# SPDX-License-Identifier: Apache-2.0
"""Phase 96 Plan 01 — reuse-existing-coach AST gate (CONTEXT.md §Decisions).

Every tutor-narration prompt builder under ``src/vibemix/learn/`` MUST
compose its prompt body via :func:`vibemix.state.prompt_builder.AICoach.build_prompt`.
The lens never rolls its own LLM prompt body — pin invariant-#1-by-
construction at the prompt-composition seam: if ``learn/`` owns prompt
building, it grows incentives to write MusicState; routing through
AICoach.build_prompt keeps the data flow one-way (state/refresh.py
writes MusicState → AICoach reads it → learn/ wraps the composed
prompt only).

REQ-ID: CURR-3.07 + reuse-existing-coach binding.

Scope: the gate is narrow by filename — it scans
``prompts.py`` / ``tutor_narration.py`` / ``proactive_lens.py`` /
``tutor.py`` modules under ``learn/``. A helper named
``_compose_prompt_section`` inside ``runtime.py`` is NOT a violation;
the actual prompt-composition seam lives in the four named files.
"""
from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterable

# Function names that smell like prompt builders. Matched
# case-insensitive via the lowercased name; substring match.
_PROMPT_BUILDER_NAME_PATTERNS: tuple[str, ...] = (
    "tutor_prompt",
    "build_tutor",
    "tutor_narration",
    "compose_prompt",
    "proactive_lens",
)


# Module filenames in scope for the gate. Restricting the scan to these
# keeps the gate narrow + signal-rich — a helper named
# ``_compose_prompt_section`` inside ``runtime.py`` is not a violation;
# the lens's actual prompt-composition seam lives in ``prompts.py`` /
# ``tutor_narration.py`` / ``proactive_lens.py`` (when Plan 96-03 ships).
_PROMPT_COMPOSITION_MODULES: tuple[str, ...] = (
    "prompts.py",
    "tutor_narration.py",
    "proactive_lens.py",
    "tutor.py",
)


# Magic opt-out comment authors can attach to a smell-matching function
# that is NOT a real prompt builder (e.g. a unit-test helper, a stub).
_OPT_OUT_TOKEN: str = "allow-tutor-prompt-without-coach"


def _repo_root() -> pathlib.Path:
    # tests/learn/test_course3_uses_existing_coach.py → ../../
    return pathlib.Path(__file__).resolve().parent.parent.parent


def _default_learn_dir() -> pathlib.Path:
    return _repo_root() / "src" / "vibemix" / "learn"


def _walk_python_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if not root.exists():
        return
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _function_smell(name: str) -> bool:
    lname = name.lower()
    return any(p in lname for p in _PROMPT_BUILDER_NAME_PATTERNS)


