# Internal deployment

The native binary supports stdio for local clients and authenticated, stateless
Streamable HTTP for shared internal clients. Runtime code/data must not depend
on an operator's home directory. No public proxy or public port is required.

## Layout

| Path | Ownership | Purpose |
|---|---|---|
| `/opt/jev-skill-router/jev-skill-router` | root:root, 0755 | Tested release binary; not writable by service |
| `/var/lib/jev-skill-router/skills.db` | root:jev-skill-router, 0640 | Published snapshot; read-only to service |
| `/etc/jev-skill-router.env` | root:root, 0600 | Provider key, MCP token and explicit configuration |
| `/etc/systemd/system/jev-skill-router.service` | root:root, 0644 | Supplied isolated unit |

Create a dedicated non-login system account `jev-skill-router`. Data directory
permissions are 0750 root:jev-skill-router; code is 0755 root:root. Systemd reads the
protected environment file before dropping privileges. The process only needs
read access to the database, not read access to the credential file itself.

Set these explicit values in the protected environment file, using your site's
Tailnet address and credentials rather than committing an environment file:

- `SKILL_ROUTER_DB=/var/lib/jev-skill-router/skills.db`
- `SKILL_ROUTER_BIND=<tailnet-ip>:3016`
- `SKILL_ROUTER_TOKEN=<random-secret-at-least-32-ascii-bytes>`
- `TYPESAFE_API_KEY=<typesafe-key>`
- `JEV_API=https://api.typesafe.ai/v1/systemone`
- `JEV_MODEL=jev-latest`

The [unit](jev-skill-router.service) starts `/opt/jev-skill-router/jev-skill-router --http`,
protects system/home/kernel paths, removes capabilities, bounds resources and sends
logs to journald. The database is deliberately root-owned and not a mutable
`StateDirectory`: both SQLite and filesystem permissions prevent runtime writes.

## First installation

1. Build and run the complete verification commands from the root README.
2. Finish `router.py index`; require zero discovery/fetch/parse failures and reconcile
   discovered paths against rows plus recorded skips. Never deploy a failed refresh.
3. Make a consistent database copy with SQLite's backup API; verify its corpus identity
   and integrity before installing. Copying a DB while a writer runs is not a backup.
4. Install only this service's account, binary, snapshot, environment and unit. Validate
   the unit with `systemd-analyze verify` before enabling it.
5. Start the unit; verify initialize, tools/list, skills_stats, skills_search and a live
   skills_route through `/mcp`. Compare the returned corpus identity to the source copy.
6. Repeat authentication/Host/Origin/body-size negatives and an authenticated request
   from a second Tailnet host. Inspect actual listener and process identity.

`systemctl is-active` or a listening socket alone is not delivery evidence. The
real provider call must preserve all candidates and disclose model, timing and
rejections. Synthetic smoke fixtures are not an alternative to this check.

## Refresh / upgrade / rollback

Build a new snapshot with the offline indexer, outside the protected service tree.
A successful index refresh is atomic; network/parser failures retain the last good DB.
Back up the deployed binary and snapshot before an upgrade. Install the validated
replacement under a temporary filename with correct ownership/mode, then rename
it into place. Restart after a binary change and verify the live endpoint again.

For snapshot-only replacements, each request opens one read transaction: in-flight
requests retain their old coherent snapshot; later requests open the new one. Keep
SQLite sidecars out of file-only copies by using the backup API.

Rollback means restoring the exact previous binary and snapshot, restarting and
repeating the authenticated smoke. On a first install, disable/stop this unit to
remove the new runtime without touching other projects. Keep credentials, data and
source until the owner authorizes permanent removal.

## Automatic source-list consumption

The separate Rust `jev-skill-refresh` utility consumes the current `Skills-list.md`
from `King4s/jev-skill-router` on GitHub. It pins the `main` commit before fetching
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
account. Install only the reviewed batch binary, `router.py` and
`requirements-offline.txt`; install its pinned dependency into the private offline
venv, not globally. The root process reads the protected credential and launches
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
failed at `wanghuan9/skilldock` in the current 109-source list. The journal recorded
`discovery_failed` with that repo and `refresh_exit_status=1`; the live DB SHA-256
remained `1e93dda087ac38ac946e95916f61d129419fcf73cebb2eedb30f67d6ecd8195b`.
The unchanged native process passed authenticated MCP smoke and real Jev ranking
(40 accepted candidates, model `jev-1.13.0`). Daily cron consumption is installed;
**a fresh live publication remains blocked**, not complete. No source was excluded,
no other project's code changed, and no `main` merge was performed. A manually
exercised cron command does not prove the next scheduled tick has already run.

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
