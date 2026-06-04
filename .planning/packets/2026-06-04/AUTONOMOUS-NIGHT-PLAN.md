# AUTONOMOUS NIGHT PLAN — break the human-in-the-loop QA, ship overnight

**Date:** 2026-06-04 · **Branch:** `ux-redesign-impeccable` · **Author:** Claude (read-only orchestrator)
**Grounded in:** `qa-loop-map/MAP-*.md` (8 substrate maps) + `qa-loop-map/REDTEAM-{closeloop,orchestration}.md`, all file:line-verified this session.

> Goal (Kaan): remove himself from being the by-ear / by-eye QA so 2-3 Codex lanes ship unattended overnight. The loop-breaker is an automated QA harness, not more shippers.

---

## 1. VERDICT (the honest answer)

- **By-EAR loop (Sven prose + grounding + should-speak) — CAN close tonight.** Everything for it exists; the gap is ~1 evening of GLUE + one 30-second Kaan privacy designation.
- **By-EYE loop (vision/UX judge) — CANNOT close tonight.** The vision judge is 0% built (a multi-evening real build). Lane 3 (UX) self-QAs on the existing vitest/Playwright suite + the keyless MOSS→Chatterbox rename, and defers visual judgment to a human morning pass.
- **The keystone "no 3-hour set" blocker is a PHANTOM.** Real long recordings exist: `~/Library/Application Support/vibemix/recordings/20260602-075843` (98 min, **178 real Sven invocations**, 1.9M events.jsonl) and `20260529-150224` (218 min). The replay feeder + judges already exist and ran grounded today.

**The real blocker = the orchestrator GLUE (one verdict file) + a Kaan "this recording is QA-safe" designation. Both small. Everything downstream is REAL.**

---

## 2. WHAT IS ALREADY REAL (do NOT rebuild — verified)

| Capability | Status | Proof |
|---|---|---|
| Recorded-set FEED into the live pipeline (`VIBEMIX_REPLAY_SESSION`) | REAL, wired, proven | `_audio_replay.py:166-186`; `__main__.py:1373,1392,1457`; grounded run `current-source-live-capture-blackhole-20260604-110953/` |
| A long real set on disk | REAL (maps were wrong) | `20260602-075843` 98min/178 inv; `20260529-150224` 218min |
| Sven-prose judge on REAL lines, 5-dim + `should_speak`, exit-code gate | REAL | `respan_sven_heartbeat_judge.py --session --require-quality` (`:73-299`, thresholds `:98-103`) |
| No-key deterministic gate floor | REAL | `--dry-run --describe-bank-census`; `respan_sven_sim.py --gate-only` (9/9 this session) |
| Offline citation-F1 judge | REAL | `replay_harness.py` + `judge.py` |
| Respan provider-cred wall | CLEARED | `sven-strict-gate-20260604` artifact: friend 3.0 / grounded 3.0, gate 10/10 |
| Drive + observe the live app over ws | REAL, live-verified | vibemix-dev MCP `ws_observe`/`ws_trigger`/`sidecar_status` (116 frames/3s) |
| Debrief headless + citation-grounded + cache-replayable | REAL | `--debrief` short-circuits audio; SHA cache |
| Viber keyless proof-of-life | REAL | `auto_crate` (`library_cmds.rs:935`, no login) |

## 3. WHAT IS MISSING (the glue + the 2 real builds)

