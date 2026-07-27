"""Cinderhaven Household Panel — shared, seed-locked synthetic panel.

Built by tool #3 (Decompose); imported unchanged by tool #4 (Leaky Bucket).
Grain: household x transaction x item x date x spend, aligned to the canonical
Cinderhaven universe. Generation is deterministic given ``SEED``.

Public API grows through Slice 1:
  A1 (this step): SEED, PANEL_VERSION, sizing constants, the 12-quarter calendar,
                  and the reused canonical universe.
  Later steps add: get_households, get_transactions, get_period_metrics,
                   get_buyer_flow.
"""

from .calendar import (
    ANALYSIS_QUARTER_LABELS,
    BURN_IN_QUARTER_LABELS,
    QUARTERS,
    build_quarters,
    get_quarters,
)
from .constants import (
    ALL_SKUS,
    ANALYSIS_QUARTERS,
    BURN_IN_QUARTERS,
    CANONICAL_ANNUAL_SCAN_REVENUE,
    DEMO_AS_OF_DATE,
    N_HOUSEHOLDS,
    PANEL_START_YEAR,
    PANEL_VERSION,
    PRODUCT_LINES,
    PROJECTION_REFERENCE_YEAR,
    REGIONS,
    RETAILERS,
    SEED,
    TOTAL_QUARTERS,
)
from .households import get_households
from .metrics import get_buyer_flow, get_period_metrics
from .pricing import (
    LAUNCH_ITEMS,
    get_launch_items,
    get_price_path,
    get_sku_prices,
)
from .projection import get_projection_factor
from .transactions import get_transactions

__all__ = [
    # canonical universe (reused from cinderhaven-store-universe)
    "ALL_SKUS",
    "PRODUCT_LINES",
    "RETAILERS",
    "REGIONS",
    "DEMO_AS_OF_DATE",
    # locked panel constants
    "SEED",
    "PANEL_VERSION",
    "N_HOUSEHOLDS",
    "BURN_IN_QUARTERS",
    "ANALYSIS_QUARTERS",
    "TOTAL_QUARTERS",
    "PANEL_START_YEAR",
    # brand-scale projection (shared with tool #4)
    "CANONICAL_ANNUAL_SCAN_REVENUE",
    "PROJECTION_REFERENCE_YEAR",
    "get_projection_factor",
    # calendar
    "QUARTERS",
    "ANALYSIS_QUARTER_LABELS",
    "BURN_IN_QUARTER_LABELS",
    "build_quarters",
    "get_quarters",
    # household dimension
    "get_households",
    # pricing + launch items
    "get_sku_prices",
    "get_price_path",
    "get_launch_items",
    "LAUNCH_ITEMS",
    # transactions (the panel)
    "get_transactions",
    # period metrics + buyer flow
    "get_period_metrics",
    "get_buyer_flow",
]
