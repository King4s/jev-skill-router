# Optional Mefi Studio integration plan

Status: proposed integration, prepared on 2026-10-10. This document specifies future
work in the router and Mefi Studio. It does not describe an already shipped MCP
server, installer, or Studio integration.

## Goal and scope

Let Studio optionally prepare relevant skills before a coding task starts:

**Task → decision maker like Jev recommends skills → selected skills are retrieved
and checked → Studio loads the accepted instructions → the agent works.**

The user can select Jev, Perplexity Decisions, or both. Routing remains separate from
the coding harness and its model. Changing the decision maker does not change which
agent writes the code.

The router's CLI is the foundation. An MCP adapter makes recommendations available
to Studio; a separate preparation service and host hook complete automatic retrieval
and activation. Merely adding the connector does not install skills or make Studio
load them before every task.

All configuration labels, documentation, logs, examples, and implementation comments
for this integration should be in English.

## Verified integration points

The Studio baseline inspected for this plan is upstream commit
`b73a22e854ea6861b8079b8a362dd344bed2db21`. Recheck these entry points against the
target Studio revision before implementation; this is a `main` source inspection,
not a guarantee about a particular downloadable release.

| Existing capability | Consequence for the proposed integration |
|---|---|
| Team › Connectors supports stdio and Streamable HTTP, validates tool names up to 48 characters, and limits MCP tools to 16 per role. Resources, sampling, elicitation, and OAuth login are unsupported. | Start with a local stdio adapter exposing two short tool names. Return tool results rather than MCP resources. |
| OpenCode, Claude Code, and Codex receive Studio's per-run MCP bridge; Grok and Antigravity do not. | First verify optional routing with the three supported bridges. Host-prepared prompt injection can support other harnesses later without promising them MCP access. |
| Skills have separate usage settings for Chat, Agents, and Builders. Skills do not grant tool permissions. | Enable the integration for Builders first. Additional role access remains an explicit setting. |

