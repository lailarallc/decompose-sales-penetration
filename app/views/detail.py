"""Detail view — per-period metric cards + a per-quarter detail table.

The cards put the three levers for Period A and Period B side by side with the change
on each; the table is every metric per quarter — the numbers behind the waterfall.
Both recompute from the panel for the current filters.
"""

import dash_ag_grid as dag
from dash import Input, Output, callback, html

from app import panel_data
from app.components import view_heading
from app.constants import fmt_dollars, fmt_number, fmt_pct


def _fmt_cents(value):
    """Dollars with cents — for per-trip / per-unit amounts where cents matter."""
    return "N/A" if value is None else f"${value:,.2f}"


def _sign(delta: float) -> str:
    if delta == 0:
        return ""
    return "+" if delta > 0 else "−"


# Delta formatters — each takes the signed A→B change and formats it with a sign in
# the metric's own unit. Carried per-metric in _CARD_METRICS so the delta unit is
# data-driven, not inferred from the (rewordable) display label.
def _dollar_delta(d):
    return f"{_sign(d)}{fmt_dollars(abs(d))}"


def _cents_delta(d):
    return f"{_sign(d)}{_fmt_cents(abs(d))}"


def _pp_delta(d):
    return f"{_sign(d)}{abs(d) * 100:.1f} pp"


def _trips_delta(d):
    return f"{_sign(d)}{abs(d):.2f} trips"


# Table columns: (field, header, formatter). Quarter is the key column — never
# truncated, always left and wide.
_COLUMNS = [
    ("quarter_label", "Quarter", None),
    ("penetration", "Penetration", lambda v: fmt_pct(v)),
    ("buying_households", "Buying HH", lambda v: fmt_number(v)),
    ("frequency", "Frequency", lambda v: f"{v:.2f}"),
    ("spend_per_trip", "Spend / trip", _fmt_cents),
    ("units_per_trip", "Units / trip", lambda v: f"{v:.2f}"),
    ("price_per_unit", "Price / unit", _fmt_cents),
    ("sales", "Sales", lambda v: fmt_dollars(v)),
]

# The three levers as cards, plus the sales headline.
# (field, label, value formatter, delta formatter)
_CARD_METRICS = [
    ("sales", "Sales", fmt_dollars, _dollar_delta),
    ("penetration", "Household penetration", fmt_pct, _pp_delta),
    ("frequency", "Purchase frequency", lambda v: f"{v:.2f} trips", _trips_delta),
    ("spend_per_trip", "Spend per trip", _fmt_cents, _cents_delta),
]


def layout():
    return html.Div(
        [
            view_heading(
                "Period detail",
                "The three levers side by side for the two periods, with the "
                "spend-per-trip split into units per trip × price per unit.",
            ),
            html.Div(id="metric-cards", className="metric-cards"),
            html.H3("Every quarter", className="detail-subhead"),
            html.Div(id="detail-table"),
        ],
        className="view detail-view",
    )


def _metric_card(label, value_fmt, delta_fmt, a_val, b_val):
    delta = b_val - a_val
    change = delta_fmt(delta)
    if delta == 0:
        delta_class = "delta-flat"
    elif delta > 0:
        delta_class = "delta-up"
    else:
        delta_class = "delta-down"
    return html.Div(
        [
            html.Div(label, className="metric-card-label"),
            html.Div(value_fmt(b_val), className="metric-card-value"),
            html.Div(
                [
                    html.Span(f"from {value_fmt(a_val)}", className="metric-card-prev"),
                    html.Span(change, className=f"metric-card-delta {delta_class}"),
                ],
                className="metric-card-foot",
            ),
        ],
        className="metric-card",
    )


def _build_metric_cards(metrics, period_a, period_b):
    m = metrics.set_index("quarter_label")
    a, b = m.loc[period_a], m.loc[period_b]
    cards = [
        _metric_card(label, value_fmt, delta_fmt, a[field], b[field])
        for field, label, value_fmt, delta_fmt in _CARD_METRICS
    ]
    return [
        html.Div(f"{period_a} → {period_b}", className="metric-cards-caption"),
        html.Div(cards, className="metric-cards-grid"),
    ]


def _build_detail_table(metrics):
    row_data = []
    for _, row in metrics.iterrows():
        record = {}
        for field, _header, formatter in _COLUMNS:
            value = row[field]
            record[field] = formatter(value) if formatter else value
        record["_is_analysis"] = bool(row["is_analysis"])
        row_data.append(record)

    column_defs = [
        {
            "field": field,
            "headerName": header,
            "pinned": "left" if field == "quarter_label" else None,
            "minWidth": 130 if field == "quarter_label" else 110,
            "flex": 0 if field == "quarter_label" else 1,
        }
        for field, header, _fmt in _COLUMNS
    ]

    # responsiveSizeToFit re-fits the columns whenever the container resizes —
    # essential here because the tab panels pre-render while display:none (0 width),
    # so a one-shot sizeToFit would collapse the columns.
    return dag.AgGrid(
        rowData=row_data,
        columnDefs=column_defs,
        columnSize="responsiveSizeToFit",
        defaultColDef={"sortable": True, "resizable": True, "suppressMovable": True},
        dashGridOptions={"domLayout": "autoHeight", "suppressCellFocus": True},
        className="ag-theme-alpine decompose-grid",
        style={"width": "100%"},
    )


def register_callbacks():
    # The main-tabs value is an Input (not just filter-state) so the grid is rebuilt
    # when the Detail tab is activated. The tab panels pre-render while display:none
    # (0 width), so a grid mounted then would size its columns to nothing; remounting
    # it while the panel is visible lets responsiveSizeToFit fit the columns properly.
    @callback(
        Output("metric-cards", "children"),
        Output("detail-table", "children"),
        Input("filter-state", "data"),
        Input("main-tabs", "value"),
    )
    def _update(filter_json, _active_tab):
        period_a, period_b, line, retailer = panel_data.parse_filter_state(filter_json)
        metrics = panel_data.get_metrics(line, retailer)
        return (
            _build_metric_cards(metrics, period_a, period_b),
            _build_detail_table(metrics),
        )
