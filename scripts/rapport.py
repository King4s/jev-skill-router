#!/usr/bin/env python3
"""Build the HTML report from the route JSON files. The raw data stays next to it,
so the report can be regenerated without calling Jev again:

  python3 router.py route "<description>" --out <dir>/<name>.json    # per project
  python3 scripts/rapport.py --dir <dir>                             # -> rapport.html

Run measurements come from artifacts; missing legacy provenance stays unknown."""
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=".")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    d = Path(args.dir)
    out = Path(args.out) if args.out else d / "rapport.html"

    cards, tot_hit, tot_want = [], 0, 0
    known_cases = 0
    for name, (want, label) in FACIT.items():
        f = d / f"{name}.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        ranked, rejected = data.get("ranked", []), data.get("rejected", [])
        got = {r["name"] for r in ranked}
        rank_hits = [w for w in want if w in got]
        candidates = data.get("candidates")
        hits = [w for w in want if w in {c["name"] for c in candidates}] if isinstance(candidates, list) else None
        if hits is not None:
            tot_hit += len(hits)
            tot_want += len(want)
            known_cases += 1
        meta = data.get("meta", {})
        top = meta.get("top", "unknown")
        corpus = meta.get("corpus", {})
        latency = meta.get("latency_s", "unknown")
        provenance = html.escape(f"top {top} · rule {meta.get('rule', 'unknown')} · "
                                 f"model {meta.get('model') or 'unknown'} · Jev latency {latency} s · "
                                 f"corpus {corpus.get('unique', 'unknown')} skills / "
                                 f"{corpus.get('sources', 'unknown')} sources · "
                                 f"snapshot {corpus.get('identity', 'unknown')}")
        recall = f"{len(hits)}/{len(want)}" if hits is not None else "unknown (legacy artifact has no candidates)"
        rows = []
        for i, r in enumerate(ranked[:8], 1):
            hit = "hit" if r["name"] in want else ""
            warn = " low" if r["confidence"] < 0.35 else ""
            rows.append(
                f'<tr class="{hit}"><td class="n">{i}</td>'
                f'<td class="nm">{html.escape(r["name"])}'
                f'<span class="tier" style="color:{TIER_COLOR.get(r["tier"], "")}">'
                f'{html.escape(r["tier"])}</span><span class="repo">{html.escape(r["repo"])}</span></td>'
                f'<td class="sc">{r["score"]:.2f}</td><td>{bar(r["score"], r["confidence"])}</td>'
                f'<td class="cf{warn}">{r["confidence"]:.2f}</td></tr>')
        miss = [w for w in want if w not in {c["name"] for c in candidates}] if isinstance(candidates, list) else []
        cards.append(f"""<section class="card">
<h3>{html.escape(label)}</h3>
<p class="sub">{provenance}</p>
<p class="verd">Retrieval recall: <b>{recall}</b>. Validated ranking coverage: <b>{len(rank_hits)}/{len(want)}</b>.
{'<span class="miss">Missing from shortlist: ' + html.escape(', '.join(miss)) + '</span>' if miss else ''}
{'· ' + str(len(rejected)) + ' answers dropped on contract breach' if rejected else ''}</p>
<table>{''.join(rows)}</table></section>""")

    if not cards:
        raise ValueError("No known project artifacts found")
    rules = json.loads((d / "regler.json").read_text()) if (d / "regler.json").exists() else {}
    rules = rules.get("rules", rules)
    rule_rows = "".join(
        f'<tr><td>{html.escape(k)}</td><td class="sc">{v["hit"]}/{v["want"]}</td>'
        f'<td>{100 * v["hit"] // v["want"]}%</td><td class="note">{html.escape(v.get("note", ""))}</td></tr>'
        for k, v in rules.items())

    delivery = ""
    if (d / "deployment.json").exists():
        deployed = json.loads((d / "deployment.json").read_text())
        stats = deployed["stats"]
        corpus, coverage = stats["corpus"], stats["corpus"]["coverage"]
        for name in FACIT:
            if (d / f"{name}.json").exists():
                route = json.loads((d / f"{name}.json").read_text())
                assert route.get("meta", {}).get("corpus", {}).get("identity") == corpus["identity"]
        assert coverage["discovered"] == sum(coverage[k] for k in
            ("parsed", "missing_metadata", "known_negative_fixture", "parse_failed", "fetch_failed"))
        assert stats["rows"] == corpus["unique"] + stats["duplicates"] == coverage["parsed"]
        evaluations = []
        for n in (40, 300):
            f = d / f"eval{n}.json"
            if f.exists():
                measured = json.loads(f.read_text())
                assert measured["corpus"]["identity"] == corpus["identity"]
                v = measured["rules"][measured["active_rule"]]
                evaluations.append(f"{v['hit']}/{v['want']} at top {measured['top']}")
        runtime_evidence = (f"Snapshot: {corpus['identity']}\nBinary SHA-256: {deployed['binary_sha256']}"
                            f"\nDatabase SHA-256: {deployed['database_sha256']}\n"
                            + deployed['service'] + deployed['listener'])
        delivery = f"""<section class="card"><h2>Verified native deployment</h2>
<p>Measured {html.escape(deployed['verified_at'])}. {html.escape(str(corpus['sources']))} pinned sources;
{coverage['discovered']} paths = {stats['rows']} parsed + {coverage['missing_metadata']} missing metadata
+ {coverage['known_negative_fixture']} exact negative fixture + {coverage['parse_failed']} parse failures
+ {coverage['fetch_failed']} fetch failures. {corpus['unique']} canonical metadata records;
{stats['duplicates']} duplicate source rows.</p>
<p>Current lexical recall: <b>{html.escape('; '.join(evaluations)) or 'not recorded'}</b>.
These regression labels do not establish ranking accuracy. Wider retrieval does not bypass provider budgets.</p>
<p>{html.escape(deployed['wire_checks'])} Second Tailnet host:
{html.escape(deployed['second_host'])}, HTTP {html.escape(str(deployed['second_host_status']))} with identical stats.</p>
<p>{html.escape(deployed['scope'])}</p>
<details><summary>Snapshot, runtime and isolation evidence</summary>
<pre>{html.escape(runtime_evidence)}</pre>
</details></section>"""

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
<p class="sub">Measurements and corpus provenance are shown per artifact. Raw route output stays in this directory.
Unknown legacy values are not substituted with assumed measurements.</p>
{delivery}

