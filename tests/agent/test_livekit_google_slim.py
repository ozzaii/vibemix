# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the slim LiveKit Google import path."""

from __future__ import annotations

import subprocess
import sys


def _run_probe(code: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def test_slim_livekit_google_leaves_do_not_load_cloud_stack() -> None:
    out = _run_probe(
        """
import sys
from vibemix.agent._livekit_google_slim import google_llm_class

LLM = google_llm_class()
from livekit.plugins import google as google_plugin

assert google_plugin.LLM is LLM
assert not [m for m in sys.modules if m.startswith("google.cloud")]
assert not [m for m in sys.modules if m.startswith("grpc")]
assert "livekit.plugins.google.beta" not in sys.modules
assert "livekit.plugins.google.stt" not in sys.modules
assert "livekit.plugins.google.tts" not in sys.modules
print("OK")
"""
    )
    assert out == "OK"


def test_live_factories_do_not_load_cloud_stack() -> None:
    out = _run_probe(
        """
import sys
from vibemix.agent.llm_factory import build_llm
from vibemix.agent.chatterbox_tts import ChatterboxUnavailable
from vibemix.agent.tts_chain import build_tts_chain

build_llm("dummy-key")
try:
    build_tts_chain()
except ChatterboxUnavailable:
    pass

assert not [m for m in sys.modules if m.startswith("google.cloud")]
assert not [m for m in sys.modules if m.startswith("grpc")]
assert "livekit.plugins.google.stt" not in sys.modules
assert "livekit.plugins.google.tts" not in sys.modules
print("OK")
"""
    )
    assert out == "OK"
