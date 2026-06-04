export const meta = {
  name: 'wire-userready',
  description: 'Wire-everything ALL-MODULES -> USER-READY integration audit (many agents). Reads the frontend + backend exit-maps + all packets, resolves inter-lane handshakes, traces the full fresh-user path, and produces USER-READY-WIRING-EXIT-MAP.md = the final integration wires + per-session ship-wire goals to hand to the AIs.',
  phases: [
    { title: 'Audit', detail: '10 parallel slices: fresh-user path E2E, cross-engine handshakes, democratization E2E, 3-tier gap, packaging/DMG, anti-slop/grounding final, voice-end-to-end, learn-end-to-end, cue-end-to-end, inter-lane conflicts vs FE/BE maps' },
    { title: 'Synthesis', detail: 'read FE+BE exit-maps + all packets, write USER-READY-WIRING-EXIT-MAP.md + per-session ship-wire goals + NEEDS-CLARIFICATION' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host in the ship endgame. Quality bar: "real DJ friend in your ear, no AI slop"; grounding is law. BUILT-BUT-DARK; fix = WIRING; exact wires only (file:line -> file:line). 3 proof tiers: SRC != PKG != LIVE; test-passing-but-dark = 0. Read-only; do NOT launch the sidecar (one socket 127.0.0.1:8765). This is the INTEGRATION pass: read the two exit-maps just produced - .planning/packets/2026-06-04/FRONTEND-WIRING-EXIT-MAP.md and BACKEND-WIRING-EXIT-MAP.md - and the ship packets (SHIP-DRIVE.md, SHIP-FINISH-PLAN.md, SHIP-READINESS-2026-06-04.md) FIRST. Your job is what those two MISSED: the seams between frontend and backend, the cross-engine handshakes, and the end-to-end fresh-user path to a user-ready landing. Do not re-list a wire already in the FE or BE map; reference it and focus on the JOIN. Builders must NOT rush to exit at test-green; the exit is by-ear/by-eye in the real app.`

phase('Audit')

const audits = await parallel([
  () => agent(`Slice 1 - the FRESH-USER PATH end-to-end (the on-ramp that must not have one dead step). ${CTX}
Trace, as a brand-new non-dev on a clean Mac: download DMG -> open (Gatekeeper) -> first-run wizard (skill level) -> audio routing (BlackHole install + route the DJ app) -> reach the brain (paste Gemini key in-GUI OR flip proxy toggle) -> models auto-fetch (CLAP/CUE/MOSS or Chatterbox) -> start a set -> hear a grounded line. Mark EACH step LIVE / DARK / MISSING with the file/handler that owns it. The first dead step is the ship blocker. Output "## U1 fresh-user-path" the step ladder + the exact wire for each dead step.`, { label: 'ur:fresh-user', phase: 'Audit' }),
  () => agent(`Slice 2 - CROSS-ENGINE handshakes. ${CTX}
Connections that make the product coherent but may be unexploited: taste<->suggestion, library<->learn, debrief<->profile, key/camelot<->next-suggestion, intel-scorer<->pill, cue<->Viber<->semantic search. For each: both endpoints file:line, what the join buys at ship, wire-vs-build, effort. Exclude wires already in FE/BE maps. Output "## U2 cross-engine".`, { label: 'ur:cross-engine', phase: 'Audit' }),
  () => agent(`Slice 3 - DEMOCRATIZATION end-to-end (no .env hand-edit, ever). ${CTX}
Join the Frontend key-field/proxy-toggle to the backend persist handler to the live brain init: a fresh user pastes a key in the GUI and the NEXT reaction uses it, with no restart-from-terminal and no secret logged/committed. Trace config.json convergence (Rust store reload before save) + keychain. Output "## U3 democratization-e2e" the seam wires + any missing handler.`, { label: 'ur:democratization', phase: 'Audit' }),
  () => agent(`Slice 4 - the 3-PROOF-TIER gap. ${CTX}
What is SRC-green but PKG-dark (in source, not in the signed DMG at HEAD - the ~158-commit-stale DMG) or LIVE-dark (in the DMG but a real user never reaches it)? List the items that pass tests yet a stranger would never experience. Output "## U4 tier-gap".`, { label: 'ur:tier-gap', phase: 'Audit' }),
  () => agent(`Slice 5 - PACKAGING / DMG / release gates. ${CTX}
Read-only (do not build): DMG freshness vs HEAD, PyInstaller specs, release gates (MOSS bundle / Chatterbox model bundle? / learn wavs / Developer-ID sign / notarize+staple / updater + freshness manifest), sidecar boot-clean. What must rebuild at HEAD and which steps are external (SignPath/Apple)? Output "## U5 packaging" the gate report + remaining steps.`, { label: 'ur:packaging', phase: 'Audit' }),
  () => agent(`Slice 6 - ANTI-SLOP / GROUNDING final sweep across human-facing surfaces. ${CTX}
Every surface a human perceives (voice line, pill text, organism glow, learn coaching, debrief) must light ONLY for grounded/cited events (Invariant #2/#3). Find any surface that can fire un-caused (slop risk): a fallback line, a default glow, a placeholder that reads as real. Output "## U6 grounding-final" each risk + the guard wire.`, { label: 'ur:grounding', phase: 'Audit' }),
  () => agent(`Slice 7 - VOICE end-to-end (founder concern, the JOIN). ${CTX}
Given the BACKEND map's voice fix, verify the FULL chain a user experiences: pick voice in Settings -> persisted to config.json -> sidecar reads it on a normal/packaged launch (NOT env) -> the live agent speaks in that voice -> the model is bundled/auto-fetched in the DMG. Mark each link LIVE/DARK. Output "## U7 voice-e2e" the seam wires + bundle status.`, { label: 'ur:voice-e2e', phase: 'Audit' }),
  () => agent(`Slice 8 - LEARN end-to-end (the fused beatmatch loop join). ${CTX}
Kill-criterion: a beginner on L2.01 hears the kicks drift+lock, Sven SAYS it, the lock-meter needle centers, [ev:BEATMATCH_GRADED@t] resolves on the ws bus. Given FE+BE learn wires, verify the full loop joins (audible decks -> grade -> IPC -> HUD + tutor voice), honoring A1 (never over a live set). Output "## U8 learn-e2e" the seam + any remaining break.`, { label: 'ur:learn-e2e', phase: 'Audit' }),
  () => agent(`Slice 9 - CUE end-to-end + reuse for other engines (Viber/semantic). ${CTX}
Kaan: make the cue work "sexy + useful for other engines such as Viber, semantic, etc." Trace offline-audio -> CueAnchor -> CueSet -> land() -> Rekordbox/Serato/M3U export, AND cue -> Viber auto-cue-on-export -> semantic/library reuse. Where does the chain break for a user, and what reuse is left on the table? Output "## U9 cue-e2e" the seam wires + the reuse wins.`, { label: 'ur:cue-e2e', phase: 'Audit' }),
  () => agent(`Slice 10 - INTER-LANE CONFLICTS vs the FE/BE maps. ${CTX}
Read FRONTEND-WIRING-EXIT-MAP.md + BACKEND-WIRING-EXIT-MAP.md closely. Find: IPC types one side expects that the other does not provide; a handler named by one map that the other did not assign; a hot file two lanes both touch (e.g. learn/runtime.py - organism teaching_focus AND learn cue-grade). For each conflict: the two sides + the single-owner resolution. Output "## U10 inter-lane" the conflicts + resolutions.`, { label: 'ur:inter-lane', phase: 'Audit' }),
])

const A = audits.map((x, i) => x || `(userready slice ${i + 1} failed)`).join('\n\n')

phase('Synthesis')

const report = await agent(`Write .planning/packets/2026-06-04/USER-READY-WIRING-EXIT-MAP.md - the master integration exit-path that lands vibemix at a fully-wired, user-ready state. FIRST read FRONTEND-WIRING-EXIT-MAP.md, BACKEND-WIRING-EXIT-MAP.md, and the ship packets so this is the JOIN, not a re-list. Synthesize the 10 integration slices below.

Sections:
1. "## Are we one wire away or many?" - blunt state of the end-to-end chain.
2. "## The fresh-user path - step ladder" - each step LIVE/DARK/MISSING with the owning wire (this is the spine).
3. "## Integration exit-map" - a table: seam | both endpoints (file:line) | the join wire | owning lane | proof (by-ear/by-eye E2E).
4. "## Inter-lane resolutions" - the single-owner calls for every conflict found vs the FE/BE maps (hot files, IPC handshakes).
5. "## Ship-wire goals to hand to the AIs" - the FINAL per-session paste-ready /goal blocks (Frontend / library / learn / sven / keystone+packaging), each disjoint, each carrying the SHARED LAW (one tree, git add exact paths never -A, IPC Frontend-only, socket 8765 one, commit -s Kaan Ozkan <rahipdotaci@gmail.com>, do NOT rush to exit at test-green - prove the E2E by-ear/by-eye in the real app, commit each piece the instant it is green+proven). These are what we ship to the sessions.
6. "## NEEDS-CLARIFICATION" - only genuine blockers needing a Kaan decision. If none, "none".

Evidence only. Anti-slop: no em-dashes, active voice, specific. Do NOT commit. After writing, return a tight ~14-line chat summary: the one-wire-or-many answer, the fresh-user step ladder verdict, the inter-lane resolutions, and any NEEDS-CLARIFICATION.

--- AUDIT SLICES ---
${A}
---`, { label: 'ur:synthesis', phase: 'Synthesis' })

return report
