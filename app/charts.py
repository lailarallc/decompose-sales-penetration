"""Shared Economist-style chart defaults and SVG config for Plotly figures.

Cloned from Spin Rate so Decompose's charts are visually identical by construction:
Lailara tokens, serif titles, a single bottom horizontal legend, automargin so the
longest category label always renders, and currency ticks that show each tick's true
value with no duplicates.
"""

import math

from app.constants import (
    CANVAS,
    FONT_SANS,
    FONT_SERIF,
    GRIDLINE,
    INK,
    TEXT_SECONDARY,
)


def economist_layout(**overrides):
    """Return a Plotly layout dict with Lailara/Economist-style defaults."""
    defaults = dict(
        paper_bgcolor=CANVAS,
        plot_bgcolor=CANVAS,
        font=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        title=dict(font=dict(family=FONT_SERIF, size=22, color=INK)),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor=GRIDLINE,
            automargin=True,
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRIDLINE,
            gridwidth=1,
            showline=False,
            automargin=True,
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
        ),
        margin=dict(l=70, r=24, t=64, b=48),
        hoverlabel=dict(
            bgcolor=CANVAS,
            font=dict(family=FONT_SANS, size=13, color=INK),
            bordercolor=GRIDLINE,
        ),
        dragmode=False,
        showlegend=True,
        # Bottom, horizontal, small swatches — every figure inherits this unless it
        # explicitly overrides, so legend placement is consistent across charts.
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="left",
            x=0,
            font=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        ),
    )
    defaults.update(overrides)
    return defaults


def _nice_dollar_dtick(max_value: float) -> float:
    """Pick a round dollar tick step (1/2/2.5/5 × 10ⁿ) giving ~5–8 ticks.

    Guarantees evenly spaced ticks whose formatted labels never round to the same
    value (the duplicate-tick bug the chart rules call out).
    """
    if max_value <= 0:
        return 1.0

    raw = max_value / 6.0
    magnitude = 10 ** math.floor(math.log10(raw))
    step = 10 * magnitude
    for mult in (1, 2, 2.5, 5, 10):
        if mult * magnitude >= raw:
            step = mult * magnitude
            break
    # Never step below $1: the axis formats whole dollars, so a sub-dollar step
    # would render duplicate labels ($0, $0, $1, …). Real dollar axes here are in
    # the thousands, but this keeps the guarantee total.
    return max(1.0, step)


def dollar_yaxis(max_value: float, title: str = "Sales ($)", **overrides) -> dict:
    """A y-axis config for dollars: true, evenly-spaced, non-duplicate $ ticks,
    with the axis max extended past the largest value so top labels aren't clipped."""
    dtick = _nice_dollar_dtick(max_value)
    axis = dict(
        title=dict(text=title, font=dict(family=FONT_SANS, size=14, color=TEXT_SECONDARY)),
        showgrid=True,
        gridcolor=GRIDLINE,
        gridwidth=1,
        showline=False,
        automargin=True,
        # SI-abbreviated dollars ("$2M", "$325k") — reads cleanly at brand scale and
        # matches the bar value labels; the round dtick keeps SI labels non-duplicate.
        tickformat="$~s",
        dtick=dtick,
        range=[0, max_value * 1.15 if max_value > 0 else 1],
        tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SECONDARY),
    )
    axis.update(overrides)
    return axis


CHART_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "toImageButtonOptions": {"format": "svg"},
}
