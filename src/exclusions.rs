use anyhow::{bail, Context, Result};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::{json, Value};
use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::Read,
    path::Path,
};

const MAX_BYTES: u64 = 1024 * 1024;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    version: u32,
    entries: Vec<Entry>,
}
#[derive(Deserialize)]
struct Entry {
    repo: String,
    path: String,
    revision: String,
    evidence_id: String,
}
fn hex(value: &str, len: usize) -> bool {
    value.len() == len && value.bytes().all(|b| b.is_ascii_hexdigit())
}
fn load(path: &Path) -> Result<Manifest> {
    // One open descriptor survives atomic rename; never cache a last-good policy.
    let file = File::open(path).context("Required exclusion file unavailable")?;
    let metadata = file.metadata()?;
    if !metadata.is_file() || metadata.len() > MAX_BYTES {
        bail!("Exclusion file must be a regular file of at most 1 MiB");
    }
    let mut bytes = Vec::new();
    file.take(MAX_BYTES + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BYTES {
        bail!("Exclusion file exceeds 1 MiB");
    }
    let manifest: Manifest = serde_json::from_slice(&bytes).context("Invalid exclusion JSON")?;
    if manifest.version != 1 || manifest.entries.len() > 10000 {
        bail!("Exclusions require version 1 and at most 10000 entries");
    }
    for entry in &manifest.entries {
        let parts: Vec<_> = entry.repo.split('/').collect();
        let valid_repo = parts.len() == 2
            && parts.iter().all(|p| {
                !p.is_empty()
                    && *p != "."
                    && *p != ".."
                    && p.bytes()
                        .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
            });
        let parts: Vec<_> = entry.path.split('/').collect();
        let valid_path = parts.last() == Some(&"SKILL.md")
            && parts
                .iter()
                .all(|p| !p.is_empty() && *p != "." && *p != "..")
            && !entry.path.contains('\\')
            && !entry.path.chars().any(char::is_control);
        if !valid_repo || !valid_path || !hex(&entry.revision, 40) || !hex(&entry.evidence_id, 64) {
            bail!("Invalid exclusion repo, relative SKILL.md path, revision or evidence_id");
        }
    }
    Ok(manifest)
}

pub fn resolve(db: &Connection, path: Option<&Path>) -> Result<(HashSet<i64>, Value)> {
    let Some(path) = path else {
        return Ok((
            HashSet::new(),
            json!({"status":"disabled","entry_count":0,"canonical_count":0,"matched_source_count":0}),
        ));
    };
    let manifest = load(path)?;
    let targets: HashSet<_> = manifest
        .entries
        .iter()
        .map(|e| (e.repo.as_str(), e.path.as_str()))
        .collect();
    let mut parents = HashMap::new();
    let mut blocked = HashSet::new();
    let mut stmt = db.prepare("SELECT id,repo,path,dup_of FROM skills")?;
    let rows = stmt.query_map([], |r| {
        Ok((
            r.get::<_, i64>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, Option<String>>(2)?,
            r.get::<_, Option<i64>>(3)?,
        ))
    })?;
    // ponytail: one O(corpus rows) scan per request; add an indexed join if this becomes a bottleneck.
    for row in rows {
        let (id, repo, skill, parent) = row?;
        if skill
            .as_deref()
            .is_some_and(|skill| targets.contains(&(repo.as_str(), skill)))
        {
            blocked.insert(id);
        }
        parents.insert(id, parent);
    }
    let matched = blocked.len();
    let mut pending: Vec<_> = blocked.iter().copied().collect();
    while let Some(id) = pending.pop() {
        match parents.get(&id) {
            Some(Some(parent)) => {
                if blocked.insert(*parent) {
                    pending.push(*parent);
                }
            }
            Some(None) => {}
            None => bail!("Exclusion encountered a missing duplicate target"),
        }
    }
    let canonical = blocked
        .iter()
        .filter(|id| parents.get(id) == Some(&None))
        .count();
    Ok((
        blocked,
        json!({"status":"active","entry_count":manifest.entries.len(),"canonical_count":canonical,"matched_source_count":matched}),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounded_validated_manifest() {
        let path = std::env::temp_dir().join(format!("jev-policy-{}.json", std::process::id()));
        let valid = json!({"version":1,"entries":[{"repo":"owner/repo","path":"nested/SKILL.md","revision":"a".repeat(40),"evidence_id":"b".repeat(64)}]});
        std::fs::write(&path, valid.to_string()).unwrap();
        assert!(load(&path).is_ok());
        for (field, value) in [
            ("repo", "owner/repo/extra"),
            ("path", "../SKILL.md"),
            ("path", "/SKILL.md"),
            ("path", "nested/skill.md"),
            ("revision", "bad"),
            ("evidence_id", "g"),
        ] {
            let mut bad = valid.clone();
            bad["entries"][0][field] = json!(value);
            std::fs::write(&path, bad.to_string()).unwrap();
            assert!(load(&path).is_err(), "{field}: {value}");
        }
        for bad in [
            json!({"version":2,"entries":[]}),
            json!({"version":1,"entries":vec![valid["entries"][0].clone();10001]}),
            json!({"version":1,"entries":[{"repo":"owner/repo"}]}),
        ] {
            std::fs::write(&path, bad.to_string()).unwrap();
            assert!(load(&path).is_err());
        }
        std::fs::write(&path, vec![b' '; MAX_BYTES as usize + 1]).unwrap();
        assert!(load(&path).is_err());
        std::fs::remove_file(path).unwrap();
    }
}
