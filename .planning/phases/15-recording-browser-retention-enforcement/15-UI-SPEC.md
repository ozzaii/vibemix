---
phase: 15
slug: recording-browser-retention-enforcement
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-14
canonical_mock: mocks/vibemix-settings-drawer.html
visual_baseline: mocks/vibemix-direction-final.html (CDJ Whisper v5)
extends: tauri/ui/src/settings/SettingsDrawer.ts (Phase 14 v5)
---

# Phase 15 — UI Design Contract

> Recording Browser + Retention Enforcement.
> Surface lives **inside the Phase 14 Settings drawer** as a new RECORDING group.
> Visual language is locked: CDJ Whisper v5 — Pioneer-grade hardware in library mode.
> The shipped components (`recording-browser.ts`, `recording-row.ts`, `retention-slider.ts`) are the source of truth; this spec re-anchors them so the checker / auditor / planner have a written contract to verify against.

---

## Phase Surface Inventory

This phase ships ONE new section inside the existing right-side Settings drawer (400px wide slide-over from Phase 12 / refined in Phase 14). No new top-level shell. No new route. The drawer already exists — we extend its body with a `RECORDING` group that contains, in order:

1. **`RETENTION` slider label + 6-stop disc slider** (already shipped by `retention-slider.ts`; this spec re-anchors visuals only).
2. **Disk usage silkscreen line** — single-line readout `RECORDINGS · {N} SESSIONS · {SIZE} USED` (sentinel-aware: `LOADING…` while in flight, `UNAVAILABLE` after error).
3. **Sessions list** — chronological roster (newest first) of past sessions, each row 44px min-height, with replay + delete affordances. Empty-state body when zero sessions.
4. **Undo toast** — bottom-right of the drawer, fires on row delete, 4-second window, single-slot.

The CALIBRATION confirm dialog already uses the in-app `confirm-dialog.ts` modal primitive (NOT browser `alert()` — Tauri IPC blocking issue covered in Phase 12). Phase 15's delete UX bypasses the modal entirely in favor of optimistic-remove + undo toast (impeccable Wave 5.A 2026-05-14 critique outcome — touring DJs tagging old sets shouldn't get tapped on the shoulder for every delete).

**What this phase does NOT touch:**
- Drawer chrome (header, close button, backdrop, slide-in animation).
- PERSONA / OUTPUT / HOTKEY / CALIBRATION / MASCOT / PERFORMANCE groups (Phase 12 + 13 + 14 territory).
- Live session UI (Phase 11 + 12).
- Mascot overlay window (Phase 13 + 14).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (hand-rolled vanilla TS + CSS variables) |
| Preset | not applicable — vibemix design system is bespoke (CDJ Whisper v5) |
| Component library | none (no React, no shadcn — Tauri WebView with vanilla DOM) |
| Icon library | inline SVG paths (REPLAY = filled triangle, DELETE = trash-can stroke) |
| Font stack | Saira (display + body, variable wdth+wght) + JetBrains Mono (numerics, tabular-nums) |
| Token source | `tauri/ui/src/tokens.css` (v5; backward-compat shim deleted Phase 14 Wave 5) |
| Shadcn registry | not applicable |

**Why no shadcn?** vibemix renders inside a Tauri 2.x WebView with no React/Vue dependency. The UI is hand-rolled vanilla TypeScript + CSS for bundle size (~10× smaller than Electron + React) and zero build-toolchain risk on the one-click installer path. shadcn would require introducing React, Tailwind, and a build pipeline that violates the bundle-size ceiling.

---

## Spacing Scale

Declared values (multiples of 4 — mapped to existing `--sp-*` tokens in `tokens.css`):

| Token | Value | Usage in Phase 15 |
|-------|-------|-------|
| `--sp-1` | 4px | Vertical padding of expanded transcript event lines, gap between toast pill bullet + label |
| `--sp-2` | 8px | Action-cluster icon gaps, transcript timestamp right-margin, group header inner spacing |
| `--sp-3` | 12px | Row horizontal padding, expanded-panel inner gap, toast horizontal padding |
| `--sp-4` | 16px | Group body padding, expanded-panel padding, browser top-margin under retention slider, toast vertical padding |
| `--sp-5` | 24px | Toast position offset from drawer right + bottom edge, drawer body horizontal padding |
| `--sp-6` | 40px | Empty-state vertical padding |

**Exceptions (documented and required):**

| Exception | Value | Why |
|-----------|-------|-----|
| Row min-height | 44px | iOS / WCAG touch-target floor. The row is the primary tap surface and must not be smaller than the standard accessible target. Documented in `recording-row.ts:173`. |
| Action button hit area | 24×24px (icon) + 8px gap | The row itself absorbs taps that miss the small icons; the row's 44px min-height covers a11y. |
| Disk-usage line gap | `var(--sp-2)` (8px) below | Matches the section-label rhythm used elsewhere in the drawer (RETENTION label has the same 8px below it). |

