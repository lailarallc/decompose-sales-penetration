"""Locked constants for the Cinderhaven household panel.

The canonical universe (SKUs, product lines, retailers, regions) is reused from
``cinderhaven-store-universe`` — the series SSOT — so this panel never drifts from
the rest of the Cinderhaven tools. Panel-specific figures below are locked and
versioned; changing them is a change-protocol event (see DECISIONS.md).
"""

try:
    from cinderhaven_store_universe.constants import (
        ALL_SKUS,
        DEMO_AS_OF_DATE,
        PRODUCT_LINES,
        REGIONS,
        RETAILERS,
    )
except ImportError as exc:  # pragma: no cover - environment setup guard
    raise ImportError(
        "cinderhaven-household-panel requires the peer package "
        "cinderhaven-store-universe (the canonical universe SSOT). Install it "
        "editable first, e.g. `pip install -e "
        "<doormath>/packages/cinderhaven-store-universe`."
    ) from exc

def line_of(sku: str) -> str:
    """Product-line code for a canonical SKU (``CHP-SB-010`` -> ``SB``).

    The one place the SKU-string contract is parsed; pricing and transactions
    both import this rather than re-splitting the id.
    """
    return sku.split("-")[1]


# --- Locked generation seed --------------------------------------------------
# Generation is deterministic given this value. Matches the house seed.
SEED = 42

# --- Panel data version ------------------------------------------------------
# Bump when the generated panel changes in a way that would shift downstream
# figures. 0.2.0: absolute totals from get_period_metrics / get_buyer_flow are now
# projected to brand scale (see projection.py); rates are unchanged.
PANEL_VERSION = "0.2.0"

# --- Panel size (locked, confirmed with Shawn 2026-07-06) --------------------
N_HOUSEHOLDS = 5_000

# --- Brand-scale projection (derived from the locked canonical figure) --------
# The panel is a ~5,000-household sample. ABSOLUTE totals (sales $, buyer/household
# counts, trip counts) are scaled by a single fixed sample-to-universe factor k so
# they read at Cinderhaven's brand scale; RATES (penetration %, purchase frequency,
# spend per trip) are panel-measured and NOT scaled — k cancels in a ratio.
# See projection.get_projection_factor for how k is derived and locked.
#
# Anchor: the panel's reference-year sales project to the canonical ANNUAL scan
# revenue. This DERIVES from the locked canonical figure — it does not alter it.
#   Canonical annual scan revenue = $32.8M (CINDERHAVEN_CANONICAL.md, trailing-52w).
# NOTE: the ~$99M often quoted for Cinderhaven is the 3-YEAR cumulative scan total
# (2023-01 -> 2026-01), NOT an annual figure — do not anchor annual sales to it.
CANONICAL_ANNUAL_SCAN_REVENUE = 32_800_000
PROJECTION_REFERENCE_YEAR = 2025  # latest full analysis year ~ trailing-52w

# --- Timeline: 4 burn-in quarters + 8 analysis quarters = 12 quarters --------
BURN_IN_QUARTERS = 4
ANALYSIS_QUARTERS = 8
TOTAL_QUARTERS = BURN_IN_QUARTERS + ANALYSIS_QUARTERS

# Calendar anchor. The 8-quarter analysis window aligns to the store-universe POS
# window (2024-2025, as-of 2025-12-29); the 4 burn-in quarters therefore cover
# 2023, giving tool #4's trial/repeat logic history runway before the window.
PANEL_START_YEAR = 2023

__all__ = [
    "ALL_SKUS",
    "line_of",
    "DEMO_AS_OF_DATE",
    "PRODUCT_LINES",
    "REGIONS",
    "RETAILERS",
    "SEED",
    "PANEL_VERSION",
    "N_HOUSEHOLDS",
    "BURN_IN_QUARTERS",
    "ANALYSIS_QUARTERS",
    "TOTAL_QUARTERS",
    "PANEL_START_YEAR",
    "CANONICAL_ANNUAL_SCAN_REVENUE",
    "PROJECTION_REFERENCE_YEAR",
]
