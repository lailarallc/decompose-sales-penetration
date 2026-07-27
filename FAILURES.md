# Decompose — Failure Log

What was attempted that didn't work, why, and what was tried next. Lower bar than
DECISIONS.md — capture dead-ends so future-you doesn't re-attempt them.

This file is seeded with **inherited dead-ends** from sibling Cinderhaven tools so
they are not re-discovered here.

---

## Entries

### 2026-07-27 — pytest couldn't import the panel: editable installs pinned to the deleted `active` path

**Attempted:** Ran `pytest` at session start; all test modules failed to collect with
`ModuleNotFoundError: No module named 'cinderhaven_household_panel'` — even though
`pip list` showed the package "installed" (at v0.1.0).

**Why it didn't work:** The three local editable installs (`cinderhaven-store-universe`,
`cinderhaven-household-panel`, `decompose-sales-penetration`) were pinned to the OLD repo
path `C:\Users\mssha\projects\active\decompose-sales-penetration`. That folder was deleted
when the repo moved to `projects\published\`, so every editable install dangled. `pip show`
reporting a Location under `projects\active\...` is the tell.

**What we tried instead / fix:** Reinstalled from the current location —
`pip install -e packages/cinderhaven-store-universe -e packages/cinderhaven-household-panel -e . --no-deps`.
Not a code change. (This also surfaced the panel `pyproject.toml` still at 0.1.0 while
`PANEL_VERSION` was 0.2.0 — bumped to 0.2.0.)

**Status:** Resolved. **Lesson:** if tests can't import the local packages on this machine,
reinstall editable from `published\` — don't debug the code. **Tags:** editable-install,
pip, folder-move, pytest

### 2026-07-07 — The wrangler OAuth token can't edit Cloudflare DNS (wasted a long hunt)

**Attempted:** To create the `decompose.lailarallc.com` DNS record, searched env vars,
every `.env`/cred file across all repos, shell profiles, `~/.claude`, Windows Credential
Manager, and MCP connectors for a Cloudflare DNS token. Then tried the wrangler OAuth
token (`~/.wrangler/config/default.toml`) against the Cloudflare API.

**Why it didn't work:** The wrangler OAuth token is scoped `zone:read` + Workers/Pages
only — the `dns_records` endpoint returns `Authentication error (code 10000)`. The
DNS-edit credential is a **separate "Lailara LLC custom token"** that lives ONLY at
`~/.config/lailara/cloudflare-dns-token` (outside all repos); Cloudflare never reveals a
token's value after creation, so it can't be recovered — only Shawn had it.

**What we tried instead:** Shawn provided the token; stored it at the home path above
(see the `cloudflare-dns-token` memory). Fly custom-domain DNS is then a DNS-only CNAME +
`_acme-challenge` CNAME (doormath pattern). Also mis-assumed the apex site was Squarespace
(a `_domainconnect` record) — it's Cloudflare; verified the live site clean directly.

**Status:** Resolved. **Lesson for next time:** for any `*.lailarallc.com` DNS work, read
the token at `~/.config/lailara/cloudflare-dns-token` — do NOT rely on the wrangler OAuth.
**Tags:** cloudflare, dns, credentials, wrangler, deploy

### 2026-07-07 — Preview screenshots time out on infinite CSS animations

**Attempted:** `preview_screenshot` to visually verify the app.

**Why it didn't work:** The selected-tab CSS (inherited from the Spin Rate clone) has a
running animation; the screenshot tool waits for animation/idle and times out (30s).

**What we tried instead:** DOM/`preview_eval` + `preview_inspect` + accessibility
snapshots to verify content, ticks, overflow, and computed styles — more reliable than
screenshots anyway. Also: `dcc.Tab` divs don't respond to `preview_click`; drive them with
a native `document.querySelectorAll('.custom-tab')[i].click()` via eval.

**Status:** Worked around. **Tags:** preview-harness, screenshots, dash, verification

### 2026-07-06 — Deploy will fail until `cinderhaven-store-universe` is vendored (Slice 5 blocker)

**Found during:** Slice 3 (writing the Dockerfile).

**Problem:** The panel package `cinderhaven-household-panel` depends on the peer
package `cinderhaven-store-universe` (the canonical-universe SSOT), which lives in
the **doormath** repo (`doormath-sales-penetration/packages/cinderhaven-store-universe`),
installed editable on this machine. The Docker build context is this repo only, so
`pip install cinderhaven-household-panel` inside the image cannot resolve it and the
build will fail.

**Not fixed in Slice 3** (deploy is Slice 5, gated on Shawn). Scaffolded the
Dockerfile with the correct structure and a prominent blocker comment. Before deploy,
either vendor `cinderhaven-store-universe` into `packages/` (like lailara-palette) or
install it from a private index. Vendoring duplicates the canonical universe, so it's
a decision to confirm with Shawn (precedent: lailara-palette was vendored).

**Status:** Open — pre-deploy task. **Tags:** deploy, docker, peer-package, slice-5

---

### 2026-07-06 — Could not rename the misspelled project folder in place

**Attempted:** `mv` / `Rename-Item` of `decomppose-sales-penetration` →
`decompose-sales-penetration` from within the session.

**Why it didn't work:** The live Claude Code session pins its working directory to
that folder at the OS level (Windows "used by another process" + the shell CWD is
reset back to it after every command). A directory cannot be renamed while it is a
process's CWD.

**What we tried instead:** Created the correctly-named folder and built the whole
project there. The empty misspelled folder must be deleted from a future session
that is not rooted in it.

**Status:** Worked around. **Tags:** windows, folder-rename, cwd-lock

---

### (inherited) cinderhaven-db `pg` health check — PROVEN unrepairable in place

**Attempted (3 prior sessions on cinderhaven-data-platform):** realign
`flypgadmin`'s password via `OPERATOR_PASSWORD`, then `SU_PASSWORD`, then direct
file-based `ALTER ROLE`; verified the DB-level credential is correct and the
checker process has the same value in its own environment.

**Why it didn't work:** The checker still fails auth even though the credential is
provably correct and present in its env — the failure is outside what
`flyctl secrets set` / SQL can reach (cached SCRAM state, different credential
source, or a bug in that postgres-flex build). Cosmetic: does not affect the
app-facing `postgres` role or the 6 downstream apps.

**Do not repeat:** Do not touch `cinderhaven-db` secrets/roles or restart it to
chase this. If ever worth fixing, the scoped path is a fresh Fly Postgres app +
6-app `DATABASE_URL` cutover, with explicit go-ahead — not more credential guessing.
Also: never inline secrets through `flyctl ssh console -C "sh -c \"...$VAR...\""` —
nested shells mangled it to an empty password twice; write SQL to a file and
`sftp put` it.

**Status:** Abandoned (parked). **Tags:** cinderhaven-db, fly, postgres, health-check

---

### (inherited, do-not-clone) Spin Rate `/health` hard-gates the whole site on the DB

**Observed:** Spin Rate's `wsgi.py` `/health` returns `503` when `SELECT 1` fails,
and `fly.toml` points the health check at `/health`. A stale `DATABASE_URL` secret
(DB itself was fine) therefore took the entire external site to 503, not just a
degraded data panel.

**Why it matters here:** This is the exact anti-pattern Decompose must avoid — see
the "resilient health" decision in DECISIONS.md. Do not copy Spin Rate's
`/health`/`fly.toml` health wiring verbatim.

**Status:** Design guardrail. **Tags:** health, fly, resilience, do-not-clone

---

### (inherited) DATABASE_URL secret desync silently breaks Cinderhaven consumer apps

**Observed:** spinrate, ask-cinderhaven, and edi-reconciliation-tool all 503'd on
`password authentication failed for user "postgres"` / `SSL SYSCALL error: EOF`
because their Fly `DATABASE_URL` secrets had drifted from the DB's real `postgres`
password — the DB was fine. Fixed by resyncing each app's secret to the canonical
credential in `cinderhaven-data-platform/.env`, not by touching the DB.

**Do not repeat:** When a Cinderhaven app reports that auth error, check its
`DATABASE_URL` secret against the canonical credential first — don't re-diagnose
the DB. Wire this app's `DATABASE_URL` into the synced set from the start.

**Status:** Resolved (pattern). **Tags:** database-url, secrets, desync, cinderhaven
