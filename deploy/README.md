# Internal deployment

The native binary supports stdio for local clients and authenticated, stateless
Streamable HTTP for shared internal clients. Runtime code/data must not depend
on an operator's home directory. No public proxy or public port is required.

Native configurable providers were merged in PR #5. This release preserves the
previously deployed native exclusion guard; an upgrade must retain its configured
policy and existing authentication. A merged commit is not evidence of installation.
The dated 2026-10-11 receipts below describe the earlier Jev deployment and snapshot,
not a later binary rollout or live Perplexity success.

## Layout

| Path | Ownership | Purpose |
|---|---|---|
| `/opt/jev-skill-router/jev-skill-router` | root:root, 0755 | Tested release binary; not writable by service |
| `/var/lib/jev-skill-router/skills.db` | root:jev-skill-router, 0640 | Published snapshot; read-only to service |
| `/etc/jev-skill-router.providers.json` | root:root, 0644 | Approved non-secret runtime profiles; readable, not writable by service |
| `/etc/jev-skill-router.env` | root:root, 0600 | Provider key, MCP token and explicit configuration |
| `/etc/systemd/system/jev-skill-router.service` | root:root, 0644 | Supplied isolated unit |

Create a dedicated non-login system account `jev-skill-router`. Data directory
permissions are 0750 root:jev-skill-router; code is 0755 root:root. Systemd reads the
protected environment file before dropping privileges. The process only needs
read access to the database and profile file, not read access to the credential
file itself. Install the approved `decision-providers.json` as
`/etc/jev-skill-router.providers.json` with root ownership and mode 0644; never put
keys in it or make it writable by the runtime account.

Set these explicit values in the protected environment file, using your site's
Tailnet address and credentials rather than committing an environment file:

- `SKILL_ROUTER_DB=/var/lib/jev-skill-router/skills.db`
- `SKILL_ROUTER_BIND=<tailnet-ip>:3016`
- `SKILL_ROUTER_TOKEN=<random-secret-at-least-32-ascii-bytes>`
- `SKILL_ROUTER_PROVIDERS_FILE=/etc/jev-skill-router.providers.json`
- `TYPESAFE_API_KEY=<typesafe-key>` for the Jev primary.
- `OPENAI_API_KEY=<openai-key>` for the OpenAI standby; keep both in this protected file.
- Omit `SKILL_ROUTER_PROVIDER` for the default Jev → OpenAI policy. Set it to
  `jev`, `openai`, or `perplexity` only to force one strict provider with no fallback.

Selection occurs once at **process startup**. The runtime file defines `default`
and `profiles`; the supplied default is `jev` with `fallback: openai`. An explicit
`SKILL_ROUTER_PROVIDER` disables fallback and overrides the primary. Each profile defines `endpoint`, `model` and
`key_env`, optionally `endpoint_env` and `model_env`. Model IDs are runtime data,
not Rust defaults; only selected-chain key variables are read. Shipped Jev
opts into `JEV_API`/`JEV_MODEL`; shipped Perplexity does not implicitly use Jev
variables or Python's `PERPLEXITY_DECISION_MODEL`. Use the profile file or explicit
override names to change its endpoint/model.

Other compatible typed Decisions profiles require no code changes, but must use
the same request and Score-answer contract, not a chat API. OpenAI uses the
`openai_decisions` wire adapter; other profiles default to `systemone`. Native
fallback sends only unresolved candidates to the configured standby, uses no
retries and a 30-second attempt timeout, and never averages answers. Healthy
Jev answers never trigger an OpenAI call. HTTPS or loopback HTTP only is accepted, with
redirects disabled. A missing selected key permits stats/search/empty routes, but
nonempty ranking requires a ready provider in the selected chain. Invalid profiles fail startup.

