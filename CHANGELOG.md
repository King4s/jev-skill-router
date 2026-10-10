# Changelog

## Unreleased

### Added

- Choose Jev, Perplexity Decisions, or both when recommending skills. Jev remains
  the default, and each provider keeps its own credentials and model selection.
- Combined rankings retain individual provider observations and expose score
  disagreement; failed or invalid observations never become silent fallback.
- Offline provider/routing tests and an optional, disabled-by-default Mefi Studio
  integration plan. The MCP adapter and Studio workflow remain planned work.

### Fixed

- Reject malformed score responses without crashing or accepting non-finite,
  boolean or contradictory values. Runs without valid candidates fail clearly.
- Stop retrying permanent HTTP errors and malformed responses; use bounded backoff
  for transient failures without exposing response bodies or credentials.
- Keep the HTML report compatible with UTF-8 routing output and older Windows
  files; identify the decision maker and explain combined confidence.
