# AI Agent Skills – curated list

A curated overview of AI-agent skill projects: SKILL.md-based Agent Skills (Claude Code / Anthropic), Cursor rules and plugins, Codex/OpenAI skills, awesome lists, marketplaces, registries and tooling.

- **Last updated:** 2026-10-05
- **Updated:** weekly (automated research, verified against the GitHub API)
- ★ = GitHub stars at time of update. "Updated" = last push (UTC).
- Abandoned (~9+ months without a push), empty and suspicious repos are left out. Star counts in this space are very high; they are reported as shown, not verified as organic.

## Changes this week

- **Added (official):** google/skills, cloudflare/security-audit-skill.
- **Added (collections):** affaan-m/ECC, garrytan/gstack, mvanhorn/last30days-skill, blader/humanizer, kepano/obsidian-skills, gamedev-skills/awesome-gamedev-agent-skills.
- **Added (lists/marketplaces):** quemsah/awesome-claude-plugins, lawve-ai/awesome-legal-skills, jeremylongshore/tons-of-skills-marketplace.
- **Flagged:** mukul975/Anthropic-Cybersecurity-Skills (name suggests Anthropic, but it is unaffiliated).
- **Removed:** none. All existing entries are still active and not archived; stars and push dates refreshed.

## 1. Official repos (vendors and orgs)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 179,679 | 2026-10-03 | Reference Agent Skills repo (docx/pdf/pptx/xlsx, frontend-design, skill-creator, claude-api) |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 149,443 | 2026-10-05 | Claude Code; `plugins/` holds the official example plugins |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 37,398 | 2026-10-04 | Anthropic's directory of high-quality Claude Code plugins |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 26,102 | 2026-10-04 | Plugins and skills for knowledge workers (Claude Cowork) |
| [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) | 4,472 | 2026-10-01 | Community plugin marketplace (read-only mirror) |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 39,706 | 2026-10-04 | GitHub's community instructions, agents and skills for Copilot |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 31,937 | 2026-08-28 | Vercel's official skills (React best practices, web design guidelines) |
| [openai/skills](https://github.com/openai/skills) | 27,881 | 2026-09-08 | Skills catalog for Codex |
| [openai/plugins](https://github.com/openai/plugins) | 7,304 | 2026-09-28 | OpenAI/Codex plugins |
| [huggingface/skills](https://github.com/huggingface/skills) | 11,138 | 2026-10-01 | Hugging Face skills (hf-cli, training, datasets, evals) |
| [cursor/plugins](https://github.com/cursor/plugins) | 9,832 | 2026-10-05 | Cursor plugin specification and official plugins |
| [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) | 8,425 | 2026-08-17 | Google's Agent Skills for the Stitch MCP server |
| [google/agents-cli](https://github.com/google/agents-cli) | 6,052 | 2026-09-30 | Google CLI plus skills for building and evaluating agents (ADK) |
| [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) | 4,245 | 2026-09-23 | Skills for the Gemini API and SDK |
| [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor) | 3,753 | 2026-09-01 | Gemini CLI extension for spec-driven development |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,368 | 2026-10-02 | Security research and audit skills |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | 4,843 | 2026-10-01 | Remotion's official skills |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 56,874 | 2026-10-05 | HeyGen's HTML-to-video skills |
| [larksuite/cli](https://github.com/larksuite/cli) | 17,537 | 2026-09-30 | Official Lark/Feishu CLI with many skills |
| [microsoft/skills](https://github.com/microsoft/skills) | 3,082 | 2026-10-02 | Microsoft skills, MCP servers and AGENTS.md for its SDKs |
| [microsoft/azure-skills](https://github.com/microsoft/azure-skills) | 1,538 | 2026-10-02 | Official Azure skills plus MCP configuration |
| [microsoft/power-platform-skills](https://github.com/microsoft/power-platform-skills) | 962 | 2026-10-05 | Power Platform plugin marketplace |
| [cloudflare/skills](https://github.com/cloudflare/skills) | 2,984 | 2026-10-01 | Cloudflare skills |
| [supabase/agent-skills](https://github.com/supabase/agent-skills) | 2,698 | 2026-10-02 | Supabase skills |
| [expo/skills](https://github.com/expo/skills) | 2,655 | 2026-10-03 | Expo/EAS skills |
| [stripe/ai](https://github.com/stripe/ai) | 1,855 | 2026-10-05 | Stripe's AI toolkit (includes skills) |
| [callstackincubator/agent-skills](https://github.com/callstackincubator/agent-skills) | 1,664 | 2026-09-16 | React Native skills from Callstack |
| [matlab/matlab-agentic-toolkit](https://github.com/matlab/matlab-agentic-toolkit) | 1,130 | 2026-09-30 | MATLAB skills for agents |
| [getsentry/skills](https://github.com/getsentry/skills) | 1,037 | 2026-10-02 | Sentry's skills |
| [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) | 910 | 2026-10-02 | AWS agent plugins and skills |
| [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | 883 | 2026-10-05 | HashiCorp skills and Claude Code plugins |
| [firebase/agent-skills](https://github.com/firebase/agent-skills) | 462 | 2026-10-03 | Firebase skills |
| [neondatabase/agent-skills](https://github.com/neondatabase/agent-skills) | 98 | 2026-10-03 | Neon Postgres skills |
| [google/skills](https://github.com/google/skills) | 20,935 | 2026-10-02 | Agent Skills for Google products and technologies |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 24,419 | 2026-09-14 | Cloudflare's multi-phase security-audit skill with verified findings |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 251,268 | 2026-10-05 | Hermes Agent with built-in SKILL.md support |

## 2. Large community collections

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 295,349 | 2026-09-27 | Skills framework and development methodology (brainstorming, TDD, debugging) |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 276,352 | 2026-10-04 | Engineering skills; most-installed source on skills.sh |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 133,089 | 2026-10-03 | UI/UX design skill for many agents |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 109,861 | 2026-10-04 | Token-saving skill plus proxy |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 101,282 | 2026-10-03 | Production-grade engineering skills |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 92,648 | 2026-09-26 | Design-taste skills against generic "AI slop" |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 76,479 | 2026-10-05 | Design-language skill |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 53,180 | 2026-10-03 | Marketing, CRO and SEO skills |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 47,614 | 2026-10-01 | Large library of science skills |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 43,414 | 2026-10-02 | Skills for designers and engineers |
| [wshobson/agents](https://github.com/wshobson/agents) | 40,205 | 2026-10-05 | Plugin marketplace for Claude Code, Codex, Cursor, OpenCode and Copilot |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 27,619 | 2026-08-30 | 380+ skills, agents and commands |
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 26,772 | 2026-09-14 | 100+ product-management skills |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 26,345 | 2026-09-10 | Popular Chinese skills collection |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | 25,392 | 2026-10-02 | Compound Engineering plugin (Claude Code, Codex, Cursor) |
| [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 13,248 | 2026-06-16 | AI research and ML-engineering skills |
| [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) | 11,733 | 2026-10-03 | 67 full-stack skills |
| [Mindrally/skills](https://github.com/Mindrally/skills) | 266 | 2026-09-03 | 255+ skills converted from Cursor rules |
| [Jahrome907/minecraft-agent-skills](https://github.com/Jahrome907/minecraft-agent-skills) | 165 | 2026-09-13 | Minecraft modding/server skills for Codex and Claude Code |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 273,093 | 2026-10-05 | Agent harness system (formerly everything-claude-code): skills, memory, security |
| [garrytan/gstack](https://github.com/garrytan/gstack) | 135,221 | 2026-10-05 | Garry Tan's Claude Code setup: opinionated role skills (CEO, designer, eng manager, QA) |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 63,525 | 2026-10-04 | Research skill across Reddit, X, YouTube, HN and the web |
| [blader/humanizer](https://github.com/blader/humanizer) | 54,007 | 2026-09-28 | Skill that removes signs of AI-generated writing |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 49,156 | 2026-09-15 | Obsidian skills (CLI, Markdown, Bases, Canvas) from Obsidian's CEO |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 1,311 | 2026-09-27 | 74 game-dev skills (Godot, Unity, Unreal, Phaser, three.js, Bevy) |

## 3. Awesome lists

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 76,514 | 2026-09-18 | The biggest Claude Skills list |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 55,091 | 2026-10-05 | Claude Code skills, hooks, commands and plugins |
| [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) | 52,955 | 2026-10-02 | 5,400+ OpenClaw skills, categorized |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | 47,257 | 2026-10-04 | Large skills catalog plus a local catalog tool |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 40,878 | 2026-05-30 | The canonical Cursor rules list |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 35,215 | 2026-10-02 | 1,000+ skills from official teams and the community |
| [composio-community/awesome-codex-skills](https://github.com/composio-community/awesome-codex-skills) | 16,769 | 2026-07-26 | Codex skills |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15,270 | 2026-04-28 | Claude Skills list (updates have slowed) |
| [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills) | 10,212 | 2026-09-21 | Claude Skills list |
| [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) | 6,262 | 2026-04-05 | Tutorials and skill directories |
| [libukai/awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) | 5,147 | 2026-09-04 | Agent Skills guide (Chinese/English) |
| [Prat011/awesome-llm-skills](https://github.com/Prat011/awesome-llm-skills) | 1,781 | 2026-07-14 | LLM and agent skills |
| [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins) | 1,215 | 2026-10-05 | Codex plugins and skills |
| [ccplugins/awesome-claude-code-plugins](https://github.com/ccplugins/awesome-claude-code-plugins) | 966 | 2026-08-12 | Claude Code plugins |
| [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) | 835 | 2026-08-02 | Cursor skills |
| [ZeroPointRepo/awesome-hermes-skills](https://github.com/ZeroPointRepo/awesome-hermes-skills) | 590 | 2026-09-30 | Hermes Agent skills |
| [quemsah/awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins) | 1,397 | 2026-10-05 | Automated index of Claude Code plugins with adoption metrics |
| [lawve-ai/awesome-legal-skills](https://github.com/lawve-ai/awesome-legal-skills) | 802 | 2026-10-02 | Agent Skills for legal work |

## 4. Marketplaces and registries

| Site / repo | ★ | Updated | Description |
|---|---:|---|---|
| [skills.sh](https://skills.sh) | – | – | Vercel's skills directory with install leaderboard (`npx skills`) |
| [SkillsMP](https://skillsmp.com) | – | – | Aggregator claiming 3M+ skills from GitHub; REST API and MCP server |
| [Smithery skills](https://smithery.ai/skills) | – | – | Skill registry with install counts |
| [claude-plugins.dev](https://claude-plugins.dev) ([source](https://github.com/Kamalnrf/claude-plugins)) | 565 | 2026-09-28 | Registry plus `npx claude-plugins` CLI |
| [cursor.directory](https://cursor.directory) | – | – | Cursor plugins, rules and MCP servers |
| [ClawHub](https://clawhub.ai) ([openclaw/clawhub](https://github.com/openclaw/clawhub)) | 9,484 | 2026-10-03 | OpenClaw skill and plugin registry |
| [davepoon/buildwithclaude](https://github.com/davepoon/buildwithclaude) | 3,591 | 2026-10-04 | Hub for skills, plugins and marketplaces |
| [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) | 1,289 | 2026-09-08 | Curated Claude Code marketplace |
| [numman-ali/n-skills](https://github.com/numman-ali/n-skills) | 1,051 | 2026-09-12 | Curated marketplace (Claude Code, Codex, openskills) |
| [LinklyAI/best-skills](https://github.com/LinklyAI/best-skills) | 629 | 2026-10-05 | Daily Top 100 skills ranking |
| [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) | 512 | 2026-07-14 | Community-vetted marketplace |
| [skilld-dev/skilld](https://github.com/skilld-dev/skilld) | 308 | 2026-10-05 | Open-source alternative to skills.sh |
| [jeremylongshore/tons-of-skills-marketplace](https://github.com/jeremylongshore/tons-of-skills-marketplace) | 2,811 | 2026-10-05 | Model-agnostic skills marketplace with adapters for several agents |

## 5. Tooling (spec, CLI, convert, validate, security)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | 33,138 | 2026-10-02 | `npx skills`, the open install CLI |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | 32,383 | 2026-10-05 | CLI to configure Claude Code (skills, agents, hooks) |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) ([agentskills.io](https://agentskills.io)) | 25,913 | 2026-08-09 | Open Agent Skills spec plus `skills-ref validate`; ~50 supporting clients |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | 24,768 | 2026-09-10 | The AGENTS.md standard |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 19,406 | 2026-10-05 | Security scanner for skills |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 18,034 | 2026-09-30 | Optimizer/trainer for natural-language skills |
| [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | 15,102 | 2026-09-30 | Turns docs sites, repos and PDFs into skills |
| [numman-ali/openskills](https://github.com/numman-ali/openskills) | 10,773 | 2026-01-18 | Cross-agent skills loader (⚠️ no push for ~8.5 months) |
| [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | 3,155 | 2026-10-02 | A skill that builds and improves your other skills |
| [intellectronica/ruler](https://github.com/intellectronica/ruler) | 2,941 | 2026-09-30 | Same rules for all coding agents |
| [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) | 2,572 | 2026-10-03 | Security scanner for skills |
| [rohitg00/skillkit](https://github.com/rohitg00/skillkit) | 1,545 | 2026-06-02 | Install, translate and share skills across agents |
| [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) | 1,498 | 2026-10-05 | Syncs rules and skills between agents |
| [jiweiyeah/Skills-Manager](https://github.com/jiweiyeah/Skills-Manager) | 1,009 | 2026-09-10 | Desktop app: write once, sync to 32 tools |
| [huggingface/upskill](https://github.com/huggingface/upskill) | 758 | 2026-09-23 | Generates and evaluates skills |
| [EverMind-AI/SkillCorpus](https://github.com/EverMind-AI/SkillCorpus) | 678 | 2026-10-01 | Turns SKILL.md files into a searchable corpus |
| [wanghuan9/skilldock](https://github.com/wanghuan9/skilldock) | 607 | 2026-10-03 | Desktop skill manager |
| [VikashLoomba/copilot-mcp](https://github.com/VikashLoomba/copilot-mcp) | 504 | 2026-06-15 | VS Code extension to find and install skills for Copilot |
| [K-Dense-AI/claude-skills-mcp](https://github.com/K-Dense-AI/claude-skills-mcp) | 407 | 2026-07-20 | MCP server for skill search |
| [VintLin/skill-flow](https://github.com/VintLin/skill-flow) | 261 | 2026-10-03 | Install and share skills across agents |
| [block/ai-rules](https://github.com/block/ai-rules) | 137 | 2026-05-11 | Manages rules and skills across agents |

## 6. GitLab and Hugging Face

| Project | ★ / likes | Updated | Description |
|---|---:|---|---|
| [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills) | 43 | 2026-10-05 | GitLab's official skills; also a Claude Code marketplace. GitLab Duo supports SKILL.md natively ([docs](https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/)) |
| [hf-skills](https://huggingface.co/hf-skills) | – | – | Hugging Face org with skill Spaces (skill-finder, llm-trainer); `hf skills add` installs from the Hub |
| [benchflow/skillsbench](https://huggingface.co/datasets/benchflow/skillsbench) | 16 | 2026-06-16 | Skills benchmark dataset |
| [open-index/open-skills](https://huggingface.co/datasets/open-index/open-skills) | 12 | 2026-04-10 | Archive of skills.sh |

## Flagged / excluded

- skills.sh leaderboard entries with install counts far out of line with GitHub activity (e.g. `prime-skills/runcomfy-agent-skills`, `flowkit-labs/skills`, `lllllllama/RigorPilot-Skills`).
- Repos copying the `obra/superpowers` name (`101-skills/superpowers`, `qu-skills/superpowers`).
- `mukul975/Anthropic-Cybersecurity-Skills` (33.8k★): uses "Anthropic" in its name but is not from Anthropic.
- `DietrichGebert/ponytail` (154k★, single skill, unclear star origin) and `anbeime/skill` (points to an external store).
- Older than ~9 months: `flyeric0212/cursor-rules`, `ananddtyagi/cc-marketplace`.

> Before installing third-party skills, prefer official repos or run them through a scanner such as SkillSpector or cisco-ai-defense/skill-scanner.
