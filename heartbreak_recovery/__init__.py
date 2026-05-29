"""Heartbreak recovery: plottable x,y data and interactive visualizations.

This package encodes the datasets from an empirical synthesis on the time
course of heartbreak recovery, fits an exponential-with-floor decay model to
the synthesized distress curves, and builds interactive Plotly figures.

See ``data.py`` for the datasets and their provenance, ``model.py`` for the
decay model, and ``plots.py`` for the figure builders.
"""

from . import data, model, plots

__all__ = ["data", "model", "plots"]
