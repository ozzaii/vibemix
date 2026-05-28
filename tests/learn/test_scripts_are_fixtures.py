# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — TONE-02 binding.

The lesson scripts are HAND-AUTHORED JSON fixtures; no live generative
call may write a ``tutor_speak[].text`` field at runtime. The AI tutor
adds only ONE grounded interjection per beat — citations only, never
the text body. This static gate AST-greps the ``learn/`` package for
any line that looks like a generative API call (``generate_content``,
``models.generate``, ``create_message``) coexisting with a
``tutor_speak`` / ``.text`` reference on the same line.

The ≥20-token runtime blocklist ships in Plan 94's
``scripts/launch/check_no_tutor_slop.py`` — this file pins the
*source-code-side* fixture lock so generative writes can't sneak in
between fixture-author and Plan-94 runtime check.

REQ-ID: TONE-02.

Sampling: per-task commit (~10 ms — file walk + substring scan).

The test is LIVE day-one — currently passes because no LLM-write paths
exist in ``learn/`` (the only file there is Plan 91-03's read-only
``midi_mirror.py``). Stays green as Plans 92-03..05 add tutor wiring.
"""
from __future__ import annotations

import pathlib


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent


LEARN_DIR = _repo_root() / "src" / "vibemix" / "learn"


# Tokens that indicate a generative API call. If any of these appears
# on the SAME line as ``tutor_speak`` or ``.text`` (i.e., the call's
# return value is being routed into the tutor-speak text body), the
# gate flags it.
_GENERATIVE_CALL_TOKENS: tuple[str, ...] = (
    "generate_content",  # google.genai
    "models.generate",   # google.genai client.aio.models.generate_content
    "create_message",    # alt SDKs (anthropic, openai)
)


def _walk_python_files(root: pathlib.Path):
    if not root.exists():
        return
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def test_no_generative_writes_to_tutor_speak_text() -> None:
    """Grep ``src/vibemix/learn/**/*.py`` for any line that combines a
    generative-call token with a ``tutor_speak`` or ``.text`` reference.

    Currently passes trivially (no generative calls in ``learn/`` yet).
    After Plan 92-03 wires the tutor, the JSON-fixture path is the
    sole source of ``tutor_speak[].text`` content — any direct LLM
    write trips this gate red.
    """
    offenders: list[str] = []
    for path in _walk_python_files(LEARN_DIR):
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            for tok in _GENERATIVE_CALL_TOKENS:
                if tok in line and (
                    "tutor_speak" in line or ".text" in line
                ):
                    offenders.append(f"{path}:{line_no}: {line.strip()}")

    assert not offenders, (
        "TONE-02 violation — live generative writes to "
        "tutor_speak.text. The 36 lesson scripts are hand-authored JSON "
        "fixtures; the AI adds citations only, never text.\n"
        + "\n".join(offenders)
    )
