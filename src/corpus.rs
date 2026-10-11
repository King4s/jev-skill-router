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

pub fn search(path: &Path, text: &str, top: Option<i64>) -> Result<Value> {
    let top = validate(text, top)?;
    let words = tokens(text);
    let db = open(path)?;
    // One read snapshot covers both candidates and their corpus identity.
    let tx = db.unchecked_transaction()?;
    let corpus = meta(&tx)?;
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
        for row in stmt.query_map(rusqlite::params![positive.join(" OR "), top as i64], |r| {
            Ok(json!({"id": r.get::<_,i64>(0)?, "name": r.get::<_,String>(1)?,
                "desc": r.get::<_,String>(2)?, "repo": r.get::<_,String>(3)?,
                "url": r.get::<_,String>(4)?, "tier": r.get::<_,String>(5)?, "bm25": r.get::<_,f64>(6)?}))
        })? { candidates.push(row?); }
    }
    Ok(
        json!({"candidates": candidates, "meta": {"top":top,"rule":"plain","query_tokens":words,"corpus":corpus}}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
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
