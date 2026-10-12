# AI Agent Skills – curated list

A curated overview of AI-agent skill projects: SKILL.md-based Agent Skills (Claude Code / Anthropic), Cursor rules and plugins, Codex/OpenAI skills, awesome lists, marketplaces, registries and tooling.

- **Last updated:** 2026-10-12
- **Updated:** weekly (automated research, verified against the GitHub API)
- ★ = GitHub stars at time of update. "Updated" = last push (UTC).
- Abandoned (~9+ months without a push), empty and suspicious repos are left out. Star counts in this space are very high; they are reported as shown, not verified as organic.

## Changes this week

- **Added (official):** googleworkspace/cli, browserbase/skills, mongodb/agent-skills, redis/agent-skills, alibaba/open-code-review.
- **Added (collections):** nexu-io/open-design, tt-a1i/archify, career-ops-hq/career-ops, ayghri/i-have-adhd, cathrynlavery/diagram-design, Yuan1z0825/nature-skills, virgiliojr94/book-to-skill, OthmanAdi/planning-with-files.
- **Added (lists):** VoltAgent/awesome-codex-subagents.
- **Stars/dates refreshed.** Biggest ★ movers: mattpocock/skills (+10.3k), heygen-com/hyperframes (+4.3k), affaan-m/ECC (+4.3k), cloudflare/security-audit-skill (+4.0k), addyosmani/agent-skills (+3.9k).
- **Revived:** Orchestra-Research/AI-Research-SKILLs (push 2026-10-11, after last activity 2026-06-16).
- **Flagged:** wanghuan9/skilldock still 404 (rechecked 2026-10-12); numman-ali/openskills ~8.8 months stale.
- **Removed:** none.

