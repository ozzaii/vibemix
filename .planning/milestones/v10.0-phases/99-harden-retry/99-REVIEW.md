---
phase: 99-harden-retry
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/library/toolset.py
  - src/vibemix/library/codex_curate.py
  - src/vibemix/library/mcp_server.py
  - src/vibemix/library/telegram_bridge.py
  - src/vibemix/__main__.py
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: clean
fix_commits:
  - 6de3ac2f  # WR-01 __all__ export
  - 11bb45e8  # WR-02 stale comment rewrite
  - ec3757a5  # WR-03 _write_side_channel catch widen
---

# Phase 99 HARDEN-RETRY: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard (cross-file traced — toolset → codex_curate → mcp_server → CLI/Telegram)
**Files Reviewed:** 5 source files + 6 test files cross-checked
**Status:** issues_found (0 BLOCKER / 3 WARNING / 6 INFO)

## Summary

Phase 99 closes the Factor-9 partial cleanly. The architecture is sound — the side-channel-file propagation seam (Decision 4 + RESEARCH.md § Channel A) bypasses the LLM correctly, the counter writes are confined to the dispatch-calling thread per the documented serialization at `toolset.py:407-411`, and the threshold-trip short-circuit fires BEFORE `create_playlist`'s library re-validation (verified — `dispatch()` checks `self.stop_reason` at the top before any handler dispatch, including `create_playlist`).

**Cardinal Invariant #2 (citation grounding) verdict: HELD.** `self.seen.add` count is 2, unchanged from the pre-Phase-99 baseline (test_no_seen_relaxation.py:93 pins this). No new path mutates `self.seen`. The terminal short-circuit at `toolset.py:1134` runs BEFORE the handler dispatch table, so a starved `create_playlist` returns `{"error": "tool_starvation", "stop_reason": ...}` without ever touching the seen-set gate or the library re-validation. `tests/library/test_toolset_starvation.py::test_starvation_short_circuits_create_playlist` confirms with a RuntimeError sentinel on the module-bound `create_playlist` callable.

**Cardinal Invariant #1 (single-writer analog) verdict: HELD.** Counter writes are confined to `dispatch()` (one site at `toolset.py:1180/1200`), both AFTER `fut.result()` returns, on the dispatch-calling thread. The `with ThreadPoolExecutor(...)` block at 1160 exits and joins the worker before the counter update runs. The `_consecutive_empties` symbol exists ONLY in `toolset.py` (gate-pinned).

**Forward-compat for Phase 100:** every branch keys off `payload.get("reason") == "tool_starvation"` (codex_curate.py:539, 854; telegram_bridge.py:118; __main__.py:2664, 2715, 2939) — a sibling `elif payload.get("reason") == "clarification_needed"` drops in without restructuring. Confirmed.

**Anti-slop check on hint copy:** Cases A/B/C avoid "I apologize" / "Sorry, I cannot" / "As an AI". Wording is direct and actionable per Decision 5 seed.

The warnings below are pragmatic friction points worth fixing before ear-pass, not architectural failures. Info items are nits.

## Warnings

### WR-01: `TOOL_STARVATION_THRESHOLD` missing from `__all__` export

**File:** `src/vibemix/library/toolset.py:1333`
**Issue:** The module-level constant `TOOL_STARVATION_THRESHOLD` is defined at line 75 and explicitly documented as "tunable in tests via monkeypatch", but the module's `__all__` only declares `["TOOL_CALL_TIMEOUT_S", "LibraryToolset"]`. Test files import the constant via `from vibemix.library.toolset import TOOL_STARVATION_THRESHOLD` (RESEARCH.md § Pattern 4 scaffold) — this works at runtime because `__all__` only governs `from … import *`, but it means:

  1. Static analyzers / linters can flag the constant as "private / not part of the public API"
  2. A future refactor that respects `__all__` could prune the symbol without realizing tests + (per the test gate at `tests/repo/test_no_seen_relaxation.py:248`) the Decision-1 contract depend on it
  3. Inconsistent with Decision 3 ("module constant TOOL_STARVATION_THRESHOLD as the tunable surface") — if it's part of the contract, it should be exported

