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

## Local installation check (2026-10-29)

Scope: the Python `route` command and the skill instructions. The native MCP output is
unchanged, so nothing here claims installation status for MCP clients.

- `python3 -B -m unittest test_router`: **35 tests pass** (31 existing + 4 new), covering
  both skill-tree layouts (`skills/<name>/` and `skills/<group>/<name>/`), case-insensitive
  name matching, missing and file roots, the `[install]` line, `meta.install_scan`,
  `--no-install-check`, duplicate names collapsing to one entry, and a machine with no
  resolvable home directory (which skips the check instead of failing the route).
- `python3 -B -m unittest discover -s tests`: **79 tests pass**, unchanged.
- `python3 -B router.py selftest`: `all checks passed`, now also asserting install
  annotation.
- On this machine the default roots resolve 110 installed skills from `~/.agents/skills`.

Measured under WSL Ubuntu (Python 3.12.3, PyYAML 6.0.1). The Windows run of the legacy suite
failed at that time on `TemporaryDirectory` cleanup (`WinError 32`, an open `skills.db`) and
two CLI artefact tests; both causes were traced and fixed later the same day — see "Windows
suite cleanup" below, which describes the current state. `selftest` passed on Windows Python
3.11.16 at the time of this measurement.

No paid provider request was made for this change: routing output is exercised with a
patched scorer, so the new flags and markers are verified without inference spend.

## Windows suite cleanup (2026-10-29)

The offline suite failed on Windows with 5 failures and 24 errors that were environmental,
not behavioural. Both causes are fixed at the source rather than suppressed:

- **Unclosed SQLite handles.** `with sqlite3.connect(path) as db:` commits at block exit but
  never closes the connection, so `skills.db` stayed locked and `TemporaryDirectory` cleanup
  raised `PermissionError: [WinError 32]`. `cmd_index`, the selftest fixture, the test suite
  and the three smoke scripts now use `contextlib.closing(...)` around the connection while
  keeping the commit/rollback context manager.
- **Ambient provider settings.** The shell in this environment exports `SKILL_ROUTER_PROVIDER`
  and `TYPESAFE_API_KEY`, so tests that do not pass `--provider` exercised a different code
  path, produced a real model name in artifacts and returned exit 0 where the contract
  requires 1. The test cases now clear `SKILL_ROUTER_*`, `JEV_*`, `PERPLEXITY_*` and
  `TYPESAFE_*` for their duration and restore them afterwards.

Result on the same machine, Windows 11 / Python 3.11.16, with the ambient variables present:

- `python -m unittest test_router`: **35 tests pass** (35 at this point; the UTF-8 regression
  test recorded below makes 36).
- `python -m unittest discover -s tests`: **79 tests pass**.
- `python router.py selftest`: `all checks passed`.
- `python -m py_compile router.py test_router.py scripts/*.py`: clean.

The `ignore_cleanup_errors=True` workaround added earlier to the new test class was removed
once the handles were closed, so a future leak fails the suite instead of being hidden.

Functional checks on the same Windows host, with the inherited `PYTHONPATH` cleared:

- `router.py stats` reads the live 26,013-row index (15,544 unique).
- `router.py index --sources <2 repos> --db <temp>` completes: 21 discovered, 21 parsed,
  0 fetch/parse failures — the path the UTF-8 fix unblocked.
- A real `router.gh_api("repos/King4s/jev-skill-router")` call returns the repository object,
  so the subprocess decode works against live GitHub, not only the fixture.
- `scripts/eval_shortlist.py --help` and `scripts/rapport.py --help` start cleanly.
Linux (WSL, Python 3.12.3) still reports 35 + 79 passing tests and a clean selftest.

### GitHub JSON encoding (2026-10-29)

`gh_api` now pins `encoding="utf-8"`. Without it, `text=True` decodes with the legacy
Windows code page and raises `UnicodeDecodeError` on the first non-ASCII `SKILL.md` path in
a repository tree, which aborted `index`. The offline regression test drives the real
subprocess with a UTF-8 payload while the client's default is cp1252, so it fails on the old
behaviour and passes on the fix, on any platform.

Counts after this change: `test_router` **36 tests pass**, `discover -s tests` **79 pass**,
`selftest` clean, on Windows 11 / Python 3.11.16 and on Linux (WSL, Python 3.12.3).

