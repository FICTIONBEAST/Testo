"""Quantitative backbone for the oil thesis.

Reads the CSV snapshots pulled through the Coupler.io Yahoo Finance source
(see README.md) and prints every number quoted in THESIS.md.

    python3 oil_thesis/analysis.py
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"

BRENT = {
    "Nov-26": "BZ=F", "Dec-26": "BZZ26.NYM", "Mar-27": "BZH27.NYM",
    "Jun-27": "BZM27.NYM", "Dec-27": "BZZ27.NYM",
}
WTI = {
    "Nov-26": "CLX26.NYM", "Dec-26": "CLZ26.NYM", "Mar-27": "CLH27.NYM",
    "Jun-27": "CLM27.NYM", "Dec-27": "CLZ27.NYM",
}


def load_curve(path: Path) -> pd.Series:
    """Last traded price per symbol from one snapshot file."""
    df = pd.read_csv(path)
    return df.groupby("symbol")["last"].last()


def curve_stats(last: pd.Series) -> dict:
    b = {k: float(last[v]) for k, v in BRENT.items()}
    w = {k: float(last[v]) for k, v in WTI.items()}
    ho_bbl = float(last["HO=F"]) * 42
    rb_bbl = float(last["RB=F"]) * 42
    return {
        "brent": b,
        "wti": w,
        "brent_m1_m2": b["Nov-26"] - b["Dec-26"],
        "brent_front_dec27": b["Nov-26"] - b["Dec-27"],
        "wti_m1_m2": w["Nov-26"] - w["Dec-26"],
        "wti_front_dec27": w["Nov-26"] - w["Dec-27"],
        "brent_wti_nov": b["Nov-26"] - w["Nov-26"],
        "brent_wti_dec27": b["Dec-27"] - w["Dec-27"],
        "ho_bbl": ho_bbl,
        "ho_crack_wti": ho_bbl - w["Nov-26"],
        "rb_bbl": rb_bbl,
        "rb_crack_wti": rb_bbl - w["Nov-26"],
        "crack_321": (2 * rb_bbl + ho_bbl) / 3 - w["Nov-26"],
        "ovx": float(last["^OVX"]),
        "ovx_daily_move_pct": float(last["^OVX"]) / math.sqrt(252),
        "dxy": float(last["DX-Y.NYB"]),
        # What a long in Dec-26 earns if it converges to an unchanged Nov-26 price
        "brent_roll_to_front_pct": (b["Nov-26"] / b["Dec-26"] - 1) * 100,
    }


def weekly_stats(path: Path) -> dict:
    df = pd.read_csv(path, parse_dates=["week_start"]).sort_values("week_start")
    df["ret"] = df["close"].pct_change()
    full = df.iloc[:-1]  # last row is the partial current week
    lo_i, hi_i = df["low"].idxmin(), df["high"].idxmax()
    june_trough = df.loc[(df.week_start >= "2026-06-01") & (df.week_start <= "2026-07-06"), "low"].min()
    trough_week = df.loc[df["low"] == june_trough, "week_start"].iloc[0]
    return {
        "first_close": (df.iloc[0].week_start.date(), float(df.iloc[0].close)),
        "latest_close": (df.iloc[-1].week_start.date(), float(df.iloc[-1].close)),
        "52w_low": (df.loc[lo_i, "week_start"].date(), float(df.loc[lo_i, "low"])),
        "52w_high": (df.loc[hi_i, "week_start"].date(), float(df.loc[hi_i, "high"])),
        "pre_war_close_w_feb23": float(df.loc[df.week_start == "2026-02-23", "close"].item()),
        "june_trough": float(june_trough),
        "weekly_vol_ann_pct": float(full["ret"].std() * math.sqrt(52) * 100),
        "weekly_vol_since_war_ann_pct": float(full.loc[full.week_start >= "2026-03-02", "ret"].std() * math.sqrt(52) * 100),
        "max_weekly_gain_pct": float(full["ret"].max() * 100),
        "max_weekly_loss_pct": float(full["ret"].min() * 100),
        "peak_to_june_trough_pct": float((june_trough / df.loc[hi_i, "high"] - 1) * 100),
        "weeks_peak_to_trough": int((trough_week - df.loc[hi_i, "week_start"]).days / 7),
    }


def scenario_ev(entry: float, scenarios: list[tuple[str, float, float]]):
    """Expected P&L per barrel for one contract held to the horizon.

    scenarios: (name, probability, terminal price of that same contract).
    Convergence toward the prompt price is already inside each terminal
    price, so no separate roll-yield term is added.
    """
    rows = [(n, p, px, px - entry) for n, p, px in scenarios]
    return sum(p * pnl for _, p, _, pnl in rows), rows


def breakeven_deal_probability(entry: float, scenarios: list[tuple[str, float, float]]) -> float:
    """P(scenario A) at which the long's EV is zero, holding the B:C ratio fixed."""
    (_, _, pxA), (_, pB, pxB), (_, pC, pxC) = scenarios
    lo, hi = 0.0, 1.0
    for _ in range(60):
        pa = (lo + hi) / 2
        s = (1 - pa) / (pB + pC)
        ev, _ = scenario_ev(entry, [("A", pa, pxA), ("B", pB * s, pxB), ("C", pC * s, pxC)])
        lo, hi = (pa, hi) if ev > 0 else (lo, pa)
    return lo


