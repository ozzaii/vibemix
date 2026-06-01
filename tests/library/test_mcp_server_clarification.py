# SPDX-License-Identifier: Apache-2.0
"""FastMCP exposure of ``request_clarification`` — Plan 100-02 (Factor 7).

Plan 100-01 shipped the ``LibraryToolset.request_clarification`` handler at
``src/vibemix/library/toolset.py:1126-1245``. It is dispatch-callable from
Python, but it is NOT yet reachable from Codex's MCP harness — Codex only sees
the tools registered via ``@mcp.tool()`` in
``src/vibemix/library/mcp_server.py``'s ``build_server``. Plan 100-02 adds the
thin FastMCP wrapper. These tests pin five behaviors:

1.  **Build smoke** — ``build_server(fake_toolset)`` returns a FastMCP-like
    object (has a ``run`` method) without raising. No Codex spawn, no STDIO
    transport — purely a ``build_server()`` unit check.
2.  **Tool count regression-pin** — the registered tool count is the grounded
    base surface (16) + 1 = **17**. If a future refactor accidentally drops a
    tool, this count flips and the regression is caught.
3.  **Tool delegation correctness** — invoking the registered
    ``request_clarification`` function delegates to
    ``fake_toolset.request_clarification`` with the exact args dict
    ``{"question": question, "choices": choices}`` (Decision 1 contract: the
    MCP wrapper dict-packs the kwargs; the toolset handler is the single
    source of truth for validation).
4.  **Signature pin** — ``inspect.signature`` confirms parameters are exactly
    ``(question: str, choices: list[str])`` — no defaults, no extra params.
    Annotation on ``choices`` is the ``list[str]`` shape FastMCP needs to
    derive the JSON schema (Decision 1 strict signature).
5.  **Docstring TEACHING surface (anti-slop substring check)** — Codex reads
    the docstring as part of its tool repertoire. We pin that it is non-empty
    AND contains the phrase ``"ambiguous"`` or ``"disambiguation"`` AND
    contains at least one of the seed examples (``"BPM range"`` / ``"context"``
    / ``"mood register"``). If the docstring drifts away from teaching Codex
    WHEN to call this tool, Factor-7 compliance silently regresses; this
    substring contract is the runtime gate.

Plus an existing-exposures byte-equivalence check (no accidental drop of the
16 grounded base tools).

No Codex spawn. No STDIO transport. The fake toolset is a plain class with
stub methods returning ``{}`` for each registered tool — enough for FastMCP's
introspection / signature derivation to succeed at ``build_server`` time.
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from typing import Any

import pytest

from vibemix.library.mcp_server import build_server

# --------------------------------------------------------------------------- #
# FakeToolset — stub object with one method per registered tool.
# --------------------------------------------------------------------------- #


class _FakeToolset:
    """Lightweight stub mirroring LibraryToolset's public dispatch surface.

    Every method returns ``{}`` by default. ``request_clarification`` records
    the args dict it received so the delegation test can assert the dict
    shape the MCP wrapper passes through.
    """

    def __init__(self) -> None:
        self.recorded_clarification_args: dict[str, Any] | None = None

    # -- core discovery + playlist write ---------------------------------- #
    def search_vibe(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def get_track_features(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def get_track_sections(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def transition_slate(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def compile_musical_context(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def smart_hot_cues(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def export_smart_cues(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def create_playlist(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    # -- set-prep --------------------------------------------------------- #
    def get_track_energy(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def discover_pool(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def sequence_set(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def export_set(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    # -- DJ-knowledge / source -------------------------------------------- #
    def web_search(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def fetch_url(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def quote_moment(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    def retrieve_dj_knowledge(self, args: dict[str, Any]) -> dict[str, Any]:
        return {}

    # -- Plan 100-02's new surface ---------------------------------------- #
    def request_clarification(self, args: dict[str, Any]) -> dict[str, Any]:
        # Record the args the MCP wrapper hands us — the delegation test
        # reads this to confirm dict-packing shape.
        self.recorded_clarification_args = args
        return {
            "clarification_needed": True,
            "question": args.get("question"),
            "choices": args.get("choices"),
        }


# --------------------------------------------------------------------------- #
# Fixtures.
# --------------------------------------------------------------------------- #


@pytest.fixture
def fake_toolset() -> _FakeToolset:
    return _FakeToolset()


@pytest.fixture
def server(fake_toolset: _FakeToolset) -> Any:
    """A built FastMCP server with the fake toolset. Plan 100-02 GREEN target."""
    return build_server(fake_toolset)


# --------------------------------------------------------------------------- #
# Tests.
# --------------------------------------------------------------------------- #


def test_build_server_smoke(server: Any) -> None:
    """build_server returns a FastMCP-like object (has a ``run`` method).

    Plan 100-02 must not break this baseline.
    """
    assert hasattr(server, "run"), "FastMCP server must expose a run() method"


def test_registered_tool_count_is_seventeen(server: Any) -> None:
    """The grounded base surface is 16; request_clarification brings it to 17.

    Regression-pin: if a future refactor drops a tool, this flips.
    """
    tools = server._tool_manager.list_tools()
    assert len(tools) == 17, (
        f"Expected 17 registered tools (16 base + 1 request_clarification), "
        f"got {len(tools)}: {[t.name for t in tools]}"
    )


def test_request_clarification_is_registered(server: Any) -> None:
    """The new tool is registered by name."""
    names = {t.name for t in server._tool_manager.list_tools()}
    assert "request_clarification" in names, (
        f"request_clarification not registered; got: {sorted(names)}"
    )


def test_existing_sixteen_grounded_tools_still_registered(server: Any) -> None:
    """The 16 grounded base tools are registered; raw cue export stays absent.

    Raw ``export_cues`` accepted arbitrary track paths/cue payloads and is no
    longer part of the agent-facing MCP surface; ``export_smart_cues`` is the
    grounded cue-write path.
    """
    expected_base = {
        "search_vibe",
        "get_track_features",
        "get_track_sections",
        "transition_slate",
        "compile_musical_context",
        "smart_hot_cues",
        "export_smart_cues",
        "create_playlist",
        "get_track_energy",
        "discover_pool",
        "sequence_set",
        "export_set",
        "web_search",
        "fetch_url",
        "quote_moment",
        "retrieve_dj_knowledge",
    }
    names = {t.name for t in server._tool_manager.list_tools()}
    missing = expected_base - names
    assert not missing, f"Plan 100-02 accidentally dropped: {sorted(missing)}"
    assert "export_cues" not in names


def test_request_clarification_delegates_with_dict_packed_args(
    fake_toolset: _FakeToolset, server: Any
) -> None:
    """Calling the registered tool dict-packs the kwargs and forwards them
    to ``toolset.request_clarification`` exactly as Decision 1 specifies.

    The MCP wrapper signature is ``(question: str, choices: list[str])`` —
    the body must pack those into ``{"question": question, "choices": choices}``
    before delegating. No inlined validation; single source of truth at the
    toolset layer.
    """
    tool = server._tool_manager.get_tool("request_clarification")
    assert tool is not None, "tool must be registered for delegation check"

    # Invoke the underlying callable directly.
    result = tool.fn(
        question="BPM range?",
        choices=["slow (90-110)", "fast (130-140)"],
    )

    # Delegation invariant: the toolset receives the dict-packed shape.
    assert fake_toolset.recorded_clarification_args == {
        "question": "BPM range?",
        "choices": ["slow (90-110)", "fast (130-140)"],
    }, (
        "Wrapper must dict-pack kwargs into {'question': q, 'choices': cs} "
        "before calling toolset.request_clarification — Decision 1 contract."
    )

    # And the wrapper passes the toolset's return dict back unchanged.
    assert result["clarification_needed"] is True
    assert result["question"] == "BPM range?"
    assert result["choices"] == ["slow (90-110)", "fast (130-140)"]


def test_request_clarification_signature_is_strict(server: Any) -> None:
    """Exactly two parameters, no defaults, ``list[str]`` on choices.

    FastMCP infers the JSON schema from this signature; any drift (default
    values, extra params, weakened annotations) changes the schema Codex
    sees, which silently changes Factor-7 behavior.
    """
    tool = server._tool_manager.get_tool("request_clarification")
    assert tool is not None

    sig = inspect.signature(tool.fn)
    params = list(sig.parameters.values())
    assert len(params) == 2, f"expected exactly 2 params, got {len(params)}: {params}"

    p_question, p_choices = params
    assert p_question.name == "question"
    assert p_choices.name == "choices"

    # No defaults — both params are required.
    assert p_question.default is inspect.Parameter.empty, "question must have no default"
    assert p_choices.default is inspect.Parameter.empty, "choices must have no default"

    # Annotations resolve to str and list[str] under the module's
    # `from __future__ import annotations` posture. Annotations come back as
    # strings in that case; check string equality which is the precise
    # contract we ship.
    assert p_question.annotation in (str, "str"), (
        f"question annotation must be str, got {p_question.annotation!r}"
    )
    assert p_choices.annotation in (list[str], "list[str]"), (
        f"choices annotation must be list[str], got {p_choices.annotation!r}"
    )


def test_request_clarification_docstring_teaches_codex(server: Any) -> None:
    """The docstring is the LLM-teaching surface; it must be non-empty
    AND mention ambiguity AND mention at least one seed example.

    Anti-slop substring gate — keeps the teaching prompt from drifting into
    generic "ask the user something" boilerplate.
    """
    tool = server._tool_manager.get_tool("request_clarification")
    assert tool is not None
    doc = tool.fn.__doc__
    assert doc and doc.strip(), "request_clarification must have a non-empty docstring"

    doc_lower = doc.lower()
    assert "ambiguous" in doc_lower or "disambiguation" in doc_lower, (
        "docstring must mention 'ambiguous' or 'disambiguation' so Codex learns "
        "the trigger condition — Decision 2 teaching surface."
    )

    seed_examples = ("bpm range", "context", "mood register")
    assert any(s in doc_lower for s in seed_examples), (
        f"docstring must include at least one of the seed examples "
        f"{seed_examples} so Codex sees concrete disambiguation patterns."
    )


def test_grep_gate_seventeen_mcp_tool_decorators() -> None:
    """Subprocess grep gate — independent confirmation that the source file
    has exactly 17 ``@mcp.tool()`` decorators.

    Belt-and-braces for the registered-tool-count check; this also catches
    "tool was added but build_server didn't re-bind it" drift since the
    decorator is what binds.
    """
    src = Path(__file__).resolve().parents[2] / "src" / "vibemix" / "library" / "mcp_server.py"
    assert src.exists(), f"mcp_server.py not found at {src}"
    out = subprocess.run(
        ["grep", "-c", "@mcp.tool()", str(src)],
        capture_output=True,
        text=True,
        check=False,
    )
    count = int(out.stdout.strip())
    assert count == 17, (
        f"Expected exactly 17 @mcp.tool() decorators in mcp_server.py, "
        f"got {count}. Either request_clarification is missing, the raw "
        f"export_cues tool came back, or a sibling grounded tool was dropped."
    )


def test_docstring_mentions_choices_length_bound(server: Any) -> None:
    """Decision 2 lock: choices length is 2-5. The teaching docstring should
    surface that bound so Codex doesn't emit empty/1-element/10-element
    choice lists that the toolset would just reject."""
    tool = server._tool_manager.get_tool("request_clarification")
    assert tool is not None
    doc = (tool.fn.__doc__ or "").lower()
    # Either the explicit numeric range OR the phrase "2-5" / "2 to 5" /
    # "between 2 and 5" all satisfy this — keep the gate text-tolerant.
    has_range = (
        "2-5" in doc
        or "2 to 5" in doc
        or ("between 2 and 5" in doc)
        or ("at most 5" in doc and "at least 2" in doc)
    )
    assert has_range, (
        "docstring should mention the 2-5 choices length bound (Decision 2 lock) "
        "so Codex doesn't waste calls with rejected choice counts."
    )
