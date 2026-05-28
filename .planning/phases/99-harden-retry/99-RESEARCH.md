# Phase 99: HARDEN-RETRY — Viber Tool-Retry Policy (Factor 9) - Research

**Researched:** 2026-05-28
**Domain:** Viber/Codex tool-dispatch hardening — counter + terminal stop_reason payload + CLI exit codes + uniform propagation
**Confidence:** HIGH (every claim verified against current source by file:line reads in this session)

## Summary

Phase 99 closes the Factor-9 partial in the 2026-05-28 12-factor-agents audit by giving `LibraryToolset` an additive per-instance error counter and a sibling `self.stop_reason: dict | None` attribute. After N=3 consecutive empty `search_vibe` / `{"error": ...}` tool returns, the toolset emits a terminal `tool_starvation` payload that propagates uniformly to CLI (exit 10), Telegram (`format_reply` branch), and GUI consumers via `CodexCurateResult.stop_reason`.

The whole change is **disjoint from every active parallel session** (LiveKit handoff in `__main__.py:1353`, frontend wiring in `tauri/ui/*`, Codex sessions doing additive new-file product-sweep work). The two `__main__.py` lines that change (`_cmd_library_curate_codex` dispatch table at `__main__.py:2547-2555` and `_cmd_library_build_set_codex` dispatch table at `__main__.py:2593-2601`) are nowhere near the LiveKit live-session block at `__main__.py:1353`. Surgical, named-path commits per `feedback_concurrent_sessions_one_tree` — never `git add -A`.

The most load-bearing technical decision in this phase is **how the toolset's `stop_reason` crosses the MCP STDIO subprocess boundary back to `curate_with_codex`**. The toolset lives inside the MCP server subprocess (`library/mcp_server.py:65-81 build_toolset`); the wrapper only sees Codex's `--output-schema`-enforced `out.json` (`codex_curate.py:507-525`). Research-recommended seam: **side-channel file passed via env var** (`VIBEMIX_STOP_REASON_FILE`) — bypasses the LLM entirely (the model cannot elide what it never sees), zero schema changes, additive, forward-compatible with Phase 100's sibling `clarification_needed` payload.

**Primary recommendation:** Add `_consecutive_empties: int = 0` + `stop_reason: dict | None = None` to `LibraryToolset.__init__`. Inside `dispatch()` AFTER `fut.result()` (so the write is on the dispatch-calling thread, never the handler thread — critical to avoid the race documented at `toolset.py:407-411`), inspect the return value and update the counter. On threshold-trip, set `self.stop_reason` AND write the payload to `VIBEMIX_STOP_REASON_FILE` if present. Wrapper reads the file after Codex exits; CLI branches on the result's `stop_reason`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Decision 1 — Counter location:** `LibraryToolset` instance attribute (`self._consecutive_empties: int = 0`), mirroring the lifetime of `self.seen` / `self.seen_sections` / `self.issued_*`. One instance == one curation run, so counter scope == run scope.

**Decision 2 — What increments the counter:** Both (a) `search_vibe` returning zero candidates, AND (b) any handler returning `{"error": ...}` from the dispatch table. Counter resets on any successful non-empty tool return.

**Decision 3 — Threshold N:** `TOOL_STARVATION_THRESHOLD = 3` as a module constant in `library/toolset.py`. Tunable.

**Decision 4 — Stop-reason surface:** New instance attribute `self.stop_reason: dict | None = None` on `LibraryToolset`. When the counter hits the threshold, the next `dispatch()` call writes `self.stop_reason = {"reason": "tool_starvation", "hint": "...", "tool": "<last_tool_name>"}` and returns it directly. Mirrors the existing `self.created` / `self.exported` attribute-as-result-spine.

**Decision 5 — Hint generation policy:** Deterministic, generated from the toolset's view of the world at threshold-trip time. Three named cases:
- Library has zero tracks → `"library has 0 tracks — run \`library ingest\` first"`
- Library has tracks but `search_vibe` returned zero on the run's theme → `"no tracks matched '<theme>' — try a broader theme or different BPM range"`
- Repeated tool-error → `"tool '<name>' kept failing — try again or check codex installation"`

**Decision 6 — CLI exit codes:** `exit code 10` for `tool_starvation`. Reserved range: 10-19 for terminal `stop_reason` codes (10=tool_starvation, 11=clarification_needed (Phase 100), 12-19=future). Existing code path keeps using 1 for unhandled errors and 0 for success.

**Decision 7 — Test seam:** Unit-test `LibraryToolset` directly with fake `embedder` / `store` / `library` objects. The counter/threshold/stop_reason logic lives in the toolset, so the Codex CLI never needs to be present. Codex propagation is covered with the existing `_runner` injection seam in `codex_curate.py:392`.

**Decision 8 — Telegram propagation:** `format_reply` adds a `tool_starvation` branch alongside the existing playlist + error branches. Renders the hint via `strip_leaks` (privacy preserved).

### Claude's Discretion

CONTEXT.md auto-resolved every grey area via `--auto` (default-YES on grey-area per `gsd-autonomous fully`). The remaining unresolved technical question is **stop_reason propagation channel** (toolset-in-subprocess → wrapper-in-parent), which CONTEXT.md punts to research. See `## Stop-Reason Propagation Channel` below — **recommended: env-var-passed side-channel file** (additive, schema-free, bypasses LLM, forward-compat for Phase 100).

### Deferred Ideas (OUT OF SCOPE)

- Telemetry / metrics on starvation rate (deferred to future telemetry milestone; CLAUDE.md privacy hard-rule rules out shipping data home anyway).
- Auto-retry with broadened theme (violates 12-factor-agents Factor 9 "self-healing trap").
- `tool_starvation` recovery loop (multi-turn) — DEFERRED to HARDEN-FUTURE-01.
- Hint copy A/B testing — deferred to post-launch ear-pass + KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARDEN-RETRY-01 | `LibraryToolset` tracks consecutive empty `search_vibe` / tool-error responses via additive per-instance counter | Counter location verified at `toolset.py:94-111` (mirrors `self.seen`, `self.created`, `self.exported`). Insertion site: `__init__` after `self.exported` line 105. |
| HARDEN-RETRY-02 | After N consecutive empty/error tool calls (default 3), toolset surfaces terminal `stop_reason="tool_starvation"` payload readable by `codex_curate` | Counter-update site identified at `dispatch()` post-`fut.result()` line 1009 (calling thread, NOT handler thread — see thread-race analysis below). Module constant `TOOL_STARVATION_THRESHOLD = 3` placement: top of file near existing `TOOL_CALL_TIMEOUT_S = 30.0` line 65. |
| HARDEN-RETRY-03 | Payload carries actionable user-facing hint identifying root cause (empty library / no theme match / specific tool starving) | Three-case hint generator: library-has-zero-tracks → check via `len(self._library.tracks) == 0` (verified API at `rekordbox.py` — `self.tracks: dict[str, TrackEntry]`); no-theme-match → triggered when last tool was `search_vibe` with empty results; tool-error → triggered when last tool returned `{"error": ...}` 3x in a row. The hint string is the union surface — see `## Hint Generation Logic` below. |
| HARDEN-RETRY-04 | CLI `library curate` and `library build-set` exit with non-zero status on `tool_starvation`, distinct from "no playlist found" | Exact CLI exit-code dispatch sites identified: `__main__.py:2545-2556` (`_cmd_library_curate_codex` hint dict + `return 1`) and `__main__.py:2591-2602` (`_cmd_library_build_set_codex` hint dict + `return 1`). Surgical change: replace `return 1` with case-dispatch `return 10 if result.stop_reason == "tool_starvation" else 1`. |
| HARDEN-RETRY-05 | Cardinal Invariant #2 holds — counter is additive telemetry; never relaxes `seen` grounding gate or `create_playlist` library re-validation; writes confined to handler-entry/exit sites | Verified: counter writes will live ONLY inside `dispatch()` (one site). The `create_playlist` two-gate validation (`toolset.py:431-444` seen-set + `create_playlist.py:60+` library re-validation) is structurally untouched. A starvation termination short-circuits BEFORE any write because `dispatch()` is the only path to write tools. AST gate spec: `tests/repo/test_no_seen_relaxation.py` (NEW) — grep that `self.seen.add(` count is unchanged from baseline, and no new `seen` write sites appear outside `search_vibe` / `discover_pool`. |
| HARDEN-RETRY-06 | Failing-then-passing tests cover: zero-track library, narrow theme zero-hits, dispatch-error path counter inc, counter reset on success, interaction with `create_playlist` (starvation short-circuits before partial write) | Test seam parity: existing `tests/library/test_toolset.py:148-170` fixture (`library`, `toolset`) is the canonical posture to mirror; new file `tests/library/test_toolset_starvation.py` reuses it via shared `conftest.py` or direct copy. |
| HARDEN-RETRY-07 | `curate_with_codex` and `build_set_with_codex` parse `tool_starvation` from MCP tool output and propagate to `CodexCurateResult.stop_reason` so callers (CLI + Telegram + GUI) see uniform terminal stop_reason | Propagation seam: `CodexCurateResult.stop_reason: str` already exists at `codex_curate.py:206` with the `_STOP_REASONS` comment block at lines 221-227 enumerating the known values. Add `tool_starvation` to the documented set. Wrapper-side detection via side-channel file (see `## Stop-Reason Propagation Channel`). The CLI branch in `__main__.py:2545-2556` already type-switches on `result.stop_reason` via a dict — additive hint entry only. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Counter increment + threshold detection | Toolset (Python, in-process — but lives inside MCP subprocess child) | — | Mirrors per-run grounding state (`seen`, `created`, `exported`) at `toolset.py:94-105`. One instance == one curation run. |
| Stop-reason payload generation | Toolset | — | Deterministic case-based generation (Decision 5). No LLM input — Invariant #2 extended. |
| Stop-reason cross-process propagation | Wrapper (`codex_curate.py`) | Side-channel file (env-var-passed temp path) | Toolset is in the MCP subprocess; wrapper is in parent. Codex's `--output-schema` JSON is LLM-controlled and can elide fields. File-channel bypasses the LLM. |
| CLI exit-code emission | CLI dispatcher (`__main__.py:2545-2611`) | — | The exit-code switch is at the seam where `result.stop_reason` is already type-dispatched. Single dict-lookup change per command. |
| User-facing hint rendering (Telegram) | Telegram bridge (`format_reply` at `telegram_bridge.py:107-124`) | `strip_leaks` (existing privacy scrubber) | Privacy rule: hint may carry library state; `strip_leaks` scrubs FS paths regardless. |
| User-facing hint rendering (CLI stderr) | `_cmd_library_curate_codex` hint dict (`__main__.py:2547-2555`) | — | The hint copy was seeded by Decision 5; KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS polishes. |
| GUI surfacing | `CodexCurateResult.to_dict()` (`codex_curate.py:217-218`) | Tauri bridge in `tauri/ui/*` (NOT TOUCHED — separate handoff) | Result dict already serializes `stop_reason`. Frontend handoff will consume in its own session. |

