use anyhow::{bail, Result};
use regex::Regex;
use rusqlite::{Connection, OpenFlags};
use serde_json::{json, Value};
use std::{
    collections::{BTreeMap, HashSet},
    path::Path,
    sync::OnceLock,
};

pub fn tokens(text: &str) -> Vec<String> {
    static RE: OnceLock<Regex> = OnceLock::new();
    let re = RE.get_or_init(|| Regex::new(r"[\p{L}\p{N}]+").unwrap());
    let mut seen = HashSet::new();
    re.find_iter(text)
        .map(|m| m.as_str())
        .filter(|w| w.chars().count() >= 2 && !w.chars().all(crate::digits::is_digit))
        .filter(|w| seen.insert(w.to_string()))
        .take(40)
        .map(str::to_string)
        .collect()
}

pub fn validate(text: &str, top: Option<i64>) -> Result<usize> {
    let top = top.unwrap_or(40);
    if !(1..=300).contains(&top) {
        bail!("top must be in [1,300]");
    }
    if text.len() > 16384 {
        bail!("query/project exceeds 16384 UTF-8 bytes");
    }
    Ok(top as usize)
}

pub fn open(path: &Path) -> Result<Connection> {
    let c = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    c.busy_timeout(std::time::Duration::from_secs(5))?;
    Ok(c)
}

fn meta(db: &Connection) -> Result<Value> {
    let unique: i64 = db.query_row(
        "SELECT COUNT(*) FROM skills WHERE dup_of IS NULL",
        [],
        |r| r.get(0),
    )?;
    let sources: i64 = db.query_row("SELECT COUNT(*) FROM sources", [], |r| r.get(0))?;
    let has_meta: bool = db.query_row(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE name='index_meta')",
        [],
        |r| r.get(0),
    )?;
    let mut stored = BTreeMap::<String, String>::new();
    if has_meta {
        let mut stmt = db.prepare("SELECT key,value FROM index_meta")?;
        for row in stmt.query_map([], |r| Ok((r.get(0)?, r.get(1)?)))? {
            let (k, v) = row?;
            stored.insert(k, v);
        }
    }
    let coverage: Value = stored
        .get("coverage")
        .map(|s| serde_json::from_str(s))
        .transpose()?
        .unwrap_or(Value::Null);
    Ok(
        json!({"unique": unique, "sources": sources, "identity": stored.get("identity"),
        "created_at": stored.get("created_at"), "parser_version": stored.get("parser_version"), "coverage": coverage}),
    )
}

pub fn stats(path: &Path) -> Result<Value> {
    let db = open(path)?;
    let tx = db.unchecked_transaction()?;
    let total: i64 = tx.query_row("SELECT COUNT(*) FROM skills", [], |r| r.get(0))?;
    let corpus = meta(&tx)?;
    Ok(
        json!({"rows": total, "duplicates": total-corpus["unique"].as_i64().unwrap(), "corpus": corpus}),
    )
}

