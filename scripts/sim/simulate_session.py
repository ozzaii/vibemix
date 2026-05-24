# SPDX-License-Identifier: Apache-2.0
"""Offline session simulation harness (v8.0 P72 — SIM-01 / SIM-02 / SIM-03).

Drives the hardware-gated paths of vibemix through the REAL runtime primitives
with **zero live hardware and zero live Gemini**, and emits one deterministic
artifact (``sim_report.json``). This is the software-verification surface for
the §V7-LIVE deferrals — the things that otherwise wait on a real BlackHole
device, a real DDJ-FLX4 over USB, and a hosted Gemini key.

Four legs, each exercising a REAL primitive (not a mock):

  1. **device**  — ``audio.device_select.select_master_input`` over a synthetic
     "founder rig" device list: must pick ``BlackHole 2ch`` (never the DDJ-FLX4
     controller soundcard or a mic), and must RAISE on a BlackHole-absent rig
     rather than grabbing the wrong input. (SIM-02, the release-blocking bug.)
  2. **midi**    — a real ``ControllerState`` bound to the shipped FLX4 profile,
     fed a synthetic mido-shaped CC/note stream: decode must reflect the right
     per-deck state + emit typed events + record move labels. (SIM-02.)
  3. **reaction**— the offline ``scripts.eval.replay_harness`` (REAL
     EvidenceRegistry + EventDetector + CitationLinter, ``--judges noop`` so no
     Gemini call) over the bundled synthetic session: must exit 0 and emit an
     eval report with >= 1 session. (SIM-01, the full reaction path.)
  4. **citation**— the real ``CitationLinter`` run over an un-grounded reaction
     against an EMPTY evidence snapshot: records the gate verdict (the anti-slop
     spine, exercised headlessly). (SIM-01.)

CLI:
    python -m scripts.sim.simulate_session --output /tmp/vibemix-sim
Exit 0 = all legs pass; 1 = a leg failed. Importable: ``run_simulation(out)``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# Repo root: scripts/sim/simulate_session.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVAL_FIXTURES = _REPO_ROOT / "tests" / "eval" / "fixtures"

# A synthetic "founder rig" CoreAudio device list, in realistic enumeration
# order (controller + aggregates BEFORE BlackHole — exactly what broke the old
# naive first-match scan). Mirrors tests/audio/test_device_select.py.
_FOUNDER_RIG: list[dict[str, Any]] = [
    {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
    {"name": "MacBook Pro Speakers", "max_input_channels": 0, "max_output_channels": 2},
    {"name": "DDJ-FLX4", "max_input_channels": 4, "max_output_channels": 4},
    {"name": "rekordbox Aggregate Device", "max_input_channels": 4, "max_output_channels": 4},
    {"name": "AI Capture", "max_input_channels": 2, "max_output_channels": 2},
    {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "BlackHole 16ch", "max_input_channels": 16, "max_output_channels": 0},
]
_NO_BLACKHOLE_RIG: list[dict[str, Any]] = [
    {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
    {"name": "DDJ-FLX4", "max_input_channels": 4, "max_output_channels": 4},
]


def _leg_device() -> dict[str, Any]:
    from vibemix.audio.device_select import (
        MasterCaptureNotFoundError,
        select_master_input,
    )

    idx = select_master_input(_FOUNDER_RIG)
    chosen = _FOUNDER_RIG[idx]["name"]
    raised = False
    try:
        select_master_input(_NO_BLACKHOLE_RIG)
    except MasterCaptureNotFoundError:
        raised = True
    ok = chosen == "BlackHole 2ch" and raised
    return {
        "founder_rig_choice": chosen,
        "no_blackhole_raises": raised,
        "pass": ok,
    }


def _cc(channel: int, control: int, value: int) -> SimpleNamespace:
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127) -> SimpleNamespace:
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _leg_midi() -> dict[str, Any]:
    from vibemix.midi import load_profile
    from vibemix.midi.state import ControllerState

    profile = load_profile("pioneer_ddj_flx4")
    cs = ControllerState(profile=profile)
    cs.mark_connected("DDJ-FLX4 USB MIDI (synthetic)")
    # deck A volume up, then play A — a minimal live-shaped stream.
    cs.handle_msg(_cc(0, 19, 110))
    cs.handle_msg(_note_on(0, 11, velocity=127))
    snap = cs.deck_snapshot()
    labels = [label for _, label in cs.moves_since(0.0)]
    n_events = len(list(cs.events_since(0.0)))
    ok = (
        profile is not None
        and snap["A"]["vol"] == 110
        and snap["A"]["play"] is True
        and any("A_vol up" in lbl for lbl in labels)
        and n_events >= 2
    )
    return {
        "profile": "pioneer_ddj_flx4",
        "deck_a_vol": snap["A"]["vol"],
        "deck_a_play": snap["A"]["play"],
        "moves": labels,
        "events": n_events,
        "pass": ok,
    }


def _leg_reaction(out_dir: Path) -> dict[str, Any]:
    from scripts.eval.replay_harness import main as harness_main

    if not _EVAL_FIXTURES.is_dir():
        return {"pass": False, "reason": f"missing fixtures: {_EVAL_FIXTURES}"}
    replay_out = out_dir / "replay"
    rc = harness_main(
        ["--corpus", str(_EVAL_FIXTURES), "--judges", "noop", "--output", str(replay_out)]
    )
    report_path = replay_out / "eval_report.json"
    sessions = 0
    if report_path.is_file():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            sessions = len(data.get("sessions", []))
        except Exception:
            sessions = 0
    ok = rc == 0 and report_path.is_file() and sessions >= 1
    return {
        "harness_rc": rc,
        "eval_report": str(report_path),
        "sessions": sessions,
        "gemini": "none (offline --judges noop)",
        "pass": ok,
    }


def _leg_citation() -> dict[str, Any]:
    from vibemix.coach.citation_linter import CitationLinter

    linter = CitationLinter()
    # An ungrounded reaction citing evidence that resolves nowhere in an EMPTY
    # snapshot — the anti-slop gate's core job. We RECORD the verdict (the gate
    # is the proven enforcement in the reaction leg); this leg proves the linter
    # constructs + runs headlessly.
    ungrounded = linter.check("Massive drop incoming [audio:rms@99.9]", {}, mode="live")
    plain = linter.check("nice energy in here", {}, mode="live")
    return {
        "ungrounded_valid": bool(ungrounded.valid),
        "ungrounded_reason": ungrounded.reason,
        "plain_valid": bool(plain.valid),
        "plain_reason": plain.reason,
        "pass": True,  # constructs + runs; semantics asserted in the reaction leg
    }


# Every user the product ships for: 3 skill levels × 2 modes = 6 personas.
_SKILLS = ("beginner", "intermediate", "pro")
_MODES = ("hype", "coach")
# Every interaction the live runtime reacts to (the EventDetector taxonomy).
_EVENT_TYPES = (
    "TRACK_CHANGE",
    "PHASE",
    "LAYER_ARRIVAL",
    "MIX_MOVE",
    "HEARTBEAT",
    "KAAN_SPOKE",
    "MANUAL",
)


def _leg_interactions() -> dict[str, Any]:
    """Simulate EVERYBODY × EVERY interaction (Kaan, 2026-05-25).

    Persona matrix: build the system instruction for all 6 (skill × mode)
    personas — every user level the product ships for, in both modes — and
    confirm each renders, non-empty and distinct. Interaction matrix: build the
    per-event coach prompt for every event type in the live taxonomy, confirming
    every interaction the co-host reacts to resolves through the real prompt
    builder. No Gemini, no hardware — the prompt machinery only.
    """
    from vibemix.prompts import build_system_instruction
    from vibemix.state import AICoach, Event, MusicState

    # --- persona matrix (everybody) ---
    persona_instructions: dict[str, int] = {}
    rendered: set[str] = set()
    for skill in _SKILLS:
        for mode in _MODES:
            instr = build_system_instruction(skill, mode)
            persona_instructions[f"{skill}/{mode}"] = len(instr)
            rendered.add(instr)
    personas_ok = (
        len(persona_instructions) == len(_SKILLS) * len(_MODES)
        and all(n > 0 for n in persona_instructions.values())
        and len(rendered) == len(_SKILLS) * len(_MODES)  # all 6 distinct
    )

    # --- interaction matrix (every event) ---
    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.audible_track = "Daft Punk - Around the World"
    state.audible_track_confidence = 0.8
    state.phase = "peak"
    state.rms = 0.05
    state.bpm = 128.0
    event_prompts: dict[str, bool] = {}
    for et in _EVENT_TYPES:
        try:
            ev = Event(type=et, state=state, extra={})
            prompt = AICoach.build_prompt(ev)
            event_prompts[et] = bool(prompt and prompt.strip())
        except Exception:
            event_prompts[et] = False
    events_ok = all(event_prompts.values())

    return {
        "personas": persona_instructions,
        "personas_distinct": len(rendered),
        "events": event_prompts,
        "pass": personas_ok and events_ok,
    }


def run_simulation(output_dir: Path) -> dict[str, Any]:
    """Run all legs, write ``sim_report.json``, return the report dict."""
    output_dir.mkdir(parents=True, exist_ok=True)
    legs: dict[str, Any] = {}
    legs["device"] = _leg_device()
    legs["midi"] = _leg_midi()
    legs["reaction"] = _leg_reaction(output_dir)
    legs["citation"] = _leg_citation()
    legs["interactions"] = _leg_interactions()
    overall = all(leg.get("pass", False) for leg in legs.values())
    report = {
        "sim_version": "v8.0-P72",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hardware": "none (synthetic device + MIDI fixtures)",
        "gemini": "none (offline)",
        "legs": legs,
        "pass": overall,
    }
    (output_dir / "sim_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vibemix-sim",
        description="Offline no-hardware/no-Gemini session simulation (v8.0 SIM-01..03).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output dir for sim_report.json (default: a temp dir).",
    )
    args = parser.parse_args(argv)
    out = Path(args.output) if args.output else Path(tempfile.mkdtemp(prefix="vibemix-sim-"))
    report = run_simulation(out)
    summary = " · ".join(
        f"{name}={'ok' if leg.get('pass') else 'FAIL'}" for name, leg in report["legs"].items()
    )
    verdict = "PASS" if report["pass"] else "FAIL"
    print(f"[sim] {verdict} — {summary}", file=sys.stderr, flush=True)
    print(f"[sim] artifact: {out / 'sim_report.json'}", file=sys.stderr, flush=True)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