## Standard Stack

### Core (already in-tree — zero new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `concurrent.futures.ThreadPoolExecutor` | stdlib | Per-tool timeout (existing `toolset.py:1006-1013`) | Already the dispatch executor — counter writes co-locate on the same thread as `fut.result()` (the calling thread, not the worker) |
| Python `typing` | stdlib | `dict | None` for `stop_reason` attribute | Existing convention (see `self.created: PlaylistResult | None` at `toolset.py:101`) |
| `tempfile` + `os.environ` | stdlib | Side-channel file for cross-subprocess propagation | Same pattern `codex_curate.py:450 tempfile.TemporaryDirectory` already uses for `schema.json` / `out.json` |
| `pytest` 8.x | dev dep | Test framework | Existing — `pyproject.toml [tool.pytest.ini_options]` |
| `subprocess.CompletedProcess` (fake) | stdlib | `_runner` injection seam — already at `codex_curate.py:392` | Existing test posture in `tests/library/test_codex_curate.py:61-70` (`_runner_writing` helper) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Side-channel file (recommended) | Schema-extension (add `stop_reason`/`hint` fields to `_OUTPUT_SCHEMA` / `_BUILD_SET_SCHEMA`) | Schema-extension forces the LLM to surface the field. OpenAI strict mode requires every property in `required` (see `codex_curate.py:189-198` comment) — would require careful schema design. **Rejected:** LLM can refuse / elide / hallucinate the field; file-channel survives any LLM behavior. |
| Side-channel file | Sentinel-string in `error` field parsed by wrapper | Brittle — relies on string parsing; mixes telemetry with error transport; future-incompatible with Phase 100's sibling. |
| Side-channel file | Custom `ToolStarvationError` raise in handlers | Violates `library/toolset.py` module docstring contract ("handlers RETURN error dicts — they never raise"). |
| `int` counter on `LibraryToolset` | `dataclass RetryContext` passed between handlers | Adds plumbing for no gain; existing toolset state pattern is plain attributes. |
| `TOOL_STARVATION_THRESHOLD = 3` (module constant) | Env-var configurable | Decision 3 explicitly picked module constant. Env-var would invite production-vs-test drift; constant is testable in-place via `monkeypatch.setattr(toolset_mod, "TOOL_STARVATION_THRESHOLD", 2)`. |

**Installation:** No new packages — zero install commands. This phase is a pure-code change inside existing modules.

**Version verification:** N/A — no new third-party deps. Existing stdlib usage verified at file:line above.

## Package Legitimacy Audit

> **Not applicable** — this phase adds zero external packages. All work uses stdlib + existing in-tree modules (`vibemix.library.*`).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | N/A — zero new deps |

## Architecture Patterns

### System Architecture Diagram

```
                   ┌──────────────────────────────────────────────┐
                   │  PARENT PROCESS (vibemix CLI / Telegram)    │
                   │                                              │
                   │  _cmd_library_curate_codex()                 │
                   │    │                                         │
                   │    ▼                                         │
                   │  curate_with_codex(theme, lib)              │
                   │    │                                         │
                   │    ├── alloc tempfile: stop_reason.json    │ ◄── NEW seam (P99)
                   │    ├── env["VIBEMIX_STOP_REASON_FILE"]=path│
                   │    │                                         │
                   │    ▼ subprocess.run(["codex","exec",...])   │
                   └──────────────┬───────────────────────────────┘
                                  │ STDIO
                   ┌──────────────▼───────────────────────────────┐
                   │  codex exec (Codex's harness; bypass-sandbox)│
                   │                                              │
                   │  spawn MCP server STDIO child:               │
                   │    python -m vibemix.library.mcp_server      │
                   │                                              │
                   │                ┌──────────────────────────┐  │
                   │                │ MCP SUBPROCESS           │  │
                   │                │                          │  │
                   │   ┌────────────│  build_toolset() →       │  │
                   │   │  read      │  LibraryToolset instance │  │
                   │   │  env var ──┤    .seen, .stop_reason   │  │ ◄── NEW attrs (P99)
                   │   │            │    ._consecutive_empties │  │
                   │   │            │                          │  │
                   │   │            │  FastMCP tools loop:     │  │
                   │   │            │    dispatch(name, args)  │  │
                   │   │            │     ├─ handler in thread │  │
                   │   │            │     ├─ fut.result()      │  │
                   │   │            │     ├─ counter update   ◄┼──┼── HOOK (P99)
                   │   │            │     └─ if threshold:     │  │
                   │   │            │         set stop_reason  │  │
                   │   │            │         WRITE FILE  ◄────┼──┼── side-channel
                   │   │            │                          │  │
                   │   ▼            └──────────────────────────┘  │
                   │  /tmp/.../stop_reason.json (if written)      │
                   └──────────────┬───────────────────────────────┘
                                  │
                   ┌──────────────▼───────────────────────────────┐
                   │  PARENT: after codex exec returns            │
                   │                                              │
                   │  if stop_reason_file exists and non-empty:  │
                   │    payload = json.loads(file)               │
                   │    return CodexCurateResult(                │
                   │      stop_reason="tool_starvation",         │
                   │      error=payload["hint"],                 │
                   │      ...                                     │
                   │    )                                         │
                   │                                              │
                   │  _cmd_library_curate_codex receives result:  │
                   │    exit code dispatch:                       │
                   │      tool_starvation → exit 10               │
                   │      created        → exit 0                 │
                   │      no_playlist    → exit 1                 │
                   │      timeout        → exit 1                 │
                   │      ...                                     │
                   └──────────────────────────────────────────────┘
```