<h2>1. What was measured, and on what data</h2>
<p class="sub">Four project descriptions, each with a hand-written list of skills that <i>should</i>
appear (facit). Two are Marcin's real projects (OpenCorde, Tilbud 2.0); two are controls where the
correct answer is obvious (Minecraft server, the router itself — the latter because it must find
better skills than the ones we wrote by hand). Retrieval recall at the recorded shortlist size: does the right skill survive the
shortlist at all? Whether the <i>order</i> is right is Jev's job, not the shortlist's.</p>
<p class="sub">Shortlist recall across {known_cases} artifacts with candidate provenance: <b>{str(tot_hit)+'/'+str(tot_want) if tot_want else 'unknown'}</b>.
Ranking coverage and answer rejections are reported separately.</p>

<h2>2. Rankings present in these artifacts</h2>
{''.join(cards)}

<h2>3. Which shortlist rule won</h2>
<p class="sub">Available scoring-rule measurements, same harness
(<code>scripts/eval_shortlist.py</code>). Measured, not argued:</p>
<table>{rule_rows}</table>

<h2>4. What this does not show</h2>
<ul class="limits sub">
<li><b>The facit lists are mine.</b> They catch "the right skill vanished", not "the order is
sensible". Recall is the cheap half; ranking quality would need a human or an independent judge.</li>
<li><b>A finite shortlist is not a lexical ceiling.</b> In the original four-case snapshot, plain
recall was 11/15 at 40 and 200, but 14/15 at 300. The LLM evaluation skill at rank 248 has lexical
overlap. A larger pool must still be measured for request budget and ranking quality.</li>
<li><b>Near-duplicates crowd the list.</b> Three variants of <code>*-linux-triage</code> from one
repo can take three slots. Metadata-fingerprint dedupe does not prove identical bodies or catch siblings that differ by one word.</li>
<li><b>Skill-ranking confidence is not validated by another task.</b> Calibration measurements
from grocery classification or vendor demos do not establish routing accuracy.</li>
<li><b>Source coverage belongs to the index snapshot.</b> Inspect the recorded discovered, missing-metadata,
fetch and parse counts; failed enumeration is not evidence of a link-list-only repository.</li>
</ul>
</html>"""
    out.write_text(doc)
    print(f"written: {out}  ({len(doc)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
