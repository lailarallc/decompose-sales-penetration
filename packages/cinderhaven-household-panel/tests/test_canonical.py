"""Canonical / locked-constant tests for the household panel.

Mirrors the cinderhaven-store-universe test_canonical.py pattern. Grows with each
Slice 1 sub-task; this file currently covers A1 (constants + calendar).
"""

import cinderhaven_household_panel as hp
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def tx():
    return hp.get_transactions()


class TestConstants:
    def test_seed_locked(self):
        assert hp.SEED == 42

    def test_household_count_locked(self):
        assert hp.N_HOUSEHOLDS == 5000

    def test_quarter_split_locked(self):
        assert hp.BURN_IN_QUARTERS == 4
        assert hp.ANALYSIS_QUARTERS == 8
        assert hp.TOTAL_QUARTERS == 12

    def test_panel_version_set(self):
        assert isinstance(hp.PANEL_VERSION, str) and hp.PANEL_VERSION

    def test_canonical_universe_reused(self):
        # Reused from the SSOT — must match the canonical universe exactly.
        assert len(hp.ALL_SKUS) == 50
        assert set(hp.PRODUCT_LINES.keys()) == {"AS", "PS", "SC", "DG", "SB"}
        assert len(hp.RETAILERS) == 6
        assert hp.DEMO_AS_OF_DATE == pd.Timestamp("2025-12-29")


class TestCalendar:
    def test_twelve_quarters(self):
        q = hp.get_quarters()
        assert len(q) == 12
        assert q["quarter_index"].tolist() == list(range(12))

    def test_burn_in_then_analysis(self):
        q = hp.get_quarters()
        assert (q["phase"] == "burn_in").sum() == 4
        assert (q["phase"] == "analysis").sum() == 8
        # burn-in strictly precedes the analysis window
        assert q.loc[q["is_analysis"], "quarter_index"].min() == 4

    def test_labels_and_pos_alignment(self):
        q = hp.get_quarters()
        assert q["label"].iloc[0] == "2023-Q1"
        assert q["label"].iloc[-1] == "2025-Q4"
        # analysis window aligns to the store-universe POS window (2024-2025)
        analysis = q[q["is_analysis"]]
        assert analysis["label"].iloc[0] == "2024-Q1"
        assert analysis["label"].iloc[-1] == "2025-Q4"
        assert hp.ANALYSIS_QUARTER_LABELS[0] == "2024-Q1"
        assert hp.BURN_IN_QUARTER_LABELS == ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"]

    def test_dates_contiguous_and_non_overlapping(self):
        q = hp.get_quarters().sort_values("quarter_index").reset_index(drop=True)
        for i in range(len(q)):
            assert q.loc[i, "start_date"] < q.loc[i, "end_date"]
            if i > 0:
                # each quarter starts the day after the previous one ends
                assert q.loc[i, "start_date"] == q.loc[i - 1, "end_date"] + pd.Timedelta(days=1)

    def test_reproducible(self):
        pd.testing.assert_frame_equal(hp.get_quarters(), hp.get_quarters())


class TestHouseholds:
    def test_count_locked(self):
        assert len(hp.get_households()) == 5000

    def test_reproducible(self):
        pd.testing.assert_frame_equal(hp.get_households(), hp.get_households())

    def test_regions_are_canonical(self):
        h = hp.get_households()
        assert set(h["region"]) == set(hp.REGIONS)

    def test_latent_attrs_in_unit_range(self):
        h = hp.get_households()
        for col in ("price_sensitivity", "innovator_affinity"):
            assert h[col].between(0.0, 1.0).all(), f"{col} outside [0,1]"

    def test_propensity_right_skewed_and_overdispersed(self):
        x = hp.get_households()["base_propensity"].to_numpy()
        assert (x >= 0).all()
        m, s = x.mean(), x.std()
        skew = (((x - m) / s) ** 3).mean()  # Fisher-Pearson sample skewness
        assert skew > 1.0, f"propensity skew {skew:.2f} not right-skewed enough"
        assert x.var() / x.mean() > 1.0, "propensity should be overdispersed"

    def test_ids_unique_and_formatted(self):
        h = hp.get_households()
        assert h["household_id"].is_unique
        assert h["household_id"].iloc[0] == "HH-00001"
        assert h["household_id"].iloc[-1] == "HH-05000"


class TestPricing:
    _LINE_RANGES = {
        "AS": (7.50, 11.50), "PS": (3.50, 6.50), "SC": (5.50, 9.50),
        "DG": (4.50, 8.50), "SB": (2.75, 5.25),
    }

    def test_prices_positive_and_in_line_range(self):
        p = hp.get_sku_prices()
        assert len(p) == 50
        assert set(p["product_line"]) == {"AS", "PS", "SC", "DG", "SB"}
        assert (p["base_price"] > 0).all()
        for _, row in p.iterrows():
            lo, hi = self._LINE_RANGES[row["product_line"]]
            assert lo <= row["base_price"] <= hi

    def test_price_path_flat_then_2025_ramp(self):
        path = hp.get_price_path()
        assert len(path) == 12
        pre_2025 = path[path["label"].str.startswith(("2023", "2024"))]
        assert (pre_2025["price_index"] == 1.00).all()
        y2025 = path[path["label"].str.startswith("2025")].sort_values("quarter_index")
        assert (y2025["price_index"] > 1.00).all()
        # strictly rising across the 2025 stretch
        assert y2025["price_index"].is_monotonic_increasing
        assert y2025["price_index"].iloc[-1] >= 1.14

    def test_reproducible(self):
        pd.testing.assert_frame_equal(hp.get_sku_prices(), hp.get_sku_prices())
        pd.testing.assert_frame_equal(hp.get_price_path(), hp.get_price_path())

    def test_launch_items_defined(self):
        li = hp.get_launch_items()
        assert len(li) == 2
        assert set(li["sku_id"]).issubset(set(hp.ALL_SKUS))
        assert set(li["role"]) == {"leaky", "sticky"}
        leaky = li[li["role"] == "leaky"].iloc[0]
        sticky = li[li["role"] == "sticky"].iloc[0]
        # leaky = bigger trial reach, lower repeat propensity than sticky
        assert leaky["trial_reach"] > sticky["trial_reach"]
        assert leaky["repeat_propensity"] < sticky["repeat_propensity"]
        # launch sits in burn-in so trial + repeat runway precede the analysis window
        assert (li["launch_quarter_index"] < hp.BURN_IN_QUARTERS).all()