**Key invariant preserved:** the side-channel file path is allocated by the WRAPPER and passed via env var. The MCP subprocess (toolset) writes; the wrapper reads. Neither the LLM nor Codex's harness sees, controls, or can elide the file's contents.

### Recommended File Touch Map (surgical, named-path)

```
src/vibemix/library/toolset.py    # +counter attrs, +threshold constant, +dispatch hook
src/vibemix/library/codex_curate.py    # +side-channel file alloc + env var + read + result wiring
                                  #  in BOTH curate_with_codex and build_set_with_codex
src/vibemix/library/mcp_server.py    # +read VIBEMIX_STOP_REASON_FILE env var, pass to LibraryToolset
src/vibemix/library/telegram_bridge.py    # +format_reply tool_starvation branch
src/vibemix/__main__.py    # +exit-code dispatch in 2 CLI handler hint dicts (10 lines total)
tests/library/test_toolset_starvation.py    # NEW: counter, threshold, hint generation, reset
tests/library/test_toolset_starvation_concurrency.py    # NEW: acid test (parallel dispatch monotonic)
tests/library/test_codex_curate_stop_reason.py    # NEW: propagation via _runner + side-channel
tests/library/test_telegram_bridge.py    # EXTEND: format_reply tool_starvation branch
tests/library/test_cli_exit_codes.py    # NEW: exit 10 dispatch
```

### Pattern 1: Instance-attribute-as-terminal-result

**What:** Adding `self.stop_reason: dict | None = None` to `LibraryToolset.__init__` follows the EXACT pattern already used for `self.created` (`toolset.py:101`) and `self.exported` (`toolset.py:105`).

**When to use:** Always for per-run terminal results in vibemix's toolset.

**Example:**
```python
# Source: src/vibemix/library/toolset.py:101-111 (existing, verified)
self.created: PlaylistResult | None = None
self.exported: ExportResult | None = None
# ... add HERE for Phase 99:
self._consecutive_empties: int = 0
self.stop_reason: dict[str, Any] | None = None
```

### Pattern 2: Dispatch-table extension (additive hint dict)

**What:** The CLI handlers ALREADY dispatch on `result.stop_reason` via dict-lookup at `__main__.py:2547-2555`:

```python
# Source: src/vibemix/__main__.py:2547-2556 (existing, verified)
hint = {
    "codex_not_installed": (...),
    "codex_auth_required": "Run `codex login`...",
    "timeout": "Codex took too long — try a narrower theme.",
}.get(result.stop_reason, result.error or "no playlist created")
print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
return 1
```

Phase 99 change: add `"tool_starvation"` entry to the hint dict and replace `return 1` with a tiny dispatch:

```python
# Phase 99 surgical edit:
hint = {
    "codex_not_installed": (...),
    "codex_auth_required": "...",
    "timeout": "...",
    "tool_starvation": result.error or "no playlist (tool starvation)",  # NEW
}.get(result.stop_reason, result.error or "no playlist created")
print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
return 10 if result.stop_reason == "tool_starvation" else 1  # NEW
```

### Pattern 3: Side-channel file via tempfile + env var

**What:** Mirrors the EXACT pattern already used in `codex_curate.py:450-453`:
```python
# Source: src/vibemix/library/codex_curate.py:450-453 (existing, verified)
with tempfile.TemporaryDirectory(prefix="viber-codex-") as td:
    schema_path = str(Path(td) / "schema.json")
    out_path = str(Path(td) / "out.json")
    Path(schema_path).write_text(json.dumps(_OUTPUT_SCHEMA), encoding="utf-8")
```

Phase 99 extension: alloc `stop_reason_path = str(Path(td) / "stop_reason.json")`, pass to MCP via env, read after Codex exits.

**Example:**
```python
# Phase 99 — inside curate_with_codex, BEFORE the _runner call:
stop_reason_path = str(Path(td) / "stop_reason.json")
env = build_subprocess_env(codex)
env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path  # propagated to MCP subprocess

# ... existing _runner call with env=env (env was already built)

# AFTER _runner returns, BEFORE parsing out.json:
if Path(stop_reason_path).exists():
    try:
        payload = json.loads(Path(stop_reason_path).read_text(encoding="utf-8"))
        if payload.get("reason") == "tool_starvation":
            return CodexCurateResult(
                theme=theme,
                stop_reason="tool_starvation",
                error=payload.get("hint", "Viber ran out of grounded options."),
            )
    except (OSError, json.JSONDecodeError):
        pass  # fall through — never wedge on a malformed side-channel file
```

### Pattern 4: Test seam mirroring (fixture parity)

**What:** Existing `tests/library/test_toolset.py:148-170` defines the canonical `library` + `toolset` fixtures + `_stub_search` helper. New test files must reuse, not redefine.

**Example test file scaffold:**
```python
# tests/library/test_toolset_starvation.py (NEW)
from vibemix.library.toolset import LibraryToolset, TOOL_STARVATION_THRESHOLD
from vibemix.library import toolset as tool_mod

def test_counter_resets_on_successful_nonempty_search(toolset, monkeypatch):
    # reuse existing fixture; reuse existing _stub_search posture
    ...

def test_threshold_trip_sets_stop_reason(toolset, monkeypatch):
    monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 2)
    # ... fire 2 empty searches; assert toolset.stop_reason is not None
```

### Anti-Patterns to Avoid

- **Writing the counter inside the handler thread:** `toolset.py:407-411` explicitly documents the lazy-init race-avoidance pattern (`_genre_lookup` lazy-init is safe ONLY because dispatch serializes). The counter is safe for the SAME reason — but ONLY if writes happen AFTER `fut.result()` returns to the calling thread. Writing inside `search_vibe`'s body would race a future concurrent dispatcher.
- **Hardcoding `consecutive_empties=3` in a comparison instead of using the module constant:** breaks test monkeypatching.
- **Returning stop_reason via Codex's `--output-schema`:** the LLM can drop the field. The side-channel file bypasses the LLM entirely.
- **Modifying `self.seen` writes:** Cardinal Invariant #2. Counter is ADDITIVE; never relax the grounding gate.
- **Forgetting to reset the counter on `search_vibe` success-with-results:** the spec is "consecutive", not "cumulative". A single non-empty search resets to 0.
- **Coupling the counter to specific tool names beyond `search_vibe`:** ALL handler returns of `{"error": ...}` count — `get_track_features` errors, `discover_pool` errors, etc. (Decision 2 locked).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-subprocess message passing | Custom RPC channel / shared memory / new socket | Side-channel file via env var + `tempfile.TemporaryDirectory` | Already the project's pattern (`schema.json` / `out.json` at `codex_curate.py:450`). One-socket invariant #4 preserved. Zero new ports. |
| Thread-safe counter | `threading.Lock` / `threading.RLock` | NOTHING — dispatch already serializes | `toolset.py:407-411` documents the existing serialization guarantee: "dispatch serializes tool calls within a run." Counter writes co-located on the calling thread are race-free by construction. |
| Stop-reason serialization | Custom protocol / pickling / msgpack | Plain JSON dict via `json.dumps` / `json.loads` | Already the project's pattern (every result dict, every IPC envelope). |
| Hint string formatting | LLM call / template engine / i18n framework | f-string with three named cases | Deterministic copy is testable + ear-passable; LLM-generated violates Invariant #2-extended to curation. |
| Exit-code constants | New `ExitCode` enum module | Inline literals (`10`) with the dispatch-dict comment | The constants are NAMED in CONTEXT.md Decision 6. Two call sites total. Phase 100 will mirror — no shared constant module needed yet. |

**Key insight:** Every plumbing primitive Phase 99 needs already exists in-tree. The work is wiring + ~80 lines of new code total, ~120 lines of new test code. Zero new dependencies, zero new architectural seams.

## Runtime State Inventory

> Rename/refactor/migration phase? **NO.** Phase 99 is additive feature work — no string-rename, no schema migration, no datastore key changes. Section retained for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — counter lives in-memory only on `LibraryToolset` instance (per-run). No persistence. | None — verified: counter scope is one Codex `exec` invocation. MCP subprocess dies at end of run. |
| Live service config | None — no env vars renamed; ONE new env var added (`VIBEMIX_STOP_REASON_FILE`) is internal CLI↔MCP plumbing, not user-facing config. | None — internal-only; document inline. |
| OS-registered state | None — no Task Scheduler / launchd / systemd entries. | None — verified. |
| Secrets/env vars | None — `VIBEMIX_STOP_REASON_FILE` is a temp path, not a secret. Existing `VIBEMIX_CODEX_ALLOW_SHELL` / `VIBEMIX_TELEGRAM_TOKEN` untouched. | None — verified. |
| Build artifacts | None — no `pyproject.toml` rename, no module rename. `LibraryToolset` class name unchanged. | None — verified. |

