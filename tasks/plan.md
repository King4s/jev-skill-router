# Implementation plan: selectable decision makers

## Scope

Add Perplexity Decisions to the existing Python router with three explicit modes:
`jev` (the backwards-compatible default), `perplexity`, and `both`. Deliver an
optional Mefi Studio integration plan; Studio code and an MCP server are future
work. All new code, documentation, test names and commits are in English.

## Contracts and decisions

- Preserve the existing SQLite index, FTS5 shortlist and recommendation-only role.
- Use the official Perplexity Decisions endpoint and `pplx-decider-v1.1-27b`.
- Keep credentials separate: `TYPESAFE_API_KEY` (or the existing Jev key file)
  and `PERPLEXITY_API_KEY`. Send keys only to their fixed HTTPS endpoint.
- `--provider jev|perplexity|both` overrides `SKILL_ROUTER_PROVIDER`; default `jev`.
  Explicit per-provider model options override their environment defaults.
- Both providers receive identical candidates, task state and rubric. Batch at
  128 questions to respect the Perplexity limit; call both providers concurrently.
- In `both`, only candidates validated by both providers enter the ranking.
  Scores and distributions are arithmetic means; confidence is the lower provider
  confidence, labelled as such, not a calibrated consensus estimate. Retain each
  provider's original observations and report absolute score disagreement.
- A provider request failure fails the requested mode without switching providers.
  Invalid candidate answers are recorded in `rejected`; preserve candidate counts.
- Keep `project`, `ranked`, `rejected`, `score`, `confidence`, and `probabilities`
  compatible with the existing report reader. Add provider and request provenance.
- Validate external containers, finite numbers, rubric keys and probability sums.
  HTTP errors expose status/request ID rather than response bodies or secrets.

## Ordered implementation tasks

1. **Provider transport and validation** (no dependencies).
   Add the standard-library provider adapter and offline HTTP/validation tests.
   Acceptance: correct URLs/auth/models; selected key only; bounded retry/backoff;
   malformed answers and responses fail clearly; no credential-bearing redirects.
   Verification: `python -m unittest discover -s tests -v` and original selftest.
2. **Selection and combined ranking** (depends on 1).
   Add CLI options, batch scoring, provider metadata and explicit combined policy.
   Acceptance: all three modes work; same rubric/candidates; each candidate is
   ranked or rejected; provider failures never cause silent fallback.
   Verification: offline route/CLI fixtures for all modes and more than 128 skills.
3. **Documentation and Studio plan** (depends on the contracts above).
   Update usage, skill instructions and change notes; document Studio's optional
   disabled-by-default integration phases with source links and acceptance gates.
   Verification: examples match `route --help`; independent review of the diff.

## Checkpoints

- Before implementation: current `python router.py selftest` passes.
- Each slice: new tests first fail, then pass; commit verified increments.
- Completion: full offline suite, selftest and CLI verification pass; review fixes
  resolved; report whether live provider calls were actually exercised.

## Official sources

- [Perplexity Decisions quickstart](https://docs.perplexity.ai/docs/decisions/quickstart)
- [Mefi Studio agent tools](https://github.com/nateecho32-stack/mefi-studio/blob/main/docs/agent-tools.md)
- [Studio integration plan](../docs/studio-integration-plan.md)

## Limits

Existing shortlist quality is unchanged. Dual-provider means are a transparent
ranking policy, not measured calibration. Automated installation and activation
are not part of this router change. Offline tests do not prove live credentials,
provider availability or end-to-end Studio compatibility.
