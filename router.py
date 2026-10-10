#!/usr/bin/env python3
"""Skill Router — harvest skill frontmatter from source repos,
index it in SQLite FTS5, and let a decision maker like Jev rank candidates.

Why it is split this way:
  * Code finds the candidates (SQLite FTS5, stdlib, no embeddings, no deps).
  * Jev, Perplexity Decisions, or both judge the candidates with the same rubric.
  Thousands of skills cannot be one question; retrieval precedes decision making.

Usage:
  python3 router.py index                     # build/refresh the index
  python3 router.py stats                     # what is in it
  python3 router.py route "describe project"  # rank candidates with Jev
  python3 router.py route "describe project" --provider perplexity
  python3 router.py route "describe project" --provider both
  python3 router.py selftest                  # offline check of the logic

Needs: gh (authenticated) for index; TYPESAFE_API_KEY (or
~/.config/jev-loop/typesafe_api_key) for Jev, PERPLEXITY_API_KEY for Perplexity.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from decision_providers import (KEY_FILE, MAX_QUESTIONS, REQUEST_ID,
                                ProviderError, decision_call, provider_key, resolve_model)

ROOT = Path(__file__).resolve().parent
DB = ROOT / "skills.db"
SOURCES = ROOT / "Skills-list.md"          # maintained by Grok Bot
JEV_API = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
FM_BYTES = 4096          # frontmatter lives in the first few KB of the file
PER_WORD = 20            # the "pool" rule: how many documents each query word contributes
TIERS = {"1": "vendor", "2": "community", "3": "list", "4": "registry", "5": "tooling", "6": "gitlab"}

# Score levels: situations, not degrees (docs.typesafe.ai/primitives/score).
LEVELS = [
    "Irrelevant for this project — nothing in it applies",
    "Background — useful context for understanding the domain, not needed to build",
    "Directly useful — a concrete step, convention or reference this project will use",
    "Core — must be loaded before work starts, the project is built on it",
]


# ---------------------------------------------------------------- frontmatter

def _fold(v: str) -> str:
    """YAML folded scalar: > and | blocks collapse onto one line."""
    return re.sub(r"\s+", " ", v).strip().strip('"\'')


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    key: str | None = None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:", line):
            key, _, val = line.partition(":")
            key = key.strip()
            if val.strip() in {">", ">-", ">+", "|", "|-", "|+"}:   # block scalar starts
                val = ""
            out[key] = _fold(val)
        elif key and line.strip():                      # continuation of a block scalar
            out[key] = _fold(out.get(key, "") + " " + line)
    return out


def fingerprint(name: str, desc: str) -> str:
    """The same skill copied into five awesome-lists must count once."""
    norm = re.sub(r"[^a-z0-9 ]", "", f"{name} {desc}".lower())
    return hashlib.sha1(re.sub(r"\s+", " ", norm).encode()).hexdigest()


# ---------------------------------------------------------------- sources

def read_sources(path: Path) -> list[tuple[str, str]]:
    """-> [(repo, tier)]. Reads Grok Bot's markdown list (Skills-list.md) as well as
    a flat owner/repo file. The tier comes from the section number; sections without
    a number (e.g. 'Flagged / excluded') are skipped."""
    text = path.read_text(encoding="utf-8")
    tier, out, seen = "community", [], set()
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^#{2,3}\s*(\d)\.", s)
        if m:
            tier = TIERS.get(m.group(1), "community")
            continue
        if s.startswith("##"):
            tier = None                          # unnumbered section = not a source
            continue
        if tier is None:
            continue
        for repo in re.findall(r"\]\(https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\)", s):
            if repo not in seen:
                seen.add(repo)
                out.append((repo, tier))
        if not s.startswith(("-", "|", "#", ">")) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s):
            if s not in seen:
                seen.add(s)
                out.append((s, tier))
    return out


def gh_api(path: str):
    r = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def list_skill_paths(repo: str) -> tuple[str, list[tuple[str, str]], int]:
    """(branch, [(path, blob sha)], stars) via two API calls — no clone.
    The blob sha is the version key: an unchanged sha means cached frontmatter can be reused."""
    meta = gh_api(f"repos/{repo}") or {}
    branch = meta.get("default_branch", "main")
    stars = meta.get("stargazers_count", 0)
    tree = gh_api(f"repos/{repo}/git/trees/{branch}?recursive=1") or {}
    paths = [(e["path"], e.get("sha", "")) for e in tree.get("tree", [])
             if e.get("path", "").endswith("SKILL.md") and e.get("type") == "blob"]
    return branch, paths, stars


def fetch_head(repo: str, branch: str, path: str) -> str | None:
    """Only the first few KB of the file — the frontmatter is all we need."""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    req = urllib.request.Request(url, headers={
        "Range": f"bytes=0-{FM_BYTES - 1}", "User-Agent": "jev-skill-router"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read(FM_BYTES).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 416:                            # file is shorter than the range
                try:
                    return urllib.request.urlopen(
                        urllib.request.Request(url, headers={"User-Agent": "jev-skill-router"}),
                        timeout=20).read(FM_BYTES).decode("utf-8", "replace")
                except Exception:
                    return None
            if e.code in (429, 500, 502, 503) and attempt < 2:
                continue
            return None
        except Exception:
            if attempt < 2:
                continue
            return None
    return None


# ---------------------------------------------------------------- index

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY, name TEXT, desc TEXT, tags TEXT, tier TEXT, repo TEXT,
  stars INTEGER, path TEXT, url TEXT, fp TEXT, dup_of INTEGER, seen_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS skills_repo ON skills(repo);
CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(name, desc, tags);
DROP INDEX IF EXISTS skills_fp;               -- was UNIQUE: made duplicate rows impossible to store
CREATE INDEX IF NOT EXISTS skills_fp ON skills(fp);
CREATE TABLE IF NOT EXISTS sources (repo TEXT PRIMARY KEY, tier TEXT, branch TEXT,
  stars INTEGER, listed INTEGER, truncated INTEGER, note TEXT, seen_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS fm (repo TEXT, path TEXT, sha TEXT, name TEXT, desc TEXT, tags TEXT,
  PRIMARY KEY (repo, path));
"""


