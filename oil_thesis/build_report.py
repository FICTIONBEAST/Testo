"""Render thesis.html from the data files in data/.

    python3 oil_thesis/build_report.py

Charts are plain inline SVG computed here so the page ships with its data
and needs no library.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "thesis.html"

CONTRACTS = [("Nov-26", 0), ("Dec-26", 1), ("Mar-27", 4), ("Jun-27", 7), ("Dec-27", 13)]
BRENT = ["BZ=F", "BZZ26.NYM", "BZH27.NYM", "BZM27.NYM", "BZZ27.NYM"]
WTI = ["CLX26.NYM", "CLZ26.NYM", "CLH27.NYM", "CLM27.NYM", "CLZ27.NYM"]


def curve(path: Path) -> dict[str, float]:
    return pd.read_csv(path).groupby("symbol")["last"].last().to_dict()


# --------------------------------------------------------------------------- chart 1
def brent_path_chart(df: pd.DataFrame) -> str:
    W, H, ml, mr, mt, mb = 960, 380, 54, 30, 30, 46
    ymin, ymax = 50, 130
    n = len(df)
    xs = [ml + i * (W - ml - mr) / (n - 1) for i in range(n)]

    def y(v: float) -> float:
        return mt + (ymax - v) / (ymax - ymin) * (H - mt - mb)

    pts = list(zip(xs, df["close"].tolist()))
    line = "M" + " L".join(f"{x:.1f},{y(c):.1f}" for x, c in pts)
    area = line + f" L{xs[-1]:.1f},{y(ymin):.1f} L{xs[0]:.1f},{y(ymin):.1f} Z"

    grid = "".join(
        f'<line class="grid" x1="{ml}" x2="{W - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
        f'<text class="tick" x="{ml - 8}" y="{y(v) + 4:.1f}" text-anchor="end">${v}</text>'
        for v in (60, 80, 100, 120)
    )
    xt = ""
    prev_month = None
    for i, d in enumerate(df["week_start"]):
        if d.month in (10, 1, 4, 7) and d.month != prev_month:
            xt += f'<text class="tick" x="{xs[i]:.1f}" y="{H - mb + 20}" text-anchor="middle">{d.strftime("%b %y")}</text>'
        prev_month = d.month

    idx = {d.date(): i for i, d in enumerate(df["week_start"])}
    ann = [
        (date(2026, 3, 2), "close", "War begins", -1, 0),
        (date(2026, 4, 27), "close", "Week of the $126.10 high", -1, 0),
        (date(2026, 6, 29), "close", "$70.14 trough after the 17 Jun MoU", 1, 0),
        (date(2026, 9, 7), "close", "Saudi pipeline shut, $110 high", -1, -14),
    ]
    marks = ""
    for d, col, label, side, dx in ann:
        i = idx[d]
        v = float(df.iloc[i][col])
        px, py = xs[i], y(v)
        ly = py - 22 if side < 0 else py + 30
        anchor = "middle"
        if i > n - 8:
            anchor = "end"
        marks += (
            f'<line class="leader" x1="{px:.1f}" y1="{py:.1f}" x2="{px + dx:.1f}" y2="{ly + (6 if side < 0 else -10):.1f}"/>'
            f'<circle class="mark" cx="{px:.1f}" cy="{py:.1f}" r="4.5"/>'
            f'<text class="ann" x="{px + dx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{label}</text>'
        )
    last_x, last_c = pts[-1]
    end = (
        f'<circle class="mark" cx="{last_x:.1f}" cy="{y(last_c):.1f}" r="5"/>'
        f'<text class="ann strong" x="{last_x + 2:.1f}" y="{y(last_c) + 22:.1f}" text-anchor="end">${last_c:.2f}</text>'
    )
    data = json.dumps([{"d": d.strftime("w/o %d %b %Y"), "c": float(c), "x": round(x, 1), "y": round(y(c), 1)}
                       for d, (x, c) in zip(df["week_start"], pts)])
    return f"""
<figure class="chart" id="fig-path">
  <figcaption><span class="cap-title">Brent front-month, weekly closes</span><span class="cap-sub">ICE Brent via Yahoo Finance (BZ=F), w/o 15 Sep 2025 to w/o 14 Sep 2026, $/bbl</span></figcaption>
  <div class="chart-wrap">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Brent weekly closes over the past year with the war, the April peak, the June trough, the Abqaiq strike and the Saudi pipeline shutdown marked">
    {grid}{xt}
    <line class="axis" x1="{ml}" x2="{W - mr}" y1="{y(ymin):.1f}" y2="{y(ymin):.1f}"/>
    <path class="area long" d="{area}"/>
    <path class="line long" d="{line}"/>
    {marks}{end}
    <line id="xhair" class="xhair" x1="0" x2="0" y1="{mt}" y2="{y(ymin):.1f}" style="display:none"/>
    <circle id="xdot" class="xdot" r="5" style="display:none"/>
  </svg>
  <div class="tip" id="tip-path" hidden="hidden"></div>
  </div>
  <script type="application/json" id="path-data">{data}</script>
