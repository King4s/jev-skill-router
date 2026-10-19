# AI Agent Skills – curated list

A curated overview of AI-agent skill projects: SKILL.md-based Agent Skills (Claude Code / Anthropic), Cursor rules and plugins, Codex/OpenAI skills, awesome lists, marketplaces, registries and tooling.

- **Last updated:** 2026-10-19
- **Updated:** weekly (automated research, verified against the GitHub API)
- ★ = GitHub stars at time of update. "Updated" = last push (UTC).
- Abandoned (~9+ months without a push), empty and suspicious repos are left out. Star counts in this space are very high; they are reported as shown, not verified as organic.

## Changes this week

- **Added (official):** matlab/simulink-agentic-toolkit, NousResearch/hermes-official-plugins.
- **Added (collections):** wheresryan22/anatomy, rehan-remade/universal-modder, alchaincyf/huashu-art-motion.
- **Stars/dates refreshed.** Biggest ★ movers: mattpocock/skills (+9.9k), cathrynlavery/diagram-design (+7.0k), affaan-m/ECC (+6.1k), heygen-com/hyperframes (+5.8k), anthropics/claude-plugins-official (+5.2k).
- **Revived:** heilcheng/awesome-agent-skills (push 2026-10-19, after last activity 2026-04-05).
- **Flagged:** wanghuan9/skilldock still 404 (rechecked 2026-10-19; owner account also 404); numman-ali/openskills now 9 months without a push (last 2026-01-18); `Jakeschincariol/*-skill` series not added (single-commit repos with fast star growth).
- **Removed:** numman-ali/openskills (moved from Tooling to Flagged / excluded).

