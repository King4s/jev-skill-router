# jev-skill-router

Collects skill sources from across the ecosystem, indexes them locally, and lets
**a decision maker like Jev** pick the best ones for the project you are about to build.
Choose **Jev**, **Perplexity Decisions**, or **both**. The router recommends skills;
it does not install or activate them.

## The architecture in one sentence

Code finds the candidates; the selected decision maker judges them. FTS5 builds a
shortlist from thousands of skills, and the providers rank it against the same
four-level relevance rubric, with their own reported confidence.

```
Skills-list.md ──► index ──► skills.db (SQLite FTS5) ──► route ──► ranking
                GitHub API   18k rows, 0 deps            FTS5 prefilter
                                                         └─► Jev / Perplexity / both
                                                              one Score per candidate per provider
```

## Measured (2026-10-04)

These historical measurements used Jev only. They do not measure Perplexity or
the combined ranking, whose accuracy and calibration need their own evaluation.

| | |
|---|---|
| Sources in `Skills-list.md` | 98 (34 vendor, 21 tooling, 19 community, 16 list, 8 registry) |
| `SKILL.md` found via the tree API | **18,562** |
| Unique skills after dedupe | **10,656** (7,408 were copies — 41%) |
| Sources carrying no `SKILL.md` | 16 — pure link lists, see *Phase 2* |
| Star counts in the list | verified against the GitHub API |
| One routing call | 40 candidates scored in **~0.5 s** |

Indexing is metadata-only: each repo costs two API calls (`repos/<r>` +
`trees?recursive=1`), and each skill is fetched as the first 4 KB of the raw file.
No clones. The frontmatter is all the router uses.

**Re-indexing is incremental.** The blob sha from the tree API is the version key: an
unchanged sha reuses the cached frontmatter from the `fm` table with no network call.
The first run fetches everything; later runs fetch only what Grok Bot added.

## Usage

```
python3 router.py index                      # build/refresh the index (network, ~10 min)
python3 router.py stats                      # what is in it
python3 router.py route "describe project"   # Jev remains the default
python3 router.py route "describe project" --provider perplexity
python3 router.py route "describe project" --provider both --out ranking.json
python3 router.py selftest                   # offline check, no network
python3 -m unittest discover -s tests -v     # offline provider and routing tests

python3 scripts/eval_shortlist.py --show     # does the shortlist find the known-good skills?
python3 scripts/rapport.py --dir <dir>       # HTML report from route JSON files
```

On Windows, use `python` if `python3` is unavailable.

`route --top 40` is the default: one request per selected provider. Larger
shortlists are split into batches of at most 128 questions. In `both` mode the
providers run concurrently against the same candidates, task state and rubric.

`gh` uses your authenticated session for indexing. Provider keys are read locally
and are never written into the repository or routing output:

| Selection | Required credentials | Default model |
|---|---|---|
| `jev` | `TYPESAFE_API_KEY`, or `~/.config/jev-loop/typesafe_api_key` | `jev-latest` |
| `perplexity` | `PERPLEXITY_API_KEY` | `pplx-decider-v1.1-27b` |
| `both` | Both credentials, checked before requests start | Both models above |

`--provider` overrides `SKILL_ROUTER_PROVIDER` (default `jev`). Use `--jev-model`
or `--perplexity-model` to override `JEV_MODEL` or `PERPLEXITY_DECISION_MODEL`.
Only the selected providers receive requests or require keys. `both` sends the
task and candidate metadata to both services and uses both accounts.

