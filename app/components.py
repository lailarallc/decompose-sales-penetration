"""Shared UI building blocks for the Decompose views — headings, the 'why this
matters' panel, and the glossary of terms."""

from dash import html

# The exec-facing glossary. Each entry is (term, definition); the phrasing is
# deliberately plain so a CFO reads it without a stats background.
GLOSSARY = [
    ("Household penetration",
     "The share of all panel households that bought the brand in a quarter — "
     "raw panel buyers ÷ 5,000 panelists, not a national projection. Meaning "
     "#3 — the one a distribution or velocity dashboard doesn't show you."),
    ("Buying households",
     "How many distinct households bought at all in the period — the first lever. "
     "The displayed count is projected to brand scale (see 'Projected to brand "
     "scale' below); the raw panel count is much smaller."),
    ("Purchase frequency",
     "Trips per buying household in the period — how often your buyers came back."),
    ("Spend per trip",
     "Dollars per trip — basket size, split into units per trip × price per unit."),
    ("New / retained / lapsed",
     "Of this quarter's buyers, who is new vs. kept from last quarter (retained); "
     "lapsed households bought last quarter but not this one."),
    ("Three-lever bridge",
     "Sales = buying households × purchase frequency × spend per trip. The waterfall "
     "splits the change between two periods across exactly those three levers "
     "(an exact Shapley attribution), so the pieces sum to the total change."),
    ("Projected to brand scale",
     "The panel is a ~5,000-household synthetic sample. Dollar totals and buyer counts "
     "are scaled by one fixed factor to Cinderhaven's brand scale (~$32.3M retail scan "
     "in CY2025; ~$99.1M scanned 2023–2025). Penetration, frequency, and spend per "
     "trip are panel-measured rates and are not scaled. The warehouse carries neither "
     "households nor the projection factor — panel figures are panel-only."),
]


def view_heading(title: str, blurb: str):
    """A view's serif heading plus a one-line 'why this matters' blurb."""
    return html.Div(
        [
            html.H2(title, className="view-title"),
            html.P(blurb, className="view-blurb"),
        ],
        className="view-heading",
    )


def why_this_matters(text: str):
    """A muted, collapsible 'why this matters' panel for exec context."""
    return html.Details(
        [
            html.Summary("Why this matters", className="why-toggle"),
            html.P(text, className="why-body"),
        ],
        className="why-details",
    )


def definitions_panel():
    """A collapsible glossary of the terms used across the tool."""
    items = [
        html.Div(
            [
                html.Dt(term, className="glossary-term"),
                html.Dd(definition, className="glossary-def"),
            ],
            className="glossary-row",
        )
        for term, definition in GLOSSARY
    ]
    return html.Details(
        [
            html.Summary("Glossary", className="why-toggle"),
            html.Dl(items, className="glossary-list"),
        ],
        className="why-details glossary-details",
    )
