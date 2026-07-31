Never write secrets, tokens, or passwords into tracked files, READMEs, or commit messages — use environment variables and secret stores only.

# Decompose — Project Context for Claude

## What this project is

Decompose is **tool #3 of 5** in the Cinderhaven sales-penetration series
(#1 Door Math · #2 Spin Rate · **#3 Decompose** · #4 Leaky Bucket · #5 Void
Finder). It answers a single CEO/CFO question: **did sales move because more
households bought us, because they bought more often, or because they spent
more per trip — and which lever do we pull next?**

It decomposes **Sales = buying households × purchase frequency × spend per
trip**, reports household penetration % and new/retained/lapsed buyer flow, and
produces a three-lever period-over-period waterfall that reconciles *exactly* to
the sales delta. It is the payoff to the live blog post "Penetration Means Three
Things" — household penetration is "Meaning #3, the one your dashboard isn't
showing you."

**Business question this project answers:** Which of the three growth levers
(more buyers / more frequent trips / bigger baskets) actually moved this brand's
sales between two periods, and which one should we pull next?

**Paired build:** #3 builds the shared synthetic **household panel**; #4 (Leaky
Bucket) imports the same panel. The panel ships as a standalone, versioned,
seed-locked package (`cinderhaven-household-panel`) — never a second copy. A
burn-in period is baked into the panel timeline now so #4's trial/repeat has
history runway.

## Stack and tools

- Primary language: Python 3.11
- App: Dash 4.x + Plotly 6.x (mirror the Spin Rate stack, do not reinvent)
- Data: pandas 2.x, numpy. **In-process only** — the app imports the seed-locked
  `cinderhaven-household-panel` package, generates the panel once, and caches it to
  disk. **No psycopg2, no Postgres, no `DATABASE_URL` at request time.** (The panel
  is deterministic; a DB copy would just duplicate canonical data. This keeps
  Decompose off the `cinderhaven-db` fragility surface — see Database section below.)
- UI: dash-ag-grid for tables, clientside JS callbacks
- Deploy: Gunicorn + Docker + Fly.io (shared-cpu-1x, `iad`)
- Entry point: `wsgi.py`
- Subdomain: `decompose.lailarallc.com`
- Shared packages: `packages/cinderhaven-household-panel` (new, this repo owns it),
  `lailara-palette` (design tokens, cloned from Spin Rate)

## Project files

- CLAUDE.md (this file) — permanent rules and facts
- DECISIONS.md — durable choices and reasoning
- HANDOFF.md — current session state (read at session start)
- PLAN.md — current work arc (read at session start)
- FAILURES.md — things tried that didn't work + inherited dead-ends
- docs/SPEC.md — full tool specification
- docs/brainstorms/ — the original brief and brainstorm
- docs/solutions/ — documented solutions to past problems (bugs, best practices,
  workflow patterns), organized by category with YAML frontmatter (`module`, `tags`,
  `problem_type`). Relevant when implementing or debugging in a documented area.

Global solo-dev workflow rules (`~/.claude/CLAUDE.md`) and the session-start
protocol apply. This file only records what is specific or non-obvious to
Decompose.

## Hard rules — carried from #1/#2/#5, do not relearn

### Data / infrastructure

