"""Penetration & Buyers view — household penetration trend + new/retained/lapsed flow.

Two charts, both recomputed from the panel for the current filters:
  1. Household penetration % across the eight analysis quarters (Periods A and B
     marked), so a decline hiding under rising sales is visible.
  2. Buyer flow — retained + new stacked above zero, lapsed below, per adjacent
     quarter pair, so churn and acquisition read at a glance.
"""

import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from app import panel_data
from app.charts import CHART_CONFIG, economist_layout
from app.components import view_heading, why_this_matters
from app.constants import (
    CHICAGO_20,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    HK_35,
    INK,
    REFERENCE,
    TEXT_SECONDARY,
    TOKYO_40,
)

_WHY = (
    "Household penetration is the share of all panel households that bought you in a "
    "quarter — the meaning your dashboard usually hides. Sales can rise while "
    "penetration falls if the households who stay are simply spending more. The buyer "
    "flow shows whether you are replacing the households you lose."
)


def layout():
    return html.Div(
        [
            view_heading(
                "Penetration & buyers",
                "Household penetration is the share of all panel households that "
                "bought you in a quarter — the meaning your dashboard isn't showing.",
            ),
            dcc.Graph(id="penetration-trend", config=CHART_CONFIG, style={"minHeight": "360px"}),
            html.P(
                "Dashed lines mark the two periods you're comparing.",
                className="chart-caption",
            ),
            dcc.Graph(id="buyer-flow", config=CHART_CONFIG, style={"minHeight": "380px"}),
            html.P(
                "Above zero: households retained from the prior quarter plus new ones. "
                "Below zero: households that lapsed.",
                className="chart-caption",
            ),
            why_this_matters(_WHY),
        ],
        className="view penetration-view",
    )


def _build_penetration_trend(metrics, period_a, period_b):
    analysis = metrics[metrics["is_analysis"]].copy()
    x = analysis["quarter_label"].tolist()
    y = analysis["penetration"].tolist()

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers+text",
            line=dict(color=CHICAGO_20, width=3),
            marker=dict(size=8, color=CHICAGO_20),
            text=[f"{v:.0%}" for v in y],
            textposition="top center",
            textfont=dict(family=FONT_SANS, size=11, color=INK),
            cliponaxis=False,
            hovertemplate="%{x}<br>Penetration %{y:.1%}<extra></extra>",
            name="Penetration",
        )
    )

    y_max = max(y) if y else 0.1
    # xaxis inherits economist_layout's default.
    layout = economist_layout(
        title=dict(
            text="Household penetration by quarter",
            font=dict(family=FONT_SERIF, size=22, color=INK),
        ),
        yaxis=dict(
            title=dict(
                text="Penetration %",
                font=dict(family=FONT_SANS, size=14, color=TEXT_SECONDARY),
            ),
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            showline=False,
            automargin=True,
            tickformat=".0%",
            rangemode="tozero",
            range=[0, y_max * 1.2 if y_max else 1],
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        ),
        showlegend=False,
        margin=dict(l=64, r=24, t=64, b=44),
    )
    fig.update_layout(**layout)

    # Mark the two compared periods.
    for label, tag in ((period_a, "A"), (period_b, "B")):
        if label in x:
            fig.add_vline(x=label, line=dict(color=REFERENCE, width=1.5, dash="dash"))
            fig.add_annotation(
                x=label, yref="paper", y=1.02, text=tag, showarrow=False,
                font=dict(family=FONT_SANS, size=13, color=REFERENCE),
            )
    return fig


def _build_buyer_flow(flow):
    x = flow["to_label"].tolist()
    retained = flow["retained"].tolist()
    new = flow["new"].tolist()
    lapsed = [-v for v in flow["lapsed"].tolist()]  # below zero = churn

    # Bold count labels inside each segment (ints for counts, per the chart rules);
    # uniformtext hides any that can't fit rather than letting them overflow.
    label_font = dict(family=FONT_SANS, size=11, color="#ffffff")
    fig = go.Figure()
    # Counts are projected to brand scale (floats), so labels use SI (".3s" -> "248k")
    # inside the bars and integer formatting on hover.
    fig.add_bar(
        x=x, y=retained, name="Retained", marker_color=HK_35,
        text=retained, texttemplate="%{text:.3s}", textposition="inside",
        insidetextfont=label_font,
        hovertemplate="%{x}<br>Retained %{y:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=x, y=new, name="New", marker_color=CHICAGO_20,
        text=new, texttemplate="%{text:.3s}", textposition="inside",
        insidetextfont=label_font,
        hovertemplate="%{x}<br>New %{y:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=x, y=lapsed, name="Lapsed", marker_color=TOKYO_40,
        customdata=flow["lapsed"].tolist(),
        text=flow["lapsed"].tolist(), texttemplate="%{text:.3s}", textposition="inside",
        insidetextfont=label_font,
        hovertemplate="%{x}<br>Lapsed %{customdata:,.0f}<extra></extra>",
    )

    # xaxis inherits economist_layout's default.
    layout = economist_layout(
        title=dict(
            text="Where buyers came from and went",
            font=dict(family=FONT_SERIF, size=22, color=INK),
        ),
        barmode="relative",
        uniformtext=dict(minsize=9, mode="hide"),
        yaxis=dict(
            title=dict(
                text="Households",
                font=dict(family=FONT_SANS, size=14, color=TEXT_SECONDARY),
            ),
            showgrid=True, gridcolor=GRIDLINE, gridwidth=1, showline=False,
            automargin=True, zeroline=True, zerolinecolor=REFERENCE, zerolinewidth=1,
            tickformat=",.0f",
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        ),
        margin=dict(l=68, r=24, t=64, b=64),
    )
    fig.update_layout(**layout)
    return fig


def register_callbacks():
    @callback(
        Output("penetration-trend", "figure"),
        Output("buyer-flow", "figure"),
        Input("filter-state", "data"),
    )
    def _update(filter_json):
        period_a, period_b, line, retailer = panel_data.parse_filter_state(filter_json)
        metrics = panel_data.get_metrics(line, retailer)
        flow = panel_data.get_flow(line, retailer)
        # Buyer flow only within the analysis window (transitions into an analysis Q).
        analysis_labels = set(panel_data.analysis_quarters())
        flow = flow[flow["to_label"].isin(analysis_labels)]
        return (
            _build_penetration_trend(metrics, period_a, period_b),
            _build_buyer_flow(flow),
        )