</figure>"""


# --------------------------------------------------------------------------- chart 2
def curve_chart(prev: dict, cur: dict, prev_label: str, cur_label: str) -> str:
    W, H, ml, mr, mt, mb = 960, 340, 54, 110, 30, 46
    ymin, ymax = 65, 110
    xmax = CONTRACTS[-1][1]
    xs = [ml + m / xmax * (W - ml - mr) for _, m in CONTRACTS]

    def y(v: float) -> float:
        return mt + (ymax - v) / (ymax - ymin) * (H - mt - mb)

    grid = "".join(
        f'<line class="grid" x1="{ml}" x2="{W - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
        f'<text class="tick" x="{ml - 8}" y="{y(v) + 4:.1f}" text-anchor="end">${v}</text>'
        for v in (70, 80, 90, 100, 110)
    )
    xt = "".join(f'<text class="tick" x="{x:.1f}" y="{H - mb + 20}" text-anchor="middle">{name}</text>'
                 for (name, _), x in zip(CONTRACTS, xs))

    def series(vals: list[float], cls: str, label: str, faded: bool) -> str:
        pth = "M" + " L".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, vals))
        dots = "".join(
            f'<circle class="dot {cls}{" faded" if faded else ""} pt" cx="{x:.1f}" cy="{y(v):.1f}" r="5" '
            f'data-tip="{label} · {name}: ${v:.2f}"/>'
            for (name, _), x, v in zip(CONTRACTS, xs, vals)
        )
        return f'<path class="line {cls}{" faded" if faded else ""}" d="{pth}"/>{dots}'

    b_prev = [prev[s] for s in BRENT]
    b_cur = [cur[s] for s in BRENT]
    w_prev = [prev[s] for s in WTI]
    w_cur = [cur[s] for s in WTI]
    body = (series(b_prev, "long", f"Brent {prev_label}", True) + series(w_prev, "short", f"WTI {prev_label}", True)
            + series(b_cur, "long", f"Brent {cur_label}", False) + series(w_cur, "short", f"WTI {cur_label}", False))
    ends = (
        f'<text class="ann" x="{xs[-1] + 12:.1f}" y="{y(b_cur[-1]) + 4:.1f}">Brent ${b_cur[-1]:.2f}</text>'
        f'<text class="ann" x="{xs[-1] + 12:.1f}" y="{y(w_cur[-1]) + 4:.1f}">WTI ${w_cur[-1]:.2f}</text>'
        f'<text class="ann strong" x="{xs[0] + 10:.1f}" y="{y(b_cur[0]) - 10:.1f}">${b_cur[0]:.2f}</text>'
        f'<text class="ann strong" x="{xs[0] + 10:.1f}" y="{y(w_cur[0]) + 18:.1f}">${w_cur[0]:.2f}</text>'
    )
    legend = f"""
  <div class="legend">
    <span><i class="sw long"></i>Brent {cur_label}</span>
    <span><i class="sw long faded"></i>Brent {prev_label}</span>
    <span><i class="sw short"></i>WTI {cur_label}</span>
    <span><i class="sw short faded"></i>WTI {prev_label}</span>
  </div>"""
    return f"""
<figure class="chart" id="fig-curve">
  <figcaption><span class="cap-title">Futures curve, two snapshots</span><span class="cap-sub">Nov-26 to Dec-27 contracts, $/bbl, last trade at pull time. The front fell $4; Dec-27 rose $1.50.</span></figcaption>
  {legend}
  <div class="chart-wrap">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Brent and WTI futures curves on 11 and 21 September 2026, both steeply backwardated">
    {grid}{xt}
    <line class="axis" x1="{ml}" x2="{W - mr}" y1="{y(ymin):.1f}" y2="{y(ymin):.1f}"/>
    {body}{ends}
  </svg>
  <div class="tip" id="tip-curve" hidden="hidden"></div>
  </div>
