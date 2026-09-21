"""Pins the trigger thresholds and stance logic of THESIS.md §6.

    python3 -m unittest oil_thesis.test_signals -v
"""
from __future__ import annotations

import dataclasses
import unittest
from datetime import date

from oil_thesis.signals import (
    SNAPSHOT_2026_09_21, Stance, TalksStatus, score,
    HORMUZ_TRANSITS_BEARISH, M1_M2_BEARISH, MM_NET_LONG_CROWDED, SPX_DRAWDOWN_BEARISH,
    TIME_STOP, ELECTION,
)


def snap(**changes):
    return dataclasses.replace(SNAPSHOT_2026_09_21, **changes)


class Thresholds(unittest.TestCase):
    def test_thresholds_match_thesis_document(self):
        self.assertEqual(HORMUZ_TRANSITS_BEARISH, 25.0)
        self.assertEqual(M1_M2_BEARISH, 1.50)
        self.assertEqual(MM_NET_LONG_CROWDED, 350_000)
        self.assertEqual(SPX_DRAWDOWN_BEARISH, 7.0)
        self.assertEqual(TIME_STOP, date(2026, 10, 23))
        self.assertEqual(ELECTION, date(2026, 11, 3))


class StanceOnThesisDate(unittest.TestCase):
    def test_baseline_is_long_with_no_triggers(self):
        v = score(SNAPSHOT_2026_09_21)
        self.assertEqual(v.stance, Stance.LONG)
        self.assertEqual(v.bearish_fired, [])
        self.assertEqual(v.bullish_fired, [])


class BearishTriggers(unittest.TestCase):
    def test_one_trigger_holds_long(self):
        v = score(snap(talks=TalksStatus.SCHEDULED))
        self.assertEqual(v.stance, Stance.LONG)
        self.assertEqual(v.bearish_fired, ["B1"])

    def test_two_triggers_reduce(self):
        v = score(snap(talks=TalksStatus.SCHEDULED, hormuz_transits_5d=30))
        self.assertEqual(v.stance, Stance.REDUCE)
        self.assertEqual(v.bearish_fired, ["B1", "B2"])

    def test_three_triggers_flip_to_short_before_election(self):
        v = score(snap(talks=TalksStatus.FRAMEWORK, hormuz_transits_5d=30, brent_m1_m2=1.0))
        self.assertEqual(v.stance, Stance.SHORT)
        self.assertEqual(v.bearish_fired, ["B1", "B2", "B3"])

    def test_saudi_bypass_needs_all_three_conditions(self):
        self.assertEqual(score(snap(saudi_bypass_mbd=5.0)).bearish_fired, [])
        self.assertEqual(score(snap(saudi_bypass_mbd=5.0, yanbu_loading_normal=True)).bearish_fired, [])
        v = score(snap(saudi_bypass_mbd=5.0, yanbu_loading_normal=True, days_since_saudi_strike=14))
        self.assertEqual(v.bearish_fired, ["B4"])

    def test_crowding_only_counts_when_price_fails(self):
        self.assertEqual(score(snap(mm_brent_net_long=400_000, brent_new_high_20d=True)).bearish_fired, [])
        self.assertEqual(score(snap(mm_brent_net_long=400_000)).bearish_fired, ["B5"])

    def test_demand_shock_needs_fed_and_equities(self):
        self.assertEqual(score(snap(spx_drawdown_pct=9.0, fed_signalling_hikes=False)).bearish_fired, [])
        self.assertEqual(score(snap(spx_drawdown_pct=9.0)).bearish_fired, ["B7"])


class BullishTriggers(unittest.TestCase):
    def test_two_bullish_triggers_add(self):
        v = score(snap(us_strike_campaign=True, gulf_terminal_struck=True))
        self.assertEqual(v.stance, Stance.LONG_ADD)
        self.assertEqual(v.bullish_fired, ["U1", "U2"])

    def test_bullish_does_not_override_bearish(self):
        v = score(snap(us_strike_campaign=True, gulf_terminal_struck=True,
                       talks=TalksStatus.SCHEDULED, hormuz_transits_5d=30))
        self.assertEqual(v.stance, Stance.REDUCE)

    def test_low_transits_is_bullish(self):
        self.assertEqual(score(snap(hormuz_transits_5d=3)).bullish_fired, ["U5"])


class Calendar(unittest.TestCase):
    def test_after_time_stop_is_flat(self):
        self.assertEqual(score(snap(as_of=date(2026, 10, 24))).stance, Stance.FLAT)

    def test_on_time_stop_still_long(self):
        self.assertEqual(score(snap(as_of=TIME_STOP)).stance, Stance.LONG)

    def test_after_election_is_short(self):
        self.assertEqual(score(snap(as_of=date(2026, 11, 4))).stance, Stance.SHORT)

    def test_bullish_after_time_stop_does_not_reopen_long(self):
        v = score(snap(as_of=date(2026, 10, 30), us_strike_campaign=True, gulf_terminal_struck=True))
        self.assertEqual(v.stance, Stance.FLAT)


class Invalidators(unittest.TestCase):
    def test_signed_reopening_goes_flat(self):
        v = score(snap(signed_reopening_with_us=True, us_strike_campaign=True, gulf_terminal_struck=True))
        self.assertEqual(v.stance, Stance.FLAT)

    def test_war_ending_strike_goes_flat_even_with_bearish_triggers(self):
        v = score(snap(war_ending_strike=True, talks=TalksStatus.FRAMEWORK, hormuz_transits_5d=30, brent_m1_m2=0.5))
        self.assertEqual(v.stance, Stance.FLAT)


if __name__ == "__main__":
    unittest.main()