def _function_calls_aicoach_build_prompt(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """True iff the function body has at least one Call whose func is
    ``Attribute(value=Name("AICoach"), attr="build_prompt")`` OR
    ``Attribute(value=Attribute(...), attr="build_prompt")`` (handles
    module-qualified ``coach.AICoach.build_prompt`` /
    ``vibemix.state.prompt_builder.AICoach.build_prompt`` shapes), OR a local
    coach-named binding like ``coach.build_prompt(...)``.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Attribute) and func.attr == "build_prompt":
                # Resolve the value chain to a terminal Name; assert
                # "AICoach" appears in that chain.
                cur = func.value
                while isinstance(cur, ast.Attribute):
                    cur = cur.value
                if isinstance(cur, ast.Name) and cur.id == "AICoach":
                    return True
                # Also allow ``coach_instance.build_prompt(...)`` where
                # the binding name carries "coach" — carve-out for
                # ``coach = AICoach(...)`` patterns.
                if isinstance(cur, ast.Name) and "coach" in cur.id.lower():
                    return True
    return False


def _has_opt_out_comment(source: str, lineno: int) -> bool:
    """True iff the function-def at ``lineno`` carries the magic opt-out
    token in a comment on the def line itself, or anywhere in the
    contiguous comment block immediately above the def.

    Walks BACKWARDS from the line above the def, scanning comment lines
    (``stripped.startswith("#")``) and blank lines. The first non-comment,
    non-blank line breaks the block — the opt-out comment must sit
    inside the contiguous header block (the natural place a planner
    annotates "this looks like a prompt builder but is not").
    """
    lines = source.splitlines()
    # ``lineno`` is 1-based; the def line is ``lines[lineno - 1]``.
    def_idx = max(0, lineno - 1)
    if def_idx >= len(lines):
        return False
    if _OPT_OUT_TOKEN in lines[def_idx]:
        return True
    # Walk backwards through the contiguous block of comment/blank lines.
    i = def_idx - 1
    while i >= 0:
        stripped = lines[i].strip()
        if stripped == "":
            i -= 1
            continue
        if stripped.startswith("#"):
            if _OPT_OUT_TOKEN in lines[i]:
                return True
            i -= 1
            continue
        # First real-code line above the def — stop.
        break
    return False


def _scan_module(path: pathlib.Path) -> list[tuple[int, str]]:
    """Return list of (line_no, function_name) for every smell-matching
    function in ``path`` that does NOT call AICoach.build_prompt and does
    NOT carry the opt-out comment.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _function_smell(node.name):
                continue
            if _has_opt_out_comment(source, node.lineno):
                continue
            if _function_calls_aicoach_build_prompt(node):
                continue
            offenders.append((node.lineno, node.name))
    return offenders


def test_learn_prompt_builders_route_through_aicoach() -> None:
    """CURR-3.07 + reuse-existing-coach binding (CONTEXT.md §Decisions).

    Every tutor-narration prompt builder under ``src/vibemix/learn/``
    composes its prompt via ``state.prompt_builder.AICoach.build_prompt``. The
    lens never rolls a fresh LLM prompt body. This pins
    invariant-#1-by-construction at the prompt-composition seam: if
    learn/ owns prompt building, it grows incentives to write
    MusicState; routing through AICoach.build_prompt keeps the data
    flow one-way.
    """
    learn_dir = _default_learn_dir()
    all_offenders: list[str] = []
    for path in _walk_python_files(learn_dir):
        if path.name not in _PROMPT_COMPOSITION_MODULES:
            continue
        for line_no, fname in _scan_module(path):
            all_offenders.append(f"{path}:{line_no}: function `{fname}`")
    assert not all_offenders, (
        "CURR-3.07 violation — a ``learn/`` prompt-composition module "
        "rolled its own LLM prompt body without calling "
        "AICoach.build_prompt. Route through state.prompt_builder.AICoach.build_prompt "
        "(the v8.0 evidence_line + task_for_event + format_wrapper triad) "
        "or attach ``# allow-tutor-prompt-without-coach: <reason>`` to "
        "the function if it genuinely is not a prompt builder.\n\n"
        "Offenders:\n  " + "\n  ".join(all_offenders)
    )


def test_synthetic_offender_reds_the_gate(tmp_path: pathlib.Path) -> None:
    """Negative-control proof."""
    offender = tmp_path / "prompts.py"
    offender.write_text(
        "def build_tutor_prompt():\n"
        '    return "raw prompt body — no AICoach reference"\n',
        encoding="utf-8",
    )
    offenders = _scan_module(offender)
    assert offenders, "gate failed to detect a known-bad prompt builder"


def test_synthetic_complier_passes(tmp_path: pathlib.Path) -> None:
    """Positive-control proof."""
    complier = tmp_path / "prompts.py"
    complier.write_text(
        "from vibemix.state.prompt_builder import AICoach\n"
        "def build_tutor_prompt(state, event):\n"
        "    return AICoach.build_prompt(state, event)\n",
        encoding="utf-8",
    )
    offenders = _scan_module(complier)
    assert not offenders, (
        f"gate falsely flagged a compliant builder: {offenders}"
    )


def test_opt_out_magic_comment_respected(tmp_path: pathlib.Path) -> None:
    """Explicit opt-out for false positives."""
    opt_out = tmp_path / "prompts.py"
    opt_out.write_text(
        "# allow-tutor-prompt-without-coach: stub fixture for unit test\n"
        "def build_tutor_prompt():\n"
        '    return "stub"\n',
        encoding="utf-8",
    )
    offenders = _scan_module(opt_out)
    assert not offenders, (
        f"opt-out comment ignored — false positive: {offenders}"
    )


def test_out_of_scope_modules_not_scanned(tmp_path: pathlib.Path) -> None:
    """``runtime.py`` / ``fixtures.py`` etc. with smell-matching helpers
    are NOT in-scope (gate is narrow by design).

    The scanner-level call ``_scan_module(runtime.py)`` still flags
    smell-matching functions (the scanner has no scope filter), but
    only the OUTER filename filter in
    ``test_learn_prompt_builders_route_through_aicoach`` makes the gate
    narrow. Confirm the scanner-level behavior matches.
    """
    runtime = tmp_path / "runtime.py"
    runtime.write_text(
        "def _compose_prompt_section():\n"
        '    return "internal helper"\n',
        encoding="utf-8",
    )
    offenders = _scan_module(runtime)
    # ``_compose_prompt_section`` matches the "compose_prompt" smell
    # pattern, so the scanner returns it as an offender — but only the
    # outer filename filter narrows the gate.
    assert offenders, (
        "scanner unexpectedly returned no offenders — "
        "_compose_prompt_section matches the smell pattern even outside "
        "prompts.py"
    )
