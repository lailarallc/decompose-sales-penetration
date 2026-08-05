# Decompose — Client Data Input Specification

Decompose splits a period-over-period sales change into the three levers that
fully explain it — **buying households × purchase frequency × spend per trip** —
reconciling exactly to the sales delta (Shapley), and names the lever to pull.

**Grain note.** Decompose is a **household-panel** tool, not a store-POS tool. Its
levers are household-level, so it does **not** use the shared POS scan contract
(store/week grain). It reads a client **panel-transaction** file through the same
`lailara_engagement` scaffold (tolerant intake + preflight + provenance).

## §Transactions — the panel trip ledger (required)
One row per shopping trip on the brand (or per line item, if you provide
`trip_id` to group them).

| Column | Type | Required | Used for |
|---|---|---|---|
| `household_id` | identifier (text) | **required** | buying-household counts (penetration) |
| `period` | string | **required** | the period label the trip falls in (e.g. `2025-Q2`) |
| `spend` | number ≥ 0 | **required** | sales; spend-per-trip |
| `trip_id` | identifier (text) | optional | groups line items into a trip; **absent ⇒ each row is one trip** |
| `units` | number ≥ 0 | optional | reported if present; not required for the decomposition |

Per period the tool derives: buying households (distinct `household_id`),
frequency (trips ÷ buyers), and spend per trip (spend ÷ trips). Their product is
total spend by construction — the identity the waterfall reconciles to.

## Periods (required)
Name the two periods to bridge — `--period-a` / `--period-b` or
`basis.period_a` / `basis.period_b` in `engagement.yml`. Both must appear in the
`period` column.

## Column mapping (`engagement.yml`)
```yaml
client: {name: Your Brand}
engagement: {id: YB-2026-08}
as_of_date: 2026-06-27
basis:
  period_a: "2025-Q1"
  period_b: "2025-Q2"
inputs:
  transactions: client-data/transactions.csv
columns:
  household_id: "Panelist ID"
  period: "Quarter"
  spend: "Trip $"
  trip_id: "Basket ID"
```