Sources: [Studio connectors and coding workers](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/docs/agent-tools.md#connectors-mcp-servers),
[worker bridge](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/scripts/agent-tools-mcp.cjs).

Studio's `spawnNextJob` in `main.cjs` assembles builder instructions with
`agentAddons.instructions`, subtracts their length from `EXECUTOR_PROMPT_MAX`
(24,000 characters), and passes the remaining budget to
`executorCore.workerPrompt`. Preparation belongs before this assembly. It must
also respect the dispatcher's task ownership and cancellation checks.
[Host prompt assembly](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/main.cjs#L21150),
[prompt builder](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/scripts/executor-core.cjs#L173).

The selected and always-on skill path has an eight-skill, 16,000-character budget.
`use_skill` has its own loading limit. The automatic catalog also has count and
description limits, so placing a skill on disk does not guarantee that it will be
offered or loaded. Reuse the existing counting rules and add an explicit per-task
bundle rather than changing global skill usage settings.
[Skill assembly](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/scripts/agent-addons.cjs#L103),
[skill limits](https://github.com/nateecho32-stack/mefi-studio/blob/b73a22e854ea6861b8079b8a362dd344bed2db21/scripts/skill-use.cjs#L33).

## User controls

The feature is **disabled by default**. Existing projects keep their current worker
behavior without installing the router or configuring provider credentials.

Proposed project settings, with optional per-task overrides:

| Setting | Initial behavior |
|---|---|
| Enable automatic skill routing | Off |
| Decision maker | `jev`, `perplexity`, or `both`; `both` automatically uses the available provider when one fails |
| Operation | Recommend only, or prepare and activate |
| Allowed skill sources | User-configured repositories and paths |
| Maximum additional skills | Three initially; within the remaining Studio limits |
| Score/confidence policy | Configurable thresholds, tested against representative tasks |
| Routing unavailable | Continue with the existing configured skills, or hold for resolution; successful degraded routing continues with its recommendations |
| Revision updates | Follow the configured source trust policy; never silently replace an active bundle |

Studio's provider setting maps to the CLI's `--provider jev|perplexity|both`.
`SKILL_ROUTER_PROVIDER` supplies the CLI default, which is `jev`. Model overrides
map to `--jev-model` / `JEV_MODEL` and `--perplexity-model` /
`PERPLEXITY_DECISION_MODEL`.

Credentials stay on the device in the existing connector secret/environment
mechanism. Jev needs `TYPESAFE_API_KEY`; Perplexity needs `PERPLEXITY_API_KEY`; `both`
needs at least one usable provider credential. Missing or invalid credentials and
model configuration are reported per provider while the other is used. Neither
key belongs in exported team presets, repositories, task
prompts, process command arguments, or recommendation output. The setup view shows
which providers receive the sanitized task brief and candidate metadata.

Connector approval and skill-source trust are different controls. Reuse Studio's
connector approval behavior. For skills, support automatic use of already trusted
sources within a configured policy, and review only material outside that policy.
Honor explicit authorization already given by the user; do not require repeated
approval for the same authorized preparation.

## Decision-maker contract

The shortlist is generated once. In `both` mode, attempt configured, usable
providers concurrently against a common task state, instructions, and four-level
rubric. If one is unavailable or errors, use the other automatically. A provider
that fails a later batch keeps its earlier valid observations but receives no
further requests; the other continues over the full shortlist. Explicit `jev` and
`perplexity` modes require the selected service and remain strict.

Perplexity Decisions provides ordered `score` answers with probabilities and
confidence, which can be validated against the router's common score contract.
[Perplexity Decisions quickstart](https://docs.perplexity.ai/docs/decisions/quickstart#score-a-level-on-an-ordered-rubric).

For candidates with valid answers from both providers:

- Aggregate score: `(jev_score + perplexity_score) / 2`.
- Aggregate probability for each level: the equal arithmetic mean of the two
  validated probabilities for that level.
- Keep each provider's score, confidence, probabilities, model, and request metadata.
- Expose `score_disagreement` as the absolute difference between the provider scores.
- If a top-level confidence is needed, use the minimum provider confidence and label
  it `confidence_kind: minimum_provider_confidence`. This is a selection policy,
  not a calibrated probability that the combined result is correct.
- Label the candidate `aggregation: equal_mean` and list both `used_providers`.

For a candidate with only one valid answer, use that answer's score and
probabilities unchanged, label `aggregation: single` and
`confidence_kind: provider_reported`, and list the contributing `used_providers`.
Set `score_disagreement` to `null`: disagreement cannot be measured from one answer.
Preserve the unavailable, failed, or invalid provider's reason without fabricating
its score. Reject the candidate only when neither answer is valid.

The Studio client consumes a versioned result containing the requested `provider`
mode, `used_providers`, rubric version, candidate identifiers, ranked results,
rejected results, and per-provider status/error and request metadata. The route's
`status` distinguishes `complete`, `degraded`, and `unavailable`. `degraded` means
valid recommendations are available with incomplete provider coverage: Studio
continues preparation and shows which provider was used and why the other did not
contribute. It must not treat successful fallback as an overall routing failure.

When no provider supplies any valid ranking, routing is `unavailable` and Studio
follows its continue/hold policy. The CLI exits nonzero and still writes structured
rejections and provenance when `--out` is supplied. The Studio client validates
that every shortlisted candidate is accounted for. Provider confidence is not
assumed to be calibrated equally across services.

## Preparation and execution

1. **Prepare a bounded task brief.** Include the goal, stack, acceptance criteria,
   relevant constraints, and builder role. Apply Studio's outbound secret filter.
   Do not send the whole repository. Run routing once per material task version.
2. **Request recommendations.** The MCP adapter calls the router's provider-neutral
   routing functions. Accept both complete and degraded recommendations, showing
   the contributing providers and fallback reasons. Keep indexing outside the
   task's synchronous startup path.
3. **Resolve immutable sources.** The current index stores metadata, branch-based
   links, and a frontmatter blob cache. Extend the integration manifest with the
   source repository, repository-relative skill path, exact commit, and content
   hashes. A cached frontmatter blob hash alone does not pin supporting files.
4. **Retrieve the required files.** Fetch the complete `SKILL.md` and declared local
   supporting files from that same commit into staging. Enforce file count, total
   bytes, time, allowed source, and relative path limits. Refuse traversal,
   symlinks escaping the bundle, and arbitrary model-supplied download URLs.
5. **Validate before activation.** Parse the skill, verify hashes and source policy,
   inspect instructions, scan when configured, and check required scripts/tools.
   Do not execute downloaded scripts or install dependencies during validation.
   Unsupported external references and missing dependencies yield an explicit
   unavailable status; a scanner result does not establish complete safety.
6. **Create a run-specific bundle.** Store accepted files and a manifest in a
   private Studio cache. Expose their absolute local paths to the worker so relative
   script/reference paths can be resolved. Publish the bundle atomically. Do not
   overwrite project or user skills, and do not create global always-on settings.
7. **Fit and inject instructions.** Preserve explicitly selected and invoked skills
   first. Deduplicate by source/version identity, avoid name collisions, then fit
   recommended skills in score order into the remaining count, skill, and total
   prompt budgets. Skip whole instructions with a recorded reason; never truncate
   essential steps. Record what actually reached the prompt, not merely what was
   recommended or downloaded.
8. **Launch and verify.** Attach required tools separately through the existing
   worker policy. Recommendations do not grant permissions. Studio keeps its
   current scheduling and acceptance checks; the decision maker does not decide
   that the code task is complete.

The preparation hook receives the run ID, task version, captured settings, active
project identity, and cancellation signal. After every asynchronous boundary it
rechecks that the project and task claim still belong to the run. A canceled task
or superseded task brief cannot acquire a late bundle or launch a worker.

## Cache, history, and failure behavior

Use separate caches for recommendation results and immutable skill content. A
recommendation cache key includes the sanitized task hash, index generation,
candidate metadata revisions, rubric/prompt versions, selected provider mode,
provider models, and selection/trust policy version. A cached degraded result keeps
its original provider coverage and error status visible; it must not prevent a new
request after previously unavailable provider configuration becomes usable. A
content cache key includes
repository, commit, path, and file hashes. Revalidate policy before using cached
content. A changed provider, source revision, task, or policy invalidates the
corresponding selection.

Task attempt history records recommendation and preparation IDs, requested provider
mode, route status, used providers, per-provider results and errors, per-candidate
aggregation, rejection/skip reasons, resolved versions, validation outcome,
loaded instruction hashes, cache use, latency, and verification result. Store
request IDs and usage only when supplied; unknown cost remains unknown. Keep keys
and raw private task text out of routine logs.

Preparation has a cancellable overall deadline below Studio's connector call
timeout, bounded retries, and a concurrency limit. The host must pass that deadline
through to provider requests rather than nesting a long CLI timeout inside the MCP
timeout. Rate-limit backoff stops at the overall deadline.

| Failure | Result |
|---|---|
| In `both`, one provider has missing/invalid configuration or a request error | Use the other provider automatically. Preserve valid earlier answers and stop further calls to the failed provider. Show degraded status when ranking remains available; continue preparation. |
| In `both`, a candidate has only one valid answer | Use the valid answer with single-provider provenance; disagreement is unavailable. Reject only when neither answer is valid. |
| No valid ranking, missing index, malformed MCP result, or overall routing timeout | Report routing unavailable. Follow the selected continue/hold policy; preserve rejection/error provenance. Explicit single-provider modes do not switch services. |
| A candidate cannot be retrieved, fails validation, or lacks a dependency | Exclude it with a reason; continue preparing the remaining candidates. |
| Accepted skill exceeds remaining budgets | Keep existing selected skills and omit the recommendation; report the budget reason. |
| Task canceled, project switched, or claim released | Cancel preparation, discard unpublished staging, and prevent late activation. |
| Changed trust policy or revoked source | Revalidate before a new run; quarantine affected cache entries. |

Degraded routing with usable recommendations proceeds through normal retrieval,
validation, and activation, with its fallback status visible. Under the default
optional failure policy, unavailable routing does not become a
failure of the code task: the worker can still start with its existing configured
skills. Required routing uses a visible preparation hold without consuming coding
attempts or creating an unbounded retry loop. Cached results are not silently used
as an outage fallback; any explicitly enabled stale-result policy must show that
status and its age.

## Ordered implementation tasks

Each task should fit a focused change of roughly one to five implementation/test
files. Proposed module names below are new components, not claims about existing
Studio APIs. Follow the target repositories' test and contribution conventions.

### Phase 1: recommendations through MCP

**Task 1 — Define and test the MCP adapter contract.** Router repository; depends
on the multi-provider CLI.

- Acceptance: expose only `route_skills` and `router_status`; enforce the provider
  enum, bounded inputs, structured results, and cancellation/deadline contract.
- Acceptance: stdio stdout contains only MCP messages; diagnostic output goes to
  stderr. Index refresh is a separate operator command.
- Acceptance: fixtures prove all three modes, automatic fallback in `both`,
  per-candidate single/equal-mean provenance, and rejection only without a valid
  answer. Explicit single-provider modes stay strict.
- Acceptance: missing/invalid provider configuration, later-batch failure, and
  unavailable routing keep structured status/error metadata and candidate counts.

Verification: protocol client tests with mocked providers, including malformed
JSON, cancellation, one-provider and both-provider errors, and a failed selected
provider in explicit single-provider mode. Likely files: a new MCP entry
point, router service boundary, and adapter tests. Start with stdio; add Streamable
HTTP only if remote deployment is required.

**Task 2 — Connect a recommendations-only pilot.** Studio configuration/docs;
depends on Task 1.

- Acceptance: Team › Connectors can review, test, and enable the adapter; both tool
  names survive discovery and remain within the role's 16-tool allocation.
- Acceptance: Builders can request recommendations with each provider mode;
  nothing is installed or automatically activated.
- Acceptance: one usable credential in `both` returns readable degraded
  recommendations; no usable provider and oversized results produce readable
  errors. Normal output is bounded below the worker bridge's text limit.

Verification: a local pilot with OpenCode, Claude Code, and Codex; captured fixture
output verifies provider provenance. Likely files: integration instructions and
connector/bridge tests. Checkpoint: recommendation transport works independently
of automatic preparation.

### Phase 2: optional validated task bundles

**Task 3 — Add immutable skill retrieval.** Router preparation service; depends on
Task 1.

- Acceptance: manifest resolves the exact commit and hashes the complete skill
  and each supporting file, rather than trusting mutable branch URLs.
- Acceptance: allowed-source, path, file count, byte, and deadline rules apply to
  retrieval; interrupted staging cannot become an active bundle.
- Acceptance: files are cached without executing third-party code or changing
  existing project/user skills.

Verification: fixtures for a changing branch, mismatched hash, missing file,
traversal, escaping symlink, partial download, and cache reuse. Likely files: new
retrieval/manifest module, fixture data, and focused tests.

**Task 4 — Add validation and source policy.** Preparation service; depends on
Task 3.

- Acceptance: policy distinguishes trusted automatic use, review-required sources,
  and blocked sources; existing authorization is preserved.
- Acceptance: missing tools, unsafe content, scanner failure, and unsupported
  references have explicit outcomes without running the skill's scripts.
- Acceptance: policy changes invalidate earlier acceptance before the next run.

Verification: policy and scanner-adapter fixtures, including scanner unavailable
and revocation after caching. Likely files: policy module, validation adapter, and
tests. Checkpoint: only policy-accepted immutable bundles can be published.

### Phase 3: Studio preparation before dispatch

**Task 5 — Add the disabled-by-default settings.** Studio; depends on Task 2.

- Acceptance: existing configuration migrates to routing off; project and task
  overrides resolve predictably without changing global skill usage settings.
- Acceptance: English controls expose mode, provider/model selection, source
  policy, limits, and continue/hold behavior; credentials remain device-local.
- Acceptance: enabling routing without a ready approved connector shows an
  actionable preparation status. In `both`, one usable provider is sufficient;
  the setup view reports skipped providers and permits configuration of the other.

Verification: settings normalization/migration and UI tests. Likely files:
settings module, project settings UI, and focused tests.

**Task 6 — Prepare and inject per-task skills.** Studio; depends on Tasks 4 and 5.

- Acceptance: a new preparation module is called before `spawnNextJob` assembles
  builder instructions; settings and task versions are captured per run.
- Acceptance: explicit skills retain priority, deduplication is deterministic,
  limits include the entire assembled prompt, and every excluded skill has a reason.
- Acceptance: canceled/released claims and project switches cannot attach late
  bundles; disabling routing follows the original launch path.

Verification: executor tests with concurrent tasks, cancellation during download,
an oversized bundle, and fixtures for each supported harness. Likely files:
new preparation module, the narrow `main.cjs` hook, `agent-addons.cjs`, and focused
tests. Checkpoint: one enabled task starts with exactly its validated skill bundle;
an adjacent disabled task receives no router instructions.

### Phase 4: operational readiness

**Task 7 — Add provenance and bounded recovery.** Studio; depends on Task 6.

- Acceptance: attempt records show requested mode, route status, used providers,
  per-candidate aggregation, recommendations, per-provider scores/confidence and
  errors, revisions, cache decisions, loaded hashes, and failure/skip reasons.
- Acceptance: continue/hold policies, deadlines, and bounded retries behave as
  documented without consuming coding attempts for preparation failures.
  Degraded routing continues with available recommendations and visible fallback.
- Acceptance: no credential or private task text appears in routine logs, exported
  presets, or command arguments.

Verification: fake clocks and failure-injection tests for provider outages,
timeouts, corrupt cache entries, and trust-policy changes. Likely files:
preparation module, attempt history integration, and tests.

**Task 8 — Validate the pilot and rollback.** Both repositories; depends on Task 7.

- Acceptance: end-to-end fixtures cover off, Jev, Perplexity, both, recommend-only,
  activate, single-provider fallback in both directions, invalid candidate answers,
  later-batch failure, and both-provider unavailability with the intended outcome.
- Acceptance: switching the feature off restores the previous dispatch behavior
  immediately for future runs, with no router network calls or cached instructions.
- Acceptance: publish installation, provider configuration, budget behavior, and
  removal instructions, identifying the Studio revision tested.

Verification: targeted upstream executor/skills/connector suites plus a real local
pilot. Paid live provider checks are separate from offline tests and use configured
authorized credentials. Release to opt-in users first; compare useful-skill recall,
startup latency, rejection rate, and task verification outcomes before broadening
availability.

## Rollback and completion criteria

The project switch disables routing for future runs. Existing runs retain their
captured bundle unless canceled. Connector removal stops future adapter use; cache
cleanup removes only integration-owned files after checking that no active run
references them. Existing manually configured skills remain usable.

This integration is ready when an enabled task can use any of the three decision
maker modes, receives only validated reproducible instructions, preserves Studio's
permissions and acceptance checks, explains every failure, and can be disabled
without affecting the original task workflow. The Studio changes remain future
work; implementing router provider selection alone does not satisfy these criteria.
