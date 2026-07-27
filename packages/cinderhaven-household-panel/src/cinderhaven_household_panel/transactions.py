"""Transaction generator — the panel itself (A4).

Grain: one row per household per trip per item (single item per trip). Trip counts
are Poisson with a household's gamma propensity as the rate → negative-binomial /
overdispersed across households, like real panel data. Prices paid scale with the
quarterly price index, so the 2025 price-up stretch raises spend per trip while
price-sensitive households lose trips (and some lapse) — the erosion mechanism.

Two launch items get explicit trial/repeat handling on top of the base assortment:
trial is a launch-quarter spike gated by innovator-affinity; repeat is a per-trier
Bernoulli on the item's repeat propensity, realized in later quarters.

Everything here is mechanism. Penetration, frequency, and repeat rates are computed
from the resulting rows downstream (A5/A6), never written in.
"""

import functools

import numpy as np
import pandas as pd

from ._rng import child_rng
from .calendar import get_quarters
from .constants import ALL_SKUS, N_HOUSEHOLDS, RETAILERS, line_of
from .households import get_households
from .pricing import (
    LAUNCH_ITEMS,
    PRICE_ELASTICITY,
    get_price_path,
    get_sku_prices,
)

# Baseline mean quarterly trips (before propensity/price effects). Tuned so baseline
# household penetration lands in a realistic band (~40-45%); see A6.
BASE_QUARTERLY_TRIP_RATE = 0.9

# Each repeater buys the launch item in a later quarter with this per-quarter prob
# (with at least one repeat guaranteed for repeaters).
_LAUNCH_REPEAT_QUARTER_PROB = 0.5

_COLUMNS = [
    "household_id", "quarter_index", "quarter_label", "date",
    "sku_id", "product_line", "retailer_id", "units", "unit_price", "spend",
]

# Retailer of each trip, drawn in proportion to door count (bigger banners get more
# of the household's trips). Households shop multiple retailers across the panel.
_RETAILER_IDS = np.array(list(RETAILERS.keys()))
_RETAILER_WEIGHTS = np.array(
    [RETAILERS[r]["door_count"] for r in _RETAILER_IDS], dtype=float
)
_RETAILER_WEIGHTS /= _RETAILER_WEIGHTS.sum()


def _base_transactions(hh: pd.DataFrame, quarters: pd.DataFrame,
                       prices: pd.DataFrame, price_path: pd.Series) -> pd.DataFrame:
    """Vectorized base assortment trips for all households across all quarters."""
    rng = child_rng("transactions")

    propensity = hh["base_propensity"].to_numpy()
    price_sens = hh["price_sensitivity"].to_numpy()
    hh_ids = hh["household_id"].to_numpy()
    n = N_HOUSEHOLDS

    # General assortment = everything except the launch items (those are handled
    # separately with trial/repeat). Popularity is a skewed Dirichlet share.
    general = [s for s in ALL_SKUS if s not in LAUNCH_ITEMS]
    general_arr = np.array(general)
    general_lines = np.array([line_of(s) for s in general])
    price_lookup = prices.set_index("sku_id")["base_price"]
    general_base_price = price_lookup.loc[general].to_numpy()
    weights = child_rng("popularity").dirichlet(np.full(len(general), 0.9))

    frames = []
    for qi, label, start, end in quarters[
        ["quarter_index", "label", "start_date", "end_date"]
    ].itertuples(index=False):
        pidx = float(price_path.loc[qi])
        price_effect = pidx ** (-PRICE_ELASTICITY * price_sens)
        lam = BASE_QUARTERLY_TRIP_RATE * propensity * price_effect
        n_trips = rng.poisson(lam)
        total = int(n_trips.sum())
        if total == 0:
            continue

        hh_pos = np.repeat(np.arange(n), n_trips)
        day_span = (end - start).days
        offsets = rng.integers(0, day_span + 1, size=total)
        dates = start + pd.to_timedelta(offsets, unit="D")

        choice = rng.choice(len(general), size=total, p=weights)
        skus = general_arr[choice]
        lines = general_lines[choice]
        unit_price = np.round(general_base_price[choice] * pidx, 2)
        units = 1 + rng.poisson(0.6, size=total)
        spend = np.round(units * unit_price, 2)
        retailers = _RETAILER_IDS[rng.choice(len(_RETAILER_IDS), size=total, p=_RETAILER_WEIGHTS)]

        frames.append(pd.DataFrame({
            "household_id": hh_ids[hh_pos],
            "quarter_index": qi,
            "quarter_label": label,
            "date": dates,
            "sku_id": skus,
            "product_line": lines,
            "retailer_id": retailers,
            "units": units,
            "unit_price": unit_price,
            "spend": spend,
        }))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_COLUMNS)


