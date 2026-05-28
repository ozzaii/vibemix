# SPDX-License-Identifier: Apache-2.0
"""Phase 100 HARDEN-CLARIFY-07 — Cardinal Invariant #2 structural safety AST gate.

The request_clarification handler in `LibraryToolset` has NO `track_id` surface
by construction: it accepts only `question: str` and `choices: list[str]` (via
the args dict per the dispatch convention), and it never reads any track_id
key from args, never writes to self.seen / self.seen_sections / self.issued_*,
never touches any grounding gate. This file PROVES that property structurally
at every PR — a future maintainer who adds a track_id parameter or accidentally
mutates self.seen from this handler trips the gate at PR time, not at customer
time.

Run with:
    PYTHONPATH=src python3 -m pytest -q tests/library/test_request_clarification_no_track_surface.py

The gate complements (does NOT replace) the behavioral tests in
tests/library/test_toolset_clarification.py from Plan 100-01. Those tests check
that a VALID call works as expected; this gate checks that the handler CANNOT
do something that violates Invariant #2 (no matter how cleverly it's edited).

## What this gate pins (six structural properties)

1. **No track_id surface** (`test_request_clarification_no_track_surface`) —
   the handler body MUST NOT contain any string-literal alias for track_id
   (track_id / trackId / track-id / track_ids / trackIds). If those strings
   are absent from the function body's string constants, the handler cannot
   read `args.get("track_id")` (etc.) — Cardinal Invariant #2 holds by
   construction.

2. **No grounding-state mutation** (`test_request_clarification_no_seen_mutation`)
   — the handler MUST NOT reference any attribute chain rooted at
   `self.seen` / `self.seen_sections` / `self.issued_*`. Reading these would
   suggest a write is imminent; the disambiguation path stays disjoint from
   the discovery/curation grounding spine.

3. **No starvation counter coupling**
   (`test_request_clarification_no_consecutive_empties_touch`) — CONTEXT.md
   Decision 4 mandates the clarification path is independent of Phase 99's
   `_consecutive_empties` starvation counter. Touching it would couple two
   terminal paths and risk spurious `tool_starvation` trips after a legitimate
   clarification.

4. **Strict dispatch-convention signature**
   (`test_request_clarification_signature_strict`) — CONTEXT.md Decision 1
   locks `(self, args)` with no *args/**kwargs/keyword-only args. Explicit
   `(question, choices)` kwargs would break the dispatch table's uniform
   calling convention.

5. **Single-turn semantics**
   (`test_request_clarification_single_turn_no_internal_loop`) — the handler
   MUST NOT contain a while-loop or self-recursion. HARDEN-CLARIFY-06
   single-turn contract is structural: one trip in, one trip out. Multi-turn
   refactors belong to HARDEN-FUTURE-01.

6. **BASELINE_SEEN_ADD_COUNT carry-over**
   (`test_baseline_seen_add_count_unchanged_post_phase_100`) — Plan 99-05's
   tests/repo gate pins the `self.seen.add(` site count at 2. Plan 100-06
   mirrors the pin from the tests/library/ side so the Phase 100 plan's
   must-haves include a literal regression check.

## Why static AST (not behavioral mock-based)

The behavioral pin (mocks proving `self.seen` is never accessed) lives in
Plan 100-01's `tests/library/test_toolset_clarification.py`. That test
exercises ONE code path. This file gates EVERY possible code path because
it inspects the AST itself. A clever maintainer who short-circuits the mock
under a feature flag would still trip the AST gate, because the forbidden
strings / attribute chains would still appear in the source text. AST is the
authoritative grammar; the gate cannot be lied to.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLSET = REPO_ROOT / "src" / "vibemix" / "library" / "toolset.py"

# Track-id alias surface forbidden in request_clarification body.
# A `args.get("track_id")` call leaves the string literal "track_id" in the
# function body's ast.Constant nodes; the gate catches it without needing
# to simulate the call.
FORBIDDEN_TRACK_ID_KEYS: frozenset[str] = frozenset({
    "track_id",
    "trackId",
    "track-id",
    "track_ids",
    "trackIds",
})

# Grounding-state attributes forbidden as access/mutation targets in
# request_clarification. Coverage:
#   * self.seen — the Cardinal Invariant #2 grounding spine (write sites
#     pinned at 2 by Plan 99-05's BASELINE_SEEN_ADD_COUNT).
#   * self.seen_sections — section-level grounding for the discover_pool /
#     sequence_set surface.
#   * self.issued_transition_candidates / issued_cue_proposals /
#     issued_context_packets — per-run dedup gates for those handlers; a
#     clarification handler reaching into them would couple two unrelated
#     terminal paths.
#   * self.seen_urls — URL-level grounding for the web-search surface.
FORBIDDEN_GROUNDING_ATTRS: frozenset[str] = frozenset({
    "seen",
    "seen_sections",
    "issued_transition_candidates",
    "issued_cue_proposals",
    "issued_context_packets",
    "seen_urls",
})


def _find_function_in_class(
    source: str, class_name: str, func_name: str
) -> ast.FunctionDef:
    """Return the FunctionDef node for class_name.func_name. Raises if not found.

    Walks the parsed AST looking for a top-level ClassDef matching `class_name`,
    then scans its direct body for a FunctionDef matching `func_name`. We do
    NOT walk recursively into nested classes/functions — the handler lives at
    LibraryToolset's top-level method scope, and matching a same-named nested
    helper would be a false positive.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == func_name:
                    return item
    raise AssertionError(
        f"Could not find {class_name}.{func_name} in "
        f"{TOOLSET.relative_to(REPO_ROOT)}. If the handler moved, update "
        "this gate's lookup."
    )


