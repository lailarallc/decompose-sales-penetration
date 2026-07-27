"""Per-SKU prices, the quarterly price path, and the two launch-item definitions (A3).

Only *mechanism* is set here — base prices, a deliberate 2025 price-up stretch, and
each launch item's trial reach + repeat propensity. Observed household penetration
and repeat rates are computed downstream from the transactions, never hardcoded.
"""

import pandas as pd

from ._rng import child_rng
from .calendar import QUARTERS
from .constants import ALL_SKUS, PRODUCT_LINES, line_of

# Base price range ($/unit) per product line for the ~$25M specialty brand.
_LINE_PRICE_RANGE = {
    "AS": (7.50, 11.50),  # Artisan Sauces
    "PS": (3.50, 6.50),   # Pantry Staples
    "SC": (5.50, 9.50),   # Specialty Condiments
    "DG": (4.50, 8.50),   # Dried Goods
    "SB": (2.75, 5.25),   # Snack Bites
}
assert set(_LINE_PRICE_RANGE) == set(PRODUCT_LINES), "price ranges must cover all product lines"

# Price-response strength. In A4 a household's effective trip rate scales by
# price_index ** (-PRICE_ELASTICITY * household price_sensitivity): higher prices +
# higher sensitivity → fewer trips, so price-sensitive households lapse as prices rise.
# Tuned (A6) so the price lift outweighs the volume loss — sales rise while
# penetration quietly declines, rather than volume collapsing and sales falling.
PRICE_ELASTICITY = 1.2

# 2025 price-up stretch (multiplicative brand price index). Flat through 2023-2024;
# this is the mechanism behind the "growth that's actually erosion" window.
_PRICE_RAMP_2025 = {1: 1.08, 2: 1.12, 3: 1.16, 4: 1.20}


def get_sku_prices() -> pd.DataFrame:
    """Deterministic base price per SKU (sku_id, product_line, base_price)."""
    rng = child_rng("prices")
    rows = []
    for sku in ALL_SKUS:
        line = line_of(sku)
        lo, hi = _LINE_PRICE_RANGE[line]
        base = round(float(rng.uniform(lo, hi)), 2)
        rows.append({"sku_id": sku, "product_line": line, "base_price": base})
    return pd.DataFrame(rows)


def build_price_path() -> pd.DataFrame:
    """Brand price index per quarter (quarter_index, label, price_index).

    Periods come from the calendar (the single source of truth for quarter
    boundaries), so labels/indices can never desync from the rest of the panel.
    """
    rows = []
    for q in QUARTERS.itertuples(index=False):
        price_index = _PRICE_RAMP_2025[q.quarter] if q.year >= 2025 else 1.00
        rows.append(
            {"quarter_index": q.quarter_index, "label": q.label, "price_index": price_index}
        )
    return pd.DataFrame(rows)


PRICE_PATH = build_price_path()


def get_price_path() -> pd.DataFrame:
    """Return a copy of the locked quarterly price path."""
    return PRICE_PATH.copy()


# --- Launch items (the two trial/repeat stories tool #4 reuses) --------------
# Mechanism params only. The leaky item is engineered with a big trial reach and low
# repeat propensity (targets ~15% repeat); the sticky item with modest trial and high
# repeat propensity (targets 45%+). The realized rates emerge in A4 and are verified
# against bands in A6 — they are not asserted here.
# Both launch in burn-in (2023-Q2) so the trial spike + repeat runway sit BEFORE the
# 2024-2025 analysis window — this is the runway the brief wants for #4, and it keeps
# the launch spike from distorting Decompose's period-over-period penetration.
LAUNCH_ITEMS = {
    "CHP-SB-010": {  # Snack Bites — impulse, high trial / low repeat
        "role": "leaky",
        "launch_quarter_index": 1,  # 2023-Q2 (burn-in)
        "trial_reach": 0.25,        # big trial spike
        "repeat_propensity": 0.15,  # low stickiness
    },
    "CHP-PS-010": {  # Pantry Staple — repurchased, modest trial / high repeat
        "role": "sticky",
        "launch_quarter_index": 1,  # 2023-Q2 (burn-in)
        "trial_reach": 0.09,        # modest trial
        "repeat_propensity": 0.52,  # high stickiness
    },
}
assert all(sku in ALL_SKUS for sku in LAUNCH_ITEMS), "launch SKUs must be canonical"


def get_launch_items() -> pd.DataFrame:
    """Return launch-item metadata as a frame (for tool #4's trial/repeat analysis)."""
    rows = []
    for sku, cfg in LAUNCH_ITEMS.items():
        label = QUARTERS.loc[cfg["launch_quarter_index"], "label"]
        rows.append({"sku_id": sku, "launch_label": label, **cfg})
    return pd.DataFrame(rows)
