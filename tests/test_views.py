"""View figure-builder tests (Slice 5).

test_layout asserts the view *shells* expose the right output ids; these assert the
builders actually carry the invariants that matter — the waterfall's reconciliation
survives into the drawn bars, buyer-flow lapsed renders below zero, the penetration
trend plots the analysis window in order — plus the two behaviours added in the
Slice-5 review (zero-delta verdict, data-driven card deltas)."""

import cinderhaven_household_panel as hp

from app import panel_data
from app.constants import LEVER_ORDER
from app.decomposition import Waterfall, three_lever_waterfall, which_lever_verdict
from app.views.detail import _build_metric_cards
from app.views.penetration import _build_buyer_flow, _build_penetration_trend
from app.views.which_lever import _build_waterfall_figure, _verdict_children


def _text(component) -> str:
    if isinstance(component, str):
        return component
    if isinstance(component, (list, tuple)):
        return " ".join(_text(c) for c in component)
    children = getattr(component, "children", None)
    return _text(children) if children is not None else ""


def _classes(component) -> str:
    """Every className in a component tree, space-joined (for asserting state classes)."""
    out = getattr(component, "className", "") or ""
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        out += " " + " ".join(_classes(c) for c in children)
    elif children is not None:
        out += " " + _classes(children)
    return out


class TestWaterfallFigure:
    def test_relative_bars_reconcile_to_the_sales_delta(self):
        wf = three_lever_waterfall("2024-Q4", "2025-Q4")
        fig = _build_waterfall_figure(wf, "2024-Q4", "2025-Q4")
        tr = fig.data[0]
        assert list(tr.measure) == ["absolute", "relative", "relative", "relative", "total"]
        # The three relative bars Plotly actually draws are the lever contributions,
        # in LEVER_ORDER, and they sum to the sales change.
        relative = list(tr.y)[1:4]
        assert relative == [wf.contributions[lever] for lever in LEVER_ORDER]
        assert abs(sum(relative) - (wf.sales_b - wf.sales_a)) <= 1e-6


class TestBuyerFlowFigure:
    def test_lapsed_renders_below_zero_and_gains_above(self):
        flow = panel_data.get_flow(None, None)
        analysis = set(panel_data.analysis_quarters())
        flow = flow[flow["to_label"].isin(analysis)]
        fig = _build_buyer_flow(flow)
        series = {tr.name: list(tr.y) for tr in fig.data}
        assert all(v <= 0 for v in series["Lapsed"])          # churn is negated
        assert all(v >= 0 for v in series["Retained"])
        assert all(v >= 0 for v in series["New"])
        # The negated lapsed bar equals the true lapsed counts in magnitude.
        assert [-v for v in series["Lapsed"]] == flow["lapsed"].tolist()


class TestPenetrationTrend:
    def test_plots_analysis_window_in_calendar_order(self):
        metrics = panel_data.get_metrics(None, None)
        fig = _build_penetration_trend(metrics, "2024-Q4", "2025-Q4")
        tr = fig.data[0]
        analysis = metrics[metrics["is_analysis"]]
        assert list(tr.x) == analysis["quarter_label"].tolist()
        assert list(tr.y) == analysis["penetration"].tolist()


class TestZeroDeltaVerdict:
    def test_identical_periods_report_unchanged_not_a_false_rise(self):
        wf = three_lever_waterfall("2025-Q4", "2025-Q4")
        verdict = which_lever_verdict(wf)
        assert wf.delta == 0
        assert verdict["headline_lever"] == "none"
        assert "unchanged" in verdict["sentence"].lower()
        # Must NOT claim a lever rose/fell.
        assert "driven mainly by" not in verdict["sentence"]

    def test_zero_delta_headline_is_neutral(self):
        wf = Waterfall(
            period_a="2025-Q4", period_b="2025-Q4",
            sales_a=1000.0, sales_b=1000.0, delta=0.0,
            contributions={"buying_households": 0.0, "frequency": 0.0, "spend_per_trip": 0.0},
        )
        children = _verdict_children(wf, which_lever_verdict(wf), "2025-Q4", "2025-Q4")
        classes = " ".join(getattr(c, "className", "") for c in children)
        assert "delta-flat" in classes
        assert "delta-up" not in classes

    def test_negative_delta_headline_renders_down(self):
        wf = Waterfall(
            period_a="2024-Q4", period_b="2025-Q4",
            sales_a=1000.0, sales_b=900.0, delta=-100.0,
            contributions={"buying_households": -80.0, "frequency": -10.0, "spend_per_trip": -10.0},
        )
        children = _verdict_children(wf, which_lever_verdict(wf), "2024-Q4", "2025-Q4")
        classes = " ".join(getattr(c, "className", "") for c in children)
        assert "delta-down" in classes and "delta-up" not in classes
        assert "−" in _text(children)  # the change is shown with a minus sign


class TestMetricCardDeltas:
    def test_cards_show_the_computed_delta_in_each_metric_own_unit(self):
        # Assert the actual computed delta strings appear — that the right delta
        # formatter is applied to the right field's (b - a) difference — not merely
        # that "pp"/"$" show up somewhere (which a swapped formatter would still pass).
        from app.views.detail import _cents_delta, _dollar_delta, _pp_delta, _trips_delta

        metrics = hp.get_period_metrics(None, None)
        indexed = metrics.set_index("quarter_label")
        a, b = indexed.loc["2024-Q4"], indexed.loc["2025-Q4"]
        text = _text(_build_metric_cards(metrics, "2024-Q4", "2025-Q4"))

        assert _pp_delta(b["penetration"] - a["penetration"]) in text       # e.g. "−2.2 pp"
        assert _dollar_delta(b["sales"] - a["sales"]) in text               # e.g. "+$2K"
        assert _trips_delta(b["frequency"] - a["frequency"]) in text        # e.g. "−0.14 trips"
        assert _cents_delta(b["spend_per_trip"] - a["spend_per_trip"]) in text  # e.g. "+$1.88"

    def test_unchanged_metric_card_renders_neutral(self):
        from app.views.detail import _dollar_delta, _metric_card

        card = _metric_card("Sales", lambda v: f"${v:,.0f}", _dollar_delta, 100.0, 100.0)
        classes = _classes(card)
        assert "delta-flat" in classes
        assert "delta-up" not in classes and "delta-down" not in classes
