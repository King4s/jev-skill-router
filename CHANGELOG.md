# Changelog

## Unreleased

### Added

- Choose Jev, Perplexity Decisions, or both when recommending skills. Jev remains
  the default, and each provider keeps its own credentials and model selection.
- Combined rankings retain individual provider observations, report which
  providers were used, and expose disagreement when both answers are valid.
- Offline provider/routing tests and an optional, disabled-by-default Mefi Studio
  integration plan. The MCP adapter and Studio workflow remain planned work.

### Fixed

- In `both` mode, automatically use the other provider when one is unavailable
  or errors. One usable credential is sufficient; valid earlier batch answers
  are retained, and a failed provider receives no further requests in the run.
- Use a single valid answer when the other is missing or invalid; reject a
  candidate only when neither is valid. Report degraded status and provider
  errors without fabricating scores. Explicit single-provider modes remain strict.
- Preserve structured rejection and provenance output on runs with no valid
  ranking when `--out` is supplied, while keeping their nonzero CLI exit.
- Reject malformed score responses without crashing or accepting non-finite,
  boolean or contradictory values. Runs without valid candidates fail clearly.
- Stop retrying permanent HTTP errors and malformed responses; use bounded backoff
  for transient failures without exposing response bodies or credentials.
- Keep the HTML report compatible with UTF-8 routing output and older Windows
  files; identify the decision maker and explain combined confidence.
