"""Decomposition math tests (Slice 2).

The reconciliation guarantee — the three lever contributions sum EXACTLY to the sales
delta — is the tool's whole credibility, so it is tested hard: exhaustively on the
Shapley kernel, and on real period pairs through the public function.
"""

import cinderhaven_household_panel as hp
import numpy as np
import pytest

from app.decomposition import (
    Waterfall,
    _shapley_three_factor,
    three_lever_waterfall,
    which_lever_verdict,
)


class TestShapleyKernel:
    def test_reconciles_on_many_random_triples(self):
        rng = np.random.default_rng(0)
        for _ in range(2000):
            a0, b0, c0, a1, b1, c1 = rng.uniform(0.1, 100, size=6)
            phi = _shapley_three_factor(a0, b0, c0, a1, b1, c1)
            delta = a1 * b1 * c1 - a0 * b0 * c0
            assert abs(sum(phi) - delta) <= 1e-6 * max(1.0, abs(delta))

    def test_single_factor_move_isolated(self):
        # Only C changes → all of ΔSales attributes to C, none to A or B.
        phi_a, phi_b, phi_c = _shapley_three_factor(5, 4, 3, 5, 4, 9)
        assert abs(phi_a) < 1e-9 and abs(phi_b) < 1e-9
        assert abs(phi_c - (5 * 4 * 9 - 5 * 4 * 3)) < 1e-9

    def test_zero_change_gives_zero(self):
        assert all(abs(x) < 1e-12 for x in _shapley_three_factor(5, 4, 3, 5, 4, 3))

    def test_all_negative_move_reconciles(self):
        phi = _shapley_three_factor(10, 10, 10, 6, 7, 8)
        assert abs(sum(phi) - (6 * 7 * 8 - 10 * 10 * 10)) < 1e-9

    def test_symmetry_two_factors_share_equally(self):
        # If A and B change by the same multiplicative factor and C is fixed, their
        # contributions are equal.
        phi_a, phi_b, phi_c = _shapley_three_factor(2, 2, 5, 4, 4, 5)
        assert abs(phi_a - phi_b) < 1e-9


class TestWaterfallOnRealData:
    def _sample_pairs(self):
        labels = hp.get_period_metrics()["quarter_label"].tolist()
        # consecutive + a few long spans
        pairs = list(zip(labels[:-1], labels[1:]))
        pairs += [("2024-Q1", "2025-Q4"), ("2024-Q4", "2025-Q4"), ("2023-Q1", "2025-Q4")]
        return pairs

    def test_every_sampled_pair_reconciles_exactly(self):
        for a, b in self._sample_pairs():
            wf = three_lever_waterfall(a, b)
            assert wf.reconciles
            assert abs(sum(wf.contributions.values()) - wf.delta) <= 1e-6
            assert abs(wf.delta - (wf.sales_b - wf.sales_a)) <= 1e-6

    def test_same_period_is_zero(self):
        wf = three_lever_waterfall("2024-Q2", "2024-Q2")
        assert abs(wf.delta) < 1e-9
        assert all(abs(v) < 1e-9 for v in wf.contributions.values())

    def test_filtered_pair_reconciles(self):
        wf = three_lever_waterfall("2024-Q4", "2025-Q4", product_line="AS")
        assert wf.reconciles
        wf2 = three_lever_waterfall("2024-Q4", "2025-Q4", retailer_id="RET-WALMART")
        assert wf2.reconciles

    def test_erosion_signature(self):
        # The seeded story: 2024-Q4 -> 2025-Q4 sales rise, but on price/basket while
        # buying households decline. Spend-per-trip contributes positively, buying
        # households negatively.
        wf = three_lever_waterfall("2024-Q4", "2025-Q4")
        assert wf.delta > 0
        assert wf.contributions["spend_per_trip"] > 0
        assert wf.contributions["buying_households"] < 0


class TestVerdict:
    def _wf(self, contribs, delta=None):
        delta = sum(contribs.values()) if delta is None else delta
        return Waterfall("A", "B", 100.0, 100.0 + delta, delta, contribs)

    def test_names_dominant_lever(self):
        v = which_lever_verdict(self._wf(
            {"buying_households": 5.0, "frequency": 2.0, "spend_per_trip": 90.0}
        ))
        assert v["dominant"] and v["headline_lever"] == "spend_per_trip"
        assert "spend per trip" in v["sentence"]

    def test_hedges_on_near_tie(self):
        v = which_lever_verdict(self._wf(
            {"buying_households": 40.0, "frequency": 35.0, "spend_per_trip": 25.0}
        ))
        assert not v["dominant"] and v["headline_lever"] == "mixed"
        assert "no single dominant lever" in v["sentence"]

    def test_hedges_when_levers_fight(self):
        # One up, one down, small net — top lever is < 50% of gross move → hedge.
        v = which_lever_verdict(self._wf(
            {"buying_households": -40.0, "frequency": 8.0, "spend_per_trip": 45.0}
        ))
        assert v["headline_lever"] == "mixed", v["shares"]

    def test_verdict_on_real_erosion_pair(self):
        v = which_lever_verdict(three_lever_waterfall("2024-Q4", "2025-Q4"))
        assert v["direction"] == "up"
        assert isinstance(v["sentence"], str) and v["sentence"]

    def test_names_dominant_lever_on_a_decline(self):
        # The tool's central case: sales FELL, driven by a dominant negative lever.
        # Guards the 'fell' wording and the negative-direction lever phrases.
        v = which_lever_verdict(self._wf(
            {"buying_households": -90.0, "frequency": -2.0, "spend_per_trip": -5.0}
        ))
        assert v["direction"] == "down" and v["dominant"]
        assert v["headline_lever"] == "buying_households"
        assert "Sales fell $97" in v["sentence"]
        assert "fewer households buying the brand" in v["sentence"]

    def test_hedges_on_a_mixed_decline(self):
        v = which_lever_verdict(self._wf(
            {"buying_households": -40.0, "frequency": -35.0, "spend_per_trip": -25.0}
        ))
        assert v["direction"] == "down" and v["headline_lever"] == "mixed"
        assert "fell" in v["sentence"] and "no single dominant lever" in v["sentence"]

    def test_flat_verdict_when_nothing_moved(self):
        v = which_lever_verdict(self._wf(
            {"buying_households": 0.0, "frequency": 0.0, "spend_per_trip": 0.0}, delta=0.0
        ))
        assert v["direction"] == "flat" and v["headline_lever"] == "none"
        assert not v["dominant"]
        assert "unchanged" in v["sentence"]


class TestUnknownPeriodGuard:
    def test_unknown_period_raises_keyerror(self):
        with pytest.raises(KeyError):
            three_lever_waterfall("not-a-quarter", "2025-Q4")
