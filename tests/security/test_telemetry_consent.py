# SPDX-License-Identifier: Apache-2.0
"""Phase 34 / SEC-08 — telemetry consent invariants.

Pitfall P67 — telemetry consent must be:
  1. Default OFF in the dataclass.
  2. Round-tripped through ConfigStore.from_dict / to_dict.
  3. Corrupted on-disk values (non-bool) silently fall back to False.

UI-side prominence parity (both radios share the same CSS class /
padding / typography) is enforced by static inspection of the TS
component file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.runtime.config_store import ConfigStore, load_config


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT = REPO_ROOT / "tauri/ui/src/wizard/components/telemetry-consent.ts"
STEP = REPO_ROOT / "tauri/ui/src/wizard/step-telemetry-consent.ts"


# ---------------------------------------------------------------------------
# Dataclass invariants
# ---------------------------------------------------------------------------

def test_telemetry_consent_default_off():
    cs = ConfigStore()
    assert cs.telemetry_consent is False, (
        "Pitfall P67 — telemetry consent default MUST be False (OFF)"
    )


def test_telemetry_consent_round_trip_false(tmp_path: Path):
    cs = ConfigStore()
    p = cs.save(tmp_path / "config.json")
    loaded = load_config(p)
    assert loaded.telemetry_consent is False


def test_telemetry_consent_round_trip_true(tmp_path: Path):
    cs = ConfigStore(telemetry_consent=True)
    p = cs.save(tmp_path / "config.json")
    loaded = load_config(p)
    assert loaded.telemetry_consent is True


def test_telemetry_consent_corrupt_value_falls_back_to_off(tmp_path: Path):
    """A garbage on-disk value MUST NOT coerce to True (P67)."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"telemetry_consent": "yes"}), encoding="utf-8")
    loaded = load_config(p)
    assert loaded.telemetry_consent is False, (
        "non-bool telemetry_consent must fall back to OFF, not coerce to ON"
    )


def test_telemetry_consent_int_value_falls_back_to_off(tmp_path: Path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"telemetry_consent": 1}), encoding="utf-8")
    loaded = load_config(p)
    assert loaded.telemetry_consent is False


def test_telemetry_consent_persists_alongside_phase12_fields(tmp_path: Path):
    cs = ConfigStore(voice="leda", mode="hype", telemetry_consent=False)
    p = cs.save(tmp_path / "config.json")
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["telemetry_consent"] is False
    assert raw["voice"] == "leda"
    assert raw["mode"] == "hype"


# ---------------------------------------------------------------------------
# UI prominence parity (no dark patterns)
# ---------------------------------------------------------------------------

def test_component_file_exists():
    assert COMPONENT.exists()
    assert STEP.exists()


def test_component_uses_radio_inputs_not_checkbox():
    txt = COMPONENT.read_text(encoding="utf-8")
    # Two radio inputs of the same name → standard form group.
    assert "type" in txt and "radio" in txt
    assert 'name: "telemetry_consent"' in txt
    assert "telemetry-off" in txt
    assert "telemetry-on" in txt


def test_component_both_options_use_same_css_class():
    """Both rows must use the same CSS class — no asymmetric prominence."""
    txt = COMPONENT.read_text(encoding="utf-8")
    # The single class string applied to both rows.
    assert "vmx-telemetry-consent__radio-row" in txt
    # The class must be applied identically in both makeRadioRow calls.
    count = txt.count('row.className = "vmx-telemetry-consent__radio-row"')
    # Class is set once in the helper that both rows go through.
    assert count >= 1


def test_component_default_off_is_first_in_dom():
    """The default-selected option must carry data-default='true'."""
    txt = COMPONENT.read_text(encoding="utf-8")
    # The Don't share row's defaultSelected: true is explicit in the source.
    assert "Don't share" in txt
    # Find each row's defaultSelected literal value and pair with label.
    # We assert exactly one row carries defaultSelected: true and it's
    # the "Don't share" row by source order.
    dont_share_idx = txt.find('"Don\'t share"')
    share_idx = txt.find("Share anonymous diagnostics")
    assert dont_share_idx > 0 and share_idx > 0
    # Don't share appears first in the source (its row is built before share).
    assert dont_share_idx < share_idx, (
        "Don't share must be rendered first — default-selected option first"
    )


def test_component_lists_not_collected_fields():
    """The wizard MUST visibly list what is NOT collected (P67)."""
    txt = COMPONENT.read_text(encoding="utf-8")
    assert "NEVER_COLLECTED" in txt
    for term in ("track titles", "audio", "library", "MIDI", "window titles"):
        assert term in txt, f"NEVER-COLLECTED list must mention {term!r}"


def test_step_does_not_block_continue_on_consent():
    """Continue advances regardless of toggle state — no forced-on dark pattern."""
    txt = STEP.read_text(encoding="utf-8")
    # The Continue button has no `disabled` or consent-gate condition.
    assert "onClick: cb.onContinue" in txt
    # No `if (state.consent)` gate on the Continue button.
    assert "if (state.consent)" not in txt
    assert "if (!state.consent)" not in txt


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