pub fn search(
    path: &Path,
    text: &str,
    top: Option<i64>,
    exclusions: Option<&Path>,
) -> Result<Value> {
    let top = validate(text, top)?;
    let words = tokens(text);
    let db = open(path)?;
    // One read snapshot covers both candidates and their corpus identity.
    let tx = db.unchecked_transaction()?;
    let corpus = meta(&tx)?;
    let (blocked, exclusion_meta) = crate::exclusions::resolve(&tx, exclusions)?;
    let mut positive = Vec::new();
    for word in &words {
        let found: i64 = tx.query_row(
            "SELECT COUNT(*) FROM skills_fts WHERE skills_fts MATCH ?1",
            [format!("\"{word}\"")],
            |r| r.get(0),
        )?;
        if found > 0 {
            positive.push(format!("\"{word}\""));
        }
    }
    let mut candidates = Vec::new();
    if !positive.is_empty() {
        let mut stmt = tx.prepare("SELECT s.id,s.name,s.desc,s.repo,s.url,s.tier,bm25(skills_fts) AS r FROM skills_fts JOIN skills s ON s.id=skills_fts.rowid WHERE skills_fts MATCH ?1 AND s.dup_of IS NULL ORDER BY r LIMIT ?2")?;
        for row in stmt.query_map(rusqlite::params![positive.join(" OR "), if blocked.is_empty() { top as i64 } else { -1 }], |r| {
            Ok(json!({"id": r.get::<_,i64>(0)?, "name": r.get::<_,String>(1)?,
                "desc": r.get::<_,String>(2)?, "repo": r.get::<_,String>(3)?,
                "url": r.get::<_,String>(4)?, "tier": r.get::<_,String>(5)?, "bm25": r.get::<_,f64>(6)?}))
        })? {
            let candidate = row?;
            if !blocked.contains(&candidate["id"].as_i64().unwrap()) {
                candidates.push(candidate);
                if candidates.len() == top { break; }
            }
        }
    }
    Ok(
        json!({"candidates": candidates, "meta": {"top":top,"rule":"plain","query_tokens":words,"corpus":corpus,"exclusions":exclusion_meta}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exclusions_reload_refill_and_fail_closed() {
        let dir = std::env::temp_dir().join(format!("jev-exclusions-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("skills.db");
        let gate = dir.join("exclusions.json");
        let db = Connection::open(&path).unwrap();
        db.execute_batch("CREATE TABLE skills(id INTEGER PRIMARY KEY,name TEXT,desc TEXT,repo TEXT,path TEXT,url TEXT,tier TEXT,dup_of INTEGER);
            CREATE TABLE sources(repo TEXT);
            CREATE VIRTUAL TABLE skills_fts USING fts5(name,desc);
            INSERT INTO skills VALUES(1,'PDF','PDF PDF PDF','owner/repo','bad/SKILL.md','url','vendor',NULL),
            (2,'PDF','PDF','owner/repo','safe/SKILL.md','url','vendor',NULL),
            (3,'PDF','PDF','other/repo','bad/SKILL.md','url','vendor',NULL),
            (4,'PDF','PDF','alias/repo','alias/SKILL.md','url','vendor',1),
            (5,'PDF','PDF','alias/repo','alias/SKILL.md','url','vendor',3);
            INSERT INTO skills_fts(rowid,name,desc) SELECT id,name,desc FROM skills;").unwrap();
        drop(db);
        let publish = |repo: &str, skill: &str| {
            let next = dir.join("next.json");
            std::fs::write(&next, json!({"version":1,"entries":[{"repo":repo,"path":skill,"revision":"a".repeat(40),"evidence_id":"b".repeat(64),"reason":"fixture"}]}).to_string()).unwrap();
            std::fs::rename(next, &gate).unwrap();
        };
        let ids = |value: &Value| {
            value["candidates"]
                .as_array()
                .unwrap()
                .iter()
                .map(|c| c["id"].as_i64().unwrap())
                .collect::<Vec<_>>()
        };
        let baseline = search(&path, "PDF", Some(1), None).unwrap();
        assert_eq!(ids(&baseline), vec![1]);
        publish("owner/repo", "bad/SKILL.md");
        let filtered = search(&path, "PDF", Some(2), Some(&gate)).unwrap();
        assert_eq!(ids(&filtered).len(), 2);
        assert!(!ids(&filtered).contains(&1));
        assert!(ids(&filtered).contains(&2));
        assert!(ids(&filtered).contains(&3));
        assert_eq!(filtered["meta"]["exclusions"]["canonical_count"], 1);
        publish("alias/repo", "alias/SKILL.md");
        let aliases = search(&path, "PDF", Some(2), Some(&gate)).unwrap();
        assert_eq!(ids(&aliases), vec![2]);
        assert_eq!(aliases["meta"]["exclusions"]["canonical_count"], 2);
        publish("owner/repo", "safe/SKILL.md");
        assert_eq!(
            ids(&search(&path, "PDF", Some(1), Some(&gate)).unwrap()),
            vec![1]
        );
        std::fs::write(&gate, "{").unwrap();
        assert!(search(&path, "PDF", None, Some(&gate)).is_err());
        std::fs::remove_file(&gate).unwrap();
        assert!(search(&path, "", None, Some(&gate)).is_err());
        assert_eq!(ids(&search(&path, "PDF", Some(1), None).unwrap()), vec![1]);
        std::fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn tokens_and_limits() {
        assert_eq!(
            tokens("MCP-service C++ PDF PDF １２ ²² ⅫⅫ a _sqlite"),
            vec!["MCP", "service", "PDF", "ⅫⅫ", "sqlite"]
        );
        assert!(validate("pdf", Some(0)).is_err());
        assert!(validate(&"x".repeat(16385), None).is_err());
        assert_eq!(validate("", None).unwrap(), 40);
    }
    #[test]
    fn missing_database_is_not_created() {
        let path = std::env::temp_dir().join(format!("jev-missing-{}.db", std::process::id()));
        assert!(!path.exists());
        assert!(open(&path).is_err());
        assert!(!path.exists());
    }
}
