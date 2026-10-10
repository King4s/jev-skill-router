# Validation record

Date: 2026-10-10. Runtime: Python 3.13 on Windows.

## Offline checks

- `python -m unittest discover -s tests -v`: **46 tests pass**, covering provider transport, response
  validation, all three routing modes, concurrent calls, batching, metadata,
  missing credentials, malformed answers, model precedence, and CLI compatibility.
  Report subprocess tests cover UTF-8 output and legacy Windows CP1252 files.
- `python router.py selftest`: existing frontmatter, dedupe, source parsing,
  retrieval and score-contract checks.
- `python -m py_compile router.py decision_providers.py scripts/eval_shortlist.py scripts/rapport.py`.
- `python router.py route --help`: documented provider and model options exist.
- `git diff --check`.

Provider HTTP tests use fixtures and a loopback redirect test. They do not call
paid services. The existing retrieval benchmark was not rerun: its real skill
index is not in a fresh clone, and retrieval behavior was not changed.

Independent review identified HTTP protocol exceptions, deeply nested JSON, and
Windows report encoding as edge cases. Regression tests were added before the
fixes; all findings were resolved and the reviewer found no remaining blockers.

## Live provider smoke check

One request per provider was made with configured credentials. Both received the
same synthetic PDF-processing task and two public skill descriptions: a PDF
skill and an unrelated Minecraft-server skill. No private project files were sent.

| Provider | Requested model | Returned model | Reported input/output tokens |
|---|---|---|---|
| Jev | `jev-latest` | `jev-1.13.0` | 636 / 38 |
| Perplexity Decisions | `pplx-decider-v1.1-27b` | `pplx-decider-v1.1-27b` | 473 / 2 |

Both providers' answers passed the shared score contract. Combined mode accounted
for both candidates with two ranked records and no rejected records. The PDF
skill's combined score was about 2.938; the unrelated skill's about 0.000186.
This confirms request/response interoperability for one small sample. It does not
measure ranking quality, corpus-wide recall, confidence calibration, rate-limit
behavior, or large-request performance.

## Studio status

The [Studio integration plan](studio-integration-plan.md) is a design document.
No Studio source was changed and no MCP server was implemented in this change.
End-to-end installation, automatic skill preparation, and Studio worker loading
remain acceptance gates for the planned integration.