def main() -> None:
    files = sorted(DATA.glob("curve_snapshot_*.csv"))
    prev, cur = load_curve(files[-2]), load_curve(files[-1])
    p, c = curve_stats(prev), curve_stats(cur)

    print(f"== Curve: {files[-2].name}  ->  {files[-1].name}")
    print(f"  {'contract':10s} {'Brent prev':>11s} {'Brent now':>10s} {'chg':>7s}   {'WTI prev':>9s} {'WTI now':>8s} {'chg':>7s}")
    for k in BRENT:
        print(f"  {k:10s} {p['brent'][k]:11.2f} {c['brent'][k]:10.2f} {c['brent'][k]-p['brent'][k]:+7.2f}   "
              f"{p['wti'][k]:9.2f} {c['wti'][k]:8.2f} {c['wti'][k]-p['wti'][k]:+7.2f}")
    keys = ["brent_m1_m2", "brent_front_dec27", "wti_m1_m2", "wti_front_dec27", "brent_wti_nov",
            "brent_wti_dec27", "ho_bbl", "ho_crack_wti", "rb_bbl", "rb_crack_wti", "crack_321",
            "ovx", "ovx_daily_move_pct", "dxy", "brent_roll_to_front_pct"]
    print(f"\n  {'metric':26s} {'prev':>8s} {'now':>8s} {'chg':>7s}")
    for k in keys:
        print(f"  {k:26s} {p[k]:8.2f} {c[k]:8.2f} {c[k]-p[k]:+7.2f}")

    wk = sorted(DATA.glob("brent_weekly_1y_*.csv"))[-1]
    w = weekly_stats(wk)
    print(f"\n== Brent weekly: {wk.name}")
    for k, v in w.items():
        print(f"  {k:32s} {v}")

    entry = c["brent"]["Dec-26"]
    scenarios = [
        ("A: deal / reopening path by 23 Oct", 0.30, 82.0),
        ("B: grind, no deal, Saudi bypass back", 0.45, 102.0),
        ("C: escalation, new Gulf losses", 0.25, 128.0),
    ]
    ev, rows = scenario_ev(entry, scenarios)
    print(f"\n== Scenario EV: long Brent Dec-26 at {entry:.2f}, horizon 23 Oct 2026")
    for n, pr, px, pnl in rows:
        print(f"  {n:40s} p={pr:.2f} px={px:6.1f} pnl={pnl:+6.1f}")
    print(f"  EV/bbl long = {ev:+.1f}   short = {-ev:+.1f}")
    print(f"  Long EV turns negative once P(A) > {breakeven_deal_probability(entry, scenarios):.0%}")


if __name__ == "__main__":
    main()