def cmd_index(args) -> int:
    db = sqlite3.connect(args.db)
    db.executescript(SCHEMA)
    sources = read_sources(Path(args.sources))
    print(f"[index] {len(sources)} sources from {args.sources}", flush=True)
    cache = {(r[0], r[1]): (r[2], r[3], r[4], r[5])
             for r in db.execute("SELECT repo, path, sha, name, desc, tags FROM fm")}

    # 1) find every SKILL.md path (sequentially — tree calls are cheap, the API is rate limited)
    jobs: list[tuple[str, str, str, str, int, str]] = []
    for repo, tier in sources:
        branch, paths, stars = list_skill_paths(repo)
        db.execute("INSERT OR REPLACE INTO sources(repo,tier,branch,stars,listed,note) "
                   "VALUES(?,?,?,?,?,?)",
                   (repo, tier, branch, stars, len(paths),
                    "no SKILL.md (link-list only)" if not paths else ""))
        print(f"[index]   {len(paths):5d}  {repo}", flush=True)
        jobs += [(repo, branch, p, tier, stars, sha) for p, sha in paths]
    db.commit()
    print(f"[index] {len(jobs)} SKILL.md in total", flush=True)
    meta_of = {(j[0], j[2]): (j[3], j[4], j[1]) for j in jobs}   # (repo, path) -> (tier, stars, branch)

    # 2) fetch frontmatter in parallel; an unchanged blob sha is reused from the cache
    def pull(job):
        repo, branch, path, tier, stars, sha = job
        hit = cache.get((repo, path))
        if hit and hit[0] == sha and sha:
            return (repo, path, sha, *hit[1:])
        head = fetch_head(repo, branch, path)
        if not head:
            return None
        fm = parse_frontmatter(head)
        name, desc = fm.get("name", "").strip(), fm.get("description", "").strip()
        if not name or not desc:
            return None
        return (repo, path, sha, name, desc, fm.get("tags", "") or fm.get("metadata", ""))

    rows, keep, fetched = [], [], 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for res in ex.map(pull, jobs):
            fetched += 1
            if fetched % 2000 == 0:
                print(f"[index]   processed {fetched}/{len(jobs)}", flush=True)
            if res:
                keep.append(res)
                repo, path, sha, name, desc, tags = res
                tier, stars, branch = meta_of[(repo, path)]
                rows.append((name, desc, tags, tier, repo, stars, path,
                             f"https://github.com/{repo}/blob/{branch}/{path}",
                             fingerprint(name, desc)))

    db.executemany("INSERT OR REPLACE INTO fm(repo,path,sha,name,desc,tags) VALUES(?,?,?,?,?,?)",
                   keep)

    # 3) dedupe on fingerprint: the first occurrence wins, copies are recorded as dup_of
    db.execute("DELETE FROM skills")
    db.execute("DELETE FROM skills_fts")
    seen: dict[str, int] = {}
    for name, desc, tags, tier, repo, stars, path, url, fp in rows:
        if fp in seen:
            db.execute("INSERT OR IGNORE INTO skills(name,desc,tags,tier,repo,stars,path,url,fp,dup_of)"
                       " VALUES(?,?,?,?,?,?,?,?,?,?)", (name, desc, tags, tier, repo, stars,
                                                        path, url, fp, seen[fp]))
            continue
        cur = db.execute("INSERT OR IGNORE INTO skills(name,desc,tags,tier,repo,stars,path,url,fp)"
                         " VALUES(?,?,?,?,?,?,?,?,?)",
                         (name, desc, tags, tier, repo, stars, path, url, fp))
        if cur.rowcount:
            seen[fp] = cur.lastrowid
            db.execute("INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(?,?,?,?)",
                       (cur.lastrowid, name, desc, tags))
    db.commit()

    uniq = db.execute("SELECT COUNT(*) FROM skills WHERE dup_of IS NULL").fetchone()[0]
    dups = db.execute("SELECT COUNT(*) FROM skills WHERE dup_of IS NOT NULL").fetchone()[0]
    db.execute("INSERT INTO skills_fts(skills_fts) VALUES('optimize')")
    db.commit()
    print(f"[index] done: {uniq} unique skills, {dups} duplicates filtered out")
    return 0