- **Decompose does not use a database.** Its data is the in-process, seed-locked
  `cinderhaven-household-panel` package (see Stack above). This is deliberate: it
  keeps Decompose (and #4) entirely off the `cinderhaven-db` fragility surface —
  no cred sync, no 503 health gate, no dependence on the unrepairable pg health
  check. The Spin Rate DB-resilience hazards below are therefore designed *out*,
  not worked around.
- **Health = liveness only.** The Fly check targets a liveness endpoint that
  returns 200 while the process is up. There is no DB to degrade, so there is no
  readiness endpoint and no 503-on-DB gate. (Spin Rate's bug: its `/health`
  returned 503 when the DB was down and `fly.toml` checked `/health`, pulling both
  machines from the proxy → external 503. Nothing here can reproduce that.)
- **Do NOT touch `cinderhaven-db` internals** (secrets, roles, restarts). Decompose
  has no reason to connect to it at all. Any work on it needs a separate, explicit
  go-ahead.
- Do not touch the canonical `cinderhaven` raw schema or doormath's locked figures.

### Local dev (this machine)

- No database to run locally — the panel is generated in-process. Run the app with
  `python wsgi.py` (or gunicorn); first boot generates + caches the panel to disk.
- Docker Desktop is broken here (stale-socket crash loop) — build/deploy via Fly's
  remote builder, not local Docker.
- Repo-local `git config credential.helper '!gh auth git-credential'` so `git push`
  auths (already set for this repo).

### Design / charts — identical to Spin Rate by construction

- Reuse Spin Rate's actual design tokens (`lailara-palette`), `lailara_frame`
  header/footer chrome, and shared chart template. This is a clone, not a
  rebuild. Serif headings, brand navy/burgundy, logo + link to lailarallc.com,
  matching footer. Read `LAILARA_DESIGN_SYSTEM.md` before any visual work.
- Charts (bake into the shared template, then verify every chart individually):
  - `automargin=True` / adequate margins so the LONGEST category label renders
    in full — no clipped "5moky…" / "lmond…".
  - Currency ticks show each tick's TRUE value, evenly spaced, NO duplicates —
    fix `dtick` + formatter; extend axis max past the largest value.
  - Legends at the BOTTOM (horizontal), with margin so they never overlap a bar.
  - Bold, formatted value data labels ($ for dollars, ints for counts), not
    clipped at the edge.
  - After building, inspect EVERY chart: no clipped labels, no duplicate/mis-
    rounded ticks, no legend overlap.
- Tabs: each tab renders its OWN distinct content. Add a regression test
  asserting this (a CSS/markup refactor once silently broke it in #5).
- Tables: never truncate the key identifier column. Scores as % or
  High/Med/Low, not raw decimals. Label/clarify any computed column.
- Filter row: one tidy grid, equal-width controls, labels on a common baseline
  (uniform label min-height) so no control floats above the others.
- Stat cards: real hierarchy — primary numbers emphasized (top border/larger),
  secondary counts muted.

### Exec-facing content (this tool is CEO/CFO-facing)

- Lead with one big headline number in plain language a CFO can't misread. Avoid
  implicit phrasing ("sitting in stores" read as inventory in #5).
- LABEL every number with its timeframe; show the as-of/measurement date and make
  it selectable if useful. State the period explicitly.
- Tooltips on every metric and filter; a short "why this matters" panel; a
  glossary; keep the synthetic-data disclosure on the page.
- Shawn reviews all copy — draft it, expect a copy pass. Keep the Cinderhaven
  synthetic figure and methodology honest.

### Data model / canonical

- Reuse shared packages, don't duplicate (the `cinderhaven-store-universe`
  pattern). Lock the panel seeds and version them like `CINDERHAVEN_CANONICAL`.
- The panel aligns to the canonical universe: ~$25M brand at wholesale (~$32.3M/yr
  at retail scan (CY2025); ~$99M scanned over three years — NOT an annual figure), 50 SKUs,
  5 product lines (AS·PS·SC·DG·SB), 6 retailers. `SEED` locked; reproducibility
  unit-tested. Absolute totals are projected to retail-scan brand scale by the panel
  package's locked factor k (v0.2.0); rates stay panel-measured. See DECISIONS.md.
- If anything would shift doormath's or the series' locked canonical figures:
  change protocol + canonical-figures impact check + Shawn's explicit approval.
  Do NOT change locked figures silently.

## Definition of done (matches the Spin Rate bar)

- Waterfall reconciles exactly to the sales delta (unit-tested), panel-realism
  checks pass, tabs regression test passes.
- `/ce:compound` + multi-agent code review run; findings driven to resolution.
- Tests green. HANDOFF.md + FAILURES.md written. Memory saved.
- CONFIRM WITH SHAWN before deploy: (1) name/subdomain, (2) panel size/period
  count, (3) anything touching locked canonical figures.

## Voice and standards

- Economist style for written deliverables: sober, declarative, data-forward.
- No marketing voice or consultant filler ("leverage," "synergy," "unlock,"
  "drive value"). No hedging that softens a real finding.
- Say "I don't know" / "I can't verify this" instead of guessing.