The implicit default file is cwd `decision-providers.json`, not a path relative
to the binary. Do not rely on systemd's working directory: set the explicit file
variable above. An unreadable/missing explicit file fails startup. Only a missing
implicit cwd file enables legacy Jev using `TYPESAFE_API_KEY`, optional `JEV_API`
and a **required explicit `JEV_MODEL`** for nonempty ranking; no hardcoded model
default is supplied. A fileless non-Jev selection fails.

The [unit](jev-skill-router.service) starts `/opt/jev-skill-router/jev-skill-router --http`,
protects system/home/kernel paths, removes capabilities, bounds resources and sends
logs to journald. The database is deliberately root-owned and not a mutable
`StateDirectory`: both SQLite and filesystem permissions prevent runtime writes.

## Exact-skill exclusion policy

Set `SKILL_ROUTER_EXCLUSIONS` to the operator-managed manifest when the existing
screening loop requires filtering. Preserve its environment/drop-in during binary
upgrades; do not remove it merely to make a deployment start. The runtime never
writes policy, edits upstream sources, uninstalls skills or runs screening scripts.

The JSON contract is `{"version":1,"entries":[...]}`. Entries contain `repo`, an
exact relative `path` ending in `SKILL.md`, a 40-hex `revision`, and a 64-hex
`evidence_id`. Publication belongs to the separately approved screening process;
keep the file readable but not writable by the runtime account. Admission is
bounded to a regular file of 1 MiB and 10,000 entries. Matching follows exact
repo/path across corpus revisions and duplicate pointers to canonical IDs; a
safe sibling skill in the same repository remains eligible.

Each search/route request opens policy once, so atomic rename replaces policy for
the next request without restarting. Filtering occurs before `top` truncation,
allowing eligible candidates to refill the shortlist. Missing, unreadable, corrupt
or invalid configured policy refuses search/routing, including empty queries,
while initialization and stats remain available. Unset configuration disables the
filter explicitly; an empty valid manifest is active with zero entries. Inspect
`meta.exclusions` in successful search/route results. Filtering does not certify
all remaining skills as safe.

## First installation

1. Build and run the complete verification commands from the root README.
2. Finish `router.py index`; require zero discovery/fetch/parse failures and reconcile
   discovered paths against rows plus recorded skips. Never deploy a failed refresh.
3. Make a consistent database copy with SQLite's backup API; verify its corpus identity
   and integrity before installing. Copying a DB while a writer runs is not a backup.
4. Install only this service's account, binary, snapshot, non-secret profiles,
   protected environment and unit. Validate
   the unit with `systemd-analyze verify` before enabling it.
5. Start the unit; verify initialize, tools/list, skills_stats, skills_search and a live
   skills_route through `/mcp`. Compare the returned corpus identity to the source copy.
6. Repeat authentication/Host/Origin/body-size negatives and an authenticated request
   from a second Tailnet host. Inspect actual listener and process identity.

`systemctl is-active` or a listening socket alone is not delivery evidence. The
real provider call must preserve all candidates and disclose `meta.provider`,
`meta.requested_model`, per-batch `meta.response_models`, timing and rejections.
`meta.model` is null when batch response models are missing or differ. Existing
ranked/rejected/degraded/candidate/corpus fields are retained. Synthetic smoke
fixtures, including `scripts/provider_smoke.py`, are not an alternative to this
check; do not claim a selected operator works live without its actual receipt.

## Refresh / upgrade / rollback

Build a new snapshot with the offline indexer, outside the protected service tree.
A successful index refresh is atomic; network/parser failures retain the last good DB.
Back up the deployed binary, profiles, protected environment and snapshot before
an upgrade. Install the validated replacement under a temporary filename with
correct ownership/mode, then rename
it into place. Restart after a binary change, profile edits/reselection or selected
key/model/endpoint environment changes, and verify the live endpoint again.

For snapshot-only replacements, each request opens one read transaction: in-flight
requests retain their old coherent snapshot; later requests open the new one. Keep
SQLite sidecars out of file-only copies by using the backup API.