## 1. Official repos (vendors and orgs)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 180,569 | 2026-10-09 | Reference Agent Skills repo (docx/pdf/pptx/xlsx, frontend-design, skill-creator, claude-api) |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 150,270 | 2026-10-11 | Claude Code; `plugins/` holds the official example plugins |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 37,707 | 2026-10-11 | Anthropic's directory of high-quality Claude Code plugins |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 29,160 | 2026-10-11 | Plugins and skills for knowledge workers (Claude Cowork) |
| [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) | 4,628 | 2026-10-11 | Community plugin marketplace (read-only mirror) |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 39,930 | 2026-10-12 | GitHub's community instructions, agents and skills for Copilot |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 32,254 | 2026-08-28 | Vercel's official skills (React best practices, web design guidelines) |
| [openai/skills](https://github.com/openai/skills) | 28,012 | 2026-09-08 | Skills catalog for Codex |
| [openai/plugins](https://github.com/openai/plugins) | 7,404 | 2026-10-08 | OpenAI/Codex plugins |
| [huggingface/skills](https://github.com/huggingface/skills) | 11,159 | 2026-10-08 | Hugging Face skills (hf-cli, training, datasets, evals) |
| [cursor/plugins](https://github.com/cursor/plugins) | 10,944 | 2026-10-12 | Cursor plugin specification and official plugins |
| [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) | 8,474 | 2026-08-17 | Google's Agent Skills for the Stitch MCP server |
| [google/agents-cli](https://github.com/google/agents-cli) | 6,077 | 2026-10-06 | Google CLI plus skills for building and evaluating agents (ADK) |
| [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) | 4,265 | 2026-10-06 | Skills for the Gemini API and SDK |
| [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor) | 3,763 | 2026-09-01 | Gemini CLI extension for spec-driven development |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,490 | 2026-10-09 | Security research and audit skills |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | 5,043 | 2026-10-07 | Remotion's official skills |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 61,156 | 2026-10-12 | HeyGen's HTML-to-video skills |
| [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | 46,287 | 2026-10-12 | Alibaba open-source code-review tool with bundled agent skills (deterministic + LLM) |
| [larksuite/cli](https://github.com/larksuite/cli) | 17,632 | 2026-10-12 | Official Lark/Feishu CLI with many skills |
| [googleworkspace/cli](https://github.com/googleworkspace/cli) | 31,370 | 2026-10-06 | Google Workspace CLI with bundled AI agent skills (Drive, Gmail, Calendar, Docs, Sheets, Chat, Admin) |
| [microsoft/skills](https://github.com/microsoft/skills) | 3,101 | 2026-10-09 | Microsoft skills, MCP servers and AGENTS.md for its SDKs |
| [microsoft/azure-skills](https://github.com/microsoft/azure-skills) | 1,559 | 2026-10-09 | Official Azure skills plus MCP configuration |
| [microsoft/power-platform-skills](https://github.com/microsoft/power-platform-skills) | 993 | 2026-10-12 | Power Platform plugin marketplace |
| [cloudflare/skills](https://github.com/cloudflare/skills) | 3,043 | 2026-10-10 | Cloudflare skills |
| [supabase/agent-skills](https://github.com/supabase/agent-skills) | 2,767 | 2026-10-02 | Supabase skills |
| [expo/skills](https://github.com/expo/skills) | 2,763 | 2026-10-07 | Expo/EAS skills |
| [stripe/ai](https://github.com/stripe/ai) | 1,898 | 2026-10-12 | Stripe's AI toolkit (includes skills) |
| [callstackincubator/agent-skills](https://github.com/callstackincubator/agent-skills) | 1,666 | 2026-10-08 | React Native skills from Callstack |
| [browserbase/skills](https://github.com/browserbase/skills) | 3,732 | 2026-09-29 | Browserbase's official agent skills for web access and browser automation |
| [matlab/matlab-agentic-toolkit](https://github.com/matlab/matlab-agentic-toolkit) | 1,151 | 2026-10-08 | MATLAB skills for agents |
| [getsentry/skills](https://github.com/getsentry/skills) | 1,047 | 2026-10-09 | Sentry's skills |
| [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) | 917 | 2026-10-09 | AWS agent plugins and skills |
| [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | 893 | 2026-10-05 | HashiCorp skills and Claude Code plugins |
| [firebase/agent-skills](https://github.com/firebase/agent-skills) | 466 | 2026-10-10 | Firebase skills |
| [mongodb/agent-skills](https://github.com/mongodb/agent-skills) | 190 | 2026-10-10 | Official MongoDB agent skills (Atlas, schema, query, search) |
| [redis/agent-skills](https://github.com/redis/agent-skills) | 167 | 2026-09-08 | Redis' official collection of agent skills |
| [neondatabase/agent-skills](https://github.com/neondatabase/agent-skills) | 100 | 2026-10-09 | Neon Postgres skills |
| [google/skills](https://github.com/google/skills) | 21,192 | 2026-10-09 | Agent Skills for Google products and technologies |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 28,410 | 2026-09-14 | Cloudflare's multi-phase security-audit skill with verified findings |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 252,871 | 2026-10-12 | Hermes Agent with built-in SKILL.md support |

## 2. Large community collections

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 297,839 | 2026-10-10 | Skills framework and development methodology (brainstorming, TDD, debugging) |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 286,640 | 2026-10-09 | Engineering skills; most-installed source on skills.sh |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 134,906 | 2026-10-12 | UI/UX design skill for many agents |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 111,098 | 2026-10-12 | Token-saving skill plus proxy |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 105,160 | 2026-10-10 | Production-grade engineering skills |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | 100,631 | 2026-10-12 | Open-source design plugin/harness with a large SKILL.md library (prototypes, landing pages, slides) |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 94,825 | 2026-10-11 | Design-taste skills against generic "AI slop" |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | 82,190 | 2026-10-12 | Agent skill that turns ideas or codebases into interactive architecture diagrams |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 79,968 | 2026-10-12 | Design-language skill |
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | 74,086 | 2026-10-12 | AI job-search agent skills: board scan, CV scoring, resume/cover letters, interview prep |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 54,261 | 2026-10-08 | Marketing, CRO and SEO skills |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | 50,882 | 2026-10-10 | Editorial diagram-design skill (44 types, HTML/SVG) for Claude Code, Codex, Cursor, Copilot |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 48,458 | 2026-10-05 | Large library of science skills |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | 47,482 | 2026-10-11 | Academic/research skills for Nature-style writing, figures and literature search |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 45,453 | 2026-10-11 | Skills for designers and engineers |
| [wshobson/agents](https://github.com/wshobson/agents) | 40,436 | 2026-10-12 | Plugin marketplace for Claude Code, Codex, Cursor, OpenCode and Copilot |
| [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 34,588 | 2026-10-12 | Turns technical book PDFs into ready-to-use Claude Code skills |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 28,031 | 2026-08-30 | 380+ skills, agents and commands |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27,400 | 2026-10-10 | Persistent file-based planning for coding agents (crash-proof plans, session recovery) |
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 26,904 | 2026-10-10 | 100+ product-management skills |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 26,555 | 2026-09-10 | Popular Chinese skills collection |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | 25,483 | 2026-10-11 | Compound Engineering plugin (Claude Code, Codex, Cursor) |
| [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 13,461 | 2026-10-11 | AI research and ML-engineering skills |
| [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) | 11,832 | 2026-10-03 | 67 full-stack skills |
| [Mindrally/skills](https://github.com/Mindrally/skills) | 274 | 2026-10-08 | 255+ skills converted from Cursor rules |
| [Jahrome907/minecraft-agent-skills](https://github.com/Jahrome907/minecraft-agent-skills) | 174 | 2026-10-11 | Minecraft modding/server skills for Codex and Claude Code |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 277,365 | 2026-10-12 | Agent harness system (formerly everything-claude-code): skills, memory, security |
| [garrytan/gstack](https://github.com/garrytan/gstack) | 136,055 | 2026-10-12 | Garry Tan's Claude Code setup: opinionated role skills (CEO, designer, eng manager, QA) |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 63,999 | 2026-10-11 | Research skill across Reddit, X, YouTube, HN and the web |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | 56,532 | 2026-10-11 | Skill that keeps agent answers short and ADHD-friendly (stops burying the answer) |
| [blader/humanizer](https://github.com/blader/humanizer) | 55,880 | 2026-09-28 | Skill that removes signs of AI-generated writing |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 49,415 | 2026-09-15 | Obsidian skills (CLI, Markdown, Bases, Canvas) from Obsidian's CEO |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 1,440 | 2026-10-09 | 74 game-dev skills (Godot, Unity, Unreal, Phaser, three.js, Bevy) |

## 3. Awesome lists

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 76,896 | 2026-09-18 | The biggest Claude Skills list |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 55,470 | 2026-10-12 | Claude Code skills, hooks, commands and plugins |
| [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) | 53,074 | 2026-10-11 | 5,400+ OpenClaw skills, categorized |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | 47,477 | 2026-10-12 | Large skills catalog plus a local catalog tool |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 40,893 | 2026-05-30 | The canonical Cursor rules list |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 35,535 | 2026-10-11 | 1,000+ skills from official teams and the community |
| [composio-community/awesome-codex-skills](https://github.com/composio-community/awesome-codex-skills) | 16,869 | 2026-07-26 | Codex skills |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15,370 | 2026-04-28 | Claude Skills list (updates have slowed) |
| [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills) | 10,236 | 2026-09-21 | Claude Skills list |
| [VoltAgent/awesome-codex-subagents](https://github.com/VoltAgent/awesome-codex-subagents) | 6,304 | 2026-10-05 | Curated list of 130+ specialized Codex subagents |
| [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) | 6,266 | 2026-04-05 | Tutorials and skill directories |
| [libukai/awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) | 5,159 | 2026-09-04 | Agent Skills guide (Chinese/English) |
| [Prat011/awesome-llm-skills](https://github.com/Prat011/awesome-llm-skills) | 1,792 | 2026-07-14 | LLM and agent skills |
| [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins) | 1,284 | 2026-10-11 | Codex plugins and skills |
| [ccplugins/awesome-claude-code-plugins](https://github.com/ccplugins/awesome-claude-code-plugins) | 970 | 2026-08-12 | Claude Code plugins |
| [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) | 848 | 2026-08-02 | Cursor skills |
| [ZeroPointRepo/awesome-hermes-skills](https://github.com/ZeroPointRepo/awesome-hermes-skills) | 610 | 2026-10-05 | Hermes Agent skills |
| [quemsah/awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins) | 1,425 | 2026-10-12 | Automated index of Claude Code plugins with adoption metrics |
| [lawve-ai/awesome-legal-skills](https://github.com/lawve-ai/awesome-legal-skills) | 855 | 2026-10-02 | Agent Skills for legal work |

## 4. Marketplaces and registries

| Site / repo | ★ | Updated | Description |
|---|---:|---|---|
| [skills.sh](https://skills.sh) | – | – | Vercel's skills directory with install leaderboard (`npx skills`) |
| [SkillsMP](https://skillsmp.com) | – | – | Aggregator claiming 3M+ skills from GitHub; REST API and MCP server |
| [Smithery skills](https://smithery.ai/skills) | – | – | Skill registry with install counts |
| [claude-plugins.dev](https://claude-plugins.dev) ([source](https://github.com/Kamalnrf/claude-plugins)) | 563 | 2026-10-05 | Registry plus `npx claude-plugins` CLI |
| [cursor.directory](https://cursor.directory) | – | – | Cursor plugins, rules and MCP servers |
| [ClawHub](https://clawhub.ai) ([openclaw/clawhub](https://github.com/openclaw/clawhub)) | 9,502 | 2026-10-12 | OpenClaw skill and plugin registry |
| [davepoon/buildwithclaude](https://github.com/davepoon/buildwithclaude) | 3,620 | 2026-10-12 | Hub for skills, plugins and marketplaces |
| [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) | 1,292 | 2026-10-10 | Curated Claude Code marketplace |
| [numman-ali/n-skills](https://github.com/numman-ali/n-skills) | 1,050 | 2026-09-12 | Curated marketplace (Claude Code, Codex, openskills) |
| [LinklyAI/best-skills](https://github.com/LinklyAI/best-skills) | 638 | 2026-10-12 | Daily Top 100 skills ranking |
| [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) | 513 | 2026-07-14 | Community-vetted marketplace |
| [skilld-dev/skilld](https://github.com/skilld-dev/skilld) | 324 | 2026-10-10 | Open-source alternative to skills.sh |
| [jeremylongshore/tons-of-skills-marketplace](https://github.com/jeremylongshore/tons-of-skills-marketplace) | 2,831 | 2026-10-12 | Model-agnostic skills marketplace with adapters for several agents |

## 5. Tooling (spec, CLI, convert, validate, security)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | 33,859 | 2026-10-09 | `npx skills`, the open install CLI |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | 32,572 | 2026-10-12 | CLI to configure Claude Code (skills, agents, hooks) |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) ([agentskills.io](https://agentskills.io)) | 26,054 | 2026-08-09 | Open Agent Skills spec plus `skills-ref validate`; ~50 supporting clients |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | 24,871 | 2026-09-10 | The AGENTS.md standard |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 19,980 | 2026-10-10 | Security scanner for skills |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 18,248 | 2026-10-06 | Optimizer/trainer for natural-language skills |
| [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | 15,134 | 2026-09-30 | Turns docs sites, repos and PDFs into skills |
| [numman-ali/openskills](https://github.com/numman-ali/openskills) | 10,779 | 2026-01-18 | Cross-agent skills loader (⚠️ no push for ~8.8 months) |
| [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | 3,265 | 2026-10-09 | A skill that builds and improves your other skills |
| [intellectronica/ruler](https://github.com/intellectronica/ruler) | 2,943 | 2026-09-30 | Same rules for all coding agents |
| [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) | 2,592 | 2026-10-09 | Security scanner for skills |
| [rohitg00/skillkit](https://github.com/rohitg00/skillkit) | 1,548 | 2026-06-02 | Install, translate and share skills across agents |
| [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) | 1,514 | 2026-10-12 | Syncs rules and skills between agents |
| [jiweiyeah/Skills-Manager](https://github.com/jiweiyeah/Skills-Manager) | 1,020 | 2026-09-10 | Desktop app: write once, sync to 32 tools |
| [huggingface/upskill](https://github.com/huggingface/upskill) | 757 | 2026-09-23 | Generates and evaluates skills |
| [EverMind-AI/SkillCorpus](https://github.com/EverMind-AI/SkillCorpus) | 687 | 2026-10-08 | Turns SKILL.md files into a searchable corpus |
| [VikashLoomba/copilot-mcp](https://github.com/VikashLoomba/copilot-mcp) | 506 | 2026-06-15 | VS Code extension to find and install skills for Copilot |
| [K-Dense-AI/claude-skills-mcp](https://github.com/K-Dense-AI/claude-skills-mcp) | 407 | 2026-07-20 | MCP server for skill search |
| [VintLin/skill-flow](https://github.com/VintLin/skill-flow) | 262 | 2026-10-03 | Install and share skills across agents |
| [block/ai-rules](https://github.com/block/ai-rules) | 139 | 2026-05-11 | Manages rules and skills across agents |

## 6. GitLab and Hugging Face

| Project | ★ / likes | Updated | Description |
|---|---:|---|---|
| [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills) | 46 | 2026-10-12 | GitLab's official skills; also a Claude Code marketplace. GitLab Duo supports SKILL.md natively ([docs](https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/)) |
| [hf-skills](https://huggingface.co/hf-skills) | – | – | Hugging Face org with skill Spaces (skill-finder, llm-trainer); `hf skills add` installs from the Hub |
| [benchflow/skillsbench](https://huggingface.co/datasets/benchflow/skillsbench) | 16 | 2026-06-16 | Skills benchmark dataset |
| [open-index/open-skills](https://huggingface.co/datasets/open-index/open-skills) | 12 | 2026-04-10 | Archive of skills.sh |

## Flagged / excluded

- [wanghuan9/skilldock](https://github.com/wanghuan9/skilldock) (Desktop skill manager; last recorded 607★, pushed 2026-10-03): GitHub API and public repository URL returned HTTP 404 on 2026-10-12 (rechecked). Moved here with owner approval; retained for source accounting, excluded from indexing until available again.

- skills.sh leaderboard entries with install counts far out of line with GitHub activity (e.g. `prime-skills/runcomfy-agent-skills`, `flowkit-labs/skills`, `lllllllama/RigorPilot-Skills`).
- Repos copying the `obra/superpowers` name (`101-skills/superpowers`, `qu-skills/superpowers`).
- `mukul975/Anthropic-Cybersecurity-Skills` (33.8k★): uses "Anthropic" in its name but is not from Anthropic.
- `DietrichGebert/ponytail` (154k★, single skill, unclear star origin) and `anbeime/skill` (points to an external store).
- Older than ~9 months: `flyeric0212/cursor-rules`, `ananddtyagi/cc-marketplace`.

> Before installing third-party skills, prefer official repos or run them through a scanner such as SkillSpector or cisco-ai-defense/skill-scanner.