</figure>"""


# --------------------------------------------------------------------------- page
def build() -> str:
    wk = pd.read_csv(sorted(DATA.glob("brent_weekly_1y_*.csv"))[-1], parse_dates=["week_start"]).sort_values("week_start")
    files = sorted(DATA.glob("curve_snapshot_*.csv"))
    prev, cur = curve(files[-2]), curve(files[-1])
    prev_label = files[-2].stem[-10:][8:] + " Sep"
    cur_label = files[-1].stem[-10:][8:] + " Sep"
    fig1 = brent_path_chart(wk)
    fig2 = curve_chart(prev, cur, prev_label, cur_label)
    m1m2 = cur["BZ=F"] - cur["BZZ26.NYM"]
    ho_crack = cur["HO=F"] * 42 - cur["CLX26.NYM"]
    html = TEMPLATE
    for k, v in {
        "%%FIG1%%": fig1, "%%FIG2%%": fig2,
        "%%DEC26%%": f"{cur['BZZ26.NYM']:.2f}", "%%NOV26%%": f"{cur['BZ=F']:.2f}",
        "%%WTI%%": f"{cur['CLX26.NYM']:.2f}", "%%DEC27%%": f"{cur['BZZ27.NYM']:.2f}",
        "%%M1M2%%": f"{m1m2:.2f}", "%%HOCRACK%%": f"{ho_crack:.0f}", "%%OVX%%": f"{cur['^OVX']:.0f}",
        "%%DXY%%": f"{cur['DX-Y.NYB']:.1f}", "%%SPREAD1327%%": f"{cur['BZH27.NYM'] - cur['BZZ27.NYM']:.2f}",
    }.items():
        html = html.replace(k, v)
    return html


TEMPLATE = r"""<title>Long the Front, Short the Peace</title>
<meta name="description" content="A tactical oil thesis for Q4 2026: long Brent into the US midterms, flat before them, short the curve after.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  color-scheme:light;
  --bg:#f3f4f6;--surface:#ffffff;--ink:#16191d;--ink-2:#4d5766;--muted:#7c8794;--line:#dde2e8;--line-2:#c6cdd5;
  --accent:#0b6b74;--accent-ink:#ffffff;--accent-soft:#e2f0f1;--long:#2a78d6;--short:#eb6834;
  --good:#0ca30c;--warn:#c98500;--crit:#d03b3b;
  --serif:"Newsreader",Georgia,"Times New Roman",serif;--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --bg:#101316;--surface:#171b20;--ink:#eaedf0;--ink-2:#b4bdc7;--muted:#8b95a1;--line:#2a3138;--line-2:#3b434c;
    --accent:#45b8c1;--accent-ink:#0b1416;--accent-soft:#12333a;--long:#3987e5;--short:#d95926;--warn:#fab219;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#101316;--surface:#171b20;--ink:#eaedf0;--ink-2:#b4bdc7;--muted:#8b95a1;--line:#2a3138;--line-2:#3b434c;
  --accent:#45b8c1;--accent-ink:#0b1416;--accent-soft:#12333a;--long:#3987e5;--short:#d95926;--warn:#fab219;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.55;padding-inline:20px;padding-block:32px 64px}
