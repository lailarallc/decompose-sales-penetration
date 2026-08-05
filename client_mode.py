"""Client-mode CLI for Decompose.

Decomposes a client's period-over-period sales change into the three levers —
buying households × purchase frequency × spend per trip — that fully explain it,
reconciling exactly to the sales delta (Shapley), and names the lever to pull.

Grain note: Decompose is a **household-panel** tool, not a store-POS tool. Its
levers are household-level (penetration, trips per buyer, spend per trip), so it
does NOT consume the shared POS scan contract (store_id/week_ending). It reads a
client **panel-transaction** file through the same ``lailara_engagement`` scaffold
(tolerant intake + preflight + provenance) with a panel-specific schema, and
reuses the tested Shapley engine in ``app/decomposition.py`` unchanged.

Required input: **transactions** (household_id, period, spend; optional trip_id
and units). Period metrics are derived, then the two periods named in config
(``basis.period_a`` / ``basis.period_b``) are bridged. A missing required column
blocks with a branded Data Readiness Report; a clean run writes a
draft-watermarked, provenance-footed **Three-Lever Decomposition** (HTML) to
``client-output/`` only.

Usage:
    python client_mode.py --config engagement.yml [--out client-output] [--final]
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import pandas as pd

from app.decomposition import Waterfall, _shapley_three_factor, which_lever_verdict
from lailara_engagement import (
    ColumnSpec,
    PreflightSpec,
    build_provenance,
    load_config,
    read_table,
    run_preflight,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.pos import to_frame
from lailara_engagement.provenance import Provenance

TOOL = "decompose"
TOOL_VERSION = "1.0"


def _transactions_spec() -> PreflightSpec:
    return PreflightSpec(tool=TOOL, version=TOOL_VERSION, columns=[
        ColumnSpec(name="household_id", dtype="identifier", required=True,
                   description="panel household id", spec_ref="INPUT-SPEC §Transactions"),
        ColumnSpec(name="period", dtype="string", required=True,
                   description="period label the trip falls in (e.g. 2025-Q2)",
                   spec_ref="INPUT-SPEC §Transactions"),
        ColumnSpec(name="spend", dtype="number", required=True, not_negative=True,
                   description="dollars spent on the brand in the trip", spec_ref="INPUT-SPEC §Transactions"),
        ColumnSpec(name="trip_id", dtype="identifier", required=False, allow_blank=True,
                   description="trip id; if absent, each row is one trip", spec_ref="INPUT-SPEC §Transactions"),
        ColumnSpec(name="units", dtype="number", required=False, allow_blank=True, not_negative=True,
                   description="units bought", spec_ref="INPUT-SPEC §Transactions"),
    ])


def period_metrics(tx: pd.DataFrame) -> pd.DataFrame:
    """Per-period buying_households, frequency (trips/buyer), spend_per_trip.

    Sales = buying_households × frequency × spend_per_trip == total spend, by
    construction — the identity the waterfall reconciles to.
    """
    has_trip = "trip_id" in tx.columns and tx["trip_id"].astype(str).str.strip().ne("").any()
    rows = []
    for period, g in tx.groupby("period"):
        bh = g["household_id"].nunique()
        if has_trip:
            trips = g[["household_id", "trip_id"]].drop_duplicates().shape[0]
        else:
            trips = len(g)                       # each row is a trip
        spend = float(g["spend"].sum())
        if bh == 0 or trips == 0:
            continue
        rows.append({"period": str(period), "buying_households": float(bh),
                     "frequency": trips / bh, "spend_per_trip": spend / trips,
                     "sales": spend})
    return pd.DataFrame(rows).set_index("period")


def build_waterfall(metrics: pd.DataFrame, period_a: str, period_b: str) -> Waterfall:
    if period_a not in metrics.index or period_b not in metrics.index:
        raise SystemExit(f"period(s) not in data: {period_a!r}, {period_b!r}. "
                         f"available: {list(metrics.index)}")
    a, b = metrics.loc[period_a], metrics.loc[period_b]
    phi_h, phi_f, phi_s = _shapley_three_factor(
        a["buying_households"], a["frequency"], a["spend_per_trip"],
        b["buying_households"], b["frequency"], b["spend_per_trip"])
    return Waterfall(period_a=period_a, period_b=period_b,
                     sales_a=float(a["sales"]), sales_b=float(b["sales"]),
                     delta=float(b["sales"] - a["sales"]),
                     contributions={"buying_households": float(phi_h),
                                    "frequency": float(phi_f), "spend_per_trip": float(phi_s)})


def _fmt_dollars(v):
    return ("-" if v < 0 else "") + f"${abs(v):,.0f}"


_LEVER_LABEL = {"buying_households": "Buying households", "frequency": "Purchase frequency",
                "spend_per_trip": "Spend per trip"}


def _deliverable_html(config, wf: Waterfall, verdict, provenance: Provenance,
                      limitations, *, draft: bool) -> str:
    esc = html.escape
    draft_class = " ll-draft" if draft else ""
    rows = "".join(
        f"<tr><td>{esc(_LEVER_LABEL[k])}</td><td class=num>{_fmt_dollars(v)}</td>"
        f"<td class=num>{verdict['shares'][k]*100:.1f}%</td></tr>"
        for k, v in wf.contributions.items()
    )
    lim = "".join(f"<li>{esc(x)}</li>" for x in limitations)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Three-Lever Decomposition — {esc(config.client_name)}</title><style>{_css(draft)}</style></head>
<body class="{draft_class.strip()}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Decompose</div>
  <h1 class=ll-title>Three-Lever Decomposition</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>Periods</span> {esc(wf.period_a)} → {esc(wf.period_b)}</div>
    <div><span class=ll-k>Prepared by</span> {esc(config.prepared_by)}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{esc(verdict['sentence'])}</div>
  <div>Sales {esc(wf.period_a)} {_fmt_dollars(wf.sales_a)} → {esc(wf.period_b)} {_fmt_dollars(wf.sales_b)}
       · delta {_fmt_dollars(wf.delta)}</div>
  <div class=ll-basis>Basis: exact Shapley attribution — the three levers sum to the
       sales delta ({_fmt_dollars(sum(wf.contributions.values()))} ≈ {_fmt_dollars(wf.delta)}).
       Household-panel grain (penetration × frequency × spend/trip).</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Lever contributions</h2>
  <table class=ll-table><thead><tr><th>Lever</th><th>Contribution to Δ</th>
  <th>Share of gross movement</th></tr></thead><tbody>{rows}</tbody></table>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Data limitations</h2>
  <ul class=ll-limitations>{lim}</ul>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}
*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_CHICAGO_SURFACE};color:{P.LL_CHICAGO}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:20px}}
.ll-basis{{font-size:12px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-limitations{{margin:0;padding-left:20px}}.ll-limitations li{{margin-bottom:6px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def run(config_path: str, out_dir: str, args, *, final: bool = False) -> dict:
    config = load_config(config_path)
    ci = config.raw.get("inputs") or {}
    tx_path = args.transactions or ci.get("transactions")
    if not tx_path:
        raise SystemExit("missing required input: transactions.")
    basis = config.basis or {}
    period_a, period_b = args.period_a or basis.get("period_a"), args.period_b or basis.get("period_b")

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    spec = _transactions_spec()
    read = read_table(tx_path)
    report = run_preflight(read, spec, config)
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[read], config=config,
        validation_status=validation_status_label(report.status, report.n_warnings),
        extra={"Grain": "household panel (not store POS)"})
    if not report.passed:
        p = write_report(report, config, str(out), provenance=provenance, draft=not final,
                         basename="data-readiness-transactions",
                         title="Decompose Data Readiness Report")
        return {"status": "blocked", "readiness_report": p["html"]}

    tx = to_frame(read, report, spec)
    metrics = period_metrics(tx)
    if period_a is None or period_b is None:
        periods = list(metrics.index)
        if len(periods) < 2:
            raise SystemExit("need at least two periods; set basis.period_a / basis.period_b.")
        period_a, period_b = periods[0], periods[-1]
    wf = build_waterfall(metrics, str(period_a), str(period_b))
    verdict = which_lever_verdict(wf)

    limitations = [f"[transactions] {f.message}" for f in report.findings if f.severity == "warning"]
    if not limitations:
        limitations.append("No warnings — the transaction file passed preflight cleanly.")

    csv_path = out / "period-metrics.csv"
    metrics.reset_index().to_csv(csv_path, index=False)
    html_path = out / "three-lever-decomposition.html"
    html_path.write_text(_deliverable_html(config, wf, verdict, provenance, limitations, draft=not final),
                         encoding="utf-8")
    return {"status": "ok", "delta": round(wf.delta, 2), "reconciles": wf.reconciles,
            "headline_lever": verdict["headline_lever"], "report": str(html_path),
            "metrics_csv": str(csv_path), "n_warnings": report.n_warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="decompose client mode")
    ap.add_argument("--config", required=True)
    ap.add_argument("--transactions"); ap.add_argument("--period-a", dest="period_a")
    ap.add_argument("--period-b", dest="period_b")
    ap.add_argument("--out", default="client-output"); ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.out, args, final=args.final)
    if result["status"] == "blocked":
        print(f"BLOCKED — data not ready. See {result['readiness_report']}")
        return 3
    print(f"delta {_fmt_dollars(result['delta'])} · reconciles={result['reconciles']} · "
          f"lever={result['headline_lever']}")
    print(f"report -> {result['report']}\ncsv    -> {result['metrics_csv']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
