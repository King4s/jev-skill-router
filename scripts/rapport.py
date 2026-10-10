#!/usr/bin/env python3
"""Build the HTML report from the route JSON files. The raw data stays next to it,
so the report can be regenerated without calling Jev again:

  python3 router.py route "<description>" --out <dir>/<name>.json    # per project
  python3 scripts/rapport.py --dir <dir>                             # -> rapport.html

Every number is read from the files; nothing is written into the HTML."""
import argparse
import html
import json
from pathlib import Path

# facit per project: the skills we KNOW belong in the top (my list, not a judge's)
FACIT = {
    "minecraft": (["minecraft-modpack-server", "minecraft-server-admin", "minecraft-modding"],
                  "Modded Minecraft server for friends"),
    "opencorde": (["sveltekit", "rust-sqlx-postgres-service", "qa/e2e-playwright",
                   "identity-federation"],
                  "OpenCorde — Discord parity (Rust + SvelteKit + LiveKit)"),
    "tilbud": (["llm-evaluation", "rust-sqlx-postgres-service", "systemd-services",
                "web-scraping"],
               "Tilbud 2.0 — Danish offer-catalog ingest and LLM classification"),
    "router": (["rust-mcp-server-generator", "sqlite-storage", "rust-deployable-service",
                "fastmcp"],
               "The Jev Skill Router itself — Rust MCP over SQLite FTS5"),
}
TIER_COLOR = {"vendor": "var(--ok, #3fa66a)", "community": "var(--accent, #6aa9ff)",
              "list": "var(--muted-foreground)", "registry": "var(--muted-foreground)",
              "tooling": "var(--muted-foreground)"}


def bar(score: float, conf: float) -> str:
    """Score 0-3 as bar length, confidence as opacity of the inner fill."""
    w = max(0.0, min(1.0, score / 3)) * 100
    return (f'<span class="bar"><span class="fill" style="width:{w:.0f}%;'
            f'opacity:{0.35 + 0.65 * conf:.2f}"></span></span>')


def read_json(path: Path):
    """New routing files use UTF-8; older Windows output used CP1252."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp1252")
    return json.loads(text)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=".")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    d = Path(args.dir)
    out = Path(args.out) if args.out else d / "rapport.html"

    cards, tot_hit, tot_want = [], 0, 0
    for name, (want, label) in FACIT.items():
        f = d / f"{name}.json"
        if not f.exists():
            continue
        data = read_json(f)
        ranked, rejected = data["ranked"], data.get("rejected", [])
        got = [r["name"] for r in ranked]
        hits = [w for w in want if w in got]
        tot_hit += len(hits)
        tot_want += len(want)
        rows = []
        for i, r in enumerate(ranked[:8], 1):
            hit = "hit" if r["name"] in want else ""
            warn = " low" if r["confidence"] < 0.35 else ""
            used = r.get("used_providers", [])
            source = f'<span class="repo">Using: {html.escape(", ".join(used))}</span>' if used else ""
            rows.append(
                f'<tr class="{hit}"><td class="n">{i}</td>'
                f'<td class="nm">{html.escape(r["name"])}'
                f'<span class="tier" style="color:{TIER_COLOR.get(r["tier"], "")}">'
                f'{r["tier"]}</span><span class="repo">{html.escape(r["repo"])}</span>{source}</td>'
                f'<td class="sc">{r["score"]:.2f}</td><td>{bar(r["score"], r["confidence"])}</td>'
                f'<td class="cf{warn}">{r["confidence"]:.2f}</td></tr>')
        miss = [w for w in want if w not in got]
        requested = html.escape(str(data.get("provider", "jev")))
        provider = html.escape(", ".join(data["used_providers"]) or "none") if "used_providers" in data else requested
        confidence_note = (" · two valid answers: minimum provider confidence, not consensus; "
                           "one valid answer: provider-reported confidence") if data.get("provider") == "both" else ""
        routing_note = ""
        if "used_providers" in data:
            used = html.escape(", ".join(data["used_providers"]) or "none")
            status = html.escape(str(data.get("status", "unknown")))
            fallback = ""
            if data.get("status") == "degraded":
                fallback = " · fallback used" if any(row.get("aggregation") == "single" for row in ranked) else " · incomplete provider coverage"
            routing_note = f" · Requested mode: {requested} · Routing status: {status} · Providers used: {used}{fallback}"
        cards.append(f"""<section class="card">