def cmd_stats(args) -> int:
    db = sqlite3.connect(args.db)
    q = db.execute
    total, uniq = q("SELECT COUNT(*), SUM(dup_of IS NULL) FROM skills").fetchone()
    print(f"index: {args.db}  ({total} rows, {uniq} unique, {total - uniq} duplicates)")
    print("\nper tier (unique):")
    for tier, n in q("SELECT tier, COUNT(*) FROM skills WHERE dup_of IS NULL "
                     "GROUP BY tier ORDER BY 2 DESC"):
        print(f"  {n:6d}  {tier}")
    print("\ntop 10 repos (unique):")
    for repo, n in q("SELECT repo, COUNT(*) FROM skills WHERE dup_of IS NULL "
                     "GROUP BY repo ORDER BY 2 DESC LIMIT 10"):
        print(f"  {n:6d}  {repo}")
    print("\nsources with no SKILL.md (link lists, phase 2):")
    for repo, note in q("SELECT repo, note FROM sources WHERE listed=0 ORDER BY repo"):
        print(f"    {repo}  ({note})")
    return 0


# ---------------------------------------------------------------- route

def _pool_rank(db: sqlite3.Connection, informative: list[str], dfs: dict, total: int,
               top: int) -> list[dict]:
    """Each query word contributes its own best PER_WORD documents, and the union is
    ranked by how many of the description's words a document matches before the idf sum
    breaks ties. This is what surfaces documents the single OR query buries — measured
    at 8/15 alone, but it is the only rule that finds some of them."""
    pool: dict[int, float] = {}
    matched: dict[int, int] = {}
    for w in informative:
        idf = math.log(total / dfs[w])
        for (rid,) in db.execute(
                "SELECT rowid FROM skills_fts WHERE skills_fts MATCH ? "
                "ORDER BY bm25(skills_fts) LIMIT ?", (f'"{w}"', PER_WORD)):
            pool[rid] = pool.get(rid, 0.0) + idf
            matched[rid] = matched.get(rid, 0) + 1
    best = sorted(pool.items(), key=lambda kv: (-matched[kv[0]], -kv[1]))[:top]
    if not best:
        return []
    marks = ",".join("?" * len(best))
    meta = {r[0]: r for r in db.execute(
        f"SELECT id, name, desc, repo, url, tier FROM skills WHERE id IN ({marks})",
        [b[0] for b in best])}
    return [{"id": i, "name": meta[i][1], "desc": meta[i][2], "repo": meta[i][3],
             "url": meta[i][4], "tier": meta[i][5], "score": s}
            for i, s in best if i in meta]


