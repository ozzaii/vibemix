# SPDX-License-Identifier: Apache-2.0
"""Plan 42-06 Task 3 — privacy contract test for eval/README.md (GATE-09).

Per memory ``feedback_privacy_scope_narrow``: ear-test log files live in the
repo as audit trail (single-DJ regime — Kaan owns the repo, gate reviewers
need verifiable evidence the gate fired on real signed sessions). But the
textual content of those logs — free_form notes, specific session_ids,
signed_at timestamps — MUST NOT appear in eval/README.md, which is
public-facing.

This test enforces that asymmetry as a hard contract:
    - structured logs stay in repo
    - their textual content does NOT leak into public docs
    - the README itself self-documents the redaction principle

If no ear-test logs exist yet (Kaan hasn't discharged §GATE-05), the leakage
tests skip cleanly — the contract still holds, there's just nothing to leak
yet. Future log files will trigger the leakage check on every CI run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "eval" / "README.md"
LOGS_DIR = REPO_ROOT / "eval" / "ear-test-logs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_log_payloads() -> list[tuple[Path, dict]]:
    """Load every ear-test log JSON file (excluding schema.json).

    Returns ``[(path, payload), ...]``. Empty list if dir absent or holds
    only the schema.
    """
    if not LOGS_DIR.is_dir():
        return []
    out: list[tuple[Path, dict]] = []
    for json_path in sorted(LOGS_DIR.glob("*.json")):
        if json_path.name == "schema.json":
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Malformed log files are someone else's problem (schema test
            # catches that); skip here so privacy test stays focused.
            continue
        if isinstance(payload, dict):
            out.append((json_path, payload))
    return out


def _extract_free_form_chunks(payload: dict, *, min_chars: int = 10) -> list[str]:
    """Return free_form substrings ≥ min_chars (whole phrases, not single words).

    Splits on whitespace so individual common words like "good" don't trigger
    false positives. Whole phrases ≥ min_chars chars are the load-bearing
    contract surface — a public README containing such a phrase verbatim from
    a private log is a leak.
    """
    raw = payload.get("free_form", "")
    if not isinstance(raw, str):
        return []
    # Coarse-grained chunks: split on common sentence boundaries, keep
    # substrings that are at least min_chars long.
    chunks: list[str] = []
    for chunk in raw.replace("\n", ". ").split(". "):
        normalized = chunk.strip()
        if len(normalized) >= min_chars:
            chunks.append(normalized)
    return chunks


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def log_payloads() -> list[tuple[Path, dict]]:
    return _load_log_payloads()


# ---------------------------------------------------------------------------
# Leakage contract — free_form, session_id, signed_at
# ---------------------------------------------------------------------------


def test_no_free_form_text_in_readme(
    readme_text: str, log_payloads: list[tuple[Path, dict]]
):
    """Every free_form chunk ≥ 10 chars from every log file must be absent from README."""
    if not log_payloads:
        pytest.skip(
            "no ear-test logs to redact yet — discharge §GATE-05 first to populate "
            "eval/ear-test-logs/. Future logs will trigger this leakage check on every PR."
        )
    leaks: list[str] = []
    for path, payload in log_payloads:
        for chunk in _extract_free_form_chunks(payload):
            if chunk in readme_text:
                leaks.append(f"{path.name}: {chunk!r}")
    assert not leaks, (
        "private ear-test log free_form content leaked into public eval/README.md:\n"
        + "\n".join(leaks)
    )


def test_no_session_id_specific_anecdotes_in_readme(
    readme_text: str, log_payloads: list[tuple[Path, dict]]
):
    """session_id is structured but identifies a specific Kaan-DJ-session — stays private."""
    if not log_payloads:
        pytest.skip("no ear-test logs to check session_id leakage against yet")
    leaks: list[str] = []
    for path, payload in log_payloads:
        sid = payload.get("session_id")
        if isinstance(sid, str) and sid and sid in readme_text:
            leaks.append(f"{path.name}: session_id={sid!r}")
    assert not leaks, (
        "private session_id leaked into public eval/README.md:\n" + "\n".join(leaks)
    )


def test_no_signed_at_timestamps_in_readme(
    readme_text: str, log_payloads: list[tuple[Path, dict]]
):
    """Full ISO8601 signed_at strings identify when Kaan signed off a specific session."""
    if not log_payloads:
        pytest.skip("no ear-test logs to check signed_at leakage against yet")
    leaks: list[str] = []
    for path, payload in log_payloads:
        signed_at = payload.get("signed_at")
        if isinstance(signed_at, str) and signed_at and signed_at in readme_text:
            leaks.append(f"{path.name}: signed_at={signed_at!r}")
    assert not leaks, (
        "private signed_at timestamp leaked into public eval/README.md:\n"
        + "\n".join(leaks)
    )


# ---------------------------------------------------------------------------
# Positive assertions — policy is self-documented + schema excluded
# ---------------------------------------------------------------------------


def test_readme_does_document_redaction_explicitly(readme_text: str):
    """Positive contract: README must self-describe the redaction principle.

    Re-verifies (independent of public-facing test) the policy itself is
    stated in the doc, not just enforced by tests.
    """
    lowered = readme_text.lower()
    assert "ear-test" in lowered, "missing 'ear-test' reference"
    assert ("redact" in lowered) or ("redacted" in readme_text), (
        "missing 'redact' / 'REDACTED' policy statement"
    )
    assert "audit trail" in lowered, "missing 'audit trail' rationale phrase"


def test_schema_json_excluded_from_log_iteration():
    """Sanity: schema.json exists but the loader correctly skips it.

    schema.json is the contract document, not a log entry — it must never be
    treated as a payload to scan for free_form leakage.
    """
    schema_path = LOGS_DIR / "schema.json"
    assert schema_path.is_file(), "ear-test-logs/schema.json missing (Plan 42-03 dep)"
    payloads = _load_log_payloads()
    payload_paths = {p.name for p, _ in payloads}
    assert "schema.json" not in payload_paths, (
        "schema.json was iterated as a log file — loader bug"
    )
