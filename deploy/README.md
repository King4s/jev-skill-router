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

## Client notes

- Endpoint: `http://<tailnet-ip>:3016/mcp`; no public domain.
- Bearer header on every request; `Accept: application/json, text/event-stream`.
- MCP initialization is standard; no legacy session identifier is required.
- Use the bound IP in the URL/Host header. Aliases and reverse proxies require an
  explicit design change to the exact-Host allowlist, not disabling validation.
- Browser Origin headers are rejected deliberately; use a trusted agent client.
- Supply the token via the client's secret store/environment, not source control.
- The service has no automatic installer, update timer or embedding infrastructure.
