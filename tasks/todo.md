# Work checklist

- [x] Inspect repository, existing commands and official provider documentation.
- [x] Run the existing offline selftest and define provider/result contracts.
- [x] Add failing behavioral tests for transport, validation, modes and CLI.
- [x] Implement provider adapters with isolated credentials and bounded retries.
- [x] Implement selectable providers, batching and transparent provider provenance.
- [x] Update English usage, skill instructions and change notes.
- [x] Write the optional Studio integration plan with acceptance criteria.
- [x] Run full offline verification and independent code review; resolve findings.
- [x] Verify real Jev and Perplexity responses with a synthetic task.
- [x] Prepare reviewed commits for delivery of the code and plan.
- [x] Make both mode continue with the other provider when one is unavailable or errors.
- [x] Cover partial batches, candidate-level fallback, and complete failure artifacts.
- [x] Update report labels and the optional Studio plan to use the fallback policy.
- [x] Prefer higher measured accuracy, using measured cost to break exact ties.
- [x] Call the standby only for unresolved candidates, preserving valid preferred answers.
- [x] Verify priority profiles and a live preferred-only request with no standby calls.
