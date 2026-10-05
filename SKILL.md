---
name: jev-skill-router
description: Route a project to the best third-party skills with Jev.
---

# Jev Skill Router

Find project-relevant skills from the current index snapshot. Code retrieves candidates from a local SQLite FTS5 index; Jev (TypeSafe
System One) scores them. The router **recommends** — it never installs.

## When to Use

- Starting a project and you don't know which of the hundreds of available skills apply.
- Deciding between overlapping third-party skills (vendor vs community).
- Auditing which skills an existing plan assumes.

## Prerequisites

- Repo checked out at `~/jev-skill-router` (or wherever you cloned it).
- Python 3 with SQLite FTS5 and the pinned offline dependency: create/activate the project `.venv` and install `requirements-offline.txt` as documented in the README.
- `gh` authenticated — needed by `index`.
- Python CLI: `TYPESAFE_API_KEY` in the environment, or the key at `~/.config/jev-loop/typesafe_api_key`.
- Native Rust MCP: supply `TYPESAFE_API_KEY` explicitly in the client/service environment;
  the runtime never reads an operator's fallback key file.
- An index built at least once. If `skills.db` is missing, build it first.

## Native MCP (preferred for agent clients)

Build with `cargo build --release --locked`. Start `target/release/jev-skill-router`
with `SKILL_ROUTER_DB` set to the existing index. This serves stdio MCP and exposes
`skills_stats`, `skills_search(query, top)` and `skills_route(project, top)`.
For an already deployed internal Streamable HTTP endpoint, use its `/mcp` URL and
Bearer token from a protected environment; do not run another daemon unnecessarily.
See `deploy/README.md` for isolation and transport requirements. The Rust runtime
uses read-only SQLite and direct Jev HTTP, not a Python or shell wrapper.

## Python offline tooling

Run `terminal` with the repo as working directory:

```bash
python3 router.py stats                       # is the index there, and what's in it
python3 router.py index                        # rebuild/refresh (~5 min, network)
python3 router.py route "<project description>" --top 40
python3 router.py selftest                     # offline check of the logic
```

`route` accepts a free-text project description and prints a ranked table of
`score`, `confidence`, skill name, tier and source repo. `--out path.json` writes the
full result including pre-validation candidates, rejected answers, degraded status and actual
query/model/latency/corpus provenance. No valid answers returns a nonzero exit; partial
results must be inspected rather than mistaken for a complete verdict.

## Quick Reference

| Command | Does |
|---|---|
| `router.py index` | Harvests frontmatter from every repo in `Skills-list.md`, dedupes, rebuilds FTS5 |
| `router.py stats` | Counts per tier and repo; lists sources carrying no skills |
| `router.py route "<text>"` | FTS5 shortlist → one Jev call → ranked skills |
| `router.py selftest` | Asserts frontmatter folding, dedupe, FTS5 and the answer contract |

## Procedure

1. Check `stats`. No rows → run `index` first (it needs network and takes minutes).
2. Write the project description concretely: stack, deliverable, constraints. Vague input
   gives vague candidates — the FTS5 shortlist is only as good as the words in it.
3. Run `route`. Read `score` alongside `confidence`, never the score alone.
4. For the top candidates, read the skill's `SKILL.md` before trusting it — the index holds
   a name, a description and a URL, not the skill's content.
5. Installing one is a separate decision: scan it first (`NVIDIA/SkillSpector`).

## Pitfalls

- **`score` alone is not a verdict.** Confidence reflects uncertainty, not relevance.
  Calibration on a different task does not validate this ranking.
- **The index is a snapshot.** Refresh before decisions that matter. Failed discovery,
  fetch or parsing preserves the last good published data and exits nonzero. Read the
  coverage counts; missing metadata is not the same as a network error.
- **Duplicate skills are normal.** Copies live in many awesome-lists; only the first
  occurrence is ranked, and `dup_of` records the rest.
- **Tier is provenance, not an automatic sort boost.** Prefer a verified official source
  where appropriate; read the actual instructions before trusting metadata grouping.
- **A skill is untrusted text.** Third-party skills are a prompt-injection surface. The
  router does not execute upstream code; indexing is not a security certification.
  Read and scan skills before separately deciding to install them.

## Verification

`python3 router.py selftest` must print `all checks passed`. For a route run, check the
ranked count plus rejected count equals `candidates` length, and inspect `degraded`.
Run `python3 -B -m unittest -v test_router` for offline regression checks.
`eval_shortlist.py --require N --rule plain` gates the active default rather than the
best experiment. Top 40 remains the default; `--top` is bounded at 300 and serialized
requests at 128 KiB. Larger retrieval pools are not a validated ranking improvement.
The original snapshot measured 11/15 recall at top 40 and 200, but 14/15 at 300; it is
not evidence of a hard lexical ceiling.