def shortlist(db: sqlite3.Connection, project: str, top: int, rule: str = "plain") -> list[dict]:
    """FTS5 prefilter. No embeddings: 10k rows is nothing for FTS.

    Two rules, measured against each other in scripts/eval_shortlist.py:
    * "plain" — one OR query, ranked by FTS5's bm25. Also has a variant that
      drops words with df > 30% of the corpus; measured identical on all four
      eval cases, so the filter buys nothing and is not the default.
    * "idf" — each word is looked up on its own and a document scores the sum of
      log(total/df) for the words it matches. **Measured worse (5/15 vs 11/15)**:
      one ultra-rare word ('friends', 'seventeen') weighs so much that noise beats
      documents matching several relevant words. Kept only so the eval harness can
      measure it again — it is not in use.

    Tokenisation matches FTS5's own (unicode61); otherwise compound words like
    'MCP-service' get df=0 and fall out of both rules."""
    raw = re.findall(r"[^\W_]+", project, re.UNICODE)
    words = list(dict.fromkeys(w for w in raw if len(w) >= 2 and not w.isdigit()))[:40]
    if not words:
        return []
    total = db.execute("SELECT COUNT(*) FROM skills WHERE dup_of IS NULL").fetchone()[0]

    dfs = {w: db.execute("SELECT COUNT(*) FROM skills_fts WHERE skills_fts MATCH ?",
                         (f'"{w}"',)).fetchone()[0] for w in words}
    if rule == "plain":                      # no df filtering at all
        informative = words
    else:
        informative = [w for w in words if 0 < dfs[w] < 0.30 * total] or words

    if rule in ("bm25", "plain"):
        query = " OR ".join(f'"{w}"' for w in informative)
        rows = db.execute(
            "SELECT s.id, s.name, s.desc, s.repo, s.url, s.tier, bm25(skills_fts) AS r "
            "FROM skills_fts JOIN skills s ON s.id = skills_fts.rowid "
            "WHERE skills_fts MATCH ? AND s.dup_of IS NULL ORDER BY r LIMIT ?",
            (query, top)).fetchall()
        return [{"id": r[0], "name": r[1], "desc": r[2], "repo": r[3], "url": r[4],
                 "tier": r[5], "bm25": r[6]} for r in rows]

    if rule == "pool":
        return _pool_rank(db, informative, dfs, total, top)

    if rule == "hybrid":
        # Neither rule wins alone: the single OR query keeps the strong multi-word
        # matches, the pool keeps the rare-word ones the OR query buries. Keep both,
        # the OR query taking the larger share.
        head = shortlist(db, project, math.ceil(top * 0.6), rule="plain")
        seen_ids = {c["id"] for c in head}
        tail = [c for c in _pool_rank(db, informative, dfs, total, top) if c["id"] not in seen_ids]
        return (head + tail)[:top]

    scores: dict[int, float] = {}
    for w in informative:
        idf = math.log(total / dfs[w])
        for (rid,) in db.execute("SELECT rowid FROM skills_fts WHERE skills_fts MATCH ?",
                                 (f'"{w}"',)):
            scores[rid] = scores.get(rid, 0.0) + idf
    best = sorted(scores.items(), key=lambda kv: -kv[1])[:top]
    if not best:
        return []
    marks = ",".join("?" * len(best))
    meta = {r[0]: r for r in db.execute(
        f"SELECT id, name, desc, repo, url, tier FROM skills WHERE id IN ({marks})",
        [b[0] for b in best])}
    return [{"id": i, "name": meta[i][1], "desc": meta[i][2], "repo": meta[i][3],
             "url": meta[i][4], "tier": meta[i][5], "score": s}
            for i, s in best if i in meta]


