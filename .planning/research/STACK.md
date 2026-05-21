# Stack Research — v5.0 "The Useful Cut"

**Domain:** Local AI DJ co-host — adding (A) full deck-state awareness, (B) musical-key/harmonic analysis, (C) floating Super-Whisper-style pill UI
**Researched:** 2026-05-21
**Confidence:** HIGH on Tauri pill + key detection + Rekordbox path; MEDIUM on non-Rekordbox deck sources (no Context7 entries; web + format-spec verified, no live-hardware confirmation)
**Mode:** Ecosystem (subsequent-milestone integration)

> **Note:** The prior `STACK.md` (v3.1 Distribution-Ready Pass research) is preserved at
> `.planning/research/STACK-v3.1-archived.md`. This file is the v5.0 milestone stack research.

---

## TL;DR Recommendations

| Feature | PRIMARY (recommended) | FALLBACK (graceful degrade) | New install-impact |
|---------|----------------------|------------------------------|--------------------|
| **A. Deck state** | `pyrekordbox` **0.4.4** live `Rekordbox6Database` read (SQLCipher, read-only) as the metadata oracle for Rekordbox users + **Gemini-vision deck read** (existing screenshot) for universal loaded-track identity | **Dual-deck audio analysis** via existing numpy/scipy on the master + `nowplaying-cli`/SMTC audible anchor (both already shipped) | **GREEN** — pyrekordbox already a dep; SQLCipher wheel stays optional/lazy |
| **B. Musical key** | **Reuse pre-computed key tags** from the deck source (Rekordbox `Tonality`, Serato/Traktor/Engine tags, or vision-read key badge) — zero new code path | **In-house numpy** Krumhansl/Temperley key estimate on the existing 16 kHz buffer when no tag exists | **GREEN** if in-house numpy; **YELLOW** if librosa; **RED** if Essentia |
| **C. Floating pill** | **`tauri-nspanel` v2.1** (macOS NSPanel, non-activating) + existing transparent/always-on-top/`set_ignore_cursor_events` pattern; `window-vibrancy` **0.7.x** for the frosted-glass look | Plain Tauri `WebviewWindowBuilder` (transparent + always_on_top + skip_taskbar + focused(false)) on Windows — no NSPanel equivalent needed there | **GREEN** — one git crate (mac-only) + one crates.io crate; both small, no runtime download |

---

## CRITICAL CONTEXT CORRECTION (read before planning)

Two claims in the briefing/CLAUDE.md are **stale** versus the actual `pyproject.toml` + `uv.lock`:

1. **Essentia and librosa are NOT in the stack.** They appear in no dependency list. The entire audio-analysis path (`src/vibemix/audio/features.py`) is **pure numpy/scipy FFT** — band energy, autocorrelation BPM, spectral-flux onset, downbeat phase. There is no MIR library installed. Any "reuse Essentia" plan is actually a **new heavy C++ dependency**, not a reuse. This materially changes the install-impact rating for feature B. (HIGH confidence — read both files directly.)
2. **pyrekordbox is installed XML-only.** `pyproject.toml` (lines 41-72) hard-locks the SQLCipher path **dormant**: `sqlcipher3-wheels` is overridden out via a never-matching platform marker, `src/vibemix/library/rekordbox.py` only uses `RekordboxXml`, and a grep-gate forbids `Rekordbox6Database`/`pyrekordbox.db6`. So "use pyrekordbox to read the live DB" means **deliberately activating a path the codebase currently bans** — a real architectural decision, not a free integration.

Both are fixable and both are the right call for v5.0, but the roadmap must budget for them as real work, not "already there."

---

## A. DECK-STATE DATA SOURCE

### The problem shape

The co-host today knows only the **audible** track (via `nowplaying-cli` on mac / SMTC on Windows, cross-referenced with MIDI deck weights in `track_resolver.py`). v5.0 needs **every loaded track across all decks + each track's key/BPM/energy**, so it can reason about the *upcoming* blend and harmonic clash before it happens.

There is no single cross-app live "what's loaded on deck B" API. The realistic options, ranked:

