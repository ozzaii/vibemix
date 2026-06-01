# Packets — 2026-06-01 (durable archive + recovery)

**Why this dir exists:** the live coordination inbox `/tmp/vibemix-codex-inbox/` was wiped by a
macOS `/tmp` rotation (reboot/cleanup) — it was never a safe archive. From now on **every final
packet lands here, in the git tree**, not in `/tmp`. Track or commit a packet before relying on it.

**Status:** the work is bruised, not dead. All Claude-produced workflow docs were **recovered from
the surviving session transcripts** (`~/.claude/.../subagents/workflows/wf_*/`). Codex-authored raw
packets are gone as raw text but their **conclusions survive** in `.planning/handoffs/` (see below).

---

## 1. Authoritative / corrected

| Doc | What | Status |
|---|---|---|
| [`DRIFT-current-head.md`](DRIFT-current-head.md) | Drift-aware landing-readiness sweep at HEAD `dc4702eb` (6 commits since `e5c0e34e`; utility `wf_1f8b30d4-c6e`) | **FRESHEST current-HEAD truth — read first.** Tree SAFE (HOLD-bleed CLEAN; DROP speech still dirty-only + default now OFF). **1 CRITICAL ship-blocker:** MOSS model not bundled + no downloader + unwrapped call site (`__main__.py:1311`) → fresh-machine boot crash (MOSS is now the only voice). **+ package checker RED** (4 unassigned library-freshness paths). Codex consumed the board: settings-nav/freshness-badge/sentencepiece/drop-default-OFF all landed. Raw: `_drift-raw-wf_1f8b30d4.json`. |
| [`CODEX_VERIFICATION-current-head.md`](CODEX_VERIFICATION-current-head.md) | Read-only verification of the 5 LAND commits since `2bd44cc5` at HEAD `e5c0e34e` (22-agent adversarial workflow `wf_c96f6f8d-aa8`) | **Current-HEAD truth. Start here for landing.** All 5 commits ACCEPTED (302d747d/3892f4bd/6254c923/8105b04f/e5c0e34e). 8105b04f Serato writer: opt-in/double-gated/merge-preserved/byte-conformant — only real-Serato render eye-check remains. Includes the dirty-tree hunk-staging map + 5 ground-state corrections. |
| [`NEXT-LAND-BOARD-current-head.md`](NEXT-LAND-BOARD-current-head.md) | Ranked top-8 next slices (analysis) | **The routing map.** 4 SAFE_NOW (settings-nav fix, cue-export GUI, freshness badge, real-audio cue eval) + 1 source-safe watcher (P0 freshness) + 3 HOLD (MOSS-only TTS = ear-pass, DROP-call = grounding-review+on-by-default, Beatmatch producer = live proof). Full per-slice fields + lane summaries + HOLD gate register. |
| [`CODEX_READY-next-land-board.md`](CODEX_READY-next-land-board.md) | Codex-facing actionable packet | **Pick up here to land.** L1-L5 land queue with exact include/keep-out + proof + the shared-file hunk-staging recipe; H1-H3 hold queue with each gate. |
| `_verification-raw-wf_c96f6f8d.json` | Raw 11-item evidence (findings + adversarial verdicts) | Durable raw backing for the 3 docs above (persisted from `/private/tmp` immediately — the wipe can't touch it). |
| [`viber-capability-CORRECTION.md`](viber-capability-CORRECTION.md) | Source-verified correction to the Viber packet's #1 P0 | **READ THIS over the recovered Viber packet.** "Crate entirely unplugged" was FALSE — it's wired via Tauri `invoke()` (main.rs:105-113 / api.ts:2354-2476 / index.ts renderers). Real gaps: watcher, cue-GUI, freshness badge. NOTE (2026-06-01 verification): `ipc.library.*` is **conditionally** both-ended (gated on `if ipc_router is not None`), not pure-dead — reconcile before deleting. |
| [`CODEX_PACKAGE_SWEEP_STATUS.md`](CODEX_PACKAGE_SWEEP_STATUS.md) | Codex sweep status after package verification | **Start here for the landing phase.** Strict package assignment is green, 32 READY + 3 HOLD packet docs are durable, the Apple Silicon sidecar freshness blocker has been cleared, latest-code signed package boot/Quit is proven from a copied DMG app, and remaining release blockers are launch-collateral hold plus final live/release acceptance. |
| [`CODEX_GOLD_STRUCTURE.md`](CODEX_GOLD_STRUCTURE.md) | Grouped product-stream map over the verified packet archive | **Use this for batching.** It turns the packet pile into Gold 0-7 streams (control plane, observability/eval, IPC/transport, library/Viber/cues, Learn/Earned, speech/Judge/mascot, runtime/package/signing, economics/launch) while preserving LAND/HOLD boundaries. |
| [`CODEX_READY-planning-control-plane.md`](CODEX_READY-planning-control-plane.md) | Package 0/0B-0H proof packet for planning/control-plane docs and package governance | **LAND packet, planning control slice.** Dirty-tree package checker, future-AI routing, IPC/dependency/refactor/rebuild handoffs, Claude fanout archive, capability ledger, and final acceptance contract are classified as LAND docs with current checker/test/diff evidence. |
| [`CODEX_READY-product-posture-docs-cleanup.md`](CODEX_READY-product-posture-docs-cleanup.md) | Package 0I proof packet for public/product posture docs cleanup | **LAND packet, product posture docs slice.** Public/current docs are aligned to managed commercial service posture without stale OSS-first or false signed-release claims; repo/launch/docs tests and stale-claim grep passed with one historical internal KNOWBOOK line explicitly bounded. |
| [`CODEX_READY-ai-message-observability-spine.md`](CODEX_READY-ai-message-observability-spine.md) | Package 1A proof packet for shared AI-message logging and verification | **LAND packet, observability backbone slice.** Live cohost, Viber/Codex, eval judge, bench, deck vision, debrief, and Learn tutor surfaces persist inspectable AI-message/evidence rows; verifier proof covers session/global artifacts and move-bearing rows. |
| [`CODEX_READY-audio-vibe-contract-prompt-guard.md`](CODEX_READY-audio-vibe-contract-prompt-guard.md) | Package 8E proof packet for the live-audio prompt contract | **LAND packet.** Prompt steers Gemini/Sven away from treating audio as proof of track/deck/control causality; focused prompt tests + Ruff passed. |
| [`CODEX_READY-cohost-viber-release-matrix-wrapper.md`](CODEX_READY-cohost-viber-release-matrix-wrapper.md) | Package 1E proof packet for the cohost/Viber release matrix wrapper | **LAND packet, release-gate composition slice.** Matrix composes autopilot, corpus, runtime canaries, and FLX4 proof policy; safe automation run passed with FLX4 skipped. |
| [`CODEX_READY-cohost-viber-live-rehearsal-wrapper.md`](CODEX_READY-cohost-viber-live-rehearsal-wrapper.md) | Package 1F proof packet for the live rehearsal lifecycle wrapper | **LAND packet, live rehearsal lifecycle slice.** Wrapper can start/use source sidecar and run the matrix; safe no-start smoke fails correctly when no live socket is listening. |
| [`CODEX_READY-cohost-viber-runtime-canaries-wrapper.md`](CODEX_READY-cohost-viber-runtime-canaries-wrapper.md) | Package 1G proof packet for focused cohost/Viber runtime canaries | **LAND packet.** 8 canaries exercised/passed; wrapper tests, syntax check, and Ruff passed. |
| [`CODEX_READY-debrief-test-hygiene.md`](CODEX_READY-debrief-test-hygiene.md) | Package 1B proof packet for mechanical debrief test lint cleanup | **LAND packet, test hygiene slice.** Removes unused imports/import-order/f-string lint from debrief tests; debrief suite remains green. |
| [`CODEX_READY-desktop-auto-master-16ch-upgrade.md`](CODEX_READY-desktop-auto-master-16ch-upgrade.md) | Package 15 proof packet for explicit BlackHole 16ch routing under auto-master mode | **LAND packet, macOS audio routing slice.** Tauri auto-master defaults no longer hijack explicit `BlackHole 16ch` requests; audible deck proof still required. |
| [`CODEX_READY-emote-mascot-reaction-bridge.md`](CODEX_READY-emote-mascot-reaction-bridge.md) | Package 8C proof packet for bridging co-host `[emote:*]` controls to mascot reactions | **LAND packet, source-wired mascot reaction slice.** Co-host emote tags are stripped from speech/transcript, whitelisted intents increment `reaction_intent_seq`, and the Tauri mascot consumes each fresh sequence once; live visual proof still required. |
| [`CODEX_READY-ipc-contract-cleanup.md`](CODEX_READY-ipc-contract-cleanup.md) | Package 3 proof packet for pruning stale IPC bus contracts | **LAND packet, IPC cleanup slice.** Top-level IPC count is intentionally 72; stale library bus wrappers and debrief placeholders are gone while real library search/similar remains via Tauri commands. |
| [`CODEX_READY-auto-anlz-hot-cue-pipeline.md`](CODEX_READY-auto-anlz-hot-cue-pipeline.md) | Package 4 proof packet for materialized ANLZ/auto cue provenance through suggestions | **LAND packet, offline cue provenance slice.** ANLZ and auto anchors materialize only when DJ cues are absent; source/confidence/A-H slots survive cache, pill suggestions, and Viber sections, while auto uncertainty stays CARE. |
| [`CODEX_READY-library-ui-live-read-context.md`](CODEX_READY-library-ui-live-read-context.md) | Package 5 proof packet for Viber chat live-read context in the library UI | **LAND packet, Viber live-read UI slice.** The library webview normalizes deck/source/audio-window/live-evidence context before calling `library_chat`, shows waiting/partial/armed proof state, and clears stale unsupported context. |
| [`CODEX_READY-compact-pill-polish.md`](CODEX_READY-compact-pill-polish.md) | Package 6 proof packet for compact next-suggestion pill interactions | **LAND packet, pill UI slice.** Collapsed hover peek stays grounded/empty-silent, risky or auto-review suggestions surface as CARE, click/keyboard completion clears stale state, and Playwright covers narrow layout, focus, demo pads, and reduced motion. |
| [`CODEX_READY-learn-operator-action-bridge.md`](CODEX_READY-learn-operator-action-bridge.md) | Package 7 proof packet for Learn operator-action prompts | **LAND packet, Learn setup-action bridge.** Course 3 route fixes and generic grounded operator actions cross ws/Tauri into one compact booth prompt, preserve route/step evidence in ARIA/title, and screen-only controls avoid false missing-highlight warnings. |
| [`CODEX_READY-beatmatch-judge-honesty-boundary.md`](CODEX_READY-beatmatch-judge-honesty-boundary.md) | Package 8 proof packet for Learn beatmatch Mastered honesty | **LAND packet, Learn truth boundary.** The owned-deck judge and recognizer branch are tested, but Beatmatch remains not live-creditable until a production `BEATMATCH_GRADED` emitter exists; stale stored mastery is masked and reality pins guard the missing producer. |
| [`CODEX_READY-earned-wall-live-refresh.md`](CODEX_READY-earned-wall-live-refresh.md) | Package 9 proof packet for refreshing the Earned Wall after live cited credits | **LAND packet, Learn runtime refresh slice.** Cited coach events can advance/persist Learn progress, emit `ipc.learn.progress_state`, and fire a fixed `session.say(..., add_to_chat_ctx=False)` Mastered line once; live desktop repaint proof remains pending. |
| [`CODEX_READY-live-stack-cost-pricing-model.md`](CODEX_READY-live-stack-cost-pricing-model.md) | Package 10 proof packet for the live-stack cost model and budget CLI | **LAND packet, internal cost-model slice.** Pricing rows carry source/date/verified flags, `library budget --stack live` emits human/JSON reports, Cartesia Sonic stays `! UNVERIFIED`, and external pricing copy remains gated on billing confirmation. |
| [`CODEX_HOLD-launch-collateral.md`](CODEX_HOLD-launch-collateral.md) | Package 11 hold packet for current launch collateral | **HOLD packet.** Screenshot/media mechanics pass, but launch-copy files still carry stale release posture, free/open-source positioning, cloud/privacy overclaims, Viber cue-export overclaims, and old amber-era design language. Rewrite before public/partner use. |
| [`CODEX_HOLD-open-hold-lanes.md`](CODEX_HOLD-open-hold-lanes.md) | Consolidated hold packet for all currently dirty Hold Lane sections | **HOLD packet.** Makes every active hold lane explicit with dirty-path counts and promotion rules so scratch/research/eval artifacts are not accidentally bundled into LAND commits. |
| [`CODEX_HOLD-flx4-live-acceptance-current.md`](CODEX_HOLD-flx4-live-acceptance-current.md) | Current signed-DMG FLX4 live acceptance attempt | **HOLD packet.** Latest signed copied-DMG app booted live context and saw DDJ-FLX4 MIDI/audio presence, but release acceptance failed honestly: no direct MIDI motion frames, no recent moves, no audible deck audio, and no resolved deck identity in the proof window. |
| [`CODEX_READY-runtime-memory-clap-readiness.md`](CODEX_READY-runtime-memory-clap-readiness.md) | Package 12 proof packet for runtime memory/CLAP readiness | **LAND packet, memory readiness slice.** Empty stale sqlite-vec tables self-heal to current CLAP dimensions, populated stale tables fall back instead of wiping/mixing, memory ingest runs off-loop/best-effort, and diagnostic `--session` disables CLAP indexing while still proving the session bus. |
| [`CODEX_READY-tauri-sidecar-bundle-freshness-guard.md`](CODEX_READY-tauri-sidecar-bundle-freshness-guard.md) | Package 13 proof packet for stale Tauri sidecar bundle rejection | **LAND packet, package-input guard slice.** The guard rejects placeholder, missing, tiny, non-executable, incomplete, missing-schema, and stale-schema sidecars before Tauri packaging; after fresh Apple Silicon rebuilds, the guard is green, the embedded IPC schema matches source, latest-code unsigned Tauri app/DMG drag-install smoke passes, the bundled sidecar boots, and normal Quit leaves no orphan. |
| [`CODEX_READY-macos-signing-notarization-flow.md`](CODEX_READY-macos-signing-notarization-flow.md) | Package 13B proof packet for macOS signing/notarization support | **LAND packet, signing-flow slice.** Local Apple-ID fallback and `APPLE_SIGNING_IDENTITY` alias are documented/wired; latest artifact `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` is Developer-ID signed, notarized, stapled, Gatekeeper accepted, secret-scanned clean, drag-install smoked, and copied-DMG-app boot/Quit proven. Live DJ proof remains open. |
| [`CODEX_READY-viber-library-request-live-guard.md`](CODEX_READY-viber-library-request-live-guard.md) | Package 5B proof packet for Viber library requests with live context attached | **LAND packet, Viber text-boundary slice.** Library/crate requests no longer surface unsupported live-move fallback text when live context is only a guard rail; suppressed leaks remain recorded in `live_verification`. |
| [`CODEX_READY-viber-library-freshness-status.md`](CODEX_READY-viber-library-freshness-status.md) | Package 5C proof packet for source-aware library freshness status | **LAND packet, first slice only.** `library stats --json` now carries cache/source freshness through Python, Rust, and UI normalization; full watcher/refusal behavior remains next. |
| [`CODEX_READY-viber-stale-setprep-tool-guard.md`](CODEX_READY-viber-stale-setprep-tool-guard.md) | Package 5D proof packet for fail-closed Viber set-prep tools | **LAND packet, guard slice.** Product MCP tools now block local-library search/sequence/export/facts when freshness is not current; watcher/UI action remains next. |
| [`CODEX_READY-library-freshness-watcher-pulse.md`](CODEX_READY-library-freshness-watcher-pulse.md) | Package 5E proof packet for live-session freshness nudges | **LAND packet, watcher pulse slice.** Runtime polls source-aware freshness and reuses the existing staleness banner nudge when the library turns stale; follow-up current-source proof found and fixed the late-client delivery gap. |
| [`CODEX_READY-library-staleness-replay-on-connect.md`](CODEX_READY-library-staleness-replay-on-connect.md) | Package 5E/5F follow-up for reliable staleness nudge delivery | **LAND packet, runtime delivery slice.** `ipc.library.staleness_nudge` is now retained as sticky status and replayed to late websocket clients; current-source live proof captured the stale nudge after boot. Rebuild/re-sign before packaged claim. |
| [`CODEX_READY-stale-library-refresh-action.md`](CODEX_READY-stale-library-refresh-action.md) | Package 5F proof packet for stale library refresh UI action | **LAND packet, action slice.** Staleness nudge carries optional refreshable XML `source_path`/`reason`; Settings banner can trigger the existing importer through `Refresh library`. Current-source nudge delivery is proven; packaged refresh proof still required after rebuild. |
| [`CODEX_READY-library-freshness-badge.md`](CODEX_READY-library-freshness-badge.md) | Package 5G proof packet for the shell freshness badge | **LAND packet, shell readout slice.** Main shell footer consumes `libraryStats()` and shows `library fresh/stale/not indexed/unknown` without adding backend behavior. Build and focused UI tests passed; visual/package proof remains later. |
| [`CODEX_READY-judge-voice-runtime-wire.md`](CODEX_READY-judge-voice-runtime-wire.md) | Package 8B proof packet for Vibe Judge evidence in TRACK_CHANGE prompts | **LAND packet, judged-evidence speech slice.** Judged verdicts attach grounded `[judge:transition@t]` evidence to the next prompt; abstains inject nothing. Live two-deck artifact proof still required. |
| [`CODEX_READY-live-tts-shutdown-hygiene.md`](CODEX_READY-live-tts-shutdown-hygiene.md) | Package 14 proof packet for closing nested live TTS providers | **LAND packet, runtime cleanup slice.** Shutdown closes the live TTS chain and nested provider sessions once; focused/full smoke tests passed and a source run reached the ws bus, stopped at `-> bye`, and showed no unclosed-session warning. |
| [`CODEX_READY-no-spoken-fallbacks-live-guard.md`](CODEX_READY-no-spoken-fallbacks-live-guard.md) | Package 8D proof packet for stripping unsafe live-claim fallbacks | **LAND packet, spoken safety slice.** Guard-corrected live-cohost text is kept in artifacts/eval but not voiced; release report blocks any regression where the fallback is spoken. |
| [`CODEX_READY-release-binary-verification-hardening.md`](CODEX_READY-release-binary-verification-hardening.md) | Package 13C proof packet for post-sign binary verifier hardening | **LAND packet, release-verifier slice.** Strict branded secret scans remain active while generated signatures/native blobs avoid noisy generic39/sk-substring false positives; current rebuilt macOS `.app` scans clean. |
| [`CODEX_READY-session-ipc-diagnostics-wiring.md`](CODEX_READY-session-ipc-diagnostics-wiring.md) | Package 2 proof packet for live session IPC and diagnostics wiring | **LAND packet, session transport slice.** IPC count/codegen parity is 72/72, status/profile/citation/snapshot channels are both-end wired, source-mode websocket probes passed, and mock-transfer now contracts the new drop/proof/deferred-note anchors. |

## 2. Recovered named artifacts (the day's work — all in `recovered/`)

> ⚠️ These are **verbatim workflow outputs**, recovered from transcripts. Treat their self-claims
> as workflow-asserted (lower evidence rank than current source); the Viber packet specifically
> carries a known inverted P0 — see the CORRECTION above. Research/goldmine docs are design-only.

**Product / capability:**
- `…viber-capability-exploration…md` (347L) — Viber capability + product-gap map. **Apply the CORRECTION.**
- `…mix-gold-mine-recovery-ledger.md` (225L) — 45 ideas, real-vs-claimed wiring ledger.
- `…the-vibemix-creative-idea-forge.md` (202L) — 33 scored creative ideas.
- `…learn-module-reality-map…md` (89L) — v11.0 "Earned" lesson→Competent→Mastered producer/consumer map.
- `…earned-wall-skill-tree…md` (44L) — 6-competency × 2-stage producer/consumer map.

**Ecosystem / license:**
- `…the-vibe-web-map.md` (156L) + `…vibe-web-map-fact-check-addendum.md` (166L) — OSS DJ/MIR ecosystem, license-verified (madmom = NC BLOCKED; python-audio-separator = torch-hard avoid).

**Mixxx goldmine (GPL-2.0 — learn-from-spec ONLY, never vendor source):**
- `…the-mixxx-goldmine-map.md` (162L, Round 1) + sub-specs: beat-detection+beatgrid (113L),
  tempo/phase sync (129L), cue logic (110L), musical-key detection (99L).
- `…the-mixxx-goldmine-map-round-2…md` (204L) + sub-specs: EQ/filter DSP R-SLOP unlock (170L),
  controller-mapping engine + device catalog (150L), mixer/crossfader curve math (132L),
  loop+beatjump (96L), waveform RGB band-split (99L), crossfader-curve capability map (91L).

## 3. Phase fragments (scout/refute intermediates — low value, kept for completeness)

Short transcript outputs (14–99L) from scout/adversarial-refute phases of the audit workflows
(public-claims scout, dirty-path check, monetized-posture confirm, runtime-anti-slop verify, etc.).
Files `recovered/wf_{163ba30a,2f8307d9,3a74b067,433453b0,49e25400,7a8321fa,7b89e59b,8ff71b82,9b1a672c,a46bea3a,ab04e1f7,af18018f,b4cda12d,d120ebf7,eadf5888}…md`. These are intermediate evidence, not final packets.

## 4. Codex-authored packets — raw text GONE, conclusions PRESERVED

The `CODEX_READY-*` (Codex's implementation packets), `CODEX_VERDICT-*`, and `CODEX_OBSERVATION-*`
were written by Codex directly to `/tmp` and are **not** in Claude's transcripts → raw text lost.
Their decisions live in these committed docs (verified present):
- `.planning/handoffs/2026-05-31-package-checklist.md` (3499L) — the package lanes 0–13C.
- `.planning/handoffs/2026-05-31-capability-integration-ledger.md`
- `.planning/handoffs/2026-05-31-final-acceptance-contract.md`
- `.planning/handoffs/2026-05-31-future-ai-routing.md`
- `.planning/handoffs/2026-05-31-rebuild-brief.md`
- `.planning/handoffs/2026-05-31-maintainability-map.md`

If a specific Codex packet's full text is needed, **re-synthesize it** (the checklist + ledger
carry its files/acceptance) or have Codex re-emit it **into this dir**, not `/tmp`.

## 5. Recovery method (re-runnable)

- `_recover_all.py` — pulls every workflow's best document(s) from the transcript journals +
  assistant messages (`type=result` fields and assistant text blocks), length-ranked, alt-docs
  saved so multi-doc workflows aren't truncated. Re-run anytime: `python3 _recover_all.py`.
- `_recover_viber.py` — single-packet recovery (superseded by `_recover_all.py`).
- Source of truth for recovery: `~/.claude/projects/-Users-ozai-projects-dj-set-ai/05e3ff51-…/subagents/workflows/wf_*/`.

## 6. Process rule going forward

1. Packets → `.planning/packets/<date>/`, **in the repo**, never `/tmp`.
2. Maintain this `INDEX.md` as packets land.
3. Track (or commit) a packet before relying on it. `/tmp` is scratch, not an archive.

## 7. Workflow outputs — where everything lives (Codex: read this)

Workflow output exists in **three layers**. Codex should rely on layer A only.

**A. DURABLE — in the repo, Codex-readable (the ONLY source of truth):** `.planning/packets/2026-06-01/`
- Verification (run `wf_c96f6f8d-aa8`): `CODEX_VERIFICATION-current-head.md`, `NEXT-LAND-BOARD-current-head.md`, `CODEX_READY-next-land-board.md`, raw `_verification-raw-wf_c96f6f8d.json`.
- Drift sweeps (utility below): `DRIFT-<head>.md` + raw `_drift-raw-<runid>.json`, written here each run. **Codex's pick-up point after every drift run.**
- Reusable utility script: `_drift_verify.workflow.js`.

**B. RAW / EPHEMERAL — do NOT rely on (this is the `/tmp` trap that already bit us once):**
- Live task output: `/private/tmp/claude-501/.../tasks/<task-id>.output` — **wiped on reboot/cleanup.**
- Agent transcripts: `~/.claude/projects/-Users-…/subagents/workflows/wf_*/` — session-scoped raw agent logs; recoverable via `_recover_all.py` but not a handoff surface.

**Rule:** the orchestrator (Claude) extracts every workflow's result and persists the human-facing doc + raw JSON into layer A **immediately** on completion. Codex never reads `/tmp` or transcripts — it reads layer A. If a doc Codex needs is missing from layer A, it was not persisted yet → ask, don't hunt `/tmp`.

**Re-runnable drift utility (Codex or Claude):**
```
Workflow({ scriptPath: ".planning/packets/2026-06-01/_drift_verify.workflow.js",
           args: { since: "<last-verified-HEAD-sha>" } })
```
It verifies what landed since `since`, runs the **HOLD-bleed sentinel** (did a gated item — DROP-call speech, MOSS-only-without-sentencepiece, etc. — land/stage without its gate?), scans current ship-blockers, re-checks the HOLD gates, and refreshes the next-slice board. Output → `DRIFT-<head>.md` in this dir. Set `since` to the HEAD recorded in the most recent `DRIFT-*`/`CODEX_VERIFICATION-*` doc so each run covers only the new delta.
