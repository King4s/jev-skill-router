# jev-skill-router

Collects skill sources from across the ecosystem, indexes them locally, and lets
**Jev** (TypeSafe System One) pick the best ones for the project you are about to build.

## The architecture in one sentence

Code finds the candidates, Jev judges them. 10.000+ skills cannot be a single Jev
question — so FTS5 builds the shortlist, and Jev ranks it with `Score` plus calibrated
confidence.

```
Skills-list.md ──► index ──► skills.db (SQLite FTS5) ──► route ──► ranking
                GitHub API   18k rows, 0 deps            FTS5 prefilter
                                                         └─► Jev: one call, one Score per candidate
```

## Measured (2026-10-04)

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
python3 router.py route "describe project"   # FTS5 shortlist -> Jev -> ranking
python3 router.py selftest                   # offline check, no network

python3 scripts/eval_shortlist.py --show     # does the shortlist find the known-good skills?
python3 scripts/rapport.py --dir <dir>       # HTML report from route JSON files
```

`route --top 40` is the default: 40 candidates in **one** Jev call. Batching is the whole
point — 21 questions in one call cost the same wall time as 1.

Exact keys: `gh` needs no key (it uses your authenticated session), and `TYPESAFE_API_KEY`
must be in the environment or at `~/.config/jev-loop/typesafe_api_key`. Both are read
server-side by the tool and never written into the repo.

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

Type safety that is not enforced is only cosmetic. Every Jev answer is validated before it
counts: `type == "score"`, `probabilities` keyed exactly like the levels, every number
finite in [0,1], sum within ±0.02 of 1, score inside the level range. Breaches are dropped
into `rejected` with the reason — they do not disappear quietly.

Read `score` **together with** `probabilities` and `confidence`. From our own measurements:
confidence below 0.5 → 19% right, above 0.9 → 98.8%. A score of 2.4 at confidence 0.35
means "the model is split between two levels", not "2.4 is certain".

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

## Next step

Rust-first: the MCP service itself is written in Rust (`reqwest` + `rusqlite`; Jev is
called over HTTP — there is no Rust SDK). This Python file is the data pipeline that
proves the loop; the port happens once the ranking is measured good enough.

## Repository language

Everything in this repo — code, comments, docs, commit messages — is in English.