def _walk_strings(node: ast.AST) -> list[str]:
    """Return every string-literal value reached from `node`.

    Uses ast.Constant (Python 3.8+ canonical form). The handler body's
    `args.get("question")` and `args.get("choices")` calls leave their string
    arguments as Constant nodes; the gate scans for forbidden keys among them.
    """
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value)
    return out


def _walk_attribute_chains(node: ast.AST) -> list[str]:
    """Return dotted attribute chains like 'self.seen', 'self.seen.add'.

    For each ast.Attribute node, render the chain by walking back through
    `.value` until we hit a Name (the root). `self.seen.add` is shaped as
    Attribute(attr='add', value=Attribute(attr='seen', value=Name('self'))).
    Useful for cheap structural checks without writing a full NodeVisitor.

    Note: chains rooted at non-Name expressions (e.g. `func().attr`) are
    rendered without the root, which is fine for our purposes — we only
    care about chains rooted at `self`.
    """
    chains: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            parts: list[str] = [child.attr]
            cur: ast.AST = child.value
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            chains.append(".".join(reversed(parts)))
    return chains


def test_request_clarification_no_track_surface() -> None:
    """request_clarification MUST NOT read any track_id alias from args.

    A call to ``args.get("track_id")`` or any FORBIDDEN_TRACK_ID_KEYS variant
    inside the handler body fails this gate. Cardinal Invariant #2 (citation
    grounding) holds STRUCTURALLY: a clarification CANNOT fabricate a track
    reference because the handler never reads one.

    Detection: scans every string-literal Constant in the handler body. The
    handler legitimately uses literals like "question", "choices", "error",
    "rejected", "clarification_needed" — none of those collide with any
    track_id alias, so the gate's intersection check has zero false positives.
    """
    source = TOOLSET.read_text(encoding="utf-8")
    func = _find_function_in_class(source, "LibraryToolset", "request_clarification")
    strings = _walk_strings(func)
    forbidden_seen = set(strings) & FORBIDDEN_TRACK_ID_KEYS
    assert not forbidden_seen, (
        f"request_clarification handler references forbidden track_id-alias "
        f"key(s) {sorted(forbidden_seen)} in its body. Cardinal Invariant #2 "
        f"requires NO track_id surface in this handler (a clarification cannot "
        f"fabricate a track reference). Remove the args.get(\"<key>\") read "
        f"or move the logic to a different handler that has a grounded "
        f"track_id surface (e.g. get_track_features)."
    )