## Common Pitfalls

### Pitfall 1: Counter writes on the handler thread (silent thread race)

**What goes wrong:** Putting counter updates inside `search_vibe` / `get_track_features` / etc handler bodies makes them run on the `ThreadPoolExecutor` worker thread, while another `dispatch()` call could (in theory) read `self.stop_reason` on the main thread.

**Why it happens:** Looks natural — the handler knows whether its result was empty or errored. But `toolset.py:982-1013 dispatch()` ALREADY centralizes this: it calls the handler and inspects the return.

**How to avoid:** Put ALL counter updates and stop_reason writes inside `dispatch()` AFTER `fut.result()` returns. The dispatch-calling thread is the only writer; the handler thread NEVER touches counter state.

**Warning signs:** Test `test_toolset_starvation_concurrency.py` (the acid test) fails with duplicated stop_reason writes or non-monotonic counter.

### Pitfall 2: Forgetting to reset the counter on `search_vibe` returning non-empty

**What goes wrong:** Spec says "consecutive empties/errors trigger starvation"; "consecutive" means the counter must RESET on any successful non-empty/non-error tool return. If you only increment, a normal long curation session (12 searches, 1 empty, 11 successes) would trip starvation falsely.

**Why it happens:** Easy to wire increment-only and forget the reset branch.

**How to avoid:** Explicit reset logic in `dispatch()`:
```python
if _is_empty_or_error_result(result, name):
    self._consecutive_empties += 1
    if self._consecutive_empties >= TOOL_STARVATION_THRESHOLD and self.stop_reason is None:
        self.stop_reason = _build_stop_reason(...)
        # write side-channel file
else:
    self._consecutive_empties = 0
```

**Warning signs:** REQ-RETRY-06 "counter reset on successful tool call" test fails.

### Pitfall 3: Empty-result detection ambiguity on `search_vibe`

**What goes wrong:** `search_vibe` returns `{"results": [...]}` on success, `{"error": "..."}` on error. The empty-list case is `{"results": []}` — NOT an error. If the empty-detection logic only checks for the `"error"` key, empty searches won't increment the counter and starvation never trips.

**Why it happens:** `error` key check is the obvious one. Empty-results is a quieter signal.

**How to avoid:** Detection logic must be: `result.get("error") is not None OR (name == "search_vibe" AND not result.get("results"))`. Verified result shape at `toolset.py:134-145`:
```python
return {
    "results": [
        {"track_id": r.track_id, "title": r.title, ...}
        for r in results
    ]
}
```
On zero results, `results` list is empty list `[]`, falsy. Other handlers (`discover_pool` at `toolset.py:577-590` returns `{"pool": [...]}`) follow the same pattern — `discover_pool` empty is `{"pool": []}`. **Decision 2 (CONTEXT.md) locked: only `search_vibe` empty counts; other empty-result handlers are not part of the empty-list trigger.** Other tools count toward the threshold only when they return an `{"error": ...}` dict.

**Warning signs:** Test fixture with a fake `vibe_search` returning empty list never trips starvation.

### Pitfall 4: Side-channel file written but never read

**What goes wrong:** Wrapper allocates the temp path INSIDE `tempfile.TemporaryDirectory(prefix="viber-codex-")` (`codex_curate.py:450`). The `with` block exits at the end of the function — the file is deleted before the wrapper can read it. Result: starvation always loses.

**Why it happens:** The temp dir gets cleaned up too early. Same pattern works for `schema.json` (read by Codex before exit) and `out.json` (read INSIDE the with block at `codex_curate.py:509`).

**How to avoid:** Read the stop_reason file INSIDE the `with tempfile.TemporaryDirectory(...)` block, immediately after `_runner` returns. Stash the parsed payload in a local variable. Don't move the read outside the `with` block.

**Warning signs:** Integration test passes locally with hardcoded paths but fails CI / under TemporaryDirectory.

### Pitfall 5: Telegram bridge re-entrant counter race (FALSE ALARM — verified disjoint)

**What initially looks like:** Telegram's `_handle` at `telegram_bridge.py:148-180` calls `loop.run_in_executor(None, self._curate_fn, text)`. If `curate_fn` shared a `LibraryToolset` instance across messages, parallel Telegram requests would race the counter.

**Verification:** `__main__.py:2837-2850 curate_fn` calls `curate_with_codex(theme, lib)` per message. `curate_with_codex` spawns a fresh Codex subprocess → fresh MCP subprocess → fresh `LibraryToolset` instance per message. **Confirmed: no shared instance. No race.**

**How to avoid (forward-compat):** If a future refactor pools toolset instances, add `threading.Lock` to counter writes. Today's architecture (per-message subprocess) is race-free by construction.

### Pitfall 6: CLI exit-code clash with existing Unix conventions

**What goes wrong:** Exit codes 1-15 are heavily used by shells. `make`, `git`, `pytest`, etc. all use 1, 2, 5 for various failures.

**Verification of code 10:** `bash` reserves >128 for signals; codes 1-2 are general/builtin failures; codes 64-78 are sysexits.h. Code 10 is unallocated in standard conventions — safe to use. CONTEXT.md Decision 6 locked it.

**Warning signs:** If a wrapper script checks `if [[ $? -eq 10 ]]` and it conflicts with another tool's exit 10, that's a wrapper-script integration concern, not a vibemix design concern.

### Pitfall 7: Threshold tunability lost when `TOOL_STARVATION_THRESHOLD` is inlined

