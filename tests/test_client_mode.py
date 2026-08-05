"""Client-mode tests for Decompose (checklist §6).

Skipped unless the shared ``lailara_engagement`` lib is installed. The fixture is
tuned to reproduce the engine golden (period A 100hh×2.0×$10 = $2,000; period B
120hh×2.2×$10.5 = $2,772; delta $772, buying-households dominant).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("lailara_engagement")

import client_mode  # noqa: E402


def _transactions():
    rows = []
    # Period A: 100 households × 2 trips × $10.
    for h in range(100):
        for k in range(2):
            rows.append((f"H{h:03d}", "2025-Q1", f"A-{h}-{k}", 10.0, 1))
    # Period B: 264 trips over 120 households (24 with 3 trips, 96 with 2) × $10.50.
    for h in range(120):
        n = 3 if h < 24 else 2
        for k in range(n):
            rows.append((f"H{h:03d}", "2025-Q2", f"B-{h}-{k}", 10.5, 1))
    return pd.DataFrame(rows, columns=["household_id", "period", "trip_id", "spend", "units"])


def _write(d: Path, tx=None):
    tx = tx if tx is not None else _transactions()
    p = d / "transactions.csv"; tx.to_csv(p, index=False)
    return p


def _cfg(d: Path, period_a="2025-Q1", period_b="2025-Q2"):
    import yaml
    p = d / "engagement.demo.yml"
    p.write_text(yaml.safe_dump({
        "client": {"name": "Cinderhaven Provisions (demo)"}, "engagement": {"id": "T-1"},
        "as_of_date": "2025-12-27", "demo": True,
        "basis": {"period_a": period_a, "period_b": period_b}}), encoding="utf-8")
    return p


def _args(transactions=None, period_a=None, period_b=None):
    return SimpleNamespace(transactions=transactions, period_a=period_a, period_b=period_b)


def test_clean_run_reproduces_the_golden_decomposition(tmp_path):
    tp = _write(tmp_path)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(tp)))
    assert res["status"] == "ok"
    assert res["delta"] == 772.00
    assert res["reconciles"] is True
    assert res["headline_lever"] == "buying_households"
    assert Path(res["report"]).is_file() and Path(res["metrics_csv"]).is_file()


def test_deliverable_shows_verdict_and_reconciliation(tmp_path):
    tp = _write(tmp_path)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(tp)))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "more households buying the brand" in html
    assert "exact Shapley attribution" in html
    assert "household panel (not store POS)" in html   # provenance grain note
    assert "DRAFT" in html


def test_missing_spend_column_blocks(tmp_path):
    tp = _write(tmp_path)
    pd.read_csv(tp).drop(columns=["spend"]).to_csv(tp, index=False)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(tp)))
    assert res["status"] == "blocked"
    assert "spend" in Path(res["readiness_report"]).read_text(encoding="utf-8")


def test_unknown_period_errors(tmp_path):
    tp = _write(tmp_path)
    cfg = _cfg(tmp_path, period_b="2099-Q9")
    with pytest.raises(SystemExit):
        client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(tp)))
