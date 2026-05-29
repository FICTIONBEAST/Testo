# Heartbreak Recovery — plottable data & interactive charts

Turns an empirical synthesis on the *time course of heartbreak recovery* into
concrete `x,y` values (CSV) and **interactive Plotly charts** (HTML).

## Quick start

```bash
python3 generate.py
```

No third-party Python packages are required — everything uses the standard
library. The generated HTML loads `plotly.js` from its CDN, so **opening the
charts needs internet access** (the data is embedded in the file; only the
rendering library is fetched).

Outputs land under `output/`:

```
output/csv/    decay_curves.csv, decay_curves_fitted.csv,
               sbarra_emery_trajectories.csv, morris_anguish.csv,
               first_week_declines.csv
output/html/   decay_curves.html, sbarra_emery.html, morris_anguish.html,
               first_week_declines.html, dashboard.html  ← open this one
```

## The four charts

1. **Decay curves (headline).** Distress/longing (0–100) over weeks 0–104 for
   Women/Men × betrayal/non-betrayal. Each series shows the discrete data points
   *and* a fitted exponential-with-floor model. Grounded segments (non-betrayal
   weeks 0–4, anchored to Sbarra & Emery 2005) are **solid**; interpolated /
   derived segments are **dashed**. Threshold lines mark the "indifference" (30)
   and "cessation of attraction" (15) levels; vertical markers flag the 11-week
   and ~3-month milestones.
2. **Sbarra & Emery trajectories.** Grounded love / sadness / anger / relief
   means over the first 28 days.
3. **Morris gender anguish.** Peak emotional vs physical anguish by gender (0–10).
4. **First-week declines.** Love −41% / Sadness −60% / Anger −77%.

## Model

The decay curves are fit to

```
distress(t) = floor + (peak − floor) · e^(−t / τ)
```

with `peak` fixed to the week-0 value and `floor`, `τ` found by least squares
(`heartbreak_recovery/model.py`, dependency-free). Typical fit: τ ≈ 8 weeks,
with a higher residual `floor` for men and for betrayal — matching the
synthesis's "steep-then-flat, higher asymptote" reading.

## Data provenance (important)

The four decay curves are a **transparent synthesis**, not a single measured
dataset. Only weeks 0–4 of the non-betrayal curves are anchored to published
data (Sbarra & Emery 2005); later weeks and all betrayal columns are
interpolated/derived from milestone and infidelity-PTSD literature. Source
strings are attached to each dataset in `heartbreak_recovery/data.py` and shown
as captions on every chart.

### Key sources

- Sbarra, D. A., & Emery, R. E. (2005). *Personal Relationships*, 12(2), 213–232.
- Morris, C. E., Reiber, C., & Roman, E. (2015). *Evolutionary Behavioral Sciences*, 9(4), 270–282.
- Acolin, J., et al. (2023). *Emerging Adulthood*, 11(5), 1211–1222.
- Gordon, K. C., Baucom, D. H., & Snyder, D. K. (2004). *J. Marital & Family Therapy*, 30(2), 213–231.

## Layout

```
heartbreak_recovery/
  data.py     datasets as x,y values + provenance flags
  model.py    exponential-with-floor model + dependency-free fitter
  plots.py    Plotly figure builders + HTML writer
generate.py   entry point: writes CSVs and HTML
```
