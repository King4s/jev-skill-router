---
name: jev-skill-router
description: Recommend third-party skills with a configured typed decision provider; Python also supports ordered failover.
---

# Jev Skill Router

Find project-relevant skills from the current index snapshot. Code retrieves
candidates from local SQLite FTS5. Native Rust MCP selects one configured typed
decision provider at startup (shipped profiles: Jev and Perplexity Decisions);
optional Python offline tooling selects Jev, Perplexity Decisions, or both.
The router **recommends** and marks which recommendations are already installed on this
machine — it never installs or activates skills.

## When to Use

- Starting a project and you don't know which of the hundreds of available skills apply.
- Deciding between overlapping third-party skills (vendor vs community).
- Auditing which skills an existing plan assumes.

## Prerequisites

- Repo checked out at `~/jev-skill-router` (or wherever you cloned it).
- Python 3 with SQLite FTS5 and the pinned offline dependency: create/activate the project `.venv` and install `requirements-offline.txt` as documented in the README.
- `gh` authenticated — needed by `index`.
- Python CLI: `TYPESAFE_API_KEY` in the environment, or the key at `~/.config/jev-loop/typesafe_api_key`.
- Native Rust MCP: supply the selected profile's `key_env` variable in the protected
  client/service environment (`TYPESAFE_API_KEY` for Jev, `PERPLEXITY_API_KEY` for
  Perplexity). The runtime never reads an operator's fallback key file. Stats,
  search and empty routes need no key; nonempty ranking needs the selected key/model.
- Python CLI Perplexity: `PERPLEXITY_API_KEY`. For `both`: at least one usable
  provider credential; configuring both enables fallback when the preferred provider fails.
- An index built at least once. If `skills.db` is missing, build it first.

## Native MCP (preferred for agent clients)

Build with `cargo build --release --locked`. The native server and `jev-skill-refresh` are
Unix-only — `src/main.rs` uses `tokio::signal::unix` and the refresh utility hard-codes a
Linux service layout, so the build fails on Windows; use the Python CLI there.
Start `target/release/jev-skill-router`
with `SKILL_ROUTER_DB` set to the existing index. This serves stdio MCP and exposes
`skills_stats`, `skills_search(query, top)` and `skills_route(project, top)`.
For an already deployed internal Streamable HTTP endpoint, use its `/mcp` URL and
Bearer token from a protected environment; do not run another daemon unnecessarily.
See `deploy/README.md` for isolation and transport requirements. The Rust runtime
uses read-only SQLite and direct typed Decisions HTTP, not a Python or shell wrapper.

Set `SKILL_ROUTER_PROVIDERS_FILE` to the approved non-secret profile file; otherwise
the process reads cwd `decision-providers.json`. The shipped file defaults to `jev`;
`SKILL_ROUTER_PROVIDER` selects another configured profile at **startup**, not per
tool request. Restart after profile edits, reselection or environment changes.
DB-only snapshot replacement does not require a restart.

Profiles require `endpoint`, `model`, `key_env`, with optional `endpoint_env` and
`model_env` override names. Model IDs come from that file or opted-in environment
variables, not Rust defaults. Only the selected profile's key variable is read.
Shipped Jev opts into `JEV_API`/`JEV_MODEL`; shipped Perplexity ignores them and has
no implicit model override. Additional compatible typed Decisions profiles need
no code changes; chat APIs are not adapters. Native has no fallback, fanout or
`both` policy. Without the implicit cwd file, legacy Jev uses `TYPESAFE_API_KEY`,
optional `JEV_API`, and a **required explicit `JEV_MODEL`** for nonempty ranking.
Missing explicit files, invalid profiles and fileless non-Jev selection fail closed.

Native `top` is 1–300 (default 40). Ranking uses at most 128 questions per batch,
preflights every serialized batch against 128 KiB before any provider call, and
shares the strict 0.04 weighted-score validator across providers (probability-sum
tolerance 0.02). Responses are bounded to 2 MiB; each provider request has at most
four attempts. Routing has four shared non-queueing permits. Endpoints allow HTTPS
or loopback HTTP only, with no redirects and refusal of Retry-After delays over
30 seconds. Unknown answer IDs
reject the affected batch. Existing `ranked`, `rejected`, `degraded`, `candidates`
and corpus fields remain; inspect `meta.provider`, `meta.requested_model` and
`meta.response_models`. `meta.model` is null when batch models are absent or differ.

Native configurable providers were merged in PR #5. Publication is separate from
installation; dated 2026-10-11 Jev receipts do not prove a later deployment or live
Perplexity success. Preserve any configured `SKILL_ROUTER_EXCLUSIONS` policy during
upgrades: exact repo/path exclusions apply before top truncation to both search
and routing, reload per request, and follow duplicate pointers to canonical IDs.
Missing or invalid configured policy refuses search and routing; init/stats remain
available. No policy is configured by default, and indexing is not a safety guarantee.

## Python offline tooling

Run `terminal` with the repo as working directory:

```bash
python3 router.py stats                       # is the index there, and what's in it
python3 router.py index                        # rebuild/refresh (~5 min, network)
python3 router.py index --max-parse-failures 50 # publish despite broken upstream YAML
python3 router.py route "<project description>" --top 40
python3 router.py route "<project description>" --provider perplexity
python3 router.py route "<project description>" --provider both --out ranking.json
python3 router.py route "<project description>" --provider both --priority-profile my-priority.json
python3 router.py selftest                     # offline check of the logic
python3 -m unittest discover -s tests -v       # offline provider contract tests
```

