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
- In `both`, attempt configured, usable providers concurrently, using a common
  task state and rubric. Batch at 128 questions to respect the Perplexity limit.
  At least one usable credential is sufficient. Record missing/invalid key or
  model configuration and continue with the other provider.
- In `both`, a candidate needs at least one valid answer. Average two valid
  scores/distributions equally; otherwise retain the single valid answer. Label
  candidate `aggregation` as `equal_mean` or `single`, and record `used_providers`.
  Confidence is `minimum_provider_confidence` for two answers and
  `provider_reported` for one. Disagreement is the absolute score difference for
  two answers and unavailable (`null`) for one; neither policy proves calibration.
- After a provider request fails, keep its valid earlier batch observations and
  stop its further requests. The other provider continues over the full shortlist.
  Reject a candidate only when neither provider has a valid answer; record reasons.
- Explicit `jev` and `perplexity` modes remain strict. Record per-provider
  status/error and route `status: complete|degraded|unavailable`, retaining the
  requested mode separately from `used_providers`. Degraded fallback is successful
  routing. No valid ranking produces a nonzero CLI exit; `--out` still writes the
  structured rejection/provenance result. Preserve candidate counts.
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
   Acceptance: all three modes work; each candidate is ranked or rejected; `both`
   survives missing configuration, request failure, and invalid individual answers
   whenever another valid answer exists, with explicit fallback provenance.
   Acceptance: a later batch failure retains earlier answers, stops that provider,
   and lets the other finish; neither usable provider yields structured failure.
   Verification: offline route/CLI fixtures for all modes, one/both-provider
   failures, candidate-level invalid answers, and more than 128 skills.
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
