export const meta = {
  name: 'ship-map-master',
  description: 'HUGE fresh-eye full-codebase + ship-state mapping pass. 14 parallel deep readers across every subsystem + the 3 proof tiers + the locked decisions, synthesized into SHIP-MAP-MASTER.md — the single orientation doc the organizer reads post-compact to re-organize the ship.',
  phases: [
    { title: 'Map', detail: '14 parallel deep readers: state/agent, intel, library/cue, learn, runtime/audio/platform, frontend, wired-vs-dark census, voice path, proxy/democratization, SRC tier, PKG tier, fresh-user+5-seams, planning-corpus, critical-path critic' },
    { title: 'Synthesis', detail: 'consolidate into SHIP-MAP-MASTER.md (architecture + wired/dark + 3-tier ship state + decisions + blockers + critical path + doc index)' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host (LiveKit + Gemini Flash reaction brain "Sven" + local Chatterbox-Turbo TTS; Apache-licensed client). Quality bar: "real DJ friend in your ear, no AI slop"; grounding is LAW (nothing un-caused reaches the human). The product is BUILT-BUT-DARK: the engine is ~70-80% real, the human-facing last layer is the gap. THIS IS A FRESH-EYE full-codebase + ship-state mapping pass — the organizer will compact right after this lands and use the map to re-orient and organize the ship. Be a comprehensive CARTOGRAPHER, not a fixer: READ-ONLY (code + git + codegraph + the committed packets), do NOT edit code, do NOT launch the sidecar (one socket 127.0.0.1:8765). Build on the existing maps, do not re-derive — read as needed: .planning/packets/2026-06-04/WIRE-DRIVE.md, SHIP-WIRE-GOALS-RERAIL.md, USER-READY-WIRING-EXIT-MAP.md, FRONTEND-WIRING-EXIT-MAP.md, BACKEND-WIRING-EXIT-MAP.md, SHIP-READINESS-2026-06-04.md, and .planning/packets/2026-06-03/WIRE-THE-GOLD-MASTER-BACKLOG.md.
LOCKED DECISIONS (treat as FIXED, map against them):
(1) VOICE = the zero-shot pranker Chatterbox is the ONLY cohost voice; MOSS is being NUKED; Mac = mlx-audio (built), Windows = a GPU backend BUILD, no compatible GPU = voiceless + honest banner. Ref = ~/.cache/vibemix/cohost_voice_ref.wav (source ~/Downloads/Prank_L4_t20 (1).wav).
(2) BRAIN ACCESS = hosted Bravoh proxy DEFAULT, and it is NOW LIVE + FUNDED (verified today: register -> JWT -> gemini-3.5-flash -> HTTP 200 on api.altidus.world, path /api/vibemix/v1/register). The client default must flip from direct to proxy. In-GUI key field = advanced BYO.
(3) START GATE + model lifecycle = SHIP-CRITICAL: no heavy model resident at idle, a "Start" button, silent pre-warm.
(4) STREAK = full Daft Punk Technologic robot voice in v1, rebind to a cited EXECUTED transition first.
The #1 ship-blocker = the FRESH-USER CRASH (wizard done -> session boots mode=direct -> no key -> sys.exit(4)); fixed by the proxy-default flip + the set_brain backend handler.
3 proof tiers, never conflated: SRC (green tests) != PKG (in the signed DMG at HEAD) != LIVE (a real user reaches it). test-passing-but-dark = 0. Every finding precise with file:line. HEAD moves under you (many concurrent sessions) — note the HEAD you read at.`

phase('Map')

// Two sequential waves of 7 to stay under the server-side burst limit
// (a single 14-agent fan-out reliably trips it; 11-13 has cleared). Each
// wave is a barrier; full 14-map coverage preserved.
const waveA = await parallel([
  () => agent(`MAP 1 — the BRAIN: state/ + agent/. ${CTX}
Map MusicState (single-writer), refresh.py, event_detector.py (the EventType taxonomy + cooldowns), coach.py / prompt_builder.py (event->prompt cells), evidence_registry.py (citation grounding Inv #2), agent/dj_cohost.py (the live Gemini reaction path + scaffold/linter repair), the in-flight gate. For each: what it does, the data flow, what is REAL vs DARK/orphaned. Output "## MAP1 brain" with file:line anchors + a wired/dark verdict per component.`, { label: 'map:brain', phase: 'Map' }),
  () => agent(`MAP 2 — intel/ (the musical-intelligence primitives, ~16 modules). ${CTX}
Use codegraph callers/0-caller. Map claims/claim_validator/decision_runtime/decision_trace/decision_validator, transition_scorer, taste_model, transition_judge, eq_move_model, musical_ontology, profile_projection. For EACH: does its output reach the live coach prompt / a human surface, or is it ORPHANED (0 live callers)? This is the narrator->coach gap. Output "## MAP2 intel" each module + reaches-human? + the wire if dark.`, { label: 'map:intel', phase: 'Map' }),
  () => agent(`MAP 3 — library/ + the cue moat. ${CTX}
Map CLAP ONNX embeddings + sqlite-vec, cue_landing.py / cue_export.py / cue_folder.py / smart_cues.py, the Viber/codex curator (toolset.py, codex_curate.py, mcp_server.py), auto_crate.py, next_suggestion.py (the pill engine). What is wired to a live surface vs dark? The cue->Viber->pill chain status. Output "## MAP3 library-cue" with file:line + wired/dark + the moat status.`, { label: 'map:library', phase: 'Map' }),
  () => agent(`MAP 4 — learn/ (the teaching engine, ~35 modules). ${CTX}
Map the teaching loop closure: skill_tree/skill_recognizer/graduation, curriculum/lesson_flow, two_deck_player/beatmatch_practice_driver/beatmatch_judge/cue_placement_judge, runtime.py (IPC + grade), teaching_loop. How many of the 5 loop stages actually close? Is the grade carried to IPC or discarded? Audio-over-silence? A1 guard. The recent "launched smoke failure" commit (462157e7) — what failed? Output "## MAP4 learn" loop-closure % + dark spots + file:line.`, { label: 'map:learn', phase: 'Map' }),
  () => agent(`MAP 5 — runtime/ + audio/ + platform/ + events/ + midi/. ${CTX}
Map ws_bus + session_loop + suggestion service + soak/ttft, audio capture/playback ring buffers + Levels + the route-doctor (the 2ch-vs-16ch determinism), platform _audio/_screen/_hid backends (incl. the djay-only macOS screen crop + the orphaned NI HID bridge), event taxonomy emission, the 11 MIDI controller profiles. Output "## MAP5 runtime-io" wired/dark + the route-doctor + input-surface status with file:line.`, { label: 'map:runtime', phase: 'Map' }),
  () => agent(`MAP 6 — the FRONTEND (tauri/ui/src). ${CTX}
Map the DesktopShell, session deck/hero/citation receipt, settings drawer (the shipped BRAIN group key-field + voice picker, 8c6a7b6e), the pill (reasons/cue-confidence/streak), the organism (particle visual), cue-tray (built?), learn surfaces, debrief, wizard, the IPC client + ws bus consumption. Per surface: live data or static/dark? Output "## MAP6 frontend" per-surface wired/dark + file:line.`, { label: 'map:frontend', phase: 'Map' }),
  () => agent(`MAP 7 — WIRED-vs-DARK census (whole tree). ${CTX}
Use codegraph to enumerate substantial 0-caller functions + computed-but-never-surfaced ws/IPC fields across src/vibemix/** and tauri/ui/src. Distinguish "dark gold" (real value, no live surface) from "dead/legacy". This is the master dark-list. Output "## MAP7 dark-census" a ranked table: symbol | file:line | computed-what | dies-where | shippable-value y/n.`, { label: 'map:dark', phase: 'Map' }),
])

const waveB = await parallel([
  () => agent(`MAP 8 — the VOICE path end-to-end (vs the MOSS-nuke decision). ${CTX}
Map the current truth: agent/tts_chain.py engine select (default + env), agent/chatterbox_tts.py (mlx-audio, ref resolver, temp), agent/local_tts.py (MOSS — to be nuked), runtime/config_store.py (is there a tts_engine field yet?), __main__.py:1607/1621 call-sites + :1420 env-seed point, voice_presets, _router_config voice ids, every MOSS reference across the tree. What is wired NOW vs what the decision requires (config-reachable engine, Chatterbox default, MOSS gone, bundled ref). Output "## MAP8 voice" current-vs-required + the exact remaining wires.`, { label: 'map:voice', phase: 'Map' }),
  () => agent(`MAP 9 — DEMOCRATIZATION / proxy client path. ${CTX}
The proxy SERVER is now live+funded (api.altidus.world). Map the CLIENT side: agent/proxy_client.py, jwt_cache, the VIBEMIX_LLM_MODE switch (default still direct?), config_store mode/base_url, the boot path in __main__.py that sys.exit(4)s on missing key, the set_brain handler (absent?), the wizard key step. What must change client-side so a fresh no-key user routes through the funded proxy and never crashes. Output "## MAP9 democratization" the client wires + the crash path with file:line.`, { label: 'map:proxy', phase: 'Map' }),
  () => agent(`MAP 10 — SRC proof tier (the test + gate shape). ${CTX}
Map the test topology: pytest markers + the big suites, vitest (~886+), the CI gates (model-literal grep, clean-checkout imports, IPC schema parity, no-speculative-phrase, repo-scrub). Which gates are RED at HEAD (auto_crate stop-reason / persona tests / any)? What does green-SRC currently assert vs miss. Output "## MAP10 src-tier" gate inventory + RED list + what tests do NOT cover (the dark-but-green risk).`, { label: 'map:src', phase: 'Map' }),
  () => agent(`MAP 11 — PKG proof tier (packaging + DMG). ${CTX}
Read-only (do not build): the PyInstaller specs (vibemix-core.{macos,windows}.spec), the release gates (MOSS bundle -> now must become Chatterbox/mlx-audio + the ref clip; learn wavs; Developer-ID sign; notarize/staple; updater + freshness manifest), the dist/ DMG date + commit-distance from HEAD (the stale-DMG trap), sidecar boot. Output "## MAP11 pkg-tier" what the gates enforce + DMG staleness + the exact steps to a fresh signed HEAD DMG + which are external (SignPath/Apple).`, { label: 'map:pkg', phase: 'Map' }),
  () => agent(`MAP 12 — the FRESH-USER path E2E + the 5 W3 seams, re-verified at current HEAD. ${CTX}
Walk install -> wizard (skill + audio route + key/proxy) -> first session -> grounded line heard, marking each step LIVE/DARK/CRASH at the CURRENT HEAD. Re-verify the 5 seams from USER-READY-WIRING-EXIT-MAP.md (A brain handler, B voice+MOSS-nuke, C Start gate, D citation ts-carry, E proxy default) — which are still open. Output "## MAP12 fresh-user" the step ladder verdict + per-seam status with file:line.`, { label: 'map:freshuser', phase: 'Map' }),
  () => agent(`MAP 13 — the PLANNING CORPUS consolidation. ${CTX}
Read every .planning/packets/2026-06-04/*.md (the exit-maps, WIRE-DRIVE, SHIP-WIRE-GOALS-RERAIL, SHIP-READINESS, the gate decisions, the cue/pill/voice packets) + skim 2026-06-03 WIRE-THE-GOLD-MASTER-BACKLOG. Produce: the CANONICAL locked-decision set (one place), the open questions, and a ONE-LINE index of what each live doc is for. Resolve any contradictions between docs (newer wins; the 4 locked decisions are final). Output "## MAP13 corpus" the canonical decisions + open-Qs + the doc index.`, { label: 'map:corpus', phase: 'Map' }),
  () => agent(`MAP 14 — CRITICAL-PATH critic + the organize plan. ${CTX}
Step back: given everything, what is the SHORTEST honest path to a shippable v1 (a fresh stranger installs, reaches the funded brain, hears a grounded Chatterbox line, no crash)? Sequence the blockers (fresh-user crash -> voice -> start-gate -> packaging -> keystone capture), name collisions (main()/config_store single-owner), name what is Kaan-only (DMG sign/notarize, by-ear, credit already funded). What is the SINGLE next move. Be the completeness critic: what would we regret NOT mapping? Output "## MAP14 critical-path" the ordered ship path + collisions + the single next move + map-gaps.`, { label: 'map:critic', phase: 'Map' }),
])

const maps = [...waveA, ...waveB]
const M = maps.map((x, i) => x || `(map agent ${i + 1} failed)`).join('\n\n')

phase('Synthesis')

const report = await agent(`Write .planning/packets/2026-06-04/SHIP-MAP-MASTER.md — THE single fresh-eye orientation document the organizer reads post-compaction to re-organize the vibemix ship. Read the 14 maps below + the key packets so it is authoritative and contradiction-free. This doc must let a freshly-compacted organizer, in one read, know the whole system + exactly where to look + how to organize the ship.

Structure:
1. "## Read-me-first" — 6 lines: what vibemix is, the built-but-dark thesis, the 4 locked decisions (one line each), the proxy-now-live+funded fact, the #1 blocker (fresh-user crash), the single next move.
2. "## Architecture map" — each subsystem (brain/intel/library-cue/learn/runtime-io/frontend) in 2-4 lines with its key file:line anchors and a wired/dark verdict.
3. "## Wired vs DARK" — the ranked dark-list (shippable-value first): symbol | file:line | dies-where.
4. "## 3-tier ship state" — SRC (gates + RED list), PKG (DMG staleness + gate steps + externals), LIVE (fresh-user step ladder + the 5 seams status).
5. "## The voice path + the proxy path" — current-vs-required for each, the exact remaining wires.
6. "## Locked decisions (canonical)" + "## Open questions (Kaan)".
7. "## Lanes + ownership + collisions" — who owns what file-island, single-owner rules (main()/config_store/IPC schema), landed-vs-inflight.
8. "## Critical path to v1" — the ordered blocker sequence + the single next move + what is Kaan-only.
9. "## Doc index" — one line per live .planning/packets/2026-06-04 doc.

Evidence only, file:line precise, no invented numbers. Anti-slop: no em-dashes, active voice, specific. Note the HEAD it was synthesized at. Do NOT commit (the organizer commits). After writing, return a tight ~16-line chat summary: the read-me-first block + the critical-path single-next-move + the count of dark items and open RED gates.

--- 14 MAPS ---
${M}
---`, { label: 'map:synthesis', phase: 'Synthesis' })

return report
