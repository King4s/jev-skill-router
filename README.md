<div align="center">

# Jev Skill Router

### Find the right skills. Let code retrieve. Let Jev judge.

**GitHub metadata → SQLite FTS5 → TypeSafe Jev → ranked recommendations**

[![Verification](https://github.com/King4s/jev-skill-router/actions/workflows/verify.yml/badge.svg)](https://github.com/King4s/jev-skill-router/actions/workflows/verify.yml)
![Runtime: Rust](https://img.shields.io/badge/runtime-Rust-orange)
![Protocol: MCP](https://img.shields.io/badge/protocol-MCP-blue)
![Safety: read only](https://img.shields.io/badge/safety-read--only-2ea44f)

[Quick start](#quick-start) · [MCP tools](#mcp-tools) · [Safety](#safety-and-limits) · [Verification](#verification) · [Sources](Skills-list.md)

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
Clients POST MCP messages to `/mcp` with `Authorization: Bearer <your-token>` and
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
    A[98 authorized GitHub sources] --> B[Pin branch revision and complete tree]
    B --> C[Bounded frontmatter + blob-SHA cache]
    C --> D[Atomic SQLite snapshot]
    D --> E[Read-only FTS5 shortlist]
    E --> F[One Jev Score per candidate]
    F --> G[Validated ranked recommendations]
```

- [`Skills-list.md`](Skills-list.md) is the single source list. Numbered sections
  map to provenance tiers; the flagged/excluded section is not ingested. Site-only
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
  rebuild or mutate the corpus. Refresh and deployment remain explicit operator actions.

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

### Evaluation is not ranking accuracy

[`scripts/eval_shortlist.py`](scripts/eval_shortlist.py) compares lexical rules on four
hand-selected cases. `--require` gates the specified active rule, not the best experiment.
The verified **2026-10-05 parser-8 snapshot** contains **10,710 canonical metadata records**
from **98 pinned sources**. All **18,629 discovered paths** are accounted for:
18,133 parsed records (including 7,423 duplicate source rows), 495 missing-metadata
paths and one exact negative fixture; **zero fetch or parse failures**.
Current plain recall is **9/15 at top 40 and 14/15 at top 300**.
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

All source, comments, documentation, CLI output and new commit messages are in English.
