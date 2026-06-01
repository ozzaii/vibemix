Perfect! Now I have all the evidence I need. Let me compile a comprehensive report classifying all controls by their wiring status.

Based on my systematic read-only scout of the vibemix codebase, I can now provide a complete classification. The IPC wiring checker confirms all 72 message types are wired on both shell and sidecar ends. Let me now provide the detailed control classification.

## Scout Findings

**CONTROL CLASSIFICATIONS:**

### WIRED (Live-applies via IPC, state mutation confirmed)

1. **Mute Button (Deck Rail)** | STATE: WIRED
   - PATH: SessionLayout.ts:851-855 → muteBtn.addEventListener("click") → render-loop.ts:57-62 cohostMuteHandler → emitIpc("ipc.session.mute", {toggle: true})
   - HANDLER: session_loop.py:385 _on_settings_set registers "ipc.session.mute" handler → applies state → broadcasts ipc.session.mute {muted: bool}
   - EVIDENCE: ws-bridge.ts:248-250 subscribes to ipc.session.mute → applyMuteAck → setSessionState({muted: bool}) → render-loop next frame reads and renders mounted.muteButton.dataset.on
   - COMMAND: grep -n "onMute\|cohostMuteHandler\|ipc.session.mute" tauri/ui/src/session/{SessionLayout,render-loop,ws-bridge}.ts && grep -n "register_handler.*session.mute" src/vibemix/runtime/session_loop.py

2. **Persona (Mood Cycle) Button** | STATE: WIRED
   - PATH: SessionLayout.ts:838 → personaButton.click → render-loop.ts:101-111 cohostMoodCycleHandler → emitIpc("ipc.settings.set", {field: "mood", value: next})
   - HANDLER: session_loop.py:385 _on_settings_set → SettingsApplier.apply(field="mood", value) → broadcast ipc.settings.state with mood field
   - EVIDENCE: ws-bridge.ts:233-235 subscribes ipc.settings.state → applySettingsState → setSessionState({persona.mood}) → render-loop next frame reads and renders mounted.persona.dataset.mood
   - COMMAND: grep -n "cohostMoodCycleHandler\|MOOD_CYCLE\|ipc.settings.set" tauri/ui/src/session/render-loop.ts && grep -n "_on_settings_set" src/vibemix/runtime/session_loop.py

3. **Mode Picker (4-segment)** | STATE: WIRED
   - PATH: SessionLayout.ts:809 → modePicker.onChange → render-loop.ts:121-149 modeChangeHandler → local state write via setSessionState({mode}) → emitIpc("ipc.session.set_mode", {mode})
   - HANDLER: session_loop.py:267 register_handler("ipc.session.set_mode", _on_session_set_mode) → persists mode to ConfigStore.extra["session.mode"]
   - EVIDENCE: applyState(SessionLayout.ts:1047-1049) diffs and calls setModePickerActive → CSS data-active reflects mounted state
   - COMMAND: grep -n "modeChangeHandler\|ipc.session.set_mode" tauri/ui/src/session/{SessionLayout,render-loop}.ts && grep -n "_on_session_set_mode" src/vibemix/runtime/session_loop.py

4. **Status Row Input Buttons (Audio/AI/Screen/MIDI)** | STATE: WIRED
   - PATH: SessionLayout.ts:1010-1011 → statusInput.click → render-loop.ts:67-74 statusRecheckHandler → emitIpc("ipc.status.recheck", {component})
   - HANDLER: session_loop.py:270 register_handler("ipc.status.recheck") → probes the component → broadcasts ipc.status.tick with fresh status
   - EVIDENCE: ws-bridge.ts:228-230 subscribes ipc.status.tick → applyStatusTick → setSessionState(status.*) → render-loop diff applies setInputDown data-down/data-actionable
   - COMMAND: grep -n "statusRecheckHandler\|ipc.status.recheck" tauri/ui/src/session/{SessionLayout,render-loop}.ts && grep -n "register_handler.*status.recheck" src/vibemix/runtime/session_loop.py

5. **Fault Recovery Label (↻ RETRY)** | STATE: WIRED (Tauri command, not IPC)
   - PATH: SessionLayout.ts:867 → liveFault.click → render-loop.ts:45-50 cohostRetryHandler → invoke("restart_sidecar") [Tauri command]
   - EFFECT: Tauri bridge launches a fresh sidecar process → bridge picks up new sidecar's ipc.session.snapshot → footer flips back to GROUNDED
   - EVIDENCE: SessionLayout.ts:78 documents the callback; render-loop line 46 fires the Tauri invoke without waiting for IPC reply
   - COMMAND: grep -n "onRetry\|cohortRetryHandler\|restart_sidecar" tauri/ui/src/session/{SessionLayout,render-loop}.ts

6. **Vibe Engine (Library) Button** | STATE: WIRED (Tauri command, not IPC)
   - PATH: SessionLayout.ts:850 → vibeEngineBtn.click → render-loop.ts:79-84 openVibeEngineHandler → invoke("open_library_window") [Tauri command]
   - EFFECT: Tauri side opens a new OS window bound to the library/build surface; the button is presentation-only trigger for a side effect
   - EVIDENCE: render-loop.ts:79 comment states "uses the same registered Tauri command as the tray menu"; no IPC message type for this
   - COMMAND: grep -n "onOpenVibeEngine\|openVibeEngineHandler\|open_library_window" tauri/ui/src/session/{SessionLayout,render-loop}.ts