def test_request_clarification_no_seen_mutation() -> None:
    """request_clarification MUST NOT touch any grounding-state attribute.

    Scans every attribute chain in the handler body for chains rooted at
    `self.<FORBIDDEN>` where FORBIDDEN is any entry of
    FORBIDDEN_GROUNDING_ATTRS. Detection is coarse (any chain that STARTS
    with `self.seen` etc., including bare reads) — the rationale is that
    even a read of these attributes from this handler is a code-smell:
    the disambiguation path should not need them at all.

    The handler legitimately reads `self.stop_reason` and calls
    `self._build_clarification_payload(...)` / `self._write_side_channel(...)`
    — none of those start with a forbidden grounding attr, so the gate has
    zero false positives against the current implementation.
    """
    source = TOOLSET.read_text(encoding="utf-8")
    func = _find_function_in_class(source, "LibraryToolset", "request_clarification")
    chains = _walk_attribute_chains(func)
    forbidden_chains = [
        c for c in chains
        if any(
            c == f"self.{attr}" or c.startswith(f"self.{attr}.")
            for attr in FORBIDDEN_GROUNDING_ATTRS
        )
    ]
    assert not forbidden_chains, (
        f"request_clarification handler references grounding-state "
        f"attribute(s) {sorted(set(forbidden_chains))}. Cardinal Invariant #2 "
        f"requires the handler stay disjoint from the grounding spine "
        f"(self.seen / self.seen_sections / self.issued_*). If you need to "
        f"reach those attributes, you're in the wrong handler — "
        f"request_clarification is the disambiguation path, not the "
        f"discovery/curation path."
    )


def test_request_clarification_no_consecutive_empties_touch() -> None:
    """request_clarification MUST NOT read or write self._consecutive_empties.

    The clarification path is INDEPENDENT of Phase 99's starvation counter
    (CONTEXT.md Decision 4: terminal short-circuit reuse is via the
    self.stop_reason attribute, NOT via the counter). A handler touching
    _consecutive_empties would couple the two terminal paths and risk
    spurious tool_starvation trips after a legitimate clarification.
    """
    source = TOOLSET.read_text(encoding="utf-8")
    func = _find_function_in_class(source, "LibraryToolset", "request_clarification")
    chains = _walk_attribute_chains(func)
    forbidden = [c for c in chains if "_consecutive_empties" in c]
    assert not forbidden, (
        f"request_clarification handler touches _consecutive_empties "
        f"(found: {sorted(set(forbidden))}). CONTEXT.md Decision 4 mandates "
        f"the clarification path is independent of the starvation counter. "
        f"Detect terminal state via self.stop_reason instead — that is the "
        f"public propagation seam shared with Phase 99."
    )


def test_request_clarification_signature_strict() -> None:
    """Signature regression-pin: ``(self, args: dict[str, Any]) -> dict[str, Any]``.

    The handler MUST follow the dispatch convention (CONTEXT.md Decision 1):
    a single ``args`` parameter, dict-typed. NOT explicit ``(question, choices)``
    kwargs — that breaks the dispatch table's uniform calling convention at
    toolset.py:1145-1163 (every handler is invoked as ``handler(args_dict)``).
    """
    source = TOOLSET.read_text(encoding="utf-8")
    func = _find_function_in_class(source, "LibraryToolset", "request_clarification")
    # Expected positional args: [self, args]. No defaults, no varargs, no kwargs.
    arg_names = [a.arg for a in func.args.args]
    assert arg_names == ["self", "args"], (
        f"request_clarification signature drifted from the dispatch "
        f"convention: expected positional args [self, args], got {arg_names}. "
        f"CONTEXT.md Decision 1 locks the args-dict signature. If you want "
        f"explicit kwargs, you're breaking the dispatch table."
    )
    assert not func.args.kwonlyargs, (
        "request_clarification must not have keyword-only args — dispatch "
        "table calls handler(args_dict) positionally."
    )
    assert func.args.vararg is None, (
        "request_clarification must not use *args — single args dict only."
    )
    assert func.args.kwarg is None, (
        "request_clarification must not use **kwargs — single args dict only."
    )


