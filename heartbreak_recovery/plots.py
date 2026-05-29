"""Build interactive Plotly figures as plain dicts and render them to HTML.

No Python Plotly package is required: each figure is a ``{"data": [...],
"layout": {...}}`` dict that we serialize to JSON and hand to ``Plotly.newPlot``
in the browser. ``plotly.js`` itself is loaded from the official CDN, so the
generated ``.html`` files are self-contained Python-side and render anywhere
with internet access.
"""

from __future__ import annotations

import html
import json

from . import data
from .model import dense_grid, fit_exponential_floor

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


# ---------------------------------------------------------------------------
# Figure builders -> {"data": [...], "layout": {...}}
# ---------------------------------------------------------------------------

def build_decay_figure():
    """Main figure: 4 distress-decay curves, data markers + fitted overlay.

    Grounded portions (non-betrayal weeks 0–4) are drawn solid; interpolated /
    derived portions are dashed. Also returns the per-curve fit results.
    """
    weeks = data.DECAY_WEEKS
    traces = []
    fits = {}

    for key, curve in data.DECAY_CURVES.items():
        ys = curve["y"]
        color = curve["color"]
        label = curve["label"]
        grounded_week = curve["grounded_through_week"]

        fit = fit_exponential_floor(weeks, ys)
        fits[key] = fit
        ts, fitted = dense_grid(fit, t_max=weeks[-1])

        hover = (
            "%{x:.0f} wk<br>distress %{y:.1f}<br>"
            f"fit: floor {fit.floor:.1f}, τ {fit.tau:.1f} wk"
            "<extra>" + label + "</extra>"
        )

        # Fitted overlay, split into grounded (solid) and interpolated (dashed).
        if grounded_week >= 0:
            g_ts = [t for t in ts if t <= grounded_week]
            g_ys = [y for t, y in zip(ts, fitted) if t <= grounded_week]
            traces.append({
                "type": "scatter", "mode": "lines", "x": g_ts, "y": g_ys,
                "line": {"color": color, "width": 3},
                "legendgroup": key, "showlegend": False,
                "hovertemplate": hover,
            })
            i_ts = [t for t in ts if t >= grounded_week]
            i_ys = [y for t, y in zip(ts, fitted) if t >= grounded_week]
            traces.append({
                "type": "scatter", "mode": "lines", "x": i_ts, "y": i_ys,
                "line": {"color": color, "width": 2, "dash": "dash"},
                "legendgroup": key, "showlegend": False,
                "hovertemplate": hover,
            })
        else:
            traces.append({
                "type": "scatter", "mode": "lines", "x": ts, "y": fitted,
                "line": {"color": color, "width": 2, "dash": "dash"},
                "legendgroup": key, "showlegend": False,
                "hovertemplate": hover,
            })

        # Data-point markers (legend entry for the series). Grounded points are
        # filled circles; interpolated points are open circles.
        symbols = [
            "circle" if (grounded_week >= 0 and w <= grounded_week) else "circle-open"
            for w in weeks
        ]
        traces.append({
            "type": "scatter", "mode": "markers", "x": weeks, "y": ys,
            "name": label, "legendgroup": key,
            "marker": {"color": color, "size": 9, "symbol": symbols,
                       "line": {"color": color, "width": 1.5}},
            "hovertemplate": "%{x:.0f} wk<br>distress %{y}<extra>" + label + " (data)</extra>",
        })

    # Threshold lines + milestone markers as layout shapes/annotations.
    shapes = []
    annotations = []
    for name, level in data.THRESHOLDS.items():
        shapes.append({
            "type": "line", "x0": 0, "x1": weeks[-1], "y0": level, "y1": level,
            "line": {"color": "gray", "width": 1, "dash": "dot"},
        })
        annotations.append({
            "x": weeks[-1], "y": level, "xanchor": "right", "yanchor": "bottom",
            "text": name.replace("_", " ").title() + f" ({level})",
            "showarrow": False, "font": {"size": 10, "color": "gray"},
        })
    for label, wk in data.MILESTONES.items():
        shapes.append({
            "type": "line", "x0": wk, "x1": wk, "y0": 0, "y1": 105,
            "line": {"color": "#2f9e44", "width": 1, "dash": "dot"},
        })
        annotations.append({
            "x": wk, "y": 104, "xanchor": "left", "yanchor": "top",
            "text": " " + label, "textangle": 90,
            "showarrow": False, "font": {"size": 9, "color": "#2f9e44"},
        })
    annotations.append({
        "x": 0.5, "y": -0.16, "xref": "paper", "yref": "paper",
        "text": "<i>" + data.DECAY_SOURCE + "</i>",
        "showarrow": False, "font": {"size": 9}, "xanchor": "center",
    })

    layout = {
        "title": {"text": "Synthesized heartbreak recovery curves by gender and breakup type"},
        "xaxis": {"title": {"text": "Weeks since breakup"}, "range": [-2, 106]},
        "yaxis": {"title": {"text": "Distress / longing intensity (0–100)"}, "range": [0, 108]},
        "shapes": shapes, "annotations": annotations,
        "legend": {"orientation": "h", "y": 1.08, "x": 0},
        "hovermode": "closest", "template": "plotly_white",
        "margin": {"b": 110},
    }
    return {"data": traces, "layout": layout}, fits