`route` accepts a free-text project description and prints a ranked table of
`score`, `confidence`, skill name, tier and source repo. `--out path.json` writes the
full result including pre-validation candidates, rejected answers, degraded status and actual
query/model/latency/corpus provenance. No valid answers returns a nonzero exit; partial
results must be inspected rather than mistaken for a complete verdict.
On Windows, use `python` if `python3` is unavailable. `--provider` overrides
`SKILL_ROUTER_PROVIDER`; Jev is the Python default. Model overrides are `--jev-model`
and `--perplexity-model`, or `JEV_MODEL` and `PERPLEXITY_DECISION_MODEL`.
`--priority-profile` overrides `SKILL_ROUTER_PRIORITY_PROFILE`; otherwise use the
shipped `provider-priority.json`. CLI flags, priority/failover and report policy are
Python-only; native also recognizes `SKILL_ROUTER_PROVIDER` and the shipped Jev
profile opts into `JEV_MODEL`, but selection happens at startup.

## Quick Reference

| Command | Does |
|---|---|
| `router.py index` | Harvests frontmatter from every repo in `Skills-list.md`, dedupes, rebuilds FTS5 |
| `router.py stats` | Counts per tier and repo; lists sources carrying no skills |
| `router.py route "<text>" --provider jev\|perplexity\|both` | FTS5 shortlist → chosen decision makers → ranked skills |
| `router.py selftest` | Asserts frontmatter folding, dedupe, FTS5, install detection and the answer contract |

The Python `route` command marks every ranked skill `[installed]` or `[not installed]`
from the local skill trees: `SKILL_ROUTER_INSTALL_ROOTS` or `--installed-root DIR`
(repeatable) when set, otherwise `~/.agents/skills`, `~/.hermes/skills`, the Hermes
profile `skills/` trees, `~/.claude/skills` and `~/.codex/skills`. Detection reads
directory names and `SKILL.md` presence only; it never opens the skill body. A missing
or unreadable tree is ignored, not an error. `--no-install-check` skips the check.

## Procedure

1. Check `stats`. No rows → run `index` first (it needs network and takes minutes).
2. Write the project description concretely: stack, deliverable, constraints. Vague input
   gives vague candidates — the FTS5 shortlist is only as good as the words in it.
3. For native MCP, use the operator-selected startup profile; inspect `degraded`,
   rejections and `meta` provider/model provenance. The remainder of this step is
   **Python-only**. Use the provider mode the user selected. Run `route`; inspect status,
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
5. Check whether each recommendation is installed here. A recommended skill that is
   **not installed** is not an unavailable skill: ask the user whether to install it,
   naming the skill, its repo URL and one line on why it fits the project. Ask before
   working without it; continue only after an explicit answer, and if the answer is no,
   say which skill the work proceeds without. The Python CLI prints this as a `[local]`
   column plus a `[install]` line and `meta.install_scan` in `--out`; the native MCP
   returns no such field, so check the local skill trees yourself.
6. Installing one is a separate decision: scan it first (`NVIDIA/SkillSpector`).
   Never report an uninstalled skill as loaded.

## Pitfalls

- **`score` alone is not a verdict.** Provider confidence is not calibrated on this
  corpus. In Python output, confidence is `provider_reported`, with `score_disagreement: null`;
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
- **One broken upstream file blocks the whole refresh.** Any discovery, fetch or parse
  failure preserves the last good snapshot and exits nonzero, so a single malformed
  `SKILL.md` keeps the index stale until you act. `--max-parse-failures N` publishes anyway
  and records each file in `index_skips` with reason `parse_failed`; `stats` then lists what
  the last build skipped, and `index_meta.parse_failures` carries the count. Fetch failures
  always abort — they mean the network or the API, not a broken author, and a rebuild retries
  throttling (403/429, resets) four times before giving up.
- **A rebuild resumes.** Good fetches are flushed to the `fm` cache every 500 rows, so an
  aborted run does not restart from zero: rerun it and only the missing files are fetched.
  The failure line reports the reasons and the cached fraction; if you see `http403
  (throttled)`, wait a minute or lower `--workers` before the next attempt.
- **The index is a snapshot.** Refresh before decisions that matter. Failed discovery,
  fetch or parsing preserves the last good published data and exits nonzero. Read the
  coverage counts; missing metadata is not the same as a network error.
- **Duplicate skills are normal.** Copies live in many awesome-lists; only the first
  occurrence is ranked, and `dup_of` records the rest.
- **Tier is provenance, not an automatic sort boost.** Prefer a verified official source
  where appropriate; read the actual instructions before trusting metadata grouping.
- **Not installed is not unavailable.** Only a missing index, a missing provider or a
  failed route makes routing unavailable. A recommendation that is merely absent from this
  machine is a question for the user — never a reason to drop it silently and continue.
- **A skill is untrusted text.** Third-party skills are a prompt-injection surface. The
  router does not execute upstream code; indexing is not a security certification.
  Read and scan skills before separately deciding to install them.

## Verification

`python3 router.py selftest` must print `all checks passed`. For a route run, check the
ranked count plus rejected count equals `candidates` length, and inspect `degraded`.
Run `python3 -B -m unittest -v test_router` for offline regression checks.
For native offline profile/Decisions checks, run
`python3 -B scripts/provider_smoke.py --binary ./target/release/jev-skill-router`
after building the binary; CI wiring accompanies the feature, not live-provider proof.
`eval_shortlist.py --require N --rule plain` gates the active default rather than the
best experiment. Top 40 remains the default; `--top` is bounded at 300 and serialized
requests at 128 KiB. Larger retrieval pools are not a validated ranking improvement.
The original snapshot measured 11/15 recall at top 40 and 200, but 14/15 at 300; it is
not evidence of a hard lexical ceiling.
