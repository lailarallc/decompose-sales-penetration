"""Shared filter bar component and callbacks.

Cloned from Spin Rate's filters, simplified: Decompose's options come from the
in-process panel (``panel_data``) at build time, so there is no populate-from-DB
callback. Controls are the four the clarified scope allows — Period A, Period B,
Product line, Retailer (channel is deliberately NOT a top-level control).
"""

import json

from dash import Input, Output, callback, dcc, html

from app import panel_data

DEFAULT_PERIOD_A, DEFAULT_PERIOD_B = panel_data.default_periods()

DEFAULT_FILTER_STATE = {
    "period_a": DEFAULT_PERIOD_A,
    "period_b": DEFAULT_PERIOD_B,
    "product_line": "__all__",
    "retailer": "__all__",
}


def _quarter_options():
    return [{"label": q, "value": q} for q in panel_data.analysis_quarters()]


def build_filter_bar():
    """Return the filter bar: Period A, Period B, Product line, Retailer."""
    return html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Period A",
                        title="The earlier period — the 'from' side of the comparison.",
                    ),
                    dcc.Dropdown(
                        id="filter-period-a",
                        options=_quarter_options(),
                        value=DEFAULT_PERIOD_A,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "140px", "flex": "1"},
            ),
            html.Div(
                [
                    html.Label(
                        "Period B",
                        title="The later period — the 'to' side of the comparison.",
                    ),
                    dcc.Dropdown(
                        id="filter-period-b",
                        options=_quarter_options(),
                        value=DEFAULT_PERIOD_B,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "140px", "flex": "1"},
            ),
            html.Div(
                [
                    html.Label(
                        "Product line",
                        title="Narrow to one product line, or keep All lines for the whole brand.",
                    ),
                    dcc.Dropdown(
                        id="filter-product-line",
                        options=panel_data.product_line_options(),
                        value="__all__",
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "180px", "flex": "1"},
            ),
            html.Div(
                [
                    html.Label(
                        "Retailer",
                        title="Narrow to one retailer, or keep All retailers for every channel.",
                    ),
                    dcc.Dropdown(
                        id="filter-retailer",
                        options=panel_data.retailer_options(),
                        value="__all__",
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
                style={"minWidth": "180px", "flex": "1"},
            ),
        ],
        className="filter-bar",
    )


def register_filter_callbacks():
    """Register filter callbacks — sync the four controls into the shared store."""

    @callback(
        Output("filter-state", "data"),
        Input("filter-period-a", "value"),
        Input("filter-period-b", "value"),
        Input("filter-product-line", "value"),
        Input("filter-retailer", "value"),
    )
    def _sync_filter_state(period_a, period_b, product_line, retailer):
        return json.dumps(
            {
                "period_a": period_a or DEFAULT_PERIOD_A,
                "period_b": period_b or DEFAULT_PERIOD_B,
                "product_line": product_line or "__all__",
                "retailer": retailer or "__all__",
            }
        )
