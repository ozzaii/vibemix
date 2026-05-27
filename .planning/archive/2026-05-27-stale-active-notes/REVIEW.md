---
phase: live-tuning-or-brain (working-tree review — Curate GUI + library stats CLI + pill collapsed-hover)
reviewed: 2026-05-25T17:10:00Z
depth: deep
files_reviewed: 14
files_reviewed_list:
  - src/vibemix/__main__.py
  - tauri/src-tauri/src/library_cmds.rs
  - tauri/src-tauri/src/main.rs
  - tauri/ui/library.html
  - tauri/ui/pill.html
  - tauri/ui/src/library/api.ts
  - tauri/ui/src/library/index.ts
  - tauri/ui/src/library/library.css
  - tauri/ui/src/library/state-machine.ts
  - tauri/ui/src/library/curate.test.ts
  - tauri/ui/src/pill/index.ts
  - tauri/ui/src/pill/pill.css
  - tauri/ui/src/pill/state-machine.ts
  - tauri/ui/src/pill/state-machine.test.ts
  - tests/library/test_stats_cli.py
  - tests/security/test_no_api_key_surface.py
  - CLAUDE.md
findings:
  critical: 1
  warning: 4
  info: 4
  total: 9
status: issues_found
---

# Working-Tree Code Review — Curate GUI / library stats CLI / Pill collapsed-hover

**Reviewed:** 2026-05-25T17:10:00Z
**Depth:** deep (cross-file: Rust bridge ↔ Python CLI contract ↔ TS frontend ↔ window geometry)
**Files Reviewed:** 14 source + 2 test/doc
**Status:** issues_found

## Summary

Reviewed four landed changes: (1) the Curate 4th-mode GUI + Rust `library_curate`/`map_curate_result` + rewired two-call `library_stats`, (2) the offline `library stats --json` CLI, (3) the pill collapsed-hover peek, (4) CLAUDE.md currency edits. `src/vibemix/memory/**` excluded per scope.

**Strengths (verified, not assumed):**
- **Anti-slop / Invariant #2 holds in the production path.** `PlaylistResult.to_dict()` carries only `track_ids` (strings) — no human titles. `map_curate_result`'s flat-id branch maps id → `{track_id, title=id, meta="track <id>"}`, fabricating nothing. Verified against `agent.py::ViberAgentResult.to_dict` + `create_playlist.py::PlaylistResult`.
- **Real backend errors propagate.** `libraryCurate` returns dev data ONLY when `getInvoke()` is falsy (no Tauri); the real bridge lets `parse_cli_json` Err surface unmasked. The CLI no-playlist path (exit 1, stderr) yields a real error string (`[viber] no playlist created (stop_reason=…)`) via the stderr-tail branch — honest failure, never fake data.
- **`library stats` offline guarantee confirmed.** `_cmd_library_stats` imports only `vibemix.library.store.open_store`, reads `row_count()`/`backend_name`, and catches all exceptions to a fallback. No genai/httpx/network. `open_store` logs to stderr only — stdout stays pure JSON for the Rust parser.
- **Honest-None at the suggestion level holds.** `renderNextSuggestion(null|missing track_id|missing title) → null`; `syncPeekCard` appends nothing; CSS `:not(:empty)` is the belt-and-suspenders guard.
- **CDJ-Whisper / no-AI-slop respected.** No Inter/Roboto/system-ui, no raw hex/purple/blue — all via design tokens (`--amber`, `--void-3`, `--glass-3`, `--silk-*`). Single amber accent on labels only (20/80 honored). One orchestrated ease-out reveal + reduced-motion guard.
- Tests green: 867/867 vitest, 5/5 stats CLI.

**Key concern:** the pill peek card geometry contradicts the fixed pill-window dimensions — in the only state where it is shown (collapsed), the card is positioned below the window's clipped bottom. See CR-01.

## Structural Findings (fallow)

No `<structural_findings>` block was provided with this review; narrative findings only.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Pill peek card is positioned below the fixed 44px collapsed window and clipped by `overflow:hidden` — feature renders nothing in its only active state

**File:** `tauri/ui/src/pill/pill.css:215` (`.pill__peek { top: 64px; ... }`) with `tauri/src-tauri/src/pill_window.rs:86-87,193,197` (`PILL_COLLAPSED_H = 44.0`, `resizable(false)`, `.inner_size(280, 44)`) and `tauri/ui/src/pill/pill.css:40,57` (`.pill { inset:0; overflow:hidden }`)

**Issue:** The peek card is `position:absolute; top:64px` inside `.pill`, which is `inset:0` (fills the OS window) and `overflow:hidden`. The pill window is created fixed at **280×44** and `resizable(false)`; no code path resizes it (the only `@tauri-apps/api/window` use in `index.ts` is `startDragging()`, no `setSize`). The peek is shown ONLY when `state.peek && state.mode !== "expand"` — i.e. while collapsed, when the window is 44px tall. A card at `top:64px` begins 20px **below** the window's bottom edge and is fully clipped by `overflow:hidden`. The card therefore never becomes visible on collapsed hover, defeating the feature's stated purpose ("next-track glance on hover of the COLLAPSED pill"). The pure `setPeek` flag, `data-peek` toggle, and `syncPeekCard` DOM-population all run correctly — but the user sees nothing.