Rollback means restoring the exact previous binary, profiles, protected environment
and snapshot, restarting and repeating the authenticated smoke. On a first install,
disable/stop this unit to
remove the new runtime without touching other projects. Keep credentials, data and
source until the owner authorizes permanent removal.

## Automatic source-list consumption

The separate Rust `jev-skill-refresh` utility consumes the current `Skills-list.md`
from `King4s/skill-router` on GitHub. It pins the `main` commit before fetching
that one Markdown file. **It never fetches or updates executable code.** The
installed offline indexer remains the reviewed version with pinned PyYAML; the MCP
binary still contains no Python/shell launcher.

The optional [cron entry](jev-skill-router-refresh.cron) reuses the host's existing
cron daemon, daily at **03:20 local host time**. No new daemon or systemd unit is
required. A root-controlled exclusive lock rejects overlapping maintenance runs.
Native `timeout` limits the complete process group to three hours, with a 30-second
kill-after grace period, and logs termination plus the final exit status.

### Isolated installation layout

| Path | Ownership / mode | Purpose |
|---|---|---|
| `/opt/jev-skill-router/jev-skill-refresh` | root:root, 0755 | Reviewed Rust maintenance binary |
| `/opt/jev-skill-router/offline/` | root:root, 0755 | Reviewed local `router.py`, requirements and project-only Python venv |
| `/var/lib/jev-skill-router-refresh/` | root:jev-skill-refresh, 0750 | Root-controlled lock and pinned source list |
| `/var/lib/jev-skill-router-refresh/incoming/` | jev-skill-refresh:jev-skill-refresh, 0700 | Writable staging DB and temporary files |
| `/etc/jev-skill-router-refresh.token` | root:root, 0600 | Existing GitHub API credential, never stored in Git |
| `/etc/cron.d/jev-skill-router-refresh` | root:root, 0644 | Supplied cron entry, no secrets |
| `/var/lib/jev-skill-router/skills.previous.db` | Same owner/group/mode as live DB | One consistent rollback snapshot, created only on successful publication |

Create a dedicated non-login account `jev-skill-refresh`, separate from the runtime
account. Install only the reviewed batch binary and the coherent offline Python
bundle: `router.py`, its sibling modules `decision_providers.py` and
`provider_priority.py`, `provider-priority.json`, and `requirements-offline.txt`.
The sibling imports are required even for indexing; their optional routing support
does not add a provider call to the refresh batch. Install the pinned dependency
into the private offline venv, not globally. The root process reads the protected credential and launches
GitHub CLI/indexing with `setpriv`, no supplementary groups and a cleared explicit
environment. Network and YAML handling run under the unprivileged refresh account.
The account cannot write the runtime DB directory, the installed code, the curated
source list or the cron entry.

### Publication and failure behavior

Each run seeds a writable staging DB from the live read-only snapshot using
SQLite `VACUUM INTO`, preserving the blob-SHA cache. The indexer uses the pinned
source list and independently pins every listed repository revision. Publication
requires exact source/tier membership, complete per-source/path and skip accounting,
zero fetch/parse failures, nonempty usable metadata, cache/duplicate/FTS parity and
SQLite integrity. Root first makes a consistent private candidate copy, validates
that copy, and records the authority's commit as `index_meta.source_list_revision`.

A validated candidate is fsynced and renamed atomically in the live DB directory
with the original owner/group/mode. One consistent previous snapshot is retained.
The MCP process is not restarted: each later request opens the new file, while
in-flight requests retain their coherent old snapshot. An unsuccessful index or
candidate validation leaves the published DB untouched.

Diagnostics identify the failed category and manifest-matched repo/path using
bounded JSON records. Raw GitHub bodies/stdout and credential values are not
forwarded. At most 64 KiB of indexer stderr and 32 diagnostic records are accepted;
output overflow fails closed. The cron receipt is `refresh_exit_status=<status>`;
a timeout also emits the native termination message. Read journal entries tagged
`jev-skill-router-refresh`, not just the cron process's status.

