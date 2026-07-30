# Decompose — Full Specification

Tool #3 of the Cinderhaven sales-penetration series. This spec is the buildable
contract behind the brief and brainstorm (both in `docs/brainstorms/`). Read
alongside CLAUDE.md (rules), DECISIONS.md (locked choices), PLAN.md (arc).

---

## 1. The problem

Sales moved. A single top-line number cannot say *why*, and each "why" implies a
different next move:

| Lever | If this moved | You pull |
|---|---|---|
| **Buying households** (household penetration) | More/fewer distinct households bought at all | Trial drivers — display, sampling, distribution |
| **Purchase frequency** | Existing buyers came back more/less often | Usage occasions, reminders, loyalty |
| **Spend per trip** | Each trip got bigger/smaller | Pack architecture, trade-up, price |

A brand that cannot decompose its growth literally cannot tell whether its
*marketing* (trial) or its *merchandising* (basket) is working.

## 2. The disambiguation job (spine of the series)

Tool #1 (Door Math) is **shelf** penetration — % of *doors/ACV* carrying the
brand. This tool is **buyer** penetration — % of *households* that bought the
brand at least once in a period (the Byron Sharp / *How Brands Grow* metric).
Conflating them produces bad strategy. Decompose exists partly to make the
distinction concrete, and it is the payoff to the live blog post "Penetration
Means Three Things" (household penetration = "Meaning #3, the one your dashboard
isn't showing you").

Panel data ≠ POS data. Most small brands have POS (scan) data and no panel
(Numerator/Circana territory). The writeup explains this distinction.

## 3. The decomposition math

### 3.1 Identity

For a period *t*, with a fixed panel of `N` total households:

```
Sales_t = BuyingHouseholds_t × Frequency_t × SpendPerTrip_t
Penetration_t = BuyingHouseholds_t / N
SpendPerTrip_t = UnitsPerTrip_t × PricePerUnit_t   (optional 2nd-level split)
```

Because `N` is fixed across periods, movement in **buying households** *is* the
movement in **household penetration** (a rescaling by `N`). The three levers are
therefore: **buying households**, **frequency**, **spend per trip**.

### 3.2 Period-over-period bridge (the waterfall) — MUST reconcile exactly

`ΔSales = Sales_B − Sales_A` must equal the sum of three lever contributions with
no residual. A product change `A·B·C → A'·B'·C'` does not split additively by
inspection, so use an **order-independent exact attribution**:

- **Default method: Shapley decomposition** (average marginal contribution of each
  factor over all `3! = 6` orderings). For three factors the Shapley contributions
  sum *exactly* to `ΔSales` by construction, and the method is symmetric (no
  arbitrary factor ordering). This is the reconciliation guarantee.
- **Rejected alternative: single-order sequential substitution.** Exact but
  order-dependent — the lever you list first absorbs the interaction terms, which
  is misleading in an exec-facing verdict. Document why it was rejected in
  DECISIONS.md if ever revisited.

**Hard test (Slice 2):** for every period pair and edge cases (zero delta,
single-lever move, all-negative, one factor = 0), assert
`sum(lever_contributions) == ΔSales` to floating tolerance ≤ 1e-6 (ideally exact).

### 3.3 Buyer flow (the "why" behind penetration)

Classify each household for each period pair (A→B):

- **New** — bought in B, did not buy in A.
- **Retained** — bought in both A and B.
- **Lapsed** — bought in A, did not buy in B.

Accounting identities (unit-tested every period):

```
BuyingHouseholds_A = Retained + Lapsed
BuyingHouseholds_B = Retained + New
```

"Lapsed" needs history runway — hence the burn-in quarters in the panel.

## 4. The household panel (Slice 1)

Ships as `packages/cinderhaven-household-panel` — see that package's README for
the full contract. Summary:

- **~5,000 households**, **12 quarters** (4 burn-in + 8 analysis). Locked `SEED`.
- Grain: `household_id × transaction × item × date × spend`, aligned to the
  canonical universe (50 SKUs / 5 lines / 6 retailers, ~$25M brand at wholesale /
  ~$32.3M/yr retail scan (t52w); ~$99M scanned over three years).
- **Brand-scale projection (v0.2.0):** absolute totals (sales $, buyer/household
  counts, trip counts) are scaled by one locked factor k to retail-scan brand scale;
  rates (penetration/frequency/spend-per-trip) stay panel-measured. See DECISIONS.md.
