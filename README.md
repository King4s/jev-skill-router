# jev-skill-router

Samler skill-kilder fra hele økosystemet, indekserer dem lokalt, og lader **Jev**
(TypeSafe System One) vælge de bedste til det projekt du skal bygge.

## Arkitekturen i én sætning

Kode finder kandidater, Jev dømmer dem. 15.000+ skills kan ikke være ét Jev-spørgsmål —
så FTS5 laver shortlisten, og Jev rangerer den med `Score` + kalibreret confidence.

```
sources.txt ──► index ──► skills.db (SQLite FTS5) ──► route ──► rangliste
              GitHub API     15k rækker, 0 deps        FTS5-prefilter
                                                       └─► Jev: ét kald, Score pr. kandidat
```

## Målt på første kørsel (2026-10-04)

| | |
|---|---|
| Kilder i `sources.txt` | 78 rækker (76 GitHub-repos + 2 GitLab/HF) |
| Repos der bærer `SKILL.md` | 63 |
| Repos uden (rene link-lister) | 14 — se *Fase 2* |
| `SKILL.md` fundet via tree-API | **15.642** |
| Stjernetallene i oversigten | bekræftet ægte mod GitHub-API'et |

Ingen kloning: hvert repo koster to API-kald (`repos/<r>` + `trees?recursive=1`), og hver
skill hentes som de første 4 KB af rå-filen — frontmatter er alt routeren bruger.

## Brug

```
python3 router.py index                      # byg/opdatér indekset (netværk, ~5 min)
python3 router.py stats                      # hvad ligger der
python3 router.py route "beskriv projektet"  # FTS5-shortlist → Jev → rangliste
python3 router.py selftest                   # offline check, ingen netværk
```

`route --top 40` er default: 40 kandidater i **ét** Jev-kald. Batching er hele pointen —
21 spørgsmål i ét kald koster samme tid som 1.

Kræver `gh` (autentificeret) til `index` og `TYPESAFE_API_KEY` (eller
`~/.config/jev-loop/typesafe_api_key`) til `route`.

## Dedupe

Samme skill ligger kopieret ind i mange awesome-lister. Fingerprint = sha1 af
normaliseret `name + description`; første forekomst vinder, kopier gemmes med `dup_of`
peget på originalen. Routeren rangerer kun originalen, men kan svare på hvor mange
kilder der bærer den.

## Kilde-tiers

`sources.txt` er sektionsopdelt, og sektionsnummeret bliver til en tier:
`vendor` (officielle firma-repos), `community`, `list` (awesome-lister),
`registry`, `tooling`, `gitlab`. Tieren følger med i ranglisten, så et `vendor`-hit
kan foretrækkes over et community-hit ved samme score.

**Grok Bot vedligeholder `sources.txt`.** Tilføj en linje `owner/repo` i den rigtige
sektion — routeren læser filen, ingen kodeændring nødvendig.

## Svarkontrakten håndhæves

Type-sikkerhed der ikke håndhæves er kun kosmetisk. Hvert Jev-svar valideres før det
tæller: `type == "score"`, `probabilities` med nøgler præcis som niveauerne, alle tal
finite i [0,1], sum ≈ 1 (±0.02), score inden for niveauerne. Brud dumpes med årsag i
`rejected` — de forsvinder ikke stille.

Læs `score` **sammen med** `probabilities` og `confidence`. Kalibreringen fra vores egne
målinger: confidence under 0,5 → 19 % rigtige, over 0,9 → 98,8 %. Et score på 2,4 ved
confidence 0,35 betyder "modellen er delt mellem to niveauer", ikke "2,4 er sikkert".

## Fase 2 — de 14 link-lister

`VoltAgent/awesome-agent-skills`, `hesreallyhim/awesome-claude-code`, `agentsmd/agents.md`,
`intellectronica/ruler`, `K-Dense-AI/claude-skills-mcp` m.fl. bærer ingen `SKILL.md` — de
*peger* på andre repos. Deres README skal parses for `github.com/owner/repo`-links, og de
links skal kurateres ind i `sources.txt` (ellers eksploderer korpusét ukontrolleret — én
af listerne lover 5.400 skills).

## Sikkerhed

Routeren **læser** kun offentlige repos og udfører intet derfra. Installation af en
anbefalet skill er en separat beslutning: kør den gennem en scanner
(`NVIDIA/SkillSpector`, `cisco-ai-defense/skill-scanner`) før den lander i en agent.
En tredjeparts-skill er en prompt-injection-flade, ikke bare en tekstfil.

## Næste skridt

Rust-first: selve MCP-tjenesten skrives i Rust (`reqwest` + `rusqlite`, Jev kaldes over
HTTP — der findes ingen Rust-SDK). Denne Python-fil er data-pipelinen der beviser
loopet; porten sker når rangeringen er målt god nok.
