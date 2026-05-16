# SPDX-License-Identifier: Apache-2.0
"""Plan 29-00 Task 1 — capability allowlist regex + windows list extension.

Loads `tauri/src-tauri/capabilities/default.json`, extracts the
`shell:allow-execute` permission for `binaries/vibemix-core`, and verifies:
  (a) the first args validator accepts `--debrief` (and still accepts
      `--wizard` and `--session` — no v2.0 regression).
  (b) a second args entry exists whose validator matches canonical session
      directory names of the form `YYYYMMDD-HHMMSS`.
  (c) the `windows` array includes `"debrief"` so the new WebviewWindow
      label is in capability scope.
  (d) the validator rejects unknown flags (e.g. `--malicious`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CAPABILITY_PATH = (
    Path(__file__).resolve().parents[2]
    / "tauri"
    / "src-tauri"
    / "capabilities"
    / "default.json"
)


def _load_capability() -> dict:
    return json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))


def _find_sidecar_args(cap: dict) -> list[dict]:
    """Return the args list for `binaries/vibemix-core` under shell:allow-execute."""
    for perm in cap.get("permissions", []):
        if not isinstance(perm, dict):
            continue
        if perm.get("identifier") != "shell:allow-execute":
            continue
        for allow in perm.get("allow", []):
            if allow.get("name") == "binaries/vibemix-core":
                args = allow.get("args")
                assert isinstance(args, list), "args must be a list"
                return args
    raise AssertionError("binaries/vibemix-core sidecar permission not found")


def test_debrief_flag_matches_validator():
    cap = _load_capability()
    args = _find_sidecar_args(cap)
    validator = args[0]["validator"]
    assert re.fullmatch(validator, "--debrief"), (
        f"validator {validator!r} should match '--debrief'"
    )


def test_session_dir_validator_present():
    cap = _load_capability()
    args = _find_sidecar_args(cap)
    assert len(args) >= 2, (
        "expected a second args entry for the session-dir positional"
    )
    validator = args[1]["validator"]
    # Canonical session-dir form: YYYYMMDD-HHMMSS
    assert re.fullmatch(validator, "20260515-112139"), (
        f"validator {validator!r} should match '20260515-112139'"
    )


def test_malicious_arg_not_matched():
    cap = _load_capability()
    args = _find_sidecar_args(cap)
    validator = args[0]["validator"]
    assert re.fullmatch(validator, "--malicious") is None, (
        f"validator {validator!r} should NOT match '--malicious'"
    )


def test_windows_array_includes_debrief():
    cap = _load_capability()
    windows = cap.get("windows", [])
    assert "debrief" in windows, (
        f"windows array should include 'debrief', got {windows!r}"
    )


def test_wizard_and_session_still_match():
    """No regression for v2.0 callers — --wizard and --session still pass."""
    cap = _load_capability()
    args = _find_sidecar_args(cap)
    validator = args[0]["validator"]
    assert re.fullmatch(validator, "--wizard"), "v2.0 regression: --wizard must still match"
    assert re.fullmatch(validator, "--session"), "v2.0 regression: --session must still match"