Perplexity uses the official [Decisions API](https://docs.perplexity.ai/docs/decisions/quickstart),
not its search/chat endpoint. The adapter uses Python's standard library, with no
new dependencies. Authentication errors fail immediately; transient errors use
bounded retries and backoff. A rate-limit delay longer than 30 seconds fails for
a later retry instead of retrying before the server allows it.

## Combined ranking and output

For `both`, a candidate needs a valid answer from **each** provider. Its combined
`score` and `probabilities` are arithmetic means with equal weights. This is a
transparent ranking policy, not a measured accuracy or calibration guarantee.

Each accepted candidate includes `provider_scores` with the original score,
confidence and probabilities. `score_disagreement` is the absolute difference
between the scores (0 to 3). The compatibility `confidence` field is the lower
provider confidence, labelled `confidence_kind: minimum_provider_confidence`;
it is **not** confidence that the providers agree. Two confident providers can
strongly disagree. Single-provider output labels it `provider_reported`.
Combined console output also explains `conf` and shows disagreement as `delta`.

The JSON output preserves `project`, `ranked`, and `rejected`, and adds
`schema_version`, the chosen `provider`, the `aggregation` policy, and `providers`
metadata (requested/resolved models, reported token usage, request IDs and calls).
There is exactly one ranked or rejected record per candidate. A malformed answer
is rejected with its provider's reason. A provider request failure fails the run
without silently falling back; no valid candidates produces a nonzero exit.
The existing HTML report continues to read the compatible ranking fields.

## What the measurement says

Four projects with hand-written facit lists (`scripts/eval_shortlist.py`): Minecraft 3/3,
OpenCorde 4/4, Tilbud 2/4, the router itself 2/4. Shortlist recall is 11/15 — and it is the
shortlist, not Jev, that loses the two weak cases.

Two rules were measured against each other on the same four projects: plain BM25 11/15,
IDF-weighted term coverage 5/15. The IDF rule lost because one ultra-rare word
("friends", "seventeen") outweighs several relevant ones. It is kept in the code only so
the harness can measure it again.

**Known ceiling — lexical overlap.** When a project's words and a skill's words do not
overlap, no keyword rule finds it. Measured: "classify each line into a product type from
a closed vocabulary" leaves the skill *"evaluation strategies for LLM applications"* at
rank **#248**. Fixing that means semantic retrieval in the first stage; it is not a
tuning problem.

## Dedupe

The same skill is copied into many awesome-lists. Fingerprint = sha1 of the normalised
`name + description`; the first occurrence wins and copies are stored with `dup_of`
pointing at the original. Only the original is ranked, and the copies still record how
many sources carry it.

Note that this catches identical copies, not near-siblings — three variants of
`*-linux-triage` from one repo can still take three slots in a ranking.

## Source tiers

`Skills-list.md` is sectioned, and the section number becomes a tier: `vendor` (official
company repos), `community`, `list` (awesome lists), `registry`, `tooling`. The tier rides
along in the ranking so a `vendor` hit can be preferred over a community copy at the same
score.

**Grok Bot maintains `Skills-list.md`.** Add a line or a table row with a
`github.com/owner/repo` link in the right section — the router reads the file, no code
change needed. Unnumbered sections (e.g. *Flagged / excluded*) are ignored on purpose.

## The answer contract is enforced

Type safety that is not enforced is only cosmetic. Every provider answer is validated before it
counts: `type == "score"`, `probabilities` keyed exactly like the levels, every number
finite in [0,1], sum within ±0.02 of 1, score inside the level range and consistent
with the distribution within 0.05. Numeric strings and booleans are rejected. Breaches are dropped
into `rejected` with the reason — they do not disappear quietly.

Read `score` together with the distribution, provider confidence and, in `both`,
disagreement. The earlier Jev confidence figures do not establish calibration for
this skill corpus, Perplexity, or the ensemble. A score is an expected rubric
level, not a probability that installing the skill is correct.

## Phase 2 — the 16 link lists

`VoltAgent/awesome-agent-skills`, `hesreallyhim/awesome-claude-code`, `agentsmd/agents.md`,
`intellectronica/ruler`, `K-Dense-AI/claude-skills-mcp` and others carry no `SKILL.md` at
all — they *point* at other repos. Their READMEs have to be parsed for
`github.com/owner/repo` links, and those links curated into `Skills-list.md`; pulling them
in automatically would blow the corpus up (one of the lists claims 5,400 skills).

## Security

The router **reads** public repos only and executes nothing from them. Installing a
recommended skill is a separate decision: run it through a scanner
(`NVIDIA/SkillSpector`, `cisco-ai-defense/skill-scanner`) before it reaches an agent. A
third-party skill is a prompt-injection surface, not just a text file.

## Optional Mefi Studio integration

The [Studio integration plan](docs/studio-integration-plan.md) describes a
disabled-by-default option: task → decision maker recommends → retrieve and
validate → load approved instructions → worker executes. It includes an MCP
adapter, a bounded skill cache, per-task loading and phased acceptance tests.
These Studio components are **planned**, not implemented by this CLI change.
Adding a connector alone does not install or activate recommended skills.

## Next step

The repository currently ships the Python CLI. A Rust MCP service using
`reqwest` and `rusqlite` remains a possible future implementation; both decision
providers can be called over HTTP. The Studio plan starts with a thin adapter
around the tested Python pipeline so a port is not a prerequisite.

## Repository language

Everything in this repo — code, comments, docs, commit messages — is in English.
