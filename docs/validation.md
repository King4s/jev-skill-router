# Validation record

Date: 2026-10-10. Runtime: Python 3.13 on Windows.

## Offline checks

- `python -m unittest discover -s tests -v`: **74 tests pass**, covering provider transport, response
  validation, all three routing modes, ordered failover, batching, metadata,
  missing credentials, malformed answers, model precedence, and CLI compatibility.
  Report subprocess tests cover UTF-8 output and legacy Windows CP1252 files.
  Fallback tests cover unavailable configuration, errors in either provider,
  malformed envelopes, invalid candidate answers, preserved earlier batches,
  complete failure artifacts, and actual-provider labels in the console/report.
  Priority tests verify higher measured accuracy wins, cost breaks exact ties,
  unknown metrics stay unknown, model mismatches ignore stale measurements,
  and healthy preferred answers cause no standby request. Fallback requests contain
  only unresolved candidate IDs and automatic mode does not retry before failover.
- `python router.py selftest`: existing frontmatter, dedupe, source parsing,
  retrieval and score-contract checks.
- `python -m py_compile router.py decision_providers.py provider_priority.py scripts/eval_shortlist.py scripts/rapport.py`.
- `python router.py route --help`: documented provider and model options exist.
- `git diff --check`.

Provider HTTP tests use fixtures and a loopback redirect test. They do not call
paid services. The existing retrieval benchmark was not rerun: its real skill
index is not in a fresh clone, and retrieval behavior was not changed.

Independent review identified HTTP protocol exceptions, deeply nested JSON, and
Windows report encoding as edge cases. Regression tests were added before the
fixes; all findings were resolved and the reviewer found no remaining blockers.

After the priority policy was revised, both mode was tested with injected failures:
the preferred provider is called first; an unusable answer or provider failure
uses the standby for unresolved candidates, with its provider identified. A valid
preferred answer remains unchanged. No valid observation remains unavailable.
Explicit single-provider selections still fail when their selected service fails.
These failure tests are offline and do not deliberately disrupt a live service.

## Initial live provider interoperability check

One request per provider was made with configured credentials. Both received the
same synthetic PDF-processing task and two public skill descriptions: a PDF
skill and an unrelated Minecraft-server skill. No private project files were sent.

| Provider | Requested model | Returned model | Reported input/output tokens |
|---|---|---|---|
| Jev | `jev-latest` | `jev-1.13.0` | 636 / 38 |
| Perplexity Decisions | `pplx-decider-v1.1-27b` | `pplx-decider-v1.1-27b` | 473 / 2 |

Both providers' answers passed the shared score contract. The original paired
smoke check accounted for both candidates with two ranked records and no rejected
records. This preceded the priority-first policy; automatic mode no longer combines
two scores for the same candidate.
This confirms request/response interoperability for one small sample. It does not
measure ranking quality, corpus-wide recall, confidence calibration, rate-limit
behavior, or large-request performance.

## Live priority-first check

The same synthetic task and two public candidates were scored in the final `both`
mode. The result was `complete`, with priority Perplexity then Jev and only
Perplexity used. Perplexity made one call, reporting 473 input tokens and two
output tokens; Jev made zero attempts and remained `not_used`. Both candidates
passed validation. The PDF skill scored about 2.935 and the unrelated skill about
0.000372. This verifies that a healthy preferred provider does not trigger a
second paid call. Provider-failure paths remain covered by injected offline tests.

The initial priority profile records external Decision Bench evidence (1,071
single-choice cases), with a corpus hash, observation date, models and cost basis.
It is a provisional starting order, not measured skill-router accuracy. The
profile can be replaced by task-specific accuracy and complete-request costs.

## Studio status

The [Studio integration plan](studio-integration-plan.md) is a design document.
No Studio source was changed and no MCP server was implemented in this change.
End-to-end installation, automatic skill preparation, and Studio worker loading
remain acceptance gates for the planned integration.