## 1. Official repos (vendors and orgs)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 182,048 | 2026-10-09 | Reference Agent Skills repo (docx/pdf/pptx/xlsx, frontend-design, skill-creator, claude-api) |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 152,288 | 2026-10-18 | Claude Code; `plugins/` holds the official example plugins |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 42,868 | 2026-10-18 | Anthropic's directory of high-quality Claude Code plugins |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 30,269 | 2026-10-17 | Plugins and skills for knowledge workers (Claude Cowork) |
| [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) | 4,692 | 2026-10-18 | Community plugin marketplace (read-only mirror) |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 40,168 | 2026-10-16 | GitHub's community instructions, agents and skills for Copilot |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 32,619 | 2026-10-14 | Vercel's official skills (React best practices, web design guidelines) |
| [openai/skills](https://github.com/openai/skills) | 28,155 | 2026-09-08 | Skills catalog for Codex |
| [openai/plugins](https://github.com/openai/plugins) | 7,494 | 2026-10-08 | OpenAI/Codex plugins |
| [huggingface/skills](https://github.com/huggingface/skills) | 11,182 | 2026-10-08 | Hugging Face skills (hf-cli, training, datasets, evals) |
| [cursor/plugins](https://github.com/cursor/plugins) | 12,843 | 2026-10-19 | Cursor plugin specification and official plugins |
| [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) | 8,546 | 2026-08-17 | Google's Agent Skills for the Stitch MCP server |
| [google/agents-cli](https://github.com/google/agents-cli) | 6,099 | 2026-10-12 | Google CLI plus skills for building and evaluating agents (ADK) |
| [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) | 4,300 | 2026-10-13 | Skills for the Gemini API and SDK |
| [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor) | 3,770 | 2026-09-01 | Gemini CLI extension for spec-driven development |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,638 | 2026-10-15 | Security research and audit skills |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | 5,341 | 2026-10-16 | Remotion's official skills |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 66,949 | 2026-10-19 | HeyGen's HTML-to-video skills |
| [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | 47,613 | 2026-10-19 | Alibaba open-source code-review tool with bundled agent skills (deterministic + LLM) |
| [larksuite/cli](https://github.com/larksuite/cli) | 17,730 | 2026-10-19 | Official Lark/Feishu CLI with many skills |
| [googleworkspace/cli](https://github.com/googleworkspace/cli) | 31,662 | 2026-10-06 | Google Workspace CLI with bundled AI agent skills (Drive, Gmail, Calendar, Docs, Sheets, Chat, Admin) |
| [microsoft/skills](https://github.com/microsoft/skills) | 3,131 | 2026-10-18 | Microsoft skills, MCP servers and AGENTS.md for its SDKs |
| [microsoft/azure-skills](https://github.com/microsoft/azure-skills) | 1,576 | 2026-10-16 | Official Azure skills plus MCP configuration |
| [microsoft/power-platform-skills](https://github.com/microsoft/power-platform-skills) | 1,021 | 2026-10-19 | Power Platform plugin marketplace |
| [cloudflare/skills](https://github.com/cloudflare/skills) | 3,100 | 2026-10-15 | Cloudflare skills |
| [supabase/agent-skills](https://github.com/supabase/agent-skills) | 2,879 | 2026-10-02 | Supabase skills |
| [expo/skills](https://github.com/expo/skills) | 2,925 | 2026-10-18 | Expo/EAS skills |
| [stripe/ai](https://github.com/stripe/ai) | 1,960 | 2026-10-19 | Stripe's AI toolkit (includes skills) |
| [callstackincubator/agent-skills](https://github.com/callstackincubator/agent-skills) | 1,674 | 2026-10-08 | React Native skills from Callstack |
| [browserbase/skills](https://github.com/browserbase/skills) | 3,738 | 2026-09-29 | Browserbase's official agent skills for web access and browser automation |
| [matlab/matlab-agentic-toolkit](https://github.com/matlab/matlab-agentic-toolkit) | 1,180 | 2026-10-14 | MATLAB skills for agents |
| [matlab/simulink-agentic-toolkit](https://github.com/matlab/simulink-agentic-toolkit) | 1,238 | 2026-10-14 | MathWorks' Simulink skills plus MCP tools for Model-Based Design (Claude Code, Copilot, Codex, Gemini CLI) |
| [getsentry/skills](https://github.com/getsentry/skills) | 1,066 | 2026-10-16 | Sentry's skills |
| [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) | 924 | 2026-10-15 | AWS agent plugins and skills |
| [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | 900 | 2026-10-05 | HashiCorp skills and Claude Code plugins |
| [firebase/agent-skills](https://github.com/firebase/agent-skills) | 472 | 2026-10-18 | Firebase skills |
| [mongodb/agent-skills](https://github.com/mongodb/agent-skills) | 190 | 2026-10-16 | Official MongoDB agent skills (Atlas, schema, query, search) |
| [redis/agent-skills](https://github.com/redis/agent-skills) | 167 | 2026-09-08 | Redis' official collection of agent skills |
| [neondatabase/agent-skills](https://github.com/neondatabase/agent-skills) | 101 | 2026-10-16 | Neon Postgres skills |
| [google/skills](https://github.com/google/skills) | 21,407 | 2026-10-16 | Agent Skills for Google products and technologies |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 31,254 | 2026-09-14 | Cloudflare's multi-phase security-audit skill with verified findings |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 255,011 | 2026-10-19 | Hermes Agent with built-in SKILL.md support |
| [NousResearch/hermes-official-plugins](https://github.com/NousResearch/hermes-official-plugins) | 321 | 2026-10-19 | Nous Research's official first-party plugins for Hermes Agent (plugin catalog) |

## 2. Large community collections

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 301,743 | 2026-10-10 | Skills framework and development methodology (brainstorming, TDD, debugging) |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 296,491 | 2026-10-13 | Engineering skills; most-installed source on skills.sh |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 137,322 | 2026-10-15 | UI/UX design skill for many agents |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 113,517 | 2026-10-18 | Token-saving skill plus proxy |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 108,285 | 2026-10-13 | Production-grade engineering skills |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | 102,275 | 2026-10-19 | Open-source design plugin/harness with a large SKILL.md library (prototypes, landing pages, slides) |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 98,968 | 2026-10-19 | Design-taste skills against generic "AI slop" |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | 85,503 | 2026-10-19 | Agent skill that turns ideas or codebases into interactive architecture diagrams |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 82,794 | 2026-10-19 | Design-language skill |
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | 75,536 | 2026-10-19 | AI job-search agent skills: board scan, CV scoring, resume/cover letters, interview prep |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | 57,891 | 2026-10-16 | Editorial diagram-design skill (44 types, HTML/SVG) for Claude Code, Codex, Cursor, Copilot |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 55,420 | 2026-10-15 | Marketing, CRO and SEO skills |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 52,717 | 2026-10-15 | Large library of science skills |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | 49,179 | 2026-10-19 | Academic/research skills for Nature-style writing, figures and literature search |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 47,439 | 2026-10-11 | Skills for designers and engineers |
| [wshobson/agents](https://github.com/wshobson/agents) | 41,041 | 2026-10-19 | Plugin marketplace for Claude Code, Codex, Cursor, OpenCode and Copilot |
| [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 35,290 | 2026-10-18 | Turns technical book PDFs into ready-to-use Claude Code skills |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 28,381 | 2026-08-30 | 380+ skills, agents and commands |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27,519 | 2026-10-17 | Persistent file-based planning for coding agents (crash-proof plans, session recovery) |
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 27,188 | 2026-10-16 | 100+ product-management skills |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 26,760 | 2026-09-10 | Popular Chinese skills collection |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | 25,592 | 2026-10-17 | Compound Engineering plugin (Claude Code, Codex, Cursor) |
| [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) | 16,294 | 2026-10-18 | Skill that builds interactive isometric illustrations of machines and systems (SVG, WebGL, 3D) |
| [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 13,686 | 2026-10-11 | AI research and ML-engineering skills |
| [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) | 11,935 | 2026-10-16 | 67 full-stack skills |
| [rehan-remade/universal-modder](https://github.com/rehan-remade/universal-modder) | 8,371 | 2026-10-19 | Skills, tools and knowledge base that let coding agents mod almost any PC game (with fal MCP) |
| [alchaincyf/huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) | 4,421 | 2026-10-16 | Art-animation skill: 35+ art styles and 9 narration grammars rendered in code (Chinese/English) |
| [Mindrally/skills](https://github.com/Mindrally/skills) | 277 | 2026-10-08 | 255+ skills converted from Cursor rules |
| [Jahrome907/minecraft-agent-skills](https://github.com/Jahrome907/minecraft-agent-skills) | 182 | 2026-10-11 | Minecraft modding/server skills for Codex and Claude Code |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 283,449 | 2026-10-19 | Agent harness system (formerly everything-claude-code): skills, memory, security |
| [garrytan/gstack](https://github.com/garrytan/gstack) | 136,881 | 2026-10-19 | Garry Tan's Claude Code setup: opinionated role skills (CEO, designer, eng manager, QA) |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 64,683 | 2026-10-18 | Research skill across Reddit, X, YouTube, HN and the web |
| [blader/humanizer](https://github.com/blader/humanizer) | 58,188 | 2026-10-16 | Skill that removes signs of AI-generated writing |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | 57,734 | 2026-10-11 | Skill that keeps agent answers short and ADHD-friendly (stops burying the answer) |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 49,748 | 2026-09-15 | Obsidian skills (CLI, Markdown, Bases, Canvas) from Obsidian's CEO |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 1,615 | 2026-10-09 | 74 game-dev skills (Godot, Unity, Unreal, Phaser, three.js, Bevy) |

## 3. Awesome lists

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 77,402 | 2026-09-18 | The biggest Claude Skills list |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 55,982 | 2026-10-19 | Claude Code skills, hooks, commands and plugins |
| [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) | 53,199 | 2026-10-19 | 5,400+ OpenClaw skills, categorized |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | 47,916 | 2026-10-18 | Large skills catalog plus a local catalog tool |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 40,961 | 2026-05-30 | The canonical Cursor rules list |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 35,963 | 2026-10-19 | 1,000+ skills from official teams and the community |
| [composio-community/awesome-codex-skills](https://github.com/composio-community/awesome-codex-skills) | 16,958 | 2026-07-26 | Codex skills |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15,457 | 2026-04-28 | Claude Skills list (updates have slowed) |
| [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills) | 10,269 | 2026-09-21 | Claude Skills list |
| [VoltAgent/awesome-codex-subagents](https://github.com/VoltAgent/awesome-codex-subagents) | 6,373 | 2026-10-05 | Curated list of 130+ specialized Codex subagents |
| [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) | 6,289 | 2026-10-19 | Tutorials and skill directories |
| [libukai/awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) | 5,183 | 2026-09-04 | Agent Skills guide (Chinese/English) |
| [Prat011/awesome-llm-skills](https://github.com/Prat011/awesome-llm-skills) | 1,807 | 2026-07-14 | LLM and agent skills |
| [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins) | 1,347 | 2026-10-19 | Codex plugins and skills |
| [ccplugins/awesome-claude-code-plugins](https://github.com/ccplugins/awesome-claude-code-plugins) | 977 | 2026-08-12 | Claude Code plugins |
| [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) | 856 | 2026-08-02 | Cursor skills |
| [ZeroPointRepo/awesome-hermes-skills](https://github.com/ZeroPointRepo/awesome-hermes-skills) | 630 | 2026-10-12 | Hermes Agent skills |
| [quemsah/awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins) | 1,449 | 2026-10-18 | Automated index of Claude Code plugins with adoption metrics |
| [lawve-ai/awesome-legal-skills](https://github.com/lawve-ai/awesome-legal-skills) | 874 | 2026-10-02 | Agent Skills for legal work |

## 4. Marketplaces and registries

| Site / repo | ★ | Updated | Description |
|---|---:|---|---|
| [skills.sh](https://skills.sh) | – | – | Vercel's skills directory with install leaderboard (`npx skills`) |
| [SkillsMP](https://skillsmp.com) | – | – | Aggregator claiming 3M+ skills from GitHub; REST API and MCP server |
| [Smithery skills](https://smithery.ai/skills) | – | – | Skill registry with install counts |
| [claude-plugins.dev](https://claude-plugins.dev) ([source](https://github.com/Kamalnrf/claude-plugins)) | 564 | 2026-10-12 | Registry plus `npx claude-plugins` CLI |
| [cursor.directory](https://cursor.directory) | – | – | Cursor plugins, rules and MCP servers |
| [ClawHub](https://clawhub.ai) ([openclaw/clawhub](https://github.com/openclaw/clawhub)) | 9,517 | 2026-10-19 | OpenClaw skill and plugin registry |
| [davepoon/buildwithclaude](https://github.com/davepoon/buildwithclaude) | 3,650 | 2026-10-18 | Hub for skills, plugins and marketplaces |
| [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) | 1,303 | 2026-10-10 | Curated Claude Code marketplace |
| [numman-ali/n-skills](https://github.com/numman-ali/n-skills) | 1,051 | 2026-09-12 | Curated marketplace (Claude Code, Codex, openskills) |
| [LinklyAI/best-skills](https://github.com/LinklyAI/best-skills) | 649 | 2026-10-19 | Daily Top 100 skills ranking |
| [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) | 516 | 2026-07-14 | Community-vetted marketplace |
| [skilld-dev/skilld](https://github.com/skilld-dev/skilld) | 327 | 2026-10-10 | Open-source alternative to skills.sh |
| [jeremylongshore/tons-of-skills-marketplace](https://github.com/jeremylongshore/tons-of-skills-marketplace) | 2,851 | 2026-10-19 | Model-agnostic skills marketplace with adapters for several agents |

## 5. Tooling (spec, CLI, convert, validate, security)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | 35,527 | 2026-10-09 | `npx skills`, the open install CLI |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | 32,739 | 2026-10-19 | CLI to configure Claude Code (skills, agents, hooks) |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) ([agentskills.io](https://agentskills.io)) | 26,279 | 2026-08-09 | Open Agent Skills spec plus `skills-ref validate`; ~50 supporting clients |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | 24,987 | 2026-09-10 | The AGENTS.md standard |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 20,510 | 2026-10-19 | Security scanner for skills |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 18,546 | 2026-10-18 | Optimizer/trainer for natural-language skills |
| [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | 15,180 | 2026-09-30 | Turns docs sites, repos and PDFs into skills |
| [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | 3,422 | 2026-10-16 | A skill that builds and improves your other skills |
| [intellectronica/ruler](https://github.com/intellectronica/ruler) | 2,948 | 2026-10-14 | Same rules for all coding agents |
| [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) | 2,610 | 2026-10-15 | Security scanner for skills |
| [rohitg00/skillkit](https://github.com/rohitg00/skillkit) | 1,557 | 2026-06-02 | Install, translate and share skills across agents |
| [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) | 1,535 | 2026-10-19 | Syncs rules and skills between agents |
| [jiweiyeah/Skills-Manager](https://github.com/jiweiyeah/Skills-Manager) | 1,031 | 2026-09-10 | Desktop app: write once, sync to 32 tools |
| [huggingface/upskill](https://github.com/huggingface/upskill) | 764 | 2026-10-14 | Generates and evaluates skills |
| [EverMind-AI/SkillCorpus](https://github.com/EverMind-AI/SkillCorpus) | 686 | 2026-10-15 | Turns SKILL.md files into a searchable corpus |
| [VikashLoomba/copilot-mcp](https://github.com/VikashLoomba/copilot-mcp) | 505 | 2026-06-15 | VS Code extension to find and install skills for Copilot |
| [K-Dense-AI/claude-skills-mcp](https://github.com/K-Dense-AI/claude-skills-mcp) | 407 | 2026-07-20 | MCP server for skill search |
| [VintLin/skill-flow](https://github.com/VintLin/skill-flow) | 263 | 2026-10-18 | Install and share skills across agents |
| [block/ai-rules](https://github.com/block/ai-rules) | 139 | 2026-05-11 | Manages rules and skills across agents |

## 6. GitLab and Hugging Face

| Project | ★ / likes | Updated | Description |
|---|---:|---|---|
| [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills) | 46 | 2026-10-18 | GitLab's official skills; also a Claude Code marketplace. GitLab Duo supports SKILL.md natively ([docs](https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/)) |
| [hf-skills](https://huggingface.co/hf-skills) | – | – | Hugging Face org with skill Spaces (skill-finder, llm-trainer); `hf skills add` installs from the Hub |
| [benchflow/skillsbench](https://huggingface.co/datasets/benchflow/skillsbench) | 16 | 2026-06-16 | Skills benchmark dataset |
| [open-index/open-skills](https://huggingface.co/datasets/open-index/open-skills) | 13 | 2026-04-10 | Archive of skills.sh |

## Flagged / excluded

- [wanghuan9/skilldock](https://github.com/wanghuan9/skilldock) (Desktop skill manager; last recorded 607★, pushed 2026-10-03): GitHub API and public repository URL returned HTTP 404 on 2026-10-12 and again on 2026-10-19 (the owner account `wanghuan9` now also returns 404). Moved here with owner approval; retained for source accounting, excluded from indexing until available again.

- [numman-ali/openskills](https://github.com/numman-ali/openskills) (Cross-agent skills loader; 10,785★, last push 2026-01-18): no push for 9 months as of 2026-10-19; removed from Tooling. Will be restored if development resumes.
- skills.sh leaderboard entries with install counts far out of line with GitHub activity (e.g. `prime-skills/runcomfy-agent-skills`, `flowkit-labs/skills`, `lllllllama/RigorPilot-Skills`).
- Repos copying the `obra/superpowers` name (`101-skills/superpowers`, `qu-skills/superpowers`).
- `mukul975/Anthropic-Cybersecurity-Skills` (34.7k★): uses "Anthropic" in its name but is not from Anthropic.
- `DietrichGebert/ponytail` (167k★, single skill, unclear star origin) and `anbeime/skill` (points to an external store).
- `Jakeschincariol/*-skill` series (`replica-skill` 3.4k★, `linkedin-agent-skill` 2.3k★, `youtube-agent-skill` 1.7k★, `founder-skill` 1.0k★): near-identical "Eleven free Claude skills" repos, each with a single commit; stars out of line with substance.
- Older than ~9 months: `flyeric0212/cursor-rules`, `ananddtyagi/cc-marketplace`.

> Before installing third-party skills, prefer official repos or run them through a scanner such as SkillSpector or cisco-ai-defense/skill-scanner.