def build_sbarra_figure():
    """Sbarra & Emery (2005) grounded emotion trajectories over days 1–28."""
    traces = []
    for emo in data.SBARRA_TRAJECTORIES.values():
        traces.append({
            "type": "scatter", "mode": "lines+markers",
            "x": data.SBARRA_DAYS, "y": emo["y"], "name": emo["label"],
            "line": {"color": emo["color"], "width": 2},
            "marker": {"color": emo["color"], "size": 8},
            "hovertemplate": "day %{x}<br>%{y}<extra>" + emo["label"] + "</extra>",
        })
    layout = {
        "title": {"text": "Sbarra & Emery (2005): emotion trajectories, first 28 days (grounded)"},
        "xaxis": {"title": {"text": "Days since breakup"}, "dtick": 7},
        "yaxis": {"title": {"text": "Intensity (0–100)"}, "range": [0, 65]},
        "template": "plotly_white", "hovermode": "x unified",
        "annotations": [{
            "x": 0.5, "y": -0.18, "xref": "paper", "yref": "paper",
            "text": "<i>" + data.SBARRA_SOURCE + "</i>",
            "showarrow": False, "font": {"size": 9}, "xanchor": "center",
        }],
        "margin": {"b": 90},
    }
    return {"data": traces, "layout": layout}


def build_morris_figure():
    """Grouped bar chart of peak anguish (emotional vs physical) by gender."""
    genders = list(data.MORRIS_ANGUISH.keys())
    traces = [
        {
            "type": "bar", "name": "Emotional anguish",
            "x": genders, "y": [data.MORRIS_ANGUISH[g]["emotional"] for g in genders],
            "marker": {"color": "#d6336c"},
            "text": [f"{data.MORRIS_ANGUISH[g]['emotional']:.2f}" for g in genders],
            "textposition": "outside",
        },
        {
            "type": "bar", "name": "Physical anguish",
            "x": genders, "y": [data.MORRIS_ANGUISH[g]["physical"] for g in genders],
            "marker": {"color": "#1c7ed6"},
            "text": [f"{data.MORRIS_ANGUISH[g]['physical']:.2f}" for g in genders],
            "textposition": "outside",
        },
    ]
    layout = {
        "title": {"text": "Peak breakup anguish by gender (Morris, Reiber & Roman 2015)"},
        "barmode": "group",
        "xaxis": {"title": {"text": "Gender"}},
        "yaxis": {"title": {"text": "Anguish (0–10)"}, "range": [0, 8]},
        "template": "plotly_white",
        "annotations": [{
            "x": 0.5, "y": -0.2, "xref": "paper", "yref": "paper",
            "text": "<i>" + data.MORRIS_SOURCE + "</i>",
            "showarrow": False, "font": {"size": 9}, "xanchor": "center",
        }],
        "margin": {"b": 90},
    }
    return {"data": traces, "layout": layout}


def build_first_week_figure():
    """Bar chart of first-week percentage declines by emotion."""
    emotions = list(data.FIRST_WEEK_DECLINES.keys())
    vals = [data.FIRST_WEEK_DECLINES[e] for e in emotions]
    traces = [{
        "type": "bar", "x": emotions, "y": vals,
        "marker": {"color": ["#d6336c", "#7048e8", "#e8590c"]},
        "text": [f"{v}%" for v in vals], "textposition": "outside",
        "hovertemplate": "%{x}: %{y}%<extra></extra>",
    }]
    layout = {
        "title": {"text": "First-week decline in distress by emotion (Sbarra & Emery 2005)"},
        "xaxis": {"title": {"text": "Emotion"}},
        "yaxis": {"title": {"text": "Change over first week (%)"}, "range": [-90, 5]},
        "template": "plotly_white", "showlegend": False,
        "annotations": [{
            "x": 0.5, "y": -0.2, "xref": "paper", "yref": "paper",
            "text": "<i>" + data.FIRST_WEEK_SOURCE + "</i>",
            "showarrow": False, "font": {"size": 9}, "xanchor": "center",
        }],
        "margin": {"b": 90},
    }
    return {"data": traces, "layout": layout}


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _figure_block(div_id, figure, height):
    payload = json.dumps(figure)
    return (
        f'<div id="{div_id}" style="width:100%;height:{height}px;"></div>\n'
        f'<script>\n'
        f'  var fig_{div_id} = {payload};\n'
        f'  Plotly.newPlot("{div_id}", fig_{div_id}.data, fig_{div_id}.layout, '
        f'{{responsive:true}});\n'
        f'</script>\n'
    )


def write_html(path, figures, page_title):
    """Write one or more figures to a standalone HTML file.

    ``figures`` is a list of ``(div_id, figure_dict, height_px)`` tuples.
    """
    blocks = "\n".join(_figure_block(d, f, h) for d, f, h in figures)
    doc = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"  <title>{html.escape(page_title)}</title>\n"
        f"  <script src=\"{PLOTLY_CDN}\"></script>\n"
        "  <style>body{font-family:system-ui,Arial,sans-serif;margin:24px;"
        "max-width:1100px;} h1{font-size:1.3rem;}</style>\n"
        "</head>\n<body>\n"
        f"  <h1>{html.escape(page_title)}</h1>\n"
        f"{blocks}\n"
        "</body>\n</html>\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
