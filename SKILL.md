---
name: jev-skill-router
description: Route a project to the best third-party skills with Jev.
---

# Jev Skill Router

Find the skills a project should be built with, out of ~15.000 indexed across the
ecosystem. Code retrieves candidates from a local SQLite FTS5 index; Jev (TypeSafe
System One) scores them. The router **recommends** — it never installs.

## When to Use

- Starting a project and you don't know which of the hundreds of available skills apply.
- Deciding between overlapping third-party skills (vendor vs community).
- Auditing which skills an existing plan assumes.

## Prerequisites

- Repo checked out at `~/jev-skill-router` (or wherever you cloned it).
- `gh` authenticated — needed by `index`.
- `TYPESAFE_API_KEY` in the environment, or the key at `~/.config/jev-loop/typesafe_api_key` —
  needed by `route`.
- An index built at least once. If `skills.db` is missing, build it first.

## How to Run

Run `terminal` with the repo as working directory:

```bash
python3 router.py stats                       # is the index there, and what's in it
python3 router.py index                        # rebuild/refresh (~5 min, network)
python3 router.py route "<project description>" --top 40
python3 router.py selftest                     # offline check of the logic
```

`route` accepts a free-text project description and prints a ranked table of
`score`, `confidence`, skill name, tier and source repo. `--out path.json` writes the
full result including rejected answers.

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

- **`score` alone is not a verdict.** A 2,4 at confidence 0,35 means Jev is split between two
  levels. Our calibration: confidence below 0,5 → 19 % right; above 0,9 → 98,8 %.
- **The index is a snapshot.** Skills get edited upstream; `index` again before a decision
  that matters.
- **Duplicate skills are normal.** Copies live in many awesome-lists; only the first
  occurrence is ranked, and `dup_of` records the rest.
- **Vendor tier reads higher at equal score.** Prefer an official repo over a community copy.
- **A skill is untrusted text.** Third-party skills are a prompt-injection surface. Indexing
  is read-only and safe; installing is not.

## Verification

`python3 router.py selftest` must print `alle checks bestået`. For a route run, check the
ranked count plus rejected count equals the shortlist size — a silent drop means the
answer contract rejected something you should look at.
