"""Demo golden lock — Decompose (three-lever Shapley engine).

Decompose's whole promise is that the three levers reconcile **exactly** to the
sales delta. This locks that guarantee and pins a representative decomposition so
the attribution math cannot silently drift.
"""
from __future__ import annotations

from app.decomposition import Waterfall, _shapley_three_factor, which_lever_verdict


# Period A: 100 buying hh × 2.0 trips × $10.00/trip = $2,000.
# Period B: 120 buying hh × 2.2 trips × $10.50/trip = $2,772.  Delta = $772.
A = (100.0, 2.0, 10.0)
B = (120.0, 2.2, 10.5)


def test_shapley_reconciles_exactly_to_the_delta():
    phi_h, phi_f, phi_s = _shapley_three_factor(*A, *B)
    delta = B[0] * B[1] * B[2] - A[0] * A[1] * A[2]
    assert abs((phi_h + phi_f + phi_s) - delta) <= 1e-9   # Shapley efficiency
    assert round(delta, 2) == 772.00


def test_pinned_lever_contributions():
    phi_h, phi_f, phi_s = _shapley_three_factor(*A, *B)
    assert round(phi_h, 2) == 430.67
    assert round(phi_f, 2) == 225.67
    assert round(phi_s, 2) == 115.67


def test_verdict_names_the_dominant_lever():
    phi_h, phi_f, phi_s = _shapley_three_factor(*A, *B)
    wf = Waterfall("2025-Q1", "2025-Q2", A[0]*A[1]*A[2], B[0]*B[1]*B[2],
                   B[0]*B[1]*B[2] - A[0]*A[1]*A[2],
                   {"buying_households": phi_h, "frequency": phi_f, "spend_per_trip": phi_s})
    assert wf.reconciles
    v = which_lever_verdict(wf)
    assert v["headline_lever"] == "buying_households"
    assert v["dominant"] is True
    assert "more households buying the brand" in v["sentence"]