.page{max-width:1000px;margin:0 auto}
header{display:grid;gap:10px;margin-bottom:28px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-weight:500;font-size:clamp(34px,5vw,50px);line-height:1.05;margin:0;letter-spacing:-.01em;text-wrap:balance}
h1 em{font-style:italic;color:var(--accent)}
.lede{font-size:18px;color:var(--ink-2);max-width:68ch;margin:0}
.stamp{font-family:var(--mono);font-size:12px;color:var(--muted)}
h2{font-family:var(--serif);font-weight:500;font-size:28px;line-height:1.15;margin:44px 0 12px;letter-spacing:-.005em;text-wrap:balance}
h3{font-size:15px;font-weight:600;letter-spacing:.02em;text-transform:uppercase;color:var(--ink-2);margin:26px 0 8px}
p{max-width:68ch;margin:0 0 14px}
ul,ol{max-width:68ch;padding-left:22px;margin:0 0 14px}
li{margin-bottom:6px}
strong{font-weight:600}
.call{background:var(--surface);border:1px solid var(--line);border-left:5px solid var(--accent);padding:22px 24px;margin:8px 0 22px}
.call .verdict{font-family:var(--serif);font-size:24px;line-height:1.25;margin:0 0 10px}
.ticket{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:0;border:1px solid var(--line);background:var(--surface);margin:18px 0 6px}
.ticket>div{padding:14px 16px;border-bottom:1px solid var(--line);border-right:1px solid var(--line)}
.ticket .k{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.ticket .v{font-family:var(--mono);font-size:15px;line-height:1.4}
.ticket .v.big{font-size:22px;font-weight:500}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 6px}
.stat{background:var(--surface);border:1px solid var(--line);padding:14px 16px}
.stat .k{font-size:12px;color:var(--muted);margin-bottom:6px}
.stat .v{font-size:26px;font-weight:600;line-height:1.1;font-family:var(--sans)}
.stat .d{font-family:var(--mono);font-size:12px;color:var(--ink-2);margin-top:6px}
.chart{margin:22px 0 6px;background:var(--surface);border:1px solid var(--line);padding:16px 16px 10px}
figcaption{display:flex;flex-wrap:wrap;gap:4px 16px;align-items:baseline;margin-bottom:8px}
.cap-title{font-weight:600}
.cap-sub{font-size:13px;color:var(--muted)}
.chart-wrap{position:relative}
svg{width:100%;height:auto;display:block;font-family:var(--sans)}
.grid{stroke:var(--line);stroke-width:1}
.axis{stroke:var(--line-2);stroke-width:1}
.tick{fill:var(--muted);font-size:12px;font-family:var(--mono)}
.ann{fill:var(--ink-2);font-size:12.5px}
.ann.strong{fill:var(--ink);font-weight:600;font-family:var(--mono)}
.leader{stroke:var(--line-2);stroke-width:1}
.mark{fill:var(--long);stroke:var(--surface);stroke-width:2}
.line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.line.long,.dot.long{stroke:var(--long)}.dot.long{fill:var(--long)}
.line.short,.dot.short{stroke:var(--short)}.dot.short{fill:var(--short)}
.dot{stroke:var(--surface);stroke-width:2;cursor:crosshair}
.faded{opacity:.38}
.area.long{fill:var(--long);opacity:.10;stroke:none}
.xhair{stroke:var(--line-2);stroke-width:1}
.xdot{fill:var(--long);stroke:var(--surface);stroke-width:2}
.tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);font-family:var(--mono);font-size:12px;padding:6px 9px;border-radius:3px;white-space:nowrap;transform:translate(-50%,-125%);z-index:2}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink-2);margin:2px 0 10px}
.sw{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:7px;border-radius:2px}
.sw.long{background:var(--long)}.sw.short{background:var(--short)}
.table-wrap{overflow-x:auto;margin:14px 0 18px;border:1px solid var(--line);background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;background:var(--bg)}
td.n,th.n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:none}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:760px){.two{grid-template-columns:1fr}}
.board{background:var(--surface);border:1px solid var(--line);padding:16px 18px}
.board h3{margin-top:0}
.board ol{padding-left:0;list-style:none;margin:0}
.board li{display:grid;grid-template-columns:38px 1fr;gap:8px;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.board li:last-child{border-bottom:none}
.code{font-family:var(--mono);font-size:12px;font-weight:600;padding:2px 6px;border-radius:3px;align-self:start;text-align:center}
.code.bear{background:color-mix(in srgb,var(--short) 16%,var(--surface));color:var(--ink)}
.code.bull{background:color-mix(in srgb,var(--long) 16%,var(--surface));color:var(--ink)}
.timeline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.tl{background:var(--surface);border:1px solid var(--line);padding:12px 14px;font-size:13.5px}
.tl .d{font-family:var(--mono);font-size:12px;color:var(--accent);font-weight:500;margin-bottom:4px}
.tl.key{border-color:var(--accent);background:var(--accent-soft)}
.tl .a{color:var(--ink-2);margin-top:4px}
.note{font-size:13.5px;color:var(--ink-2);max-width:72ch}
.pill{display:inline-block;font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;border-radius:2px;background:var(--accent);color:var(--accent-ink);vertical-align:middle;margin-left:8px}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);font-size:13px;color:var(--muted);max-width:80ch}
a{color:var(--accent)}
@media (prefers-reduced-motion:no-preference){.tip{transition:opacity .08s}}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>

<div class="page">
<header>
  <div class="eyebrow">Oil · tactical thesis · Q4 2026</div>
  <h1>Long the front, <em>short the peace</em></h1>
  <p class="lede">The physical market is the tightest it has been all year and the political calendar defers resolution until after 3 November. Own the front of the curve into the election, be flat before it, and be short the curve after it.</p>
  <div class="stamp">Prepared 21 Sep 2026 · market data 12:48 UTC via Coupler.io → Yahoo Finance · macro via Wolfram Alpha · full text and code: oil_thesis/THESIS.md</div>
</header>

