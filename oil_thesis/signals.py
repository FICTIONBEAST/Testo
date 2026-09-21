"""Trigger board for the oil thesis (see THESIS.md §6).

Pure Python, no dependencies. Feed it a MarketSnapshot and it returns a
Verdict: the stance the thesis prescribes for that state of the world.

    from oil_thesis.signals import MarketSnapshot, score
    v = score(MarketSnapshot(...))
    print(v.stance, v.bearish_fired, v.bullish_fired)

Thresholds are module constants so a change here must also change the
tests in test_signals.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

# --- Calendar ---------------------------------------------------------------
TIME_STOP = date(2026, 10, 23)      # flatten the long, no exceptions
ELECTION = date(2026, 11, 3)        # phase-2 window opens the day after

# --- Bearish thresholds (§6, B1..B7) -----------------------------------------
HORMUZ_TRANSITS_BEARISH = 25.0      # 5-day average ships/day
M1_M2_BEARISH = 1.50                # $/bbl prompt spread
SAUDI_BYPASS_MBD = 4.0              # East-West flow mb/d
SAUDI_QUIET_DAYS = 14               # days since last strike on Saudi energy assets
MM_NET_LONG_CROWDED = 350_000       # lots, Brent managed money
SPX_DRAWDOWN_BEARISH = 7.0          # % below the 13 Aug 2026 high

# --- Bullish thresholds (§6, U1..U6) -----------------------------------------
HORMUZ_TRANSITS_BULLISH = 5.0

# --- Stance counts -----------------------------------------------------------
BEARISH_TO_REDUCE = 2
BEARISH_TO_FLIP = 3
BULLISH_TO_ADD = 2


class TalksStatus(str, Enum):
    NONE = "none"                 # no channel, or denials
    INDIRECT = "indirect"         # mediators shuttling proposals
    SCHEDULED = "scheduled"       # direct senior talks with a confirmed date
    FRAMEWORK = "framework"       # published framework / memorandum


class Stance(str, Enum):
    LONG = "LONG"
    LONG_ADD = "LONG_ADD"
    REDUCE = "REDUCE"
    FLAT = "FLAT"
    SHORT = "SHORT"


@dataclass(frozen=True)
class MarketSnapshot:
    as_of: date
    brent_m1_m2: float                      # $/bbl, prompt minus second month
    hormuz_transits_5d: float               # ships/day, 5-day average
    talks: TalksStatus = TalksStatus.NONE
    saudi_bypass_mbd: float = 0.0           # East-West pipeline flow
    yanbu_loading_normal: bool = False
    days_since_saudi_strike: int = 0
    mm_brent_net_long: int = 0              # lots
    brent_new_high_20d: bool = False        # price made a 20-day high this week
    export_ban: bool = False
    spx_drawdown_pct: float = 0.0           # % below 13 Aug 2026 high (positive number)
    fed_signalling_hikes: bool = False
    # bullish inputs
    us_strike_campaign: bool = False
    gulf_terminal_struck: bool = False      # Ras Tanura / Juaymah / Fujairah / Habshan / Basra
    bab_el_mandeb_closed: bool = False
    mass_casualty_attack: bool = False      # on a US carrier or a GCC capital
    escorted_transits_halted: bool = False
    distillate_counter_seasonal_draw: bool = False
    # framework invalidators
    signed_reopening_with_us: bool = False
    war_ending_strike: bool = False


@dataclass(frozen=True)
class Trigger:
    code: str
    fired: bool
    detail: str


@dataclass
class Verdict:
    stance: Stance
    bearish: list[Trigger] = field(default_factory=list)
    bullish: list[Trigger] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def bearish_fired(self) -> list[str]:
        return [t.code for t in self.bearish if t.fired]

    @property
    def bullish_fired(self) -> list[str]:
        return [t.code for t in self.bullish if t.fired]


def bearish_triggers(s: MarketSnapshot) -> list[Trigger]:
    return [
        Trigger("B1", s.talks in (TalksStatus.SCHEDULED, TalksStatus.FRAMEWORK),
                f"talks={s.talks.value}"),
        Trigger("B2", s.hormuz_transits_5d > HORMUZ_TRANSITS_BEARISH,
                f"hormuz_5d={s.hormuz_transits_5d:.1f} > {HORMUZ_TRANSITS_BEARISH}"),
        Trigger("B3", s.brent_m1_m2 < M1_M2_BEARISH,
                f"m1_m2={s.brent_m1_m2:.2f} < {M1_M2_BEARISH}"),
        Trigger("B4", s.saudi_bypass_mbd > SAUDI_BYPASS_MBD and s.yanbu_loading_normal
                and s.days_since_saudi_strike >= SAUDI_QUIET_DAYS,
                f"bypass={s.saudi_bypass_mbd:.1f} yanbu={s.yanbu_loading_normal} quiet={s.days_since_saudi_strike}d"),
        Trigger("B5", s.mm_brent_net_long > MM_NET_LONG_CROWDED and not s.brent_new_high_20d,
                f"mm_net_long={s.mm_brent_net_long} new_high={s.brent_new_high_20d}"),
        Trigger("B6", s.export_ban, f"export_ban={s.export_ban}"),
        Trigger("B7", s.spx_drawdown_pct > SPX_DRAWDOWN_BEARISH and s.fed_signalling_hikes,
                f"spx_dd={s.spx_drawdown_pct:.1f}% fed_hikes={s.fed_signalling_hikes}"),
    ]


def bullish_triggers(s: MarketSnapshot) -> list[Trigger]:
    return [
        Trigger("U1", s.us_strike_campaign, "US strike campaign ordered"),
        Trigger("U2", s.gulf_terminal_struck, "Gulf export terminal struck"),
        Trigger("U3", s.bab_el_mandeb_closed, "Bab el-Mandeb closed to Saudi/UAE tonnage"),
        Trigger("U4", s.mass_casualty_attack, "mass-casualty attack on US carrier or GCC capital"),
        Trigger("U5", s.hormuz_transits_5d < HORMUZ_TRANSITS_BULLISH or s.escorted_transits_halted,
                f"hormuz_5d={s.hormuz_transits_5d:.1f}, escorts_halted={s.escorted_transits_halted}"),
        Trigger("U6", s.distillate_counter_seasonal_draw, "counter-seasonal distillate draw"),
    ]


def score(s: MarketSnapshot) -> Verdict:
    """Apply the thesis rules in priority order.

    1. Framework invalidators -> FLAT (then re-enter phase 2 manually).
    2. Three bearish triggers -> SHORT (phase 2) at any date.
    3. After the election -> SHORT (phase 2 is the base case).
    4. After the time stop -> FLAT.
    5. Two bearish triggers -> REDUCE.
    6. Two bullish triggers (and no bearish) -> LONG_ADD.
    7. Otherwise -> LONG.
    """
    bear = bearish_triggers(s)
    bull = bullish_triggers(s)
    v = Verdict(Stance.LONG, bear, bull)
    n_bear = len(v.bearish_fired)
    n_bull = len(v.bullish_fired)

    if s.signed_reopening_with_us or s.war_ending_strike:
        v.stance = Stance.FLAT
        v.reasons.append("framework invalidated: signed reopening with US participation or war-ending strike")
        return v
    if n_bear >= BEARISH_TO_FLIP:
        v.stance = Stance.SHORT
        v.reasons.append(f"{n_bear} bearish triggers fired: {v.bearish_fired}")
        return v
    if s.as_of > ELECTION:
        v.stance = Stance.SHORT
        v.reasons.append("post-election window: phase 2 is the base case")
        return v
    if s.as_of > TIME_STOP:
        v.stance = Stance.FLAT
        v.reasons.append(f"past time stop {TIME_STOP.isoformat()}: pre-election flat")
        return v
    if n_bear >= BEARISH_TO_REDUCE:
        v.stance = Stance.REDUCE
        v.reasons.append(f"{n_bear} bearish triggers fired: {v.bearish_fired}")
        return v
    if n_bull >= BULLISH_TO_ADD and n_bear == 0:
        v.stance = Stance.LONG_ADD
        v.reasons.append(f"{n_bull} bullish triggers fired: {v.bullish_fired}")
        return v
    v.reasons.append(f"bearish={n_bear} bullish={n_bull}: hold the tactical long")
    return v


# The state of the world on the thesis date, for the tests and the README.
SNAPSHOT_2026_09_21 = MarketSnapshot(
    as_of=date(2026, 9, 21),
    brent_m1_m2=4.09,
    hormuz_transits_5d=8.0,
    talks=TalksStatus.INDIRECT,
    saudi_bypass_mbd=0.0,
    yanbu_loading_normal=False,
    days_since_saudi_strike=2,
    mm_brent_net_long=265_000,
    brent_new_high_20d=False,
    export_ban=False,
    spx_drawdown_pct=2.7,
    fed_signalling_hikes=True,
)


if __name__ == "__main__":
    verdict = score(SNAPSHOT_2026_09_21)
    print(f"{SNAPSHOT_2026_09_21.as_of}: {verdict.stance.value}")
    for t in verdict.bearish + verdict.bullish:
        print(f"  {t.code} {'FIRED' if t.fired else '  -  '} {t.detail}")
    for r in verdict.reasons:
        print(f"  -> {r}")
