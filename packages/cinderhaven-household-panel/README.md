# cinderhaven-household-panel

Shared, versioned, **seed-locked** synthetic **household panel** for the
Cinderhaven sales-penetration tools. Built by tool #3 (Decompose); imported
unchanged by tool #4 (Leaky Bucket). This is the largest new data asset of the
series — panel data, not POS scan data.

> **Status: built (v0.2.0).** Deterministic given `SEED=42`; 58 canonical / realism /
> seeded-story / projection / integration tests green. Packaged like
> `cinderhaven-store-universe` (doormath) — `pip install -e .` (requires that peer
> package installed for the canonical universe).

## Why a package (not per-tool code)

The panel is shared with #4. A second copy would drift. Ship it once as a
`pip install -e`-able package with a locked `SEED`, deterministic generation, and
a canonical test — exactly how `cinderhaven-store-universe` is shipped.

## Grain

`household_id × transaction × item × date × spend` — with derived per-period
aggregates. Households buy the canonical universe: ~$25M brand at wholesale
(~$33M/yr at retail scan), 50 SKUs, 5 product lines (AS·PS·SC·DG·SB), 6 retailers.

## Brand-scale projection (v0.2.0)

`get_period_metrics` and `get_buyer_flow` scale **absolute totals** — sales $,
buyer/household counts, trip counts — by one fixed factor `k` (`get_projection_factor`,
≈ 166.49) so they read at Cinderhaven's retail-scan brand scale. **Rates** (household
penetration %, purchase frequency, spend per trip) are panel-measured and NOT scaled —
`k` cancels in a ratio. `k` is locked (one factor for every period, so real movement is
preserved) and anchored so the reference year (2025) projects to the canonical annual
scan revenue (`$32,323,139.62`, CY2025 — canonical_values.yml `revenue.retail_scan.cy2025`,
verified against production 2026-07-29); it derives from the verified canonical figure, does not alter it,
and is the identical factor tool #4 uses. NB: the oft-quoted **~$99M is the 3-year
cumulative scan total, not annual**.

## Timeline (locked)

- **~5,000 households**
- **12 quarters total** = **4 burn-in quarters** + **8 analysis quarters**
- Burn-in exists so tool #4's trial/repeat logic has history runway before the
  analysis window. Do not remove it.

## Realism bar

- Purchase-incidence and frequency distributions are heavily right-skewed
  (negative-binomial-ish). If they look uniform/toy, anyone who has seen real
  panel output dismisses the demo. Enforced by realism unit tests.

## Seeded story (the punchline)

A deliberate window where **sales grow on price increases while household
penetration quietly declines** — "growth that's actually erosion" — mapping to the
trap named in the anchor blog post. Enforced by a unit test.

## API (shipped)

```python
from cinderhaven_household_panel import (
    SEED, PANEL_VERSION,           # locked int (42), version string ("0.2.0")
    N_HOUSEHOLDS,                  # 5000
    BURN_IN_QUARTERS, ANALYSIS_QUARTERS, TOTAL_QUARTERS,   # 4, 8, 12
    ALL_SKUS, PRODUCT_LINES, RETAILERS, REGIONS,           # canonical universe (reused)
    LAUNCH_ITEMS,                  # the two #4 launch stories (leaky / sticky)
    get_quarters,                  # 12-quarter calendar (label, phase, dates)
    get_households,                # 5,000 households: region + latent propensity/sensitivity/affinity
    get_sku_prices, get_price_path,# per-SKU base price; quarterly price index (2025 ramp)
    get_launch_items,              # launch metadata (sku, launch quarter, trial/repeat params)
    get_transactions,             # THE PANEL: household x quarter x date x sku x retailer x units x spend
    get_period_metrics,            # per-quarter penetration, frequency, spend/trip (+ units/price split), absolute totals projected; product_line/retailer filters
    get_buyer_flow,                # new / retained / lapsed per adjacent quarter pair (projected counts)
    get_projection_factor,         # the locked brand-scale factor k (shared with #4)
    CANONICAL_ANNUAL_SCAN_REVENUE, PROJECTION_REFERENCE_YEAR,  # $32.32M CY2025 anchor
)
```

`get_period_metrics(product_line=None, retailer_id=None)` and `get_buyer_flow(...)`
take optional filters. Penetration denominator is always the full panel
(`N_HOUSEHOLDS`, and penetration stays the raw panel share — it is not projected).
The identity `buying_households × frequency × spend_per_trip == sales` holds per
quarter (projected `buying_households` and `sales` both carry `k`, so it reconciles).
All generators are deterministic given `SEED` and return identical frames across calls.

**Note on erosion grain:** the seeded "growth that's actually erosion" story is a
*quarterly* signal (annual reach saturates). Compare quarters year-over-year
(2025-Qn vs 2024-Qn) to see sales rise while household penetration falls.

## Tests

Mirror `cinderhaven-store-universe/tests/test_canonical.py`: fixed counts, locked
seed, reproducibility, realism (skew), and the seeded-story assertion.
