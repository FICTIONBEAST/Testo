"""Datasets for the heartbreak-recovery synthesis, as plottable x,y values.

Every dataset carries a short ``source`` string used in chart captions and a
``grounded`` flag distinguishing data anchored to a published study from values
that are interpolated/derived in the synthesis.

All distress/longing values use the synthesis's 0–100 intensity index
(100 = peak distress at the breakup) unless noted otherwise.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Synthesized decay curves: gender x breakup-type, weeks 0..104.
#    Weeks 0–4 of the two NON-betrayal curves are anchored to Sbarra & Emery
#    (2005); everything else (later weeks, all betrayal columns) is
#    interpolated/derived in the synthesis.
# ---------------------------------------------------------------------------

DECAY_WEEKS = [0, 1, 2, 4, 8, 11, 16, 26, 52, 78, 104]

# The week index (inclusive) up to which the non-betrayal curves are grounded.
GROUNDED_THROUGH_WEEK = 4

DECAY_CURVES = {
    "women_nonbetrayal": {
        "label": "Women — non-betrayal",
        "color": "#d6336c",
        "y": [90, 80, 71, 57, 38, 29, 20, 11, 7, 6, 5],
        # grounded for weeks 0–4 (Sbarra & Emery love+sadness composite)
        "grounded_through_week": GROUNDED_THROUGH_WEEK,
    },
    "women_betrayal": {
        "label": "Women — betrayal",
        "color": "#a61e4d",
        "y": [100, 92, 85, 73, 56, 48, 40, 31, 24, 21, 20],
        "grounded_through_week": -1,  # fully interpolated/derived
    },
    "men_nonbetrayal": {
        "label": "Men — non-betrayal",
        "color": "#1c7ed6",
        "y": [80, 73, 66, 55, 40, 33, 27, 21, 18, 17, 16],
        "grounded_through_week": GROUNDED_THROUGH_WEEK,
    },
    "men_betrayal": {
        "label": "Men — betrayal",
        "color": "#0b4884",
        "y": [90, 84, 79, 70, 58, 53, 48, 43, 39, 37, 36],
        "grounded_through_week": -1,
    },
}

DECAY_SOURCE = (
    "Synthesized: weeks 0–4 non-betrayal anchored to Sbarra & Emery (2005); "
    "later points & all betrayal curves interpolated/derived from milestone + "
    "infidelity-PTSD literature — NOT direct measurements."
)

# Annotation thresholds / milestones for the main decay figure.
THRESHOLDS = {
    "indifference": 30,          # distress level ~ "view ex positively" (~wk 11)
    "cessation_of_attraction": 15,
}
MILESTONES = {
    "11-week (~71% view ex positively)": 11,
    "~3-month (depressive symptoms to baseline)": 13,
}


# ---------------------------------------------------------------------------
# 2. Sbarra & Emery (2005) daily-diary emotion trajectories (grounded).
#    Weekly means at days 1, 7, 14, 21, 28; scales rescaled 0–100.
# ---------------------------------------------------------------------------

SBARRA_DAYS = [1, 7, 14, 21, 28]

SBARRA_TRAJECTORIES = {
    "love": {"label": "Love / longing", "color": "#d6336c", "y": [57, 52, 49, 49, 45]},
    "sadness": {"label": "Sadness", "color": "#7048e8", "y": [46, 37, 32, 32, 31]},
    "anger": {"label": "Anger", "color": "#e8590c", "y": [35, 28, 24, 25, 26]},
    "relief": {"label": "Relief", "color": "#2f9e44", "y": [50, 44, 44, 43, 48]},
}

SBARRA_SOURCE = (
    "Sbarra & Emery (2005), Personal Relationships 12(2):213–232 "
    "(N=58; 28-day diary; weekly means rescaled 0–100). Grounded data."
)


# ---------------------------------------------------------------------------
# 3. Morris, Reiber & Roman (2015) anguish peaks by gender (0–10 scale).
# ---------------------------------------------------------------------------

MORRIS_ANGUISH = {
    "Women": {"emotional": 6.84, "physical": 4.21, "color": "#d6336c"},
    "Men": {"emotional": 6.58, "physical": 3.75, "color": "#1c7ed6"},
}

MORRIS_SOURCE = (
    "Morris, Reiber & Roman (2015), Evolutionary Behavioral Sciences "
    "9(4):270–282 (~5,705 participants, 96 countries). Peak anguish, 0–10."
)


# ---------------------------------------------------------------------------
# 4. First-week percentage declines (Sbarra & Emery 2005).
# ---------------------------------------------------------------------------

FIRST_WEEK_DECLINES = {
    "Love": -41,
    "Sadness": -60,
    "Anger": -77,
}

FIRST_WEEK_SOURCE = (
    "Sbarra & Emery (2005): first-week declines — Love −41%, Sadness −60%, "
    "Anger −77%."
)
