# oil_thesis

A tactical oil thesis for Q4 2026 (long the front of the curve into the US midterms, flat before them, short the curve after), with the data pulls, the arithmetic and the trigger rules that back it.

| File | What it is |
|---|---|
| `THESIS.md` | The thesis: situation, argument, short case, scenarios, trade construction, trigger board, risks, provenance, engineering notes |
| `thesis.html` | Shareable report with the price-path and futures-curve charts, built by `build_report.py` |
| `analysis.py` | Prints every number quoted in the thesis from the CSVs in `data/` (curve, spreads, cracks, vol, scenario EV) |
| `signals.py` | The trigger board as code: a `MarketSnapshot` in, a `Verdict` (LONG / LONG_ADD / REDUCE / FLAT / SHORT) out |
| `test_signals.py` | Pins the thresholds and the stance logic |
| `build_report.py` | Renders `thesis.html` from the data files |
| `data/curve_snapshot_2026-09-11.csv`, `data/curve_snapshot_2026-09-21.csv` | Front, Dec-26, Mar-27, Jun-27, Dec-27 Brent and WTI, ULSD, RBOB, OVX, DXY (Yahoo Finance via Coupler.io) |
| `data/brent_weekly_1y_2026-09-14.csv` | 53 weekly Brent bars, Sept 2025 to Sept 2026 |

## Run

```bash
pip install -r oil_thesis/requirements.txt      # pandas only; signals.py needs nothing
python3 oil_thesis/analysis.py                  # the numbers
python3 -m unittest oil_thesis.test_signals -v  # the rules
python3 -m oil_thesis.signals                   # today's verdict
python3 oil_thesis/build_report.py              # rebuild thesis.html
```

## Where the data came from

The market data was pulled through the **Coupler.io** connector using its Yahoo Finance Price source (no vendor credential needed), dataflow `98da0d11-063d-4119-af02-d925bf18efba` in the connected workspace, and queried with SQL through the connector's `get-data` tool. The free tier caps each source at 100 rows and the workspace at one connection, so one source was re-pointed between two configurations:

- Curve snapshot: tickers `CL=F,BZ=F,HO=F,RB=F,CLX26.NYM,CLZ26.NYM,CLH27.NYM,CLM27.NYM,CLZ27.NYM,BZX26.NYM,BZZ26.NYM,BZH27.NYM,BZM27.NYM,BZZ27.NYM,^OVX,DX-Y.NYB`, interval `1d`, range `5d`.
- Weekly Brent: ticker `BZ=F`, interval `1wk`, range `1y`.

Macro prints (CPI, unemployment, Fed funds, the Treasury curve, S&P 500, WTI monthly spot) came from **Wolfram Alpha**. Agency reports (IEA, OPEC, EIA) and the news flow came from web search; the agency sites themselves are egress-blocked from the sandbox this was built in, so their figures are as reported by Argus, Reuters, Rigzone, BOE Report and IndexBox. Full table in `THESIS.md` §8.

## Refreshing

1. In Coupler.io, run the dataflow (or set a schedule) and export the rows to a CSV named `data/curve_snapshot_YYYY-MM-DD.csv` with the columns `symbol,date,open,high,low,close,volume,last,last_time_utc`.
2. `python3 oil_thesis/analysis.py` picks the two most recent snapshots automatically and prints the week-over-week table.
3. Update `SNAPSHOT_2026_09_21` in `signals.py` (or construct a new `MarketSnapshot`) with the day's transits, spread, talks status and so on, then run `python3 -m oil_thesis.signals`.
4. `python3 oil_thesis/build_report.py` regenerates the report.

## Turning it into a monitored system

See `THESIS.md` §9. Short version: land the Coupler.io pulls plus EIA API v2, CFTC/ICE COT and IMF PortWatch into one narrow Postgres fact table; keep the trigger thresholds in a versioned `rules` table; run `signals.py` from a cron (GitHub Actions or a small VPS) and alert only on stance changes; rebuild the static report on each run and serve it from object storage. No inbound ports are needed anywhere.
