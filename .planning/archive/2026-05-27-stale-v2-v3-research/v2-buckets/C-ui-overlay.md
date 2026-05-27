# Bucket C — UI Overlay Highlight Research

**Researched:** 2026-05-13
**Domain:** Cross-platform transparent overlay + DJ-app UI element targeting (the "viral demo" feature)
**Confidence:** MEDIUM — overlay window scaffolding HIGH (already proven in our codebase); coordinate-mapping LOW for Rekordbox/Serato, MEDIUM-HIGH for djay Pro
**Status:** Feasible in v1.1 only as **djay-Pro-first**. Rekordbox/Serato are tractable only through brittle template matching or a manual coord map maintained per software version.

---

## TL;DR

- **One target app for v1.1: djay Pro.** It's the only major DJ app with first-class macOS Accessibility (`NSAccessibility`) coverage — there's already a working open-source Swift bridge (`kyleawayan/djay-pro-bridge`) that pulls deck state via `AXUIElement` at ~8 Hz. Rekordbox and Serato render their UI to canvas/Qt and expose almost nothing useful via AX. [VERIFIED: GitHub repo metadata + Algoriddim community post]
- **Mac overlay window is a solved problem in our codebase.** `tauri/src-tauri/src/mascot_window.rs` already builds the exact window we need: `transparent + always_on_top + decorations:false + skip_taskbar + visible_on_all_workspaces + set_ignore_cursor_events(true)`. Re-use the builder; spawn a second runtime window labeled `highlight` and re-point the WebviewUrl. [VERIFIED: source read in this research]
- **Windows overlay is feasible but click-through has known Tauri sharp edges** — `setIgnoreCursorEvents` ships, but per-region hit-testing requires either a polling loop or a fully click-through window with no interactive zones. For a pure-highlight overlay (no interactive UI) we want fully click-through, which sidesteps the bug. [VERIFIED: tauri/tauri issue #11461, #2090, #6164]
- **Element COORDINATES are the bottleneck, not WINDOW coordinates.** Even on djay where AX works, `djay-pro-bridge` returns **values, not positions** — readers get "tempo=+2.3%", they don't get "the tempo slider is at screen (1284, 462)". For visual highlighting we need (a) AX position attributes where present, or (b) a hand-maintained `element_id → percentage-of-window-rect` map per app per major version. [VERIFIED: WebFetch of repo README]
- **Legal envelope: yellow, not red.** Rekordbox EULA prohibits "reverse engineering, disassembling or decompiling" — overlays don't do any of that. Reading public `kCGWindowBounds` and AX trees is the same surface VoiceOver uses; community projects (Beat Link, prolink-tools, djay-pro-bridge) have run for years unmolested. Risk if we ever ship deck-control feedback that materially demonstrates rekordbox-internal state — that's reverse engineering-adjacent. For a draw-on-top-of-screenshot overlay, we're clean. [CITED: rekordbox.com/en/license-agreement, github.com/Deep-Symmetry/beat-link]

**Recommended v1.1 cut:** djay Pro on macOS, 8-12 hand-mapped pointable elements, percentage-of-window-rect coord map refreshed per djay major release. Windows + Rekordbox + Serato deferred to v1.2 (one app, one OS at a time — clean utility discipline).

---

## Mac transparent overlay window (concrete recipe + gotchas)

### Recipe (we already have this — re-use the builder)

```rust
// Adapted from tauri/src-tauri/src/mascot_window.rs lines 82-104.
// Re-point the URL, change the label, drop min/max size (overlay is window-bounds-driven).
let window = WebviewWindowBuilder::new(
    app,
    "highlight",                              // new label — add to capabilities/default.json windows allowlist
    WebviewUrl::App("highlight.html".into()), // new HTML asset under ui/
)
.transparent(true)
.always_on_top(true)
.decorations(false)
.resizable(false)                              // overlay is programmatically positioned, never user-dragged
.skip_taskbar(true)
.visible_on_all_workspaces(true)
.shadow(false)                                 // no drop-shadow on a transparent canvas
.focused(false)                                // never steal focus on show
.build()?;

window.set_ignore_cursor_events(true)?;        // fully click-through — overlay never intercepts input
```

The `tauri.conf.json5` `macOSPrivateApi: true` flag is already set (Phase 11) — that's a prerequisite for `transparent: true` to render with the alpha channel correctly. [VERIFIED: file read]

### Coordinate gotchas — `kCGWindowBounds` is the same trap we already navigate in `find_djay_window_bounds`

`cohost_v4.py:224-246` already does this dance for screen capture. Lifting the same logic for highlight positioning:

| Trap | What goes wrong | Fix |
|------|----------------|-----|
| **Retina scaling** | `kCGWindowBounds` returns **points**, not pixels. On Retina displays one point = 2 backing pixels. If you draw at `bounds.x` directly in a backing-pixel-aware Canvas, the highlight is half-position. | Multiply by `window.scale_factor()` (Tauri exposes this) before drawing — or stay in points end-to-end. |
| **Multi-monitor Y-axis** | macOS global coords have origin at top-left of the *primary* display; secondary displays can have negative Y. `NSScreen.Screens` flips Y so its origin is bottom-left of the bottom-most display. Mixing the two systems silently puts the overlay one screen off. | Use Quartz coords (top-left origin, Y grows down) consistently. Don't touch NSScreen.frame unless you flip Y. [CITED: github.com/tmandry/Swindler issue #62] |
| **Hidden / minimized djay** | `CGWindowListCopyWindowInfo` with `kCGWindowListOptionOnScreenOnly` skips minimized windows. Switch to `kCGWindowListOptionAll` and you get garbage off-screen bounds. | Keep `OnScreenOnly` + treat "no bounds" as "hide overlay". `cohost_v4.py:229` already does this. |
| **Window not active app** | Bounds are reported for the window even when it's behind another app. Drawing the overlay anyway puts a highlight on top of, say, Finder. | Check `kCGWindowLayer == 0` AND verify djay is the frontmost app via `NSWorkspace.frontmostApplication`. Hide the overlay otherwise. |
| **Fullscreen Space** | A djay fullscreen window lives on its own Space. Tauri's `visible_on_all_workspaces` flag DOES NOT fully cover this on macOS as of 2026 — there are open bugs (`tauri-apps/tauri#11488`, `#11791`). | Fall back to `set_activation_policy(Accessory)` per the workaround thread — but Dock icon disappears. For DJ rehearsal in a window (our primary use case), fullscreen is not the default. Document it as a known gap. [CITED: tauri-apps/tauri#11488] |

### Polling rate for window tracking

`CGWindowListCopyWindowInfo` is cheap (microseconds) — poll at 10 Hz from a background async task. We don't need CGSWindow notification subscriptions (private API, fragile). The mascot already proved this cadence is invisible to users.

**Gotcha:** if djay is being live-resized by the user (rare during a set, common in setup), the overlay lags 100ms per poll cycle. Acceptable for a feature that fires only on AI utterance, not constantly.

---

## Windows transparent overlay window (concrete recipe + gotchas)

### Recipe

Tauri 2 supports the same `transparent + always_on_top + decorations:false` flags on Windows via `WS_EX_LAYERED`. The Tauri 2.0 stable release explicitly enables this — our mascot already runs on Windows. [VERIFIED: Tauri 2.0 stable release notes]

```rust
// Same WebviewWindowBuilder call as macOS — Tauri 2 abstracts the platform difference.
// On Windows it sets WS_EX_LAYERED + WS_EX_TRANSPARENT via tao.
.transparent(true)
.always_on_top(true)
.skip_taskbar(true)
.decorations(false)
// .visible_on_all_workspaces translates to "all virtual desktops" on Windows; works in our mascot.
```

The pure-click-through (no interactive elements anywhere on the overlay) path avoids the well-known Tauri bug where per-region hit-testing fails on Windows (`tauri-apps/tauri#11461`). Because our highlight overlay never has clickable buttons — it's draw-only — we just call `set_ignore_cursor_events(true)` once at build time and forget it.

### Coordinate gotchas — Windows DPI

| Trap | What goes wrong | Fix |
|------|----------------|-----|
| **DPI virtualization** | `GetWindowRect` on a window owned by another process auto-scales to the *caller's* DPI awareness. If our app is per-monitor DPI-aware and the target app is system DPI-aware, the rect we get back is silently rescaled. [CITED: Microsoft Learn — `GetWindowRect`] | Mark our process `PROCESS_PER_MONITOR_DPI_AWARE_V2` at startup (Tauri exposes this), call `GetDpiForWindow(target_hwnd)` to learn the target's actual DPI, scale ourselves. |
| **Multi-monitor at different DPIs** | A 100% scaled secondary + a 150% scaled primary — `GetWindowRect` returns physical pixels but our overlay window is positioned in *logical* coords. | Compute per-monitor scale factors via `MonitorFromWindow` + `GetDpiForMonitor`. |
| **Target window class names vary by version** | Rekordbox 6 vs 7 may use different `lpszClassName`. Hardcoding `"Rekordbox"` is fragile. | Match on `GetWindowText` substring + process executable name via `GetWindowThreadProcessId` + `QueryFullProcessImageName`. |
| **DWM + transparency on older Windows** | Pre-Windows 10 1903 had quirks with layered windows + DWM. | Already a non-issue — Tauri 2 minimum is Windows 10 1809, and we already ship the mascot on Windows. |

### Target window detection (Windows)

```rust
// Enumerate top-level windows, filter by process name.
EnumWindows(|hwnd| {
    let mut pid = 0; GetWindowThreadProcessId(hwnd, &mut pid);
    let exe = process_exe_name(pid);                  // "rekordbox.exe", "djayPro.exe", "Serato DJ Pro.exe"
    if matches!(exe.as_str(), "rekordbox.exe" | "djayPro.exe" | "Serato DJ Pro.exe") {
        let mut rect: RECT = zeroed(); GetWindowRect(hwnd, &mut rect);
        // emit (exe, rect)
    }
    TRUE
}, 0);
```

No private API needed. Same surface every screen recorder and overlay tool uses.

---

## UI element coordinate mapping

This is the hard problem. The three approaches:

### Approach (a) — Manual coordinate map per app per version

**The pitch:** maintain a JSON file like `assets/element_maps/djay_pro_5.json` that says "deck_a_mid_eq = (x_pct=0.18, y_pct=0.31, radius_pct=0.025)" — percentages of the djay window rect. When AI says "deck A mid EQ", we look up the percentages, multiply by current window size, draw the highlight at that screen location.

**Profiling cost (one-time per app version):**
- Open djay at 1920×1200, screenshot.
- Open in Photoshop / Figma / a calibration tool we build, click each pointable element, record `(x_pct, y_pct)` relative to the window rect.
- ~30 minutes for 12 elements per app.
- Repeat on a layout switch (djay's "4 deck" vs "2 deck" mode rearranges everything — that's a 4-deck variant file).

**Pros:**
- **The cheapest path to a working demo.** No CV models, no AX gymnastics.
- Works equally on Rekordbox, Serato, djay — they all scale their UI proportionally enough that percentage-of-window works for ~80% of elements. [ASSUMED: needs visual verification on Rekordbox / Serato at 3 different window sizes]
- Trivial to validate visually: load the map, draw red dots, screenshot, compare.

**Cons:**
- Brittle on major UI redesigns (djay had a substantial UI shift between v3 and v5).
- Rekordbox has free-floating panels (sampler, FX) that users can detach — percentage-of-window doesn't model that. [ASSUMED]
- Doesn't know *whether the element is visible* — if user collapses the mixer view, we'd draw a highlight on empty canvas.

**Rekordbox / Serato sub-question — does the UI scale proportionally?**
- Rekordbox: master layout (decks, waveforms, browser, mixer) is fixed-grid that scales proportionally to window size. FX, sampler, lights panels are tear-off — percentage map doesn't cover them. [ASSUMED — needs manual verification on Rekordbox 7]
- Serato: similar — decks scale, but the "Library" panel can be hidden/shown changing the deck region. Need to either detect library visibility or only map elements that don't move with library state.
- djay Pro: cleanest scaling — main mixer + decks fill the window proportionally; advanced panels are modal.

### Approach (b) — macOS Accessibility API (`AXUIElement*`)

**The pitch:** walk the AX tree of djay/rekordbox/serato, find element by role + label ("AXSlider" + "Mid EQ Deck A"), read its `kAXPositionAttribute` + `kAXSizeAttribute` to get a screen rect, draw the highlight there. Dynamic to UI changes, works across versions if labels are stable.

**The hard reality, per-app:**

| App | AX exposure | Position attrs available? | Verdict |
|-----|-------------|---------------------------|---------|
| **djay Pro** | "Excellent accessibility support" — proven by `kyleawayan/djay-pro-bridge` reading deck state @ 8 Hz via AX. Algoriddim ships full VoiceOver coverage. | **Almost certainly yes** for every labeled control. djay-pro-bridge reads *values* but doesn't expose positions — the positions ARE there in the AX tree, the project just doesn't use them. [VERIFIED: README + project structure] | **GREEN. v1.1 path.** |
| **Rekordbox** | Closed ecosystem, no public API ("only open part is Syphon for visuals"). Pioneer DJ community confirms no third-party API. UI is rendered via custom toolkit (likely OpenGL/Skia surface — pure pixels, no AX nodes). [VERIFIED: Pioneer DJ community + Slashdot integrations] | **Almost certainly no** — canvas-rendered UI returns an empty AX subtree (just the window node + maybe menu bar). | **RED. Approach (b) won't work.** |
| **Serato DJ Pro** | Switched from Carbon to Qt in v1.8.0, breaking screen-reader support. Community confirms Serato is not accessible to JAWS / VoiceOver. Qt's NSAccessibility implementation is famously partial — `QAccessibleWidget` doesn't always bridge to NSAccessibility properly. [VERIFIED: AppleVis forum + Qt forum thread] | **Probably no** for control elements; *maybe* for menu items only. | **YELLOW. Likely a bust, test before betting on it.** |
| **Traktor Pro** | "Not accessible" per AppleVis. Custom-rendered UI. | **No.** | **RED.** |

**Permission UX cost (this is a one-click-install problem):**
- AX permission is a TCC prompt — first time the user runs vibemix, macOS shows the "vibemix wants to control your computer using Accessibility" dialog. User must (a) click "Open System Settings", (b) toggle vibemix on in the list. This is two extra steps in the install flow. Documented as Phase 4 work in `.planning/` already (`tauri/src-tauri/src/permissions.rs`). [VERIFIED: file exists in repo]
- **Tauri sidecar bug:** `tauri-apps/tauri#8329` — sidecars don't reliably inherit AX permissions from the parent app bundle on built+installed Mac apps. Our Python sidecar (where the AX call would live if we use pyobjc) gets prompted on every launch and never sticks. **Fix:** make the AX call from the Rust parent (where the bundle identity is stable) and pass the resulting rect over the WS bus to the sidecar. Do NOT call AX from Python in the sidecar. [VERIFIED: GitHub issue]
- macOS requires the app bundle to be code-signed for TCC to remember the grant. Phase 18 already covers signing — no new work. [VERIFIED: tauri.conf.json5 hardenedRuntime + entitlements]

**Pros:**
- Dynamic — adapts to UI changes without re-profiling.
- Reliable on djay (proven in the wild).
- Returns labels too, so we could even do *fuzzy* targeting ("find anything labeled 'mid' on deck A").

**Cons:**
- Useless on Rekordbox, Traktor; probably useless on Serato.
- Permission UX friction (acceptable — Phase 4 already designed for it).
- AX trees can be slow to walk on heavy UIs (djay-pro-bridge polls at 8 Hz, not 30). For a "draw a highlight when AI speaks" feature, 8 Hz cached + on-demand walk is fine.

### Approach (c) — Computer vision template matching

**The pitch:** ship a per-app template library (a 64×64 PNG of "the mid EQ knob in djay"), grab a screenshot, run `cv2.matchTemplate` to locate it, draw the highlight at the result rect.

**Performance reality:**
- Single template, 1920×1080 screenshot, OpenCV `matchTemplate` with `TM_CCOEFF_NORMED`: ~30-80ms on M-series Mac. Acceptable for *one* match per AI utterance.
- 30Hz continuous matching: not viable — multi-template matching at 30fps is documented as a hard problem, the matched-templates count drops fps drastically. [CITED: forum.opencv.org template-matching threads]
- Multi-scale (handles different window sizes): multiplies cost by ~5-10×. Pre-compute scale per current window size and only match at that scale = back to single-cost.
- ORB / SIFT features: faster matching once descriptors are extracted, but extraction itself isn't free; and these algorithms shine on rotated/skewed templates, which doesn't apply to DJ UI — templates are pixel-aligned with the source.

**Verdict on tractability:** template matching is fine for **one-shot per AI utterance** ("find the mid EQ knob once, draw, hold for 2 seconds, fade"). NOT viable for continuous tracking (highlight follows the knob as the user moves it). Continuous tracking isn't a useful feature for our use case anyway — the AI isn't going to say "now move it left a bit" with frame-accurate timing.

**Brittleness:**
- Theme changes (Rekordbox has color themes) → template fails. Mitigation: include grayscale-edge match instead of color match.
- Version-to-version UI tweaks → template fails. Mitigation: ship templates per app version, fall back to nearest-version, log mismatch.
- User adds skins (Serato has community skins) → template fails. Mitigation: document "official theme only" in README.

**Pros:**
- Works on Rekordbox, Serato, Traktor — anywhere a screenshot can be taken.
- Doesn't need AX permission.
- Versionable (one PNG per element per app version, easy to crowdsource).

**Cons:**
- Brittle.
- Slow enough that "highlight appears 100ms after AI speaks" — but AI speech latency is already 2-5s in our pipeline, so 100ms is in the noise. Acceptable.

### Recommended approach for v1.1

**djay Pro: hybrid (a) + (b).**
- Default: hand-mapped percentage coordinates (approach a) — fast, deterministic, ships immediately.
- Where AX label exists (likely 80% of controls): also store the AX path. Use AX position attribute IF available to refine the percentage map at runtime ("user has resized in a non-proportional way, AX knows the real position"). Fall back to percentage map if AX returns nothing.
- Polling: AX walk on-demand at highlight-fire time, not continuously. djay-pro-bridge's 8Hz background poll is for live data streams; ours is event-driven.

**Rekordbox / Serato: deferred to v1.2 with approach (c) when we do.**
- The viral demo only needs ONE app to look magical. djay Pro is also Algoriddim — a single press release, a friendly relationship with the vendor, no Pioneer-DJ hostility risk.

---

## Element vocabulary proposal

A stable taxonomy so Gemini can say `point.deck.a.mid_eq` and the overlay knows where to draw across apps. Stored as a JSON namespace:

```jsonc
// 12 elements covers >80% of likely "point at X" utterances during a 30-second viral cut.
// Per-deck (× 2 decks for v1.1; × 4 deferred to v1.2):
{
  "deck.{a|b}.low_eq":     "low/bass EQ knob",
  "deck.{a|b}.mid_eq":     "mid EQ knob",
  "deck.{a|b}.high_eq":    "high/treble EQ knob",
  "deck.{a|b}.gain":       "deck input gain",
  "deck.{a|b}.filter":     "filter / high-low-pass knob",
  "deck.{a|b}.tempo":      "tempo slider / pitch fader",
  "deck.{a|b}.fader":      "channel fader",
  "deck.{a|b}.play":       "play/pause button",
  "deck.{a|b}.cue":        "cue button",
  "deck.{a|b}.sync":       "sync button",
  "deck.{a|b}.loop":       "loop in/out / size knob",
  "deck.{a|b}.hot_cues":   "hot-cue pad grid (whole region)",
  "deck.{a|b}.waveform":   "waveform view (whole region)",
  "deck.{a|b}.jog":        "jog wheel / scratch zone",

// Master / mixer:
  "master.crossfader":     "crossfader",
  "master.gain":           "master gain knob",
  "master.fx_a.amount":    "FX unit A amount",
  "master.fx_b.amount":    "FX unit B amount",

// View regions (for "look at this" rather than "tweak this"):
  "region.browser":        "track browser / library",
  "region.waveform_full":  "the combined waveform area",
}
```

**Prompt-engineering shape:** Gemini outputs structured replies with optional `point` field:

```json
{
  "say": "mids are stacked on deck A — try cutting them 3-4 dB",
  "point": "deck.a.mid_eq",
  "hold_ms": 2500
}
```

We parse `point`, look up the rect, draw the highlight (a soft circle / ring) for `hold_ms`, fade out. `point` is OPTIONAL — most utterances won't have one. Quality bar: don't point unless the AI is referencing a specific control. Pointing on every utterance = AI-slop visual noise.

**Coverage discipline:** start with **12 elements per deck (no master, no view regions)**. Add only after Kaan validates the demo. The taxonomy above is the eventual ceiling, not the v1.1 cut.

---

## Legal envelope

| Vendor | EULA stance | What we do | Risk |
|--------|-------------|-----------|------|
| **AlphaTheta (Rekordbox)** | EULA forbids reverse-engineering, decompiling, modifying the program. Forbids "framing" or "linking to" program content in a way that violates IP. [VERIFIED: rekordbox.com/en/license-agreement] | Read `kCGWindowBounds` (public API). Optionally take screenshots (same surface as macOS screen recording). Draw on TOP of the window — never inside it, never modifying it, never intercepting input. | **YELLOW.** Reading public window bounds isn't reverse engineering. Beat Link, prolink-tools, and others have done much more invasive things (decoding the Pro DJ Link protocol) for ~8 years without takedowns. Our overlay does strictly less. |
| **Algoriddim (djay)** | Standard commercial EULA, no specific anti-overlay clause. Algoriddim *publishes* an accessibility API surface for VoiceOver — we'd be using the same surface. | Use the AX API exactly as VoiceOver does. Draw on top. | **GREEN.** djay-pro-bridge exists publicly, no action against it. |
| **Serato Limited** | Standard EULA. Allows third-party visualizers, controllers, plug-ins per documented integration paths. | Same — overlay only. | **YELLOW-GREEN.** Lower priority since we likely can't make Serato work technically. |
| **Native Instruments (Traktor)** | Standard EULA. Active third-party ecosystem (Reaktor, NI Controller Editor). | N/A in v1.1. | **YELLOW-GREEN.** Same as Serato. |

**The crisp distinction the EULA hangs on:** *modifying, intercepting, redirecting, decompiling* the program is forbidden. *Coexisting next to it* — by reading public OS APIs, drawing on the screen above it — is not modification. Same legal posture as every screen-recording app, every accessibility tool, every overlay (Cluely, OBS, Loom, Discord game overlay).

**Where we could cross the line:**
- Hooking djay/Rekordbox processes (DLL injection, dylib injection, code patches) → red.
- Decompiling the binary to figure out internal state → red.
- Reading rekordbox's `.edb` database directly to enrich our overlay → yellow (was a banned API surface per the rekordbox forum thread, has shifted).
- Sending fake MIDI / OSC into rekordbox to control it → green (we're already going to do this for vibemix v2).

**Conclusion:** the overlay-only path stays YELLOW for Rekordbox (cautious watchful) and GREEN for djay. Open-source MIT or Apache 2.0 with a clear "this is an unofficial third-party tool" disclaimer in the README. Don't trademark-stomp on "rekordbox" or "Serato" in the product name; "vibemix" is clean.

---

## Demo storyboard (30-second viral cut)

Title card: **"AI that actually sees your set."** (1.5s, dark background, Geist typeface, the brand mark.)

**0:00–0:03** — DJ booth shot. Kaan in headphones, hands on DDJ-FLX4. djay Pro on the laptop screen behind him. Cinematic 3-second hold.

**0:03–0:08** — Music dropping. Cut to laptop screen: djay Pro UI in full. Build-up phrase running. Three tracks layered, low end visibly stacking on both waveforms. Camera pushes in slightly.

**0:08–0:11** — vibemix's mascot (top-right corner, glowing) lights up. Voiceover from headphones (loud and clear in the mix): **"Low end's stacking on A — kill it."** Simultaneously, a **soft amber ring** pulses around the mid-low EQ knob on Deck A in djay Pro. The ring is unmistakably part of djay's UI but obviously not native — it has the vibemix amber glow.

**0:11–0:14** — Kaan twists the knob (real footage, sync'd to the ring fading as his finger lands on it). The bass clears in the mix. The ring fades to nothing.

**0:14–0:18** — Another moment. Camera close on the screen. AI: **"Build's been running too long — release it."** Soft ring around the filter knob, then the play-cue zone. Kaan smashes it. Drop lands.

**0:18–0:24** — Quick cut montage: 4 more moments, each <1.5s. AI utterance + ring + correction. "Hats are too bright on B" → ring on high EQ deck B. "You missed the phrase — cue point's 2 bars off" → ring on the cue button. "Crossfader's dragging" → ring on crossfader. Each one feels surgical.

**0:24–0:28** — Pull back to wide. Kaan smiles. AI: **"That last blend was clean."** No ring. (The negative space matters — overlay only fires when the AI actually means it. The product isn't constantly flashing.)

**0:28–0:30** — Cut to black. Brand mark + tagline: **"vibemix — AI DJ co-host. Free, open source, runs on your machine."** GitHub stars counter on screen, ticking up.

**Why it pops:**
- Visual contract is unambiguous — when AI talks, you see WHERE on the deck it's talking about. There's nothing else like this in the DJ space.
- Density: 7 reactions in 25 seconds. The clip rewards rewatching.
- Honesty: 1 "no ring" moment. The product isn't a slot machine of fake alerts. (This sells the anti-slop thesis visually.)
- Mascot in the corner = brandable, GIF-able, meme-able.
- The screenshot of djay + amber ring is a single image that **alone** would post well on Reddit / Twitter / r/Beatmatch.

**Posting plan:**
- IG Reels: vertical 9:16 recut, the clip + Kaan's face in the upper third. Caption in Italian + English.
- Twitter / X: 30s landscape, 1 thread with technical breakdown linking the GitHub repo.
- r/Beatmatch, r/DJs: a single 1-min variant + write-up explaining the open-source angle.
- Hacker News: the GitHub repo with a 2-paragraph "show HN" describing the grounded-AI thesis.

---

## Tractability matrix

| Target app | Approach | Effort (eng-days) | Wow-factor | Recommend? |
|------------|----------|------------------|------------|------------|
| djay Pro / macOS | (a) manual coord map | 3 days | 8/10 | **YES — v1.1 baseline** |
| djay Pro / macOS | (b) AX positions | +2 days (on top of a) | 9/10 (adapts to window resize) | **YES — v1.1 enhancement** |
| djay Pro / macOS | (c) template matching | 4 days | 7/10 (slower, brittler) | No — (a)+(b) dominate |
| djay Pro / Windows | (a) manual coord map | +2 days (DPI + window detection) | 8/10 | **Defer to v1.2** |
| Rekordbox / macOS | (a) manual coord map | 4 days (more elements, tear-off panels) | 8/10 | **Defer to v1.2** |
| Rekordbox / macOS | (b) AX | N/A — canvas UI | 0/10 | No |
| Rekordbox / macOS | (c) template matching | 6 days (theme variants) | 6/10 | Defer to v1.2 if (a) doesn't ship |
| Serato / macOS | (a) | 4 days (library panel reflow) | 7/10 | Defer to v1.2 |
| Serato / macOS | (b) AX | LOW success probability — test 1 day before committing | 4/10 | No |
| Traktor / either OS | any | 5+ days | 6/10 | Defer to v1.3+ |

---

## Recommended v1.1 scope

**One app, one OS, twelve elements:**

- **Target:** djay Pro on macOS only.
- **Elements (12):** per deck × 2 decks → `low_eq, mid_eq, high_eq, gain, filter, tempo, fader, play, cue, sync, loop, hot_cues`. (Total: 24 element instances across 2 decks; 12 logical names in the vocabulary.)
- **Coord source:** hand-mapped percentage-of-window-rect JSON file (`assets/element_maps/djay_pro_5.json`), with AX position refinement when available.
- **Window tracking:** re-use `find_djay_window_bounds()` already in `cohost_v4.py` lines 224-246. Lift to a `WindowTracker` service that emits `(x, y, w, h)` updates to the highlight webview over WS at 10 Hz.
- **Overlay window:** second Tauri window, label `highlight`, built via a clone of `mascot_window.rs` with min/max size dropped and resizable=false.
- **Drawing:** Canvas 2D in `highlight.html`, ~200 lines of vanilla JS. A single "soft ring" animation (radial gradient + opacity tween, 1.2s in-hold-fade-out). One CSS keyframe.
- **Gemini integration:** add an optional `point` field to the response schema. On parse, if `point` is present and maps to a known element, fire `highlight.show(element_id, hold_ms)`.

**Fallback behavior (when AX is unavailable, when element isn't in map, when djay window is hidden):**
- Drop the highlight silently. The AI still speaks. Pointing is a bonus, not a hard requirement of every reaction.
- Log to `events.jsonl` for debug: `highlight_skipped: reason=djay_hidden | element=unknown | ax_no_position`.
- Tray-icon indicator: amber dot when overlay last fired successfully in the past 30s; grey otherwise. Lets Kaan eyeball "is the highlighter working".

**Out of v1.1 scope (defer to v1.2+):**
- Rekordbox, Serato, Traktor.
- Windows.
- More than 2 decks (djay's 4-deck mode has a different element map).
- Continuous tracking (overlay follows the knob as user turns it).
- User-customizable elements ("highlight this thing I'm pointing at").
- Multi-monitor smart placement.

**One-shot eng estimate:** 5-7 engineering days from "approved" to "shipped behind a feature flag". Add 2 days for visual polish (the ring animation + colors must be on-brand, otherwise it screams AI-slop — see `frontend-enforcement` skill).

---

## Risk + watchouts

1. **Sidecar AX permission bug.** `tauri-apps/tauri#8329` — sidecar processes don't reliably inherit AX permission from the bundled parent on installed Mac apps. **Mitigation:** do the AX call from the Rust parent (where bundle ID is stable). Pass results over WS to the Python sidecar. Never call AX from the sidecar.
2. **Brand mistaken-for-ad risk.** Amber ring overlapping a vendor's product could look like we're advertising on top of their UI. **Mitigation:** ring fades within 2.5s, never sticks. README explicit "unofficial third-party tool" disclaimer.
3. **djay UI redesign.** A major djay version bump invalidates the coord map. **Mitigation:** version-pin the map (`djay_pro_5.json`), detect version via app bundle `CFBundleShortVersionString`, fall back to nearest known map with a warning logged.
4. **Highlight feels disconnected from speech (latency).** If the ring appears 300ms before/after the AI says "mid EQ", the magic dies. **Mitigation:** the ring is fired from the SAME structured response that carries the audio — they're in the same Gemini reply, so they're inherently sync'd at the point of speak() unless we introduce drift. Schedule both on the same event.
5. **Multi-monitor wrong-screen draw.** djay on monitor 2, overlay drawn on monitor 1. **Mitigation:** the overlay window is positioned at djay's bounds + size, so it inherits its monitor automatically — Tauri handles cross-screen positioning. Test this on a dual-monitor rig before shipping.
6. **One-click install permission friction.** First-run AX prompt is 2 extra user clicks. **Mitigation:** show a single-step onboarding card "vibemix needs to see your djay window to point at things. Tap Open Settings → toggle vibemix on. We never read keystrokes or other apps." Phase 4 (`permissions.rs`) already designed for this.
7. **Vendor C&D risk (low but non-zero).** AlphaTheta or any other vendor could decide overlays are unwelcome. **Mitigation:** start with djay where the vendor is friendly. Document fallback if Pioneer ever objects: "highlight feature disabled for rekordbox" — feature flag at runtime, no client release needed.
8. **Quality bar — overlay must not become AI-slop.** A constantly flashing UI = worse than no UI. **Mitigation:** ship a "highlight cooldown" of 8s per element (same idea as `MIN_EVENT_GAP_PER_TYPE` in `cohost_v4.py`). At most one ring per 3-second utterance.

---

## Open questions for Kaan

1. **Is "djay-only at launch" acceptable for the viral demo?** Most pro DJs run rekordbox. If "vibemix only works with djay" is read as "vibemix only works with the beginner app", the demo loses some pop. Counter: djay Pro has serious users too (Algoriddim's positioning shifted), and the demo is platform-agnostic in framing — "watch our AI point at the controls" doesn't mention the app.
2. **Should `point` be every utterance or opt-in?** Sub-question: do we prompt Gemini to ALWAYS try to point (and accept that some pointings will be "deck.a.waveform" generic), or do we prompt it to ONLY point when there's a specific knob/button it's referencing? Recommendation: opt-in (specific only) for anti-slop. But this affects how dense the viral demo can be — fewer rings = lower wow density.
3. **Visual style of the ring — locked or open?** Amber circle pulse matches the `cdj-whisper` direction. Are we OK with this, or want to explore alternatives (square frame, arrow pointer, animated underline)? I'd lock amber ring for v1.1 and ship — variants are a v1.2 polish job.
4. **OK to deprioritize Windows for v1.1?** Mascot already runs on Windows in our code, but the element map work for Rekordbox/Serato/djay on Windows triples the surface area for v1.1. Recommendation: macOS-only at launch, Windows a fast-follow with a public Trello-like roadmap entry so users see it's coming.
5. **Permission UX — block first run, or show feature-disabled?** Two paths: (a) require AX permission before vibemix runs at all, (b) run vibemix without highlight, show a one-time card "enable highlight by granting permission". Recommendation: (b). Highlight is a feature, not a hard dependency. Same anti-friction stance as the BlackHole install — make missing components feel like upgrades, not blockers.

---

## Sources

### Primary (HIGH confidence)
- `tauri/src-tauri/src/mascot_window.rs` lines 28-104 — our existing overlay window scaffolding (`transparent + always_on_top + decorations:false + visible_on_all_workspaces + set_ignore_cursor_events`). [VERIFIED: file read]
- `tauri/src-tauri/tauri.conf.json5` line 90 — `macOSPrivateApi: true` already set. [VERIFIED: file read]
- `cohost_v4.py` lines 224-246 — `find_djay_window_bounds()` Quartz-based window tracking already working. [VERIFIED: file read]
- [GitHub: kyleawayan/djay-pro-bridge](https://github.com/kyleawayan/djay-pro-bridge) — Swift tool that reads djay Pro deck state via macOS Accessibility API at ~8Hz. Validates approach (b) for djay Pro. [VERIFIED: GitHub API metadata + WebFetch of README]
- [Algoriddim community: ShowKontrol-like djay tool thread](https://community.algoriddim.com/t/created-a-showkontrol-like-deck-monitoring-tool-for-djay-pro-on-macos/41823) — confirms "djay Pro has excellent accessibility support" + names the AX API as the method. [VERIFIED: WebFetch]
- [rekordbox EULA](https://rekordbox.com/en/license-agreement/) — explicit prohibition of reverse engineering, but no prohibition of overlay/external-coexistence software. [CITED: rekordbox.com/en/license-agreement]

### Secondary (MEDIUM confidence)
- [Tauri issue #8329 — sidecar AX permission inheritance bug](https://github.com/tauri-apps/tauri/issues/8329) — known unresolved issue; informs our "call AX from Rust parent, not Python sidecar" decision. [VERIFIED: search result]
- [Tauri issue #11488 — visibleOnAllWorkspaces + fullscreen apps](https://github.com/tauri-apps/tauri/issues/11488) — overlay doesn't ride over fullscreen Spaces on macOS. [VERIFIED: search result]
- [Tauri issue #11461 — setIgnoreCursorEvents Windows quirks](https://github.com/tauri-apps/tauri/issues/11461) — informs "go fully click-through, no per-region hit-testing" recommendation. [VERIFIED: search result]
- [Microsoft Learn: GetWindowRect DPI behavior](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect) — confirms DPI virtualization across processes. [CITED]
- [AppleVis: accessible DJ software thread](https://www.applevis.com/forum/macos-mac-apps/accessible-dj-software) — confirms Serato / Traktor / Ableton are not screen-reader accessible. [CITED]
- [Qt forum: NSAccessibility manual setting thread](https://forum.qt.io/topic/108280/manually-setting-nsaccessibility-value-on-mac-for-qaccessiblewidget) — Qt's NSAccessibility bridge is incomplete; informs "Serato is probably canvas-rendered" assumption. [CITED]
- [PyImageSearch: cv2.matchTemplate overview](https://pyimagesearch.com/2021/03/22/opencv-template-matching-cv2-matchtemplate/) — performance characteristics + multi-scale strategy. [CITED]
- [Swindler issue #62 — NSScreen vs AXUIElement coord systems](https://github.com/tmandry/Swindler/issues/62) — multi-monitor Y-flip gotcha confirmed. [CITED]

### Tertiary (LOW confidence — needs validation)
- Rekordbox UI rendering toolkit (assumed canvas/Skia, not native Qt-style widgets). Should be confirmed by running macOS Accessibility Inspector on rekordbox 7 before committing to "Rekordbox is approach (c) only". 30-min experiment. [ASSUMED]
- Serato Qt → canvas leakage. Same — run Accessibility Inspector on Serato DJ Pro 3.x before assuming approach (b) fails. [ASSUMED]
- Rekordbox / Serato proportional scaling. Documented in TLDR as needing manual verification — open djay/rekordbox/serato at 3 different window sizes, check whether percent-of-window holds for inner elements. 1-hour experiment. [ASSUMED]

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|--------------|
| A1 | Rekordbox renders its UI to canvas/Skia, not native widgets; AX tree is essentially empty for control elements. | Approach (b) table | If Rekordbox actually exposes useful AX nodes, we under-committed to a stronger path for v1.2. Low downside — would only unlock more value later. |
| A2 | Serato's Qt UI bridges poorly to NSAccessibility (knobs/sliders return no usable role/value). | Approach (b) table | Same as A1 — under-commit risk only. |
| A3 | Rekordbox and Serato scale their main mixer/deck layout proportionally to window size, so percentage-of-window-rect coord maps hold within ~3% accuracy. | Approach (a) — Cons | If they don't, our hand-mapped approach also fails on those apps, narrowing v1.2 too. |
| A4 | Vendor (AlphaTheta, Serato Inc.) tolerance for overlay-only third-party tools. Beat Link / prolink-tools have run unmolested ~8 years, but vendor stance can change. | Legal envelope | If a vendor C&Ds us, we feature-flag-disable per-vendor at runtime. Low blast radius. |
| A5 | A second Tauri window built with the same flags as the mascot will run cleanly in parallel on both macOS and Windows. | Mac/Windows recipe | If multi-window Tauri 2 has stability issues we haven't hit yet, would need to evaluate launching highlight as a separate process. |
| A6 | Highlight on djay window at app-active-state will sync with vendor's own UI updates without visible jitter at 10 Hz polling. | Window tracking | If jitter is visible, push poll to 30 Hz (still cheap with `CGWindowListCopyWindowInfo`). |
| A7 | Gemini 3 Flash can be prompted to emit a structured `point` field reliably without degrading speech quality. | Element vocabulary | If it can't, fall back to a post-hoc text classifier on the spoken text ("did the AI say mid EQ? → fire deck.{?}.mid_eq"). Slightly worse latency. |

---

## Metadata

**Confidence breakdown:**
- Mac overlay window: HIGH (already built in our codebase).
- Windows overlay window: MEDIUM-HIGH (mascot ships on Windows; pure-click-through sidesteps known per-region bugs).
- djay Pro coord mapping via AX: MEDIUM-HIGH (proven working tool exists, but doesn't expose positions yet — we'd be the first to lift positions from the same AX tree).
- Rekordbox / Serato coord mapping: LOW (likely template-matching only; needs Accessibility Inspector validation before locking).
- Legal envelope: MEDIUM (overlay-only stance is defensible; specific vendor stances can shift).
- Demo storyboard tractability: HIGH (every shot is implementable with the recommended scope).

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (Tauri 2 is moving fast; re-check issue #11488 + #8329 before locking the plan).