(This same geometry constraint applies to the pre-existing expand panel, which suggests the running window may differ from the 44px default via saved geometry; that ambiguity is exactly why this must be verified live before ship rather than assumed-working. The peek case is unambiguous regardless: peek only fires in the collapsed state, whose window height is the 44px `PILL_COLLAPSED_H`.)

**Fix:** Either (a) grow the pill window on hover (resize the Tauri window like expand presumably should, or add a transparent always-tall window region), or (b) anchor the peek inside the visible collapsed band. If the window cannot host the card, the honest move is to render the peek above the lozenge into the always-on-top window's transparent margin, or drop the collapsed-hover peek and surface "what's next" only in the expand panel (where the card already lives). Add a jsdom/integration test asserting the peek mount is within the visible window bounds. Concretely, verify the actual collapsed window height first:
```rust
// pill_window.rs — if peek must show below the lozenge, the collapsed window
// needs headroom (e.g. a taller transparent window with the lozenge pinned top),
// or call set_size on pointerenter/leave to open a peek-height window.
```

## Warnings

### WR-01: Peek DOM-glue + geometry are untested — only the pure flag is covered

**File:** `tauri/ui/src/pill/state-machine.test.ts` (covers `setPeek` only); no test for `syncPeekCard`, `#pill-peek` mount population, `data-peek` gating, or visibility.

**Issue:** The new tests exercise the pure `setPeek` transition (immutability, orthogonality to mode, ref-equality skip) thoroughly, but nothing tests the integration path that actually matters: that `syncPeekCard` populates the mount only when a grounded suggestion exists, clears it on null, never fires while `mode==="expand"`, and that the card lands in a visible region. CR-01 (a clipped card) would pass every existing test. This is the classic "tests pass, feature is invisible" gap.

**Fix:** Add a jsdom spec that boots the pill DOM skeleton (`#pill-peek` present), drives a `next_suggestion` onto the view, flips `setPeek(true)` while collapsed, calls `render()`, and asserts `#pill-peek` has a `.vmx-next-card` child with `data-no-drag`; then assert it is empty after a null suggestion and after entering expand mode.

### WR-02: Dev-fallback `DEV_CURATE` fabricates human track titles, inverting the title=id honesty contract the rest of the path enforces

**File:** `tauri/ui/src/library/api.ts:189-204` (`DEV_CURATE.tracks[].title = "Charli XCX - Guess (DJ Daddy Trance Edit)"`, `"Quälgeist"`, etc.)

**Issue:** Every production path (Rust `map_curate_result`, the `meta:"track <id>"` form) deliberately uses the track_id as the title because the in-memory `PlaylistResult` has no human titles. The dev sample contradicts this — it invents real-looking human titles while `meta` keeps the honest `track <id>` form. The inline comment even claims "these are real library rows the curator would have pulled," but the real curator never surfaces these titles to this UI. This trains the eye (and any reviewer/screenshot) to expect titled rows the shipped product cannot produce, and softly violates the anti-slop discipline in the dev surface. It is dev-only (fires only when `getInvoke()` is falsy), so it cannot leak to the packaged app — hence WARNING not CRITICAL.

**Fix:** Make the dev sample mirror the real contract: set each `title` to the `track_id` (matching `meta`), or add an explicit comment that these titles are illustrative-only and never appear in production. Prefer the former so the dev surface reads exactly like the shipped one.

### WR-03: `curate.test.ts` re-implements `renderCurate` instead of importing it — the real `esc()` XSS path and empty-state branch are never tested

**File:** `tauri/ui/src/library/curate.test.ts:82-98`

**Issue:** The "render smoke" test defines a private `renderCurate` mirror that uses `t.title` / `t.meta` **raw** (no `esc()`), while the real `index.ts::renderCurate` wraps them in `esc()`. The test therefore gives false confidence: the production escaping could regress (XSS via a malicious track title/meta from a future rich-track CLI payload) and this test stays green. The mirror also omits the empty-tracks branch (`vmx-lib-empty`) and the rAF `settled` animation, so neither is covered. The real `renderCurate` does escape correctly today (verified), so this is a test-quality gap, not a live vuln — WARNING.

**Fix:** Export `renderCurate` (or a pure `curateRowsHtml(result)`) from `index.ts` and import it in the test so the real escaping + empty-state path is exercised. Add a case with `title: '<img src=x onerror=alert(1)>'` asserting the rendered HTML is escaped, mirroring the existing `next-suggestion.test.ts` XSS case.

### WR-04: `library_stats` doc claims graceful no-hard-fail, but a sidecar spawn failure still propagates `Err` and hard-fails the header

