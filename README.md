# jev-skill-router

Indexes third-party skill metadata from `Skills-list.md`, retrieves candidates with
SQLite FTS5, and ranks the shortlist with TypeSafe Jev. It recommends skills; it
never installs or executes them. The MCP service is not implemented yet.

## Usage

Python standard library only. Indexing requires authenticated `gh`; routing requires
`TYPESAFE_API_KEY` or `~/.config/jev-loop/typesafe_api_key`.

```
python3 router.py index
python3 router.py stats
python3 router.py route "describe project" --top 40 --out route.json
python3 router.py selftest
python3 -B -m unittest -v test_router
python3 scripts/eval_shortlist.py --top 40 --rule plain --require 11
python3 scripts/eval_shortlist.py --top 300 --rule plain --require 14
python3 scripts/rapport.py --dir <artifact-directory>
```

Reports recognize case filenames `minecraft.json`, `opencorde.json`, `tilbud.json`
and `router.json`. Optional `regler.json` holds comparison metrics in the format
written by `eval_shortlist.py --out`.

## Architecture and review fixes

`Skills-list.md → GitHub metadata → skills.db → FTS5 shortlist → one Jev Score per candidate`

The active default remains plain BM25. Jev judges only what the retriever supplies.

- Failed lookup, truncated tree, failed download or malformed/unsupported frontmatter
  aborts refresh without replacing published rows/cache. Genuine empty trees are
  distinguished from errors. Successful refresh atomically replaces skills, FTS,
  sources, cache and provenance; confirmed upstream deletions disappear.
- Three GitHub API calls pin each source revision: metadata, commit, complete tree.
  Raw URLs use that revision and escaped file paths, matching blob-SHA cache versions.
- Complete frontmatter is fetched with a 64 KiB bound, not cut at 4 KiB. The stdlib
  parser supports plain/quoted scalars and folded/literal blocks with inline comments.
  It is not a general YAML loader: unsupported required-field structures fail explicitly.
  Missing usable name/description is counted separately as `missing_metadata`.
- Coverage records discovered, cached, parsed, missing-metadata, fetch-failure and
  parse-failure counts. Parser-version changes invalidate old parsed caches.
- Unicode-preserving SHA-256 fingerprints group normalized **metadata**, retaining C++
  punctuation. They are not hashes of skill bodies and do not prove equal instructions.
  First occurrence wins; other sources retain `dup_of` pointers.
- Responses require valid object shapes, finite JSON numbers excluding strings/bools,
  exact probability keys, values in [0,1], sum within 0.02 of 1, and score consistent
  with the weighted mean. Two-decimal rounding tolerance is
  `0.01 + 0.005 * levels * (levels - 1) / 2`. Invalid answers are rejected, not crashes.
- Zero accepted answers returns nonzero; partial artifacts carry `degraded=true` and
  preserve every candidate/rejection. Unexpected answer IDs reject the response.
- Authentication/validation HTTP errors fail immediately. Transient errors use bounded
  exponential backoff and Retry-After. No provider fallback or new dependency is added.
- Positive `--top` values are bounded at 300; serialized Jev requests at 128 KiB. These
  are client safety ceilings, not TypeSafe context-limit claims. Larger permitted
  requests can still be rejected upstream; measure budget and ranking quality first.
- Empty/OOV queries do not divide by zero in IDF/pool variants. `--require` checks the
  explicitly active rule, not the highest-scoring experiment.
- Route artifacts include pre-validation candidates, query tokens, requested top,
  rule, returned model, actual latency and corpus identity/counts. Reports separate
  retrieval recall from response-validation loss. Unknown legacy provenance stays unknown.

## Measurements and correction (2026-10-04)

The unchanged local snapshot holds 10,656 canonical metadata entries from 98 sources.
The old pipeline discovered 18,562 paths but inserted 18,064 rows, leaving 498 omissions
unexplained. It has no parser-version or coverage record. This snapshot was deliberately
not rebuilt during the fix, keeping retrieval comparisons stable. A separate test DB
was indexed twice from this repository: one parsed skill, then one blob-SHA cache hit.

Four hand-selected cases on that unchanged snapshot, plain BM25:

| Limit | Minecraft | OpenCorde | Tilbud | Router | Total |
|---|---:|---:|---:|---:|---:|
| 40 | 3/3 | 4/4 | 2/4 | 2/4 | 11/15 |
| 200 | 3/3 | 4/4 | 2/4 | 2/4 | 11/15 |
| 300 | 3/3 | 4/4 | 3/4 | 4/4 | 14/15 |

**The earlier claim that 11/15 was a lexical ceiling was wrong.** Canonical missing
skills ranked 232 (Rust MCP), 248 (LLM evaluation), 295 (SQLite), and 7850 (web-scraping).
Three have substantive lexical overlap; widening beyond 200 finds them. This neither
proves embeddings necessary nor changes the default top 40. The facit includes
Python-oriented `fastmcp` in a Rust case: it is a regression fixture, not an independent
expert benchmark. Recall is candidate survival, not Jev ordering quality. Grocery-task
or vendor confidence calibration does not establish skill-routing correctness.

The hardened live route/report path was exercised on the router case with 40 candidates.
Exact model, latency and answer counts belong to its artifact, not an assumed universal
0.5-second timing. Local probe DBs and evidence live under ignored `measurements/`.

## Sources and security

Grok Bot maintains `Skills-list.md`. Numbered sections map to vendor, community, list,
registry and tooling tiers; unnumbered excluded sections are ignored. Link-list sources
still need curated expansion, not automatic recursive ingestion of arbitrary README URLs.
An API failure is never evidence that a source contains only links.

Third-party metadata and bodies are untrusted. No upstream code is executed. Inspect
and scan recommended skills before installation. Keys are read locally and never put
in artifacts or git. The eventual MCP implementation remains Rust-first; no service,
embedding model, or production deployment is introduced by these fixes.

All source, comments, docs and new commit messages are in English.
