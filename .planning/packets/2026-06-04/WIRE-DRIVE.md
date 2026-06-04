# WIRE-DRIVE — the 3-workflow wire-everything program (2026-06-04)

Kaan's call: the product is built but the human-facing last layer is dark. Run a wire-everything audit across all lanes + all related code + all other code, show every session THE PATH TO EXIT by wiring everything perfectly, hand it to the AIs, they wire it (keep working, do NOT rush to exit at test-green), land, and ping the monitor. Three workflows, many agents each, take us to a full frontend + backend + all-modules + user-ready landing.

## The voice seed (verified before launch — the founder's live concern)

"I still hear Sven (MOSS), the new voice never plays" is a WIRING gap, not a bug:
- `agent/tts_chain.py:36 build_tts_chain` defaults the engine to MOSS; Chatterbox-Turbo only when env `VIBEMIX_TTS_ENGINE=chatterbox` (line 53). Live call-sites `__main__.py:1607` + `:1621` via `_build_tts_chain_or_mute`.
- The packaged GUI launch strips env (launchd), so the flag is UNREACHABLE from a normal app launch → always MOSS.
- No config.json / Settings control picks the engine — it is env-only.
- The Technologic (Daft Punk) streak/combo robot voice was handed off but has ZERO code (`grep technologic/streak_voice/combo_voice` = none).
The fix lives in the BACKEND workflow's `## VOICE` section: make the engine reachable from a normal launch (read from config.json that Settings writes), land the streak voice grounded to a cited event, keep voice cited-only.

## The three workflows (scripts on disk, durable)

| # | Script | Island | Output packet |
|---|---|---|---|
| W1 | `wire-frontend-wf.js` | tauri/ui/src + IPC schema + ui_bus | `FRONTEND-WIRING-EXIT-MAP.md` |
| W2 | `wire-backend-wf.js` (voice-led) | src/vibemix/** python + scripts + specs | `BACKEND-WIRING-EXIT-MAP.md` |
| W3 | `wire-userready-wf.js` (integration) | the seams + fresh-user path | `USER-READY-WIRING-EXIT-MAP.md` |

Each: ~10-11 parallel audit agents → synthesis that READS ALL PACKETS first → writes the exit-map + paste-ready per-session /goal blocks. Every finding = (computed/emitted file:line) → (where it dies) → (THE EXACT WIRE). Synthesis does NOT commit; the organizer commits after.

## Sequencing (the read-all-then-decide gate Kaan set)

1. Launch **W1 + W2 in parallel** (disjoint islands, both foundational).
2. On completion: organizer reads BOTH exit-maps + checks each `## NEEDS-CLARIFICATION`.
3. If a real blocker/ambiguity exists → run a **clarification workflow** (or AskUserQuestion to Kaan for the voice default-engine call) before W3.
4. Then launch **W3** (integration → user-ready), seeded by W1+W2.
5. Organizer commits the three exit-maps + hands the per-session /goal blocks to the AIs (Frontend cclaude + 3 Codex lanes + keystone owner).

## After the AIs wire it

The builders wire from the exit-maps, prove by-ear/by-eye in the real app (test-green is not done), commit surgically, and land. The existing **monitor `bz70ahvzt`** (clean product tree + 10-min quiesce) trips when they are done and pings the organizer → fire `ship-final-wf.js` → `SHIP-FINAL-VERDICT.md` → route any residual fixes to 2 Codex. Kaan can compact and walk away; this file + SHIP-DRIVE.md hold the whole loop.

## Gate resolved (Kaan-locked 2026-06-04)

W1 + W2 landed (`FRONTEND-WIRING-EXIT-MAP.md`, `BACKEND-WIRING-EXIT-MAP.md`). The voice root-cause confirmed: engine is env-only and the GUI strips env, so MOSS always wins; fix = `config_store.tts_engine` + `os.environ.setdefault` at `__main__.py:1420` (no `tts_chain.py` edit). Three product calls answered before W3:

1. **MOSS NUKED — finetuned Chatterbox-Turbo cohost is the ONLY voice** (Kaan, "moss nuke sadece cohost finetuned"). Remove MOSS as engine/default/floor across the tree; the live agent renders only the finetuned Chatterbox model (finetuned weights + ref + mlx-audio bundled, licensing cleared). **Platform consequence (Kaan-accepted, macOS-first):** mlx-audio is Apple-only, so Windows + Intel Macs have NO cohost voice once MOSS is gone — they ship voiceless / text-transcript-only as a tracked follow-up (a portable finetuned voice later), NOT a MOSS floor. macOS Apple-Silicon ships with voice now. No MOSS, no cloud TTS, ever, as a fallback.
2. **Brain access default = hosted Bravoh proxy** (fresh user pastes nothing). Needs live proxy credits + per-client rate limit (external/Kaan dependency). In-GUI key field = advanced BYO-key. Wizard takes the proxy-default shape.
3. **Streak voice = full Daft Punk Technologic in v1** — but re-bind the streak to a cited EXECUTED transition first (kill the self-applauding suggestion-grade count) so it is grounded before it speaks.

Organizer-set smaller defaults (Kaan may override): cue-confidence = 3 buckets; runner-up reveal = debrief; cue-landing = consolidate via `cue_landing.land()`; learn tutor voice = co-host engine with persona warmth/pace.

W3 (`wire-userready-wf.js`) is seeded with these and running. Its `USER-READY-WIRING-EXIT-MAP.md` carries the final per-session ship-wire `/goal` blocks.

## SHARED LAW (every session)

One shared tree `ux-redesign-impeccable`: commits survive, uncommitted gets WIPED by a sibling git op. `git add <exact paths>` NEVER `-A`; verify `git diff --cached`. IPC schema = Frontend lane only; backend lanes request types. Sidecar `127.0.0.1:8765` = one socket (`pkill -f "python -m vibemix"` before any probe). `commit -s`, Kaan Özkan <rahipdotaci@gmail.com>. Do NOT rush to exit at test-green; prove the real app. Commit each piece the instant it is green + proven.
