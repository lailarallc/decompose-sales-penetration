"""Data-layer tests (Slice 3B).

panel_data is the app's single seam onto the in-process panel. These tests pin the
filter vocabulary (the '__all__' sentinel → None mapping the callbacks rely on), the
exec defaults, and that the thin pass-throughs and the decompose() bundle stay honest
(the waterfall still reconciles to ΔSales through this layer).
"""

import cinderhaven_household_panel as hp
import pandas as pd

from app import panel_data as pd_layer


class TestWarmCache:
    def test_warm_cache_is_idempotent(self):
        pd_layer.warm_cache()
        pd_layer.warm_cache()  # second call must be a no-op, not a re-generation
        assert pd_layer._warmed is True


class TestPeriods:
    def test_analysis_quarters_are_the_eight_analysis_labels(self):
        assert pd_layer.analysis_quarters() == list(hp.ANALYSIS_QUARTER_LABELS)
        assert len(pd_layer.analysis_quarters()) == 8

    def test_default_periods_is_the_yoy_erosion_pair(self):
        a, b = pd_layer.default_periods()
        assert (a, b) == ("2024-Q4", "2025-Q4")
        assert a in pd_layer.analysis_quarters()
        assert b in pd_layer.analysis_quarters()


class TestParseFilterState:
    """The single decoder of the filter-state store (shared by all three views)."""

    def test_empty_or_none_falls_back_to_exec_defaults(self):
        for empty in (None, "", "{}"):
            assert pd_layer.parse_filter_state(empty) == (
                "2024-Q4", "2025-Q4", "__all__", "__all__",
            )

    def test_full_state_is_passed_through_verbatim(self):
        import json

        state = json.dumps(
            {
                "period_a": "2024-Q1",
                "period_b": "2025-Q2",
                "product_line": "AS",
                "retailer": "RET-WALMART",
            }
        )
        assert pd_layer.parse_filter_state(state) == ("2024-Q1", "2025-Q2", "AS", "RET-WALMART")


class TestFilterOptions:
    def test_product_line_options_lead_with_all_then_every_line(self):
        opts = pd_layer.product_line_options()
        assert opts[0] == {"label": "All lines", "value": "__all__"}
        values = [o["value"] for o in opts[1:]]
        assert values == list(hp.PRODUCT_LINES.keys())

    def test_retailer_options_lead_with_all_then_every_retailer(self):
        opts = pd_layer.retailer_options()
        assert opts[0] == {"label": "All retailers", "value": "__all__"}
        values = [o["value"] for o in opts[1:]]
        assert values == list(hp.RETAILERS.keys())

    def test_normalize_maps_all_sentinel_and_empty_to_none(self):
        assert pd_layer._normalize("__all__") is None
        assert pd_layer._normalize("") is None
        assert pd_layer._normalize(None) is None
        assert pd_layer._normalize("AS") == "AS"


class TestPassThrough:
    def test_get_metrics_all_matches_unfiltered_package(self):
        got = pd_layer.get_metrics("__all__", "__all__")
        expected = hp.get_period_metrics(None, None)
        pd.testing.assert_frame_equal(got, expected)

    def test_get_metrics_applies_a_line_filter(self):
        got = pd_layer.get_metrics("AS", "__all__")
        expected = hp.get_period_metrics("AS", None)
        pd.testing.assert_frame_equal(got, expected)

    def test_get_flow_applies_a_retailer_filter(self):
        got = pd_layer.get_flow("__all__", "RET-WALMART")
        expected = hp.get_buyer_flow(None, "RET-WALMART")
        pd.testing.assert_frame_equal(got, expected)


class TestDecomposeBundle:
    def test_decompose_returns_a_reconciling_waterfall_and_a_verdict(self):
        out = pd_layer.decompose("2024-Q4", "2025-Q4")
        wf = out["waterfall"]
        assert wf.reconciles
        assert out["verdict"]["sentence"].startswith("Sales ")
        assert set(wf.contributions) == {"buying_households", "frequency", "spend_per_trip"}

    def test_decompose_honors_the_all_sentinel_as_whole_brand(self):
        via_sentinel = pd_layer.decompose("2024-Q4", "2025-Q4", "__all__", "__all__")
        via_none = pd_layer.decompose("2024-Q4", "2025-Q4", None, None)
        assert via_sentinel["waterfall"].delta == via_none["waterfall"].delta