<section class="call">
  <p class="verdict">Direction: <strong>long Brent Dec-26</strong>, defined risk, flat by 23 October, reversal pre-written for 4 November.</p>
  <p class="note">Hormuz is running at 5–10 % of normal transits, Saudi Arabia's Hormuz-bypass pipeline has been shut since 10 September, US distillate stocks are 13 % below the five-year average after touching 1996 lows, and the Strategic Petroleum Reserve sits at a 1983 low. The President has said three times since 9 September that the war ends "right after the midterms" and that oil "comes tumbling down" then; Iran's parliament speaker said on 20 September that the strait stays shut until seven conditions are met. Over five weeks the risk premium is more likely to be rebuilt than removed, and a $%%M1M2%% prompt backwardation pays the long ~4 % a month to wait. The same calendar makes post-election de-escalation the base case, so the position carries a hard date, a defined loss, and a reversal written before entry.</p>
  <div class="ticket">
    <div><div class="k">Instrument</div><div class="v">ICE Brent Dec-26 (or CME BZZ26)</div></div>
    <div><div class="k">Reference</div><div class="v big">$%%DEC26%%</div></div>
    <div><div class="k">Entry zone</div><div class="v">$94–98, scaled 22–24 Sep</div></div>
    <div><div class="k">Stop / put strike</div><div class="v">$82 (−$15)</div></div>
    <div><div class="k">Risk budget</div><div class="v">1.5 % of capital → 1 lot per $1.0 m</div></div>
    <div><div class="k">Take profit</div><div class="v">⅓ at $110 · ⅓ at $120 · $10 trail</div></div>
    <div><div class="k">Defined-risk version</div><div class="v">$95/$120 call spread (~$9–10)</div></div>
    <div><div class="k">Time stop</div><div class="v big">23 Oct</div></div>
    <div><div class="k">Phase 2 (after 3 Nov)</div><div class="v">Short Mar-27 / long Dec-27 at ~$%%SPREAD1327%% → $3, stop $16</div></div>
  </div>
</section>

<div class="stats">
  <div class="stat"><div class="k">Brent Nov-26 (prompt)</div><div class="v">$%%NOV26%%</div><div class="d">−$4.23 on the week</div></div>
  <div class="stat"><div class="k">Brent Dec-27</div><div class="v">$%%DEC27%%</div><div class="d">+$1.51 on the week</div></div>
  <div class="stat"><div class="k">WTI Nov-26</div><div class="v">$%%WTI%%</div><div class="d">Brent–WTI $7.74</div></div>
  <div class="stat"><div class="k">ULSD crack vs WTI</div><div class="v">$%%HOCRACK%%</div><div class="d">normal $15–25 /bbl</div></div>
  <div class="stat"><div class="k">OVX</div><div class="v">%%OVX%%</div><div class="d">≈ ±3.2 % a day</div></div>
  <div class="stat"><div class="k">Dollar index</div><div class="v">%%DXY%%</div><div class="d">post-hike, +1.2 on the week</div></div>
</div>

%%FIG1%%

<h2>Where we are</h2>
<h3>Geopolitical</h3>
<p>US–Israeli strikes on Iran began in late February. The Strait of Hormuz has been effectively closed for about 204 days; an April ceasefire and the 17 June memorandum (60 days of toll-free passage, demining within 30 days) both collapsed, the US blockade of Iranian exports was reinstated on 14 July and Kharg loadings stopped on 31 July. This month's ladder: the US sank eight Iranian tankers, Iran struck ten ships, two US vessels and a base in Jordan and declared a "restricted zone" into the Gulf of Oman; drones from Iraq hit the Saudi East–West pipeline in at least eight places on 10–11 September and Riyadh shut it; Houthis struck Yanbu twice and fired the first ballistic missile at Riyadh on 19 September. The GCC–Iran meeting in Salalah was postponed indefinitely; Qatar is shuttling proposals during UN General Assembly week; Trump meets Gulf leaders on 22 September and Xi on 24 September with secondary sanctions on Iran's buyers on the table. Prediction markets put Hormuz traffic returning to normal by 30 September at about 2 %.</p>
<h3>Economic</h3>
<p>Headline CPI 3.4 % with energy at +14.7 %, core 2.5 %, unemployment 4.1 %. The Fed hiked 25 bp on 16 September to 3.75–4.00 % by a 12–0 vote, the first hike since 2023, and 16 of 18 participants project another. The dollar index crossed 100. IEA sees 2026 demand down 2.5 mb/d (Q3 −3.4, Q4 −2.0) with the losses in Asian middle distillates; OPEC still models +0.4 mb/d, a divergence nobody has resolved. Equities sit 2.7 % below their August high. EIA's outlook has Brent averaging ~$90 in 2H26; the post-June bank calls ($75–86) predate the July breakdown and the Saudi damage.</p>
<h3>Physical</h3>
<p>World supply 100.1 mb/d in August, down 5.7 mb/d year on year with more than 10 mb/d of Gulf output shut in and full Middle East recovery deferred to 2027. Saudi output fell to 6.24 mb/d; Riyadh is now exporting under US naval escort along the Omani coast (about 6 mb on one recent day) and expects the East–West line back at 40–60 % within roughly two weeks. Global inventories are down 400 mb year to date; US refineries run at 97.8 %; the diesel crack printed a record $106 on 1 September; VLCC earnings are at a record ~$800k/day and war-risk cover is 40× pre-crisis. From Q3 to Q4 demand recovers ~1.4 mb/d while supply is flat: a 1–1.5 mb/d deficit drawn from depleted stocks in the heating season.</p>

