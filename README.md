<div align="center">

# Jev Skill Router

### Find the right skills. Let code retrieve. Let Jev judge.

**GitHub metadata → SQLite FTS5 → TypeSafe Jev → ranked recommendations**

[![Verification](https://github.com/King4s/jev-skill-router/actions/workflows/verify.yml/badge.svg)](https://github.com/King4s/jev-skill-router/actions/workflows/verify.yml)
![Runtime: Rust](https://img.shields.io/badge/runtime-Rust-orange)
![Protocol: MCP](https://img.shields.io/badge/protocol-MCP-blue)
![Safety: read only](https://img.shields.io/badge/safety-read--only-2ea44f)

[Quick start](#quick-start) · [MCP tools](#mcp-tools) · [Safety](#safety-and-limits) · [Verification](#verification) · [Sources](https://github.com/King4s/jev-skill-router/blob/main/Skills-list.md)

</div>

---

A native Rust MCP server that recommends third-party agent skills for a project.
It retrieves deduplicated metadata with SQLite FTS5/BM25, then sends **one comparable
Jev Score per candidate in a single provider request**. It never installs or executes skills.

The Python indexer (with PyYAML) and evaluation scripts are **offline tooling**.
The Rust service opens SQLite read-only and calls TypeSafe directly: no Python wrapper,
shell subprocess, or skill execution in the runtime.

## Quick start

Requirements: Rust/Cargo, Python 3 with SQLite FTS5, authenticated [GitHub CLI](https://cli.github.com/),
and a [TypeSafe API key](https://console.typesafe.ai/keys) for ranking. Retrieval needs no model key.
This checkout includes the native implementation introduced by
[PR #1](https://github.com/King4s/jev-skill-router/pull/1).
The refresh utility consumes `main`'s source list without importing its executable code.

```sh
git clone https://github.com/King4s/jev-skill-router.git
cd jev-skill-router
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-offline.txt
python3 -B router.py index --workers 16
python3 -B router.py stats
cargo build --release --locked
```

Put `TYPESAFE_API_KEY` in your client's protected environment. Start a **stdio MCP** server:

```sh
SKILL_ROUTER_DB="$PWD/skills.db" ./target/release/jev-skill-router
```

The client owns stdin/stdout. Logs go to stderr; closing stdin shuts down the process.
The native service does **not** read Python's fallback key file. Supply its key explicitly.

### Shared internal endpoint

Run the same binary with `--http`. Set `SKILL_ROUTER_TOKEN` to a randomly generated
secret of at least 32 non-whitespace ASCII bytes, and select a loopback or Tailnet bind.
Clients POST MCP messages to `/mcp` with a bearer Authorization header and
`Accept: application/json, text/event-stream`.

This is **stateless Streamable HTTP**, not a custom REST API. It uses the official
[`rmcp` SDK](https://github.com/modelcontextprotocol/rust-sdk), pinned in `Cargo.lock`.
No public/all-interface binds are accepted. See [the deployment guide](deploy/README.md)
and [the supplied systemd unit](deploy/jev-skill-router.service).

## MCP tools

| Tool | Inputs | Output |
|---|---|---|
| `skills_stats` | None | Canonical/duplicate counts, coverage, snapshot identity |
| `skills_search` | `query`, optional `top` | BM25 candidates and corpus/query provenance; no provider call |
| `skills_route` | `project`, optional `top` | Ranked/rejected candidates, score, confidence, probabilities and actual model/timing |

`top` defaults to **40** and must be an integer in **1–300**. Text is limited to
**16 KiB of UTF-8**. Empty or out-of-vocabulary queries return an empty candidate set.
A route with candidates but no valid provider answers is an MCP tool error; a partial
route preserves the entire shortlist and sets `degraded=true`.

**Scores measure relevance, not permission to install.** Read the upstream skill and
inspect confidence as well as score before making a separate installation decision.

## How the index stays honest

```mermaid
flowchart LR
    A[Authorized GitHub sources] --> B[Pin branch revision and complete tree]
    B --> C[Bounded frontmatter + blob-SHA cache]
    C --> D[Atomic SQLite snapshot]
    D --> E[Read-only FTS5 shortlist]
    E --> F[One Jev Score per candidate]
    F --> G[Validated ranked recommendations]
```

- The [current GitHub-main `Skills-list.md`](https://github.com/King4s/jev-skill-router/blob/main/Skills-list.md)
  is the refresh authority. The current list contains 108 included GitHub sources.
  Numbered sections map to provenance tiers; the flagged/excluded section is not ingested. Site-only
  registries and GitLab/Hugging Face entries are documented, not implied GitHub coverage.
- Each GitHub source uses metadata → encoded branch ref → pinned recursive tree.
  Truncated trees fail explicitly. Raw requests use the pinned revision and escaped paths.
- Frontmatter is bounded at 64 KiB. Plain/quoted scalars, multiline quoted strings,
  folded/literal blocks and flat scalar tag lists are supported. Tag lists become normalized
  text metadata; nested ranking-field objects, anchors, aliases, explicit YAML tags,
  duplicate top-level keys and malformed scalar values are rejected. SafeLoader syntax nodes
  retain scalar text without implicit number/date/bool conversion; no upstream objects are constructed.
- **Documented extension:** fully closed, standalone single-line HTML comments inside
  frontmatter are ignored. This accommodates upstream metadata without excluding records;
  comments are never executed or interpreted as security approvals. Token-aware parsing retains
  comment text inside quoted and folded/literal block scalars. Unclosed comments, trailing garbage
  and garbage between separate comments are not swallowed by this extension.
  YAML folding preserves indented dash text within scalar values; only actual nested nodes are
  rejected. **Description-text compatibility:** when the YAML scanner rejects an unquoted colon
  separator in a root-level `description:` whose single-line plain value starts with an
  alphanumeric character, the indexer quotes that literal text and retries safe-node parsing.
  Inline YAML comments still remain comments. Quoted/block content, other fields, multiline
  continuations, anchors/aliases/tags, duplicate keys and unrelated malformed syntax are not
  repaired. Missing metadata remains separate from malformed syntax. This is bounded safe-node
  parsing, not arbitrary YAML object construction or execution.
- Missing usable name/description is recorded separately from download or parsing failure.
  `index_skips` retains exact source/path/blob identities for every intentional omission.
- One intentionally malformed upstream test fixture is recognized **only by its exact
  repository, path and blob SHA**. A changed blob becomes an error again; no blanket waiver.
- Successful refresh atomically replaces skills, FTS5, sources, caches, skip accounting
  and corpus metadata. Any discovery/fetch/parse failure preserves the last good snapshot.
- Unicode-preserving SHA-256 fingerprints group **normalized metadata**, not full skill
  bodies. Source rows remain available via duplicate pointers; metadata equality does not
  prove equal instructions.
- The service reads candidates and provenance in a single read transaction. It cannot
  rebuild or mutate the corpus. The optional [daily refresh job](deploy/README.md#automatic-source-list-consumption)
  follows the current GitHub-main source list outside the MCP runtime, validates a complete
  rebuilt snapshot, and atomically publishes it. Failed refreshes retain the live index.

### Automatic source-list consumption

`Skills-list.md` is input to the indexer, **not a file parsed on each MCP request**.
The separate Rust `jev-skill-refresh` batch utility pins the list's current GitHub-main
commit, downloads only that Markdown file, and runs the already approved offline indexer
under a dedicated non-login account. It never pulls or executes new repository code.

The supplied cron entry runs daily at **03:20 in the host's local timezone** when installed.
It uses the existing cron daemon, an exclusive refresh lock, a three-hour deadline and
journal logging. Publication checks exact source/tier membership, complete path accounting,
zero download/parser failures, cache/duplicate/FTS consistency and SQLite integrity.
The previous snapshot is retained for rollback; the MCP process stays read-only and does
not restart. In-flight requests keep their old coherent snapshot; later requests reopen
that published at the same path.

The list producer's stated weekly update cadence is separate from this daily consumer:
this job does not perform weekly research or edit the curated source list. A missing
listed repository fails the entire refresh; it is never silently dropped. See the
[deployment guide](deploy/README.md#automatic-source-list-consumption) for installation,
manual execution, failure diagnostics and rollback.

**Verified live on 2026-10-11:** the installed job published the current **108-source**
authority after the owner-approved single-source exclusion in [PR #4](https://github.com/King4s/jev-skill-router/pull/4).
The MCP endpoint served the new snapshot without a restart: **15,682 canonical records**,
**26,098 source rows**, **26,596 fully accounted paths**, zero fetch/parse failures,
and 40 validated candidates from the real Jev provider. Daily consumption is enabled;
this successful manual run does not claim the next scheduled tick has already occurred.

## Safety and limits

| Boundary | Enforced behavior |
|---|---|
| Skill trust | Metadata is untrusted data, never installed or executed |
| Database | Existing file required; read-only opens; snapshot-consistent retrieval |
| HTTP | Bearer auth, exact bound Host, reject Origin, 256 KiB actual-body limit including chunked requests |
| Ranking capacity | Four shared, non-queueing permits; excess requests fail explicitly |
| Provider budget | 128 KiB serialized request; 2 MiB response; 180-second per-attempt timeout |
| Retries | At most four attempts; bounded backoff/Retry-After; permanent errors fail immediately |
| Provider trust | Finite JSON numbers, exact probability keys, bounded probabilities, normalized sum and score consistency |
| Error handling | Unknown answer IDs reject the response; partial/no-valid distinctions preserved; no provider fallback |
| Credentials | Environment only for native runtime; provider bodies and transport errors not echoed |

Probability normalization permits a 0.02 rounding tolerance; the four-level weighted
mean permits 0.04. These are validation tolerances, not claims of model accuracy.
Jev can rank only the retrieved shortlist. Wider retrieval is not automatically better ranking.

## Verification

All checks are reproducible and run by [GitHub Actions](.github/workflows/verify.yml):

```sh
python3 -B -m unittest -v test_router
python3 -B router.py selftest
python3 -B -m unittest discover -s tests -v
cargo fmt --check
cargo test --locked
cargo clippy --locked -- -D warnings
cargo build --release --locked
python3 -B scripts/mcp_smoke.py --binary ./target/release/jev-skill-router
```

The MCP smoke harness executes the **real Rust binary**, stdio handshake/EOF and HTTP
transport, authentication/Host/Origin, invalid inputs, fixed/chunked request limits,
Python retrieval/token parity, UTF-8 text boundaries, provider byte budgets,
fail-fast four-slot capacity, and good/partial/invalid/retried provider responses.
Its temporary database and synthetic provider are explicitly **offline fixtures**, not
live TypeSafe integration. `--url <internal-mcp-url> --live --out <route.json>` exercises
a deployed endpoint with the real provider, using `SKILL_ROUTER_TOKEN` from the environment.

## Optional Python decision providers

Provider selection below is **Python offline/evaluation tooling only**. The native
Rust MCP remains Jev-only; these options do not change its runtime or MCP tools.

```
python3 router.py index                      # build/refresh the index (network, ~10 min)
python3 router.py stats                      # what is in it
python3 router.py route "describe project"   # Jev remains the default
python3 router.py route "describe project" --provider perplexity
python3 router.py route "describe project" --provider both --out ranking.json
python3 router.py route "describe project" --provider both --priority-profile my-priority.json
python3 router.py selftest                   # offline check, no network
python3 -m unittest discover -s tests -v     # offline provider and routing tests

python3 scripts/eval_shortlist.py --show     # does the shortlist find the known-good skills?
python3 scripts/rapport.py --dir <dir>       # HTML report from route JSON files
```

On Windows, use `python` if `python3` is unavailable.

`route --top 40` is the default. Larger shortlists are split into batches of at
most 128 questions. In `both` mode, the preferred provider goes first. The other
is called only for unresolved candidates if the preferred provider is unavailable,
errors, or returns malformed/missing answers. A healthy preferred provider means
no call to the other. Valid earlier batch answers are retained; a provider that
fails receives no further requests in the run. `both` disables request retries
so it can move to the fallback without repeating a failed call.

`gh` uses your authenticated session for indexing. Provider keys are read locally
and are never written into the repository or routing output:

| Selection | Required credentials | Default model |
|---|---|---|
| `jev` | `TYPESAFE_API_KEY`, or `~/.config/jev-loop/typesafe_api_key` | `jev-latest` |
| `perplexity` | `PERPLEXITY_API_KEY` | `pplx-decider-v1.1-27b` |
| `both` | At least one usable provider credential; unavailable providers are reported and skipped | Available models above |

`--provider` overrides `SKILL_ROUTER_PROVIDER` (default `jev`). Use `--jev-model`
or `--perplexity-model` to override `JEV_MODEL` or `PERPLEXITY_DECISION_MODEL`.
Only the selected providers receive requests. Explicit `jev` and `perplexity`
selections require the chosen provider and never switch services. In `both`, only
the provider currently needed receives the task and candidate metadata; a missing
or invalid key/model is reported without blocking use of the other.

Perplexity uses the official [Decisions API](https://docs.perplexity.ai/docs/decisions/quickstart),
not its search/chat endpoint. The adapter uses Python's standard library, with no
new dependencies. Explicit single-provider modes use bounded retries and backoff
for transient errors; authentication errors fail immediately. In `both`, a failed
request proceeds to fallback without retries. A rate-limit delay longer than 30
seconds fails instead of retrying before the server allows it.

## Provider priority: accuracy first, cost breaks ties

`both` is ordered failover. With valid, model-matched measurements, the provider
with higher measured accuracy goes first. If accuracy is exactly tied, lower
measured cost per candidate breaks the tie. Response confidence is not a measure
of provider accuracy and cannot establish which provider is better.

The shipped [priority profile](provider-priority.json) starts with **Perplexity →
Jev**, using this external DecisionBench snapshot inspected on 2026-10-10:

| Decision maker | Observed accuracy | Estimated cost per 1,000 benchmark rows |
|---|---|---|
| `pplx-decider-v1.1-27b` | 94.49% (1,012/1,071) | $0.01698 |
| `jev-1.13.0` | 92.44% (990/1,071) | $0.04322 |

Sources: [Perplexity announcement](https://community.perplexity.ai/t/pplx-decider-v1-1-27b-scores-the-highest-on-decision-bench-for-accuracy-with-the-lowest-cost/6312),
[published data](https://decisionbench.ai/data.json), and
[evaluation protocol](https://decisionbench.ai/protocol.txt). These are external
choice-question results, not this router's skill-score evaluation. Perplexity's
benchmark run used OpenRouter; the router uses Perplexity's direct API. The
accuracy intervals overlap, so the observed ordering does not establish universal
superiority. Costs are estimates from that workload, not verified invoices.

The profile stores model identities, accuracy, `cost_per_candidate_usd`, source,
and sample count. Replace it with representative skill-routing measurements as
they become available, and refresh it when model aliases resolve to new versions.
`--priority-profile` overrides
`SKILL_ROUTER_PRIORITY_PROFILE`; otherwise the shipped profile is used. When
comparable quality evidence is unavailable or does not match the requested models,
use a documented provisional price/default order and expose that basis rather
than claiming the providers have equal quality.

The provider documentation snapshot records input-token rates of $0.02 per million for Perplexity Decisions and
$0.042 per million for Jev; both have free output tokens.
[Perplexity pricing](https://docs.perplexity.ai/docs/decisions/quickstart#pricing),
[TypeSafe models](https://docs.typesafe.ai/models). Actual request cost also depends
on token usage, batching, and failed attempts. Prices and measurements can change.

## Ranking and output

Each accepted candidate uses the first valid answer in priority order. Its score,
confidence, and probabilities remain unchanged, with `aggregation: single`,
`confidence_kind: provider_reported`, and exactly one entry in `used_providers`
and `provider_scores`. `score_disagreement` is unavailable (`null`), because each
candidate has one accepted provider observation. Invalid earlier answers remain
in `provider_errors`. Reject a candidate only when no selected provider supplies
a valid answer. The console identifies which provider supplied each result.

The JSON output preserves `project`, `ranked`, and `rejected`, and adds
`schema_version`, the requested `provider`, `used_providers`, the aggregation
policy, and `providers` metadata (status/error, requested/resolved models,
reported token usage, request IDs and calls). The route-level `aggregation` is
`priority_failover` for `both`; `priority` exposes its `order`, `basis`, and
`metrics`; an invalid or unreadable priority profile produces `priority: null`,
an unavailable failure artifact, and no provider request. The route's `status` is
`complete` when valid ranking is available without
provider fallback, `degraded` when `both` retains valid ranking after provider
unavailability or invalid results, or `unavailable` when no valid ranking is
available. A degraded route succeeds with explicitly reported fallback.

There is exactly one ranked or rejected record per candidate. Invalid answers and
provider failures remain visible with their reasons, even when the other provider
saves the candidate. If neither provider supplies valid answers, the CLI exits
nonzero; `--out` still writes the structured rejection and provenance result.
The existing HTML report continues to read the compatible ranking fields.

### Evaluation is not ranking accuracy

[`scripts/eval_shortlist.py`](scripts/eval_shortlist.py) compares lexical rules on four
hand-selected cases. `--require` gates the specified active rule, not the best experiment.
The verified **2026-10-05 parser-8 snapshot** contains **10,710 canonical metadata records**
from **98 pinned sources**. All **18,629 discovered paths** are accounted for:
18,133 parsed records (including 7,423 duplicate source rows), 495 missing-metadata
paths and one exact negative fixture; **zero fetch or parse failures**.
That snapshot measured plain recall **9/15 at top 40 and 14/15 at top 300**;
these are historical 98-source results, not measurements of the new 108-source snapshot.
See the [delivery evidence and limitations](docs/delivery-2026-10-05.md).

The original snapshot measured plain recall **11/15 at top 40 and 200, 14/15 at 300**.
The earlier claim of an 11/15 lexical ceiling was wrong. These labels are regression
fixtures, not an independent expert benchmark: the Rust case even contains `fastmcp`.
Neither unrelated Jev confidence calibration nor shortlist recall establishes ordering quality.

The [measurement report generator](scripts/rapport.py) reads route/evaluation JSON,
separates retrieval from validation, and preserves unknown legacy provenance as unknown.
Databases, caches, binaries and local measurement artifacts are ignored, not shipped as stale indexes.

## Configuration

| Variable | Default / purpose |
|---|---|
| `SKILL_ROUTER_DB` | `skills.db`; existing SQLite snapshot |
| `TYPESAFE_API_KEY` | Required only when non-empty candidate sets are ranked |
| `JEV_API` | `https://api.typesafe.ai/v1/systemone`; HTTPS, or loopback HTTP for offline tests |
| `JEV_MODEL` | `jev-latest` |
| `SKILL_ROUTER_BIND` | `127.0.0.1:3016`; HTTP only |
| `SKILL_ROUTER_TOKEN` | Required for HTTP; no default secret |

Python also offers `route`, `--out`, `stats`, `selftest` and explicit index rebuilding.
It may read `~/.config/jev-loop/typesafe_api_key`; the Rust server deliberately does not.
No embeddings, automatic installers, arbitrary link crawling, or changes to other projects.

## Optional Mefi Studio integration

The [Studio integration plan](docs/studio-integration-plan.md) describes a
disabled-by-default option: task → decision maker recommends → retrieve and
validate → load approved instructions → worker executes. It includes an MCP
adapter, a bounded skill cache, per-task loading and phased acceptance tests.
These Studio components are **planned**, not implemented by this CLI change.
Adding a connector alone does not install or activate recommended skills.

The Studio plan describes an optional adapter around the Python pipeline, not a
change to the existing native Jev-only MCP server.

All source, comments, documentation, CLI output and new commit messages are in English.
