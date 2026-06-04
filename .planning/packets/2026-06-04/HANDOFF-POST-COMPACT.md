# HANDOFF — post-compact re-entry for the organizer (2026-06-04)

The organizer (read-only swarm Claude; Codex sessions build) spawned a HUGE fresh-eye mapping workflow, wrote this handoff, and the user compacts now. On wake, this file + the workflow output are how you re-orient.

## �first action on wake
1. Check if the master map landed: `.planning/packets/2026-06-04/SHIP-MAP-MASTER.md` (workflow task `w27d369o1`). **READ IT FIRST** — it is your whole-system fresh eye (architecture + wired/dark + 3-tier ship state + decisions + blockers + critical path + doc index). If it is not there yet, the workflow is still running; wait for the task notification, then read it + commit it (pathspec: `git add` it then `git commit -- <path>`).
2. Then check session convergence: `git log --since="2026-06-04 18:00" --format='%h %ci %s'` + `git status --porcelain -- src/vibemix tauri/ui/src`. The Codex lanes run autonomous loops on their OWN goals until Kaan pastes the re-rail goals.

## what happened this session (the load-bearing facts)
- Ran 3 wiring workflows -> committed `FRONTEND-WIRING-EXIT-MAP.md` + `BACKEND-WIRING-EXIT-MAP.md` + `USER-READY-WIRING-EXIT-MAP.md` (W1/W2/W3). Dark is concentrated in 5 cross-engine seams.
- **PROXY IS NOW LIVE + FUNDED (the big win):** swapped a new Tier-2 Prepay Gemini key into `VIBEMIX_PROXY_GEMINI_KEY` on `ssh altidus` (`/var/www/bravoh-backend/.env`, backup kept; Bravoh's own key untouched), rolling-restarted `bravoh-clean-api-0/1`. Verified end-to-end: `register -> JWT -> POST /api/vibemix/v1/register` 200 and `gemini-3.5-flash` passthrough -> HTTP 200 "pong". The keyless brain is live on our funded dime. (Key was pasted in chat -> Kaan should rotate as hygiene.) Detail: memory `project_vibemix_proxy_deployed_altidus`.
- Locked 4 decisions + resolved W3's 4 clarifications + wrote the STOP protocol + per-session re-rail goals (`SHIP-WIRE-GOALS-RERAIL.md`).

## the 4 LOCKED decisions (final, do not re-open)
1. VOICE = zero-shot pranker Chatterbox is the ONLY cohost voice; MOSS NUKED; Mac=mlx-audio (built), Windows=GPU backend BUILD, no-GPU=voiceless+honest banner. Ref `~/.cache/vibemix/cohost_voice_ref.wav` (source `~/Downloads/Prank_L4_t20 (1).wav`). NOT finetuned.
2. BRAIN ACCESS = hosted proxy DEFAULT (now live+funded). Client must flip `VIBEMIX_LLM_MODE` default direct->proxy + base_url api.altidus.world. In-GUI key field = advanced BYO.
3. START gate + model lifecycle = ship-critical (no resident model at idle, "Start/Başlat" button, silent pre-warm). NOT a full main() refactor.
4. STREAK = full Technologic robot voice in v1, rebind to a cited EXECUTED transition first.

## the #1 ship-blocker
The FRESH-USER CRASH: wizard done -> session boots `mode=direct` (config_store.py:194) -> no key -> `sys.exit(4)`. Fix = flip default to proxy (now funded) + the `set_brain` backend handler (KEYFIELD shipped the UI `8c6a7b6e`, backend half absent) + never sys.exit on missing key.

## sessions + ownership (single-owner, shared tree)
- main() + config_store + agent/voice + set_brain = ONE backend-boot lane (Sven Codex). __main__.py was dirty from Library -> Library commits+vacates it first.
- IPC schema + tauri/ui + Start-gate UI = Frontend (Claude). library/intel + Rust library_cmds + CueSet fields = Library Codex. learn/ + the smoke-failure (462157e7) = Learn Codex.
- The re-rail goals are paste-ready in `SHIP-WIRE-GOALS-RERAIL.md`; Kaan injects them into the loops (the organizer only writes packets).

## doc index (live 2026-06-04 packets)
- `SHIP-MAP-MASTER.md` — the fresh-eye whole-system map (READ FIRST when it lands).
- `WIRE-DRIVE.md` — the wiring program spine + the 4 locked decisions + gate.
- `SHIP-WIRE-GOALS-RERAIL.md` — the STOP protocol + per-session terminating ship-goals + the W3 clarification resolutions.
- `USER-READY-WIRING-EXIT-MAP.md` / `BACKEND-WIRING-EXIT-MAP.md` / `FRONTEND-WIRING-EXIT-MAP.md` — the W1/W2/W3 wire maps.
- `SHIP-READINESS-2026-06-04.md` — the 5-tier ship DoD.
- `ship-final-wf.js` + `SHIP-DRIVE.md` — the ship verification workflow + loop (older, pre-rerail).

## how to organize on wake
Read SHIP-MAP-MASTER.md -> confirm the critical path (fresh-user crash -> voice -> start-gate -> packaging -> Kaan's keystone capture) -> check which re-rail goals the lanes picked up (git) -> surface the single next move to Kaan + any new blocker the map found. Stay read-only; Codex builds; commit packets surgically (pathspec or `git add <exact path>`, never -A). Proxy is DONE server-side; the remaining proxy work is the client default flip (backend-boot lane).
