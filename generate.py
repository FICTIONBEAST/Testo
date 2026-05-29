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

from heartbreak_recovery import data, plots
from heartbreak_recovery.model import dense_grid

ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(ROOT, "output", "csv")
HTML_DIR = os.path.join(ROOT, "output", "html")


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

    decay_fig, fits = plots.build_decay_figure()
    sbarra_fig = plots.build_sbarra_figure()
    morris_fig = plots.build_morris_figure()
    fw_fig = plots.build_first_week_figure()

    # Per-figure HTML files.
    plots.write_html(os.path.join(HTML_DIR, "decay_curves.html"),
                     [("decay", decay_fig, 700)], "Heartbreak recovery — decay curves")
    plots.write_html(os.path.join(HTML_DIR, "sbarra_emery.html"),
                     [("sbarra", sbarra_fig, 600)], "Sbarra & Emery emotion trajectories")
    plots.write_html(os.path.join(HTML_DIR, "morris_anguish.html"),
                     [("morris", morris_fig, 600)], "Morris gender anguish")
    plots.write_html(os.path.join(HTML_DIR, "first_week_declines.html"),
                     [("fw", fw_fig, 600)], "First-week declines")

    # Combined dashboard.
    plots.write_html(
        os.path.join(HTML_DIR, "dashboard.html"),
        [("decay", decay_fig, 700), ("sbarra", sbarra_fig, 560),
         ("morris", morris_fig, 540), ("fw", fw_fig, 540)],
        "Heartbreak recovery — dashboard",
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
    print("\nHTML files written:")
    for name in ("decay_curves.html", "sbarra_emery.html", "morris_anguish.html",
                 "first_week_declines.html", "dashboard.html"):
        print(f"  output/html/{name}")


if __name__ == "__main__":
    main()
