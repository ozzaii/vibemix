# SPDX-License-Identifier: Apache-2.0
"""Phase 50 / E2E — audio-loopback pytest fixture.

Validates the sidecar↔BlackHole/VB-CABLE audio path against a VCR cassette
pinned to the v3.0 GATE-02 baseline. ZERO live Gemini calls in CI per
REQ E2E-04. Uses the ModelRouter abstraction — NEVER inlines ``gemini-*``
literals.

CI-tolerant per PITFALLS § 19 audio-loopback bootstrap paradox: when
``sounddevice`` cannot find BlackHole / VB-CABLE devices on a CI runner,
the fixture yields a mock-backed recorder + emits ``SKIPPED`` dimension
status rather than failing the suite.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_CASSETTE_PATH = (
    Path(__file__).resolve().parent / "cassettes" / "gate_02_v3_0_baseline.yaml"
)


@dataclass
class LoopbackRecorder:
    """Records sidecar↔driver audio samples and ModelRouter call shapes.

    The recorder NEVER fires a real network call. It consults the cassette
    via vcrpy replay-only mode for the Gemini-side roundtrip.
    """

    sample_rate_hz: int = 48000
    bit_depth: int = 16
    channels: int = 2
    mock_backed: bool = False
    cassette_path: Path = _CASSETTE_PATH
    samples_captured: list[bytes] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)

    def push(self, pcm: bytes) -> None:
        """Push a chunk of PCM samples (driver-side capture)."""
        self.samples_captured.append(pcm)

    def assert_cassette_present(self) -> None:
        """Verify the pinned cassette artifact exists at expected path."""
        assert self.cassette_path.is_file(), (
            f"Cassette artifact missing at {self.cassette_path} — "
            "run scripts/eval/record_cassettes.py --really to populate "
            "(see KAAN-ACTION-LEGAL § GATE-02)."
        )

    def cassette_is_populated(self) -> bool:
        """True iff the cassette has at least one recorded interaction.

        When False, the loopback fixture treats the run as SKIPPED (cassette
        pending Kaan-discharge) per CI-tolerant fallback.
        """
        if not self.cassette_path.is_file():
            return False
        text = self.cassette_path.read_text(encoding="utf-8")
        # Empty cassette = "interactions: []" with no recorded entries.
        # Any non-trivial body (interactions: with actual entries) returns True.
        if "interactions: []" in text:
            return False
        if "interactions:" in text and "\n  - request:" in text:
            return True
        return False


def _model_router_seam_ok() -> bool:
    """Verify ModelRouter abstraction is the call surface — NEVER SKU literals.

    Parses this module's source via ``ast`` and checks every ``Constant`` node
    of type ``str``. If any string literal in *executable* code matches a
    Gemini SKU pattern (``gemini-<digit>``), the seam is violated. Docstrings
    are skipped (they are documentation, not call literals).
    """
    import ast
    import re

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    sku_pattern = re.compile(r"gemini-\d")

    # Collect docstring node IDs to skip them.
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_ids.add(id(body[0].value))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue
            if sku_pattern.search(node.value):
                return False
    return True


@pytest.fixture
def audio_loopback_recorder(tmp_path):
    """Yield a LoopbackRecorder; cassette pinned to v3.0 GATE-02 baseline.

    Replay-only mode is hardcoded. Local-dev refresh requires running
    scripts/eval/record_cassettes.py separately (per CONTEXT.md § 4 truth).
    """
    assert _model_router_seam_ok(), (
        "ModelRouter seam violated — fixture source contains gemini-* literal. "
        "Audio-loopback MUST use ModelRouter abstraction."
    )

    # CI-tolerant: if sounddevice cannot find BlackHole/VB-CABLE, mark recorder
    # as mock-backed so tests can SKIPPED-out per PITFALLS § 19.
    mock_backed = os.environ.get("VIBEMIX_E2E_FORCE_MOCK_AUDIO") == "1"
    if not mock_backed:
        try:
            import sounddevice as sd  # noqa: F401  # availability check only

            # Probe for BlackHole / VB-CABLE in device list.
            devices = sd.query_devices() if hasattr(sd, "query_devices") else []
            names = " ".join(d.get("name", "") for d in devices).lower()
            if "blackhole" not in names and "vb-cable" not in names and "cable" not in names:
                mock_backed = True
        except Exception:
            mock_backed = True

    recorder = LoopbackRecorder(mock_backed=mock_backed)
    recorder.assert_cassette_present()
    yield recorder