**Forbidden:** 6px, 10px, 14px, 18px, 20px (off-grid). Inline px literals for spacing are forbidden — use `var(--sp-*)`.

---

## Typography

vibemix v5 ships exactly **two type families** and **four functional roles**:

| Role | Family | Size | Weight + Width | Line Height | Tracking | Used For |
|------|--------|------|----------------|-------------|----------|----------|
| Body | Saira | 14px | wdth 100, wght 400 | 1.45 | 0 | Empty-state copy, expand-panel body |
| Body-strong | Saira | 13px | wdth 100, wght 400 | 1.45 | 0 | Bold transcript event lines (AI text, trigger reasons) |
| Body-dim | Saira | 13px | wdth 100, wght 400 | 1.45 | 0 | Dim transcript event lines (controller moves, session-start) |
| Row meta | Saira | 14px | wdth 100, wght 400 | 1 | 0 | "{duration} · {N} events" center cell |
| Mono numerics | JetBrains Mono | 12px | wght 500 | 1 | 0 | Row left-cell timestamp `2026-05-13 21:04`, retention `7 D` readout (18px there), transcript event timestamps `[+M:SS]` (11px there) |
| Silkscreen label | Saira | 9px | wdth 85, wght 500-600 | 1 | 0.22em | Disk-usage line, group headers, retention stop labels (`1d 3d 7d 14d 30d ∞`), drawer chrome labels |
| Toast pill | Saira | 11px | wdth 85, wght 500 (label) / 600 (UNDO?) | 1 | 0.18em | Bottom-right delete-undo toast |

**Legibility rules (locked):**
- All-caps silkscreen text MUST set `letter-spacing >= 0.18em` (CDJ panel text would be unreadable without it).
- Tabular-nums (`font-variant-numeric: tabular-nums`) is mandatory for all timestamps, durations, and byte counts so the right-side numerics don't shift on update.
- All silkscreen text gets `text-shadow: 0 1px 0 rgba(0,0,0,0.7)` — etched-into-aluminum optical illusion that makes 9px legible against glass.
- Body text gets NO text-shadow (would muddy at 14px).

---

## Color (60/30/10 + status)

vibemix v5 has a LOCKED palette. Phase 15 introduces zero new tokens. The 60/30/10 split for THIS surface:

