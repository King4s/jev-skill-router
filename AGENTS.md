# AGENTS.md

Conventions for coding agents driven by DevDesk (`~/devdesk/desk.py`) on this repository.

## Role
You are a coding agent driven by an orchestrator. Work only inside the current git worktree
and branch. The orchestrator runs the tests, asks an independent reviewer and decides when the
task is done.

## Hard rules
- Never push, merge, deploy, tag, commit, or open pull requests or issues. The orchestrator does
  any git and GitHub work, and in phase 1 nothing leaves the machine.
- Never read, print, or change secrets, `.env` files, key files, or CI secrets.
- No network access is needed: every test runs offline. Do not install packages.
- Fix only the scope of the task. Do not touch files outside the task's `allowed_paths`.
- Keep failing regression tests. Change the implementation, not the test result.
- Run the task's test command before you finish and report what you ran.
- If continuing needs a decision about secrets, deletion, money, legal/GDPR, auth/billing code,
  merging/deploying, or a product choice: stop and fill `needs_decision`.

## Repository conventions
- Python 3.11, standard library `unittest` (not pytest). Offline only; the only third-party
  dependency is PyYAML (`requirements-offline.txt`).
- Tests live in `tests/` (`test_*.py`) plus the legacy `test_router.py` at the root.
  Each test file inserts the repo root into `sys.path` and imports modules directly.
- Test names describe behaviour: `test_<what happens>_when_<condition>`.
- Errors raised to callers use `decision_providers.ProviderError` with a short English message.
- Full verification (same as `.github/workflows/verify.yml`, Python part):
  `python3 -B -m unittest -v test_router && python3 -B -m unittest discover -s tests -v && python3 -B router.py selftest`
- The Rust part (`cargo ...`) is not run by DevDesk in phase 1.

## Code review rules
- Reject a change that edits or deletes existing tests to make them pass.
- Reject changes to files outside the task's scope.
- Reject a "tests pass" claim that is not backed by the test output.
- Reject tests that only assert truthiness where the task asks for exact values.
