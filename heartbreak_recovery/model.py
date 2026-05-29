"""Exponential-with-floor decay model and a dependency-free fitter.

The synthesis models breakup distress as a front-loaded decay toward a residual
floor (asymptote)::

    distress(t) = floor + (peak - floor) * exp(-t / tau)

where ``t`` is weeks since the breakup. We fix ``peak`` to the observed week-0
value and fit ``floor`` and ``tau`` by least squares.

The fit uses only the Python standard library: for a fixed ``tau`` the model is
linear in ``floor`` (closed-form least-squares solution), so we grid-search
``tau`` and refine, choosing the ``(floor, tau)`` pair with minimum sum of
squared errors. This avoids any numpy/scipy dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class FitResult:
    peak: float
    floor: float
    tau: float          # weeks; the time constant of the decay
    half_life: float    # weeks for the (peak-floor) gap to halve = tau * ln(2)
    sse: float          # sum of squared errors at the data points
    max_resid: float    # largest absolute residual at the data points

    def predict(self, t: float) -> float:
        return self.floor + (self.peak - self.floor) * math.exp(-t / self.tau)


def _best_floor_for_tau(xs, ys, peak, tau):
    """Closed-form least-squares floor for a fixed tau, clamped to [0, peak].

    Model: y = floor*(1 - e) + peak*e, with e = exp(-t/tau).
    Minimizing sum (y - peak*e - floor*(1-e))^2 over floor gives
    floor = sum(a*b) / sum(a*a) with a = (1-e), b = (y - peak*e).
    """
    num = 0.0
    den = 0.0
    sse = 0.0
    # First pass: solve for floor.
    for x, y in zip(xs, ys):
        e = math.exp(-x / tau)
        a = 1.0 - e
        b = y - peak * e
        num += a * b
        den += a * a
    floor = num / den if den > 1e-12 else 0.0
    floor = max(0.0, min(peak, floor))
    # Second pass: residuals at the clamped floor.
    max_resid = 0.0
    for x, y in zip(xs, ys):
        e = math.exp(-x / tau)
        pred = floor + (peak - floor) * e
        r = y - pred
        sse += r * r
        max_resid = max(max_resid, abs(r))
    return floor, sse, max_resid


def fit_exponential_floor(xs, ys, tau_min=0.5, tau_max=60.0, steps=2000) -> FitResult:
    """Fit distress(t) = floor + (peak-floor)*exp(-t/tau) to (xs, ys).

    ``peak`` is fixed to ys[0]. ``tau`` is found by a dense grid search over
    [tau_min, tau_max] followed by a local refinement, with ``floor`` solved in
    closed form at each candidate tau.
    """
    if len(xs) < 2:
        raise ValueError("need at least two points to fit")
    peak = float(ys[0])

    def search(lo, hi, n):
        best = None
        for i in range(n + 1):
            tau = lo + (hi - lo) * i / n
            if tau <= 0:
                continue
            floor, sse, max_resid = _best_floor_for_tau(xs, ys, peak, tau)
            if best is None or sse < best[1]:
                best = (tau, sse, floor, max_resid)
        return best

    tau, sse, floor, max_resid = search(tau_min, tau_max, steps)
    # Local refinement around the coarse optimum.
    span = (tau_max - tau_min) / steps
    tau, sse, floor, max_resid = search(max(tau_min, tau - span), tau + span, 200)

    return FitResult(
        peak=peak,
        floor=floor,
        tau=tau,
        half_life=tau * math.log(2.0),
        sse=sse,
        max_resid=max_resid,
    )


def dense_grid(fit: FitResult, t_max=104.0, n=300):
    """Return (ts, ys) of the fitted curve on a dense grid for smooth plotting."""
    ts = [t_max * i / n for i in range(n + 1)]
    ys = [fit.predict(t) for t in ts]
    return ts, ys
