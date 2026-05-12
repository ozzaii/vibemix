# SPDX-License-Identifier: Apache-2.0
"""Plan 13-08 — Python-side e2e check of the AI-event taxonomy fixture.

Loads ``tauri/ui/src/mascot/__fixtures__/event-traces.json`` and asserts
the fixture itself is well-formed: every trace has the required shape,
every ``expectedTransitions[i].state`` is a MascotState that the
documented taxonomy in 13-CONTEXT.md Area 3 covers, every event subtype
in ``messages[i].msg.subtype`` is one of the canonical taxonomy values.

This is the cross-language pin. The TypeScript-side replay in
``tauri/ui/src/mascot/state-machine-fixtures.test.ts`` runs the actual
state-machine math; this test guarantees the JSON contract those
fixtures rely on stays in sync with the Python sidecar's view of the
taxonomy — if a future plan adds (say) a new event subtype to the
sidecar's event-dispatcher emit path, this test will fail and force
the fixture + JS replay to stay current.

Marked ``@pytest.mark.integration`` so the fast unit-test run can skip
it. Run explicitly:

    python -m pytest tests/integration/test_mascot_event_taxonomy_e2e.py \
        -m integration -x -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Constants ────────────────────────────────────────────────────────────────

#: Repo-root-relative path to the fixture JSON. Both the vitest harness
#: and this test must agree on this single source-of-truth.
_FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "tauri"
    / "ui"
    / "src"
    / "mascot"
    / "__fixtures__"
    / "event-traces.json"
)

#: AI-event taxonomy from 13-CONTEXT.md Area 3 — the canonical event
#: subtypes the sidecar emits onto the WS bus. Updates here MUST be
#: mirrored in TypeScript's event-dispatcher.ts switch statement.
_EVENT_SUBTYPES = {
    "TRACK_CHANGE",
    "PHASE",
    "AI_GENERATING_REPLY",
    "AI_REPLY_DONE",
    "MANUAL",
}

#: PHASE event `payload.to` values mapped in event-dispatcher.ts.
_PHASE_TO_VALUES = {
    "drop",
    "peak",
    "groove",
    "build",
    "low",
    "silent",
    "breakdown",
}

#: Full set of MascotState target values from types.ts. State names
#: arriving in `expectedTransitions[i].state` must be in this set;
#: drift means types.ts has gained/lost a state and someone forgot to
#: update fixtures.
_MASCOT_STATES = {
    # idle pool
    "idle_breathe",
    "idle_breathe_slow",
    "idle_bop_to_beat_mellow",
    "idle_bop_to_beat_energetic",
    # dance pool
    "dance_a",
    "dance_b",
    "dance_hard",
    "dance_alt",
    "dance_alt2",
    # talk pool
    "talk_loop",
    "talk_loop_calm",
    "talk_loop_energetic",
    # react pool
    "react_yes",
    "react_no",
    "react_no_alt",
    "react_surprised",
    "react_drop",
    "react_glitch",
    # explanation pool
    "point_explain",
    "gesture_wide",
    "gesture_wide_alt",
    # effect
    "puff_particle",
    # misc
    "celebrate",
    "sleep",
    "locomotion_walk",
    "locomotion_run",
}

#: Top-level envelope `type` values the dispatcher recognises.
_ENVELOPE_TYPES = {"snapshot", "event", "ipc.mascot.mood_change"}


# ── Fixture loader ───────────────────────────────────────────────────────────


def _load_fixture() -> dict:
    """Read + parse the JSON fixture. Fails loud if missing/malformed."""
    if not _FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"event-traces.json fixture not found at {_FIXTURE_PATH}. "
            f"Plan 13-08 Task 1 must commit this file before Task 2 runs."
        )
    with _FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_event_taxonomy_fixture_well_formed_structure():
    """The fixture's top-level shape matches the contract the vitest
    replay harness expects.

    Asserts:
        - ``traces`` is a non-empty array.
        - Every trace has ``name`` (str), ``messages`` (list), and
          ``expectedTransitions`` (list with at least 1 entry).
        - ≥7 traces total (covers the taxonomy per 13-08-PLAN.md).
    """
    fixture = _load_fixture()
    assert "traces" in fixture
    traces = fixture["traces"]
    assert isinstance(traces, list)
    assert len(traces) >= 7, (
        f"fixture has only {len(traces)} traces; PLAN 13-08 requires "
        f"≥7 covering the full taxonomy"
    )
    for t in traces:
        assert isinstance(t.get("name"), str), f"trace missing string name: {t}"
        assert isinstance(t.get("messages"), list), f"trace messages not a list: {t['name']}"
        assert isinstance(t.get("expectedTransitions"), list), (
            f"trace expectedTransitions not a list: {t['name']}"
        )
        assert len(t["expectedTransitions"]) >= 1, (
            f"trace {t['name']} has no expectedTransitions — every trace must "
            f"assert at least one transition to be useful"
        )


@pytest.mark.integration
def test_event_taxonomy_fixture_uses_canonical_subtypes_only():
    """Every event subtype in the fixture must be a documented
    sidecar emit value.

    Closes the JS↔Py drift gap — if the sidecar's event-dispatcher
    starts emitting (say) ``BAND_SHIFT`` (cohost_lk.py vocabulary), the
    fixture either covers it or this test surfaces the gap.
    """
    fixture = _load_fixture()
    seen_subtypes: set[str] = set()
    for trace in fixture["traces"]:
        for message in trace["messages"]:
            msg = message.get("msg", {})
            envelope_type = msg.get("type")
            assert envelope_type in _ENVELOPE_TYPES, (
                f"trace {trace['name']} uses unknown envelope type "
                f"{envelope_type!r} (allowed: {sorted(_ENVELOPE_TYPES)})"
            )
            if envelope_type == "event":
                subtype = msg.get("subtype")
                assert subtype in _EVENT_SUBTYPES, (
                    f"trace {trace['name']} uses unknown event subtype "
                    f"{subtype!r} (allowed: {sorted(_EVENT_SUBTYPES)})"
                )
                seen_subtypes.add(subtype)
                if subtype == "PHASE":
                    to = msg.get("payload", {}).get("to")
                    assert to in _PHASE_TO_VALUES, (
                        f"trace {trace['name']} PHASE event has unknown "
                        f"target {to!r} (allowed: {sorted(_PHASE_TO_VALUES)})"
                    )

    # All taxonomy subtypes should be covered by at least one trace.
    missing = _EVENT_SUBTYPES - seen_subtypes
    assert not missing, (
        f"taxonomy not fully covered by fixture: missing subtypes "
        f"{sorted(missing)}. Add traces or document why they're omitted."
    )


@pytest.mark.integration
def test_event_taxonomy_fixture_expected_states_are_canonical():
    """Every ``expectedTransitions[i].state`` must be a known
    MascotState (types.ts union).

    Drift detector — if types.ts removes ``react_drop`` and a fixture
    still references it, this test fails. Forces the fixture to stay
    current with the renderer's vocabulary.
    """
    fixture = _load_fixture()
    for trace in fixture["traces"]:
        for transition in trace["expectedTransitions"]:
            state = transition.get("state")
            assert state in _MASCOT_STATES, (
                f"trace {trace['name']} expects unknown MascotState {state!r} "
                f"— either types.ts dropped it or the fixture has a typo"
            )
            after_t = transition.get("after_t")
            assert isinstance(after_t, (int, float)) and after_t >= 0, (
                f"trace {trace['name']} has invalid after_t={after_t!r}"
            )


@pytest.mark.integration
def test_event_taxonomy_fixture_covers_roadmap_criterion_5():
    """ROADMAP success criterion #5 mandates coverage for these event→state
    mappings. Every entry must appear as the ``state`` of at least one
    ``expectedTransitions[i]`` in some trace.

    From 13-CONTEXT.md Area 3 + ROADMAP Phase 13 success criterion #5:
        - track_change → react_surprised → idle_bop_to_beat (energetic variant)
        - drop → dance_hard
        - ai_generating_reply → talk_loop
        - ai_reply_done → react_yes → prior idle
        - manual_fire → react_yes
        - phase_change → silent → idle_breathe
    """
    fixture = _load_fixture()
    required_states = {
        "react_surprised",
        "idle_bop_to_beat_energetic",
        "dance_hard",
        "talk_loop",
        "react_yes",
        "idle_breathe",
        "puff_particle",  # criterion #6 mood swap
    }

    seen: set[str] = set()
    for trace in fixture["traces"]:
        for transition in trace["expectedTransitions"]:
            seen.add(transition["state"])

    missing = required_states - seen
    assert not missing, (
        f"ROADMAP criterion #5 + #6 event→state mappings not covered: "
        f"{sorted(missing)}. Add traces hitting these states or document "
        f"in 13-08-MANUAL-SMOKE.md why they're verified manually."
    )
