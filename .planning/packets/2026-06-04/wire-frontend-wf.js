export const meta = {
  name: 'wire-frontend',
  description: 'Wire-everything FRONTEND audit (many agents): every UI surface vs its live data source, every emitted IPC/ws field vs its consumer. Produces FRONTEND-WIRING-EXIT-MAP.md = the exact wire (file:line -> file:line) per dead surface, routed to the Frontend session.',
  phases: [
    { title: 'Audit', detail: '10 parallel slices: IPC<->emit, render<->source, pill, organism, cue-tray, settings/voice-picker, deck/citation, learn surfaces, debrief, wizard/audio-route' },
    { title: 'Synthesis', detail: 'read ALL packets, write FRONTEND-WIRING-EXIT-MAP.md + per-surface exact wires + NEEDS-CLARIFICATION if any' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host in the ship endgame. Quality bar: "real DJ friend in your ear, no AI slop"; grounding is law (nothing un-caused reaches the human). The product is BUILT-BUT-DARK: the engine is ~70-80% real but the human-facing last layer is dark or ungrounded across voice/UI/learn/visuals. The fix is WIRING not building: find every break in the end-to-end chain and specify THE EXACT WIRE (the one change, file:line -> file:line) that closes it. 3 proof tiers, never conflated: SRC (green tests) != PKG (in the signed DMG at HEAD) != LIVE (a real user runs it and SEES a grounded result). test-passing-but-dark = 0. Read-only: code + git + codegraph + committed packets; do NOT launch the live sidecar (one socket 127.0.0.1:8765). Be exact: every finding = (what is computed/emitted, file:line) -> (where it dies) -> (the exact wire to close it). Read these packets FIRST and build on them, do not re-derive: .planning/packets/2026-06-04/SHIP-DRIVE.md, SHIP-FINISH-PLAN.md, SHIP-READINESS-2026-06-04.md; .planning/packets/2026-06-03/WIRE-THE-GOLD-MASTER-BACKLOG.md + GOLD-WIRING-MAP.md; the master-arrangement docs if present. The builders must NOT rush to exit at test-green; the exit is by-eye in the real app. Frontend island = tauri/ui/src/** + the IPC schema (messages.schema.json / messages.ts / validator.generated.mjs) + src/vibemix/ui_bus/*.py + mascot.html. Use codegraph for callers/0-caller and grep ws-bus field names across both sides.`

phase('Audit')

const audits = await parallel([
  () => agent(`Slice 1 - IPC/ws emit -> UI consumer. ${CTX}
Enumerate every message TYPE the backend emits to the frontend (ws_bus broadcasts + IPC messages.schema.json types + ui_bus python). For EACH: is it consumed by a real UI surface, or emitted-but-unread (dark)? Output "## S1 IPC emitted-but-unread": each dead type with emit file:line + the exact UI consumer wire to add (component file:line). Then the inverse smell: any UI handler subscribed to a type the backend never emits.`, { label: 'fe:ipc-emit', phase: 'Audit' }),
  () => agent(`Slice 2 - UI render -> live data source. ${CTX}
Walk tauri/ui/src/** for surfaces that render STATIC / placeholder / mock / hardcoded values where a live backend source exists. For each: the rendered element file:line, what it shows now, the live source field, the exact wire. Output "## S2 render-without-source".`, { label: 'fe:render-source', phase: 'Audit' }),
  () => agent(`Slice 3 - the PILL (SuggestionService surface). ${CTX}
next_suggestion reasons[] / cue-confidence receipts / runner-up hover / streak. Which of these are COMPUTED in src/vibemix (suggestion.py / next_suggestion.py) but NOT rendered in the pill UI? The streak counts a SUGGESTION grade not an executed transition (PILL-FAFO-AND-LEVELUP.md) - note the rebind. Output "## S3 pill" with each computed field file:line -> pill render wire.`, { label: 'fe:pill', phase: 'Audit' }),
  () => agent(`Slice 4 - the ORGANISM (particle visual soul). ${CTX}
Per project_vibemix_organism_visual_soul: ONE living particle organism (mascot + pill + Learn focus-glow), grounded (only lights for grounded events), speech-reactive, focuses+glows on what the tutor teaches. What does the backend emit (teaching_focus, speech levels, grounded events) and does the organism render consume it, or is the visual still random/dark? Output "## S4 organism" computed->render wires + whether the grounded-only rule holds.`, { label: 'fe:organism', phase: 'Audit' }),
  () => agent(`Slice 5 - CUE TRAY UI. ${CTX}
The cue-landing backend landed (library/cue_landing.py: CueSet/LandedCue/land + provenance). Does a Cue Tray UI exist that renders a CueSet (A-H slot ladder, ProvenanceBadge hollow-AUTO vs filled-DJ, ConfidenceMeter, locked DJ rows, empty-as-empty, one-consent Land button + target picker + Landed receipt)? If missing, specify the component + the library_land_cues IPC type to add. Output "## S5 cue-tray".`, { label: 'fe:cue-tray', phase: 'Audit' }),
  () => agent(`Slice 6 - SETTINGS drawer (democratization + VOICE picker). ${CTX}
SEED (verified): the live voice defaults to MOSS; Chatterbox-Turbo only via env VIBEMIX_TTS_ENGINE=chatterbox; GUI launch strips env (launchd) so the flag is UNREACHABLE from a normal app launch; there is NO settings control to pick the voice engine. Also democratization needs an in-GUI Gemini-key field + proxy toggle (today only .env hand-edit works). For each: the control to add, the IPC message def (Frontend owns the schema), the backend handler it must call (name it for the backend lane). Settings must repaint OPTIMISTICALLY (data-active locally, per convention). Output "## S6 settings" = key-field + proxy-toggle + voice-engine-picker wires.`, { label: 'fe:settings', phase: 'Audit' }),
  () => agent(`Slice 7 - SESSION deck / hero / citation receipt. ${CTX}
The "Deck Speaks" shell: a grounded co-host line should ignite a visible citation receipt; idle (grounded=false) must NOT flip to "AI service unreachable" (Invariant #5, idle != fault). Is the live transcript_delta + citation -> hero render wired? Is the idle-grounding-failure timer correctly active-only? Output "## S7 deck-citation" wires + the idle-guard status.`, { label: 'fe:deck', phase: 'Audit' }),
  () => agent(`Slice 8 - LEARN surfaces. ${CTX}
SEED: the beatmatch grade is computed then DISCARDED (no IPC carries it, runtime.py ~2088); MiniDeck.render_block has 0 callers; 36/37 lessons play no audio. On the FRONTEND side: is there a lock-meter HUD / grade display / lesson-flow surface that WOULD render these if the backend carried them? Specify the UI components + the IPC types they need (so the backend lane knows what to emit). Output "## S8 learn-ui".`, { label: 'fe:learn', phase: 'Audit' }),
  () => agent(`Slice 9 - DEBRIEF window (port 8766) + any second-surface. ${CTX}
Is the post-session debrief UI wired to real session data (events.jsonl / decision traces / profile)? dark or live? Output "## S9 debrief" wires.`, { label: 'fe:debrief', phase: 'Audit' }),
  () => agent(`Slice 10 - WIZARD / first-run / audio-route UI (the fresh-user on-ramp). ${CTX}
Trace the first-run wizard end-to-end on the frontend: skill-level step -> audio device/route step -> key/proxy step -> done. Where does a fresh non-dev hit a dead end (a step that has no UI, or a UI with no backend wire)? Output "## S10 wizard" the gaps + exact wires.`, { label: 'fe:wizard', phase: 'Audit' }),
])

const A = audits.map((x, i) => x || `(frontend slice ${i + 1} failed)`).join('\n\n')

phase('Synthesis')

const report = await agent(`Write .planning/packets/2026-06-04/FRONTEND-WIRING-EXIT-MAP.md for the vibemix Frontend session (cclaude). FIRST read every relevant packet in .planning/packets/2026-06-04/ and .planning/packets/2026-06-03/ so you build on them and never contradict an owned decision. Synthesize the 10 audit slices below into THE perfect frontend wiring exit-path.

Sections:
1. "## The exit, in one paragraph" - what "fully wired frontend" means here, blunt.
2. "## Wiring exit-map" - a table per surface: surface | computed/emitted source (file:line) | where it dies | THE EXACT WIRE (file:line -> file:line, or the IPC type to add) | proof (by-eye). Order by ship-leverage.
3. "## New IPC types to add" - Frontend owns the schema; list each type + the backend handler name the backend lane must implement (the handshake).
4. "## Paste-ready /goal for the Frontend session" - one block, island = tauri/ui/src/** + IPC schema + ui_bus, the SHARED LAW (one tree, git add exact paths never -A, IPC Frontend-only, socket 8765 one, optimistic repaint, commit -s Kaan Ozkan <rahipdotaci@gmail.com>, do NOT rush to exit at test-green - prove by-eye in the real app, commit each surface the instant it is green+proven).
5. "## NEEDS-CLARIFICATION" - only genuine ambiguities that block specifying an exact wire (the organizer will run a clarification workflow). If none, write "none".

Evidence only, no invented numbers. Anti-slop: no em-dashes, active voice, specific. Do NOT commit (the organizer commits). After writing, return a tight ~12-line chat summary: the count of dead surfaces, the top 5 wires, the new IPC types, and any NEEDS-CLARIFICATION.

--- AUDIT SLICES ---
${A}
---`, { label: 'fe:synthesis', phase: 'Synthesis' })

return report
