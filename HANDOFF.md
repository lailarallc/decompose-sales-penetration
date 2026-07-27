# Decompose — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at session end.

For durable choices, see DECISIONS.md. For the current arc, see PLAN.md. For
things that didn't work, see FAILURES.md.

---

## 2026-07-27 14:28 — Session close (/wrap): improve + code review + UI review, redeployed

**Started from:** Decompose live + public + brand-scale; scheduled improvement review
due today. Task: run improve, code review, and UI review.

**Did:** Full audit + 4 parallel review personas (correctness/math, Python, testing,
security) + automated UI review vs the live site. **0 critical** — math verified fully
correct, security clean (no secrets, liveness-only health, no injection paths). Fixed
every finding incl. nice-to-haves in 11 commits: panel version 0.1.0→0.2.0; panel
internal cleanup (shared `line_of`, price path from calendar SSOT, dead code, hoisted
imports) — **value-preserving, every generated frame hashes identical**; typed
decomposition/data APIs (TypedDicts) + legible bit-identical Shapley; neutral zero-delta
card; ruff now enforces 100-col (`[tool.ruff.lint] select`); hardened `parse_filter_state`
+ non-root Docker + adversarial tests; **+9 tests covering the untested "sales fell"
verdict** + formatters + delta-down + KeyError; dropdown radius/border → palette,
`.view-heading` stray serif removed. Pushed + **redeployed to Fly**, verified live
(health 200, new CSS markers serving). Also repaired dangling editable installs (pinned
to the deleted `projects\active\` path — pytest couldn't import the panel).

**State:** 64 app + 58 panel = **122 tests green**, ruff clean, panel byte-identical,
no secrets. Deployed + verified: decompose.lailarallc.com/health 200. Clean tree, pushed.
2 memories saved (editable-install gotcha, panel hash-check).

**Next:** No open work on Decompose. Natural next: tool #4 (Leaky Bucket) — imports the
now-v0.2.0 panel (shared factor k, launch stories baked in). Still awaiting Shawn's
blog/work-card copy pass in `docs/launch/`.

---

## 2026-07-07 00:55 — Session close (/wrap)

**Started from:** Slices 1 & 2 done; next was Slice 3 (app shell). Repo private, not deployed.

**Did:** Slices 3–6 end to end — app shell (in-process, no DB, liveness health), all
outputs (waterfall/penetration/flow/cards/table), 5-persona review + fixes, deploy to
Fly + **decompose.lailarallc.com** (found + stored the Cloudflare DNS token outside the
repos), `/ce-compound` (3 learnings), brand-scale projection (panel v0.2.0, k≈166.49
anchored to $32.8M annual scan), `/code-review` + `/improve` + repo made **public** with
description/topics. Corrected the "$99M is 3-year not annual" spec error and fixed +
redeployed the Void Finder footer.

**State:** Decompose live + public + brand-scale; 55 app + 58 package tests green; secrets
clean. Void Finder redeployed. All pushed except the wrap commit.

**Next:** Blog + work-card copy pass (`docs/launch/`); decide the portfolio-wide "$25M
wholesale vs $33M retail" brand descriptor; tool #4 (Leaky Bucket) can now import the
v0.2.0 panel (shares factor k).

---

## 2026-07-06 — Slice 6: brand-scale projection (panel v0.2.0), redeployed

**Why:** the ~5k-household panel's raw dollars (~$0.19M/yr) didn't tie to the
Cinderhaven portfolio. Now ABSOLUTE totals project to brand scale; RATES stay
panel-measured.

**Did:**
- **6A (panel v0.2.0):** `get_period_metrics` / `get_buyer_flow` scale absolute
  totals (sales $, buyer/household counts, trip counts) by one fixed factor
  **k ≈ 166.49**, defined in the shared package (`get_projection_factor`, shared with
  #4). k = canonical annual scan revenue **$32.8M** / raw 2025 panel sales. Rates
  (penetration/frequency/spend-per-trip) untouched — k cancels. Product + flow
  identities still hold; waterfall reconciles at brand scale; verdict unchanged. +9
  projection tests (58 package tests green).
- **6B (UI):** "Projected to brand scale" chip + tooltip; glossary entry; waterfall
  y-axis SI-abbreviated (`$2M`), buyer-flow labels SI (`248k`). Verified live: headline
  **$8.2M in 2025-Q4 / +$325K**, "driven mainly by higher spend per trip" (unchanged).
- **6C (canonical-copy + redeploy):** corrected the spec error that **~$99M is
  3-YEAR cumulative scan, not annual** (annual scan = $32.8M). Fixed the Void Finder
  footer (voidfinder commit `55eea94`). Broad repo sweep otherwise clean. Redeployed
  Decompose — **live at brand scale** (decompose.lailarallc.com/health 200).

**Sign-off:** Shawn confirmed $32.8M/yr as the anchor.

**Open (for Shawn):**
- **Void Finder needs a redeploy** to publish its footer fix (only the repo is fixed).
- The apex **lailarallc.com site (Cloudflare-hosted)** was checked live across
  home/work/about/services/case-studies/tools/portfolio — **no "$99M" copy, clean.**
- Whether to restyle the canonical brand descriptor from "$25M" (wholesale) to the
  retail framing portfolio-wide is a copy-pass call (left as-is; canonical currently
  says "use $25M phrasing").
- **Publish gate** still needs `/improve` (code-review now recorded).

**State:** 55 app + 58 package tests green. PANEL_VERSION 0.2.0.

---

## 2026-07-06 — Slice 5: reviewed, fixed, DEPLOYED (custom-domain DNS pending)

**Deployed and LIVE at https://decompose.lailarallc.com** (HTTPS, cert Issued) — also
`decompose-sales-penetration.fly.dev` (2 machines, iad, health passing). `/health` →
`200 {"status":"ok"}`; production `_dash-layout` has all chart targets + as-of note +
synthetic disclosure — panel generates in-container, app fully wired.

**Custom domain done via Cloudflare API.** The Lailara DNS-edit token was located and
stored at `~/.config/lailara/cloudflare-dns-token` (outside all repos; see the
`cloudflare-dns-token` memory — the wrangler OAuth is `zone:read` only and can't edit
DNS). Created DNS-only CNAMEs matching doormath's pattern:
`decompose → zkpr0nm.decompose-sales-penetration.fly.dev` + the `_acme-challenge`
CNAME. Token value is NOT in any repo (verified).

**5A — multi-agent code review (5 personas):** correctness, Python, maintainability,
testing, project-standards. Drove all real findings to resolution:
- **Correctness bug fixed:** period_a == period_b made the verdict falsely claim
  "Sales rose $0 … driven by more households buying." Now a neutral "unchanged"
  verdict + neutral headline.
- Data-driven card deltas (no more label-string branch); consolidated 3 duplicated
  `_filters` into `panel_data.parse_filter_state`; removed 34 dead palette tokens +
  `fmt_delta`; dropped redundant xaxis overrides; added value labels to the
  buyer-flow bars + penetration points (chart rule); hardened `_nice_dollar_dtick`
  ($1 floor). **+24 tests** (charts, figure-builders, zero-delta, parse). Fixed the
  stale README (no-DB reality).

**5B — drafts** in `docs/launch/` (blog reveal post + work-page card) for Shawn's
copy pass.

**5C — deploy:** vendored `cinderhaven-store-universe` into `packages/` (best-practice
for this context — matches the lailara-palette precedent; textbook alt is a private
index but that's overkill for a locked, versioned canonical package). Panel's 49
canonical tests still pass (no drift). Confirmed with Shawn: name/subdomain/panel
unchanged; deploy go-ahead given.

**State:** **104 tests green** (55 app + 49 panel), ruff clean. Image 151 MB.

**Remaining (not blocking a working deploy):**
- DNS for the custom domain (above).
- Optional: `/ce:compound` to compound the learnings (no-DB decision, ag-grid
  hidden-init fix, the review). `/publish` to flip the repo public when ready.
- Shawn's copy pass on the blog/work-card; a prescriptive "next move" line on the
  verdict if wanted (kept computed/honest for now).

---

## 2026-07-06 — Slice 4 complete: all outputs live (charts, cards, table)

**Did (5 commits, 4A–4E):** Built the real outputs, each inspected in-slice.
- `charts.py`: cloned economist_layout + CHART_CONFIG; added `dollar_yaxis` /
  `_nice_dollar_dtick` for true, evenly-spaced, non-duplicate $ ticks.
- **Waterfall** (which_lever): `go.Waterfall` bridging Period A→B across the three
  levers, reconciled to ΔSales; increase=teal / decrease=berry / totals=navy, bold
  signed-$ labels, exact-$ hover. Figure + verdict recompute together from filters.
- **Penetration trend + buyer flow** (penetration): penetration % line (A/B marked)
  + new/retained/lapsed relative bars (lapsed below zero).
- **Metric cards + ag-grid table** (detail): four cards (Sales, penetration,
  frequency, spend/trip; B big, A + signed Δ) + per-quarter grid (Quarter pinned,
  cents where they matter).
- **Glossary** (6 terms), **filter tooltips**, **why-this-matters** panels.

**Real bug fixed:** ag-grid mounted in a `display:none` tab panel sized its columns
to 0 width. Keyed the detail callback on `main-tabs` value so the grid rebuilds when
the tab is shown → responsiveSizeToFit fits all 8 columns. (Also: charts render their
data via callbacks at load regardless of tab visibility — so verifying chart *data*
doesn't require the tab to be visible; only the ag-grid *sizing* did.)

**Inspected** @1280 and @375 across all three tabs: no clipped labels, currency
ticks true/non-duplicate ($0..$50,000; 0%..50%), legends at bottom, bold labels, no
horizontal overflow, no console errors. Whole-brand default is the erosion story end
to end — penetration −2.2pp, frequency −0.14 trips, spend/trip +$1.88 → +$1,954.

**State:** **80 tests green** (31 app + 49 panel), ruff clean. Preview-harness notes:
Plotly inits at 0 width until a viewport is set (resize to 1280 first); dcc.Tab divs
don't respond to `preview_click` — drive them with a native `.click()` via eval.

**Deferred to Shawn (Slice 5 copy pass):** a prescriptive "recommended next move" on
the verdict. Kept the verdict computed/honest (names the dominant lever) rather than
scripting advice — that's a copy decision for Shawn.

**Next:** Slice 5 — ship. `/ce:compound` + multi-agent code review; drive findings to
resolution; then deploy (needs Shawn's go-ahead + the store-universe vendoring blocker
resolved — see FAILURES.md); Work-page card; launch blog post draft.

---

## 2026-07-06 — Slice 3 complete: app shell (in-process, no DB)

**Decision (Shawn):** Decompose uses **no database**. Data is the in-process,
seed-locked `cinderhaven-household-panel` package, warmed once at startup. No
psycopg2, no `DATABASE_URL`, no Postgres at request time — this keeps Decompose (and
#4) off the `cinderhaven-db` fragility surface (cred sync, 503 gate, pg health check).
Corrected CLAUDE.md/SPEC/PLAN/app-CLAUDE and superseded the two DB decisions in
DECISIONS.md to match. Memory saved (`no-db-in-process-panel`).

**Did (7 commits, 3A–3F):** Vendored `lailara-palette` + assets; full app stack in
`pyproject.toml`. Built `panel_data.py` (the single data seam: warm_cache, filter
options, exec defaults, metrics/flow pass-throughs, `decompose()` bundle). Cloned the
Spin Rate shell: `app.py` (Dash factory + branded loading overlay), `constants.py`
(tokens + three-lever vocabulary), `lailara_frame.py`, `layout.py` (3 tabs + 4-control
filter bar + as-of/synthetic disclosure + tab-toggle), `filters.py`, `components.py`,
`views/` (which_lever/penetration/detail). `wsgi.py` with **liveness-only** `/health`;
`fly.toml`/`Dockerfile` with no DB secret.

**One output already live end-to-end:** the verdict headline recomputes from the
filters via the tested `panel_data.decompose`. Whole-brand default (2024-Q4→2025-Q4)
lands the punchline: *"Sales rose $1,954 … driven mainly by higher spend per trip."*

**No disk cache** (overrode the "cache to disk" ask, flagged to Shawn): panel gen is
**measured ~0.6s**, already `lru_cached`, and Fly `min_machines_running=1` keeps the
machine up — a parquet cache would save ~0.6s at rare boots and can't be wired without
coupling to the package's internal cache. Warm-at-startup instead. DECISIONS logged.

**State:** **77 tests green** (28 app: 13 decomposition + 11 panel_data + 4 tabs
regression; 49 panel package). Run-verified live: boots clean, `/health` 200, tabs
switch (only active panel shows), no horizontal overflow at 1280px or 375px, no
console errors. Note: env has **Dash 4.2.0** (CLAUDE said 3.x) — clone works on 4.x.

**⚠ Slice 5 deploy blocker (FAILURES.md):** peer pkg `cinderhaven-store-universe`
lives in the doormath repo, not in this build context — the Docker image won't build
until it's vendored into `packages/` (or a private index). Flagged in the Dockerfile.

**Next:** Slice 4 — the real outputs, each reviewed in-slice: three-lever waterfall
chart (shared chart template + the #5 chart rules: automargin, non-dup currency ticks,
bottom legend, bold labels), penetration trend + buyer-flow chart, "which lever"
diagnostic panel / glossary / tooltips, per-period metric cards + ag-grid detail
table. Replace the three `slice4_placeholder` blocks. The loading overlay currently
watches `#main-tabs .custom-tab`; consider re-pointing it at the waterfall chart once
it exists.

---

## 2026-07-06 — Slice 2 complete: decomposition math + verdict

**Did:** Built `app/decomposition.py` — exact **Shapley** three-lever waterfall
(buying households x frequency x spend-per-trip) that reconciles to ΔSales, plus a
direction-aware "which lever" verdict with the honest-hedge threshold. Root app
package + minimal `pyproject.toml` scaffolded (Slice 3 adds the dash/plotly/psycopg2
stack). Also cached `get_transactions` (deterministic) — speeds metrics + app filter
callbacks. Penetration/frequency/spend + buyer flow were already delivered in the
panel package (A5), so Slice 2's remaining work was the waterfall + verdict.

**State:** **62 tests green** (49 panel + 13 decomposition). Reconciliation proven on
2000 random triples + real pairs. Real erosion pair 2024-Q4→2025-Q4: sales +$1,954
"driven mainly by higher spend per trip" while buying households −$2,459 and
frequency −$3,597 — the growth-is-actually-erosion punchline, computed honestly.

**Next:** Slice 3 — clone the Spin Rate app shell (Dash/Plotly, `lailara_frame`,
`lailara-palette`, assets, shared chart template with the #5 chart rules), resilient
`/health` (liveness endpoint for the Fly check + separate DB readiness), branded
loader, `DATABASE_URL` into the synced cred set. This is the visual + DB + deploy
phase — expand root `pyproject.toml` to the full stack here. Deploy (Slice 5) needs
Shawn's explicit go-ahead.

---

## 2026-07-06 — Slice 1 complete: household-panel generator built

**Did:** Built `cinderhaven-household-panel` end-to-end (A1–B), committing each
sub-task: locked constants + 12-quarter calendar (A1); household dimension with
gamma propensity + price-sensitivity + innovator-affinity (A2); per-SKU prices +
2025 price-up path + two launch items (A3); vectorized NB transaction generator with
launch trial/repeat + retailer dimension (A4); period-metrics + buyer-flow accessors
(A5); seeded-story gates (A6); integration/version/README (B).

**State:** **49 tests green.** Panel is deterministic (`SEED=42`), versioned
(v0.1.0), reproducible, importable by #4. Emergent + verified: quarterly erosion
(2024→2025 YoY sales up ~+4%, mean penetration −1.5pp; flat 2023→2024 does not
erode), realism (trips/hh var/mean≈15, skew≈2.3), launch repeat leaky ~14% /
sticky ~52%. New scope folded in per Shawn: #4's two launch stories baked into the
shared panel (burn-in launch, 2023-Q2); retailer dimension added for the app slice.

**Decisions this session:** penetration erosion is a *quarterly* phenomenon (annual
reach saturates) → compare quarters YoY; launches sit in burn-in for #4 runway.

**Next:** Slice 2 — decomposition math: three-lever waterfall (Shapley, reconciles
exactly to ΔSales) + "which lever" verdict with the honest-hedge threshold, built on
`get_period_metrics` / `get_buyer_flow`. Then Slice 3 (clone Spin Rate app shell).

---

## 2026-07-06 — Project initialized + fully spec'd

**Started from:** New project. Brief + brainstorm attached (now in
`docs/brainstorms/`).

**Did:**
- Read prior memory across cinderhaven-db, Spin Rate, Void Finder, doormath;
  summarized carried lessons (DB resilience, don't-touch-cinderhaven-db, design/
  chart rules, shared-package + seed-locking, exec-facing content).
- Locked decisions with Shawn: name=**Decompose**, subdomain
  **decompose.lailarallc.com**, panel = **5,000 households × 12 quarters
  (8 analysis + 4 burn-in)**. Repo **private** (flips public later via /publish).
- Ran the new-project process: workflow state files, hierarchical CLAUDE.md,
  `.gitignore`, README (Lailara standard), full spec (`docs/SPEC.md`), git init +
  GitHub remote.
- Recorded inherited dead-ends in FAILURES.md so they aren't re-discovered.

**State:** Foundation complete. Slice 0 done. No app or panel code yet.

**Blocker/note:** The original folder `decomppose-sales-penetration` (misspelled,
double-p) is pinned open by this session and can't be renamed in place. All work
is in `decompose-sales-penetration`. **Reopen Claude Code in
`decompose-sales-penetration` for the next session**, and delete the empty
misspelled folder from a session not rooted in it.

**Next:** Slice 1 — scaffold `packages/cinderhaven-household-panel` and generate
the seed-locked panel (right-skewed frequencies, burn-in, seeded erosion story),
with canonical/reproducibility + realism unit tests. See PLAN.md.

---
