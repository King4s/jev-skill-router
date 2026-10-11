//! Offline batch maintenance; cron supplies the three-hour process-group timeout.
use anyhow::{bail, ensure, Context, Result};
use rusqlite::{Connection, OpenFlags};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    os::unix::fs::{chown, MetadataExt, OpenOptionsExt, PermissionsExt},
    path::{Path, PathBuf},
    process::{Command, ExitStatus, Stdio},
    sync::atomic::{AtomicUsize, Ordering},
};

const WORK: &str = "/var/lib/jev-skill-router-refresh";
const LIVE: &str = "/var/lib/jev-skill-router/skills.db";
const INDEXER: &str = "/opt/jev-skill-router/offline/router.py";
const PYTHON: &str = "/opt/jev-skill-router/offline/.venv/bin/python3";
const ACCOUNT: &str = "jev-skill-refresh";
const TOKEN: &str = "/etc/jev-skill-router-refresh.token";
const LIST_LIMIT: usize = 1_048_576;

fn commit_sha(s: &str) -> bool {
    s.len() == 40
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn lock(path: &Path) -> Result<File> {
    let file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .mode(0o600)
        .open(path)?;
    file.try_lock()
        .context("Refresh already running; not queued")?;
    Ok(file)
}

// Root-controlled directories keep these reserved files out of the worker's reach.
struct Temporary(PathBuf);
impl Temporary {
    fn new(dir: &Path) -> Result<Self> {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = dir.join(format!(
            ".jev-refresh-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&path)?;
        Ok(Self(path))
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn snapshot(source: &Path, destination: &Path) -> Result<()> {
    Connection::open_with_flags(source, OpenFlags::SQLITE_OPEN_READ_ONLY)?.execute(
        "VACUUM INTO ?1",
        [destination.to_str().context("Non-UTF-8 database path")?],
    )?;
    Ok(())
}

fn count(db: &Connection, sql: &str) -> Result<i64> {
    Ok(db.query_row(sql, [], |r| r.get(0))?)
}

fn validate(db: &Connection, manifest: &[(String, String)]) -> Result<()> {
    ensure!(!manifest.is_empty(), "Empty source manifest");
    // Stamping provenance must not invoke worker-supplied triggers.
    ensure!(
        count(
            db,
            "SELECT COUNT(*) FROM sqlite_master WHERE type IN ('trigger','view')"
        )? == 0,
        "Unexpected executable database schema"
    );
    let integrity = db
        .prepare("PRAGMA integrity_check")?
        .query_map([], |r| r.get::<_, String>(0))?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    ensure!(integrity == ["ok"], "SQLite integrity check failed");
    let mut actual = BTreeMap::new();
    let mut discovered = 0i64;
    let mut stmt = db.prepare("SELECT repo,tier,branch,listed,truncated FROM sources")?;
    for row in stmt.query_map([], |r| {
        Ok((
            r.get::<_, String>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, String>(2)?,
            r.get::<_, i64>(3)?,
            r.get::<_, i64>(4)?,
        ))
    })? {
        let (repo, tier, branch, listed, truncated) = row?;
        ensure!(
            commit_sha(&branch) && truncated == 0 && listed >= 0,
            "Incomplete source revision/tree"
        );
        let accounted: i64 = db.query_row("SELECT (SELECT COUNT(*) FROM skills WHERE repo=?1)+(SELECT COUNT(*) FROM index_skips WHERE repo=?1)", [&repo], |r| r.get(0))?;
        ensure!(accounted == listed, "Source path coverage mismatch");
        discovered = discovered
            .checked_add(listed)
            .context("Source count overflow")?;
        ensure!(actual.insert(repo, tier).is_none(), "Duplicate source");
    }
    let expected: BTreeMap<_, _> = manifest.iter().cloned().collect();
    ensure!(
        expected.len() == manifest.len() && actual == expected,
        "Source manifest mismatch"
    );
    let coverage: String = db.query_row(
        "SELECT value FROM index_meta WHERE key='coverage'",
        [],
        |r| r.get(0),
    )?;
    let coverage: Value = serde_json::from_str(&coverage).context("Invalid coverage JSON")?;
    ensure!(
        coverage.as_object().is_some_and(|o| o.len() == 7),
        "Invalid coverage fields"
    );
    let mut values = Vec::new();
    for key in [
        "discovered",
        "cached",
        "parsed",
        "missing_metadata",
        "known_negative_fixture",
        "fetch_failed",
        "parse_failed",
    ] {
        values.push(
            coverage[key]
                .as_i64()
                .filter(|n| *n >= 0)
                .context("Invalid coverage count")?,
        );
    }
    let [reported, cached, parsed, missing, known, fetch, parse]: [i64; 7] =
        values.try_into().unwrap();
    let rows = count(db, "SELECT COUNT(*) FROM skills")?;
    ensure!(
        fetch == 0 && parse == 0,
        "Fetch/parse failures refuse publication"
    );
    ensure!(
        reported == discovered
            && rows > 0
            && rows == count(db, "SELECT COUNT(*) FROM fm")?
            && cached.checked_add(parsed) == Some(rows)
            && rows.checked_add(missing).and_then(|n| n.checked_add(known)) == Some(discovered),
        "Coverage totals mismatch or empty corpus"
    );
    let mut skips = BTreeMap::new();
    for row in db
        .prepare("SELECT reason,COUNT(*) FROM index_skips GROUP BY reason")?
        .query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?)))?
    {
        let (reason, n) = row?;
        ensure!(
            ["missing_metadata", "known_negative_fixture"].contains(&reason.as_str()),
            "Unapproved skip reason"
        );
        skips.insert(reason, n);
    }
    ensure!(
        skips.get("missing_metadata").copied().unwrap_or(0) == missing
            && skips.get("known_negative_fixture").copied().unwrap_or(0) == known,
        "Skip category coverage mismatch"
    );
    for (sql, message) in [
        ("SELECT COUNT(*) FROM skills s LEFT JOIN sources r ON r.repo=s.repo LEFT JOIN fm f ON f.repo=s.repo AND f.path=s.path WHERE r.repo IS NULL OR s.tier IS NOT r.tier OR f.repo IS NULL OR s.name IS NOT f.name OR s.desc IS NOT f.desc OR s.tags IS NOT f.tags OR s.name IS NULL OR trim(s.name)='' OR s.desc IS NULL OR trim(s.desc)='' OR s.tags IS NULL OR s.fp IS NULL OR s.fp=''", "Skill/cache/source metadata mismatch"),
        ("SELECT COUNT(*) FROM fm f LEFT JOIN skills s ON s.repo=f.repo AND s.path=f.path WHERE s.id IS NULL OR f.sha IS NULL OR f.sha=''", "Orphan cache row"),
        ("SELECT COUNT(*) FROM (SELECT repo,path FROM skills GROUP BY repo,path HAVING COUNT(*)<>1)", "Duplicate skill path"),
        ("SELECT COUNT(*) FROM index_skips k LEFT JOIN sources r ON r.repo=k.repo WHERE r.repo IS NULL OR k.path IS NULL OR k.sha IS NULL OR k.sha='' OR EXISTS(SELECT 1 FROM skills s WHERE s.repo=k.repo AND s.path=k.path)", "Orphan/overlapping skip row"),
        ("SELECT COUNT(*) FROM skills s LEFT JOIN skills c ON c.id=s.dup_of WHERE s.dup_of IS NOT NULL AND (c.id IS NULL OR c.dup_of IS NOT NULL OR s.fp IS NOT c.fp)", "Invalid duplicate target"),
        ("SELECT COUNT(*) FROM (SELECT fp FROM skills GROUP BY fp HAVING SUM(dup_of IS NULL)<>1)", "Incoherent canonical fingerprints"),
        ("SELECT COUNT(*) FROM (SELECT id,name,desc,tags FROM skills WHERE dup_of IS NULL EXCEPT SELECT rowid,name,desc,tags FROM skills_fts)", "Missing canonical FTS metadata"),
        ("SELECT COUNT(*) FROM (SELECT rowid,name,desc,tags FROM skills_fts EXCEPT SELECT id,name,desc,tags FROM skills WHERE dup_of IS NULL)", "Extra/wrong FTS metadata"),
    ] { ensure!(count(db,sql)? == 0, "{message}"); }
    db.execute(
        "INSERT INTO skills_fts(skills_fts) VALUES('integrity-check')",
        [],
    )?;
    Ok(())
}

fn finish_file(path: &Path, original: &fs::Metadata) -> Result<()> {
    chown(path, Some(original.uid()), Some(original.gid()))?;
    fs::set_permissions(path, fs::Permissions::from_mode(original.mode() & 0o777))?;
    File::open(path)?.sync_all()?;
    Ok(())
}

fn publish(staged: &Path, live: &Path, sources: &[(String, String)], revision: &str) -> Result<()> {
    ensure!(commit_sha(revision), "Invalid source-list revision");
    let original = fs::symlink_metadata(live)?;
    ensure!(original.is_file(), "Live database must be a regular file");
    let dir = live.parent().context("Missing live directory")?;
    let candidate = Temporary::new(dir)?;
    // Snapshot the unprivileged candidate BEFORE validation; never copy it afterwards.
    snapshot(staged, &candidate.0)?;
    {
        let db = Connection::open(&candidate.0)?;
        validate(&db, sources)?;
        db.execute(
            "INSERT OR REPLACE INTO index_meta(key,value) VALUES('source_list_revision',?1)",
            [revision],
        )?;
        db.close().map_err(|(_, e)| e)?;
    }
    finish_file(&candidate.0, &original)?;
    let previous = Temporary::new(dir)?;
    snapshot(live, &previous.0)?;
    finish_file(&previous.0, &original)?;
    fs::rename(&previous.0, dir.join("skills.previous.db"))?;
    File::open(dir)?.sync_all()?;
    fs::rename(&candidate.0, live)?;
    File::open(dir)?.sync_all()?;
    Ok(())
}

fn protected(path: &Path, directory: bool) -> Result<fs::Metadata> {
    let m = fs::symlink_metadata(path)?;
    ensure!(
        m.uid() == 0 && m.mode() & 0o022 == 0 && if directory { m.is_dir() } else { m.is_file() },
        "Unprotected root control path"
    );
    Ok(m)
}

fn worker(uid: u32, gid: u32, token: &str, incoming: &Path) -> Command {
    let mut cmd = Command::new("/usr/bin/setpriv");
    cmd.args([
        "--reuid",
        &uid.to_string(),
        "--regid",
        &gid.to_string(),
        "--clear-groups",
    ])
    .env_clear()
    .env("PATH", "/usr/bin:/bin")
    .env("HOME", "/nonexistent")
    .env("LANG", "C.UTF-8")
    .env("TMPDIR", incoming)
    .env("GH_TOKEN", token)
    .current_dir(incoming)
    .stdin(Stdio::null())
    .stderr(Stdio::null());
    cmd
}

fn bounded_capture(mut cmd: Command, limit: usize, stderr: bool) -> Result<(ExitStatus, Vec<u8>)> {
    cmd.stdout(if stderr {
        Stdio::null()
    } else {
        Stdio::piped()
    });
    if stderr {
        cmd.stderr(Stdio::piped());
    }
    let mut child = cmd.spawn().context("Cannot start refresh subprocess")?;
    let mut data = Vec::new();
    let read = if stderr {
        child
            .stderr
            .take()
            .unwrap()
            .take(limit as u64 + 1)
            .read_to_end(&mut data)
    } else {
        child
            .stdout
            .take()
            .unwrap()
            .take(limit as u64 + 1)
            .read_to_end(&mut data)
    };
    if read.is_err() || data.len() > limit {
        let _ = child.kill();
        let status = child.wait()?;
        bail!("Refresh subprocess output failed/exceeded limit; {status}");
    }
    Ok((child.wait()?, data))
}

fn bounded_output(cmd: Command, limit: usize) -> Result<Vec<u8>> {
    let (status, data) = bounded_capture(cmd, limit, false)?;
    ensure!(
        status.success(),
        "Refresh subprocess failed; {status} (output withheld)"
    );
    Ok(data)
}

fn indexer(cmd: Command, sources: &[(String, String)], token: &str) -> Result<()> {
    // Only stderr's existing, recognized fields cross the root log boundary; stdout/body is discarded.
    let (status, data) = bounded_capture(cmd, 65536, true).map_err(|e| {
        anyhow::anyhow!("Indexer failed; live database unchanged; {e}\n{{\"category\":\"indexer_failed\",\"repo\":null,\"path\":null}}")
    })?;
    let mut records = Vec::new();
    let mut overflow = false;
    for line in String::from_utf8_lossy(&data).lines() {
        let failure =
            ["fetch_failed", "parse_failed"]
                .into_iter()
                .find_map(|category| {
                    line.strip_prefix(&format!("[index] {category}: "))
                        .and_then(|target| {
                            sources.iter().find_map(|(repo, _)| {
                                let path = target.strip_prefix(&format!("{repo}/"))?;
                                (path.len() <= 1024
                                    && path.ends_with("SKILL.md")
                                    && !path.chars().any(char::is_control))
                                .then_some((category, repo.as_str(), Some(path)))
                            })
                        })
                })
                .or_else(|| {
                    [
                        "error: GitHub lookup failed: repos/",
                        "error: Invalid GitHub JSON: repos/",
                        "error: Invalid GitHub object: repos/",
                        "error: Incomplete repository metadata: ",
                        "error: Missing commit revision: ",
                        "error: Incomplete/truncated pinned Git tree: ",
                        "error: Command '['gh', 'api', '-H', 'Accept: application/vnd.github+json', 'repos/",
                    ]
                    .into_iter()
                    .find_map(|prefix| {
                        let target = line.strip_prefix(prefix)?.split(": ").next()?;
                        let target = if prefix.starts_with("error: Command ") {
                            target.split_once("']' timed out after ")?.0
                        } else {
                            target
                        };
                        sources.iter().find_map(|(repo, _)| {
                            // Never log branch names, API error text, or HTTP bodies.
                            let endpoint = if target.contains("/git/trees/") || prefix.contains("Git tree") {
                                "git/trees"
                            } else if target.contains("/git/ref/heads/") || prefix.contains("commit revision") {
                                "git/ref/heads"
                            } else {
                                "repository"
                            };
                            (target == repo || target.starts_with(&format!("{repo}/git/")))
                                .then_some(("discovery_failed", repo.as_str(), Some(endpoint)))
                        })
                    })
                });
        if let Some((category, repo, path)) = failure {
            if records.len() == 32 {
                overflow = true;
                break;
            }
            if repo.len() <= 256 {
                records.push(
                    serde_json::json!({
                        "category": category,
                        "repo": repo.replace(token, "***"),
                        "path": path.map(|p| p.replace(token, "***")),
                    })
                    .to_string(),
                );
            }
        }
        // cmd_index aborts at discovery errors; any following lines can be an echoed HTTP body.
        if line.starts_with("error: ") {
            break;
        }
    }
    if !status.success() || !records.is_empty() {
        if records.is_empty() {
            records.push(r#"{"category":"indexer_failed","repo":null,"path":null}"#.into());
        }
        bail!(
            "Indexer failed; {status}; live database unchanged{}\n{}",
            if overflow {
                "; diagnostic record limit exceeded"
            } else {
                ""
            },
            records.join("\n")
        );
    }
    Ok(())
}

fn id(flag: &str, account: Option<&str>) -> Result<u32> {
    let mut cmd = Command::new("/usr/bin/id");
    cmd.env_clear()
        .arg(flag)
        .stdin(Stdio::null())
        .stderr(Stdio::null());
    if let Some(account) = account {
        cmd.arg(account);
    }
    Ok(std::str::from_utf8(&bounded_output(cmd, 64)?)?
        .trim()
        .parse()?)
}

fn run() -> Result<()> {
    ensure!(
        std::env::args().len() == 1 && id("-u", None)? == 0,
        "Run without arguments as root"
    );
    let work = Path::new(WORK);
    protected(work, true)?;
    let _lock = lock(&work.join("refresh.lock"))?;
    let live = Path::new(LIVE);
    protected(live.parent().unwrap(), true)?;
    protected(live, false)?;
    protected(Path::new(INDEXER), false)?;
    protected(Path::new(INDEXER).parent().unwrap(), true)?;
    let uid = id("-u", Some(ACCOUNT))?;
    let gid = id("-g", Some(ACCOUNT))?;
    ensure!(uid != 0 && gid != 0, "Refresh account must be unprivileged");
    let incoming = work.join("incoming");
    let m = fs::symlink_metadata(&incoming)?;
    ensure!(
        m.is_dir() && m.uid() == uid && m.gid() == gid && m.mode() & 0o022 == 0,
        "Unsafe incoming directory"
    );
    let m = protected(Path::new(TOKEN), false)?;
    ensure!(
        m.mode() & 0o077 == 0 && m.len() <= 4096,
        "Token must be root-only and bounded"
    );
    let token = fs::read_to_string(TOKEN).context("Cannot read refresh credential")?;
    let token = token.trim();
    ensure!(
        !token.is_empty() && token.is_ascii() && !token.bytes().any(|b| b.is_ascii_whitespace()),
        "Invalid refresh credential"
    );
    let gh = |endpoint: &str, accept: &str| {
        let mut cmd = worker(uid, gid, token, &incoming);
        cmd.args([
            "/usr/bin/timeout",
            "60",
            "/usr/bin/gh",
            "api",
            "-H",
            accept,
            endpoint,
        ]);
        cmd
    };
    let reference: Value = serde_json::from_slice(&bounded_output(
        gh(
            "repos/King4s/jev-skill-router/git/ref/heads/main",
            "Accept: application/vnd.github+json",
        ),
        65536,
    )?)?;
    let revision = reference["object"]["sha"]
        .as_str()
        .context("Missing source-list commit")?;
    ensure!(
        reference["object"]["type"] == "commit" && commit_sha(revision),
        "Invalid source-list commit"
    );
    let data = bounded_output(
        gh(
            &format!("repos/King4s/jev-skill-router/contents/Skills-list.md?ref={revision}"),
            "Accept: application/vnd.github.raw+json",
        ),
        LIST_LIMIT,
    )?;
    std::str::from_utf8(&data).context("Source list must be UTF-8")?;
    let list_temp = Temporary::new(work)?;
    File::options()
        .write(true)
        .open(&list_temp.0)?
        .write_all(&data)?;
    fs::set_permissions(&list_temp.0, fs::Permissions::from_mode(0o444))?;
    File::open(&list_temp.0)?.sync_all()?;
    let list = work.join("Skills-list.md");
    fs::rename(&list_temp.0, &list)?;
    let mut cmd = worker(uid, gid, token, &incoming);
    cmd.args([PYTHON, INDEXER, "sources", "--sources"])
        .arg(&list);
    let sources: Vec<(String, String)> =
        serde_json::from_slice(&bounded_output(cmd, 2 * LIST_LIMIT)?)?;
    ensure!(!sources.is_empty(), "Empty source manifest");
    // Seed in the root directory, not a worker-controlled VACUUM destination.
    let seed = Temporary::new(work)?;
    snapshot(live, &seed.0)?;
    chown(&seed.0, Some(uid), Some(gid))?;
    let staged = incoming.join("staging.db");
    for suffix in ["-journal", "-wal", "-shm"] {
        match fs::remove_file(incoming.join(format!("staging.db{suffix}"))) {
            Ok(()) => (),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(e) => return Err(e.into()),
        }
    }
    fs::rename(&seed.0, &staged)?;
    let mut cmd = worker(uid, gid, token, &incoming);
    cmd.args([PYTHON, INDEXER, "index", "--sources"])
        .arg(&list)
        .arg("--db")
        .arg(&staged)
        .args(["--workers", "12"]);
    indexer(cmd, &sources, token)?;
    publish(&staged, live, &sources, revision)?;
    println!(
        "Published source-list revision {revision} from {} sources",
        sources.len()
    );
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Refresh failed: {e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::{Connection, OpenFlags};
    use std::{
        os::unix::fs::{MetadataExt, PermissionsExt},
        path::PathBuf,
        sync::atomic::{AtomicUsize, Ordering},
    };
    const SHA: &str = "0123456789abcdef0123456789abcdef01234567";
    const SCHEMA: &str = "
        CREATE TABLE skills(id INTEGER PRIMARY KEY,name TEXT,desc TEXT,tags TEXT,tier TEXT,repo TEXT,stars INTEGER,path TEXT,url TEXT,fp TEXT,dup_of INTEGER,seen_at TEXT);
        CREATE VIRTUAL TABLE skills_fts USING fts5(name,desc,tags);
        CREATE TABLE sources(repo TEXT PRIMARY KEY,tier TEXT,branch TEXT,stars INTEGER,listed INTEGER,truncated INTEGER,note TEXT,seen_at TEXT);
        CREATE TABLE fm(repo TEXT,path TEXT,sha TEXT,name TEXT,desc TEXT,tags TEXT,PRIMARY KEY(repo,path));
        CREATE TABLE index_skips(repo TEXT,path TEXT,sha TEXT,reason TEXT,PRIMARY KEY(repo,path));
        CREATE TABLE index_meta(key TEXT PRIMARY KEY,value TEXT);";
    struct Scratch(PathBuf);
    impl Scratch {
        fn new() -> Self {
            static NEXT: AtomicUsize = AtomicUsize::new(0);
            let p = std::env::temp_dir().join(format!(
                "jev-refresh-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&p).unwrap();
            Self(p)
        }
    }
    impl Drop for Scratch {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    fn manifest() -> Vec<(String, String)> {
        vec![("example/repo".into(), "vendor".into())]
    }
    fn fixture(path: &Path, name: &str) {
        let db = Connection::open(path).unwrap();
        db.execute_batch(SCHEMA).unwrap();
        db.execute("INSERT INTO sources(repo,tier,branch,stars,listed,truncated,note) VALUES('example/repo','vendor',?1,0,4,0,'')", [SHA]).unwrap();
        for (id, path, dup) in [(1, "a/SKILL.md", None), (2, "b/SKILL.md", Some(1))] {
            db.execute("INSERT INTO skills(id,name,desc,tags,tier,repo,stars,path,url,fp,dup_of) VALUES(?1,?2,'Read PDFs','docs','vendor','example/repo',0,?3,'url','same',?4)", rusqlite::params![id,name,path,dup]).unwrap();
            db.execute(
                "INSERT INTO fm VALUES('example/repo',?1,?2,?3,'Read PDFs','docs')",
                rusqlite::params![path, SHA, name],
            )
            .unwrap();
        }
        db.execute(
            "INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(1,?1,'Read PDFs','docs')",
            [name],
        )
        .unwrap();
        db.execute("INSERT INTO index_skips VALUES('example/repo','missing/SKILL.md',?1,'missing_metadata')", [SHA]).unwrap();
        db.execute("INSERT INTO index_skips VALUES('example/repo','negative/SKILL.md',?1,'known_negative_fixture')", [SHA]).unwrap();
        db.execute("INSERT INTO index_meta VALUES('coverage',?1)", [r#"{"discovered":4,"cached":1,"parsed":1,"missing_metadata":1,"known_negative_fixture":1,"fetch_failed":0,"parse_failed":0}"#]).unwrap();
    }
    fn name(db: &Connection) -> String {
        db.query_row("SELECT name FROM skills WHERE id=1", [], |r| r.get(0))
            .unwrap()
    }
    #[test]
    fn replacement_preserves_old_readers_and_one_previous_snapshot() {
        let root = Scratch::new();
        let live = root.0.join("skills.db");
        let staged = root.0.join("staging.db");
        fixture(&live, "old");
        fixture(&staged, "new");
        fs::set_permissions(&live, fs::Permissions::from_mode(0o640)).unwrap();
        let original = fs::metadata(&live).unwrap();
        let reader = Connection::open_with_flags(&live, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        reader.execute_batch("BEGIN").unwrap();
        assert_eq!(name(&reader), "old");
        publish(&staged, &live, &manifest(), SHA).unwrap();
        assert_eq!(name(&Connection::open(&live).unwrap()), "new");
        assert_eq!(name(&reader), "old");
        let previous = root.0.join("skills.previous.db");
        assert_eq!(name(&Connection::open(&previous).unwrap()), "old");
        for path in [&live, &previous] {
            let m = fs::metadata(path).unwrap();
            assert_eq!(
                (m.uid(), m.gid(), m.mode() & 0o777),
                (original.uid(), original.gid(), 0o640)
            );
        }
        let db = Connection::open(&live).unwrap();
        assert_eq!(
            db.query_row(
                "SELECT value FROM index_meta WHERE key='source_list_revision'",
                [],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            SHA
        );
        drop(db);
        let reader2 = Connection::open_with_flags(&live, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        assert_eq!(name(&reader2), "new");
        publish(&staged, &live, &manifest(), SHA).unwrap();
        assert_eq!(name(&Connection::open(&previous).unwrap()), "new");
        assert_eq!(name(&reader2), "new");
    }
    #[test]
    fn invalid_candidates_preserve_live_and_previous_bytes() {
        for sql in [
            "CREATE TRIGGER sabotage AFTER INSERT ON index_meta WHEN NEW.key='source_list_revision' BEGIN DELETE FROM skills_fts; END",
            "UPDATE sources SET tier='community'",
            "UPDATE sources SET branch='main'",
            "UPDATE sources SET truncated=1",
            "UPDATE sources SET listed=5",
            "INSERT INTO sources(repo,tier,branch,listed,truncated) VALUES('extra/repo','vendor','bad',0,0)",
            "UPDATE index_meta SET value='{}' WHERE key='coverage'",
            "UPDATE index_meta SET value=json_set(value,'$.discovered',5) WHERE key='coverage'",
            "UPDATE index_meta SET value=json_set(value,'$.fetch_failed',1) WHERE key='coverage'",
            "UPDATE index_meta SET value=json_set(value,'$.parse_failed',1) WHERE key='coverage'",
            "UPDATE index_skips SET reason='unknown'",
            "UPDATE index_skips SET reason='known_negative_fixture' WHERE reason='missing_metadata'",
            "DELETE FROM fm WHERE path='a/SKILL.md'",
            "UPDATE fm SET name='wrong' WHERE path='a/SKILL.md'",
            "UPDATE skills SET repo='extra/repo' WHERE id=2",
            "UPDATE skills SET dup_of=99 WHERE id=2",
            "UPDATE skills SET fp='other' WHERE id=2",
            "UPDATE skills SET dup_of=NULL WHERE id=2",
            "DELETE FROM skills_fts",
            "UPDATE skills_fts SET desc='wrong'",
            "INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(2,'duplicate','wrong','')",
            "DELETE FROM skills; DELETE FROM fm; DELETE FROM skills_fts; DELETE FROM index_skips; UPDATE sources SET listed=0; UPDATE index_meta SET value='{\"discovered\":0,\"cached\":0,\"parsed\":0,\"missing_metadata\":0,\"known_negative_fixture\":0,\"fetch_failed\":0,\"parse_failed\":0}' WHERE key='coverage'",
        ] {
            let root = Scratch::new();
            let live = root.0.join("skills.db");
            let staged = root.0.join("staging.db");
            let previous = root.0.join("skills.previous.db");
            fixture(&live,"old"); fixture(&staged,"new"); fixture(&previous,"previous");
            let before = fs::read(&live).unwrap();
            let before_previous = fs::read(&previous).unwrap();
            Connection::open(&staged).unwrap().execute_batch(sql).unwrap();
            assert!(publish(&staged,&live,&manifest(),SHA).is_err(), "accepted {sql}");
            assert_eq!(fs::read(&live).unwrap(),before, "changed live for {sql}");
            assert_eq!(fs::read(&previous).unwrap(),before_previous);
            assert_eq!(fs::read_dir(&root.0).unwrap().count(),3, "leaked temp for {sql}");
        }
        let root = Scratch::new();
        let live = root.0.join("skills.db");
        let staged = root.0.join("staging.db");
        fixture(&live, "old");
        fixture(&staged, "new");
        let before = fs::read(&live).unwrap();
        assert!(publish(&staged, &live, &[], SHA).is_err());
        assert!(publish(&staged, &live, &manifest(), "main").is_err());
        assert_eq!(fs::read(&live).unwrap(), before);
        fs::write(&staged, b"not a SQLite database").unwrap();
        assert!(publish(&staged, &live, &manifest(), SHA).is_err());
        assert_eq!(fs::read(&live).unwrap(), before);
    }
    #[test]
    fn overlap_is_not_queued() {
        let root = Scratch::new();
        let path = root.0.join("refresh.lock");
        let held = lock(&path).unwrap();
        assert!(lock(&path).is_err());
        drop(held);
        assert!(lock(&path).is_ok());
    }
    fn failing_indexer(stderr: &str) -> Command {
        let mut cmd = Command::new("/usr/bin/python3");
        cmd.args([
            "-c",
            "import sys; sys.stdout.write('RAW_HTTP_BODY'); sys.stderr.write(sys.argv[1]); sys.exit(7)",
            stderr,
        ])
        .stderr(Stdio::null());
        cmd
    }
    #[test]
    fn indexer_failures_are_structured_bounded_and_secret_safe() {
        let token = "synthetic_GH_TOKEN_secret";
        let raw = format!(
            "[index] fetch_failed: example/repo/fetch/SKILL.md\n\
             [index] parse_failed: example/repo/quoted\"/{token}/SKILL.md\n\
             [index] parse_failed: unlisted/repo/ignored/SKILL.md\n\
             error: GitHub lookup failed: repos/example/repo: RAW_HTTP_BODY {token}\n\
             [index] fetch_failed: example/repo/RAW_HTTP_BODY/SKILL.md\n"
        );
        let error = indexer(failing_indexer(&raw), &manifest(), token)
            .unwrap_err()
            .to_string();
        assert!(error.contains("discovery_failed"), "{error}");
        assert!(error.contains("fetch_failed"), "{error}");
        assert!(error.contains("parse_failed"), "{error}");
        assert!(error.contains("example/repo"), "{error}");
        assert!(error.contains("fetch/SKILL.md"), "{error}");
        assert!(error.contains("exit status: 7"), "{error}");
        assert!(!error.contains(token), "{error}");
        assert!(!error.contains("RAW_HTTP_BODY"), "{error}");
        assert!(!error.contains("unlisted/repo"), "{error}");
        for line in error.lines().skip(1) {
            let record: Value = serde_json::from_str(line).unwrap();
            assert_eq!(record.as_object().unwrap().len(), 3);
        }
        let generic = indexer(
            failing_indexer(&format!("error: {token}")),
            &manifest(),
            token,
        )
        .unwrap_err()
        .to_string();
        assert!(generic.contains("indexer_failed"), "{generic}");
        assert!(generic.contains("exit status: 7"), "{generic}");
        assert!(!generic.contains(token));
        for (message, endpoint) in [
            ("error: Invalid GitHub JSON: repos/example/repo/git/trees/revision?recursive=1", "git/trees"),
            ("error: Invalid GitHub object: repos/example/repo", "repository"),
            ("error: Incomplete repository metadata: example/repo", "repository"),
            ("error: Missing commit revision: example/repo", "git/ref/heads"),
            ("error: Incomplete/truncated pinned Git tree: example/repo", "git/trees"),
            ("error: Command '['gh', 'api', '-H', 'Accept: application/vnd.github+json', 'repos/example/repo']' timed out after 60 seconds", "repository"),
        ] {
            let error = indexer(failing_indexer(message), &manifest(), token)
                .unwrap_err().to_string();
            let record: Value = serde_json::from_str(error.lines().nth(1).unwrap()).unwrap();
            assert_eq!(record["category"], "discovery_failed", "{error}");
            assert_eq!(record["repo"], "example/repo", "{error}");
            assert_eq!(record["path"], endpoint, "{error}");
        }
        let many = "[index] fetch_failed: example/repo/SKILL.md\n".repeat(33);
        let error = indexer(failing_indexer(&many), &manifest(), token)
            .unwrap_err()
            .to_string();
        assert!(error.contains("diagnostic record limit"), "{error}");
        assert!(error.lines().count() <= 34);
    }
    #[test]
    fn indexer_diagnostic_overflow_fails_closed_without_pipe_deadlock() {
        let mut cmd = Command::new("/usr/bin/timeout");
        cmd.args([
            "5s",
            "/usr/bin/python3",
            "-c",
            "import os;\nwhile True: os.write(2, b'x' * 4096)",
        ])
        .stderr(Stdio::null());
        let start = std::time::Instant::now();
        let error = indexer(cmd, &manifest(), "secret").unwrap_err().to_string();
        assert!(error.contains("exceeded limit"), "{error}");
        assert!(start.elapsed().as_secs() < 4, "blocked until outer timeout");
    }
    #[test]
    fn cron_logs_native_timeout_and_failure_receipt() {
        let cron = include_str!("../../deploy/jev-skill-router-refresh.cron");
        let shape = cron.lines().last().unwrap().split_once("-c '").unwrap().1;
        let scratch = Scratch::new();
        let log = scratch.0.join("timeout.log");
        let probe = shape
            .trim_end_matches('\'')
            .replace("--kill-after=30s 3h", "--kill-after=30s 0.1s")
            .replace("/opt/jev-skill-router/jev-skill-refresh", "/bin/sleep 10")
            .replace(
                "/usr/bin/logger -t jev-skill-router-refresh",
                &format!("/bin/cat > {}", log.display()),
            );
        let status = Command::new("/bin/bash")
            .args(["-o", "pipefail", "-c", &probe])
            .status()
            .unwrap();
        let output = fs::read_to_string(&log).unwrap();
        assert_eq!(status.code(), Some(124));
        assert!(output.contains("sending signal TERM"), "{output}");
        assert!(output.contains("refresh_exit_status=124"), "{output}");
        let failure = probe.replace("/bin/sleep 10", "/bin/false");
        let status = Command::new("/bin/bash")
            .args(["-o", "pipefail", "-c", &failure])
            .status()
            .unwrap();
        assert_eq!(status.code(), Some(1));
        assert!(fs::read_to_string(&log)
            .unwrap()
            .contains("refresh_exit_status=1"));
    }
    #[test]
    fn revisions_are_exact_lowercase_commit_ids() {
        assert!(commit_sha(SHA));
        for bad in [
            "main",
            "",
            &"a".repeat(39),
            &"a".repeat(41),
            &SHA.to_uppercase(),
            "../../etc/passwd",
        ] {
            assert!(!commit_sha(bad));
        }
    }
}