class TestTransactions:
    def test_schema_and_nonempty(self, tx):
        assert len(tx) > 0
        assert list(tx.columns) == [
            "household_id", "quarter_index", "quarter_label", "date",
            "sku_id", "product_line", "retailer_id", "units", "unit_price", "spend",
        ]

    def test_retailers_are_canonical(self, tx):
        assert set(tx["retailer_id"]).issubset(set(hp.RETAILERS))

    def test_reproducible(self):
        pd.testing.assert_frame_equal(hp.get_transactions(), hp.get_transactions())

    def test_spend_and_units_positive(self, tx):
        assert (tx["spend"] > 0).all()
        assert (tx["units"] >= 1).all()
        # spend is units * unit_price to the cent
        assert (tx["spend"] == (tx["units"] * tx["unit_price"]).round(2)).all()

    def test_only_canonical_skus(self, tx):
        assert set(tx["sku_id"]).issubset(set(hp.ALL_SKUS))

    def test_dates_inside_their_quarter(self, tx):
        q = hp.get_quarters().set_index("quarter_index")[["start_date", "end_date"]]
        merged = tx.join(q, on="quarter_index")
        assert (merged["date"] >= merged["start_date"]).all()
        assert (merged["date"] <= merged["end_date"]).all()

    def test_frequency_right_skewed_and_overdispersed(self, tx):
        # trips per household across ALL households (incl. never-buyers) — the
        # negative-binomial signature of real panel data.
        tph = tx.groupby("household_id").size().reindex(
            hp.get_households()["household_id"], fill_value=0
        )
        assert tph.var() / tph.mean() > 3.0, "trip counts not overdispersed enough"
        m, sd = tph.mean(), tph.std()
        skew = (((tph - m) / sd) ** 3).mean()
        assert skew > 1.0, f"trip-count skew {skew:.2f} not right-skewed enough"

    def test_launch_items_zero_before_launch_nonzero_after(self, tx):
        for sku, cfg in hp.LAUNCH_ITEMS.items():
            lq = cfg["launch_quarter_index"]
            rows = tx[tx["sku_id"] == sku]
            assert (rows["quarter_index"] >= lq).all(), f"{sku} sold before launch"
            assert (rows["quarter_index"] == lq).any(), f"{sku} has no trial-quarter sales"
            assert (rows["quarter_index"] > lq).any(), f"{sku} has no post-launch sales"


class TestPeriodMetrics:
    def test_one_row_per_quarter_in_order(self):
        m = hp.get_period_metrics()
        assert len(m) == 12
        assert m["quarter_index"].tolist() == list(range(12))

    def test_penetration_in_unit_interval(self):
        m = hp.get_period_metrics()
        assert m["penetration"].between(0.0, 1.0).all()

    def test_product_identity_holds(self):
        # buying_households x frequency x spend_per_trip == sales, every quarter.
        m = hp.get_period_metrics()
        lhs = m["buying_households"] * m["frequency"] * m["spend_per_trip"]
        assert ((lhs - m["sales"]).abs() <= 1e-6).all()

    def test_spend_per_trip_splits_into_units_x_price(self):
        m = hp.get_period_metrics()
        lhs = m["units_per_trip"] * m["price_per_unit"]
        assert ((lhs - m["spend_per_trip"]).abs() <= 1e-6).all()

    def test_reproducible(self):
        pd.testing.assert_frame_equal(hp.get_period_metrics(), hp.get_period_metrics())

    def test_filters_reduce_sales(self):
        total = hp.get_period_metrics()["sales"].sum()
        one_line = hp.get_period_metrics(product_line="AS")["sales"].sum()
        one_ret = hp.get_period_metrics(retailer_id="RET-WALMART")["sales"].sum()
        assert 0 < one_line < total
        assert 0 < one_ret < total


class TestBuyerFlow:
    def test_eleven_adjacent_pairs(self):
        f = hp.get_buyer_flow()
        assert len(f) == 11

    def test_flow_identities_hold(self):
        # Counts are projected to brand scale (floats), so compare to tolerance
        # rather than exact equality; the identities hold because every column is
        # scaled by the same k.
        f = hp.get_buyer_flow()
        assert ((f["prior_buyers"] - (f["retained"] + f["lapsed"])).abs() <= 1e-6).all()
        assert ((f["current_buyers"] - (f["retained"] + f["new"])).abs() <= 1e-6).all()

    def test_counts_nonnegative(self):
        f = hp.get_buyer_flow()
        for col in ("retained", "new", "lapsed", "prior_buyers", "current_buyers"):
            assert (f[col] >= 0).all()