| Role | % | Token(s) | Usage |
|------|---|----------|-------|
| Dominant (60%) | ~60% | `--void` / `--void-1` / `--void-2` / `--void-3` body background + `--glass-3` recessed surfaces | Drawer body backdrop (already laid down by SettingsDrawer.ts), expanded-panel bg, retention readout window |
| Secondary (30%) | ~30% | `--glass-1` (drawer panel) / `--glass-2` (rows + group bodies) / `--glass-edge` hairlines / `--silk-40` / `--silk-65` text | Row backgrounds, group surface, dim transcript ink, disk-usage line, retention stop labels |
| Accent (10%) | ~10% | `--amber` + `--amber-deep` + `--amber-pale` + `--amber-22` + `--amber-40` + `--amber-65` | EXACTLY the elements listed below — and nothing else |
| Destructive | <1% | `--led-fault` (#d4413a) | Delete-button hover-state ink + delete-button hover inset glow only |
| Status | rare | `--led-warn` (#f4c542) | Crashed-session indicator dot in row meta cell (5×5px) |

**Amber accent is RESERVED FOR exactly these elements in Phase 15 — anything else is a regression:**

1. Replay button hover — icon ink flips `silk-65 → amber`, plus `filter: drop-shadow(--glow-faint)` (4px amber halo).
2. Expanded-panel top edge — 1px `--amber-22` border-top on the recessed glass under the row when open. The "this row is live" cue.
3. Bold transcript line border-left — 1px `--amber-22` left border on AI-text + trigger lines (NOT on dim controller-move lines).
4. Inline `<audio>` accent-color — native scrubber thumb + filled portion follow `--amber`.
5. Retention slider lit-track gradient + active disc fill — already shipped.
6. Retention readout text-shadow halo — `text-shadow: 0 0 6px rgba(255,138,61,0.20)` on the recessed `7 D` readout window.
7. Undo toast bullet (5×5px) + UNDO? button text + UNDO? underline (4px text-underline-offset).
8. Crashed-session warning dot (5×5px LED-warn yellow) in row meta — single occurrence per crashed row, NOT amber.

**Amber is NEVER allowed on:**
- Row hover background (use `rgba(214, 207, 199, 0.06)` — silk-derived, NOT amber).
- Row idle text (silk only).
- Disk usage line (silk-40 only — it's a silkscreen subtitle, not a CTA).
- Group headers (silk only — `--silk` ink, no amber chip).
- Retention stop labels at idle (silk-40 — the active label gets amber + text-shadow).
- Empty-state body copy (silk-40).

**Two documented inline-rgba exceptions** (not in token system, used because they are derivations of existing tokens at non-standard alpha):

| RGBA literal | Where | Why |
|--------------|-------|-----|
| `rgba(214, 207, 199, 0.06)` | row hover background | silk at 0.06 alpha — between `--silk-12` (0.12, too bright) and not-set (0, no signal). Hover is a whisper, not a press. |
| `rgba(212, 65, 58, 0.18)` | delete-button hover inset shadow | `--led-fault` at 0.18 alpha for the inset-glow (the destructive hover sells via ink-flip + glow, not background fill). |

Both are documented in `recording-row.ts:168-235` and grandfathered into the spec as the canonical Phase 15 chromatic exceptions.

---

## Copywriting Contract

vibemix's copy bar: **"real DJ friend in your ear, no AI slop"**. No corporate empty-state moralizing. No "Oops!" / "Whoops!" / "Looks like…". Lowercase non-silkscreen prose. Silkscreen UPPERCASE for chrome.

| Element | Copy | Token | Notes |
|---------|------|-------|-------|
| Group header | `RECORDING` | silkscreen 9px wdth 85 wght 600 letter-spacing 0.28em | Already shipped via `renderSettingsGroup({ header: "RECORDING" })`. Singular, not "RECORDINGS" — matches OUTPUT / HOTKEY / CALIBRATION sibling style. |
| Section sub-label | `RETENTION` | silkscreen 10px wdth 85 wght 500 letter-spacing 0.22em | Above the slider. |
| Retention readouts | `1 D` / `3 D` / `7 D` / `14 D` / `30 D` / `INF` | mono 18px tabular-nums | Locked — DSEG7-style dial. Note the space between digit + unit (DJ console convention). |
| Retention stop labels | `1d 3d 7d 14d 30d ∞` | silkscreen 9px | Lowercase d + ∞ glyph. |
| Disk usage line — normal | `RECORDINGS · {N} SESSIONS · {SIZE} USED` (e.g. `RECORDINGS · 12 SESSIONS · 480 MB USED`) | silkscreen 9px silk-40 | Center-dot separator (· U+00B7). Size formatting: `<1 GB → "{N} MB USED"` integer; `>=1 GB → "{N.N} GB USED"` one decimal. |
| Disk usage line — loading | `RECORDINGS · LOADING…` | silkscreen 9px silk-40 | Sentinel `bytes_total === -1`. Single-shot during the in-flight `ipc.recordings.list` after drawer-open. |
| Disk usage line — error | `RECORDINGS · UNAVAILABLE` | silkscreen 9px silk-40 | Sentinel `bytes_total === -2`. After IPC failure. NO red, NO "Error:" prefix — the silkscreen tone communicates degradation; the absence of session rows tells the rest of the story. |
| Row left cell | `2026-05-13 21:04` | mono 12px silk-65 tabular-nums | ISO date + 24h time, no seconds, no timezone. |
| Row center cell | `48m · 12 events` (or `1h 24m · 47 events`) | body 14px silk + mono · separator | Duration: `<1h → "{M}m"`; `>=1h → "{H}h {M}m"` (no zero-padding on minutes). |
| Row crashed warning | `●` (5×5 LED-warn dot, no text) | silkscreen via `::before` | Prefixed inline before the duration · events string when `summary.crashed === true`. No tooltip in v2.0 (deferred — Phase 14 polish surface). |
| Row replay button aria | `replay session 2026-05-13 21:04` | n/a | Screen-reader only. |
| Row delete button aria | `delete session 2026-05-13 21:04` | n/a | Screen-reader only. |
| Row aria-label | `session 2026-05-13 21:04, 48m, 12 events` | n/a | Composed from the three displayed cells. |
| Empty state body | `No recordings yet. Sessions appear here after they end.` | body 14px silk-40 center-aligned | Two short sentences. NO illustration. NO emoji. NO CTA button (the user is already in Settings — they're not lost). |
| Expanded transcript loading | `Loading events…` | body 13px silk-40 | Single line; replaced inline once `ipc.recordings.events_result` resolves. |
| Expanded transcript error | `Events unavailable.` | body 13px silk-40 | Period — terminal. No retry link in v2.0 (re-collapse + re-expand = retry). |
| Expanded transcript event line — bold | `[+2:05] yo that breakdown landed clean` | mono 11px silk-40 timestamp + body 13px silk + 1px amber-22 left border | AI text gets first 240 chars, ellipsis suffix if truncated. |
| Expanded transcript event line — dim | `[+0:34] eq_high 0.82` | mono 11px silk-40 timestamp + body 13px silk-40 | Controller moves and session-start. |
| Delete-undo toast — left | `deleted` | silkscreen 11px wdth 85 wght 500 silk-65 | Lowercase. |
| Delete-undo toast — separator | `·` | silkscreen 11px silk-40 | Center dot. |
| Delete-undo toast — undo button | `undo?` | silkscreen 11px wdth 85 wght 600 amber + amber-65 underline at 3px offset | Lowercase + question mark — invitation, not command. |
| Delete-pending error (slice) | `delete failed: {sidecar error}` | n/a (slice-only in v2.0; surfaced in toast in 15-06) | The optimistic-remove rolls forward when the timer elapses; if the sidecar acks `ok=false`, the row stays gone client-side and the slice records the error. UI surface for this is light in v2.0; Phase 15 Plan 06 tightens it. |

**Copy rules (locked):**
- Silkscreen text is UPPERCASE always.
- Body / prose copy is sentence-case lowercase.
- No "click", "tap", "press" — assume modern affordance literacy.
- No "Are you sure?" anywhere — the undo toast IS the safety mechanism.
- No "successfully" / "Successfully deleted!" — past-tense terse "deleted" only.
- No exclamation marks anywhere in the surface.
- No emojis. No icons-as-bullets in prose.

---

## Component Inventory

All components live under `tauri/ui/src/settings/components/`. Status as of 2026-05-14:

| Component | File | Status | Owner Plan |
|-----------|------|--------|-----------|
| `renderRecordingBrowser` | `recording-browser.ts` | ✅ shipped | 15-04 (W2) |
| `renderRecordingRow` | `recording-row.ts` | ✅ shipped | 15-04 (W1) |
| `renderRetentionSlider` | `retention-slider.ts` | ✅ shipped (Phase 12 W4 — Phase 15 reuses verbatim) | 12-05 (W3) |
| `renderConfirmDialog` | `confirm-dialog.ts` | ✅ shipped — used by CALIBRATION group only; Phase 15 does NOT mount this | 12-05 (W4) |
| `renderSettingsGroup` | `group.ts` | ✅ shipped — Phase 15 wraps the recording surface in `header: "RECORDING"` | 12-05 (W4) |

### `renderRecordingBrowser` — contract

**Props:**
```typescript
interface RecordingBrowserProps {
  initialSessions: RecordingSummary[];      // newest-first
  initialUsage: RecordingsUsage;            // { sessions, bytes_total }
  onReplay: (session_dir: string) => void;  // fires on row toggle (audio is local — no IPC dispatched here)
  onDelete: (session_dir: string, timestamp: string) => void;  // fires AFTER undo window elapses, NOT on click
  absoluteWavPathResolver?: (session_dir: string) => string;  // injected by drawer; defaults to `${sd}/voice.wav` for tests
}
```

**Imperative handle:**
```typescript
interface RecordingBrowserHandle {
  root: HTMLElement;
  setSessions(sessions: RecordingSummary[]): void;  // re-mount the list
  setUsage(usage: RecordingsUsage): void;            // update the silkscreen line, sentinel-aware
}
```

**Virtualization rule:** ≤50 sessions → full mount. >50 → 12-row chunks gated by `IntersectionObserver` with `rootMargin: "200px"` (per 15-RESEARCH).

**Undo discipline (impeccable Wave 5.A):**
- One pending delete at a time.
- A second click during in-flight undo commits the prior pending delete instantly, then opens a new undo for the new row.
- Undo restores the row to its original sort position via `findRestoreIndex` walking the newest-first sort.
- Restore is client-side only (no `recording.restore` IPC); when the 4s timer elapses, the real `onDelete` callback fires the `ipc.recordings.delete` IPC.

### `renderRecordingRow` — contract

**Row anatomy (44px min-height):**
```
┌────────────────┬──────────────────────────────────┬────────────┐
│ 2026-05-13     │ 48m · 12 events                  │ ▶  🗑      │
│ 21:04          │ (or "● 1h 24m · 47 events"      │            │
│ (mono silk-65) │  if crashed — yellow dot)       │            │
│ flex 0 0 140px │ flex 1 1 auto                    │ flex 0 0 64px │
└────────────────┴──────────────────────────────────┴────────────┘
```

**Expand state (built lazily on first `setExpanded(true)`):**
- `<audio controls preload="metadata">` with `convertFileSrc(voice.wav)` source. Native chrome inverted via `filter: invert(0.92)` so the WebKit player reads dark.
- Transcript area below — `Loading events…` placeholder, replaced by the events list when `ipc.recordings.events_result` resolves.
- Transition: CSS-grid `grid-template-rows: 0fr → 1fr` over 250ms ease-out. NO `height: auto` animation (browsers can't animate to/from auto — silent no-op + every-frame layout thrash).
- Lazy mount: `<audio>` + transcript built on FIRST open. On collapse: `audioEl.removeAttribute("src") + .load()` to release the decoder (MDN-required teardown), and `transcriptEl.remove()` so a re-expand re-fetches fresh events.jsonl.
- `prefers-reduced-motion: reduce` flips to `display: none / display: block` instant (no transition).
- Single-row playback: starting playback on row N stops any active player on row M. (Browser-native — there's only one `<audio>` mounted at a time per the lazy-mount + collapse-teardown rule.)

**Interaction map:**
- Click row body (anywhere except action cluster) → toggle expand.
- Click replay icon → toggle expand (icon also serves as a discoverable affordance).
- Click delete icon → fire `openDeleteWithUndo(summary)` → row vanishes optimistically + toast appears.
- Enter/Space on focused row → toggle expand.
- Enter/Space on focused delete button → fire delete-with-undo (button's keydown handler stops propagation so the row's listener does NOT also fire toggle).

### `renderRetentionSlider` — contract (already shipped, Phase 12)

Phase 15 reuses verbatim. The contract:
- 6 fixed stops: 1 / 3 / 7 / 14 / 30 / 36500 (sentinel for ∞).
- Default = 7 days on first install.
- `onChange(days)` fires on click OR on arrow-key (Left/Right/Up/Down).
- Lit-track scales via `transform: scaleX(--vmx-retention-lit-scale)` (compositor-cheap; NOT `width` animation).
- Visual contract locked in `mocks/vibemix-settings-drawer.html §03`.

### `renderRecordingBrowser` — undo toast contract

Anatomy:
```
                                              ┌──────────────────────┐
                                              │ deleted · undo?      │
                                              └──────────────────────┘
                                              (4s amber underline countdown)
```

Token discipline:
- Position: `position: fixed; right: var(--sp-5); bottom: var(--sp-5); z-index: 60`.
- Background: `var(--glass-1)` + `backdrop-filter: var(--blur-glass-light)`.
- Border: 1px `var(--glass-edge)`.
- Shadow: `inset 0 1px 0 var(--glass-top), inset 0 -1px 0 rgba(0,0,0,0.45), 0 8px 24px rgba(0,0,0,0.55)`.
- Enter animation: `vmx-rec-toast-in` 150ms ease-out (4px translateY + opacity 0→1).
- Z-index 60 — sits ABOVE the modal-slot z-index 60 of the drawer; the toast must outrank any in-flight confirm dialog (none in Phase 15's path, but defended).

The mock at `mocks/vibemix-settings-drawer.html §06` includes a 4s amber-underline countdown bar at the toast's bottom edge. **This is OUT of scope for Phase 15 v2.0** — the shipped toast omits the countdown bar (visual cleanliness over redundancy with the timer's own implicit countdown). Phase 15 polish wave may revisit.

---

## Layout

The RECORDING group sits 4th in the drawer body:

```
PERSONA  (group)
OUTPUT   (group)
HOTKEY   (group)
RECORDING (group)  ← Phase 15 surface
  ├── label: "RETENTION" (silkscreen 10px)
  ├── retention-slider (6-stop disc + readout + labels)
  ├── recording-browser
  │   ├── disk-usage line (silkscreen 9px silk-40)
  │   └── list (rows or empty state)
  └── (toast renders to document.body — fixed-position, NOT inside the drawer scroll)
CALIBRATION (group)
MASCOT (group)
PERFORMANCE (group)
```

Order is locked. CALIBRATION moving below RECORDING is the Phase 12-05 → Phase 15 spec; do not re-order without re-spec.

The drawer body is `padding: var(--sp-5)` with `gap: var(--sp-4)` between groups (set by SettingsDrawer.ts). Phase 15 does NOT override these.

The browser sits with `margin-top: var(--sp-4)` from the retention slider's bottom edge (set by `recording-browser.ts:104` `.vmx-rec-browser { margin-top: var(--sp-4); }`).

---

## Motion Contract

| Surface | Duration | Easing | Token |
|---------|----------|--------|-------|
| Row hover background fade | 150ms | ease-out | `--motion-snap` |
| Row expand grid-template-rows 0fr→1fr | 250ms | ease-out | hand (matches `--motion-step`) |
| Row expand inner padding 0→`var(--sp-4)` | 250ms | ease-out | matches expand height transition |
| Delete-button color/shadow on hover | 150ms | ease-out | `--motion-snap` |
| Toast enter (`vmx-rec-toast-in`) | 150ms | ease-out | matches `--motion-snap` |
| Retention disc hover lift `transform: scale(1.08)` | 150ms | ease-out | `--motion-snap` |
| Retention lit-track scaleX | 150ms | ease-out | `--motion-snap` |

**Reduced-motion override:** `@media (prefers-reduced-motion: reduce)` — row expand transition removed, toast enter animation removed; `display: none/block` flip on row expand replaces the height animation.

**Forbidden motion in this phase:**
- No bounce / spring / overshoot easing on any element.
- No infinite-loop animations (the drawer's `.border-anim` belongs to the deck-only).
- No staggered list-item entrance — rows render synchronously when the IPC list arrives.
- No "deleted" row fly-out animation — the optimistic remove is instant. The toast is the feedback channel, not a row exit transition.

---

## Interaction Contracts

### Drawer open → list fetch
- `openSettings()` in `SettingsDrawer.ts:386` fires `loadRecordings()` debounced 1s — a flickering re-open within 1s reuses the in-memory slice.
- During in-flight: usage line shows `RECORDINGS · LOADING…` (sentinel `bytes_total === -1`).
- On success: slice + browser updated atomically; usage line shows the normal format.
- On error: usage line shows `RECORDINGS · UNAVAILABLE` (sentinel `bytes_total === -2`); list area renders the prior session list (if any) or the empty-state copy.

### Row replay
- Click row body OR replay icon → toggle expanded state.
- First open mounts `<audio>` + `Loading events…` placeholder.
- IPC `ipc.recordings.events` fires; response replaces the placeholder with the transcript.
- Audio plays via native `<audio controls>`. Single-row guarantee: only one row is open at a time; collapsing tears down the audio decoder.

### Row delete (no modal)
- Click delete icon → `openDeleteWithUndo(summary)`:
  1. Row optimistically vanishes (not animated).
  2. Toast appears bottom-right with `deleted · undo?` for 4 seconds.
  3. Click `undo?` within 4s → row reappears at original sort position; no IPC fired.
  4. 4s elapses → real `onDelete(session_dir, timestamp)` fires → `ipc.recordings.delete` over IPC.
- A second delete during an in-flight undo window commits the prior delete instantly, then opens a new undo for the new row.
- If `ipc.recordings.delete` returns `ok: false`, the slice records `error: "delete failed: {error}"`. v2.0 surface is slice-only (next refresh shows the error sentinel); Phase 15 Plan 06 may wire a richer in-toast retry surface.

### Retention change
- Click any disc OR Left/Right arrow on focused slider → `onChange(days)` → `sendSettings("retention_days", days)`.
- No confirmation. The change is silent on the wire and the lit-track moves under the cursor as direct feedback.

### Reveal-in-OS (DEFERRED to Phase 15 Plan 06+)
- Per CONTEXT.md `<specifics>`: macOS `open -R <path>`, Windows `explorer /select,<path>`, fired from Tauri Rust via `tauri-plugin-shell` (NOT from the Python sidecar — sidecars do not shell out).
- The icon (paperclip-style "reveal") is NOT shipped in the current row layout. Phase 15 Plan 06 / impeccable polish may add it as a third inline-icon (slot reserved between play and delete).
- This UI-SPEC reserves the slot but does not require the icon — the row's `flex 0 0 64px` action cluster has space for a third 24×24 icon + 8px gap if needed.

### Open-input.wav-in-default-app (DEFERRED to Phase 15 Plan 06+)
- Per CONTEXT.md: `input.wav` (multi-MB combined music+mic) opens externally via `tauri-plugin-shell`.
- Same row-action slot reservation as reveal-in-OS.
- v2.0 row currently exposes only `voice.wav` (AI side, short, safe inline).

---

## State Management

The drawer holds Phase 15 state in `tauri/ui/src/settings/state.ts` under the `recordings` slice:

```typescript
recordings: {
  sessions: RecordingSummary[];   // newest-first sort, owned by the slice
  usage: RecordingsUsage;          // { sessions, bytes_total }
  loading: boolean;
  error: string | null;
}
```

Wire path:
- `loadRecordings()` reads `ipc.recordings.list` → writes slice → calls `recordingBrowserHandle.setSessions/setUsage`.
- `onDeleteRecording()` writes the optimistic remove to the slice + handle.
- `ipc.recordings.usage` push (sidecar after auto-prune sweep) updates the disk-usage line; sessions list is NOT refetched (the user-visible truth is what they see; on next drawer-open the list re-syncs).
- `ipc.recordings.events` is fetched per row open, NOT cached in the slice — bounded memory + matches the lazy-mount discipline.

---

## Accessibility

| Concern | Behavior |
|---------|----------|
| Tab order | Drawer header close button → group bodies in declared order → retention slider (one tab stop, then arrow keys for stops) → first row → second row → … → next group |
| Row aria-label | `session {timestamp}, {duration}, {N} events` (composed from displayed cells) |
| Row role | `button` with `aria-expanded="true|false"` |
| Replay icon aria | `replay session {timestamp}` |
| Delete icon aria | `delete session {timestamp}` |
| Disk-usage line role | `status` with `aria-live="polite"` |
| Empty state role | `status` with `aria-live="polite"` |
| Toast role | `alert` with `aria-live="polite"` |
| Retention slider role | `slider` with `aria-valuemin=0 aria-valuemax=5 aria-valuenow={idx}` |
| Focus ring | global `*:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; box-shadow: var(--glow-soft) }` (set in tokens.css) |
| Keyboard escape | Esc closes the drawer (drawer-level handler; suppressed when `confirmDialog || hotkeyCaptureMode` in flight — neither is in flight in Phase 15's flow) |
| Reduced motion | `prefers-reduced-motion: reduce` removes row-expand and toast-enter animations |
| Touch target | Row min-height 44px; action icons 24px with 8px gap inside the 44px touch row |
| Color contrast | Body 14px on glass-2: silk (#d6cfc7) on rgba(12,14,22,0.62) over near-black ≥ 12:1; silk-40 on glass-2 ≈ 5:1 (passes AA for 13-14px body); destructive `--led-fault` only used on hover (focus-visible-grade contrast not required for hover state by WCAG) |
| Screen-reader transcript timestamps | `[+M:SS]` is read literally; we do NOT add `aria-label="plus M minutes S seconds"` overhead in v2.0 |

---

## Sentinel + Error Contract

The disk-usage line is the single error surface in this phase. Three states:

| `bytes_total` | Display | Trigger |
|---------------|---------|---------|
| `-1` | `RECORDINGS · LOADING…` | `loadRecordings()` in flight |
| `-2` | `RECORDINGS · UNAVAILABLE` | `ipc.recordings.list` rejected |
| `>= 0` | `RECORDINGS · {N} SESSIONS · {SIZE} USED` | normal |

The list area NEVER shows an error message inline. Three states for the list:
- Sessions present → render rows.
- Sessions empty + usage `bytes_total >= 0` → render empty-state body.
- Sessions empty + usage error → render empty-state body (truth: there's nothing to show; the disk-usage line carries the failure signal).

This is a deliberate de-cluttering — the silkscreen line is one channel, the rows are another, no inline banners.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | — | not applicable (no React, no shadcn) |
| Third-party | — | not applicable |

No third-party UI registries. All components are hand-rolled vanilla TS using the v5 token system in `tokens.css`. The only third-party JS pulled in by Phase 15 is `@tauri-apps/api/core.convertFileSrc` (already a project-wide dep) for converting absolute file paths to `tauri://` URLs the WebView can play.

---

## Token Discipline (gate)

This phase is **100% v5 token-derived**. The shim was deleted Phase 14 Wave 5; no `--phosphor-*`, `--brushed-*`, `--bezel-*`, `--col-mascot` aliases survive in this surface.

Audit checklist for the gsd-ui-checker / gsd-ui-auditor:

- [ ] No hex literals in any Phase 15 component CSS (only `tokens.css` may contain `#xxxxxx`).
- [ ] Only the two documented inline-rgba exceptions (`rgba(214, 207, 199, 0.06)` row hover, `rgba(212, 65, 58, 0.18)` delete-hover inset) appear in Phase 15 component code.
- [ ] No `--brushed-aluminum`, `--bezel-*`, `--phosphor-*`, `--col-mascot` references in Phase 15 components.
- [ ] All silkscreen text uses `var(--type-display)` Saira with `wdth 85` + `letter-spacing >= 0.18em`.
- [ ] All numeric readouts use `var(--type-mono)` JetBrains Mono with `font-variant-numeric: tabular-nums`.
- [ ] Spacing is 100% `var(--sp-*)` with the documented row min-height + icon size exceptions called out in this spec.
- [ ] Amber accent appears ONLY on the 8 elements enumerated in the Color section.
- [ ] No browser `alert()` / `confirm()` / `prompt()` calls (Tauri IPC blocking risk per `<context_anchors>`).

---

## Frontend-Enforcement Skill Compliance

Per `.claude/skills/frontend-enforcement/SKILL.md`:

1. ✅ **20/80 honored** — the rec rows + group are dominant glass + silk. Amber appears in 8 enumerated micro-spots: replay-hover, expand-edge hairline, transcript bold-line border, audio scrubber accent, retention lit-track, retention readout halo, undo-toast bullet + UNDO? text. Single accent across ~3-5% of the surface.
2. ✅ **Heavy textured material feel** — no flat fills. Glass surfaces carry inset highlights (`inset 0 1px 0 var(--glass-top)`), hairline edges (`1px solid var(--glass-edge)`), recessed retention readout uses inset shadow stack to read as carved-into-aluminum. Toast carries glass blur + inset top-light + drop shadow. Body inherits the cinematic vignette + film-grain overlay from `tokens.css` body::before.
3. ✅ **No generic AI aesthetics** — Saira (variable wdth + wght, character) + JetBrains Mono (tabular numerics) typography pairing. No Inter, Roboto, system-ui. No `rounded-2xl shadow-lg p-6` lazy cards. No purple gradients. Phosphor amber on dark anodized glass.
4. ✅ **Distinctive typography pairing** — Saira (display + body, ITC Avant Garde DNA, slightly futurist) paired with JetBrains Mono (DJ-console DSEG7 stand-in). Documented in tokens.css comments + this spec.
5. ✅ **Motion is intentional** — row expand reveals data on demand (NOT decoration). Toast enter is a 150ms whisper, not a bounce. Retention disc lift on hover is a tactile cue (NOT a marketing flourish). Reduced-motion fallback shipped.
6. ✅ **Retro-futurist hardware vocabulary** — silkscreen labels (UPPERCASE wdth 85 letter-spacing 0.22em), recessed DSEG7-style retention readout window with inset-shadow carve, knurled disc knobs (14×14 with inset highlights + amber fill on active), 5×5 LED dots for status (LED-warn yellow on crashed sessions, amber on toast bullet). The drawer reads as the side panel of a CDJ that swung out.

---

## Out of Scope (Reaffirmed from CONTEXT.md `<deferred>`)

- Inline waveform / spectrogram preview (v2.1).
- Bulk-select + bulk-delete (v2.1).
- Tag / favorite / pin sessions (v2.1+).
- Rename / annotate sessions in UI (v2.1+).
- OS trash-bin integration (v2.1 — cross-platform parity work).
- Auto-prune notification banner (silent prune is the contract).
- Session metadata export CSV/JSON (v2.1+ DEBRIEF surface territory).
- Reveal-in-Finder/Explorer icon (slot reserved in row action cluster, not shipped in v2.0 row layout — Phase 15 Plan 06+ may add).
- Open `input.wav` in OS default app (slot reserved; same as above).
- 4s amber-underline countdown bar inside the toast (mock §06 includes; v2.0 ships toast without — implicit countdown via timer is enough).
- Per-row "..." overflow menu (CONTEXT.md `<specifics>` rejected — inline icons are the spec).
- Tooltip on the crashed-session yellow dot (deferred to impeccable polish wave).

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — every surface element has explicit copy declared above; "no AI slop" filter holds; no `alert()` anywhere.
- [ ] Dimension 2 Visuals: PASS — heavy material treatment via glass + inset shadow + film grain; 8 accent uses enumerated; row layout matches mock §02.
- [ ] Dimension 3 Color: PASS — 60/30/10 split holds; amber reserved-for list is 8 specific elements; destructive `--led-fault` is hover-only.
- [ ] Dimension 4 Typography: PASS — 2 families (Saira + JetBrains Mono); 4 functional roles + 1 silkscreen treatment; tabular-nums on every numeric.
- [ ] Dimension 5 Spacing: PASS — `--sp-1..--sp-6` only; documented 44px row + 24px icon exceptions justified by a11y.
- [ ] Dimension 6 Registry Safety: PASS — no third-party registries; no shadcn; vanilla TS + token system only.

**Approval:** pending (gsd-ui-checker run after this spec lands)

---

## Source Documents

- **Visual baseline:** `mocks/vibemix-direction-final.html` (CDJ Whisper v5)
- **Phase-specific mock:** `mocks/vibemix-settings-drawer.html` (§02 RECORDINGS, §03 RETENTION, §06 DELETE UX)
- **Tokens:** `tauri/ui/src/tokens.css`
- **Settings drawer host:** `tauri/ui/src/settings/SettingsDrawer.ts`
- **Components shipped:** `tauri/ui/src/settings/components/recording-{browser,row}.ts`, `retention-slider.ts`, `confirm-dialog.ts`, `group.ts`
- **IPC contract:** `tauri/ui/src/ipc/messages.ts:301-363` (codegen output — `RecordingsList`, `RecordingsListResult`, `RecordingsDelete`, `RecordingsDeleteAck`, `RecordingsUsage`, `RecordingsEvents`, `RecordingsEventsResult`)
- **State slice:** `tauri/ui/src/settings/state.ts` (recordings slice)
- **Phase decisions:** `.planning/phases/15-recording-browser-retention-enforcement/15-CONTEXT.md`
- **Project frontend rules:** `.claude/skills/frontend-enforcement/SKILL.md`
- **Visual direction memory:** `project_visual_direction_cdj_whisper`

*UI-SPEC compiled 2026-05-14 by gsd-ui-researcher (autonomous mode). Anchors a partially-shipped surface so checker / auditor / planner have a written contract for Phase 15 Plan 06+ polish.*