def _launch_transactions(hh: pd.DataFrame, quarters: pd.DataFrame,
                         prices: pd.DataFrame, price_path: pd.Series) -> pd.DataFrame:
    """Trial (launch-quarter spike) + repeat (later quarters) for the launch items."""
    price_lookup = prices.set_index("sku_id")["base_price"]
    mean_affinity = hh["innovator_affinity"].mean()
    affinity = hh["innovator_affinity"].to_numpy()
    hh_ids = hh["household_id"].to_numpy()
    q_by_index = quarters.set_index("quarter_index")

    rows = []
    for sku, cfg in LAUNCH_ITEMS.items():
        line = line_of(sku)
        base_price = float(price_lookup.loc[sku])
        lq = cfg["launch_quarter_index"]
        reach = cfg["trial_reach"]
        repeat_p = cfg["repeat_propensity"]
        rng = child_rng(f"launch::{sku}")

        # Trial in the launch quarter, gated by innovator affinity (expected ~reach).
        trial_prob = np.clip(reach * affinity / mean_affinity, 0.0, 1.0)
        tried = rng.random(N_HOUSEHOLDS) < trial_prob
        trier_pos = np.where(tried)[0]

        later_quarters = quarters.loc[quarters["quarter_index"] > lq, "quarter_index"].tolist()

        def _emit(pos_array, qi):
            if len(pos_array) == 0:
                return
            qrow = q_by_index.loc[qi]
            pidx = float(price_path.loc[qi])
            day_span = (qrow["end_date"] - qrow["start_date"]).days
            offsets = rng.integers(0, day_span + 1, size=len(pos_array))
            dates = qrow["start_date"] + pd.to_timedelta(offsets, unit="D")
            units = 1 + rng.poisson(0.4, size=len(pos_array))
            unit_price = round(base_price * pidx, 2)
            retailers = _RETAILER_IDS[
                rng.choice(len(_RETAILER_IDS), size=len(pos_array), p=_RETAILER_WEIGHTS)
            ]
            rows.append(pd.DataFrame({
                "household_id": hh_ids[pos_array],
                "quarter_index": qi,
                "quarter_label": qrow["label"],
                "date": dates,
                "sku_id": sku,
                "product_line": line,
                "retailer_id": retailers,
                "units": units,
                "unit_price": unit_price,
                "spend": np.round(units * unit_price, 2),
            }))

        # Trial purchases (launch quarter).
        _emit(trier_pos, lq)

        # Repeat: a per-trier Bernoulli on the item's repeat propensity. Repeaters
        # buy in later quarters (each with prob p), with >=1 repeat guaranteed.
        if len(trier_pos) and later_quarters:
            will_repeat = rng.random(len(trier_pos)) < repeat_p
            repeater_pos = trier_pos[will_repeat]
            bought_any = np.zeros(len(repeater_pos), dtype=bool)
            for qi in later_quarters:
                buy = rng.random(len(repeater_pos)) < _LAUNCH_REPEAT_QUARTER_PROB
                bought_any |= buy
                _emit(repeater_pos[buy], qi)
            # Guarantee at least one repeat for repeaters who drew none.
            missed = repeater_pos[~bought_any]
            if len(missed):
                forced_qi = rng.choice(later_quarters, size=len(missed))
                for qi in np.unique(forced_qi):
                    _emit(missed[forced_qi == qi], int(qi))

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=_COLUMNS)


@functools.lru_cache(maxsize=1)
def get_transactions() -> pd.DataFrame:
    """Return the full, deterministic household panel (household x trip x item).

    Cached: generation is deterministic, so the panel is built once per process and
    reused (metrics/decomposition and the app's filter callbacks all read from it).
    Treat the returned frame as read-only — filters create their own copies.
    """
    hh = get_households()
    quarters = get_quarters()
    prices = get_sku_prices()
    price_path = get_price_path().set_index("quarter_index")["price_index"]

    base = _base_transactions(hh, quarters, prices, price_path)
    launch = _launch_transactions(hh, quarters, prices, price_path)

    panel = pd.concat([base, launch], ignore_index=True)
    panel = panel.sort_values(["household_id", "date", "sku_id"]).reset_index(drop=True)
    return panel[_COLUMNS]
