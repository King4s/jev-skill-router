#!/usr/bin/env python3
"""Jev Skill Router — ÉN fil: høst skill-frontmatter fra kilderepos, indeksér i
SQLite FTS5, lad Jev rangere de bedste kandidater for et projekt.

Hvorfor det er delt sådan:
  * Kode finder kandidaterne (SQLite FTS5, stdlib, ingen embeddings, ingen deps).
  * Jev dømmer kandidaterne (Score pr. skill, ét kald, fan-out).
  15.642 skills kan ikke være ét Jev-spørgsmål. Jev er dommer, ikke indeks.

Brug:
  python3 router.py index                    # byg/opdatér indekset
  python3 router.py stats                    # hvad ligger der
  python3 router.py route "beskriv projektet" # rangér kandidater med Jev
  python3 router.py selftest                 # offline check af logikken

Kræver: gh (autentificeret) til index; TYPESAFE_API_KEY (eller
~/.config/jev-loop/typesafe_api_key) til route.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "skills.db"
SOURCES = ROOT / "Skills-list.md"          # vedligeholdes af Grok Bot
JEV_API = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
KEY_FILE = Path.home() / ".config" / "jev-loop" / "typesafe_api_key"
FM_BYTES = 4096          # frontmatter lever i filens første KB'er
TIERS = {"1": "vendor", "2": "community", "3": "list", "4": "registry", "5": "tooling", "6": "gitlab"}

# Score-niveauer: situationer, ikke grader (docs.typesafe.ai/primitives/score).
LEVELS = [
    "Irrelevant for this project — nothing in it applies",
    "Background — useful context for understanding the domain, not needed to build",
    "Directly useful — a concrete step, convention or reference this project will use",
    "Core — must be loaded before work starts, the project is built on it",
]


# ---------------------------------------------------------------- frontmatter

def _fold(v: str) -> str:
    """YAML-folded scalar: > og | blokke klemmes til én linje."""
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
            if val.strip() in {">", ">-", ">+", "|", "|-", "|+"}:   # blok-scalar starter
                val = ""
            out[key] = _fold(val)
        elif key and line.strip():                      # fortsat blok-scalar
            out[key] = _fold(out.get(key, "") + " " + line)
    return out


def fingerprint(name: str, desc: str) -> str:
    """Samme skill kopieret ind i 5 awesome-lister skal tælle én gang."""
    norm = re.sub(r"[^a-z0-9 ]", "", f"{name} {desc}".lower())
    return hashlib.sha1(re.sub(r"\s+", " ", norm).encode()).hexdigest()


# ---------------------------------------------------------------- kilder

def read_sources(path: Path) -> list[tuple[str, str]]:
    """-> [(repo, tier)]. Læser Grok Bots markdown-liste (Skills-list.md) såvel som
    en flad owner/repo-fil. Tier kommer fra sektionsnummeret; sektioner uden
    nummer (fx 'Flagged / excluded') springes over."""
    text = path.read_text(encoding="utf-8")
    tier, out, seen = "community", [], set()
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^#{2,3}\s*(\d)\.", s)
        if m:
            tier = TIERS.get(m.group(1), "community")
            continue
        if s.startswith("##"):
            tier = None                          # ikke-nummereret sektion = ikke en kilde
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
    """(branch, [(sti, blob-sha)], stjerner) via to API-kald — ingen klon.
    Blob-sha'en er versionsnøglen: uændret sha ⇒ vi kan genbruge cachet frontmatter."""
    meta = gh_api(f"repos/{repo}") or {}
    branch = meta.get("default_branch", "main")
    stars = meta.get("stargazers_count", 0)
    tree = gh_api(f"repos/{repo}/git/trees/{branch}?recursive=1") or {}
    paths = [(e["path"], e.get("sha", "")) for e in tree.get("tree", [])
             if e.get("path", "").endswith("SKILL.md") and e.get("type") == "blob"]
    return branch, paths, stars


