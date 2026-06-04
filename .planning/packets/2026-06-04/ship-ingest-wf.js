export const meta = {
  name: 'ship-ingest',
  description: 'Post-"codexes-done" SHIP INGESTION across EVERY surface. 14 verifier agents (two waves of 7) ingest the REAL landed state at current HEAD + adversarially verify each done-claim (test-passing-but-dark=0), synthesized into SHIP-INGEST-2026-06-04.md — every surface landed-vs-claimed-vs-dark + GA-readiness + the single next move.',
  phases: [
    { title: 'Ingest', detail: '14 surface verifiers (2 waves of 7): voice, start-gate, brain/proxy-client, frontend, learn, library-cue, intel->spoken-line, runtime-io, fresh-user E2E, SRC gates, PKG, docs/README honesty, CI/workflows, critical-path critic' },
    { title: 'Synthesis', detail: 'consolidate into SHIP-INGEST-2026-06-04.md (per-surface landed/claimed/dark + 3-tier + GA-readiness verdict + remaining critical path + single next move)' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host (LiveKit + a hosted AI-model reaction brain "Sven" + local on-device Chatterbox voice; Apache-licensed client). Quality bar: "real DJ friend in your ear, no AI slop"; grounding is LAW. The product is BUILT-BUT-DARK: engine ~70-80% real, the human-facing last layer is the gap.
THIS IS A SHIP INGESTION PASS, run RIGHT AFTER the autonomous Codex build-loops reported "DONE". Your job: ingest the REAL landed state at the CURRENT HEAD and ADVERSARIALLY VERIFY every done-claim. Do NOT trust "it's done" or green tests alone: test-passing-but-dark = 0. For each thing claimed landed, prove it is actually wired (by grep/codegraph/by-bus reasoning), or mark it CLAIMED-BUT-DARK with the exact gap. READ-ONLY: code + git + codegraph + the committed packets; do NOT edit code, do NOT launch the sidecar (one socket 127.0.0.1:8765). Build on the existing maps, do not re-derive: .planning/packets/2026-06-04/SHIP-MAP-MASTER.md, SHIP-NEXT-GOALS-2026-06-04.md, WIRE-DRIVE.md, USER-READY/FRONTEND/BACKEND-WIRING-EXIT-MAP.md. Re-pin a FRESH HEAD SHA before acting on any line number (the tree moved a lot since the maps — many loops just committed). Note the HEAD you read at.
3 proof tiers, never conflated: SRC (green tests on source) != PKG (in a signed DMG built at HEAD) != LIVE (a real user reaches it). Every finding precise with file:line + a SRC/PKG/LIVE verdict + a LANDED / CLAIMED-BUT-DARK / NOT-STARTED flag. Anti-slop: no em-dashes, active voice, specific, no invented numbers.
LOCKED DECISIONS (map against them; they may now be LANDED):
(1) VOICE = the zero-shot pranker Chatterbox is the ONLY cohost voice; MOSS NUKED; Mac = mlx-audio (Apple-Silicon Metal), no compatible GPU = voiceless + honest banner. The #1 blocker was VOICE REACHABILITY: mlx-audio as a pyproject extra + bundle the ref + first-run model fetch via model_assets.py + env-seed VIBEMIX_TTS_ENGINE at __main__.py + swap the release gate --require-moss-source->--require-chatterbox-source. VERIFY which of these actually landed.
(2) BRAIN = hosted Bravoh proxy DEFAULT, LIVE + FUNDED (verified today: register->JWT->gemini-3.5-flash->HTTP 200 on api.altidus.world/api/vibemix/v1/register). Client default flips direct->proxy; set_brain BYO handler. VERIFY the client default + set_brain + no-key graceful (no sys.exit).
(3) START GATE = SHIP-CRITICAL: no heavy model resident at idle, a Start button, silent pre-warm, Stop releases. VERIFY the _on_session_start backend handler + the main() idle/activate split + the frontend Start button + IPC both ends.
(4) STREAK = Daft-Punk Technologic robot voice, SEQUENCED behind rebinding to a cited EXECUTED transition first.
SHIP SHAPE (Kaan-locked today): v1 = macOS Apple-Silicon (arm64) ONLY; Windows = v1.1 fast-follow (mlx-audio is Apple-only so Intel Macs are voiceless too). SignPath/Windows are OFF the v1 critical path (use VIBEMIX_PRETAG_MAC_ONLY=1). GA-TAG LANDMINE: the repo is now Bravoh-ai/vibemix (main pushed); release.yml + companion-sign fire on a v* tag push = the full signed matrix incl Windows + SignPath + the now-broken --require-moss-source gate. A 0.1.0 source-snapshot PRE-RELEASE was cut on a non-v tag (no matrix fired). Do NOT push v0.1.0 until voice+packaging land + the moss->chatterbox gate-swap + Windows excluded + secrets.
README/DOCS PARTNER-COPY POLICY (public-facing): NO model names (no "Gemini"/"MOSS" -> say "AI model"/"on-device voice"); NEVER expose api.altidus.world (say "Bravoh's hosted service"); domain is bravoh.ai NOT bravoh.com; org is Bravoh-ai NOT ozzaii. The current README still violates all of these AND leaks a dev feature-matrix dump (Phase numbers, commit SHAs, "Kaan ear-passes daily", KAAN-ACTION) = internal slop. README is pinned by 4 CI gates: test_readme_shape.py, test_readme_feature_matrix_sync.py (AUTO-GEN markers + sync_feature_matrix.py --check), scripts/launch/check_readme_grids_a11y.py (dj-software grid=6 imgs, controller grid=10 cells locked to midi/profiles), scripts/check_readme_hero_hash.py (hero sha256=PLACEHOLDER sentinel).`

phase('Ingest')

// Wave A (7) — the engine + human-facing surfaces
const waveA = await parallel([
  () => agent(`INGEST 1 — VOICE reachability (the #1 blocker). ${CTX}
VERIFY each required wire actually landed at HEAD: (a) is mlx-audio a pyproject.toml extra? (b) is cohost_voice_ref.wav a PyInstaller datas asset in vibemix-core.macos.spec + does chatterbox_tts.py resolve_ref_path() prefer the bundled path? (c) is there an install_chatterbox_model() in library/model_assets.py + a 'library models --install chatterbox' verb? (d) is os.environ.setdefault("VIBEMIX_TTS_ENGINE", ...) seeded at __main__.py boot/packaged-defaults? (e) is the release gate swapped --require-moss-source->--require-chatterbox-source in pretag_check.sh + release.yml? (f) does chatterbox_available() have a path to True on a packaged launch? For each: LANDED / CLAIMED-BUT-DARK / NOT-STARTED + file:line + SRC/PKG/LIVE. Output "## ING1 voice".`, { label: 'ing:voice', phase: 'Ingest' }),
  () => agent(`INGEST 2 — START GATE + model lifecycle. ${CTX}
VERIFY: is "ipc.session.start"/"ipc.session.stop" registered (register_handler) in session_loop.py/__main__.py with a real _on_session_start? Is main() split into a light idle boot + an _activate_session() (idle=cold, Start activates, Stop releases)? Is the silent pre-warm hook wired? Frontend: is there a real Start/Stop button bound to emitIpc + sessionActive state in tauri/ui/src? Use the ipc-wiring lens (both ends). For each: LANDED/CLAIMED-BUT-DARK/NOT-STARTED + file:line. Output "## ING2 start-gate".`, { label: 'ing:startgate', phase: 'Ingest' }),
  () => agent(`INGEST 3 — BRAIN / proxy CLIENT + fresh-user no-crash. ${CTX}
VERIFY: config_store llm_mode DEFAULT = proxy (not direct)? base_url = api.altidus.world? no-key direct falls back to proxy (no sys.exit(4) anywhere in __main__.py)? jwt_cache register path POST {base}/api/vibemix/v1/register? set_brain handler persists llm_mode + writes the key to brain_env_path()? Walk the fresh no-key boot and confirm it reaches the funded brain, never crashes. For each: LANDED/CLAIMED-BUT-DARK + file:line + SRC/LIVE. Output "## ING3 brain-proxy".`, { label: 'ing:proxy', phase: 'Ingest' }),
  () => agent(`INGEST 4 — FRONTEND, every surface (tauri/ui/src). ${CTX}
Per surface mark LIVE-data / STATIC-DARK / CRASH at HEAD: DesktopShell, session deck hero + transcript, citation receipt ts-join (does the reaction ts now byte-match so the underline fires LIVE?), settings drawer (BYO key field + voice picker), pill (reasons[] cap, cue_confidence, streak), the organism particle visual, the Cue Tray (built + backend cmd?), learn EYE surfaces, debrief, wizard (key/proxy step? voice-download step?). Note any IPC type emitted with no consumer or vice-versa. Output "## ING4 frontend" per-surface + file:line.`, { label: 'ing:frontend', phase: 'Ingest' }),
  () => agent(`INGEST 5 — LEARN teaching loop. ${CTX}
VERIFY loop closure at HEAD: OBSERVE (audible practice) -> GRADE (runtime.py) -> CARRY-TO-IPC (LearnLiveGrade) -> CREDIT (runtime/coach.py) -> UNLOCK. Is [ev:BEATMATCH_GRADED] now consumed in runtime/coach.py's credit path (W12) so a LIVE set can credit the skill, or still practice-only? Is Invariant #3 (practice audio never over a live set) intact? Did the "launched smoke failure" (462157e7) get resolved? For each stage: closes? + file:line. Output "## ING5 learn".`, { label: 'ing:learn', phase: 'Ingest' }),
  () => agent(`INGEST 6 — LIBRARY + the cue moat. ${CTX}
VERIFY: CLAP ONNX + sqlite-vec search LIVE; cue moat (CUE-DETR -> SmartCue -> non-destructive carriers, VM provenance leak closed); Viber auto-cue-on-export default-on; the W13 consolidation (does live Viber auto-cue now route through cue_landing.land(), or still the parallel inline spine?); the Cue Tray backend (library_land_cues Tauri cmd + CueSet summary/target/floor fields) landed? auto_crate.py. For each: wired/dark + file:line. Output "## ING6 library-cue".`, { label: 'ing:library', phase: 'Ingest' }),
  () => agent(`INGEST 7 — INTEL -> the SPOKEN line (the narrator->coach gap). ${CTX}
Use codegraph callers. VERIFY which intel reaches the LIVE spoken prompt vs only the pill: eq_move_model (the keystone unlock) live via apply_live_claim_guard? transition_judge abstain on a master-only rig (does it ever fire)? Did transition_scorer reasons / move_grade verdict / judge risk_flags get WIRED to speak (W8/W9/W11), or still pill-only? For each engine: reaches-spoken-line? + file:line. Output "## ING7 intel-spoken".`, { label: 'ing:intel', phase: 'Ingest' }),
])

// Wave B (7) — the proof tiers + docs + CI + critic
const waveB = await parallel([
  () => agent(`INGEST 8 — RUNTIME-IO (runtime/ audio/ platform/ events/ midi/). ${CTX}
VERIFY at HEAD: ws_bus single socket (Inv #4); how many IPC handlers registered now (session_loop.py)? master capture 2ch-first determinism + the route-doctor RMS-flip (fixed at all sites?); MIDI profile count (10 vs 11 — reconcile against src/vibemix/midi/profiles/*.json); macOS screen-watch (djay-only or app-agnostic now?); the NI HID bridge ingest seam. Output "## ING8 runtime-io" wired/dark + file:line.`, { label: 'ing:runtime', phase: 'Ingest' }),
  () => agent(`INGEST 9 — FRESH-USER E2E ladder at current HEAD. ${CTX}
Walk install -> wizard (skill + audio route + key/proxy + voice download) -> first session -> Start -> grounded line heard in the Chatterbox voice -> deck underlines its citation. Mark EACH step LIVE / DARK / CRASH at HEAD with file:line. This is the ground-truth "can a stranger get value" verdict. Output "## ING9 fresh-user".`, { label: 'ing:freshuser', phase: 'Ingest' }),
  () => agent(`INGEST 10 — SRC proof tier (the full test + gate status NOW). ${CTX}
Map the gate inventory + which are RED at HEAD: pytest default suite, vitest, tsc --noEmit, model-literal grep, clean-checkout imports, IPC schema parity, no-speculative-phrase AST, repo-scrub, the 4 README gates (shape/matrix-sync/grids-a11y/hero-hash), test_no_api_key_surface (key-field conflict), auto_crate stop-reason. Run/inspect what you safely can read-only. List the RED set + the one-line fix + whether each is a product regression or a stale-policy re-pin. Output "## ING10 src-tier".`, { label: 'ing:src', phase: 'Ingest' }),
  () => agent(`INGEST 11 — PKG proof tier (packaging readiness for an arm64 GA). ${CTX}
Read-only (do NOT build): vibemix-core.macos.spec (does it now bundle mlx-audio + the chatterbox ref instead of MOSS?); the release gates (moss->chatterbox swap done?); dist/ DMG staleness vs HEAD; the updater-manifest 3-platform requirement (relaxable to arm64-only for v1?); sidecar freshness gate (dirty seam files?). Give the exact ordered steps to a fresh signed arm64 HEAD DMG + which are Kaan-only (Apple notarize). Output "## ING11 pkg-tier".`, { label: 'ing:pkg', phase: 'Ingest' }),
  () => agent(`INGEST 12 — DOCS / README honesty (public-facing). ${CTX}
Audit README.md + the launch docs against the PARTNER-COPY POLICY: every remaining "Gemini"/"MOSS"/"api.altidus.world"/"bravoh.com"/"ozzaii" occurrence (file:line); the dev feature-matrix dump leak (Phase numbers/SHAs/"Kaan ear-passes"/KAAN-ACTION); stale claims (djay-Pro-first vs macOS-arm64, MOSS voice, Windows framing). For EACH README CI gate (shape/matrix-sync/grids-a11y/hero-hash), state what a de-slop rewrite must preserve to stay green vs what it intentionally breaks (re-pin). Output "## ING12 docs-readme" a precise fix-list + the gate-preservation contract.`, { label: 'ing:docs', phase: 'Ingest' }),
  () => agent(`INGEST 13 — CI / workflows + supply-chain. ${CTX}
Map .github/workflows: what release.yml fires on (v* tag), the --require-moss-source gate (now broken post-MOSS-nuke), companion-sign.yml (v*), sbom.yml (release: published), full-test-matrix, dep-audit, secret-scan + .secrets.baseline. Which workflows would FAIL or misfire on the Bravoh-ai org repo today (missing secrets, broken gate, Windows job)? What must change before a v* GA tag is safe. Output "## ING13 ci-workflows".`, { label: 'ing:ci', phase: 'Ingest' }),
  () => agent(`INGEST 14 — CRITICAL-PATH critic + GA-readiness. ${CTX}
Given everything: what is the shortest honest path from HEAD to a signed arm64 GA v0.1.0 (a stranger installs, reaches the funded brain, hears a grounded Chatterbox line, no crash)? Sequence the remaining blockers, name file-island collisions (main()/config_store single-owner), name what is Kaan-only (Apple notarize, by-ear keystone, secrets, the v* tag push). Be the completeness critic: which surface did the other 13 agents most likely OVER-claim as done? What is the SINGLE next move. Output "## ING14 critical-path".`, { label: 'ing:critic', phase: 'Ingest' }),
])

const ings = [...waveA, ...waveB]
const M = ings.map((x, i) => x || `(ingest agent ${i + 1} failed)`).join('\n\n')

phase('Synthesis')

const report = await agent(`Write .planning/packets/2026-06-04/SHIP-INGEST-2026-06-04.md — THE consolidated post-"codexes-done" ship-ingestion. Read the 14 surface ingests below + the key packets. This is the authoritative answer to "the loops say done, what is ACTUALLY shippable across every surface".

Structure:
1. "## Verdict" — 5 lines: GA-readiness (can we push a signed arm64 v0.1.0? what blocks it?), the single next move, the count of LANDED vs CLAIMED-BUT-DARK vs RED-gate items, the proxy-live fact, the GA-tag landmine reminder.
2. "## Every surface" — a table: surface | state (LANDED / CLAIMED-BUT-DARK / NOT-STARTED) | SRC/PKG/LIVE | file:line anchor | the gap if not done. One row per surface (voice, start-gate, brain-proxy, frontend-panels, learn, library-cue, intel-spoken, runtime-io, fresh-user, docs-readme).
3. "## Codex done-claims, verified" — for each thing the loops claimed landed, the adversarial verdict: REAL / test-passing-but-dark / partial, with the proof or the gap.
4. "## 3-tier ship state" — SRC (RED gate list + 1-line fixes + regression-vs-re-pin), PKG (arm64 DMG steps + externals), LIVE (fresh-user ladder verdict).
5. "## README / docs" — the precise de-slop fix-list (model-name/altidus/bravoh.com/ozzaii/feature-matrix-leak/stale claims) + the per-gate preservation contract.
6. "## Critical path to GA v0.1.0" — ordered blockers + the single next move + collisions + Kaan-only items + the v* tag landmine.
7. "## Doc index delta" — only what changed since SHIP-MAP-MASTER.

Evidence only, file:line precise, note the HEAD synthesized at, no invented numbers, no em-dashes, active voice. Do NOT commit (the organizer commits). After writing, return a tight ~18-line chat summary: the Verdict block + the every-surface one-word states + the single next move + GA-readiness yes/no.

--- 14 INGESTS ---
${M}
---`, { label: 'ing:synthesis', phase: 'Synthesis' })

return report