%%FIG2%%

<h2>Why long, and why not short, now</h2>
<ol>
  <li><strong>Supply loss still exceeds demand loss.</strong> −5.7 mb/d of 2026 supply against −2.5 mb/d of demand, and the seasonal demand recovery arrives before any Gulf supply recovery.</li>
  <li><strong>The buffers that broke the March–June spike are gone.</strong> March had a 400 mb coordinated release and normal product stocks. Today the SPR is at 308 mb, distillate is at multi-decade lows and refineries have no slack. The next hit meets a market with no cushion; convexity is to the upside.</li>
  <li><strong>The calendar defers the bearish catalyst.</strong> Washington says no relief before 3 November; Tehran says no reopening before its conditions are met. The pre-election tail, a "big decision" on a major strike, points up.</li>
  <li><strong>Carry favours the long.</strong> At $%%M1M2%% of prompt backwardation a short pays ~4 % a month to wait for a catalyst scheduled for November; a long is paid the same to be wrong on timing.</li>
  <li><strong>The back already prices normalisation.</strong> Dec-27 at $%%DEC27%% is below EIA's $90 and near the old bank forecasts. A short in the back has little to earn; a short in the front is a bet on a pre-election deal.</li>
  <li><strong>Positioning is not crowded.</strong> Managed-money Brent length (~265k lots) is below its May peak and funds sold products into 15 September.</li>
</ol>
<p>The four-day slide from $108 to $101 was headline-driven: Qatar-mediated messages, UNGA meetings, escorted Saudi transits, a pipeline restart "soon". None of that changes the balance before November. The June template (−44 % in nine weeks) needed a signed memorandum, a fuller SPR and normal product stocks; a repeat from here would find a higher floor.</p>

<h2>The short thesis, and when it becomes the trade</h2>
<p>The bear case is the same facts on a different clock: demand destruction compounds (China −8.9 %, the Fed hiking into an energy shock, the dollar above 100); the end of the war is being telegraphed by the one actor who can lift the blockade and markets discount known events early; Saudi barrels are leaking out under escort and Iran is admitting "friendly" tonnage; a US product-export restriction would crush NY Harbor cracks; speculative length gives back 4–6 % on talk alone.</p>
<p><strong>When:</strong> after 3 November as the base case; earlier the moment three bearish triggers fire; immediately if a decisive US strike is read as war-ending, because that is the June pattern in fast-forward. <strong>How:</strong> the curve rather than flat price. Short Mar-27 / long Dec-27 Brent at ~$%%SPREAD1327%%, target $3, stop $16: a deal collapses backwardation while the back barely moves; escalation widens it. Outright, a Mar-27 $85/$70 put spread; never naked short futures into an OVX-%%OVX%% market with a $30 upside tail. <strong>Target after a deal:</strong> $80–85, not $70: mine clearance takes 40–50 days (the Pentagon says up to six months), insurance is quick up and slow down, the SPR must be refilled, Saudi infrastructure is damaged, and distillate demand peaks in Q1.</p>

<h2>Scenarios to 23 October <span class="pill">judgmental</span></h2>
<div class="table-wrap"><table>
<thead><tr><th>Scenario</th><th class="n">P</th><th class="n">Dec-26 on 23 Oct</th><th class="n">P&amp;L / bbl</th><th>What it looks like</th></tr></thead>
<tbody>
<tr><td>A · De-escalation path</td><td class="n">30 %</td><td class="n">$82</td><td class="n">−14.9</td><td>UNGA meeting or Qatar framework with a date; Hormuz &gt; 25 transits/day; escorted flows scale; equities −5 %</td></tr>
<tr><td>B · Grind</td><td class="n">45 %</td><td class="n">$102</td><td class="n">+5.1</td><td>No deal, no new losses; East–West restarts at half capacity; Hormuz 5–15 %; roll carries the long</td></tr>
<tr><td>C · Escalation</td><td class="n">25 %</td><td class="n">$128</td><td class="n">+31.1</td><td>Major US strike campaign; Ras Tanura / Juaymah / Fujairah hit; Bab el-Mandeb closed; Kuwait or Iraq exports halt</td></tr>
</tbody></table></div>
<p>Expected value <strong>+$5.6/bbl for the long</strong> from $%%DEC26%%; it turns negative only if the probability of scenario A before 23 October exceeds 49 %. The shape matters more than the point estimate: the long's loss is bounded by structure and its gain is not; the short's gain is bounded and its loss is not.</p>

