"""Brand-scale projection tests.

The panel's absolute totals (sales $, buyer/household counts, trip counts) are scaled
by one fixed factor k so they read at Cinderhaven's brand scale, while rates
(penetration, frequency, spend per trip) stay panel-measured. These tests pin: the
anchor (reference-year sales project to the canonical annual scan revenue), that
rates are untouched, that absolute totals are scaled, that ONE fixed k preserves
period-over-period movement, and that the product identity still reconciles.
"""

import cinderhaven_household_panel as hp

_REF = str(hp.PROJECTION_REFERENCE_YEAR)


def _raw_buyers_by_quarter():
    tx = hp.get_transactions()
    return tx.groupby("quarter_label")["household_id"].nunique()


class TestFactor:
    def test_k_anchors_reference_year_to_canonical_annual_scan(self):
        tx = hp.get_transactions()
        raw_ref_sales = tx.loc[tx["quarter_label"].str.startswith(_REF), "spend"].sum()
        k = hp.get_projection_factor()
        # k is defined so raw ref-year sales project exactly to the canonical anchor.
        assert abs(raw_ref_sales * k - hp.CANONICAL_ANNUAL_SCAN_REVENUE) <= 1e-3
        # Canonical retail scan, CY2025 — canonical_values.yml
        # revenue.retail_scan.cy2025, VERIFIED-AGAINST-PRODUCTION 2026-07-29.
        assert hp.CANONICAL_ANNUAL_SCAN_REVENUE == 32_323_139.62

    def test_projected_reference_year_sales_hit_the_anchor(self):
        m = hp.get_period_metrics()
        ref_annual = m.loc[m["quarter_label"].str.startswith(_REF), "sales"].sum()
        assert abs(ref_annual - hp.CANONICAL_ANNUAL_SCAN_REVENUE) <= 1.0  # dollars

    def test_k_is_fixed_and_greater_than_one(self):
        # A sample-to-universe weight scaling ~5k households up to a real brand.
        assert hp.get_projection_factor() == hp.get_projection_factor()  # deterministic
        assert hp.get_projection_factor() > 1.0


class TestRatesUnchanged:
    def test_penetration_is_the_raw_panel_share_not_scaled(self):
        m = hp.get_period_metrics().set_index("quarter_label")
        raw_pen = _raw_buyers_by_quarter() / hp.N_HOUSEHOLDS
        for label, pen in m["penetration"].items():
            assert abs(pen - raw_pen[label]) <= 1e-9
        assert m["penetration"].between(0.0, 1.0).all()

    def test_spend_per_trip_is_small_dollars_not_scaled(self):
        m = hp.get_period_metrics()
        # A per-trip basket is single/low-double-digit dollars, never at brand scale.
        assert (m["spend_per_trip"] < 1000).all()


class TestAbsoluteTotalsScaled:
    def test_buying_households_is_raw_count_times_k(self):
        m = hp.get_period_metrics().set_index("quarter_label")
        raw = _raw_buyers_by_quarter()
        k = hp.get_projection_factor()
        for label, projected in m["buying_households"].items():
            assert abs(projected - raw[label] * k) <= 1e-6

    def test_quarterly_sales_are_at_brand_scale(self):
        m = hp.get_period_metrics()
        # Millions per quarter, not tens of thousands.
        assert m["sales"].max() > 1_000_000


class TestMovementPreserved:
    def test_one_fixed_k_preserves_period_over_period_ratios(self):
        # Scaling every period by the SAME k must leave real movement untouched:
        # the ratio of projected sales between two quarters equals the raw ratio.
        tx = hp.get_transactions()
        raw = tx.groupby("quarter_label")["spend"].sum()
        proj = hp.get_period_metrics().set_index("quarter_label")["sales"]
        a, b = "2024-Q4", "2025-Q4"
        assert abs((proj[b] / proj[a]) - (raw[b] / raw[a])) <= 1e-9


class TestReconciliationAfterProjection:
    def test_product_identity_holds_at_brand_scale(self):
        m = hp.get_period_metrics()
        lhs = m["buying_households"] * m["frequency"] * m["spend_per_trip"]
        # relative tolerance — values are now in the millions
        assert ((lhs - m["sales"]).abs() <= 1e-6 * m["sales"].abs() + 1e-6).all()
