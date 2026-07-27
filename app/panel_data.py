"""In-process panel data layer — the app's single data seam.

Decompose has **no database**. Its data is the deterministic, seed-locked
``cinderhaven-household-panel`` package: the app imports it, warms the panel once at
startup, and serves every metric from the package's in-process cache. The layout,
filters, and views import from *here*, not from the package directly, so the
"no DB, in-process" contract and the filter vocabulary live in one place.

Why no disk cache: panel generation is ~0.6s and ``functools.lru_cache`` already
builds it once per process; with Fly ``min_machines_running = 1`` the machine stays
up, so that cost is paid once at boot (``warm_cache`` below) and never on a request.
A parquet cache would only skip ~0.6s at a rare process boot, and could not be wired
without coupling to the package's internal transaction cache (which app/CLAUDE.md
forbids re-implementing). Measured, not assumed — see DECISIONS.md.
"""

import json
import logging
import time
from typing import TypedDict

import cinderhaven_household_panel as panel
import pandas as pd

from app.decomposition import (
    Verdict,
    Waterfall,
    three_lever_waterfall,
    which_lever_verdict,
)


class DecomposeResult(TypedDict):
    """The bundle a view renders: the reconciling waterfall + its plain-language verdict."""

    waterfall: Waterfall
    verdict: Verdict

logger = logging.getLogger(__name__)

# ── Re-exported panel facts (so views never reach into the package) ──
PANEL_VERSION = panel.PANEL_VERSION
AS_OF_DATE = panel.DEMO_AS_OF_DATE
N_HOUSEHOLDS = panel.N_HOUSEHOLDS
ANALYSIS_QUARTERS = list(panel.ANALYSIS_QUARTER_LABELS)

# Exec default period pair: the most recent year-over-year window, which is the
# validated "growth that's actually erosion" story (2024-Q4 -> 2025-Q4). The exact
# default pairing is a copy/product decision revisited in Slice 4's verdict review.
DEFAULT_PERIOD_A = ANALYSIS_QUARTERS[3]   # 2024-Q4
DEFAULT_PERIOD_B = ANALYSIS_QUARTERS[-1]  # 2025-Q4

_warmed = False


def warm_cache() -> None:
    """Build the panel once, at startup, so no visitor's request pays generation.

    Idempotent. Downstream ``get_period_metrics`` / ``get_buyer_flow`` /
    ``three_lever_waterfall`` all read through the same cached transactions frame.
    """
    global _warmed
    if _warmed:
        return
    start = time.perf_counter()
    panel.get_transactions()
    _warmed = True
    logger.info(
        "panel warmed in %.2fs (v%s, %d households, %d analysis quarters)",
        time.perf_counter() - start,
        PANEL_VERSION,
        N_HOUSEHOLDS,
        len(ANALYSIS_QUARTERS),
    )


def analysis_quarters() -> list[str]:
    """Analysis-window quarter labels, calendar order (period A/B dropdown source)."""
    return list(ANALYSIS_QUARTERS)


def default_periods() -> tuple[str, str]:
    """The (period_a, period_b) pair the app opens on."""
    return DEFAULT_PERIOD_A, DEFAULT_PERIOD_B


def parse_filter_state(filter_json: str | None) -> tuple[str, str, str, str]:
    """Decode the shared filter-state store into (period_a, period_b, line, retailer).

    The single reader of the filter-state JSON contract — every view calls this
    instead of re-decoding the store, so the four-key shape lives in one place
    alongside DEFAULT_FILTER_STATE. Periods fall back to the exec defaults; the
    line/retailer sentinels ('__all__') are passed through and normalized downstream.

    Hardened against untrusted input: the dcc.Store value is client-supplied (a POST
    to the Dash callback endpoint can carry any string), so malformed JSON, a non-object
    body, or an unknown code all fall back to a valid default rather than raising a 500
    or reaching the panel accessors with a bad key.
    """
    try:
        filters = json.loads(filter_json) if filter_json else {}
    except (TypeError, ValueError):
        filters = {}
    if not isinstance(filters, dict):
        filters = {}

    periods = set(ANALYSIS_QUARTERS)
    lines = {opt["value"] for opt in product_line_options()}
    retailers = {opt["value"] for opt in retailer_options()}

    def _valid(value, allowed, fallback):
        return value if value in allowed else fallback

    return (
        _valid(filters.get("period_a"), periods, DEFAULT_PERIOD_A),
        _valid(filters.get("period_b"), periods, DEFAULT_PERIOD_B),
        _valid(filters.get("product_line"), lines, "__all__"),
        _valid(filters.get("retailer"), retailers, "__all__"),
    )


def product_line_options() -> list[dict[str, str]]:
    """Dropdown options for the product-line filter, with an 'All lines' default."""
    options = [{"label": "All lines", "value": "__all__"}]
    for code, meta in panel.PRODUCT_LINES.items():
        options.append({"label": meta["name"], "value": code})
    return options


def retailer_options() -> list[dict[str, str]]:
    """Dropdown options for the retailer filter, with an 'All retailers' default."""
    options = [{"label": "All retailers", "value": "__all__"}]
    for retailer_id, meta in panel.RETAILERS.items():
        options.append({"label": meta["name"], "value": retailer_id})
    return options


def _normalize(value: str | None) -> str | None:
    """Map the sentinel '__all__' (and empty) to None for the panel accessors."""
    return None if value in (None, "__all__", "") else value


def get_metrics(product_line: str | None = None, retailer_id: str | None = None) -> pd.DataFrame:
    """Per-quarter metrics for a filter combination (thin pass-through)."""
    return panel.get_period_metrics(_normalize(product_line), _normalize(retailer_id))


def get_flow(product_line: str | None = None, retailer_id: str | None = None) -> pd.DataFrame:
    """New/retained/lapsed buyer flow for a filter combination (thin pass-through)."""
    return panel.get_buyer_flow(_normalize(product_line), _normalize(retailer_id))


def decompose(
    period_a: str, period_b: str,
    product_line: str | None = None, retailer_id: str | None = None,
) -> DecomposeResult:
    """Bundle the three-lever waterfall and plain-language verdict for a period pair.

    This is what the views render: the Shapley waterfall (reconciles to ΔSales) plus
    the direction-aware "which lever" verdict, both computed from the panel.
    """
    line = _normalize(product_line)
    retailer = _normalize(retailer_id)
    waterfall = three_lever_waterfall(period_a, period_b, line, retailer)
    verdict = which_lever_verdict(waterfall)
    return {"waterfall": waterfall, "verdict": verdict}