| Gap | Class | Owner |
|---|---|---|
| ONE orchestrator: capture → all judges → one `vibemix_qa_verdict_v1` JSON (`overall_pass` + gates + routed `next_goal`) | SMALL-WIRE (~1 evening, no new judge logic) | **Claude (GATE-0)** |
| Deterministic launcher (`uv sync` warm + free :8765 + engine-only headless) | SMALL-WIRE | **Claude (GATE-0)** |
| `.mcp.json` committed so worktrees inherit the dev MCP | SMALL-WIRE | **Claude (GATE-0)** |
| Coach-vs-narrate per-turn signal (FALSE-PASS #1 fix) | product change | **Lane 1 (Sven)** |
| Master-mix energy-read receipt (so audio-only replay has something to coach from) | product change | **Lane 1 (Sven)** |
| VISION/UX judge + headless screenshot | REAL-BUILD (0%, not tonight) | deferred |
| boot-health truthfulness (`ws_client.rs:39` ~43s latch vs ~80s uv sync) | SMALL-WIRE | optional (engine-only path sidesteps it) |

---

## 4. THE DANGEROUS FALSE-PASSES (an autonomous loop that lies is worse than none)

1. **FALSE PASS — Sven judged "coach" while structurally a narrator.** On master-only audio replay the eq-move guard needs a controller and the Vibe Judge + scorer abstain two-deck (`MAP-sven` §2), so Sven falls to the "coach the music's direction" branch = narration. The prose judge green-lights it. **Mitigation:** Lane 1 lands the coach-vs-narrate signal (`MAP-sven` #6) + the energy-read receipt (#1) FIRST; the chosen fixture `20260602-075843` HAS real MIDI moves (verified: `[midi:A_low...]` coaching lines present), which lowers this risk for the proof.
2. **FALSE PASS — replay grades downmixed MONO 16k, not the 4-ch deck split** (`recorder.py:251-253`). Deck-attributed citations degrade to "global mix" on replay. Don't assert per-deck grounding from a replay.
3. **FALSE PASS — zero lines judged = vacuous pass.** Enforce a `--min-judged` floor on the LONG set; no-lines is a hard FAIL.
4. **FALSE PASS — Respan 401 swallowed as "0 errors."** The orchestrator MUST propagate every exit code; never `try/except: pass`. Keyless deterministic gate is the floor.
5. **FALSE FAIL — debrief errors on empty `evidence_registry.json`** (legacy sessions). Use a session with a populated registry (`20260602-075843`).
6. **FALSE FAIL — first-boot "VIBEMIX-CORE STOPPED"** uv-sync race. Engine-only headless path + warm `uv sync` sidesteps it.

---

## 5. GATE-0 — build BEFORE any lane (serial, ~1-2h, Claude + one Kaan gate)

The self-QA gate every lane leans on does not exist yet. It is the real serial dependency. Build it first.

- **0a [KAAN, 30s] Designate ONE QA-safe recording.** Recommended: `20260602-075843` (98 min, 178 invocations, populated registry, has real MIDI). This is the one true human gate (privacy: the recordings hold Kaan's session audio).
- **0b [Claude] `scripts/qa/launch_replay.sh`** — `uv sync` warm → free :8765 (`lsof -ti :8765 | xargs kill`) → engine-only headless (`uv run python -m vibemix`) with `VIBEMIX_REPLAY_SESSION` + `VIBEMIX_TTS_ENGINE=off` → poll `sidecar_status()` until `ws_reachable` (~120s budget).
- **0c [Claude] `scripts/eval/qa_loop_run.py` + `vibemix_qa_verdict_v1`** — fan out the existing judges (heartbeat `--require-quality` + `replay_harness` citation-F1 + no-key census floor), merge into one `qa-verdict.json` (`overall_pass` + `gates.*.pass` + routed `next_goal` with worst-evidence rows + a copy-paste `verify` command). Propagate every exit code. Schema pinned by a unit test.
- **0d [Claude] commit `.mcp.json`** (`vibemix-dev` stdio, `--repo-root`) so each worktree inherits drive/observe.

Proof GATE-0 works = run 0c on the designated recording and get a real `qa-verdict.json` with a non-vacuous verdict.

---

## 6. THE 3 LANES (worktree each, NOT a shared tree)

Repo already runs 30+ worktrees. A shared tree guarantees `__main__.py` + `library_cmds.rs` collisions (2 of 3 lanes want each). One worktree per lane → `git commit` absorbs only that lane's files.

```
git worktree add ../qa-lane1-sven   -b qa/lane1-sven
git worktree add ../qa-lane2-engine -b qa/lane2-engine
git worktree add ../qa-lane3-ux     -b qa/lane3-ux
# each: uv sync (warm the race) once; .mcp.json inherited via commit
```

### Lane 1 — SVEN (the soul, #1). Gate: `respan_sven_heartbeat_judge.py --require-quality`
First queue items (order matters — false-pass #1):
1. **Master-mix energy-read receipt** (`MAP-sven` #1): a single-mix citable receipt from `suggestion["transition"]` score/reasons/risks + `render_audio_delta_items(state)`, no A/B deck requirement; new grounded source; new speak-gate key. Files: `runtime/transition_verdict_voice.py` (or new `energy_read_voice.py`), `runtime/coach.py:880-901`, `runtime/speak_gate.py:21`, `state/evidence_registry.py`.
2. **Coach-vs-narrate per-turn signal** (`MAP-sven` #6): log whether each spoken line carried a grounded coaching receipt vs fell to the music-direction branch. This is what lets the judge measure the gap. Files: `runtime/coach.py` near `:1029/1065`.
3. Non-causal master-mix move-direction receipt when `moves` empty (`MAP-sven` #2, `deck_context.py:2688`).
Single-owner lock: `__main__.py:1503-1507` (deck-capture default) — defer or lock.

### Lane 2 — AI / ENGINES (Debrief + Viber). Gate: keyless `auto_crate` + Debrief cache/`--require-quality`
- **Debrief** (best-wired secondary, headless-safe via `--debrief`, GEMINI key present): close session→lesson/profile loop, cite real moments. Files: `debrief/*`.
- **Viber**: keyless `auto_crate` ONLY on the unattended path (the `codex login` curate/chat path can expire at 2am — keep it off the critical path). Read `VIBEMIX_TOOL_EVENTS_FILE` JSONL, never scrape stderr. Files: `library/auto_crate.py`, `intel/move_grade.py`.
Single-owner contention: `__main__.py`, `library_cmds.rs` (shared with Lane 3) — lock.

### Lane 3 — UX (impeccable). Gate: `npm run build && npm test` (~886 vitest) + `grounding-failure.spec.ts`
- **MOSS→Chatterbox rename+reroute (biggest single win, keyless, test-gateable).** The voice-readiness badge keys on dead `model.id === "moss-tts"`; backend emits `chatterbox-voice` → badge silently hidden → user sees ZERO voice status (Kaan's "TTS is not there"). The install button is dead end-to-end (`--install moss` rejected by argparse). Files: `tauri/ui/src/shell/VoiceReadinessBadge.ts:42`, `settings/SettingsDrawer.ts:945`, `wizard/step0-intro.ts:522`, `library/api.ts:124,162,2524-2531`, + re-key the test pins `model-setup.test.ts`/`api.test.ts`/`build.test.ts`. Install fix: `library_cmds.rs:331` remap `moss→chatterbox` (Python already supports `--install chatterbox`).
- Then: voice-status chip inside Learn (reuse `ipc.status.tick.voice`), silent-lesson honesty (~26/38 lessons run "listen" copy over silence).
- Single-owner: `messages.schema.json` (then `npm run codegen:ipc` in the same commit); `library_cmds.rs` (shared w/ Lane 2).
- DEFER: vision judge (no headless screenshot source today).

---

## 7. ORCHESTRATION (Kaan out of the loop, Claude not a blocker)

- **On-disk queues, compaction-proof.** Each lane reads `QUEUE-laneN.md` at the top of every step; checks off into `DONE.log`. A recovered/compacted session resumes from disk, not memory.
- **Done-signal = structured git trailer + reproducible verdict (machine-derived, not agent-asserted):**
  ```
  QA-LANE: lane1-sven
  QA-ITEM: voice-energy-read-master-mix
  QA-VERDICT: .planning/eval-runs/qa-<ts>/qa-verdict.json
  QA-GATE: sven_prose
  QA-PASS: true
  QA-VERIFY: uv run python scripts/eval/respan_sven_heartbeat_judge.py --session <dir> --require-quality
  ```
  `QA-PASS` is trusted ONLY if the referenced verdict exists, its gate matches, and the audit can re-run `QA-VERIFY` and reproduce it. A marker without a reproducible verdict = FAIL. This kills the "tests-green = done" reskin-drift lie.
- **Claude = async, stateless, resumable auditor.** Reads commit markers + verdicts from disk, re-runs `QA-VERIFY`, appends the verdict's `next_goal` to the lane's on-disk queue, maintains `OVERNIGHT-STATUS.md`. No lane waits on a Claude ack. Run on an interval (`/loop` or cron), never a long-lived session.
- **Every gate keyless-degradeable + engine-only headless.** :8765 is held by a running app right now; no GUI-headless path exists. A lane that self-QAs by launching the GUI or calling a live key at 3am stalls. Keyless deterministic gate is the floor; the keyed gate is a bonus when the key is alive.
- **Morning handback = ONE board.** `OVERNIGHT-STATUS.md`: per-lane last SHA, last verdict, gates pass/fail, items done/deferred (with reason), and the merge order for the 3 branches. Kaan wakes to a board + 3 branches to merge, not 3am commit soup.

---

## 8. KAAN-ONLY GATES
1. **Designate the QA-safe recording** (0a) — recommend `20260602-075843`. The one true blocker.
2. **Open the 3 Codex sessions** and paste the lane goals (Claude delivers paste-ready goals).
3. **Morning: merge the 3 lane branches** (`__main__.py` / `library_cmds.rs` conflicts resolved once, awake).
4. (Optional) record a fresh rig set if you want richer per-deck/MIDI grounding — NOT required (existing fixture has MIDI).
5. (Still open) rotate the funded key if it hit chat.

---

## 9. TONIGHT'S SEQUENCE
1. Claude: build GATE-0 (0b launcher, 0c orchestrator+schema, 0d `.mcp.json`) + prove the by-ear loop on `20260602-075843` (heartbeat `--require-quality` → real verdict).
2. Claude: write the 3 paste-ready lane goals + the on-disk `QUEUE-laneN.md` files.
3. Kaan: designate the recording (if different from the recommended) + open 3 Codex sessions + paste goals.
4. Lanes run in worktrees, self-QA via GATE-0, commit with the trailer.
5. Claude async-audits on an interval, replenishes queues, maintains `OVERNIGHT-STATUS.md`.
6. Kaan wakes to the board + 3 branches to merge.
