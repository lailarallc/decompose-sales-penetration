"""Integration + reproducibility sweep (B).

Confirms the package is a clean, versioned, reproducible whole: every public
accessor returns identical frames across generations, the public surface tool #4
depends on is present, and an end-to-end pull works from a fresh import.
"""

import cinderhaven_household_panel as hp
import pandas as pd

_FRAME_ACCESSORS = [
    "get_quarters",
    "get_households",
    "get_sku_prices",
    "get_price_path",
    "get_launch_items",
    "get_transactions",
    "get_period_metrics",
    "get_buyer_flow",
]


class TestReproducibility:
    def test_every_accessor_is_reproducible(self):
        for name in _FRAME_ACCESSORS:
            fn = getattr(hp, name)
            pd.testing.assert_frame_equal(fn(), fn())


class TestPublicSurface:
    def test_version_is_set(self):
        assert hp.PANEL_VERSION == "0.2.0"

    def test_seed_and_sizing_exposed(self):
        assert hp.SEED == 42
        assert hp.N_HOUSEHOLDS == 5000
        assert hp.TOTAL_QUARTERS == 12

    def test_api_surface_present(self):
        # The exact names tool #4 (Leaky Bucket) reuses.
        for name in _FRAME_ACCESSORS + ["LAUNCH_ITEMS", "ALL_SKUS", "RETAILERS", "REGIONS"]:
            assert name in hp.__all__, f"{name} missing from public API"
            assert hasattr(hp, name)


class TestEndToEndPull:
    def test_all_frames_pull_with_expected_shape(self):
        assert len(hp.get_households()) == 5000
        assert len(hp.get_transactions()) > 0
        assert len(hp.get_period_metrics()) == 12
        assert len(hp.get_buyer_flow()) == 11
        assert len(hp.get_launch_items()) == 2

    def test_launch_metadata_matches_transactions(self):
        # Everything #4 needs to compute trial/repeat is derivable from the panel.
        li = hp.get_launch_items()
        tx = hp.get_transactions()
        for sku in li["sku_id"]:
            assert (tx["sku_id"] == sku).any(), f"launch item {sku} absent from panel"