### Option survey

| Source | What it gives | Platform | Read-only safe? | Live (running app)? | Verdict |
|--------|---------------|----------|-----------------|---------------------|---------|
| **pyrekordbox `Rekordbox6Database` (live master.db)** | Full collection + per-track BPM/key(`Tonality`)/cues; *not* per-deck "loaded-now" state | mac + win | Read-only OK; **never write** (master.db write = corruption, already a locked memory) | DB readable while RB runs; reflects collection, not the live deck buffer | **PRIMARY metadata oracle** for Rekordbox users |
| **nowplaying-cli (mac) / SMTC (win)** — already shipped | Currently-audible title/artist only | mac + win | Yes | Yes | **Already in stack** — the "what's playing now" anchor; one deck only |
| **Audible-deck heuristic** (`track_resolver.py`, MIDI + xfader) — already shipped | Which deck(s) are sounding + confidence | both | Yes | Yes | **Keep** — the bridge between "now playing" and per-deck |
| **Dual-deck audio analysis** (existing numpy/scipy on the master) | BPM/energy/key of *what's sounding* — but it's the **mixed** master, can't isolate deck B pre-fade | both | Yes | Yes | **FALLBACK** for key/BPM when no tag exists; cannot see a cued-but-silent deck |
| **Gemini-vision read of the deck UI** (already screen-capturing) | "Deck B shows track X, 124 BPM, 8A" — reads the *loaded* track even when silent | both | Yes | Yes | **FALLBACK deck-state reader** — already have the screenshot, just ask Gemini to read both deck panels |
| **prolink-connect / python-prodj-link (PRO DJ Link)** | True per-player loaded-track + metadata over network | both (UDP) | Yes (passive listen) | Only with **CDJ/XDJ hardware** on a network | **DEFER** — needs pro hardware; out of scope per memory `project_v2_open_candidates` (ProDJ Link deferred) |
| **Serato / Traktor / Engine library files** | Collection metadata (key/BPM) — not live deck state | both | Yes | Files static; not "loaded-now" | **v.next** — same role as pyrekordbox but for other apps; one importer per app |

### Recommendation: **layered grounding, not a single source**

This is the anti-slop thesis applied to deck state. Compose three layers the co-host already half-has:

1. **Identity layer (which track is loaded where):**
   - **Rekordbox users → pyrekordbox live DB** for the metadata oracle (BPM/key/cues per track in the collection), keyed by the title the co-host already resolves.
   - **Everyone → Gemini-vision deck read** on the existing screenshot. We already send the cropped DJ-window image to Gemini every turn; extend the prompt to extract the loaded track + visible key/BPM badge **on each deck panel**, not just the master. Zero new dependency — it's prompt + the screenshot we already capture. This is the universal fallback that works for Serato/djay/Traktor/Engine without per-app parsers.