def test_request_clarification_single_turn_no_internal_loop() -> None:
    """Single-turn contract: the handler MUST NOT contain a while-loop or
    a recursive call into itself.

    The clarification is a single trip. A while-loop / recursion would
    suggest the handler is trying to retry or escalate — that is a
    HARDEN-FUTURE-01 multi-turn pattern, explicitly out of scope for
    Phase 100 per CONTEXT.md domain section + HARDEN-CLARIFY-06.

    Note: ``for`` loops are NOT forbidden — the handler iterates the
    ``choices`` list to validate every entry is a non-empty string. That's
    bounded by the MAX_CHOICES constant, runs to completion in one trip,
    and does not extend the run beyond the single dispatch call.
    """
    source = TOOLSET.read_text(encoding="utf-8")
    func = _find_function_in_class(source, "LibraryToolset", "request_clarification")
    has_while = any(isinstance(n, ast.While) for n in ast.walk(func))
    assert not has_while, (
        "request_clarification handler contains a while-loop. Single-turn "
        "semantics (CONTEXT.md domain section + HARDEN-CLARIFY-06) require "
        "the handler to be a single trip — no internal retry/escalate loop. "
        "If you need multi-turn, that's HARDEN-FUTURE-01, not Phase 100."
    )
    # Detect direct self-recursion: a Call where func is
    # Attribute(value=Name('self'), attr='request_clarification').
    for child in ast.walk(func):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if (
                isinstance(child.func.value, ast.Name)
                and child.func.value.id == "self"
                and child.func.attr == "request_clarification"
            ):
                raise AssertionError(
                    "request_clarification handler calls itself recursively. "
                    "Single-turn handler — no recursion. Multi-turn belongs "
                    "to HARDEN-FUTURE-01."
                )


def test_baseline_seen_add_count_unchanged_post_phase_100() -> None:
    """Cardinal Invariant #2 carry-over check from Plan 99-05.

    Phase 100 promised: BASELINE_SEEN_ADD_COUNT stays at 2 (Plan 99-03's
    baseline). The Plan 99-05 gate at tests/repo/test_no_seen_relaxation.py
    pins this on every PR — Plan 100-06 adds an EXPLICIT verification here
    so the Phase 100 plan's must-haves include a literal regression pin
    visible from the tests/library/ side.

    Two-layer defense: tests/repo gate (Phase 99) + tests/library gate
    (Phase 100). A future PR that bumps the count must update BOTH
    constants and explicitly justify the Invariant #2 modification.
    """
    source = TOOLSET.read_text(encoding="utf-8")
    # Comment-filtered count, matching the Plan 99-05 helper logic.
    count = 0
    for line in source.splitlines():
        if line.lstrip().startswith("#"):
            continue
        if "self.seen.add(" in line:
            count += 1
    assert count == 2, (
        f"Phase 100 promised BASELINE_SEEN_ADD_COUNT stays at 2. "
        f"Current count: {count}. If you intentionally added a "
        f"self.seen.add site in Phase 100 or later, this is a Cardinal "
        f"Invariant #2 modification — see tests/repo/test_no_seen_relaxation.py "
        f"for the bump recipe (update BOTH this gate and the tests/repo gate)."
    )
