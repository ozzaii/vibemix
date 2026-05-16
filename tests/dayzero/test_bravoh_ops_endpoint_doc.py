"""Tests for `docs/bravoh-ops-endpoint.md` + Phase 36 KAAN-ACTION-LEGAL entries.

Asserts:
1. Bravoh ops endpoint doc exists and covers required surfaces.
2. KAAN-ACTION-LEGAL.md has all 6 Phase 36 entries.
"""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "bravoh-ops-endpoint.md"
KAL = ROOT / ".planning" / "KAAN-ACTION-LEGAL.md"


def test_bravoh_ops_endpoint_doc_present():
    assert DOC.is_file()
    text = DOC.read_text()
    assert "updates/upload" in text
    assert "Bearer" in text
    assert "updates/latest.json" in text
    assert "/vibemix/healthz" in text


def test_kaan_action_legal_has_phase_36_entries():
    text = KAL.read_text()
    for anchor in (
        "OPS-09-RUN",
        "OPS-10-RUN",
        "OPS-11-CRON",
        "OPS-12-OUTREACH",
        "OPS-13-EXECUTE",
        "OPS-14-SERVER",
    ):
        assert anchor in text, f"missing Phase 36 anchor: {anchor}"


def test_bravoh_doc_documents_p46_audit_allowlist():
    text = DOC.read_text()
    assert "P46" in text
    assert "allowlist" in text.lower() or "audit" in text.lower()


def test_bravoh_doc_separates_server_vs_client_ownership():
    text = DOC.read_text()
    assert "Bravoh team" in text
    assert "vibemix repo" in text