- **Right-skewed** purchase frequency (negative-binomial-ish): a few heavy buyers,
  a long tail of one-and-done. Realism unit-tested — never uniform/toy.
- **Seeded story:** a window where **sales grow on price while household
  penetration declines** ("growth that's actually erosion"), unit-tested to exist.
- Deterministic + reproducible (`assert_frame_equal` across generations).
- **In-process, not in the DB.** The app imports the package and generates/caches
  the panel at startup (disk cache; never regenerated per request). Because the
  panel is deterministic and seed-locked, persisting it to `cinderhaven-db` would
  only create a second copy of canonical data — so we don't. This deliberately
  keeps Decompose (and #4) off the `cinderhaven-db` fragility surface (cred sync,
  503 gate, pg health check). No Postgres at request time.

## 5. Outputs (Slice 4)

1. **Three-lever waterfall** — bridges period-A sales to period-B sales across
   buying-households / frequency / spend-per-trip; reconciles to `ΔSales`.
2. **Penetration trend + buyer flow** — household penetration % over the analysis
   quarters, with the new/retained/lapsed decomposition stacked beneath.
3. **"Which lever" verdict** — a plain-language paragraph naming the dominant lever
   and the recommended next move; board-deck ready.
4. Supporting: per-period metric cards (penetration %, frequency, spend/trip),
   a spend-per-trip sub-split (units × price), and an ag-grid detail table.

All charts use the shared Spin Rate chart template; every chart is inspected for
clipped labels, duplicate/misrounded currency ticks, and legend overlap.

## 6. App architecture (Slice 3 — clone Spin Rate)

- `wsgi.py` entry; `app/` package (`app.py`, `layout.py`, `views/`,
  `decomposition.py`, `charts.py`, `components.py`, `filters.py`, `constants.py`,
  `panel_data.py`, `lailara_frame.py`); `assets/`; `packages/`.
- Data layer is `panel_data.py`, **not** `db.py`: it imports
  `cinderhaven_household_panel`, generates the panel once, caches it to disk, and
  serves period metrics / buyer flow / decomposition for each filter combination.
  No psycopg2, no `DATABASE_URL`.
- **Health = liveness only.** The Fly check targets a liveness endpoint that
  returns 200 while the process is up. There is no DB to degrade, so there is no
  readiness endpoint and no 503-on-DB gate — the Spin Rate bug is designed out
  rather than worked around.
- Branded pre-hydration loading state (no blank white first paint on a cold link).

## 7. UX / exec-facing content

- Lead with one big headline number in plain language a CFO can't misread.
- LABEL every number with its timeframe; show + allow selecting the as-of date.
- Filter row: one tidy grid, equal-width controls, common label baseline.
- Stat cards with hierarchy (primary emphasized, secondary muted).
- Tooltips on every metric/filter; "why this matters" panel; glossary;
  synthetic-data disclosure on page. Copy gets a Shawn review pass.
- Tabs each render their own content (regression-tested).

## 8. Testing (the Spin Rate bar)

Waterfall reconciliation · buyer-flow identities · panel canonical/reproducibility
· panel realism (skew) · seeded-story existence · tabs regression · chart-config
(no dup ticks / no clipped labels where assertable). Green before done.
`/ce:compound` + multi-agent review; findings driven to resolution.

## 9. Deploy & deliverables

- Fly.io (`iad`, shared-cpu-1x) → `decompose.lailarallc.com`.
- Work-page card in the Door Math / Spin Rate format.
- Launch/reveal blog post draft ("here's the one your dashboard isn't showing you").
- **Leave the panel generator ready for #4.**
- CONFIRM with Shawn before deploy: (1) name/subdomain, (2) panel size/period
  count, (3) anything touching locked canonical figures.

## 10. Open questions (defaults chosen; flag if changing)

1. **Panel realism source** — default: hand-tuned negative-binomial parameters
   (brief says hand-tuned is fine if the skew reads real). Alternative: fit to a
   public reference shape.
2. **Launch post placement** — standalone reveal post vs capstone to the
   penetration series. Decide before writing the post.
3. **Spend-per-trip 2nd-level split** (units × price) — include as a drill-down or
   keep the top three levers only for v1. Default: show it as a sub-split on the
   spend-per-trip lever, not a separate top-level waterfall.
```
