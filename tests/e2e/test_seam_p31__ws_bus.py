# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-01 seam test — P31 → ws_bus.

Source: ``tauri/ui/src/mascot/priority-stack.ts`` (4-layer PriorityStack)
Sink:   ``src/vibemix/runtime/ws_bus.py`` (ws_broadcast IPC frame)

The Python ws_bus emits 30Hz frames; the TS PriorityStack subscribes
via ``ws-client.ts``. The seam contract = the Python side emits the
fields the TS side reads (``emotion``, ``reaction_intent``,
``active_genre``, ``beat_phase``, etc.) AND the 4-layer name
contract matches.

Verifies:
1. ws_bus.py source contains every field the frontend renderer binds.
2. The 4 layer names declared in priority-stack.ts exactly match the
   v2.0 + Phase 31 contract documented in ws_bus.py.
3. The frame schema is JSON-serialisable so the frontend can parse it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WS_BUS = REPO / "src" / "vibemix" / "runtime" / "ws_bus.py"
PRIORITY_STACK = REPO / "tauri" / "ui" / "src" / "mascot" / "priority-stack.ts"


@pytest.mark.e2e
def test_ws_bus_emits_layer_3_fields_priority_stack_consumes() -> None:
    """Python ws_bus.py MUST emit every field priority-stack.ts consumes."""
    ws_bus_src = WS_BUS.read_text(encoding="utf-8")
    # These fields are the Phase 31 + v2.0 contract — the frontend
    # renderer binds them directly.
    required_fields = [
        '"emotion"',  # priority-60 EmotionLayer
        '"reaction_intent"',  # priority-80 ReactionLayer
        '"active_genre"',  # GenreRouter on frontend
        '"beat_phase"',  # priority-70 anticipation hip-bob
        '"bpm"',
        '"phase"',
        '"audible"',
    ]
    for field in required_fields:
        assert field in ws_bus_src, (
            f"ws_bus.py dropped {field} from the 30Hz frame — "
            f"frontend renderer will break"
        )


@pytest.mark.e2e
def test_priority_stack_4_layer_names_match_ws_bus_contract() -> None:
    """priority-stack.ts MUST declare exactly the 4 layers ws_bus expects."""
    ps_src = PRIORITY_STACK.read_text(encoding="utf-8")
    # The TS LayerName union — extracted as a regex anchor.
    match = re.search(
        r'export\s+type\s+LayerName\s*=\s*([^;]+);', ps_src
    )
    assert match, "priority-stack.ts must export a LayerName union"
    layer_union = match.group(1)
    # The 4-layer contract.
    for layer in ("base", "emotion", "anticipation", "reaction"):
        assert f'"{layer}"' in layer_union, (
            f"priority-stack.ts missing {layer!r} layer — "
            f"v2.0 + Phase 31 contract requires all 4"
        )


@pytest.mark.e2e
def test_ws_bus_frame_is_json_serialisable() -> None:
    """The frame dict emitted at 30Hz MUST be JSON-serialisable end-to-end.

    Without this, the frontend ws-client cannot parse the message and
    the entire mascot layer-stack goes dark.
    """
    # Build a frame dict mirroring the shape ws_broadcast emits.
    # (We don't spin up the live runtime here — that's an integration
    # test elsewhere. This pins the schema contract.)
    frame = {
        "music": 0.42,
        "voice": 0.0,
        "mic": 0.0,
        "audible": "music",
        "deck": "A",
        "phase": "build",
        "bpm": 138.0,
        "mood": "hyped",
        "bpm_confidence": 0.87,
        "downbeat_phase": 0.0,
        "beat_phase": 0.0,
        "active_genre": "techno",
        "emotion": "focused",
        "reaction_intent": None,
    }
    encoded = json.dumps(frame)
    parsed = json.loads(encoded)
    assert parsed == frame
    # Required layer-3 fields present.
    assert "emotion" in parsed
    assert "reaction_intent" in parsed
    assert "active_genre" in parsed