def jev_key() -> str:
    """Retain the existing helper for callers using the Jev-only interface."""
    return provider_key("jev")


def jev_call(state: dict, questions: dict, retries: int = 3) -> dict:
    return decision_call("jev", state, questions, retries=retries, model=JEV_MODEL)


def _finite_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_score(ans: dict, levels: int) -> str | None:
    """Enforce the answer contract hard. Returns an error string, or None.
    Type safety that is not enforced is only cosmetic."""
    if not isinstance(ans, dict) or ans.get("type") != "score":
        return "answer must be a score object"
    score, conf = ans.get("score"), ans.get("confidence")
    if not _finite_number(score) or not _finite_number(conf):
        return "score/confidence must be finite numbers"
    probs = ans.get("probabilities")
    if not isinstance(probs, dict):
        return "probabilities must be an object"
    if set(probs) != {str(i) for i in range(levels)}:
        return "probability keys do not match the rubric levels"
    if not all(_finite_number(value) for value in probs.values()):
        return "probabilities must be finite numbers"
    vals = [float(probs[str(i)]) for i in range(levels)]
    if not all(0.0 <= v <= 1.0 for v in vals):
        return "probability outside [0,1]"
    if abs(sum(vals) - 1.0) > 0.02:
        return f"sum {sum(vals):.3f} != 1"
    if not (0.0 <= score <= levels - 1) or not (0.0 <= conf <= 1.0):
        return f"score/confidence out of range: {score}, {conf}"
    expected = math.fsum(i * value for i, value in enumerate(vals))
    if abs(score - expected) > 0.05:
        return "score does not match the probability distribution"
    return None