**Fix:**
```python
__all__ = ["TOOL_CALL_TIMEOUT_S", "TOOL_STARVATION_THRESHOLD", "LibraryToolset"]
```

### WR-02: Stale "scaffolding-only" comment in `LibraryToolset.__init__` contradicts shipped code

**File:** `src/vibemix/library/toolset.py:119-124`
**Issue:** The docstring above the counter attributes reads:
> "Phase 99 HARDEN-RETRY scaffolding (Plan 99-01, Decisions 1 + 4): per-run consecutive empty/error counter + terminal stop_reason surface. **Plan 99-02 wires the dispatch-site increment; Plan 99-03 writes the threshold-trip payload here. Pure scaffolding in this plan — no reads or writes anywhere else yet** (single-writer analog precondition for Cardinal Invariant #1)."

But `dispatch()` at lines 1125-1202 already does both the increment AND the threshold-trip write — the comment is from Plan 99-01 when this was scaffolding, but it survived through 99-02 / 99-03 without updating. Future readers will be confused looking for the "missing" wiring and may grep wrong.

**Fix:** Rewrite to reflect shipped state:
```python
# Phase 99 HARDEN-RETRY (Plans 99-01..04, Decisions 1 + 4):
# per-run consecutive empty/error counter + terminal stop_reason surface.
# Counter is incremented + threshold-tripped inside ``dispatch()`` below
# (the SINGLE writer site, on the dispatch-calling thread — see
# toolset.py:407-411 serialization analog for the safety argument).
# Side-channel file propagation rides ``_write_side_channel`` (env-var
# gated, no-op when absent).
self._consecutive_empties: int = 0
self.stop_reason: dict[str, Any] | None = None
```

### WR-03: `_write_side_channel` silently swallows `UnicodeEncodeError` / non-OSError IO failures

**File:** `src/vibemix/library/toolset.py:1100-1105`
**Issue:** The try/except catches only `OSError`. `json.dump(payload, f)` can raise `TypeError` if the payload contains a non-JSON-serializable value (theoretically impossible today — `_build_starvation_payload` only returns str/int/str-keyed dicts — but the contract is "any future addition to the payload could break this"). More practically, on some platforms a write to a path with a non-UTF-8-compatible filename or content can raise `UnicodeEncodeError` (subclass of `ValueError`, NOT `OSError`) and would propagate up into `dispatch()` — which the docstring promises is the most defensive surface in the file ("never wedge dispatch on FS issues").

The comment says "Best-effort — never wedge dispatch on FS issues" but the implementation only delivers on the `OSError` part of that promise.

**Fix:** Widen the catch to match the contract:
```python
try:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
except (OSError, TypeError, ValueError):
    # Best-effort — never wedge dispatch on FS / encoding / serialization issues.
    return
```
Or use `Exception` with a logged warning since this is observability-only — the in-process `self.stop_reason` is the authoritative surface (per the existing docstring), so an over-broad catch here is safer than letting an unexpected exception escape and corrupt the dispatch return path.

## Info

### IN-01: B1 startup probe in `mcp_server.py` emits an unconditional stderr line on every MCP subprocess boot

**File:** `src/vibemix/library/mcp_server.py:71-76`
**Issue:** The Plan 99-04 / B1 probe `print(f"[viber-mcp] VIBEMIX_STOP_REASON_FILE=...", file=sys.stderr, flush=True)` runs on every MCP subprocess startup. The comment correctly identifies this as a Phase-99 observability checkpoint, but:
  1. The path it logs (e.g. `/var/folders/.../viber-codex-XXXX/stop_reason.json`) is a transient temp path — not a leak in the security sense, but it does pollute `stderr` on every legitimate run including non-curation MCP-tool dev work
  2. There's no plan-tracked sunset comment for when this probe gets removed (the comment says "fix lands as HARDEN-FUTURE" but doesn't pin the removal)

**Fix:** Add a TODO with the verification milestone:
```python
# TODO(HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY): remove after the first real
# Codex run confirms env-var crosses the wrapper → Codex CLI → MCP-child
# boundary. Until verified, keep noisy.
```
Or gate behind `VIBEMIX_DEBUG_MCP` env var so soak runs stay quiet.

