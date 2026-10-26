# AI Agent Skills – curated list

A curated overview of AI-agent skill projects: SKILL.md-based Agent Skills (Claude Code / Anthropic), Cursor rules and plugins, Codex/OpenAI skills, awesome lists, marketplaces, registries and tooling.

- **Last updated:** 2026-10-26
- **Updated:** weekly (automated research, verified against the GitHub API)
- ★ = GitHub stars at time of update. "Updated" = last push (UTC).
- Abandoned (~9+ months without a push), empty and suspicious repos are left out. Star counts in this space are very high; they are reported as shown, not verified as organic.

## Changes this week

- **Added (official):** android/skills, Tencent/BrowserSkill, dotnet/skills, BuilderIO/skills, apify/agent-skills, WordPress/agent-skills, Kotlin/kotlin-agent-skills, laravel/agent-skills, elastic/agent-skills, ClickHouse/agent-skills.
- **Added (collections):** alchaincyf/huashu-design, titanwings/distilly.
- **Added (marketplaces/registries):** tech-leads-club/agent-skills, iflytek/skillhub.
- **Added (tooling):** microsoft/skill-recorder, cloudflare/agent-skills-discovery-rfc.
- **Stars/dates refreshed.** Biggest ★ movers: cloudflare/security-audit-skill (+16.1k, with no push since 2026-09-14), mattpocock/skills (+7.0k), affaan-m/ECC (+5.6k), heygen-com/hyperframes (+5.5k), pbakaus/impeccable (+5.3k). gamedev-skills/awesome-gamedev-agent-skills nearly tripled (1,615 → 4,439★).
- **Removed:** libukai/awesome-agent-skills (moved to Flagged / excluded: now redirects to a repo that returns 404).
- **Flagged:** wanghuan9/skilldock still 404 (rechecked 2026-10-26); numman-ali/openskills still no push since 2026-01-18; `Jakeschincariol/*-skill` series keeps growing (now also `instagram-agent-skill`, `day-trader-skill`, `arena-skill`, `trader-skill`) and is still excluded.