def score_candidates(project: str, cands: list[dict], provider: str = "jev",
                     jev_model: str | None = None, perplexity_model: str | None = None) -> dict:
    """Rank one shared shortlist; no installation and no hidden provider fallback."""
    if provider not in ("jev", "perplexity", "both"):
        raise ProviderError("Choose a decision provider: jev, perplexity, or both.")
    if not isinstance(project, str) or not project.strip():
        raise ProviderError("The project description must not be empty.")
    names = ["jev", "perplexity"] if provider == "both" else [provider]
    overrides = {"jev": jev_model, "perplexity": perplexity_model}
    models = {name: resolve_model(name, overrides[name]) for name in names}
    result = {"schema_version": 1, "project": project, "provider": provider,
              "aggregation": "equal_mean" if provider == "both" else "single",
              "providers": {}, "ranked": [], "rejected": []}
    if cands:
        # An absent second credential must not cause a paid first-provider request.
        for name in names:
            provider_key(name)
    state = {"project": {"spec": project},
             "note": "Pick the level that matches how the candidate applies to THIS project."}
    questions = {}
    for i, c in enumerate(cands):
        questions[f"skill_{i:03d}"] = {
            "type": "score",
            "instructions": {
                "candidate_skill": {"name": c["name"], "description": c["desc"],
                                    "source_repo": c["repo"]},
                "question": "How useful is `candidate_skill` for building the project in "
                            "`project.spec`? Judge what the skill provides against what this "
                            "project actually needs.",
            },
            "criteria": LEVELS,
        }
    def score_provider(name):
        answers = {}
        metadata = {"requested_model": models[name], "resolved_models": [],
                    "calls": 0, "request_ids": [],
                    "usage": {"input_tokens": None, "output_tokens": None}}
        usage_counts = {field: 0 for field in metadata["usage"]}
        items = list(questions.items())
        for start in range(0, len(items), MAX_QUESTIONS):
            raw = decision_call(name, state, dict(items[start:start + MAX_QUESTIONS]), model=models[name])
            if not isinstance(raw, dict) or not isinstance(raw.get("answers"), dict):
                raise ProviderError(f"{name} returned an invalid answers envelope.")
            # Keep only this batch's question IDs, even if a response includes extras.
            for key, _ in items[start:start + MAX_QUESTIONS]:
                if key in raw["answers"]:
                    answers[key] = raw["answers"][key]
            metadata["calls"] += 1
            resolved = raw.get("model")
            if isinstance(resolved, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,200}", resolved):
                if resolved not in metadata["resolved_models"]:
                    metadata["resolved_models"].append(resolved)
            request_id = raw.get("_request_id")
            if isinstance(request_id, str) and REQUEST_ID.fullmatch(request_id):
                if request_id not in metadata["request_ids"]:
                    metadata["request_ids"].append(request_id)
            usage = raw.get("usage")
            if isinstance(usage, dict):
                for field in metadata["usage"]:
                    count = usage.get(field)
                    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                        metadata["usage"][field] = (metadata["usage"][field] or 0) + count
                        usage_counts[field] += 1
        for field, count in usage_counts.items():
            if count != metadata["calls"]:
                metadata["usage"][field] = None
        return answers, metadata

    if len(names) == 2 and cands:
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            futures = {name: pool.submit(score_provider, name) for name in names}
            observations = {name: futures[name].result() for name in names}
    else:
        observations = {name: score_provider(name) for name in names}
    result["providers"] = {name: observations[name][1] for name in names}
    for i, c in enumerate(cands):
        provider_scores, errors = {}, {}
        for name in names:
            answer = observations[name][0].get(f"skill_{i:03d}")
            error = validate_score(answer, len(LEVELS))
            if error:
                errors[name] = error
            else:
                provider_scores[name] = {"score": float(answer["score"]),
                                         "confidence": float(answer["confidence"]),
                                         "probabilities": {key: float(value) for key, value in answer["probabilities"].items()}}
        if errors:
            result["rejected"].append({**c, "error": "; ".join(f"{name}: {error}" for name, error in errors.items()),
                                       "provider_errors": errors, "provider_scores": provider_scores})
            continue
        scores = list(provider_scores.values())
        result["ranked"].append({**c,
            "score": math.fsum(answer["score"] for answer in scores) / len(scores),
            "confidence": min(answer["confidence"] for answer in scores),
            "confidence_kind": "minimum_provider_confidence" if provider == "both" else "provider_reported",
            "probabilities": {str(level): math.fsum(answer["probabilities"][str(level)] for answer in scores) / len(scores)
                              for level in range(len(LEVELS))},
            "provider_scores": provider_scores,
            "score_disagreement": abs(scores[0]["score"] - scores[-1]["score"])})
    result["ranked"].sort(key=lambda row: (-row["score"], -row["confidence"]))
    return result


def cmd_route(args) -> int:
    provider = args.provider or os.environ.get("SKILL_ROUTER_PROVIDER", "jev")
    if provider not in ("jev", "perplexity", "both"):
        raise ProviderError("SKILL_ROUTER_PROVIDER must be jev, perplexity, or both.")
    if not args.project.strip():
        raise ProviderError("The project description must not be empty.")
    # Read-only opening avoids creating a misleading empty index when it is missing.
    db = sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        cands = shortlist(db, args.project, args.top)
    finally:
        db.close()
    if not cands:
        print("No candidates — is the index built? (`router.py stats`)")
        return 1
    print(f"[route] {len(cands)} candidates from FTS5, sending to {provider}", flush=True)
    result = score_candidates(args.project, cands, provider, args.jev_model, args.perplexity_model)
    ranked, rejected = result["ranked"], result["rejected"]

    if provider == "both":
        print("[both] conf is minimum provider confidence, not consensus; delta is score disagreement.")
    print(f"\n{'score':>5} {'conf':>5}" + (f" {'delta':>5}" if provider == "both" else "") + "  skill")
    for r in ranked[:args.show]:
        delta = f" {r['score_disagreement']:5.2f}" if provider == "both" else ""
        print(f"{r['score']:5.2f} {r['confidence']:5.2f}{delta}  {r['name']}  [{r['tier']}] {r['repo']}")
    if rejected:
        print(f"\n{len(rejected)} answers dropped on contract breach "
              f"(first: {rejected[0]['name']}: {rejected[0]['error']})")
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        print(f"\nwritten: {args.out}")
    return 0 if ranked else 1


