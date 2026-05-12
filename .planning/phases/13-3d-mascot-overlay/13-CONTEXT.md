# Phase 13: 3D Mascot Screen Overlay - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning (open questions resolved, Meshy assets in hand)
**Mode:** Autonomous run — `/gsd-autonomous --from 13`; all open questions resolved 2026-05-12.

> **Asset reality (2026-05-12):** Kaan has the full Meshy asset bundle in hand at `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/` — 1 base character GLB (`Meshy_AI_Neon_Rebel_biped_Character_output.glb`) + 20 separate skinned animation GLBs (each ~28 MB, single track, rig baked in). All animations share the same biped skeleton — no Blender MCP renormalization needed for v2.0. Character codename: "Neon Rebel" (replaces the placeholder "DJ bat" concept).

> **Supersedes** the prior Phase 13 ("Reactive Mascot (Avery)" SVG-pose-vocabulary plan). The earlier SVG/pose-dispatch model was a misread of Kaan's mental model; the actual vision is a 3D animated screen companion. ROADMAP.md and REQUIREMENTS.md updated 2026-05-12.

<domain>
## Phase Boundary

Phase 13 ships vibemix's **3D animated mascot** as a Clippy-meets-Codex-Pets desktop companion that floats on top of the user's screen during DJ sets. It is **NOT** a static SVG embedded in the session-UI corner; it's a separate **always-on-top, drag-positionable, transparent-background overlay window** rendered with Three.js, hosting a single rigged GLB character with a library of crossfaded animation clips.

The mascot is the **visible body of the grounded Gemini brain** — it sits ON TOP of the screen, not inside the audio signal loop. It reacts to live music + AI events via a Three.js AnimationMixer state machine fed by the existing WS bus on `127.0.0.1:8765`.

