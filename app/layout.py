"""Layout assembly — brand frame, tab navigation, filter bar, and content area.

Cloned from Spin Rate's shell. Decompose's views are simpler (no protagonist
discovery / DB narrative), and all data is in-process via panel_data.
"""

import json
import logging

from dash import Input, Output, callback, dcc, html

from app import lailara_frame, panel_data
from app.app import app
from app.filters import (
    DEFAULT_FILTER_STATE,
    build_filter_bar,
    register_filter_callbacks,
)
from app.views import detail, penetration, which_lever

logger = logging.getLogger(__name__)

TAB_LABELS = ["Which Lever", "Penetration & Buyers", "Detail"]
TAB_IDS = ["which-lever", "penetration", "detail"]


def _build_tabs():
    """Build the dcc.Tabs component with the three view tabs."""
    return dcc.Tabs(
        id="main-tabs",
        value="which-lever",
        children=[
            dcc.Tab(
                label=label,
                value=value,
                className="custom-tab",
                selected_className="custom-tab--selected",
            )
            for label, value in zip(TAB_LABELS, TAB_IDS)
        ],
        className="custom-tabs",
    )


def _build_content_area():
    """Pre-render all three tab panels; a callback toggles display so each view's
    callbacks always find their targets in the DOM."""
    return html.Div(
        [
            html.Div(which_lever.layout(), id="tab-panel-which-lever", style={"display": "block"}),
            html.Div(penetration.layout(), id="tab-panel-penetration", style={"display": "none"}),
            html.Div(detail.layout(), id="tab-panel-detail", style={"display": "none"}),
        ]
    )


_PROJECTION_TIP = (
    "Household penetration, purchase frequency, and spend per trip are measured on "
    "the household panel. Dollar totals and buyer counts are projected to "
    "Cinderhaven's brand scale (~$32.3M retail scan in CY2025; ~$99.1M scanned "
    "2023–2025). The panel is a synthetic overlay — the warehouse carries "
    "neither households nor the projection factor."
)


def _build_as_of_note():
    """As-of date + brand-scale label + synthetic-data disclosure (exec-facing page)."""
    as_of = panel_data.AS_OF_DATE.strftime("%b %d, %Y")
    return html.Div(
        [
            html.Span(f"Panel as of {as_of}", className="as-of-chip"),
            html.Span(
                "Projected to brand scale",
                className="as-of-chip projected-chip",
                title=_PROJECTION_TIP,
            ),
            html.Span(
                "Synthetic Cinderhaven data — a demonstration of the method from a "
                "representative household panel, not a real brand.",
                className="synthetic-note",
            ),
        ],
        className="as-of-row",
    )


def register_layout():
    """Set app.layout and register all callbacks."""
    inner_layout = html.Div(
        [
            dcc.Store(
                id="filter-state",
                storage_type="session",
                data=json.dumps(DEFAULT_FILTER_STATE),
            ),
            html.Div(
                [
                    _build_as_of_note(),
                    _build_tabs(),
                    build_filter_bar(),
                    _build_content_area(),
                ],
                className="lailara-container",
            ),
        ]
    )

    app.layout = lailara_frame.wrap(
        inner_layout,
        tool_name="Decompose",
        footer_note="Household-penetration decomposition for CPG brands — "
        "buying households × purchase frequency × spend per trip.",
        no_container=True,
    )

    register_filter_callbacks()
    which_lever.register_callbacks()
    penetration.register_callbacks()
    detail.register_callbacks()

    @callback(
        Output("tab-panel-which-lever", "style"),
        Output("tab-panel-penetration", "style"),
        Output("tab-panel-detail", "style"),
        Input("main-tabs", "value"),
    )
    def _toggle_tab_visibility(tab_value):
        """Show the active tab panel, hide the rest."""
        show = {"display": "block"}
        hide = {"display": "none"}
        return (
            show if tab_value == "which-lever" else hide,
            show if tab_value == "penetration" else hide,
            show if tab_value == "detail" else hide,
        )