### ECHO (Broadcast persistence only — renders UI state but does not mutate sidecar model)

1. **Live Meter (Master Level Bar)** | STATE: ECHO
   - PATH: ipc.session.snapshot carries meters.music.rms (live every 30Hz) → ws-bridge.ts applySnapshot writes to SessionState → render-loop.ts:1144-1152 reads meters.music.rms, smooths via METER_ATTACK/METER_PEAK_DECAY, pokes DOM width%
   - MUTATION: None on sidecar; the meter is a pure presentation of inbound real-time signal. Shell reads, does NOT write back.
   - EVIDENCE: SessionLayout.ts:912 mounts meterFill (display-only); render-loop diffs and mutates width CSS only (no emitIpc)
   - COMMAND: grep -n "meters.music.rms\|meterFill\|width.*%\|METER_ATTACK" tauri/ui/src/session/{SessionLayout,render-loop}.ts && grep -n "broadcast.*snapshot" src/vibemix/runtime/session_loop.py

2. **Timecode Display (BPM/Key/Track)** | STATE: ECHO
   - PATH: ipc.session.snapshot carries timecode.{bpm, key, deck, track, genre} (live every 30Hz) → ws-bridge.ts applySnapshot writes to SessionState → render-loop.ts:1137-1141 reads and renders textContent
   - MUTATION: None on sidecar; display is purely reactive to deck state changes.
   - EVIDENCE: SessionLayout.ts:146,147 mounts bpm/key elements (display-only text); no emitIpc call wires from these
   - COMMAND: grep -n "timecode\|bpm\|key\|track" tauri/ui/src/session/{SessionLayout,render-loop}.ts && grep -n "broadcast.*snapshot" src/vibemix/runtime/session_loop.py

3. **Transcript Hero + Ghosts** | STATE: ECHO
   - PATH: ipc.session.snapshot carries transcript_delta array → ws-bridge.ts appendTranscript writes to SessionState → render-loop.ts:1097-1110 reads transcript[last-1:] and renders textContent with fade/color transitions
   - MUTATION: None on sidecar; transcript appends are pure broadcast from cohost LLM.
   - EVIDENCE: SessionLayout.ts:884-899 mounts now/ghost DOM (textContent rendered, no click handler); applyState diffs and sets textContent only
   - COMMAND: grep -n "transcript\|setGhost\|vmx-now\|vmx-ghost" tauri/ui/src/session/{SessionLayout,render-loop}.ts && grep -n "transcript_delta" src/vibemix/ui_bus/messages.py

4. **Receipt Animation (Rule + Cite)** | STATE: ECHO (Display choreography only)
   - PATH: ipc.session.snapshot + ipc.session.cohost_reaction carry reaction chips keyed by transcript line ts → ws-bridge.ts appendReaction writes reactions to SessionState → render-loop.ts:1113-1134 triggers fireReceipt CSS animation on new now-line ts
   - MUTATION: None on sidecar; the gesture is pure presentation re-fire on state diff. Shell does NOT emit when cite is clicked (that's a debrief deep-link, handled by pill/render-loop via invoke).
   - EVIDENCE: SessionLayout.ts:893-897 mounts cite (button for click → open_debrief_window, not ipc.session.mute-like IPC); fireReceipt.ts:1185-1192 only manipulates dataset.arrived (CSS trigger, no state mutation)
   - COMMAND: grep -n "fireReceipt\|cite.*click\|reactions\|onChipClick" tauri/ui/src/session/{SessionLayout,render-loop}.ts

### LOCAL (Optimistic render-loop update only — no persistence, wire data only)

1. **Mode Picker Active Segment Highlight** | STATE: LOCAL (optimistic + persistent)
   - PATH: modePicker.onChange fired immediately → mountedHandle?.current.onModeChange?.() called synchronously → render-loop modeChangeHandler → setSessionState({mode}) writes to singleton IMMEDIATELY → modePicker CSS data-active reflects new mode visually
   - FOLLOW-UP: Only AFTER window open succeeds does emitIpc("ipc.session.set_mode") fire; if window open fails, modeChangeHandler reverts setSessionState({mode: previousMode})
   - EVIDENCE: render-loop.ts:121-149 shows the two-phase: (1) local write, (2) window open, (3) IPC persist OR revert
   - COMMAND: grep -n "setSessionState.*mode\|openModeSurface\|previousMode" tauri/ui/src/session/render-loop.ts:121-149

### DISPLAY-GAP (Frontend renders a field the Python builder never fills — values stuck at default)

None detected in this sweep. The IPC wiring checker confirmed all 72 types have both shell and sidecar references, and spot checks of SessionSnapshot, SettingsState, StatusTick confirm Python emitters populate every required field before broadcast.

### DEAD (Handler exists on one end but not the other)

None. The IPC wiring checker run confirmed: "OK — every type has both a shell and a sidecar reference."

---

**SUMMARY:**

- **WIRED (6)**: Mute, Mood, Mode, Status Recheck, Fault Retry, Vibe Engine
- **ECHO (4)**: Meter, Timecode, Transcript, Receipt
- **LOCAL (1)**: Mode Picker (optimistic + eventual persist)
- **DEAD**: 0
- **DISPLAY-GAP**: 0

All controls are wired. The 72 IPC types pass the bidirectional check. No one-ended features detected.