Owns:
- **Menu-bar / system-tray icon** — macOS top-right menu bar (NSStatusItem-equivalent via Tauri tray plugin) + Windows notification area icon. **Persistent always-running entry point** — click toggles mascot overlay visibility; right-click / hover popover surfaces quick controls (mood selector, mute mic, open session UI, settings, quit). Icon state communicates session status (idle / live / ai_thinking / error).
- New Tauri overlay window `tauri/ui/src/mascot/` — **Superwhisper-style sticky floating overlay**, separate window from the main session UI. Transparent background, always-on-top, **persistent across macOS Spaces / Windows virtual desktops** (mascot doesn't disappear when user switches desktops), drag-repositionable on screen, resizable within bounds, click-through optional. Default size ~300×400, position persists across sessions in `config.json`.
- Three.js scene + `AnimationMixer` pipeline in `mascot.html` (rewritten — supersedes the legacy Canvas2D POC mascot at the repo root).
- 3D character asset bundle in `tauri/ui/assets/mascot/` — single rigged GLB (biped skeleton) + named animation clip library (Meshy-AI-generated, normalized via Blender MCP, exported as multi-track GLB).
- Animation state machine in `tauri/ui/src/mascot/state-machine.ts` — maps WS-bus AI events + grounding signals to animation state transitions with crossfade.
- Beat-locked entry orchestration — uses BPM + downbeat phase from `MusicState` (Phase 3) to start new clips on bar boundary 1.
- Mood state system — hype-man / teacher / coach moods swap active Gemini TTS voice + animation clip pool + prompt vocabulary on the same rig; transition masked by particle/puff effect.
- WS:8765 client in the mascot window — subscribes to existing `levels` / `events` / `state` streams (no new bus topology).

Does NOT own:
- Audio routing / signal processing (audio loop sits beneath the mascot — Phase 2 owns).
- Embedded session-UI mascot corner (Phase 12 had reserved a 256×256 corner; with overlay-window-only v2.0, that corner is reallocated — see Open Questions).
- FL-Studio-tier visual polish loop (Phase 14 — audits mascot animation library for character-design quality).
- Mascot character art generation (manual artistic step in Meshy AI + Blender; Phase 13 provides tooling support + normalization but Kaan owns the character output).
- User-generated `/hatch` mascot pipeline (v2.x stretch — out of scope for v1).
- Webcam-driven facial mocap (explicitly out of scope — animation is AI-state-driven only).

</domain>

<decisions>
## Implementation Decisions

### Area 1: Character Asset Pipeline

- **Source:** Meshy AI generated character + 20 pre-skinned animation GLBs at `/Users/ozai/Downloads/Meshy_AI_Neon_Rebel_biped/`. All animations carry the rig + skin baked in — drop-in usable.
- **Bundle layout (v2.0):** Per-clip GLB files copied to `tauri/ui/assets/mascot/` (relative to Tauri build). 1 base character GLB + 20 animation GLBs. Phase 13 loads the character mesh from the base GLB, then extracts the `AnimationClip` from each animation GLB and binds them to the character's `SkinnedMesh`/`Skeleton` via Three.js `SkeletonUtils.retargetClip` (since the rigs are byte-identical, retarget is a no-op normalize, but the call guards against future Meshy export drift).
- **Asset size:** 21 × 28 MB ≈ **588 MB raw**, well over the < 8 MB one-click-install target. Plan must include an offline compression step (Meshy exports include embedded textures + uncompressed buffers): run `gltf-pipeline -i in.glb -o out.glb --draco.compressionLevel 10` per GLB, target final bundle ≤ 25 MB. If compression alone doesn't hit target, strip texture from animation GLBs (animations only need skeleton + tracks, no mesh/material) and keep textures only on the base character GLB. Document the chosen compression result in PLAN.md.
- **No Blender MCP step for v2.0** — assets ship as-delivered + compressed. Blender MCP normalization is a Phase 14 polish nice-to-have if rig drift surfaces.
- **Clip-name → state-vocab map (initial — Phase 13 plan locks final):**
  - `Sleep_Normally` → `idle_breathe` (slowed) + `sleep`
  - `Indoor_Swing` → `idle_bop_to_beat` (mellow) + `talk_loop_calm`
  - `Bass_Beats` → `idle_bop_to_beat` (energetic) + `talk_loop_energetic`
  - `FunnyDancing_01` → `dance_a`
  - `OMG_Groove` → `dance_b`
  - `All_Night_Dance` → `dance_hard`
  - `Hip_Hop_Dance_3` → `dance_alt`
  - `Magic_Genie` → `talk_loop` (gesture-heavy default)
  - `Cheer_with_Both_Hands` → `react_yes` + `celebrate`
  - `Shrug` / `Not_Your_Mom` → `react_no`
  - `Alert_Quick_Turn_Right` → `react_surprised`
  - `Handbag_Walk` → `point_explain` (walks while explaining)
  - `Big_Wave_Hello` / `Wave_for_Help_4` → `gesture_wide`
  - `Fast_Lightning` → `react_drop` (drop-detection peak reaction)
  - `Angry_Ground_Stomp` → `react_glitch` (error / session_error reaction)
  - `Walking` / `Running` → reserved (locomotion if mascot ever moves across screen — v2.x stretch)
- **Character name:** "Neon Rebel" (from Meshy folder name).

### Area 2: Overlay Window & Renderer

- **Window type:** Tauri `Window::builder` with `transparent(true)`, `always_on_top(true)`, `decorations(false)`, `resizable(true)`, **`visible_on_all_workspaces(true)`** (Superwhisper-style cross-Space persistence — macOS `NSWindowCollectionBehaviorCanJoinAllSpaces`; Windows equivalent via `WS_EX_TOOLWINDOW` + `IVirtualDesktopManagerInternal` to keep mascot visible across virtual desktops and out of Alt-Tab). Drag-enabled via custom handle zone (top edge or character body via pointer-events on a non-click-through region).
- **Default geometry:** 300×400, min 200×280, max 600×800. Position + size persist across sessions in `config.json` under `mascot.window`.
- **Renderer:** Three.js (latest stable) loaded as ES module — bundled in `tauri/ui/assets/vendor/` to keep offline. WebGL2 target. Anti-aliasing on. Pixel ratio capped at 2.0 to avoid Retina perf blowup.
- **Scene:** Transparent canvas (`renderer.setClearAlpha(0)`), single directional light + ambient, character mesh, no skybox. Camera framed for character bust + upper body (full-body fallback if Kaan picks a small character).
- **Click-through option:** Toggle in Phase 12 Settings — when ON, OS treats mascot clicks as transparent to underlying app (`set_ignore_cursor_events(true)`); drag-handle stays interactive via a dedicated non-transparent zone. Default = OFF (user can drag the window normally).

### Area 3: Animation State Machine

- **State vocabulary (initial — Meshy output dictates final list):**
  - Idle pool: `idle_breathe`, `idle_bop_to_beat`
  - Dance pool: `dance_a`, `dance_b`, `dance_hard`
  - Talk pool: `talk_loop`, `talk_loop_calm`, `talk_loop_energetic` (mood-variant)
  - React pool: `react_yes`, `react_no`, `react_surprised`
  - Explanation pool: `point_explain`, `gesture_wide`
  - Effects: `puff_particle` (mood-swap mask)
- **Transition rule:** All state changes use `AnimationMixer.crossFadeTo(nextClip, blendMs)`. Default blend 300ms. No hard cuts (except inside `puff_particle` mask).
- **Beat-locked entry:** When entering an idle/dance state, the new clip starts on bar boundary 1 — `setTimeout(switchState, msUntilNextDownbeat)` using BPM + downbeat phase from `MusicState`. Talk/react states are interrupt-class and start immediately.
- **AI event → state mapping:**
  - `track_change` → `react_surprised` → `idle_bop_to_beat`
  - `drop` → `dance_hard` (until `phase_change` to "groove" → `idle_bop_to_beat`)
  - `ai_generating_reply` → `talk_loop` (interrupt-class)
  - `ai_reply_done` → `react_yes` → previous idle/dance
  - `manual_fire` → `react_yes`
  - `phase_change` to "silent" → `idle_breathe`
  - `mood_swap` → `puff_particle` → `idle_breathe` (new mood pool)
- **Priority order (top wins):** `puff_particle` > `talk_loop` > `react_*` > `dance_*` > `idle_*`. AI-talk outranks dancing — if AI starts talking mid-drop, mascot switches mid-clip.

### Area 4: Mood State System (Voice + Clip-Pool + Vocab Swap)

- **Three moods (v2.0):** `hype-man`, `teacher`, `coach`. Each mood = `{ voice_id: <Gemini TTS speaker>, animation_pool: [<clip names>], vocab_profile: <prompt fragment file>, reaction_cooldown_ms: <int> }`.
- **Mood selection:** User picks in Phase 12 Settings panel; default = `hype-man`. Hot-swap mid-session via `ipc.settings.set_mood`.
- **Visual cue per mood (same rig):**
  - hype-man → faster idle pulse, dance-heavy pool, energetic talk-loop variant
  - teacher → calm idle, point/explain-heavy pool, slower reaction cadence
  - coach → thoughtful idle, gesture-while-talking-heavy pool, post-session-debrief vocabulary
- **Transition effect:** Particle/puff `THREE.Points` system (~50 particles, 500ms lifetime) masks the rig pose change during mood swap.

### Area 5: Menu-Bar / System-Tray Icon

- **Platform abstraction:** Tauri 2.x `tauri-plugin-tray` (cross-platform — macOS NSStatusItem, Windows Shell_NotifyIcon, Linux GTK status icon if ever needed). Single Rust handler in `tauri/src-tauri/src/tray.rs`.
- **Icon states (16×16 monochrome, system-convention template):**
  - `idle` — default outline (no vibemix session running)
  - `live` — accent dot (session running, audio loop active)
  - `ai_thinking` — subtle 2s pulse (Gemini generating a reply)
  - `error` — red dot (LiveKit/Gemini/MIDI/screen-capture down — surfaces from Phase 11 status badges)
- **Click behavior:**
  - **Left click:** toggle mascot overlay visibility (show ↔ hide). Single-shortcut "summon / dismiss mascot."
  - **Right click / hover (~500ms):** popover menu with: `Mood: [hype-man ▾] [teacher] [coach]`, `Mute mic (Cmd+Shift+M)`, `Open Session UI`, `Calibration wizard`, `Settings`, separator, `Quit vibemix`.
- **Lifecycle:** Tray icon is always visible while vibemix is running, **even if the main session UI window is closed**. Closing the main session UI does NOT quit the app; quit requires explicit tray menu action (matches Superwhisper / Codex Pets / system-tray-companion conventions).
- **System notifications:** Important async events (`session_error`, calibration drift, AI degraded) post via OS notification (macOS `NSUserNotification` / Windows Toast) tied to the tray. Spam-suppressed (max 1 per 5min per event class).

### Area 6: Grounding Bus Integration

- **WS subscription:** Mascot overlay window connects to `ws://127.0.0.1:8765` (existing vibemix bus) — receives `levels` (30Hz), `events` (AI triggers), `state` (`MusicState` snapshots).
- **Latency target:** AI event → animation transition start < 100ms (excluding blend duration).
- **Reconnection:** WS client reconnects with 1s/2s/4s/8s backoff; mascot freezes in current state during disconnect, resumes on reconnect; no error UI in the mascot window itself (status badge handled in main session UI).

</decisions>

<open-questions>
## Open Questions — RESOLVED 2026-05-12

1. **Click-through default ON or OFF?** → **OFF default** (draggable). Click-through is a Settings toggle.
2. **Phase 12 corner reallocation.** → **Corner dropped entirely.** Mascot lives ONLY as overlay window — Kaan's emphasis: "*it IS the AI, dancing on your screen*". Phase 12 session-UI grid will be reshaped to remove the 256×256 mascot slot (handled as a Phase 13 cross-phase edit, NOT deferred to Phase 14). The session UI uses the freed space for breathing room around the meters + transcript.
3. **Mood swap visible to AI?** → **Yes.** `MusicState.mood: Literal["hype-man", "teacher", "coach"]` field added. Coach prompt template references it via `{mood}` placeholder. Mood swap fires a `mood_change` event on the WS bus that both the mascot window AND the AI loop consume.
4. **Beat-locked entry strict vs best-effort.** → **Best-effort with 0.6 confidence threshold.** If `MusicState.bpm_confidence < 0.6`, switch immediately; else schedule the switch for the next downbeat (computed from `MusicState.bpm` + `MusicState.downbeat_phase`).
5. **Sleep clip after idle.** → **Yes.** `Sleep_Normally.glb` plays after 5 min of no AI activity (`time_since_last_event > 300s`). Wakes immediately on next event.
6. **Mascot character finalization timing.** → **Scaffold starts now with the existing Meshy assets** — no waiting. The Neon Rebel character + 20 animations are usable as-delivered.

</open-questions>

<dependencies>
## Cross-Phase Dependencies

- **Phase 12 (Live Session UI + Settings):** Phase 13 mascot reads from the same WS bus Phase 12 expanded. Mascot mood selector + click-through toggle live in Phase 12 Settings panel — Phase 12 should reserve `mascot.mood` and `mascot.click_through` and `mascot.window` keys in `config.json`. Phase 12's reserved 256×256 corner needs reallocation decision (see Open Q 2).
- **Phase 14 (Polish Phase):** Audits mascot animation library for character-design-document quality — every clip deliberate, smooth crossfades, no rigging artifacts, no T-pose snaps. POLISH-03 updated to reflect animation-library focus, not pose-vocabulary focus.
- **Phase 11 (Tauri Shell):** Phase 11 ships the Tauri 2.x shell with multi-window capability — Phase 13 adds the mascot overlay window as a second `Window` instance. No new Tauri version bump required.
- **Phase 19 (GitHub Launch Presence):** Demo video / GIF features the 3D mascot prominently — must be camera-ready by Phase 19.
- **Phase 3 (Sensing State Port):** Provides `MusicState` with `bpm` + `downbeat_phase` — beat-locked entry requires these signals.

</dependencies>

<memory-anchors>
## Memory Anchors (auto-loaded user context)

- [[project_mascot_as_vtuber_personality_surface]] — picks (Meshy + Blender MCP + Three.js), single-character mood-variation pattern, hard NO on facial mocap
- [[project_anti_slop_grounded_gemini_thesis]] — mascot is the visible body, grounding stack is the senses
- [[project_one_click_install_hard_req]] — Three.js + GLB browser-native = zero install impact, fits constraint
- [[feedback_no_scope_creep_clean_utility]] — single mascot, single Tauri overlay window, no `/hatch` in v2.0
- [[project_v2_planning_active]] — v1 narrow scope; Phase 13 bridges v1 → v2 mascot vision
- [[project_github_star_goal]] — mascot is the launch-trailer-defining feature, must be demo-quality

</memory-anchors>