**What goes wrong:** Inlining `3` in the dispatch comparison instead of importing the module constant breaks test-time monkeypatching (`monkeypatch.setattr(toolset_mod, "TOOL_STARVATION_THRESHOLD", 2)` won't take effect).

**How to avoid:** Reference via `tool_mod.TOOL_STARVATION_THRESHOLD` (lookup-on-each-call), not via a local copy captured at module import.

**Warning signs:** Tests pass with N=3 but `test_threshold_n_is_tunable_for_tests` fails when monkeypatching to N=2.

## Code Examples

### Counter + threshold hook in `dispatch()`

```python
# Source: insertion into src/vibemix/library/toolset.py:982-1013 (existing dispatch)
# (lines 1003-1013 shown for context; counter logic inserted AFTER fut.result)

def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
    # Short-circuit if a terminal stop_reason already fired this run.
    if self.stop_reason is not None:
        return {"error": "tool_starvation", "stop_reason": dict(self.stop_reason)}

    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "search_vibe": self.search_vibe,
        # ... (existing handler map unchanged)
    }
    handler = handlers.get(name)
    if handler is None:
        return {"error": f"unknown tool {name!r}"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(handler, args)
        try:
            result = fut.result(timeout=TOOL_CALL_TIMEOUT_S)
        except concurrent.futures.TimeoutError:
            result = {"error": f"tool {name!r} timed out"}
        except Exception as e:
            result = {"error": f"tool {name!r} crashed: {type(e).__name__}"}

    # ─── PHASE 99 HOOK ───────────────────────────────────────────────
    # Counter + threshold detection on the dispatch-calling thread.
    # SAFE because dispatch serializes tool calls within a run (see
    # toolset.py:407-411 — same lazy-init guarantee underpins this).
    if self._is_empty_or_error(name, result):
        self._consecutive_empties += 1
        if (
            self._consecutive_empties >= TOOL_STARVATION_THRESHOLD
            and self.stop_reason is None
        ):
            self.stop_reason = self._build_starvation_payload(
                last_tool=name,
                args=args,
            )
            self._write_side_channel(self.stop_reason)
    else:
        self._consecutive_empties = 0
    # ─── END PHASE 99 HOOK ───────────────────────────────────────────

    return result

# Helper (NEW method on LibraryToolset):
def _is_empty_or_error(self, name: str, result: dict[str, Any]) -> bool:
    """True if result is an error OR an empty search_vibe."""
    if isinstance(result, dict) and result.get("error") is not None:
        return True
    if name == "search_vibe":
        return not result.get("results")
    return False
```

### Hint generation (deterministic, three cases)

```python
# Source: NEW method on LibraryToolset
def _build_starvation_payload(
    self, last_tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Build the tool_starvation hint payload — three named cases.

    All copy is deterministic (no LLM). KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS
    will polish the wording; the structure stays additive-stable for Phase 100.
    """
    # Case A: zero-track library (any tool's empty/error AND library empty)
    if not self._library.tracks:
        hint = "library has 0 tracks — run `library ingest` first"
    # Case B: theme-no-match (last tool was search_vibe and library has tracks)
    elif last_tool == "search_vibe":
        theme = args.get("query", "")
        hint = (
            f"no tracks matched '{theme}' — try a broader theme or different "
            "BPM range"
        )
    # Case C: tool error (last tool returned error and was NOT a search)
    else:
        hint = f"tool '{last_tool}' kept failing — try again or check codex installation"
    return {
        "reason": "tool_starvation",
        "hint": hint,
        "tool": last_tool,
        "consecutive": self._consecutive_empties,
    }
```

### Side-channel file write (toolset side)

```python
# Source: NEW method on LibraryToolset
def _write_side_channel(self, payload: dict[str, Any]) -> None:
    """Write stop_reason to VIBEMIX_STOP_REASON_FILE if the wrapper provided one.

    Silent no-op when the env var is absent (e.g. direct unit tests, or
    library/curate called outside the codex_curate wrapper). The wrapper
    allocates and reads the file; we only write.
    """
    import os, json
    path = os.environ.get("VIBEMIX_STOP_REASON_FILE")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except OSError:
        # Side-channel is best-effort; never wedge the dispatch on FS issues.
        pass
```

### Wrapper-side propagation (codex_curate)

```python
# Source: insertion into src/vibemix/library/codex_curate.py:curate_with_codex
# (around the existing tempfile block at line 450)

with tempfile.TemporaryDirectory(prefix="viber-codex-") as td:
    schema_path = str(Path(td) / "schema.json")
    out_path = str(Path(td) / "out.json")
    stop_reason_path = str(Path(td) / "stop_reason.json")  # NEW
    Path(schema_path).write_text(json.dumps(_OUTPUT_SCHEMA), encoding="utf-8")

    argv = build_argv(
        codex,
        mcp_command=command,
        mcp_args=args,
        schema_path=schema_path,
        out_path=out_path,
        prompt=build_prompt(theme),
        bypass_sandbox=allow_shell,
    )

    env = build_subprocess_env(codex)
    env["VIBEMIX_STOP_REASON_FILE"] = stop_reason_path  # NEW

    try:
        proc = _runner(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # ... (existing branches unchanged)
        ...

    # ─── PHASE 99: side-channel CHECK BEFORE out.json parse ───────────
    # IMPORTANT: read INSIDE the tempfile block (Pitfall 4).
    if Path(stop_reason_path).exists():
        try:
            payload = json.loads(
                Path(stop_reason_path).read_text(encoding="utf-8")
            )
            if isinstance(payload, dict) and payload.get("reason") == "tool_starvation":
                return CodexCurateResult(
                    theme=theme,
                    stop_reason="tool_starvation",
                    error=str(payload.get("hint") or "Viber ran out of grounded options."),
                )
        except (OSError, json.JSONDecodeError):
            pass  # malformed → fall through to existing parse logic
    # ─── END PHASE 99 ─────────────────────────────────────────────────

    # ... (existing returncode/stderr/parse logic unchanged)
```

### Telegram `format_reply` branch

```python
# Source: insertion into src/vibemix/library/telegram_bridge.py:107-124

def format_reply(norm: dict[str, Any]) -> str:
    """Render a normalized curation result into a chat message (leak-stripped)."""
    # ─── PHASE 99: tool_starvation branch (BEFORE the generic error branch) ──
    if norm.get("stop_reason") == "tool_starvation":
        hint = norm.get("hint") or norm.get("error") or "Viber ran out of grounded options."
        return strip_leaks(f"⚠️ {hint}")
    # ─── END PHASE 99 ────────────────────────────────────────────────────────

    if not norm.get("ok"):
        err = norm.get("error") or "no playlist could be built"
        return strip_leaks(f"⚠️ {err}")

    name = norm.get("name") or "playlist"
    titles = norm.get("titles") or []
    lines = [f"🎧 {name} ({len(titles)} tracks)"]
    for i, t in enumerate(titles, 1):
        lines.append(f"{i}. {t}")
    lines.append("\nSaved to your vibemix playlists folder.")
    return strip_leaks("\n".join(lines))
```

And in `__main__.py:_cmd_library_telegram:2837-2850`, the `curate_fn` adapter needs a starvation branch:

```python
# Source: src/vibemix/__main__.py:2837 (extended)
def curate_fn(theme: str) -> dict:
    result = curate_with_codex(theme, lib)
    if result.stop_reason == "tool_starvation":  # NEW
        return {
            "ok": False,
            "stop_reason": "tool_starvation",
            "hint": result.error or "",
        }
    if result.playlist_name is None or not result.track_ids:
        return {"ok": False, "error": result.error or f"no playlist ({result.stop_reason})"}
    # ... existing happy-path unchanged
```

### CLI exit-code change

```python
# Source: src/vibemix/__main__.py:2547-2556 (_cmd_library_curate_codex tail)
# (delta only; surrounding code unchanged)

    if result.stop_reason != "created":
        print(_json.dumps(out, indent=2), file=sys.stderr)
        hint = {
            "codex_not_installed": (
                "Install Codex: `npm i -g @openai/codex` (or `brew install "
                "codex`), then `codex login`."
            ),
            "codex_auth_required": "Run `codex login` to connect your ChatGPT plan.",
            "timeout": "Codex took too long — try a narrower theme.",
            "tool_starvation": result.error or "no playlist (tool starvation)",  # NEW
        }.get(result.stop_reason, result.error or "no playlist created")
        print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)
        return 10 if result.stop_reason == "tool_starvation" else 1  # NEW
