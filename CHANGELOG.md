# Changelog

## Unreleased

### Added

- Choose Jev, Perplexity Decisions, or both when recommending skills. Jev remains
  the default, and each provider keeps its own credentials and model selection.
- Ordered failover in `both`: higher measured accuracy is preferred, with lower
  measured cost breaking exact accuracy ties. The shipped external benchmark
  profile starts with Perplexity, then Jev, and can be replaced through
  `--priority-profile` or `SKILL_ROUTER_PRIORITY_PROFILE`.
- Routing output exposes priority order, measurement basis and metrics, plus
  the provider that supplied each accepted answer.
- Offline provider/routing tests and an optional, disabled-by-default Mefi Studio
  integration plan. The MCP adapter and Studio workflow remain planned work.

### Fixed

- In `both` mode, automatically use the other provider when one is unavailable
  or errors. Call it only for unresolved candidates; a healthy preferred provider
  causes no additional provider call. Request retries are disabled in `both`.
  One usable credential is sufficient; valid earlier batch answers are retained,
  and a failed provider receives no further requests in the run.
- Preserve the first valid answer without averaging scores or confidence. Reject
  a candidate only when neither provider supplies a valid answer. Report degraded
  status and provider errors without fabricating scores; disagreement is unavailable.
  Explicit single-provider modes remain strict.
- Preserve structured rejection and provenance output on runs with no valid
  ranking when `--out` is supplied, while keeping their nonzero CLI exit.
- Reject malformed score responses without crashing or accepting non-finite,
  boolean or contradictory values. Runs without valid candidates fail clearly.
- Stop retrying permanent HTTP errors and malformed responses; use bounded backoff
  for transient failures without exposing response bodies or credentials.
- Keep the HTML report compatible with UTF-8 routing output and older Windows
  files; identify the actual decision maker and explain provider-reported confidence.
