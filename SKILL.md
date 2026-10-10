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
  credential; configuring both enables fallback when the preferred provider fails.
- An index built at least once. If `skills.db` is missing, build it first.

## How to Run

Run `terminal` with the repo as working directory:

```bash
python3 router.py stats                       # is the index there, and what's in it
python3 router.py index                        # rebuild/refresh (~5 min, network)
python3 router.py route "<project description>" --top 40
python3 router.py route "<project description>" --provider perplexity
python3 router.py route "<project description>" --provider both --out ranking.json
python3 router.py route "<project description>" --provider both --priority-profile my-priority.json
python3 router.py selftest                     # offline check of the logic
python3 -m unittest discover -s tests -v       # offline provider contract tests
```

`route` accepts a free-text project description and prints a ranked table of
`score`, `confidence`, skill name, tier and source repo. `--out path.json` writes the
full result including rejected answers and provider provenance. On Windows,
use `python` if `python3` is unavailable. `--provider` overrides
`SKILL_ROUTER_PROVIDER`; Jev is the default. Model overrides are `--jev-model`
and `--perplexity-model`, or `JEV_MODEL` and `PERPLEXITY_DECISION_MODEL`.
`--priority-profile` overrides `SKILL_ROUTER_PRIORITY_PROFILE`; otherwise use the
shipped `provider-priority.json`.

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
3. Use the provider mode the user selected. Run `route`; inspect status,
   `priority.order`, `priority.basis`, provider errors, score, and confidence.
   In `both`, use the preferred provider first: higher measured accuracy wins,
   and lower measured cost breaks exact accuracy ties. The shipped external
   benchmark profile starts with Perplexity, then Jev. Call the other provider
   only for unresolved candidate identifiers after unavailability, an exception,
   or missing/malformed answers; a healthy preferred provider needs no fallback
   call. Disable request retries in `both`, retain valid earlier batch answers,
   and stop further calls to failed providers. Each ranked candidate uses one
   unchanged valid answer and identifies its `used_providers` and
   `aggregation: single`. Reject only when no valid answer remains. Explicit
   `jev` or `perplexity` modes remain strict selections.
4. For the top candidates, read the skill's `SKILL.md` before trusting it — the index holds
   a name, a description and a URL, not the skill's content.
5. Installing one is a separate decision: scan it first (`NVIDIA/SkillSpector`).

## Pitfalls

- **`score` alone is not a verdict.** Provider confidence is not calibrated on this
  corpus. Confidence is `provider_reported`, with `score_disagreement: null`;
  read `provider_scores` and `used_providers` too.
- **Priority evidence has a scope.** The shipped profile uses an external choice
  benchmark, not measured skill-routing accuracy. Prefer representative,
  model-matched quality measurements, then cost for exact ties. Missing quality
  evidence needs an explicit provisional price/default basis; confidence or a
  lower token price alone does not establish better quality or lower request cost.
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