<h2>Calendar</h2>
<div class="timeline">
  <div class="tl"><div class="d">22 Sep</div>Trump meets Gulf leaders; UNGA opens; Araghchi in Doha<div class="a">Begin scaling in</div></div>
  <div class="tl"><div class="d">24 Sep</div>Trump–Xi summit; secondary sanctions on Iranian oil buyers<div class="a">Two-way headlines; hold</div></div>
  <div class="tl"><div class="d">30 Sep</div>Nov-26 Brent expires; Dec-26 becomes prompt<div class="a">Convergence check</div></div>
  <div class="tl"><div class="d">early Oct</div>East–West pipeline partial restart expected<div class="a">Watch trigger B4</div></div>
  <div class="tl"><div class="d">mid Oct</div>NOAA winter outlook; IEA/OPEC reports<div class="a">Distillate overlay decision</div></div>
  <div class="tl key"><div class="d">23 Oct</div>Seven trading days before the election<div class="a"><strong>Flatten the long. No exceptions.</strong></div></div>
  <div class="tl"><div class="d">30 Oct</div>Dec-26 Brent expires<div class="a">Nothing open</div></div>
  <div class="tl key"><div class="d">3 Nov</div>US midterms<div class="a">Phase 2 window opens the next day</div></div>
</div>

<h2>Trigger board</h2>
<p class="note">Scored by <code>oil_thesis/signals.py</code>. Cut the long at two bearish triggers, flip to Phase 2 at three; add on two bullish triggers with none bearish. Today: none fired, stance LONG.</p>
<div class="two">
  <div class="board"><h3>Bearish · reduce at 2, flip at 3</h3><ol>
    <li><span class="code bear">B1</span><span>Direct senior US–Iran talks with a confirmed date, or a published framework</span></li>
    <li><span class="code bear">B2</span><span>Hormuz 5-day average above 25 transits/day (about 8 now, 85 normal)</span></li>
    <li><span class="code bear">B3</span><span>Brent M1–M2 spread below $1.50 (from $%%M1M2%%)</span></li>
    <li><span class="code bear">B4</span><span>East–West above 4 mb/d, Yanbu loading normally, 14 days without a strike on Saudi energy assets</span></li>
    <li><span class="code bear">B5</span><span>Managed-money Brent net long above 350k lots while price fails to make a new high</span></li>
    <li><span class="code bear">B6</span><span>US product-export restriction announced</span></li>
    <li><span class="code bear">B7</span><span>S&amp;P 500 more than 7 % below its 13 Aug high with the Fed signalling further hikes</span></li>
  </ol></div>
  <div class="board"><h3>Bullish · hold, add at 2</h3><ol>
    <li><span class="code bull">U1</span><span>US strike campaign against Iranian leadership or energy infrastructure ordered</span></li>
    <li><span class="code bull">U2</span><span>Strike on Ras Tanura, Juaymah, Fujairah, Habshan or Basra loading</span></li>
    <li><span class="code bull">U3</span><span>Bab el-Mandeb effectively closed to Saudi/UAE tonnage</span></li>
    <li><span class="code bull">U4</span><span>Mass-casualty attack on a US carrier or a GCC capital</span></li>
    <li><span class="code bull">U5</span><span>Hormuz below 5 transits/day, or escorted Saudi transits halted</span></li>
    <li><span class="code bull">U6</span><span>Counter-seasonal distillate draw into October</span></li>
  </ol></div>
</div>
<p class="note" style="margin-top:14px"><strong>Invalidation:</strong> a signed, dated reopening with US participation before the election, or a decisive regime-change strike the market reads as war-ending. Either way go flat, then re-enter Phase 2 on the first failed rally.</p>

<h2>What would make this wrong</h2>
<ul>
  <li><strong>The timetable moves forward.</strong> If Qatar lands a framework during UNGA week, scenario A arrives inside the horizon and the long loses its $15 fast. That is why entry is scaled and the loss defined.</li>
  <li><strong>Demand falls faster than supply.</strong> A Fed hiking into 3.4 % inflation is the 2022 template, when oil fell from $120 to $80 in six months despite a war. The physical loss is far larger now and there is no SPR to lean on, but products are unforgiving. Trigger B7.</li>
  <li><strong>Escorted flows scale quietly.</strong> If protected transits reach 20–30 a day and Iran declines to attack them, the premium erodes without a headline. Trigger B2.</li>
  <li><strong>The June memory beats the facts.</strong> Every rally now meets sellers at $105–110; profit-taking is staged for that reason.</li>
  <li><strong>Weather.</strong> A strong El Niño points to a milder northern-tier winter, blunting the distillate kicker; NOAA's mid-October outlook is the check.</li>
  <li><strong>Model risk.</strong> The probabilities are judgment from a single crisis year. Risk control is structural (stop, put strike, time stop), not statistical.</li>
