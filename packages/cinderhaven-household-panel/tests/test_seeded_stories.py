"""Seeded-story gates (A6).

These assert the two demo stories EMERGE from the computed metrics — they are not
hardcoded anywhere in generation. If a parameter tweak breaks a story, these fail.

Story 1 — "growth that's actually erosion": across the 2025 price-up stretch,
computed sales rise while computed household penetration falls (quarterly grain;
see DECISIONS.md on why annual reach saturates). The flat-price 2024 baseline year
must NOT itself look like erosion, so the signal is specific, not global.

Story 2 — the two launch items tool #4 reuses: the leaky item lands ~15% repeat
(band 10-20%) with a big trial reach; the sticky item lands 45%+ repeat with a
smaller trial reach. Rates are computed from the transactions.
"""

import cinderhaven_household_panel as hp

_PEN_DROP = 0.003  # 0.3pp — a decline beyond noise


def _metrics_by_label():
    m = hp.get_period_metrics().set_index("quarter_label")
    return m["penetration"].to_dict(), m["sales"].to_dict()


def _is_erosion(pen, sales, a, b):
    return sales[b] > sales[a] and pen[b] < pen[a] - _PEN_DROP


def _yoy_erosion_count(pen, sales, year_a, year_b):
    """How many of the 4 quarters erode from year_a to year_b (same-quarter YoY)."""
    return sum(
        _is_erosion(pen, sales, f"{year_a}-Q{q}", f"{year_b}-Q{q}") for q in (1, 2, 3, 4)
    )


def _year_mean_pen_and_total_sales(pen, sales, year):
    labels = [f"{year}-Q{q}" for q in (1, 2, 3, 4)]
    return (
        sum(pen[lbl] for lbl in labels) / 4,
        sum(sales[lbl] for lbl in labels),
    )


class TestErosionStory:
    def test_yoy_quarters_show_erosion(self):
        # The robust signal: across the 2024->2025 price step, most quarters show
        # sales up while household penetration falls.
        pen, sales = _metrics_by_label()
        eroding = _yoy_erosion_count(pen, sales, 2024, 2025)
        assert eroding >= 3, f"only {eroding}/4 YoY quarters show erosion"

    def test_annual_sales_up_penetration_down_2025_vs_2024(self):
        # Headline: 2025 sells more than 2024 while buying fewer households per quarter.
        pen, sales = _metrics_by_label()
        pen24, sales24 = _year_mean_pen_and_total_sales(pen, sales, 2024)
        pen25, sales25 = _year_mean_pen_and_total_sales(pen, sales, 2025)
        assert sales25 > sales24 * 1.02, f"2025 sales {sales25:,.0f} not up on 2024 {sales24:,.0f}"
        assert pen25 < pen24 - 0.005, f"mean penetration {pen24:.3f}->{pen25:.3f} did not fall"

    def test_price_step_is_specific_not_global(self):
        # The flat-price 2023->2024 step must NOT erode the way the 2024->2025
        # price-up step does — otherwise the signal is a global artifact, not the
        # price mechanism.
        pen, sales = _metrics_by_label()
        assert _yoy_erosion_count(pen, sales, 2024, 2025) >= 3
        assert _yoy_erosion_count(pen, sales, 2023, 2024) <= 1


class TestLaunchStories:
    def _trial_and_repeat(self, sku):
        cfg = hp.LAUNCH_ITEMS[sku]
        lq = cfg["launch_quarter_index"]
        tx = hp.get_transactions()
        item = tx[tx["sku_id"] == sku]
        triers = set(item[item["quarter_index"] == lq]["household_id"])
        later = set(item[item["quarter_index"] > lq]["household_id"])
        repeaters = triers & later
        repeat_rate = len(repeaters) / len(triers) if triers else 0.0
        return len(triers), repeat_rate

    def test_leaky_item_low_repeat_big_trial(self):
        triers, repeat = self._trial_and_repeat("CHP-SB-010")
        assert 0.10 <= repeat <= 0.20, f"leaky repeat {repeat:.1%} outside 10-20%"
        assert triers > 800, "leaky item should have a big trial reach"

    def test_sticky_item_high_repeat(self):
        _, repeat = self._trial_and_repeat("CHP-PS-010")
        assert repeat >= 0.45, f"sticky repeat {repeat:.1%} below 45%"

    def test_leaky_has_larger_trial_reach_than_sticky(self):
        leaky_triers, _ = self._trial_and_repeat("CHP-SB-010")
        sticky_triers, _ = self._trial_and_repeat("CHP-PS-010")
        assert leaky_triers > sticky_triers