2. **Audible layer (what's sounding):** keep `nowplaying-cli`/SMTC + `track_resolver.derive_audible_deck`. Unchanged.
3. **Acoustic layer (ground-truth BPM/key of the sound):** existing numpy/scipy BPM + new in-house key estimate (see B) on the master buffer — used to *cross-check* and correct the metadata/vision layers (e.g., if Rekordbox says 8A but the audio reads clearly off, trust the audio per the locked "trust the audio" rule).

**Why this over "just turn on pyrekordbox":** pyrekordbox gives you the *collection* (every track's stored key/BPM), but it does **not** tell you which track is loaded on deck B right now — RB doesn't expose live deck state through the DB. The Gemini-vision deck read is what closes "what's loaded across decks." pyrekordbox enriches it with reliable pre-analyzed metadata. The two together are the grounded answer; either alone hallucinates.

### pyrekordbox live-DB activation — concrete plan

- **Version:** `pyrekordbox==0.4.4` (released 2025-08-17, current). Already pinned.
- **Activate the dormant path:** drop the `sqlcipher3-wheels` never-match override **only on the read path**, ship the wheel (~3.2 MB, mac+win), and lift the grep-gate ban on `Rekordbox6Database` for the new module. Keep it **strictly read-only** — never call `.commit()`/mutators (master.db write corruption is a locked constraint).
- **Key acquisition gotcha (MEDIUM-confidence, verify in spike):** since **Rekordbox ≥ 6.6.5**, Pioneer obfuscated `app.asar`, breaking automatic key extraction. pyrekordbox ships `python -m pyrekordbox download-key` to fetch the SQLCipher key from known sources into a cache file. For a distributed binary this is fragile — plan for: (a) read the user's existing cached key if present, (b) graceful "couldn't unlock RB DB → fall back to vision layer" if not. **Never bundle or hardcode the key.**
- **Fields exposed:** title, artist, **BPM**, **`Tonality` (musical key)**, cue points — exactly what feature B needs, pre-analyzed by Rekordbox (better than anything we'd compute live).

---

## B. MUSICAL KEY / HARMONIC ANALYSIS

### Recommendation: **prefer pre-computed tags; in-house numpy estimator as fallback; do NOT add Essentia or librosa as a hard dep**

**Order of preference for "what key is this track":**

1. **Pre-computed key tag from the deck source** (Rekordbox `Tonality`, or a library-file/vision-read tag for other apps). This is what DJs actually mix on, it's already in Camelot-adjacent form, and it's free + instant + as accurate as the DJ's own software. **Always prefer this.** The harmonic-clash feature is about reasoning over the keys DJs *see*, so matching their software's key analysis is a feature, not a compromise.
2. **In-house key estimate** when no tag exists (streaming track, un-analyzed file, non-Rekordbox user with no vision-readable key badge): implement **Krumhansl-Schmuckler / Temperley key-finding** directly on the existing 16 kHz buffer. It's ~80 lines of numpy: compute a chromagram (12-bin pitch-class energy from the FFT we already do in `features.py`), correlate against the 24 major/minor key profiles (Temperley or the EDMA/Faraldo EDM-tuned profiles are the right choice for dance music), pick the argmax. No new dependency — same DSP family as the BPM autocorrelation already shipped.

### Why NOT Essentia or librosa

| Candidate | Accuracy | Latency | Install impact | Verdict |
|-----------|----------|---------|----------------|---------|
| **Pre-computed tag** | = the DJ's own software (the ground truth they mix on) | 0 (lookup) | **GREEN** (no dep) | **USE** |
| **In-house numpy KS/Temperley** | Good for the fallback case; EDM profiles competitive on dance music; only fires when no tag exists | low (FFT we already compute) | **GREEN** (no dep) | **USE as fallback** |
| **librosa** | Solid chroma, but no key extractor (you'd still hand-roll the correlation); pulls numba/soundfile/audioread transitives | low | **YELLOW** — meaningful transitive weight + slower cold import; fights one-click-install size budget | **AVOID** — buys little over in-house |
| **Essentia `KeyExtractor`** | Best-in-class (HPCP + EDMA profiles), MIREX-grade | low | **RED** — heavy C++/binary wheel, platform-fragile on the mac+win one-click installer, no current pip wheel guarantee on Python 3.12 both arches | **AVOID** — install-impact kills it; not worth it for a fallback-only path |

Essentia's `KeyExtractor` is genuinely the most accurate, but key detection here is a **fallback** (the primary is pre-computed tags). Spending a RED-rated heavy binary dependency to slightly improve a path that fires only when tags are absent violates `feedback_no_scope_creep_clean_utility` and `project_one_click_install_hard_req`. The numpy KS/Temperley estimator is good enough for "is this a clash?" reasoning.

### Camelot reasoning (no dependency)

The Camelot wheel is a fixed 24-entry lookup table (key ↔ Camelot code ↔ compatible neighbors). Ship it as a small constant table in `src/vibemix/state/` (sibling to the genre profiles). The harmonic-clash logic ("8A → 9A is energy-boost compatible, 8A over 3A is a clash") is pure table lookup + the co-host's prompt grounding. **Zero new stack.**

---

## C. FLOATING PILL WINDOW (Super-Whisper-style)

### Recommendation

The codebase **already ships** the hard parts: `overlay.rs` and `mascot_window.rs` build transparent + `always_on_top(true)` + `decorations(false)` + `skip_taskbar(true)` + `visible_on_all_workspaces(true)` windows and call `set_ignore_cursor_events(true)` for click-through. The pill is a **fourth WebviewWindow** built from this proven pattern. Two additions make it feel like Super Whisper specifically:

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **tauri-nspanel** | **v2.1** (git, branch `v2.1`) | Convert the pill window to a macOS **NSPanel** (`NonactivatingPanel` style, `PanelLevel::Floating`) | Plain Tauri windows **steal focus** and the pill would deactivate the DJ app on click. NSPanel is non-activating — the user interacts with the pill without the DJ software losing key-window status. This is exactly how Super Whisper's pill stays unobtrusive. |
| **window-vibrancy** | **0.7.x** (crates.io; current 0.7.1) | Frosted-glass background (`apply_vibrancy` / `NSVisualEffectMaterial::HudWindow` on mac; `apply_acrylic`/`apply_mica`/`apply_blur` on Windows) | The Super-Whisper look is translucent material, not flat alpha. Matches the CDJ-Whisper "textured material, no AI slop" visual direction. Tauri v2 requires window-vibrancy ≥ 0.6; 0.7.x is the v2 line. |

Installed via Cargo:
```toml
# tauri/src-tauri/Cargo.toml
window-vibrancy = "0.7"                                              # cross-platform frosted glass

# macOS-only block (NSPanel has no Windows equivalent)
[target.'cfg(target_os = "macos")'.dependencies]
tauri-nspanel = { git = "https://github.com/ahkohd/tauri-nspanel", branch = "v2.1" }
```

### Platform specifics

**macOS:**
- Use `tauri-nspanel` `PanelBuilder` (or convert the built window) with `NonactivatingPanel` mask + `PanelLevel::Floating`. Gives non-focus-stealing + floats above the DJ app.
- `macos-private-api` is **already enabled** (tauri.conf.json5 line 97 `macOSPrivateApi: true`) — required for transparency. Good.
- `visible_on_all_workspaces(true)` already used; note **Tauri issue #11488**: such windows don't always stay above *full-screen* apps. NSPanel `Floating` level mitigates. Flag for the pill phase.
- **Vibrancy + transparency + DMG-build gotcha (issue #13415):** `.transparent(true)` webviews can render solid white after DMG bundling on macOS. Pin a regression test (the Phase 50 Playwright/pixelmatch harness can baseline the pill) — a v0.1.0-rc1-class bug.

**Windows:**
- No NSPanel. Plain `WebviewWindowBuilder` with `transparent + always_on_top + skip_taskbar + decorations(false)` (the existing pattern) is the full solution. Use `window-vibrancy` `apply_acrylic`/`apply_mica` for the frosted look (Win 10 acrylic / Win 11 mica).
- Non-focus-stealing on Windows: build with `focused(false)` + `skip_taskbar(true)`; `WS_EX_NOACTIVATE` behavior is approximated — acceptable, Windows DJs are a smaller share and click-through is the main need.

### Drag-anywhere — the load-bearing gotcha

- **`data-tauri-drag-region`** is the standard frameless-drag mechanism (HTML attr; mark interactive children `data-tauri-drag-region={false}`).
- **CRITICAL (Tauri issue #11605):** `data-tauri-drag-region` **does not work when the window is not focused** — and a non-activating pill is *by design* unfocused. So "draggable Super-Whisper pill" + "non-focus-stealing" are in direct tension via the easy path.
  - **Fix:** drive dragging manually with `appWindow.startDragging()` from a `mousedown` listener (works regardless of focus), OR on macOS let NSPanel's `isMovableByWindowBackground`/mouse-tracking handle it. **The pill phase MUST de-risk this with a spike** — the single most likely "looks done but feels broken" failure.
- **Click-through when idle:** reuse `set_ignore_cursor_events(true)` (already in `overlay.rs`/`config.rs:236`), toggling it off on hover/proximity so the pill is interactive only when the user reaches for it — exactly the Super Whisper idle behavior. The toggle plumbing already exists.
- **Multi-monitor positioning:** `mascot_window.rs` already persists geometry and computes per-monitor offsets; lift that pattern. Tauri's `available_monitors()` + `PhysicalPosition` cover placement on any display.

### Capability allowlist

Add the pill window label (e.g. `"pill"`) to `capabilities/default.json` `"windows"` array (currently `["main","mascot"]`) and grant the same command scopes the mascot has. The known v0.1.0-rc1 debt "Tauri capability missing for drag" must be closed here.

---

## ACTIONABLE-FEEDBACK PERSONA (feature 2) — stack note

No new stack. This is prompt-matrix + model-routing work on the existing Gemini 3 Flash + OpenRouter-fallback brain/TTS chain (the in-flight `live-tuning-or-brain` branch already touches `prompts/matrix.py`, `state/coach.py`). The **only** stack-adjacent dependency is feature A: the persona can only give "run the blend like this / those two clash in key" notes once deck-state + key data exists. Sequence A before/with 2.

---

## Installation Summary

```bash
# Python (feature A + B) — NO new PyPI package required for the recommended path.
# pyrekordbox 0.4.4 is already a dependency; activation = config + code, not install:
#   - remove the sqlcipher3-wheels never-match override on the read path
#   - ship sqlcipher3-wheels (~3.2 MB, mac+win) so Rekordbox6Database can unlock
#   - lift the Rekordbox6Database grep-gate for the new read-only module
# In-house numpy key estimator + Camelot table = new source files, zero deps.
```

```toml
# Rust (feature C) — tauri/src-tauri/Cargo.toml
window-vibrancy = "0.7"                                              # cross-platform frosted glass

[target.'cfg(target_os = "macos")'.dependencies]
tauri-nspanel = { git = "https://github.com/ahkohd/tauri-nspanel", branch = "v2.1" }
```

---

## What NOT to Use (constraint-enforced exclusions)

| Avoid | Why | Use Instead | Install-impact if added |
|-------|-----|-------------|-------------------------|
| **CLAP / LAION-CLAP / MERT / OpenL3** | Permanently banned (`feedback_no_clap_use_gemini_embedding`); vibemix is Gemini-only for embeddings | Gemini Embedding 2 (already shipped) | n/a — never |
| **Essentia** | Heavy C++ binary wheel, platform-fragile on mac+win one-click installer; only buys accuracy on a fallback-only key path | Pre-computed tags + in-house numpy KS/Temperley | **RED** |
| **librosa** | Pulls numba/soundfile/audioread; no key extractor anyway (you'd still hand-roll correlation) | In-house numpy chroma + key profiles | **YELLOW** |
| **prolink-connect / python-prodj-link (now)** | Requires PRO DJ Link **hardware** on a network; ProDJ Link explicitly deferred (`project_v2_open_candidates`) | Gemini-vision deck read + pyrekordbox metadata | **YELLOW** (UDP listener, but hardware-gated) — DEFER |
| **Serato/Traktor/Engine library parsers (this milestone)** | Per-app importers are real surface area; vision-read covers them universally for v5.0 | Gemini-vision deck read (universal) | **YELLOW** — v.next, one importer per app |
| **Any non-Gemini LLM/TTS for the new features** | Gemini-only is a hard constraint (OpenRouter is fallback chain only, already wired) | Gemini 3 Flash + existing TTS chain | n/a — never |
| **Writing to Rekordbox master.db** | Corruption risk — locked constraint from prior spike | Read-only `Rekordbox6Database`; XML round-trip for any write (not needed here) | n/a — never |
| **OCR engine (tesseract/easyocr) for the deck UI** | We already send the screenshot to a multimodal model; a separate OCR dep is redundant scope creep | Gemini-vision reads the deck panels directly | **YELLOW → avoid** |

---

## Alternatives Considered

| Recommended | Alternative | When the alternative would win |
|-------------|-------------|--------------------------------|
| Gemini-vision deck read (universal deck-state) | Per-app library-file parsers | When a user wants offline/no-Gemini deck state, or pixel-perfect key badges OCR fails on — revisit v.next |
| pyrekordbox live DB (metadata oracle) | pyrekordbox XML import (current) | If activating SQLCipher proves too fragile post-6.6.5 key-obfuscation, fall back to the existing one-shot XML import (already shipped, GREEN) |
| In-house numpy key estimator | Essentia KeyExtractor | If a future milestone makes key accuracy primary (not fallback) AND the installer can absorb a heavy binary — not today |
| tauri-nspanel | `set_activation_policy(Accessory)` | Accessory hides the Dock icon and is global to the app, not per-window — wrong tool for a single pill |

---

## Version Compatibility

| Package | Version | Compatible with | Notes |
|---------|---------|-----------------|-------|
| pyrekordbox | 0.4.4 | Python 3.12, Rekordbox 6 & 7 | SQLCipher key auto-extraction broken ≥ RB 6.6.5 — needs `download-key` cache or existing cached key |
| sqlcipher3-wheels | (pyrekordbox-pinned) | mac + win wheels | ~3.2 MB; currently override-excluded — must ship on read path |
| tauri-nspanel | v2.1 (git branch) | Tauri 2.11 (current), macOS only | No crates.io release; pin to branch `v2.1` |
| window-vibrancy | 0.7.x (0.7.1) | Tauri 2.x (needs ≥ 0.6 for v2) | v1 used 0.4; cross-platform |
| tauri | 2.11 (current) | macos-private-api already on | transparency + NSPanel both depend on private API flag (already enabled) |

---

## Sources

- [pyrekordbox PyPI](https://pypi.org/project/pyrekordbox/) — v0.4.4, 2025-08-17 (HIGH)
- [pyrekordbox Quick-Start docs](https://pyrekordbox.readthedocs.io/en/stable/quickstart.html) — `Rekordbox6Database`, `download-key` CLI (HIGH)
- [pyrekordbox db6 format docs](https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html) — SQLCipher, 6.6.5 key-obfuscation (MEDIUM — verify in spike)
- [tauri-nspanel](https://github.com/ahkohd/tauri-nspanel) — v2.1, NonactivatingPanel, PanelLevel::Floating (HIGH)
- [window-vibrancy](https://github.com/tauri-apps/window-vibrancy) — 0.7.x, v2 requires ≥0.6 (HIGH)
- [Tauri Window Customization](https://v2.tauri.app/learn/window-customization/) — drag region, decorations (HIGH)
- [Tauri issue #11605](https://github.com/tauri-apps/tauri/issues/11605) — drag-region broken on unfocused window (HIGH — load-bearing for the pill)
- [Tauri issue #11488](https://github.com/tauri-apps/tauri/issues/11488) — visibleOnAllWorkspaces vs full-screen apps (MEDIUM)
- [Tauri issue #13415](https://github.com/tauri-apps/tauri/issues/13415) — transparency lost after DMG build (MEDIUM)
- [Essentia KeyExtractor reference](https://essentia.upf.edu/reference/std_KeyExtractor.html) — accuracy context (HIGH on capability, not adopted)
- [prolink-connect](https://github.com/evanpurkhiser/prolink-connect) / [python-prodj-link](https://github.com/flesniak/python-prodj-link) — PRO DJ Link, hardware-gated (MEDIUM)
- [traktor-nml-utils](https://pypi.org/project/traktor-nml-utils/), [python-serato-crates](https://github.com/stephanlensky/python-serato-crates), [Engine Library Format (Mixxx wiki)](https://github.com/mixxxdj/mixxx/wiki/Engine-Library-Format) — non-RB library parsers, deferred to v.next (MEDIUM)
- Local ground truth: `pyproject.toml`, `src/vibemix/audio/features.py`, `src/vibemix/library/rekordbox.py`, `src/vibemix/state/track_resolver.py`, `tauri/src-tauri/{Cargo.toml,tauri.conf.json5,src/overlay.rs,src/mascot_window.rs,src/config.rs}` (HIGH)
