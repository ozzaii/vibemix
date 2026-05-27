# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-01 (Wave 0) — raw-in/raw-out no-extraction gate (STORE-02).

The milestone thesis: a memory record carries the RAW text signature + its
embedding + (session_id, ts, kind) — NEVER an LLM-extracted "insight". The
only model-facing seam ``src/vibemix/memory/`` may use is the injected
``embedder.embed_query`` protocol, currently backed by local CLAP in product
paths. Any generation surface (``generate_content`` / ``generate_reply`` /
``.chats.`` / a ``GenerateContentConfig``) in memory/ would re-open the
confabulation surface the whole milestone forbids.

This is a tokenize-stripped STATIC scan. The comment/docstring stripper is
cloned from ``tests/repo/test_repo_scrub.py::_strip_comments_and_docstrings``
so that prose DOCUMENTING the ban (in this very gate's docstrings, or in a
memory/ module's docstring) cannot self-trip the scan — only a real
generation-surface NAME/OP token sequence is flagged.

T-63-02 (Spoofing/confabulation): future memory/ calls a generation model —
mitigated by this gate (the build fails if any generation surface appears).

NOTE: STORE-04's no-hardcoded-model-literal requirement is ALREADY covered by
the shipped ``tests/repo/test_model_literal_gate.py`` (which scans all of
``src/vibemix/`` including the new ``memory/`` package). It is intentionally NOT
duplicated here.

RED-first: ``vibemix.memory`` does not exist yet, so the scan finds no files and
passes vacuously; a positive-control test below proves the stripper+scan WOULD
flag a generation surface, so the gate is not vacuously broken.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MEM = REPO / "src" / "vibemix" / "memory"

# Generation surfaces banned in memory/. The store path may only use the
# injected local embedding protocol — ``generate_content`` == extraction.
FORBIDDEN: tuple[str, ...] = (
    "generate_content",
    "generate_reply",
    ".chats.",
    "GenerateContentConfig",
)


def _strip_comments_and_docstrings(src_text: str) -> str:
    """Return executable source with ALL comments and string literals removed.

    Tokenize-based stripping (cloned from
    ``tests/repo/test_repo_scrub.py::_strip_comments_and_docstrings``): removes
    COMMENT and STRING tokens so prose that *documents* the ban (in a comment
    or docstring) is invisible to the scan, while a real
    ``client.models.generate_content(...)`` statement (a NAME/OP token
    sequence) survives. STRING tokens are replaced with an empty-string literal
    so token POSITIONS keep surrounding-code adjacency — e.g.
    ``models.generate_content(`` stays contiguous, so the substring match
    still fires. Falls back to a line-based ``#`` strip if tokenize fails
    (never silently passes a file).
    """
    try:
        kept: list[tokenize.TokenInfo] = []
        for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                if tok.type == tokenize.STRING:
                    kept.append(tok._replace(string='""'))
                continue
            kept.append(tok)
        return tokenize.untokenize(kept)
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return "\n".join(
            ln for ln in src_text.splitlines() if not ln.lstrip().startswith("#")
        )


def _memory_py_files() -> list[Path]:
    if not MEM.exists():
        return []
    return sorted(MEM.rglob("*.py"))


def test_no_extraction_detector_catches_a_generation_surface() -> None:
    """Positive control — the stripper+scan WOULD flag a generation call.

    Without this, a stripper bug that blanks everything would make the gate
    vacuously pass. A synthetic source carrying a real
    ``client.models.generate_content(...)`` must be flagged AFTER stripping;
    the same string inside a docstring must NOT be flagged (header prose can't
    self-invalidate the gate).
    """
    offending = (
        '"""Docstring mentioning generate_content to document the ban."""\n'
        "resp = client.models.generate_content(model=m, contents=c)\n"
    )
    stripped = _strip_comments_and_docstrings(offending)
    hits = [pat for pat in FORBIDDEN if pat in stripped]
    assert "generate_content" in hits, (
        f"detector failed to flag a generation call; hits={hits}"
    )

    doc_only = '"""We never call generate_content here — embeddings only."""\n' "x = 1\n"
    doc_stripped = _strip_comments_and_docstrings(doc_only)
    assert "generate_content" not in doc_stripped, (
        "stripper left a docstring mention in place — header prose would "
        "self-invalidate the gate"
    )


def test_memory_calls_only_embed_content() -> None:
    """STORE-02 — memory/ references no generation surface (raw-in/raw-out).

    Scans tokenize-stripped (comments + docstrings removed) executable source
    of every ``src/vibemix/memory/*.py`` for the forbidden generation surfaces.
    None may appear: the store's only model call is the embedding call. RED /
    vacuous until the package exists; a real guarantee thereafter.
    """
    offenders: dict[str, list[str]] = {}
    for py in _memory_py_files():
        stripped = _strip_comments_and_docstrings(
            py.read_text(encoding="utf-8", errors="replace")
        )
        hits = [pat for pat in FORBIDDEN if pat in stripped]
        if hits:
            offenders[str(py.relative_to(REPO))] = hits
    assert not offenders, (
        "vibemix.memory references a generation surface (raw-in/raw-out / "
        f"no-extraction invariant VIOLATED): {offenders}. The store path may "
        "only use the injected local embedding protocol; never generate_content "
        "/ generate_reply / a chat session."
    )