```

Same surgical edit at `_cmd_library_build_set_codex` (`__main__.py:2591-2602`).

## Stop-Reason Propagation Channel

**The architectural question CONTEXT.md left to research.**

### Channel options analyzed

| Channel | Mechanism | Pros | Cons | Verdict |
|---------|-----------|------|------|---------|
| **A: Side-channel file via env var** | Wrapper allocates `tempfile / stop_reason.json`, passes path via `VIBEMIX_STOP_REASON_FILE` env var → MCP subprocess → toolset writes on threshold. Wrapper reads after Codex exits. | Bypasses LLM entirely (model cannot elide). Zero schema changes. Mirrors existing `schema.json`/`out.json` pattern. Forward-compatible: Phase 100 reuses the same file with `reason="clarification_needed"`. | New env var added. Requires lifecycle care (read inside `with TemporaryDirectory` — see Pitfall 4). | **RECOMMENDED** |
| B: Schema extension | Add `stop_reason` / `hint` fields to `_OUTPUT_SCHEMA` / `_BUILD_SET_SCHEMA` / `_CHAT_SCHEMA`. Toolset folds payload into final tool response; Codex's structured-output enforces the field in the final JSON. | No env var. Single channel. | OpenAI strict mode requires every property in `required` AND `additionalProperties: false` (`codex_curate.py:186-198` documents this). Adding `stop_reason` as `required` forces every successful run to populate it. LLM could hallucinate the value. LLM could simply not call the tool whose response carries the payload. Three schemas to update; brittle. | Rejected. |
| C: Sentinel-string in `error` field | Toolset puts `__VIBEMIX_TOOL_STARVATION__::<json>` in the `error` field; wrapper grep-parses. | No new file, no schema change. | String parsing is brittle. Mixes telemetry with error transport. Future Phase 100 would need a second sentinel. Hard to test. | Rejected. |
| D: Exception path | Handler raises `ToolStarvationError`; dispatch catches and converts to a special return. | Pythonic. | **Violates `toolset.py` module docstring's no-raise contract** ("handlers RETURN error dicts — they never raise"). | Rejected. |

### Recommended: Channel A (side-channel file)

**Why:**
1. Survives any LLM behavior. The wrapper reads BEFORE parsing Codex's output.
2. Zero schema changes — `_OUTPUT_SCHEMA` / `_BUILD_SET_SCHEMA` / `_CHAT_SCHEMA` stay byte-identical.
3. Reuses existing `tempfile.TemporaryDirectory` pattern (`codex_curate.py:450`).
4. Phase 100 forward-compat: same file, `reason="clarification_needed"` instead of `"tool_starvation"`. The wrapper's branch dispatch is a single `if payload.get("reason") in {"tool_starvation", "clarification_needed"}`.
5. Test ergonomics: side-channel file is trivial to set up in unit tests (`monkeypatch.setenv` + `tmp_path`).

**Env var spec:**
- Name: `VIBEMIX_STOP_REASON_FILE`
- Type: absolute path to a writable file location
- Lifecycle: created (empty) by wrapper before `_runner`; written (JSON) by toolset on threshold trip; read by wrapper after `_runner` returns; cleaned up automatically by `TemporaryDirectory` context exit.
- Absence: toolset silently no-ops the write (graceful — direct CLI usage or tests without env var still work; counter and `self.stop_reason` are still set in-process for in-process readers).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Codex silently degrades on empty searches; user sees "no playlist" with no diagnosis | Per-Factor-9, surface terminal `stop_reason="tool_starvation"` with actionable hint | This phase (P99) | Closes the 2026-05-28 audit partial; aligns with [humanlayer/12-factor-agents Factor 9](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-9-compact-errors-into-context-window.md). |
| Generic exit code 1 for all curation failures | Distinct exit code 10 for `tool_starvation` (reserve 10-19 for stop_reasons) | This phase | Scripts can branch on starvation specifically. Phase 100 uses 11. |
| Telegram `format_reply` only knows playlist / error branches | New `tool_starvation` branch (privacy preserved via `strip_leaks`) | This phase | Mobile UX shows hint, not just "⚠️ something went wrong". |

**Deprecated/outdated:** None. This phase is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| (none) | All claims in this research were verified against current source by file:line reads in this session (`toolset.py`, `codex_curate.py`, `mcp_server.py`, `telegram_bridge.py`, `create_playlist.py`, `__main__.py`, `tests/library/test_toolset.py`, `tests/library/test_codex_curate.py`, `tests/library/test_telegram_bridge.py`). The Decision 5 hint copy is seeded (KAAN-ACTION ear-pass tunes wording); the seeded strings are testable as fixtures even before ear-pass polishes them. | — | — |

**Empty assumptions table:** All claims verified or directly cited from in-tree source. No user confirmation needed before planning proceeds.

## Open Questions

1. **Should the side-channel file be `stop_reason.json` (per-curation-run) or `viber-state.json` (per-run state envelope)?**
   - What we know: Phase 100 will add `clarification_needed` as a sibling stop_reason. Same file works.
   - What's unclear: Phase 100 might also carry MORE state (a question + choices array). Same JSON file with discriminated-union shape `{"reason": "...", ...rest}` handles both.
   - Recommendation: name it `stop_reason.json` (semantic), use discriminated-union shape internally. No rename needed for Phase 100.

2. **Should `dispatch()` short-circuit subsequent tool calls after `self.stop_reason` is set?**
   - What we know: Once starvation fires, the run is terminal. The LLM might still call more tools (Codex's loop has its own iteration count).
   - What's unclear: do we want subsequent dispatch calls to (a) execute normally, (b) immediately return an error echo of the stop_reason, or (c) be a no-op silent skip?
   - Recommendation: option (b) — return `{"error": "tool_starvation", "stop_reason": dict(self.stop_reason)}` for every subsequent call. The LLM gets a hint; the side-channel file is already written (we re-write idempotently). This is what the Code Example above shows.

3. **What's the right empty-results detection for `discover_pool`?**
   - What we know: Decision 2 says counter increments on `search_vibe` empty OR any handler error. `discover_pool` empty returns `{"pool": []}` (verified `toolset.py:577-589`) — which is NOT an error, but IS structurally similar to `search_vibe` empty.
   - What's unclear: should an empty `discover_pool` also trip the counter? CONTEXT.md Decision 2 names ONLY `search_vibe`.
   - Recommendation: stick to CONTEXT.md — `search_vibe` empty only. `discover_pool` only counts when it returns `{"error": ...}`. This keeps the spec narrow and testable; if KAAN-ACTION ear-pass finds set-prep starvation needs detection too, Phase 100/HARDEN-FUTURE can extend the predicate.

## Environment Availability

> No external dependencies for this phase — all stdlib + existing in-tree modules. Section retained for completeness with explicit "no items" markers per protocol.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (`concurrent.futures`, `tempfile`, `json`, `os.environ`) | Counter dispatch hook + side-channel file | ✓ | 3.12.x (verified — `.venv/` is 3.12.x; `pyproject.toml requires-python = ">=3.12,<3.13"`) | — |
| `pytest` 8.x | Tests | ✓ | (from `pyproject.toml [tool.pytest.ini_options]`) | — |
| `vibemix.library.toolset` | The target module | ✓ | in-tree | — |
| `vibemix.library.codex_curate` | The target module | ✓ | in-tree | — |
| `vibemix.library.telegram_bridge` | The target module (optional `telegram` extra not needed for unit tests of `format_reply`) | ✓ | in-tree (pure-logic surface is dep-free per module docstring `telegram_bridge.py:33-43`) | — |
| `codex` CLI | Live integration only (KAAN-ACTION ear-pass) | ✗ in CI / tests | n/a | `_runner` injection seam at `codex_curate.py:392` lets tests fake it entirely |
| Rekordbox library cache (`~/.cache/vibemix/library.pkl`) | Live CLI invocation | ✗ in unit tests | n/a | `RekordboxLibrary` in-memory fixture pattern at `tests/library/test_toolset.py:149-152` |

**Missing dependencies with no fallback:** None — every dep has either an in-tree fallback or is opt-in (KAAN-ACTION live integration).

**Missing dependencies with fallback:** `codex` CLI (fallback: `_runner` injection); live library (fallback: in-memory `RekordboxLibrary` fixture).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section included per protocol.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 8.x` (from `pyproject.toml [tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (no separate `pytest.ini`) |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/library/test_toolset_starvation.py tests/library/test_codex_curate_stop_reason.py tests/library/test_telegram_bridge.py tests/library/test_cli_exit_codes.py -q` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARDEN-RETRY-01 | Counter exists on `LibraryToolset.__init__`, starts at 0, mirrors `self.seen` lifetime | unit | `pytest tests/library/test_toolset_starvation.py::test_counter_initial_zero -x` | ❌ Wave 0 |
| HARDEN-RETRY-01 | Counter increments on empty `search_vibe` (counter == 1) | unit | `pytest tests/library/test_toolset_starvation.py::test_empty_search_increments -x` | ❌ Wave 0 |
| HARDEN-RETRY-01 | Counter increments on `{"error":...}` handler return | unit | `pytest tests/library/test_toolset_starvation.py::test_handler_error_increments -x` | ❌ Wave 0 |
| HARDEN-RETRY-02 | After 3 consecutive empties, `self.stop_reason` is set with `reason="tool_starvation"` | unit | `pytest tests/library/test_toolset_starvation.py::test_threshold_trip_sets_stop_reason -x` | ❌ Wave 0 |
| HARDEN-RETRY-02 | `TOOL_STARVATION_THRESHOLD` is module-level + tunable via monkeypatch | unit | `pytest tests/library/test_toolset_starvation.py::test_threshold_is_tunable -x` | ❌ Wave 0 |
| HARDEN-RETRY-03 | Hint case A (zero-track library) | unit | `pytest tests/library/test_toolset_starvation.py::test_hint_zero_track_library -x` | ❌ Wave 0 |
| HARDEN-RETRY-03 | Hint case B (no theme match) | unit | `pytest tests/library/test_toolset_starvation.py::test_hint_no_theme_match -x` | ❌ Wave 0 |
| HARDEN-RETRY-03 | Hint case C (tool kept failing) | unit | `pytest tests/library/test_toolset_starvation.py::test_hint_tool_error -x` | ❌ Wave 0 |
| HARDEN-RETRY-04 | CLI `library curate` exits 10 on tool_starvation | unit | `pytest tests/library/test_cli_exit_codes.py::test_curate_exits_10_on_starvation -x` | ❌ Wave 0 |
| HARDEN-RETRY-04 | CLI `library curate` exits 1 on other failures (regression-pin) | unit | `pytest tests/library/test_cli_exit_codes.py::test_curate_exits_1_on_other_failures -x` | ❌ Wave 0 |
| HARDEN-RETRY-04 | CLI `library build-set` exits 10 on tool_starvation | unit | `pytest tests/library/test_cli_exit_codes.py::test_build_set_exits_10_on_starvation -x` | ❌ Wave 0 |
| HARDEN-RETRY-05 | `seen`-set writes count unchanged after Phase 99 (AST/grep gate) | unit | `pytest tests/repo/test_no_seen_relaxation.py::test_seen_writes_unchanged -x` | ❌ Wave 0 |
| HARDEN-RETRY-05 | `create_playlist` library re-validation untouched | unit | `pytest tests/library/test_toolset.py::test_create_persists_grounded_playlist -x` (existing — regression-pin) | ✅ exists |
| HARDEN-RETRY-05 | starvation termination short-circuits BEFORE `create_playlist` partial write | unit | `pytest tests/library/test_toolset_starvation.py::test_starvation_short_circuits_create_playlist -x` | ❌ Wave 0 |
| HARDEN-RETRY-06 | Counter reset on successful non-empty tool return | unit | `pytest tests/library/test_toolset_starvation.py::test_counter_resets_on_success -x` | ❌ Wave 0 |
| HARDEN-RETRY-06 | Counter reset on successful non-empty (mixed-error scenario) | unit | `pytest tests/library/test_toolset_starvation.py::test_counter_resets_after_partial_failures -x` | ❌ Wave 0 |
| HARDEN-RETRY-06 | Anti-thread-race acid test (N+1 concurrent dispatch monotonic) | unit | `pytest tests/library/test_toolset_starvation_concurrency.py::test_monotonic_under_parallel_dispatch -x` | ❌ Wave 0 |
| HARDEN-RETRY-07 | `curate_with_codex` reads side-channel file and propagates `stop_reason="tool_starvation"` to `CodexCurateResult` | unit | `pytest tests/library/test_codex_curate_stop_reason.py::test_curate_propagates_starvation_via_side_channel -x` | ❌ Wave 0 |
| HARDEN-RETRY-07 | `build_set_with_codex` same propagation | unit | `pytest tests/library/test_codex_curate_stop_reason.py::test_build_set_propagates_starvation -x` | ❌ Wave 0 |
| HARDEN-RETRY-07 | Side-channel file ABSENT → wrapper falls through to existing parse logic (no regression) | unit | `pytest tests/library/test_codex_curate_stop_reason.py::test_no_side_channel_no_regression -x` | ❌ Wave 0 |
| HARDEN-RETRY-07 | Side-channel file MALFORMED → wrapper falls through (graceful degrade) | unit | `pytest tests/library/test_codex_curate_stop_reason.py::test_malformed_side_channel_falls_through -x` | ❌ Wave 0 |
| HARDEN-RETRY-07 | Telegram `format_reply` renders `tool_starvation` hint with `strip_leaks` | unit | `pytest tests/library/test_telegram_bridge.py::test_format_reply_starvation_branch -x` | ❌ Wave 0 (extend existing file) |
| HARDEN-RETRY-07 | Telegram bridge `curate_fn` adapter normalizes starvation result for `format_reply` | unit | `pytest tests/library/test_cli_exit_codes.py::test_telegram_curate_fn_normalizes_starvation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/library/test_toolset_starvation.py tests/library/test_codex_curate_stop_reason.py tests/library/test_telegram_bridge.py tests/library/test_cli_exit_codes.py -q` (~22 tests, < 5s)
- **Per wave merge:** `pytest tests/library/ tests/repo/ -q` (~600 tests, ~30s)
- **Phase gate:** `pytest -q` full suite must be green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/library/test_toolset_starvation.py` — 11 tests covering REQ-01/02/03/05/06
- [ ] `tests/library/test_toolset_starvation_concurrency.py` — 1 acid test for thread-race safety
- [ ] `tests/library/test_codex_curate_stop_reason.py` — 4 tests covering REQ-07 propagation
- [ ] `tests/library/test_cli_exit_codes.py` — 4 tests covering REQ-04
- [ ] `tests/library/test_telegram_bridge.py::test_format_reply_starvation_branch` — extend existing file (REQ-07 telegram branch)
- [ ] `tests/repo/test_no_seen_relaxation.py` — AST/grep gate covering REQ-05 (NEW file in `tests/repo/`)
- [ ] Framework install: not needed (pytest 8 already installed; `.venv/` operational)

## Security Domain

> Required by Security Threat Model Gate. Phase 99 has a narrow surface — no new auth, no new network, no new persistence. Security analysis focuses on the specific new attack surfaces.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth surface. Codex auth (`codex login`) is unchanged. Telegram allow-list (`telegram_bridge.py:97-99 is_authorized`) is unchanged. |
| V3 Session Management | no | No sessions. Each Codex `exec` invocation is stateless per-process. |
| V4 Access Control | yes | The side-channel file lives in `tempfile.TemporaryDirectory` — mode 0o700 on macOS/Linux by default. Cross-subprocess access is via the env-var-passed path, not a shared known location. Standard control: rely on `tempfile`'s defaults. |
| V5 Input Validation | yes | Side-channel file payload must be validated on read (the wrapper reads what the MCP subprocess wrote, but defense-in-depth). Standard control: `json.loads` + `isinstance(payload, dict)` + `.get("reason") == "tool_starvation"` checks. Already shown in Code Example. |
| V6 Cryptography | no | No crypto in this phase. |
| V14 Configuration | yes | New env var `VIBEMIX_STOP_REASON_FILE` documented inline. Not a secret. |

### Known Threat Patterns for {stack: Python in-process + subprocess STDIO}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| T-99-01: Counter underflow / overflow | Tampering | Counter is `int`, monotonic increment-only, reset-only. Bounded by N=3 threshold (after which dispatch short-circuits). Type-hinted `int`. |
| T-99-02: Stop-reason payload injection | Tampering / Spoofing | Hint string is deterministically generated by case-based code (Decision 5). NEVER accepts user input as a hint. The `theme` user-input is interpolated INTO the hint via f-string — verified safe because the hint is rendered to terminal/Telegram, not eval'd. Telegram side renders through `strip_leaks` (existing privacy scrubber at `telegram_bridge.py:102-104`). CLI side prints to stderr — safe. |
| T-99-03: Thread race on counter | Race condition (Tampering) | Counter writes ONLY happen on the dispatch-calling thread (POST `fut.result()`). Handler thread NEVER touches counter state. Documented at `toolset.py:407-411` — dispatch serializes within a run. Per-message Telegram requests get fresh `LibraryToolset` instances (verified: `__main__.py:2837-2850` creates fresh subprocess per message). |
| T-99-04: Cardinal Invariant #2 leak (`seen` relaxation) | Tampering | AST/grep gate `tests/repo/test_no_seen_relaxation.py` enforces zero new `seen` write sites. `create_playlist` library re-validation untouched. |
| T-99-05: Telegram path leak via hint | Information disclosure | All hints rendered through `strip_leaks` (existing scrubber at `telegram_bridge.py:102-104`). The hint copy seeded in Decision 5 contains literal strings + `theme` user input — no FS paths. But defense-in-depth: pass through `strip_leaks` regardless. |
| T-99-06: Side-channel file path injection | Tampering | The env var `VIBEMIX_STOP_REASON_FILE` is set by the WRAPPER from a `tempfile.TemporaryDirectory` allocation (`codex_curate.py:450` pattern). The MCP subprocess inherits the env from the wrapper. A malicious local process could not inject the env var — the wrapper writes it last. Tests reset env via `monkeypatch.setenv`. |
| T-99-07: Side-channel file race (TOCTOU) | Race condition | The file is written by the toolset (in-process inside MCP subprocess), read by the wrapper AFTER `_runner` returns (after Codex process has exited). No concurrent writers. The wrapper's read is a single `json.loads` of a final state. |
| T-99-08: Exit-code masquerade | Spoofing | Exit code 10 is unallocated in standard Unix conventions (verified — Pitfall 6). A script wrapper relying on exit codes for control flow trusts the vibemix CLI as much as it trusts any other CLI tool. No new exposure. |

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md are non-negotiable and apply to this phase:

1. **Cardinal Invariant #2 (citation grounding):** Every track_id in a playlist must be in the per-run `seen` set. P99's counter is ADDITIVE telemetry — it never relaxes the gate. Enforced by `tests/repo/test_no_seen_relaxation.py` AST grep.
2. **Threading & generation model:** "sounddevice callbacks (OS audio thread) → lock-protected buffers → asyncio event loop (AI calls, ws, state loops) ← MIDI daemon thread." P99 lives in the CLI/library subtree, NOT the live audio path. The counter writes are on the dispatch-calling thread (NOT the handler thread, NOT the audio thread). Race-free by construction per `toolset.py:407-411`.
3. **Disjointness contract:** P99 NEVER touches `src/vibemix/agent/`, `src/vibemix/intel/`, `tauri/ui/*`, or `src/vibemix/__main__.py` LiveKit-session_loop block (line 1353 turn_handling). Only the two narrow CLI dispatch sites at lines 2547-2556 and 2591-2602. Surgical commits with named paths, never `git add -A`. Per `feedback_concurrent_sessions_one_tree`.
4. **Honest-green:** Tests run on CURRENT source via `python3 -m pytest -q`, NEVER the bundled sidecar (per `feedback_stale_sidecar_verify_current_source`). The bundled sidecar lags edited `src/`.
5. **`gsd-autonomous fully` mode:** default-YES on grey-area; blockers ride forward to KAAN-ACTION (§HARDEN-PHASE-A-EAR-PASS). Only privacy hard rule + destructive risk pause.
6. **No new heavy deps / AI providers / managed-memory frameworks / ws ports / IPC envelopes:** P99 adds zero. One new env var `VIBEMIX_STOP_REASON_FILE` is internal CLI↔MCP plumbing, not user-facing config.
7. **Anti-slop posture (stop-slop project skill):** the hint copy must pass `.claude/skills/stop-slop/` blocklist — no "I apologize", no "Sorry, I cannot", no "Let me know if...". The seeded hints in Decision 5 are direct ("library has 0 tracks — run `library ingest` first") and pass this gate. KAAN-ACTION ear-pass polishes wording.
8. **Logging:** AI-relevant terminal output uses bracket-tagged stderr (`[viber/codex] tool_starvation: ...` matches existing pattern at `__main__.py:2555 print(f"[viber/codex] {result.stop_reason}: {hint}", file=sys.stderr)`).
9. **Shell numerics rule:** N/A — no `ffmpeg`/`awk`/`bc` in this phase.

## Phase 100 Forward-Compatibility Sanity Check

CONTEXT.md and additional context both flag that Phase 100 (HARDEN-CLARIFY) adds a sibling stop_reason `clarification_needed` with CLI exit 11. Every seam P99 builds MUST be reusable:

| P99 Seam | Phase 100 Reuse |
|----------|------------------|
| `self.stop_reason: dict | None` on `LibraryToolset` | Same attribute. Phase 100 sets `{"reason": "clarification_needed", "question": "...", "choices": [...]}`. |
| `VIBEMIX_STOP_REASON_FILE` side-channel | Same file, same env var. Phase 100 writes `{"reason": "clarification_needed", ...}`. Wrapper-side branch already discriminates on `reason` field. |
| `CodexCurateResult.stop_reason: str` (existing field) | Phase 100 adds `"clarification_needed"` to documented values. No schema change. |
| CLI exit-code dispatch dict in `_cmd_library_curate_codex` / `_cmd_library_build_set_codex` | Phase 100 adds `"clarification_needed": "..."` hint + `return 11 if ...` branch. Phase 100 review can add a 3-way ternary or move to dict-lookup. |
| Telegram `format_reply` branch | Phase 100 adds a sibling branch BEFORE the generic error path. Both branches render through `strip_leaks`. |
| Test posture (fake embedder/store/library; `_runner` injection) | Phase 100 reuses every fixture. |

**Verdict:** P99 design is generalized correctly. No P99 code is named "starvation" outside the actual hint generation. Every other seam (counter + threshold detection is starvation-specific; everything else is `stop_reason`-agnostic) is the spine, not the leaf.

## Sources

### Primary (HIGH confidence)

- Current in-tree source verified by direct file reads in this session:
  - `src/vibemix/library/toolset.py` (1145 lines — `LibraryToolset` class, `dispatch()`, per-run state attributes, threading documentation comments at lines 407-411)
  - `src/vibemix/library/codex_curate.py` (1226 lines — `CodexCurateResult` dataclass at line 201, `curate_with_codex` at line 382, `build_set_with_codex` at line 672, `_runner` injection seam at line 392, `_OUTPUT_SCHEMA` at line 189, tempfile pattern at line 450)
  - `src/vibemix/library/mcp_server.py` (348 lines — FastMCP wrap of toolset, `build_toolset` lifecycle at line 49)
  - `src/vibemix/library/telegram_bridge.py` (246 lines — `format_reply` at line 107, `strip_leaks` at line 102, fail-closed auth, lazy `telegram` import)
  - `src/vibemix/library/create_playlist.py` lines 1-80 (`PlaylistResult` dataclass, two-gate library re-validation)
  - `src/vibemix/__main__.py:2404-2867` (`_cmd_library_curate`, `_cmd_library_curate_codex`, `_cmd_library_build_set`, `_cmd_library_build_set_codex`, `_cmd_library_telegram` curate_fn adapter at line 2837)
  - `tests/library/test_toolset.py` lines 1-200 (existing fixture posture: `library`, `toolset`, `_stub_search`, `_make_track`)
  - `tests/library/test_codex_curate.py` lines 1-200 (`_runner_writing` test helper at line 61)
  - `tests/library/test_telegram_bridge.py` (pure-logic tests posture)
- `.planning/PROJECT.md` § Current Milestone v10.0 "12-Factor Hardening" (audit verdict, 3-phase split, acid test, KAAN-ACTION queue)
- `.planning/REQUIREMENTS.md` § HARDEN-RETRY-01..07 (the 7 phase requirements)
- `.planning/STATE.md` (current milestone state, disjointness contract, concurrent sessions list)
- `.planning/phases/99-harden-retry/99-CONTEXT.md` (8 auto-resolved decisions with rationale)
- `.planning/config.json` (workflow.nyquist_validation: true; granularity: fine; all-opus model overrides)
- `/Users/ozai/CLAUDE.md` + `/Users/ozai/projects/dj-set-ai/CLAUDE.md` (project conventions, tech stack, cardinal invariants)

### Secondary (MEDIUM confidence)

- 12-factor-agents [Factor 9: Compact Errors into Context Window](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-9-compact-errors-into-context-window.md) — referenced in PROJECT.md and CONTEXT.md as the audit standard. Pattern: retry counter + terminal stop_reason matches the documented best practice.

### Tertiary (LOW confidence)

- None — every claim in this research traces to in-tree source.

## Metadata

**Confidence breakdown:**
- Counter location + threading safety: HIGH — verified at `toolset.py:407-411` (existing documented serialization guarantee) + `toolset.py:982-1013` (dispatch implementation).
- Empty-result detection logic: HIGH — verified at `toolset.py:115-145` (`search_vibe` returns `{"results": [...]}`) and module-wide `{"error": "..."}` convention.
- Stop-reason propagation channel: HIGH — recommended Channel A (side-channel file via env var) verified to mirror existing `tempfile.TemporaryDirectory` pattern at `codex_curate.py:450`. Alternative channels analyzed honestly.
- CLI exit-code surgical edit sites: HIGH — exact file:line at `__main__.py:2545-2556` and `__main__.py:2591-2602`. No spillover into the LiveKit handoff block at line 1353.
- Telegram branch + curate_fn adapter: HIGH — verified at `telegram_bridge.py:107` and `__main__.py:2837-2850`. Per-message subprocess isolation confirmed disjoint from counter races.
- Test seam parity: HIGH — existing fixtures at `tests/library/test_toolset.py:148-170` are the canonical posture.
- Hint copy: MEDIUM — seeded copy is testable; KAAN-ACTION §HARDEN-PHASE-A-EAR-PASS polishes wording. Tests pin structure + key strings, not exact wording.

**Research date:** 2026-05-28
**Valid until:** 2026-06-04 (7 days — `live-tuning-or-brain` working tree has multiple active sessions and concurrent work; re-verify file:line references if planning is delayed beyond a week).