## 1. Official repos (vendors and orgs)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | 183,829 | 2026-10-09 | Reference Agent Skills repo (docx/pdf/pptx/xlsx, frontend-design, skill-creator, claude-api) |
| [anthropics/claude-code](https://github.com/anthropics/claude-code) | 153,396 | 2026-10-25 | Claude Code; `plugins/` holds the official example plugins |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 44,619 | 2026-10-25 | Anthropic's directory of high-quality Claude Code plugins |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 33,052 | 2026-10-24 | Plugins and skills for knowledge workers (Claude Cowork) |
| [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) | 4,768 | 2026-10-25 | Community plugin marketplace (read-only mirror) |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 40,415 | 2026-10-26 | GitHub's community instructions, agents and skills for Copilot |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 33,027 | 2026-10-14 | Vercel's official skills (React best practices, web design guidelines) |
| [openai/skills](https://github.com/openai/skills) | 28,310 | 2026-09-08 | Skills catalog for Codex |
| [openai/plugins](https://github.com/openai/plugins) | 7,591 | 2026-10-08 | OpenAI/Codex plugins |
| [huggingface/skills](https://github.com/huggingface/skills) | 11,212 | 2026-10-23 | Hugging Face skills (hf-cli, training, datasets, evals) |
| [cursor/plugins](https://github.com/cursor/plugins) | 14,088 | 2026-10-26 | Cursor plugin specification and official plugins |
| [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills) | 8,595 | 2026-08-17 | Google's Agent Skills for the Stitch MCP server |
| [google/agents-cli](https://github.com/google/agents-cli) | 6,176 | 2026-10-20 | Google CLI plus skills for building and evaluating agents (ADK) |
| [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) | 4,341 | 2026-10-13 | Skills for the Gemini API and SDK |
| [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor) | 3,773 | 2026-09-01 | Gemini CLI extension for spec-driven development |
| [trailofbits/skills](https://github.com/trailofbits/skills) | 7,804 | 2026-10-24 | Security research and audit skills |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | 5,715 | 2026-10-22 | Remotion's official skills |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 72,412 | 2026-10-26 | HeyGen's HTML-to-video skills |
| [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | 48,289 | 2026-10-22 | Alibaba open-source code-review tool with bundled agent skills (deterministic + LLM) |
| [larksuite/cli](https://github.com/larksuite/cli) | 17,830 | 2026-10-26 | Official Lark/Feishu CLI with many skills |
| [googleworkspace/cli](https://github.com/googleworkspace/cli) | 31,891 | 2026-10-06 | Google Workspace CLI with bundled AI agent skills (Drive, Gmail, Calendar, Docs, Sheets, Chat, Admin) |
| [microsoft/skills](https://github.com/microsoft/skills) | 3,148 | 2026-10-25 | Microsoft skills, MCP servers and AGENTS.md for its SDKs |
| [microsoft/azure-skills](https://github.com/microsoft/azure-skills) | 1,595 | 2026-10-23 | Official Azure skills plus MCP configuration |
| [microsoft/power-platform-skills](https://github.com/microsoft/power-platform-skills) | 1,062 | 2026-10-26 | Power Platform plugin marketplace |
| [cloudflare/skills](https://github.com/cloudflare/skills) | 3,172 | 2026-10-19 | Cloudflare skills |
| [supabase/agent-skills](https://github.com/supabase/agent-skills) | 2,932 | 2026-10-02 | Supabase skills |
| [expo/skills](https://github.com/expo/skills) | 3,021 | 2026-10-24 | Expo/EAS skills |
| [stripe/ai](https://github.com/stripe/ai) | 1,971 | 2026-10-26 | Stripe's AI toolkit (includes skills) |
| [callstackincubator/agent-skills](https://github.com/callstackincubator/agent-skills) | 1,684 | 2026-10-08 | React Native skills from Callstack |
| [browserbase/skills](https://github.com/browserbase/skills) | 3,742 | 2026-09-29 | Browserbase's official agent skills for web access and browser automation |
| [matlab/matlab-agentic-toolkit](https://github.com/matlab/matlab-agentic-toolkit) | 1,208 | 2026-10-22 | MATLAB skills for agents |
| [matlab/simulink-agentic-toolkit](https://github.com/matlab/simulink-agentic-toolkit) | 1,269 | 2026-10-21 | MathWorks' Simulink skills plus MCP tools for Model-Based Design (Claude Code, Copilot, Codex, Gemini CLI) |
| [getsentry/skills](https://github.com/getsentry/skills) | 1,088 | 2026-10-23 | Sentry's skills |
| [awslabs/agent-plugins](https://github.com/awslabs/agent-plugins) | 930 | 2026-10-15 | AWS agent plugins and skills |
| [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | 909 | 2026-10-05 | HashiCorp skills and Claude Code plugins |
| [firebase/agent-skills](https://github.com/firebase/agent-skills) | 487 | 2026-10-20 | Firebase skills |
| [mongodb/agent-skills](https://github.com/mongodb/agent-skills) | 191 | 2026-10-25 | Official MongoDB agent skills (Atlas, schema, query, search) |
| [redis/agent-skills](https://github.com/redis/agent-skills) | 170 | 2026-09-08 | Redis' official collection of agent skills |
| [neondatabase/agent-skills](https://github.com/neondatabase/agent-skills) | 106 | 2026-10-26 | Neon Postgres skills |
| [google/skills](https://github.com/google/skills) | 21,577 | 2026-10-25 | Agent Skills for Google products and technologies |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 47,391 | 2026-09-14 | Cloudflare's multi-phase security-audit skill with verified findings |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 257,141 | 2026-10-26 | Hermes Agent with built-in SKILL.md support |
| [NousResearch/hermes-official-plugins](https://github.com/NousResearch/hermes-official-plugins) | 502 | 2026-10-26 | Nous Research's official first-party plugins for Hermes Agent (plugin catalog) |
| [android/skills](https://github.com/android/skills) | 9,755 | 2026-10-23 | Android's official Agent Skills (SKILL.md) based on developer.android.com guidance |
| [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | 9,584 | 2026-10-26 | Tencent's CLI + extension that lets agents use your real, logged-in browser |
| [dotnet/skills](https://github.com/dotnet/skills) | 5,730 | 2026-10-26 | Microsoft .NET team's skills for .NET and C# (100+ SKILL.md) |
| [BuilderIO/skills](https://github.com/BuilderIO/skills) | 4,613 | 2026-10-22 | Builder.io's small, composable agent skills (`npx @agent-native/skills`) |
| [apify/agent-skills](https://github.com/apify/agent-skills) | 2,461 | 2026-10-19 | Apify's agent skills for web scraping and Actors |
| [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | 2,298 | 2026-10-26 | WordPress' official skills (blocks, themes, plugins, best practices) |
| [Kotlin/kotlin-agent-skills](https://github.com/Kotlin/kotlin-agent-skills) | 1,093 | 2026-10-20 | JetBrains/Kotlin agent skills for Kotlin projects |
| [laravel/agent-skills](https://github.com/laravel/agent-skills) | 731 | 2026-10-17 | Laravel's official agent skills |
| [elastic/agent-skills](https://github.com/elastic/agent-skills) | 601 | 2026-10-23 | Elastic's official skills (50+ SKILL.md) |
| [ClickHouse/agent-skills](https://github.com/ClickHouse/agent-skills) | 561 | 2026-10-25 | Official skills for ClickHouse and ClickHouse Cloud |

## 2. Large community collections

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 305,202 | 2026-10-23 | Skills framework and development methodology (brainstorming, TDD, debugging) |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 303,452 | 2026-10-22 | Engineering skills; most-installed source on skills.sh |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 140,508 | 2026-10-23 | UI/UX design skill for many agents |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 115,106 | 2026-10-25 | Token-saving skill plus proxy |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 110,578 | 2026-10-13 | Production-grade engineering skills |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | 104,017 | 2026-10-26 | Open-source design plugin/harness with a large SKILL.md library (prototypes, landing pages, slides) |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | 102,628 | 2026-10-26 | Design-taste skills against generic "AI slop" |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | 89,373 | 2026-10-26 | Agent skill that turns ideas or codebases into interactive architecture diagrams |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 88,110 | 2026-10-25 | Design-language skill |
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | 77,361 | 2026-10-26 | AI job-search agent skills: board scan, CV scoring, resume/cover letters, interview prep |
| [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | 61,150 | 2026-10-26 | Editorial diagram-design skill (44 types, HTML/SVG) for Claude Code, Codex, Cursor, Copilot |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 56,568 | 2026-10-22 | Marketing, CRO and SEO skills |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 54,630 | 2026-10-19 | Large library of science skills |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | 50,642 | 2026-10-25 | Academic/research skills for Nature-style writing, figures and literature search |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 49,690 | 2026-10-11 | Skills for designers and engineers |
| [wshobson/agents](https://github.com/wshobson/agents) | 41,723 | 2026-10-26 | Plugin marketplace for Claude Code, Codex, Cursor, OpenCode and Copilot |
| [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 36,118 | 2026-10-25 | Turns technical book PDFs into ready-to-use Claude Code skills |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 28,729 | 2026-10-23 | 380+ skills, agents and commands |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27,650 | 2026-10-24 | Persistent file-based planning for coding agents (crash-proof plans, session recovery) |
| [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 27,380 | 2026-10-16 | 100+ product-management skills |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 26,958 | 2026-09-10 | Popular Chinese skills collection |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | 25,713 | 2026-10-25 | Compound Engineering plugin (Claude Code, Codex, Cursor) |
| [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) | 20,750 | 2026-10-18 | Skill that builds interactive isometric illustrations of machines and systems (SVG, WebGL, 3D) |
| [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 13,952 | 2026-10-11 | AI research and ML-engineering skills |
| [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) | 12,062 | 2026-10-26 | 67 full-stack skills |
| [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | 26,357 | 2026-10-23 | HTML-native design skill: web/app prototypes, editable PPTX, animation, infographics (Chinese/English) |
| [titanwings/distilly](https://github.com/titanwings/distilly) | 26,014 | 2026-10-13 | Distills how people think into reusable skills (formerly Colleague Skill) |
| [rehan-remade/universal-modder](https://github.com/rehan-remade/universal-modder) | 8,971 | 2026-10-26 | Skills, tools and knowledge base that let coding agents mod almost any PC game (with fal MCP) |
| [alchaincyf/huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) | 5,229 | 2026-10-16 | Art-animation skill: 35+ art styles and 9 narration grammars rendered in code (Chinese/English) |
| [Mindrally/skills](https://github.com/Mindrally/skills) | 286 | 2026-10-08 | 255+ skills converted from Cursor rules |
| [Jahrome907/minecraft-agent-skills](https://github.com/Jahrome907/minecraft-agent-skills) | 187 | 2026-10-11 | Minecraft modding/server skills for Codex and Claude Code |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | 289,048 | 2026-10-26 | Agent harness system (formerly everything-claude-code): skills, memory, security |
| [garrytan/gstack](https://github.com/garrytan/gstack) | 137,755 | 2026-10-26 | Garry Tan's Claude Code setup: opinionated role skills (CEO, designer, eng manager, QA) |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 65,494 | 2026-10-26 | Research skill across Reddit, X, YouTube, HN and the web |
| [blader/humanizer](https://github.com/blader/humanizer) | 60,698 | 2026-10-16 | Skill that removes signs of AI-generated writing |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | 58,762 | 2026-10-19 | Skill that keeps agent answers short and ADHD-friendly (stops burying the answer) |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 50,105 | 2026-09-15 | Obsidian skills (CLI, Markdown, Bases, Canvas) from Obsidian's CEO |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 4,439 | 2026-10-24 | 74 game-dev skills (Godot, Unity, Unreal, Phaser, three.js, Bevy) |

## 3. Awesome lists

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 77,960 | 2026-09-18 | The biggest Claude Skills list |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 56,561 | 2026-10-26 | Claude Code skills, hooks, commands and plugins |
| [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) | 53,352 | 2026-10-19 | 5,400+ OpenClaw skills, categorized |
| [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | 48,507 | 2026-10-24 | Large skills catalog plus a local catalog tool |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | 41,023 | 2026-05-30 | The canonical Cursor rules list |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 36,369 | 2026-10-25 | 1,000+ skills from official teams and the community |
| [composio-community/awesome-codex-skills](https://github.com/composio-community/awesome-codex-skills) | 17,060 | 2026-07-26 | Codex skills |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | 15,569 | 2026-04-28 | Claude Skills list (updates have slowed) |
| [BehiSecc/awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills) | 10,303 | 2026-09-21 | Claude Skills list |
| [VoltAgent/awesome-codex-subagents](https://github.com/VoltAgent/awesome-codex-subagents) | 6,407 | 2026-10-05 | Curated list of 130+ specialized Codex subagents |
| [heilcheng/awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) | 6,314 | 2026-10-26 | Tutorials and skill directories |
| [Prat011/awesome-llm-skills](https://github.com/Prat011/awesome-llm-skills) | 1,821 | 2026-07-14 | LLM and agent skills |
| [hashgraph-online/awesome-codex-plugins](https://github.com/hashgraph-online/awesome-codex-plugins) | 1,410 | 2026-10-26 | Codex plugins and skills |
| [ccplugins/awesome-claude-code-plugins](https://github.com/ccplugins/awesome-claude-code-plugins) | 987 | 2026-08-12 | Claude Code plugins |
| [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) | 866 | 2026-08-02 | Cursor skills |
| [ZeroPointRepo/awesome-hermes-skills](https://github.com/ZeroPointRepo/awesome-hermes-skills) | 641 | 2026-10-19 | Hermes Agent skills |
| [quemsah/awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins) | 1,480 | 2026-10-26 | Automated index of Claude Code plugins with adoption metrics |
| [lawve-ai/awesome-legal-skills](https://github.com/lawve-ai/awesome-legal-skills) | 898 | 2026-10-19 | Agent Skills for legal work |

## 4. Marketplaces and registries

| Site / repo | ★ | Updated | Description |
|---|---:|---|---|
| [skills.sh](https://skills.sh) | – | – | Vercel's skills directory with install leaderboard (`npx skills`) |
| [SkillsMP](https://skillsmp.com) | – | – | Aggregator claiming 3M+ skills from GitHub; REST API and MCP server |
| [Smithery skills](https://smithery.ai/skills) | – | – | Skill registry with install counts |
| [claude-plugins.dev](https://claude-plugins.dev) ([source](https://github.com/Kamalnrf/claude-plugins)) | 562 | 2026-10-19 | Registry plus `npx claude-plugins` CLI |
| [cursor.directory](https://cursor.directory) | – | – | Cursor plugins, rules and MCP servers |
| [ClawHub](https://clawhub.ai) ([openclaw/clawhub](https://github.com/openclaw/clawhub)) | 9,527 | 2026-10-26 | OpenClaw skill and plugin registry |
| [davepoon/buildwithclaude](https://github.com/davepoon/buildwithclaude) | 3,678 | 2026-10-26 | Hub for skills, plugins and marketplaces |
| [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) | 1,309 | 2026-10-21 | Curated Claude Code marketplace |
| [numman-ali/n-skills](https://github.com/numman-ali/n-skills) | 1,051 | 2026-09-12 | Curated marketplace (Claude Code, Codex, openskills) |
| [LinklyAI/best-skills](https://github.com/LinklyAI/best-skills) | 664 | 2026-10-26 | Daily Top 100 skills ranking |
| [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) | 520 | 2026-07-14 | Community-vetted marketplace |
| [skilld-dev/skilld](https://github.com/skilld-dev/skilld) | 328 | 2026-10-10 | Open-source alternative to skills.sh |
| [jeremylongshore/tons-of-skills-marketplace](https://github.com/jeremylongshore/tons-of-skills-marketplace) | 2,871 | 2026-10-26 | Model-agnostic skills marketplace with adapters for several agents |
| [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills) | 7,089 | 2026-10-26 | Validated skill registry for coding agents (Claude Code, Cursor, Copilot, Antigravity) |
| [iflytek/skillhub](https://github.com/iflytek/skillhub) | 5,292 | 2026-10-26 | iFlytek's self-hosted enterprise skill registry: versioning, RBAC, audit logs, Docker/Kubernetes |

## 5. Tooling (spec, CLI, convert, validate, security)

| Repo | ★ | Updated | Description |
|---|---:|---|---|
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | 36,589 | 2026-10-19 | `npx skills`, the open install CLI |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | 32,904 | 2026-10-26 | CLI to configure Claude Code (skills, agents, hooks) |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) ([agentskills.io](https://agentskills.io)) | 26,634 | 2026-08-09 | Open Agent Skills spec plus `skills-ref validate`; ~50 supporting clients |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | 25,115 | 2026-09-10 | The AGENTS.md standard |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 21,639 | 2026-10-23 | Security scanner for skills |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 18,681 | 2026-10-25 | Optimizer/trainer for natural-language skills |
| [yusufkaraaslan/Skill_Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) | 15,222 | 2026-09-30 | Turns docs sites, repos and PDFs into skills |
| [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | 3,563 | 2026-10-23 | A skill that builds and improves your other skills |
| [intellectronica/ruler](https://github.com/intellectronica/ruler) | 2,951 | 2026-10-22 | Same rules for all coding agents |
| [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) | 2,634 | 2026-10-22 | Security scanner for skills |
| [rohitg00/skillkit](https://github.com/rohitg00/skillkit) | 1,562 | 2026-06-02 | Install, translate and share skills across agents |
| [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) | 1,552 | 2026-10-25 | Syncs rules and skills between agents |
| [jiweiyeah/Skills-Manager](https://github.com/jiweiyeah/Skills-Manager) | 1,039 | 2026-09-10 | Desktop app: write once, sync to 32 tools |
| [huggingface/upskill](https://github.com/huggingface/upskill) | 761 | 2026-10-14 | Generates and evaluates skills |
| [EverMind-AI/SkillCorpus](https://github.com/EverMind-AI/SkillCorpus) | 692 | 2026-10-23 | Turns SKILL.md files into a searchable corpus |
| [VikashLoomba/copilot-mcp](https://github.com/VikashLoomba/copilot-mcp) | 505 | 2026-06-15 | VS Code extension to find and install skills for Copilot |
| [K-Dense-AI/claude-skills-mcp](https://github.com/K-Dense-AI/claude-skills-mcp) | 409 | 2026-07-20 | MCP server for skill search |
| [VintLin/skill-flow](https://github.com/VintLin/skill-flow) | 263 | 2026-10-22 | Install and share skills across agents |
| [block/ai-rules](https://github.com/block/ai-rules) | 142 | 2026-05-11 | Manages rules and skills across agents |
| [microsoft/skill-recorder](https://github.com/microsoft/skill-recorder) | 5,117 | 2026-10-24 | Desktop app that records a work session and turns it into a reusable skill (Copilot SDK) |
| [cloudflare/agent-skills-discovery-rfc](https://github.com/cloudflare/agent-skills-discovery-rfc) | 362 | 2026-04-23 | Proposal for discovering Agent Skills via `.well-known` URIs (RFC 8615) |

## 6. GitLab and Hugging Face

| Project | ★ / likes | Updated | Description |
|---|---:|---|---|
| [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills) | 47 | 2026-10-26 | GitLab's official skills; also a Claude Code marketplace. GitLab Duo supports SKILL.md natively ([docs](https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/)) |
| [hf-skills](https://huggingface.co/hf-skills) | – | – | Hugging Face org with skill Spaces (skill-finder, llm-trainer); `hf skills add` installs from the Hub |
| [benchflow/skillsbench](https://huggingface.co/datasets/benchflow/skillsbench) | 18 | 2026-06-16 | Skills benchmark dataset |
| [open-index/open-skills](https://huggingface.co/datasets/open-index/open-skills) | 14 | 2026-04-10 | Archive of skills.sh |

## Flagged / excluded

- [wanghuan9/skilldock](https://github.com/wanghuan9/skilldock) (Desktop skill manager; last recorded 607★, pushed 2026-10-03): GitHub API and public repository URL returned HTTP 404 on 2026-10-12 and again on 2026-10-19 and 2026-10-26 (the owner account `wanghuan9` also returns 404). Moved here with owner approval; retained for source accounting, excluded from indexing until available again.
- [libukai/awesome-agent-skills](https://github.com/libukai/awesome-agent-skills) (Agent Skills guide, Chinese/English; last recorded 5,183★, pushed 2026-09-04): on 2026-10-26 the GitHub API returned 404 and the public URL redirects to `shikaijiaoyu/awesome-agent-skills`, which also returns 404. Removed from Awesome lists; will be restored if it becomes available again.
- [numman-ali/openskills](https://github.com/numman-ali/openskills) (Cross-agent skills loader; 10,810★, last push 2026-01-18): no push for 9 months as of 2026-10-26; removed from Tooling. Will be restored if development resumes.
- skills.sh leaderboard entries with install counts far out of line with GitHub activity (e.g. `prime-skills/runcomfy-agent-skills`, `flowkit-labs/skills`, `lllllllama/RigorPilot-Skills`).
- Repos copying the `obra/superpowers` name (`101-skills/superpowers`, `qu-skills/superpowers`).
- `mukul975/Anthropic-Cybersecurity-Skills` (35.0k★): uses "Anthropic" in its name but is not from Anthropic.
- `DietrichGebert/ponytail` (176k★, single skill, unclear star origin) and `anbeime/skill` (points to an external store).
- `Jakeschincariol/*-skill` series (`replica-skill` 5.5k★, `youtube-agent-skill` 3.0k★, `instagram-agent-skill` 2.9k★, `linkedin-agent-skill` 2.7k★, `founder-skill` 1.8k★, `day-trader-skill` 1.8k★, `arena-skill` 1.0k★, `trader-skill` 636★): near-identical "Eleven free Claude skills" repos, each with one or two commits (checked 2026-10-26); stars out of line with substance.
- Older than ~9 months: `flyeric0212/cursor-rules`, `ananddtyagi/cc-marketplace`.

> Before installing third-party skills, prefer official repos or run them through a scanner such as SkillSpector or cisco-ai-defense/skill-scanner.