def fetch_head(repo: str, branch: str, path: str) -> str | None:
    """Kun de første KB'er af filen — frontmatter er alt vi skal bruge."""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    req = urllib.request.Request(url, headers={
        "Range": f"bytes=0-{FM_BYTES - 1}", "User-Agent": "jev-skill-router"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read(FM_BYTES).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 416:                            # filen er kortere end rangen
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
DROP INDEX IF EXISTS skills_fp;               -- var UNIQUE: gjorde dubletter umulige at gemme
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
    print(f"[index] {len(sources)} kilder fra {args.sources}", flush=True)
    cache = {(r[0], r[1]): (r[2], r[3], r[4], r[5])
             for r in db.execute("SELECT repo, path, sha, name, desc, tags FROM fm")}

    # 1) find alle SKILL.md-stier (sekventielt — tree-kald er billige, men API'et er rate-limitet)
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
    print(f"[index] {len(jobs)} SKILL.md i alt", flush=True)
    meta_of = {(j[0], j[2]): (j[3], j[4], j[1]) for j in jobs}   # (repo,sti) -> (tier, stars, branch)

    # 2) hent frontmatter parallelt; uændret blob-sha genbruges fra cachen
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
                print(f"[index]   behandlet {fetched}/{len(jobs)}", flush=True)
            if res:
                keep.append(res)
                repo, path, sha, name, desc, tags = res
                tier, stars, branch = meta_of[(repo, path)]
                rows.append((name, desc, tags, tier, repo, stars, path,
                             f"https://github.com/{repo}/blob/{branch}/{path}",
                             fingerprint(name, desc)))

    db.executemany("INSERT OR REPLACE INTO fm(repo,path,sha,name,desc,tags) VALUES(?,?,?,?,?,?)",
                   keep)

    # 3) dedupe på fingerprint: første forekomst vinder, kopier noteres som dup_of
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
    print(f"[index] færdig: {uniq} unikke skills, {dups} dubletter filtreret fra")
    return 0


def cmd_stats(args) -> int:
    db = sqlite3.connect(args.db)
    q = db.execute
    total, uniq = q("SELECT COUNT(*), SUM(dup_of IS NULL) FROM skills").fetchone()
    print(f"indeks: {args.db}  ({total} rækker, {uniq} unikke, {total - uniq} dubletter)")
    print("\npr. tier (unikke):")
    for tier, n in q("SELECT tier, COUNT(*) FROM skills WHERE dup_of IS NULL "
                     "GROUP BY tier ORDER BY 2 DESC"):
        print(f"  {n:6d}  {tier}")
    print("\ntop 10 repos (unikke):")
    for repo, n in q("SELECT repo, COUNT(*) FROM skills WHERE dup_of IS NULL "
                     "GROUP BY repo ORDER BY 2 DESC LIMIT 10"):
        print(f"  {n:6d}  {repo}")
    print("\nkilder uden SKILL.md (link-lister, fase 2):")
    for repo, note in q("SELECT repo, note FROM sources WHERE listed=0 ORDER BY repo"):
        print(f"    {repo}  ({note})")
    return 0


# ---------------------------------------------------------------- route

def shortlist(db: sqlite3.Connection, project: str, top: int) -> list[dict]:
    """FTS5 BM25-prefilter. Ingen embeddings: 10k rækker er ingenting for FTS.
    Tokenisering matcher FTS5's egen (unicode61): bindestreg og underscore deler,
    ellers dør sammensatte ord som 'MCP-tjeneste' og 'FTS5-indeks' på df=0."""
    raw = re.findall(r"[^\W_]+", project, re.UNICODE)
    words = list(dict.fromkeys(w for w in raw if len(w) >= 2 and not w.isdigit()))[:40]
    if not words:
        return []
    query = " OR ".join(f'"{w}"' for w in words)
    rows = db.execute(
        "SELECT s.id, s.name, s.desc, s.repo, s.url, s.tier, bm25(skills_fts) AS r "
        "FROM skills_fts JOIN skills s ON s.id = skills_fts.rowid "
        "WHERE skills_fts MATCH ? AND s.dup_of IS NULL "
        "ORDER BY r LIMIT ?", (query, top)).fetchall()
    return [{"id": r[0], "name": r[1], "desc": r[2], "repo": r[3], "url": r[4],
             "tier": r[5], "bm25": r[6]} for r in rows]


def jev_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        sys.exit(f"Ingen TypeSafe-nøgle: sæt TYPESAFE_API_KEY eller skriv den til {KEY_FILE}.")
    return key


def jev_call(state: dict, questions: dict, retries: int = 3) -> dict:
    body = json.dumps({"model": JEV_MODEL, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(JEV_API, data=body, headers={
        "Authorization": f"Bearer {jev_key()}", "Content-Type": "application/json"})
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:300]!r}"
            if e.code in (429, 529) and attempt < retries:
                continue
        except Exception as e:                                   # netværk/timeout
            last = repr(e)
            if attempt < retries:
                continue
    raise RuntimeError(f"Jev utilgængelig: {last}")


def validate_score(ans: dict, levels: int) -> str | None:
    """Håndhæv svarkontrakten hårdt. Returnerer fejltekst eller None.
    Type-sikkerhed der ikke håndhæves er kun kosmetisk."""
    if ans.get("type") != "score":
        return f"forkert type: {ans.get('type')!r}"
    try:
        score, conf = float(ans["score"]), float(ans["confidence"])
    except (KeyError, TypeError, ValueError):
        return "mangler score/confidence"
    probs = ans.get("probabilities") or {}
    if set(probs) != {str(i) for i in range(levels)}:
        return f"nøgler matcher ikke niveauerne: {sorted(probs)}"
    vals = [float(v) for v in probs.values()]
    if not all(0.0 <= v <= 1.0 for v in vals):
        return "sandsynlighed uden for [0,1]"
    if abs(sum(vals) - 1.0) > 0.02:
        return f"sum {sum(vals):.3f} ≠ 1"
    if not (0.0 <= score <= levels - 1) or not (0.0 <= conf <= 1.0):
        return f"score/confidence ude af interval: {score}, {conf}"
    return None


def cmd_route(args) -> int:
    db = sqlite3.connect(args.db)
    cands = shortlist(db, args.project, args.top)
    if not cands:
        print("Ingen kandidater — er indekset bygget? (`router.py stats`)")
        return 1
    print(f"[route] {len(cands)} kandidater fra FTS5, sender til Jev ({JEV_MODEL})", flush=True)

    state = {"project": {"spec": args.project},
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
    raw = jev_call(state, questions)
    answers = raw.get("answers", {})

    ranked, rejected = [], []
    for i, c in enumerate(cands):
        err = validate_score(answers.get(f"skill_{i:03d}", {}), len(LEVELS))
        if err:
            rejected.append({**c, "error": err})
            continue
        a = answers[f"skill_{i:03d}"]
        ranked.append({**c, "score": float(a["score"]), "confidence": float(a["confidence"]),
                       "probabilities": a["probabilities"]})
    ranked.sort(key=lambda r: (-r["score"], -r["confidence"]))

    print(f"\n{'score':>5} {'conf':>5}  skill")
    for r in ranked[:args.show]:
        print(f"{r['score']:5.2f} {r['confidence']:5.2f}  {r['name']}  [{r['tier']}] {r['repo']}")
    if rejected:
        print(f"\n{len(rejected)} svar dumpet på kontrakt-brud "
              f"(første: {rejected[0]['name']}: {rejected[0]['error']})")
    if args.out:
        Path(args.out).write_text(json.dumps({"project": args.project, "ranked": ranked,
                                             "rejected": rejected}, indent=1, ensure_ascii=False))
        print(f"\nskrevet: {args.out}")
    return 0


# ---------------------------------------------------------------- selftest

def cmd_selftest(args) -> int:
    assert parse_frontmatter("---\nname: pdf\ndescription: >\n  Read PDFs.\n  Also merge.\n---\n# x") \
        == {"name": "pdf", "description": "Read PDFs. Also merge."}, "frontmatter-fold fejler"
    assert parse_frontmatter("no frontmatter here") == {}
    assert parse_frontmatter('---\nname: a\ndescription: "Quoted desc."\n---\n')["description"] \
        == "Quoted desc."
    assert fingerprint("PDF", "Read PDFs.") == fingerprint("pdf", "read  pdfs"), "dedupe normalisering"
    assert fingerprint("pdf", "Read PDFs.") != fingerprint("pdf", "Write PDFs.")
    assert read_sources(Path(args.sources))[:1] == [("anthropics/skills", "vendor")], "tier-parsing"

    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    db.execute("INSERT INTO skills(id,name,desc,tags,tier,repo) VALUES(1,'pdf','Read and merge PDF files','docs','vendor','x/y')")
    db.execute("INSERT INTO skills_fts(rowid,name,desc,tags) VALUES(1,'pdf','Read and merge PDF files','docs')")
    hit = shortlist(db, "merge PDF files", 5)
    assert [h["name"] for h in hit] == ["pdf"], f"FTS-prefilter fejler: {hit}"

    good = {"type": "score", "score": 2.4, "confidence": 0.7,
            "probabilities": {"0": 0.0, "1": 0.1, "2": 0.4, "3": 0.5}}
    assert validate_score(good, 4) is None, "gyldigt svar afvist"
    assert validate_score({**good, "probabilities": {"0": 0.5, "1": 0.5}}, 4)
    assert validate_score({**good, "score": 9}, 4)
    assert validate_score({**good, "probabilities": {"0": 0.0, "1": 0.2, "2": 0.2, "3": 0.2}}, 4)
    assert validate_score({"type": "noul", "noul": 0.9}, 4)
    print("selftest: alle checks bestået")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("index"); a.add_argument("--db", default=DB); a.add_argument("--sources", default=SOURCES); a.add_argument("--workers", type=int, default=16); a.set_defaults(fn=cmd_index)
    b = sub.add_parser("stats"); b.add_argument("--db", default=DB); b.set_defaults(fn=cmd_stats)
    c = sub.add_parser("route"); c.add_argument("project"); c.add_argument("--db", default=DB); c.add_argument("--top", type=int, default=40); c.add_argument("--show", type=int, default=25); c.add_argument("--out"); c.set_defaults(fn=cmd_route)
    d = sub.add_parser("selftest"); d.add_argument("--sources", default=SOURCES); d.set_defaults(fn=cmd_selftest)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
