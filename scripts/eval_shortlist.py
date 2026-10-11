#!/usr/bin/env python3
"""Eval: does the shortlist find the skills we KNOW belong there?

Four projects with a hand-written facit list. Two are Marcin's own (OpenCorde,
Tilbud 2.0), two are controls where the answer is obvious (Minecraft server, the
router itself). Run after any change to the shortlist rule:

  python3 scripts/eval_shortlist.py             # hits@40 per rule
  python3 scripts/eval_shortlist.py --show      # and what came in instead

Ceiling: the facit lists are mine, not measured against an independent judge.
They catch "the right skill vanished", not "the order is sensible" — recall is
the cheap half; the ordering is Jev's job.
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
        flag = "" if len(hits) == len(want) else "   <-- missing: " + ", ".join(
            w for w in want if w not in got)
        print(f"  {name:10} {len(hits)}/{len(want)}  {hits}{flag}")
        if show and flag:
            print("             instead: " + ", ".join(got[:8]))
    print(f"  {'TOTAL':10} {total_hit}/{total_want}  ({total_hit / total_want:.0%})")
    return total_hit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(router.DB))
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--show", action="store_true")
    p.add_argument("--rule", choices=router.RULES, default="plain", help="active rule gated by --require")
    p.add_argument("--out", help="write measured comparison JSON")
    p.add_argument("--require", type=int, default=None,
                   help="exit non-zero unless the active rule reaches this many hits")
    args = p.parse_args()
    import json
    db = router.open_index(args.db)
    if args.require is not None and not 0 <= args.require <= sum(len(w) for _, _, w in CASES):
        p.error("--require must be within the facit size")
    results = {}
    for rule in router.RULES:
        print(f"\nrule: {rule}")
        results[rule] = run(db, rule, args.top, args.show)
    best = max(results, key=lambda k: results[k])
    print(f"\ncomparison winner: {best} ({results[best]} hits); active rule: {args.rule} ({results[args.rule]} hits)")
    if args.out:
        total = sum(len(want) for _, _, want in CASES)
        payload = {"top": args.top, "active_rule": args.rule, "corpus": router.corpus_meta(db),
                   "rules": {rule: {"hit": n, "want": total} for rule, n in results.items()},
                   "cases": [{"name": name, "project": project, "want": want} for name, project, want in CASES]}
        Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    db.close()
    if args.require is not None and results[args.rule] < args.require:
        print(f"FAIL: need {args.require} hits, active {args.rule} reached {results[args.rule]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