# ---------------------------------------------------------------- selftest

def cmd_selftest(args) -> int:
    assert parse_frontmatter("---\nname: pdf\ndescription: >\n  Read PDFs.\n  Also merge.\n---\n# x") \
        == {"name": "pdf", "description": "Read PDFs. Also merge."}, "frontmatter folding fails"
    assert parse_frontmatter("no frontmatter here") == {}
    assert parse_frontmatter('---\nname: a\ndescription: "Quoted desc."\n---\n')["description"] \
        == "Quoted desc."
    assert fingerprint("PDF", "Read PDFs.") == fingerprint("pdf", "read  pdfs"), "dedupe normalisation"
    assert fingerprint("pdf", "Read PDFs.") != fingerprint("pdf", "Write PDFs.")
    assert read_sources(Path(args.sources))[:1] == [("anthropics/skills", "vendor")], "tier parsing"

    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    db.execute("INSERT INTO skills(id,name,desc,tags,tier,repo) VALUES(1,'pdf','Read and merge PDF files','docs','vendor','x/y')")
    db.execute("INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(1,'pdf','Read and merge PDF files','docs')")
    hit = shortlist(db, "merge PDF files", 5)
    assert [h["name"] for h in hit] == ["pdf"], f"FTS prefilter fails: {hit}"

    good = {"type": "score", "score": 2.4, "confidence": 0.7,
            "probabilities": {"0": 0.0, "1": 0.1, "2": 0.4, "3": 0.5}}
    assert validate_score(good, 4) is None, "a valid answer was rejected"
    assert validate_score({**good, "probabilities": {"0": 0.5, "1": 0.5}}, 4)
    assert validate_score({**good, "score": 9}, 4)
    assert validate_score({**good, "probabilities": {"0": 0.0, "1": 0.2, "2": 0.2, "3": 0.2}}, 4)
    assert validate_score({"type": "noul", "noul": 0.9}, 4)
    print("selftest: all checks passed")
    return 0


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use a positive integer.") from None
    if number < 1:
        raise argparse.ArgumentTypeError("Use a positive integer.")
    return number


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("index"); a.add_argument("--db", default=DB); a.add_argument("--sources", default=SOURCES); a.add_argument("--workers", type=int, default=16); a.set_defaults(fn=cmd_index)
    b = sub.add_parser("stats"); b.add_argument("--db", default=DB); b.set_defaults(fn=cmd_stats)
    c = sub.add_parser("route")
    c.add_argument("project")
    c.add_argument("--db", default=DB)
    c.add_argument("--top", type=positive_int, default=40)
    c.add_argument("--show", type=positive_int, default=25)
    c.add_argument("--out")
    c.add_argument("--provider", choices=("jev", "perplexity", "both"),
                   help="Decision maker selection; overrides SKILL_ROUTER_PROVIDER (default: jev).")
    c.add_argument("--jev-model", help="Override JEV_MODEL (default: jev-latest).")
    c.add_argument("--perplexity-model", help="Override PERPLEXITY_DECISION_MODEL (default: pplx-decider-v1.1-27b).")
    c.set_defaults(fn=cmd_route)
    d = sub.add_parser("selftest"); d.add_argument("--sources", default=SOURCES); d.set_defaults(fn=cmd_selftest)
    args = p.parse_args()
    try:
        return args.fn(args)
    except ProviderError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except sqlite3.Error:
        print("error: Cannot read the skill index; run `router.py index` first.", file=sys.stderr)
        return 1
    except OSError:
        print("error: Cannot read or write the requested file.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