The list producer's advertised weekly research is **not performed by this job**.
Daily consumption keeps the MCP index connected to published list changes, but
cannot turn an invalid list into a valid one. In particular, a listed 404 repository
blocks the full refresh; it is never silently excluded or reclassified. Correcting
the source authority is a separate owner-approved change. On 2026-10-11, both
isolated preflight and the **installed batch utility using the exact cron command**
failed at `wanghuan9/skilldock` in the then-current 109-source list. The journal recorded
`discovery_failed` with that repo and `refresh_exit_status=1`; the live DB SHA-256
remained `1e93dda087ac38ac946e95916f61d129419fcf73cebb2eedb30f67d6ecd8195b`.
The source-authority blocker was subsequently resolved with explicit owner approval
in the one-file [PR #4](https://github.com/King4s/skill-router/pull/4): only
`wanghuan9/skilldock` moved to documented `Flagged / excluded`, retaining its metadata.
The installed exact-cron-command run then **published the then-current 108-source snapshot**
on 2026-10-11 at 20:56:43 host-local time, with `refresh_exit_status=0`.
It consumed pinned authority commit `08c34ec43e26fceb9d922351b86d6b14a4ab65fb`.

All **26,596 discovered paths** are accounted for: **17,201 cached + 8,897 newly parsed +
497 missing-metadata + one exact negative fixture**, with zero fetch/parse failures.
The live DB has **26,098 source rows = 15,682 canonical records + 10,416 duplicates**.
Its snapshot identity is `8740e49f67c1a90b0e21775af75e8988b885db867520282511b88ffaa2b219b6`
and DB SHA-256 is `b37d246bd8fa81b7340c3c2cf0ae2168ae211dd0074bd88bf2ccf036f70ba22a`.
Readback confirmed exact 108-repo/tier membership, the authority commit, SQLite
integrity and the original root:jev-skill-router 0640 permissions. The consistent
previous snapshot retains the original 98-source identity and also passes integrity;
its physical file hash differs from the original because it was made with `VACUUM INTO`.

Authenticated deployed MCP wire/security smoke and real Jev ranking then passed
against the **new** identity (40 accepted candidates, `jev-1.13.0`). PID 1773473 and
restart count zero remained unchanged: actual next-request uptake was verified,
not inferred from file replacement. No other project's code changed. At the time
of this live measurement, only source-correction PR #4 had been merged; native
implementation PR #1 was still unmerged. Repository publication is separate from
these deployment receipts and does not update the installed executable or indexer.
These are successful **manual exact-cron-command** receipts, not proof that the next
scheduled 03:20 tick has already occurred.

Source counts in these receipts are historical; weekly source-list updates may
change current membership. They are not fresh verification of this feature branch.

For manual execution, use the same root batch binary and timeout/logger command
as the supplied cron entry. For a snapshot-only rollback, acquire the same refresh
lock and install a consistent copy of `skills.previous.db` under a temporary
filename, retain owner/group/mode, then atomically rename it over `skills.db`.
Verify authenticated MCP stats/search and the exact expected identity afterwards.
Do not move the only rollback copy away or copy a DB concurrently with a writer.

## Client notes

- Endpoint: `http://<tailnet-ip>:3016/mcp`; no public domain.
- Bearer header on every request; `Accept: application/json, text/event-stream`.
- MCP initialization is standard; no legacy session identifier is required.
- Use the bound IP in the URL/Host header. Aliases and reverse proxies require an
  explicit design change to the exact-Host allowlist, not disabling validation.
- Browser Origin headers are rejected deliberately; use a trusted agent client.
- Supply the token via the client's secret store/environment, not source control.
- The service has no automatic skill installer or embedding infrastructure. The optional
  daily offline refresh uses the existing cron daemon, not an MCP-side update timer.