</ul>

<h2>Instruments by account</h2>
<div class="table-wrap"><table>
<thead><tr><th>Account</th><th>Long expression</th><th>Loss cap</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>Futures</td><td>Long Brent Dec-26, stop $82</td><td>$15/bbl plus gap risk</td><td>Do not roll into Jan-27; you should be flat by 23 Oct</td></tr>
<tr><td>Futures + options</td><td>Long Dec-26 + $82/$70 put spread; optionally sell the $130 call</td><td>~$15 + net premium</td><td>Keeps the upside to $130</td></tr>
<tr><td>Options only</td><td>Dec-26 $95/$120 call spread</td><td>Premium (~$9–10)</td><td>Theta bleeds if scenario B is slow</td></tr>
<tr><td>ETF account</td><td>BNO at 25 % below full size, hard stop</td><td>Position size</td><td>Backwardation helps the ETF's roll; USO carries the $7.7 Brent–WTI basis</td></tr>
<tr><td>Equities</td><td>XOP / XLE</td><td>Market risk</td><td>Beta to the S&amp;P ~1; a Fed-driven selloff can lose while oil rises. Not the primary expression</td></tr>
</tbody></table></div>
<p class="note">Brent over WTI because the shortage is seaborne and Asian while US crude stocks are above their five-year average. Crude over products for the core: the ULSD crack at $%%HOCRACK%% is the most extreme number in the complex and a US export restriction would hit NY Harbor ULSD directly; cap any distillate overlay at a quarter of the crude notional.</p>

<footer>
  <p><strong>Data.</strong> Futures curve, products, OVX and DXY pulled through the Coupler.io connector's Yahoo Finance source (dataflow 98da0d11…, snapshots 11 and 21 Sep 2026) and queried with SQL; 52-week Brent bars from the same source; CPI, unemployment, Fed funds, the Treasury curve and the S&amp;P 500 from Wolfram Alpha; IEA/OPEC/EIA figures, Hormuz transit counts, positioning and the news flow from web search with cross-checks between outlets. Full provenance table in THESIS.md §8. Reproduce the numbers with <code>python3 oil_thesis/analysis.py</code>.</p>
  <p>This is a research thesis with a defined risk framework, not personalised investment advice. Futures and options can lose more than the initial margin; ETF expressions can lose their full value. Prices are as of the timestamps shown and will be stale when you read this.</p>
</footer>
</div>

<script>
(function(){
  var fig=document.getElementById('fig-path'); if(!fig) return;
  var svg=fig.querySelector('svg'), tip=document.getElementById('tip-path');
  var pts=JSON.parse(document.getElementById('path-data').textContent);
  var xh=document.getElementById('xhair'), xd=document.getElementById('xdot');
  var vb=svg.viewBox.baseVal;
  function show(e){
    var r=svg.getBoundingClientRect(); var sx=(e.clientX-r.left)/r.width*vb.width;
    var best=0,bd=1e9; for(var i=0;i<pts.length;i++){var d=Math.abs(pts[i].x-sx); if(d<bd){bd=d;best=i;}}
    var p=pts[best];
    xh.setAttribute('x1',p.x); xh.setAttribute('x2',p.x); xh.style.display='';
    xd.setAttribute('cx',p.x); xd.setAttribute('cy',p.y); xd.style.display='';
    tip.textContent=p.d+' · $'+p.c.toFixed(2);
    tip.style.left=(p.x/vb.width*100)+'%'; tip.style.top=(p.y/vb.height*r.height)+'px'; tip.hidden=false;
  }
  function hide(){xh.style.display='none';xd.style.display='none';tip.hidden=true;}
  svg.addEventListener('mousemove',show); svg.addEventListener('mouseleave',hide);
  svg.addEventListener('touchstart',function(e){show(e.touches[0]);},{passive:true});
})();
(function(){
  var fig=document.getElementById('fig-curve'); if(!fig) return;
  var svg=fig.querySelector('svg'), tip=document.getElementById('tip-curve'), vb=svg.viewBox.baseVal;
  fig.querySelectorAll('.pt').forEach(function(c){
    c.addEventListener('mouseenter',function(){
      var r=svg.getBoundingClientRect();
      tip.textContent=c.getAttribute('data-tip');
      tip.style.left=(c.getAttribute('cx')/vb.width*100)+'%'; tip.style.top=(c.getAttribute('cy')/vb.height*r.height)+'px'; tip.hidden=false;
    });
    c.addEventListener('mouseleave',function(){tip.hidden=true;});
  });
})();
</script>
"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
