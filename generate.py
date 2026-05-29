#!/usr/bin/env python3
"""Generate heartbreak-recovery x,y data (CSV) and interactive Plotly HTML.

Run:  python3 generate.py

Outputs (created under ./output):
  output/csv/   — the x,y values for every dataset, plus the fitted decay grid
  output/html/  — one interactive HTML chart per figure + a combined dashboard

Requires only the Python standard library. The HTML charts load plotly.js from
its CDN at view time (so opening them needs internet access).
"""

from __future__ import annotations

import csv
import os

from heartbreak_recovery import data, plots, svg
from heartbreak_recovery.model import dense_grid

ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(ROOT, "output", "csv")
HTML_DIR = os.path.join(ROOT, "output", "html")
SVG_DIR = os.path.join(ROOT, "output", "svg")


def _write_csv(name, header, rows):
    path = os.path.join(CSV_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def export_csvs(fits):
    written = []

    # 1. Decay curves (raw table).
    keys = list(data.DECAY_CURVES)
    header = ["week"] + keys
    rows = [[w] + [data.DECAY_CURVES[k]["y"][i] for k in keys]
            for i, w in enumerate(data.DECAY_WEEKS)]
    written.append(_write_csv("decay_curves.csv", header, rows))

    # 2. Fitted dense decay grid (one column per curve).
    grids = {k: dense_grid(fits[k], t_max=data.DECAY_WEEKS[-1]) for k in keys}
    ts = grids[keys[0]][0]
    header = ["week"] + [f"{k}_fit" for k in keys]
    rows = [[round(ts[i], 3)] + [round(grids[k][1][i], 4) for k in keys]
            for i in range(len(ts))]
    written.append(_write_csv("decay_curves_fitted.csv", header, rows))

    # 3. Sbarra & Emery trajectories.
    emos = list(data.SBARRA_TRAJECTORIES)
    header = ["day"] + emos
    rows = [[d] + [data.SBARRA_TRAJECTORIES[e]["y"][i] for e in emos]
            for i, d in enumerate(data.SBARRA_DAYS)]
    written.append(_write_csv("sbarra_emery_trajectories.csv", header, rows))

    # 4. Morris anguish.
    rows = [[g, data.MORRIS_ANGUISH[g]["emotional"], data.MORRIS_ANGUISH[g]["physical"]]
            for g in data.MORRIS_ANGUISH]
    written.append(_write_csv("morris_anguish.csv", ["gender", "emotional", "physical"], rows))

    # 5. First-week declines.
    rows = [[e, v] for e, v in data.FIRST_WEEK_DECLINES.items()]
    written.append(_write_csv("first_week_declines.csv", ["emotion", "pct_decline"], rows))

    return written


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(SVG_DIR, exist_ok=True)

    # --- Self-contained SVG charts (primary; work offline, incl. mobile) ----
    decay_svg, fits = svg.build_decay_svg()
    sbarra_svg = svg.build_sbarra_svg()
    morris_svg = svg.build_morris_svg()
    fw_svg = svg.build_first_week_svg()

    svg.write_svg(os.path.join(SVG_DIR, "decay_curves.svg"), decay_svg)
    svg.write_svg(os.path.join(SVG_DIR, "sbarra_emery.svg"), sbarra_svg)
    svg.write_svg(os.path.join(SVG_DIR, "morris_anguish.svg"), morris_svg)
    svg.write_svg(os.path.join(SVG_DIR, "first_week_declines.svg"), fw_svg)

    svg.write_html(
        os.path.join(HTML_DIR, "dashboard.html"),
        [decay_svg, sbarra_svg, morris_svg, fw_svg],
        "Heartbreak recovery — dashboard",
        intro=("Self-contained charts (static SVG, no internet required). For "
               "interactive hover/zoom versions see the interactive_*.html files, "
               "which load plotly.js from a CDN and need internet access."),
    )

    # --- Interactive Plotly versions (need internet for plotly.js CDN) -------
    decay_fig, _ = plots.build_decay_figure()
    sbarra_fig = plots.build_sbarra_figure()
    morris_fig = plots.build_morris_figure()
    fw_fig = plots.build_first_week_figure()
    plots.write_html(
        os.path.join(HTML_DIR, "interactive_dashboard.html"),
        [("decay", decay_fig, 700), ("sbarra", sbarra_fig, 560),
         ("morris", morris_fig, 540), ("fw", fw_fig, 540)],
        "Heartbreak recovery — interactive dashboard (needs internet)",
    )

    csvs = export_csvs(fits)

    # Summary.
    print("Fitted exponential-with-floor parameters (distress = floor + (peak-floor)*e^(-t/tau)):")
    print(f"  {'curve':22} {'peak':>6} {'floor':>6} {'tau(wk)':>8} {'half-life':>10} {'max_resid':>10}")
    for key, fit in fits.items():
        print(f"  {key:22} {fit.peak:6.1f} {fit.floor:6.1f} {fit.tau:8.2f} "
              f"{fit.half_life:10.2f} {fit.max_resid:10.2f}")

    print("\nCSV files written:")
    for p in csvs:
        print(f"  {os.path.relpath(p, ROOT)}")
    print("\nSVG files written:")
    for name in ("decay_curves.svg", "sbarra_emery.svg", "morris_anguish.svg",
                 "first_week_declines.svg"):
        print(f"  output/svg/{name}")
    print("\nHTML files written:")
    print("  output/html/dashboard.html              (offline, inline SVG — open this)")
    print("  output/html/interactive_dashboard.html  (Plotly; needs internet)")


if __name__ == "__main__":
    main()
