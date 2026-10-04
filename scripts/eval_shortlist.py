#!/usr/bin/env python3
"""Eval: finder shortlisten de skills vi VED er rigtige?

Fire projekter med en facit-liste. To af dem er Marcis egne (OpenCorde, Tilbud),
to er kontroller hvor svaret er indlysende (Minecraft, routeren selv).
Kør efter enhver ændring af shortlist-reglen:

  python3 scripts/eval_shortlist.py            # hit@40 pr. regel
  python3 scripts/eval_shortlist.py --show     # og hvad der kom med i stedet

Ceiling: facit-listerne er mine, ikke målt mod en uafhængig dommer. De fanger
"forsvandt den helt", ikke "er rækkefølgen god" — rækkefølgen dømmer Jev.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import router  # noqa: E402

CASES = [
    ("minecraft",
     "Set up a modded Minecraft server for friends: Java server, Forge or NeoForge "
     "modpack with about fifty mods, hosted on a Linux machine with backups and a whitelist.",
     ["minecraft-modpack-server", "minecraft-server-admin", "minecraft-modding"]),
    ("opencorde",
     "Build Discord parity for an open-source self-hosted Discord alternative. Rust Axum "
     "backend API with SQLx and Postgres, SvelteKit frontend, LiveKit WebRTC voice and video, "
     "stage channels, roles and permissions, OAuth2 and OIDC developer platform with bot "
     "tokens and slash commands, and Playwright QA harnesses that produce screenshot evidence.",
     ["sveltekit", "rust-sqlx-postgres-service", "qa/e2e-playwright", "identity-federation"]),
    ("tilbud",
     "Extend Danish grocery offer-catalog coverage: scrape weekly offer catalogs from retail "
     "chains, ingest raw offer lines into a Rust API, and use an LLM to classify each line "
     "into a product type from a closed vocabulary. Postgres, scheduled systemd timers, "
     "deployed on a Linux server.",
     ["llm-evaluation", "rust-sqlx-postgres-service", "systemd-services", "web-scraping"]),
    ("router",
     "Build a Rust MCP service that exposes a SQLite FTS5 index over seventeen thousand "
     "third-party agent skills, ranked with TypeSafe Jev. Deploy it in Docker behind Caddy "
     "and call it from an agent.",
     ["rust-mcp-server-generator", "sqlite-storage", "rust-deployable-service", "fastmcp"]),
]


def run(db, rule, top=40, show=False):
    total_hit, total_want = 0, 0
    for name, project, want in CASES:
        cands = router.shortlist(db, project, top, rule=rule)
        got = [c["name"] for c in cands]
        hits = [w for w in want if w in got]
        total_hit += len(hits)
        total_want += len(want)
        flag = "" if len(hits) == len(want) else "   <-- mangler: " + ", ".join(
            w for w in want if w not in got)
        print(f"  {name:10} {len(hits)}/{len(want)}  {hits}{flag}")
        if show and flag:
            print("             i stedet: " + ", ".join(got[:8]))
    print(f"  {'I ALT':10} {total_hit}/{total_want}  ({total_hit / total_want:.0%})")
    return total_hit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(router.DB))
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--show", action="store_true")
    args = p.parse_args()
    import sqlite3
    db = sqlite3.connect(args.db)
    results = {}
    for rule in ("plain", "bm25", "idf"):
        print(f"\nregel: {rule}")
        results[rule] = run(db, rule, args.top, args.show)
    best = max(results, key=results.get)
    print(f"\nvinder: {best} ({results[best]} hits) — sæt den som default i shortlist()")
    return 0 if results.get("idf", 0) >= results.get("bm25", 0) else 1


if __name__ == "__main__":
    sys.exit(main())