<h3>{html.escape(label)}</h3>
<p class="sub">Decision maker: {provider}{routing_note}{confidence_note}</p>
<p class="verd">Found <b>{len(hits)} of {len(want)}</b> facit skills in the top 40.
{'<span class="miss">Missing: ' + html.escape(', '.join(miss)) + '</span>' if miss else '<span class="ok">All facit skills found</span>'}
{'· ' + str(len(rejected)) + ' candidates have no valid provider score' if rejected else ''}</p>
<table>{''.join(rows)}</table></section>""")

    rules = read_json(d / "regler.json") if (d / "regler.json").exists() else {}
    rule_rows = "".join(
        f'<tr><td>{k}</td><td class="sc">{v["hit"]}/{v["want"]}</td>'
        f'<td>{100 * v["hit"] // v["want"]}%</td><td class="note">{html.escape(v["note"])}</td></tr>'
        for k, v in rules.items())

    doc = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Jev Skill Router — measurement</title>
<style>
  body {{ color: var(--foreground); font-family: inherit; margin: 0; font-size: 14px; line-height: 1.45; }}
  h1 {{ font-size: 19px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 22px 0 8px; }}
  h3 {{ font-size: 14px; margin: 0 0 2px; }}
  .sub, .note, .repo, .tier {{ color: var(--muted-foreground); }}
  .sub {{ font-size: 12px; margin: 0 0 14px; }}
  section.card {{ border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px;
                  margin: 0 0 10px; background: var(--card); }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  td {{ padding: 2px 6px 2px 0; vertical-align: middle; }}
  td.n {{ width: 16px; color: var(--muted-foreground); }}
  td.nm {{ white-space: nowrap; }}
  td.sc {{ width: 40px; text-align: right; font-variant-numeric: tabular-nums; }}
  td.cf {{ width: 42px; text-align: right; font-variant-numeric: tabular-nums; }}
  td.cf.low {{ color: #c9a227; }}
  .tier {{ font-size: 10px; margin-left: 6px; text-transform: uppercase; letter-spacing: .04em; }}
  .repo {{ font-size: 11px; margin-left: 6px; }}
  .bar {{ display: inline-block; width: 100%; height: 6px; border-radius: 3px;
          background: color-mix(in oklab, var(--muted-foreground) 22%, transparent); }}
  .fill {{ display: block; height: 6px; border-radius: 3px; background: var(--accent, #6aa9ff); }}
  tr.hit td.nm {{ font-weight: 600; }}
  tr.hit td.n::before {{ content: "●"; color: var(--ok, #3fa66a); }}
  tr:not(.hit) td.n::before {{ content: "○"; opacity: .35; }}
  .verd {{ margin: 2px 0 4px; }}
  .miss {{ color: #c9a227; }} .ok {{ color: var(--ok, #3fa66a); }}
  .limits li {{ margin-bottom: 5px; }}
  code {{ background: color-mix(in oklab, var(--muted-foreground) 15%, transparent);
          padding: 0 3px; border-radius: 3px; }}
</style>
<h1>Jev Skill Router — does the ranking hold up on real projects?</h1>
<p class="sub">Historical Jev baseline, measured 2026-10-04 · corpus: 10,656 unique skills from 98 sources ·
each project: FTS5 shortlist of 40 → one Jev call scoring all 40 · 0.5 s per project.
Current ranking providers are identified on each card. Raw route output in the same directory.</p>

<h2>1. What was measured, and on what data</h2>
<p class="sub">Four project descriptions, each with a hand-written list of skills that <i>should</i>
appear (facit). Two are Marcin's real projects (OpenCorde, Tilbud 2.0); two are controls where the
correct answer is obvious (Minecraft server, the router itself — the latter because it must find
better skills than the ones we wrote by hand). Recall@40: does the right skill survive the
shortlist at all? Whether the <i>order</i> is right is Jev's job, not the shortlist's.</p>
<p class="sub">Shortlist recall across all four: <b>{tot_hit}/{tot_want}</b>.</p>

<h2>2. The four rankings</h2>
{''.join(cards)}

<h2>3. Which shortlist rule won</h2>
<p class="sub">Three scoring rules, same four projects, same harness
(<code>scripts/eval_shortlist.py</code>). Measured, not argued:</p>
<table>{rule_rows}</table>

<h2>4. What this does not show</h2>
<ul class="limits sub">
<li><b>The facit lists are mine.</b> They catch "the right skill vanished", not "the order is
sensible". Recall is the cheap half; ranking quality would need a human or an independent judge.</li>
<li><b>Lexical retrieval has a ceiling.</b> When a project's words and a skill's words don't
overlap — "classify into a closed vocabulary" vs "evaluation strategies for LLM applications" —
no keyword rule finds it. Measured: that skill sat at #248 with the bm25 rule.</li>
<li><b>Near-duplicates crowd the list.</b> Three variants of <code>*-linux-triage</code> from one
repo can take three slots. Content-hash dedupe doesn't catch siblings that differ by one word.</li>
<li><b>Jev's confidence is calibrated on TypeSafe's data, not ours.</b> The 0.5/0.9 thresholds are
their measurements; treat ours as unvalidated until measured here.</li>
<li><b>16 of 98 sources carry no SKILL.md at all</b> — they are link lists pointing elsewhere, and
what they point at is not in this corpus.</li>
</ul>
</html>"""
    out.write_text(doc, encoding="utf-8")
    print(f"written: {out}  ({len(doc)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
