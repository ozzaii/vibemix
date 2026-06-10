# SPDX-License-Identifier: Apache-2.0
"""Phase 99 Plan 99-05 — Invariant #1 (single-writer analog) + Invariant #2
(citation grounding) AST/grep gates for Viber's Factor-9 starvation surface.

These three repo-level gates pin the structural shape of Phase 99's
starvation telemetry across `src/vibemix/`. They run on the current source
on every `pytest tests/repo/` invocation — a future PR that drifts the
surface (relaxes the `seen` write count, sprinkles counter reads across
`agent/`, leaks `stop_reason` into `intel/`) trips the gate at PR time, not
at customer time.

## Pinned contracts

* **`test_seen_writes_unchanged_from_baseline`** — pins Cardinal Invariant
  #2 (citation grounding). `self.seen.add` is the per-run grounding write
  on `LibraryToolset`; the count of write sites must remain at the
  pre-Phase-99 baseline. Comment lines are filtered before counting (per
  RESEARCH.md hygiene rule + 99-03 SUMMARY's minor-textual-fix pattern).

* **`test_consecutive_empties_single_writer`** — pins the single-writer
  analog of Cardinal Invariant #1 for the starvation counter. The instance
  attribute `_consecutive_empties` is allocated in
  `LibraryToolset.__init__` and written ONLY by the dispatch hook in the
  same file; no other source module may read or write it. (Tests under
  `tests/` MAY reference it for assertions — the gate scopes to `src/`.)

* **`test_stop_reason_writes_confined_to_toolset`** — pins every
  `stop_reason` source reference to an explicit whitelist. The original
  Phase 99 Viber starvation propagation surface is still confined to the
  four owner/dispatch files; the later AI-message observability spine is
  authorized separately so live coach, bench, deck vision, Learn, debrief,
  and eval rows can record why an assistant turn stopped without weakening
  the Viber tool-starvation contract.

## `BASELINE_SEEN_ADD_COUNT` provenance

The baseline count is **2**, recorded by Plan 99-03's SUMMARY
(`.planning/phases/99-harden-retry/99-03-SUMMARY.md`) under the
"Grep gates" section:

  > `grep -c "self\\.seen\\.add" src/vibemix/library/toolset.py` → **2**
  > (UNCHANGED from the pre-99-01 baseline). **Baseline for Plan 99-05's
  > AST/grep gate: 2.** Cardinal Invariant #2 holds.

The two write sites today (verified by `grep -n` on `src/vibemix/library/
toolset.py` at Plan-99-05 execute time):

  * line 151 — `self.seen.add(r.track_id)` (search_vibe handler — grounds
    each returned candidate into the run's seen-set before the model can
    see it).
  * line 594 — `self.seen.add(item.track_id)` (parallel grounding inside
    discover_pool / sequence_set surface — same Invariant #2 grounding
    spine).

If a future PR adds or removes a `self.seen.add` line, this gate trips.
The PR author must explicitly justify the change to Cardinal Invariant #2
(citation grounding) before bumping this constant — see the failure
message for the recipe.

## Whitelist for `stop_reason` reads/writes

Pre-Phase-99 baseline: zero hits anywhere.

Phase 99 lands the four-file Viber tool-starvation propagation surface:

| File | What it does with `stop_reason` | Plan |
|---|---|---|
| `src/vibemix/library/toolset.py` | OWNER — `LibraryToolset.stop_reason` attribute. Single writer at the threshold-trip block (`toolset.py:1176`). Single non-`__init__` read by the top-of-dispatch short-circuit (`toolset.py:1115-1116`). Side-channel write helper reads `self.stop_reason` (`toolset.py:1179`). | 99-01 / 99-03 / 99-04 |
| `src/vibemix/library/codex_curate.py` | WRAPPER — allocates side-channel file path, injects `VIBEMIX_STOP_REASON_FILE` env var into the Codex subprocess, reads the side-channel file after `_runner` returns, sets `CodexCurateResult.stop_reason` on short-circuit. The dataclass field is the cross-process propagation seam. | 99-04 |
| `src/vibemix/__main__.py` | CLI DISPATCH — reads `result.stop_reason` at the `library curate` / `library build-set` CLI surfaces; routes to stderr hint + exit-code branching. Pre-existing reads (lines ~2525, 2545, 2554, 2591, 2600, 2842) cover the today-shipped stop reasons (`created`, `exported`, `codex_not_installed`, etc.); Plan 99-07 will add the exit-code-10 dispatch on `tool_starvation`. | 99-07 (extends pre-existing surface) |
| `src/vibemix/library/telegram_bridge.py` | MOBILE FORMAT — Plan 99-06 will add a `tool_starvation` branch to `format_reply(norm)` that renders the hint via `strip_leaks`. No hits yet at Plan-99-05 execute time (Plan 99-06 has not landed); the whitelist PRE-AUTHORIZES the file so when 99-06 lands the gate does not fight it. | 99-06 (pre-authorized) |

Package 1A later adds a cross-engine AI-message observability ledger. Those
rows use the generic `stop_reason` field for live co-host, bench, deck vision,
Learn, debrief, and eval/reporting surfaces. These are NOT Viber
tool-starvation propagation reads; they are canonical event-row metadata. The
authorized observability files are:

| File | What it does with `stop_reason` | Plan |
|---|---|---|
| `src/vibemix/runtime/ai_observability.py` | Defines the shared AI-message row shape and serializes `stop_reason` into the ledger. | Package 1A |
| `src/vibemix/agent/dj_cohost.py` | Emits live-coach assistant rows with the LLM/suppression/citation stop reason. | Package 1A |
| `src/vibemix/bench/run.py` | Emits bench-cell AI-message rows. | Package 1A |
| `src/vibemix/state/deck_vision.py` | Emits deck-vision success/error AI-message rows while the screen-reader source stays gated. | Package 1A |
| `src/vibemix/learn/observability.py` | Emits authored Learn tutor speech rows. | Package 1A |
| `src/vibemix/debrief/drills.py` | Emits debrief drill generation rows. | Package 1A |
| `src/vibemix/debrief/tldr.py` | Emits debrief TLDR/TTS rows. | Package 1A |
| `src/vibemix/eval/session_report.py` | Reads global AI-message rows, including Viber `tool_starvation`, to produce repair issues. | Package 1A |

Engine/DSP later adds the deterministic keyless set-prep surface. This is NOT
another Viber starvation propagation path; it is the terminal result shape for
the local no-Codex `auto_crate` command, routed through the existing CLI
dispatch in `__main__.py`.

| File | What it does with `stop_reason` | Plan |
|---|---|---|
| `src/vibemix/library/auto_crate.py` | Defines `AutoCrateResult.stop_reason` for keyless deterministic set-prep outcomes (`created`, `exported`, setup/no-pool/no-sequence failures). | Engine/DSP auto_crate front-door |

Any other source file that mentions `stop_reason` (in `src/vibemix/`,
recursive) still fails the gate. If it is Viber starvation plumbing, route
through the four-file Phase 99 surface. If it is a new observability producer
or consumer, update this whitelist with a plan/package justification instead
of silently spreading the field.

## Phase 100 carry-over

Plan 100-06 ships a sibling AST gate at
`tests/library/test_request_clarification_no_track_surface.py` that pins
the structural-safety property of the `request_clarification` handler
shipped in Plan 100-01 — no track_id surface, no grounding-state
mutation, single-trip semantics. The whitelist below
(`STOP_REASON_WHITELIST`) is UNCHANGED between Phase 99 and Phase 100
because Plan 100-03 added `clarification_needed` references inside the
same four whitelisted files (toolset.py, codex_curate.py, __main__.py,
telegram_bridge.py). A future plan that adds `clarification_needed`
references OUTSIDE these four files still trips Gate 3 below — the
whitelist gate is reason-agnostic.

`BASELINE_SEEN_ADD_COUNT` stays at 2 post-Phase 100. Plan 100-06's AST
gate has an explicit `test_baseline_seen_add_count_unchanged_post_phase_100`
test that mirrors this constant from outside `tests/repo/` — two-layer
defense: the tests/repo gate (Phase 99) and the tests/library gate
(Phase 100). A future PR that bumps the count must update BOTH constants
and explicitly justify the Cardinal Invariant #2 modification.

The `request_clarification` handler shipped by Plan 100-01 writes to
`self.stop_reason` once (the disambiguation terminal payload) and routes
through the same Phase 99 side-channel writer at `toolset.py:_write_side_channel`.
That extra write site is INSIDE `toolset.py` (the owner file), so it does
not affect Gate 3's whitelist — `toolset.py` is and stays the single
writer of `stop_reason`.

## Phase 100 + `_consecutive_empties` independence

Plan 100-06's AST gate
(`test_request_clarification_no_consecutive_empties_touch`) STRUCTURALLY
proves the clarification handler does not touch the starvation counter.
That's a sibling to Gate 2 below (which scopes `_consecutive_empties`
to `toolset.py` only): together they pin Decision 4 from CONTEXT.md —
the clarification terminal path reuses `self.stop_reason` as the
propagation seam without coupling to the starvation counter.

Run with: `PYTHONPATH=src python3 -m pytest tests/repo/test_no_seen_relaxation.py -q`
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "vibemix"
TOOLSET = SRC_ROOT / "library" / "toolset.py"

# Baseline `self.seen.add(` write sites in src/vibemix/library/toolset.py
# AFTER filtering out comment lines (lines whose first non-whitespace
# character is `#`). Sourced from Plan 99-03 SUMMARY's Grep gates section
# ("`self.seen.add` = 2 (UNCHANGED — Plan 99-05 baseline)"). If a future PR
# legitimately changes this number, bump the constant AND justify the
# Invariant-#2 change in the PR description. Do NOT bump silently.
BASELINE_SEEN_ADD_COUNT = 2

# Files allowed to mention `stop_reason` in `src/vibemix/`. See the
# whitelist tables in this module's docstring for the rationale per file.
# Stored as relative POSIX paths from REPO_ROOT for stable cross-platform
# comparison; the gate normalizes hits to the same form before set-checking.
STOP_REASON_WHITELIST: frozenset[str] = frozenset(
    {
        "src/vibemix/__main__.py",
        "src/vibemix/agent/dj_cohost.py",
        "src/vibemix/bench/respan.py",
        "src/vibemix/bench/run.py",
        "src/vibemix/debrief/drills.py",
        "src/vibemix/debrief/tldr.py",
        "src/vibemix/eval/session_report.py",
        "src/vibemix/learn/observability.py",
        "src/vibemix/library/auto_crate.py",
        "src/vibemix/library/codex_curate.py",
        "src/vibemix/library/telegram_bridge.py",
        "src/vibemix/library/toolset.py",
        "src/vibemix/runtime/ai_observability.py",
        "src/vibemix/state/deck_vision.py",
    }
)


def _toolset_exists() -> None:
    """Sanity guard — the gate is meaningless if the toolset file moved."""
    assert TOOLSET.is_file(), (
        f"Missing required source file at {TOOLSET.relative_to(REPO_ROOT)}. "
        "Phase 99 owns this file as the single writer of the starvation "
        "counter + `stop_reason` attribute. If it moved, update this gate's "
        "TOOLSET constant; do NOT skip the gate."
    )


def _grep_count_in_toolset_filtered(pattern: str) -> int:
    """Count occurrences of `pattern` in toolset.py after stripping comment lines.

    Uses Python str ops (not subprocess) so the gate is portable across the
    Mac BSD grep / Linux GNU grep split. Filtering rule: a "comment line" is
    one whose first non-whitespace character is `#`. Inline comments
    (`code  # note`) are NOT filtered — the load-bearing code on the line
    counts. This matches RESEARCH.md's hygiene rule + the 99-03 SUMMARY
    grep-gate posture (textual count == semantic count for the executable
    `self.seen.add(` form).
    """
    text = TOOLSET.read_text(encoding="utf-8")
    count = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if pattern in line:
            count += 1
    return count


def _find_src_files_with(pattern: str) -> set[str]:
    """Return the set of `src/vibemix/**/*.py` paths (relative to REPO_ROOT,
    POSIX) that contain `pattern` as a substring on at least one line.

    Uses `git grep -l` for speed + portability (no shell glob expansion
    quirks). Falls back to a Python walk if not in a git checkout. Skips
    `__pycache__` automatically (git ignores it).
    """
    # Try git grep first — faster on large trees, honors .gitignore.
    try:
        result = subprocess.run(
            ["git", "grep", "-l", "-F", "--", pattern, "src/vibemix"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in (0, 1):
            # 0 = matches found; 1 = no matches (also OK for our purposes).
            hits = {
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and line.strip().endswith(".py")
            }
            return hits
    except (FileNotFoundError, OSError):
        pass

    # Fallback: walk src/vibemix manually (e.g. running outside a git checkout).
    hits: set[str] = set()
    for path in SRC_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern in content:
            hits.add(str(path.relative_to(REPO_ROOT).as_posix()))
    return hits


# ---------------------------------------------------------------------------
# Gate 1 — Invariant #2 (citation grounding) seen-write count
# ---------------------------------------------------------------------------


def test_seen_writes_unchanged_from_baseline() -> None:
    """`self.seen.add(` write-site count in toolset.py must equal the
    pre-Phase-99 baseline (2; recorded in Plan 99-03 SUMMARY).

    Why this gate exists: `self.seen` is the per-run grounding seen-set
    that `create_playlist` validates against (gate #1 in
    `create_playlist` handler at `toolset.py:449`). Adding or removing a
    `self.seen.add` write site changes WHICH track_ids the model is
    allowed to cite in a `create_playlist` call — that's a direct
    modification of Cardinal Invariant #2 (citation grounding, CLAUDE.md
    § Cardinal Invariants).

    If this test fails on YOUR PR:
      1. Run `grep -n "self\\.seen\\.add" src/vibemix/library/toolset.py`
         to see the current write sites.
      2. Explain in your PR description WHY the seen-set surface changed
         and what hallucination class the new posture closes/opens.
      3. Bump `BASELINE_SEEN_ADD_COUNT` in this file to the new count.
         Note the date + your PR # in the comment above the constant.
      4. Update the Cardinal Invariants section of `CLAUDE.md` if the
         change affects the semantics of "single validated write".
    """
    _toolset_exists()
    count = _grep_count_in_toolset_filtered("self.seen.add(")
    assert count == BASELINE_SEEN_ADD_COUNT, (
        f"Cardinal Invariant #2 (citation grounding) seen-write count "
        f"in {TOOLSET.relative_to(REPO_ROOT)} drifted: expected "
        f"{BASELINE_SEEN_ADD_COUNT} (pre-Phase-99 baseline per Plan 99-03 "
        f"SUMMARY), got {count}. Run `grep -n 'self\\.seen\\.add' "
        f"{TOOLSET.relative_to(REPO_ROOT)}` to find the drifted site. If "
        f"intentional, see this test's docstring for the bump recipe."
    )


# ---------------------------------------------------------------------------
# Gate 2 — Invariant #1 (single-writer analog) for `_consecutive_empties`
# ---------------------------------------------------------------------------


def test_consecutive_empties_single_writer() -> None:
    """`_consecutive_empties` may appear ONLY in
    `src/vibemix/library/toolset.py`.

    Why this gate exists: the starvation counter is per-instance state on
    `LibraryToolset` (Decision 1, CONTEXT.md). Having other source modules
    read or write it would break the single-writer analog of Cardinal
    Invariant #1 — counter semantics would depend on cross-module
    interleaving rather than the dispatch-calling-thread serialization
    documented at `toolset.py:407-411`.

    Tests under `tests/` MAY reference `_consecutive_empties` for direct
    state assertions (that's the test-fixture posture established by
    `tests/library/test_toolset_starvation.py`). The gate scopes to
    `src/vibemix/` only.

    If this test fails on YOUR PR:
      - You added a `_consecutive_empties` mention in a non-toolset src
        file. That's Decision 1 violation.
      - Move the logic INTO `LibraryToolset` or use the public surface
        (`self.stop_reason` to detect terminal state — Decision 4).
    """
    hits = _find_src_files_with("_consecutive_empties")
    allowed = frozenset({"src/vibemix/library/toolset.py"})
    offenders = hits - allowed
    assert not offenders, (
        f"`_consecutive_empties` (Phase 99 Decision 1 — counter is "
        f"per-`LibraryToolset` instance state) leaked outside its owner "
        f"file. Allowed: {sorted(allowed)}. Found in: {sorted(hits)}. "
        f"Offending files: {sorted(offenders)}. Move the logic into "
        f"`LibraryToolset` or surface terminal state via "
        f"`self.stop_reason` (Decision 4 — the public propagation seam)."
    )


# ---------------------------------------------------------------------------
# Gate 3 — `stop_reason` propagation surface confinement
# ---------------------------------------------------------------------------


def test_stop_reason_writes_confined_to_toolset() -> None:
    """`stop_reason` may appear ONLY in explicitly authorized source files.

    Viber starvation whitelist (per this module's docstring table):
      * `src/vibemix/library/toolset.py` — owner
      * `src/vibemix/library/codex_curate.py` — wrapper + propagation seam
      * `src/vibemix/__main__.py` — CLI dispatch (pre-existing reads,
        plan 99-07 will add exit-code-10 branch)
      * `src/vibemix/library/telegram_bridge.py` — mobile format
        (pre-authorized for plan 99-06)

    Package 1A observability whitelist:
      * `src/vibemix/runtime/ai_observability.py` — shared row shape
      * `src/vibemix/agent/dj_cohost.py` — live-coach assistant rows
      * `src/vibemix/bench/run.py` — bench-cell rows
      * `src/vibemix/bench/respan.py` — read-only consumer: b9ed896b's
        actionability summary copies the `stop_reason` field out of judged
        bench-row targets into a bounded report dict (no writes, no Viber
        starvation logic)
      * `src/vibemix/state/deck_vision.py` — deck-vision rows
      * `src/vibemix/learn/observability.py` — Learn tutor rows
      * `src/vibemix/debrief/drills.py` — debrief drill rows
      * `src/vibemix/debrief/tldr.py` — debrief TLDR/TTS rows
      * `src/vibemix/eval/session_report.py` — report consumer
      * `src/vibemix/library/auto_crate.py` — deterministic keyless set-prep
        terminal result shape

    Why this gate exists: `stop_reason` is the Decision-4 propagation
    surface for Viber terminal run states AND a canonical AI-message
    observability field. Spreading Viber starvation handling across
    `agent/`, `intel/`, `runtime/`, etc. would still break the four-file
    contract; emitting canonical observability rows is separately authorized
    by Package 1A and must stay confined to the files named above.

    The gate uses a per-file existence check (NOT a count): it does not
    care HOW MANY times each whitelisted file mentions `stop_reason`,
    only whether any NON-whitelisted file mentions it. This stays
    PR-friendly when plans 99-06 / 99-07 land their reads (telegram /
    main) — the gate already accepts those files.

    If this test fails on YOUR PR:
      - You added a `stop_reason` reference in a non-whitelisted source
        file.
      - If this is Viber starvation handling, route through one of the
        four Phase 99 files.
      - If this is a new AI-message observability producer/consumer, justify
        the expansion in your PR description and add the new file to
        `STOP_REASON_WHITELIST` with a docstring update documenting WHICH
        plan/package authorized the change.
    """
    hits = _find_src_files_with("stop_reason")
    offenders = hits - STOP_REASON_WHITELIST
    assert not offenders, (
        f"`stop_reason` appeared in non-whitelisted source files. "
        f"Whitelist: {sorted(STOP_REASON_WHITELIST)}. Found in: "
        f"{sorted(hits)}. Offending files: {sorted(offenders)}. Either "
        f"route Viber starvation handling through the Phase 99 files, "
        f"or expand STOP_REASON_WHITELIST in this gate for a justified "
        f"observability producer/consumer (with a docstring update "
        f"naming the authorizing plan/package)."
    )


# ---------------------------------------------------------------------------
# Gate 4 — Phase 100 carry-over: request_clarification handler two-file pattern
# ---------------------------------------------------------------------------


# Allowed locations of `def request_clarification(` in `src/vibemix/`. The
# two-file pattern matches `search_vibe`, `find_similar`, etc.: the bound
# method lives in `toolset.py` and the FastMCP exposure wrapper lives in
# `mcp_server.py`. Plan 100-01 shipped the toolset.py handler; Plan 100-02
# shipped the mcp_server.py wrapper. Any THIRD definition is a duplication
# bug — the dispatch table is the single point of routing.
REQUEST_CLARIFICATION_DEF_ALLOWED: frozenset[str] = frozenset(
    {
        "src/vibemix/library/toolset.py",
        "src/vibemix/library/mcp_server.py",
    }
)


def test_request_clarification_handler_two_file_pattern() -> None:
    """`def request_clarification(` may appear ONLY in the two whitelisted
    source files (toolset.py = handler, mcp_server.py = FastMCP exposure).

    Why this gate exists: Plan 100-01 + Plan 100-02 land the handler and
    its FastMCP exposure, mirroring the search_vibe / find_similar /
    get_track_features two-file pattern. A future PR that copy-pastes the
    handler into a third file (e.g. agent/dj_cohost.py, runtime/wizard.py)
    breaks the single-dispatch-table contract — the clarification flow is
    owned by LibraryToolset, period.

    The behavioral pin (handler wired into the dispatch table) lives in
    Plan 100-01's tests/library/test_toolset_clarification.py. The FastMCP
    registration pin lives in Plan 100-02's
    tests/library/test_mcp_server_clarification.py. This gate is the
    structural complement: no third definition is allowed.
    """
    hits = _find_src_files_with("def request_clarification(")
    offenders = hits - REQUEST_CLARIFICATION_DEF_ALLOWED
    assert not offenders, (
        f"`def request_clarification(` appeared in non-whitelisted source "
        f"files. Allowed: {sorted(REQUEST_CLARIFICATION_DEF_ALLOWED)} "
        f"(handler in toolset.py + FastMCP exposure in mcp_server.py — "
        f"mirrors the search_vibe two-file pattern). Found in: "
        f"{sorted(hits)}. Offending files: {sorted(offenders)}. The "
        f"clarification flow is owned by LibraryToolset; duplicating the "
        f"definition elsewhere breaks the single-dispatch-table contract. "
        f"If you need to expose it via a new wrapper (e.g. WebSocket bridge), "
        f"add the new file to REQUEST_CLARIFICATION_DEF_ALLOWED with a "
        f"docstring update naming the authorizing plan."
    )
    # Sanity: the handler MUST exist in toolset.py at minimum (Plan 100-01).
    assert "src/vibemix/library/toolset.py" in hits, (
        "Plan 100-01's request_clarification handler is missing from "
        "src/vibemix/library/toolset.py. Either the handler was removed "
        "(Cardinal Invariant #2 violation — drop the clarification flow) "
        "or its name changed. Update this gate's lookup."
    )
