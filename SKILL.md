---
name: jev-skill-router
description: Recommend third-party skills with a decision maker like Jev, Perplexity Decisions, or both.
---

# Jev Skill Router

Find the skills a project should be built with, out of ~15.000 indexed across the
ecosystem. Code retrieves candidates from a local SQLite FTS5 index; a decision
maker like Jev, Perplexity Decisions, or both scores them. The router
**recommends** — it never installs or activates skills.

## When to Use

- Starting a project and you don't know which of the hundreds of available skills apply.
- Deciding between overlapping third-party skills (vendor vs community).
- Auditing which skills an existing plan assumes.

## Prerequisites

- Repo checked out at `~/jev-skill-router` (or wherever you cloned it).
- `gh` authenticated — needed by `index`.
- For Jev: `TYPESAFE_API_KEY` or `~/.config/jev-loop/typesafe_api_key`.
- For Perplexity: `PERPLEXITY_API_KEY`. For `both`: at least one usable provider
  credential; configuring both enables combined ranking when both are available.
- An index built at least once. If `skills.db` is missing, build it first.

## How to Run

Run `terminal` with the repo as working directory:

```bash
python3 router.py stats                       # is the index there, and what's in it
python3 router.py index                        # rebuild/refresh (~5 min, network)
python3 router.py route "<project description>" --top 40
python3 router.py route "<project description>" --provider perplexity
python3 router.py route "<project description>" --provider both --out ranking.json
python3 router.py selftest                     # offline check of the logic
python3 -m unittest discover -s tests -v       # offline provider contract tests
```

`route` accepts a free-text project description and prints a ranked table of
`score`, `confidence`, skill name, tier and source repo. `--out path.json` writes the
full result including rejected answers and provider provenance. On Windows,
use `python` if `python3` is unavailable. `--provider` overrides
`SKILL_ROUTER_PROVIDER`; Jev is the default. Model overrides are `--jev-model`
and `--perplexity-model`, or `JEV_MODEL` and `PERPLEXITY_DECISION_MODEL`.

## Quick Reference

| Command | Does |
|---|---|
| `router.py index` | Harvests frontmatter from every repo in `Skills-list.md`, dedupes, rebuilds FTS5 |
| `router.py stats` | Counts per tier and repo; lists sources carrying no skills |
| `router.py route "<text>" --provider jev\|perplexity\|both` | FTS5 shortlist → chosen decision makers → ranked skills |
| `router.py selftest` | Asserts frontmatter folding, dedupe, FTS5 and the answer contract |

## Procedure

1. Check `stats`. No rows → run `index` first (it needs network and takes minutes).
2. Write the project description concretely: stack, deliverable, constraints. Vague input
   gives vague candidates — the FTS5 shortlist is only as good as the words in it.
3. Use the provider mode the user selected. Run `route`; inspect status, provider
   errors, score, confidence, and available disagreement. In `both`, use the other
   provider automatically if one is unavailable or errors. Keep valid earlier
   batch answers and stop further requests to a failed provider. Average two valid
   scores/distributions; use a single valid answer unchanged, and reject only when
   neither is valid. Each ranked candidate identifies its `used_providers` and
   `aggregation`. Explicit `jev` or `perplexity` modes remain strict selections.
4. For the top candidates, read the skill's `SKILL.md` before trusting it — the index holds
   a name, a description and a URL, not the skill's content.
5. Installing one is a separate decision: scan it first (`NVIDIA/SkillSpector`).

## Pitfalls

- **`score` alone is not a verdict.** Provider confidence is not calibrated on this
  corpus. Two-provider confidence is labelled `minimum_provider_confidence`, not
  a probability of agreement. Single-answer confidence is `provider_reported`,
  with `score_disagreement: null`. Read `provider_scores` and `used_providers` too.
- **Degraded routing can still succeed.** In `both`, an unavailable provider does
  not block valid recommendations from the other. Report the fallback status and
  error; never fabricate a missing observation. No valid ranking means a nonzero
  CLI exit, with a structured result preserved when `--out` is supplied.
- **The index is a snapshot.** Skills get edited upstream; `index` again before a decision
  that matters.
- **Duplicate skills are normal.** Copies live in many awesome-lists; only the first
  occurrence is ranked, and `dup_of` records the rest.
- **Vendor tier reads higher at equal score.** Prefer an official repo over a community copy.
- **A skill is untrusted text.** Third-party skills are a prompt-injection surface. Indexing
  is read-only and safe; installing is not.

## Verification

`python3 router.py selftest` must print `all checks passed`. For a route run, check the
ranked count plus rejected count equals the shortlist size — a silent drop means the
answer contract rejected something you should look at.