### IN-02: User-supplied `theme` interpolated into hint without newline / control-char sanitization

**File:** `src/vibemix/library/toolset.py:1053-1057`
**Issue:** Case B builds `hint = f"no tracks matched '{theme}' — try a broader theme or different BPM range"` where `theme` is `args.get("query", "")` — raw user input from Codex's tool call. A theme containing `'\n[viber] ROOT compromised\n'` would render as a multi-line stderr line in the CLI output (`__main__.py:2666`). The Telegram surface scrubs only filesystem paths via `strip_leaks(_PATH_RE)` (telegram_bridge.py:59) — newlines and control chars pass through.

Not a security vulnerability (the theme comes from the agent's tool args, ultimately from the user's own prompt — there's no privilege boundary being crossed), but it does enable log-injection / UI-injection cosmetics. The Telegram message would show extra lines that look like additional bot output.

**Fix:** Strip control chars before interpolation:
```python
theme = args.get("query", "")
if isinstance(theme, str):
    theme = "".join(ch for ch in theme if ch.isprintable())[:80]
else:
    theme = ""
hint = (
    f"no tracks matched '{theme}' — try a broader theme or "
    f"different BPM range"
)
```

### IN-03: `_write_side_channel` does no path-traversal validation on `VIBEMIX_STOP_REASON_FILE`

**File:** `src/vibemix/library/toolset.py:1097`
**Issue:** The toolset writes to whatever path the env var names. In production, the wrapper allocates the path via `tempfile.TemporaryDirectory(prefix="viber-codex-")` (codex_curate.py:454), so the path is trusted. But the toolset doesn't validate this — if `VIBEMIX_STOP_REASON_FILE` is set to `/etc/passwd` or `~/.ssh/authorized_keys` by an attacker who can already set env vars on the MCP subprocess, the toolset would clobber that file with the JSON payload.

This is defense-in-depth — an attacker with env-var control on the subprocess already has many other paths to file write. RESEARCH.md acknowledges the path is "internal CLI↔MCP plumbing, not user-facing config" (line 326). Worth a code comment so a future security review doesn't have to re-derive the trust boundary.

**Fix:** Add an explicit trust-boundary comment, optionally a sanity guard:
```python
def _write_side_channel(self, payload: dict[str, Any]) -> None:
    """[…existing docstring…]

    SECURITY: the env var path is trusted — it is allocated by the wrapper
    inside ``tempfile.TemporaryDirectory`` (codex_curate.py:454, 779). The
    MCP subprocess is spawned by Codex with the wrapper's env, so an
    attacker who could set this env var already has direct subprocess
    access via the same boundary.
    """
    path = os.environ.get("VIBEMIX_STOP_REASON_FILE")
    if not path:
        return
    # Defense in depth: refuse paths outside a tempdir prefix to limit
    # blast radius if a future caller forgets to allocate via tempfile.
    if not path.startswith(("/tmp/", "/var/folders/", tempfile.gettempdir())):
        return
    ...
```
(Optional — the project's hard-rule on shipping data home would catch a regression here too.)

### IN-04: `payload` variable name reused inside the same function (side-channel JSON vs codex out.json)

**File:** `src/vibemix/library/codex_curate.py:534, 564, 849, 876`
**Issue:** In both `curate_with_codex` and `build_set_with_codex`, `payload` is the name used for both the side-channel JSON parse (line 534/849) AND the Codex out.json parse (line 564/876). The first reads, checks `reason`, returns or falls through. The second reassigns. The variable from the first is not used downstream (the return inside the conditional captures both cases), so there's no actual leak — but a future developer adding code between the two parses could inadvertently reference the wrong `payload`.

**Fix:** Rename for clarity:
```python
if Path(stop_reason_path).exists():
    try:
        side_payload = json.loads(
            Path(stop_reason_path).read_text(encoding="utf-8")
        )
        if (
            isinstance(side_payload, dict)
            and side_payload.get("reason") == "tool_starvation"
        ):
            return CodexCurateResult(
                theme=theme,
                stop_reason="tool_starvation",
                error=str(side_payload.get("hint") or "..."),
            )
    except (OSError, json.JSONDecodeError):
        pass
```

### IN-05: `tool_starvation` not added to the `_STOP_REASONS` enumeration comment block

**File:** `src/vibemix/library/codex_curate.py:221-231`
**Issue:** The comment block at lines 221-231 enumerates stop-reason values. `tool_starvation` IS listed (lines 227-230), but the docstring says "see `_STOP_REASONS` below" while the actual symbol is the comment block, not a code-level enum. This is a pre-existing pattern, but it means linters / IDE tooling cannot autocomplete the legal values. Decision 6 reserves 10-19 for stop-reason codes; a Python `Literal["created", "tool_starvation", ...]` annotation on `CodexCurateResult.stop_reason: str` would make the contract machine-checkable.

**Fix (optional, for forward-compat with Phase 100):**
```python
from typing import Literal

STOP_REASON = Literal[
    "created", "exported", "codex_not_installed", "codex_auth_required",
    "codex_mcp_blocked", "timeout", "empty_output", "no_playlist",
    "tool_starvation", "error",
]

@dataclass(slots=True)
class CodexCurateResult:
    theme: str
    stop_reason: STOP_REASON
    ...
```

### IN-06: `_normalize_codex_curate_result` returns `dict | None` but contract says `dict`-or-fallthrough

**File:** `src/vibemix/__main__.py:2917-2945`
**Issue:** The helper returns `None` for non-starvation results, signaling "fall through to existing behavior" to the caller. The caller at `__main__.py:2990-2992` checks `if normalized is not None: return normalized`. This works but the Optional return type pattern is non-obvious — `None` here means "no normalization needed", not "normalization failed". A reader hitting this for the first time might assume None = error.

**Fix:** Document the return semantics more aggressively, OR use a sentinel return:
```python
def _normalize_codex_curate_result(
    result: CodexCurateResult,
) -> dict | None:
    """[…existing docstring…]

    Return semantics:
      - dict: the normalized payload for ``format_reply`` (caller MUST return).
      - None: "no normalization — caller should fall through to its existing
              happy-path / generic-error branches" (NOT an error signal).
    """
```
The current docstring does cover this, but burying "Plan 99-06 / Decision 8" jargon makes it harder to spot. The clarity could be sharper.

---

## Structural / Cross-File Verification

Confirmed by direct read (not re-listed as findings — clean):

1. **Counter writes confined to dispatch-calling thread** — `toolset.py:1160-1167` opens `with ThreadPoolExecutor`, calls `fut.result()`, exits `with` block, THEN runs `_is_empty_or_error` + counter logic. Worker is joined. No race.
2. **Terminal short-circuit fires before `create_playlist` handler** — `toolset.py:1134-1135` checks `self.stop_reason is not None` BEFORE the handler dispatch table. `create_playlist`'s `seen` re-validation never runs after starvation. `tests/library/test_toolset_starvation.py:650+` pins this with a RuntimeError sentinel.
3. **Side-channel file lifecycle correct** — `codex_curate.py:454-579` and `:774-888` both keep the side-channel read INSIDE the `with tempfile.TemporaryDirectory(...)` block. Pitfall 4 avoided.
4. **First-write-wins idempotence** — `toolset.py:1192-1194` guards with `self.stop_reason is None`. The threshold-trip block runs once per run.
5. **Telegram fall-through ordering** — `format_reply` at `telegram_bridge.py:118` checks `tool_starvation` BEFORE the generic `if not norm.get("ok")` branch. The starvation payload's `ok=False` wouldn't shadow it.
6. **Test gate enforces invariants** — `tests/repo/test_no_seen_relaxation.py` pins (a) `self.seen.add` count = 2, (b) `_consecutive_empties` only in toolset.py, (c) `stop_reason` only in 4 whitelisted files. All three gates pass on current source.
7. **Forward-compat for Phase 100 (`clarification_needed`)** — every branch keys off `payload.get("reason")` string match; a sibling `elif` lands cleanly. Confirmed at codex_curate.py:539, 854; telegram_bridge.py:118; __main__.py:2664, 2715, 2939.
8. **`from __future__ import annotations` present** — `__main__.py:30`, so the `TYPE_CHECKING`-only `CodexCurateResult` annotation at line 2918 is safe.

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