**File:** `tauri/src-tauri/src/library_cmds.rs:447-449,460-461` (both `run_library_to_completion(...).await?`)

**Issue:** The rewritten doc-comment says "Both tolerate parse hiccups gracefully so the header never hard-fails on a stats glitch." That is true for parse/exit-code errors (each wrapped in `match parse_cli_json`), but the `?` on `run_library_to_completion` propagates a **spawn** failure (sidecar binary missing/unlaunchable) as `Err`, which bubbles to the UI as a thrown invoke. The comment overstates the resilience. Behavior is unchanged from the prior single-call version (also `?`), so it is not a regression, but the doc now misleads a future maintainer who trusts it. Note also: a `stats` spawn-Err short-circuits before `budget` even runs, so `spent_eur` is lost too.

**Fix:** Either wrap the spawn so a failure also falls back (`indexed:0, backend:"sqlite-vec", spent_eur:0.0`) to honor the doc's "never hard-fails" promise, or amend the comment to "parse/exit-code hiccups" and document that a spawn failure intentionally surfaces. Prefer the former for the header (a status readout should never crash the panel):
```rust
let (s_out, s_err, s_code) =
    match run_library_to_completion(&app, &["library","stats","--json"]).await {
        Ok(t) => t,
        Err(_) => (String::new(), String::new(), -1), // → fallback below
    };
```

## Info

### IN-01: Security gate `EXCLUDED_PATHS` broadened to whitelist `crash-banner.ts` — justified, but a whitelist on a security test deserves a guard

**File:** `tests/security/test_no_api_key_surface.py:47-53`

**Issue:** `crash-banner.ts` is added to the no-API-key-surface exclusion list because its read-only error message contains the phrase "Gemini API key". Verified: the file has no `<input>`, no `localStorage`/`prompt`/key capture — only display text + a `restart_sidecar` invoke. The exclusion is legitimately scoped and the wizard/settings subtrees remain covered by `test_no_api_key_input_field_in_wizard_or_settings`. The risk is drift: a future edit could add a real capture surface to `crash-banner.ts` and this gate would no longer catch it.

**Fix:** Keep the exclusion, but consider tightening: exclude only when the match is the known guidance string, or add an assertion that `crash-banner.ts` contains no `<input>`/`createElement("input")`/`prompt(`. Low priority.

### IN-02: `map_curate_result`'s null-playlist → zero-tracks branch is dead in the production flow

**File:** `tauri/src-tauri/src/library_cmds.rs` (`map_curate_result`, the `else` flat-ids branch with empty `track_ids`) + the `curate_empty_playlist_maps_to_zero_tracks` unit test.

**Issue:** `_cmd_library_curate` exits **1** (stderr) when `result.playlist is None`, so `parse_cli_json` returns `Err` before `map_curate_result` is ever called with a null playlist. The "null playlist → 0 tracks" path and its test only exercise a shape the CLI never emits on exit 0. Harmless (defensive/forward-compat), but the test asserts behavior that cannot occur in production — note it so it isn't mistaken for live coverage.

**Fix:** None required. Optionally annotate the test as forward-compat-only.

### IN-03: Unnecessary `f`-prefix on placeholder-free f-strings in the stats human-output branch

**File:** `src/vibemix/__main__.py` (`print(f"\nLibrary stats")`, `print(f"  failed:   0")`)

**Issue:** Two `print(f"…")` calls have no interpolation placeholders — the `f` prefix is noise (minor style; many linters flag F541).

**Fix:** Drop the `f` on the two literal lines.

### IN-04: First `monkeypatch.setattr(m, "open_store", …)` in `test_seeded_store_reports_indexed_count` is dead

**File:** `tests/library/test_stats_cli.py:65-70`

**Issue:** `_cmd_library_stats` does a function-local `from vibemix.library.store import open_store`, so the effective binding is `vibemix.library.store.open_store` (patched at lines 71-74). The earlier `monkeypatch.setattr(m, "open_store", …, raising=False)` patches a name `__main__` does not use — dead but harmless. Tests pass.

**Fix:** Remove the dead first monkeypatch to avoid implying `__main__.open_store` is the binding under test.

---

## Verdict

**SHIP — conditional on resolving CR-01.**

The library-stats CLI, the curate Rust/CLI/TS contract, anti-slop honesty, offline guarantee, error propagation, and CDJ-Whisper design are all sound and well-tested. The blocker is the pill collapsed-hover peek: as written, the card is positioned (`top:64px`) below a fixed 44px `overflow:hidden` window and is clipped in the only state it appears — the feature ships invisible. Verify the actual collapsed window height on-device; if it is the 44px default, the peek must be repositioned or the window grown on hover. WR-01 (add the peek DOM/visibility test) should land with the fix. WR-02/03/04 and the Info items are quality cleanups that need not block.

---

_Reviewed: 2026-05-25T17:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
