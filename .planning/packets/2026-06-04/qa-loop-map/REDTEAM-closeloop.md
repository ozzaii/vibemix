# RED-TEAM — Can the autonomous QA loop CLOSE tonight?

**Question:** Can the autonomous QA loop actually close tonight — Kaan fully removed
from by-ear / by-eye QA? **Brutally honest, cross-synthesized across all 8 substrate
maps, with independent on-disk verification.**

**Branch:** `ux-redesign-impeccable` · **Date:** 2026-06-04 · READ-ONLY (this doc only).

---

## VERDICT (one line)

**PARTIAL — the SVEN-PROSE loop (the soul, Kaan's #1) can close tonight; the BY-EYE
(UX/visual) loop CANNOT.** "Fully removed from by-ear" = achievable tonight. "Fully
removed from by-EYE" = aspirational (the vision judge does not exist, 0%).

So the honest answer to "fully removed from by-ear AND by-eye" is **NO for tonight**,
**YES-for-by-ear / NO-for-by-eye** if you split the claim — which you must, because
they are two different loops with two different blockers.

---

## THE REAL CRITICAL-PATH BLOCKER (not the easy ones)

The maps each nominate a different blocker. Cross-synthesized, here is the truth:

- MAP-respan + MAP-audio-replay + MAP-judge all name **"no 3-hour set on disk"** as
  THE keystone blocker. **This is WRONG — I verified it false.** A **218.5-minute
  (3.6h)** recording exists at `~/Library/Application Support/vibemix/recordings/20260529-150224/`
  (419 MB `input.wav` ÷ 32 KB/s @16k mono int16), and a **98.4-minute** one at
  `20260602-075843/` with **178 invocations** (178 real Sven lines) + a 1.9 MB
  `events.jsonl`. The maps measured "longest ~8 min / ~117 s" — that was a stale or
  mis-scoped measurement. **The corpus-gap blocker is a phantom.** The fuel exists.

- The REAL blocker is **NONE of the data/feed/judge items — those are all built.** It
  is the **GLUE + the OWNER-GATE**, in this exact order:

  1. **No orchestrator exists.** Verified: `scripts/eval/qa_loop_run.py`,
     `run_overnight_qa.py` — both absent. The three judges
     (`replay_live_runner.py`, `respan_sven_heartbeat_judge.py`, `replay_harness.py`)
     are **three separate CLIs**. Nothing fans capture→judge→one verdict→next-goal.
     MAP-respan §6.2, MAP-judge §6 ("ONE entrypoint … MISSING"), MAP-judge §9.1 all
     confirm. This is a ~1-evening **wire**, not a build.

  2. **The privacy gate on the fuel.** The 503 recordings live under the
     CLAUDE.md HARD-RULE privacy path. They are co-host recordings (not Hermes/OZ
     chat), so they are *probably* QA-safe — but **Kaan must explicitly designate a
     recording as QA-safe** before an autonomous agent reads its `input.wav` /
     `events.jsonl` / invocation transcripts. MAP-respan §4 flags this exactly:
     *"Kaan must designate which recordings are QA-safe fixtures."* This is a
     30-second human decision but it is a **hard gate** — without it the loop cannot
     legitimately touch its own fuel. **This is the one true blocker that is not
     just engineering.**

**Net real blocker = the orchestrator script (≈1 evening of wiring) + a one-line Kaan
"this recording is QA-safe" designation.** Everything downstream of those two is REAL.

---

## WHAT IS ACTUALLY REAL (verified, not taken from maps)

| Component | Status | Proof |
|---|---|---|
| Recorded-set FEED into the live pipeline (`VIBEMIX_REPLAY_SESSION`) | **REAL** | `_audio_replay.py:34,39,186`; wired `__main__.py:1373,1392,1457`; already produced a grounded run 2026-06-04 |
| A long (≈3h) real recorded set on disk | **REAL** (maps say absent — they're wrong) | `20260529-150224/input.wav` = 218.5 min; `20260602-075843` = 98.4 min, **178 invocations** |
| Sven-prose judge on REAL recorded lines, 5-dim + should_speak, exit-code gate | **REAL** | `respan_sven_heartbeat_judge.py` `--session/--require-quality/--dry-run` (I ran `--help`, flags present) |
| No-key deterministic gate replay (no network) | **REAL** | heartbeat `--dry-run` + `--describe-bank-census`; sim `--gate-only` ran 9/9 this session per MAP-respan |
| Respan provider-cred wall | **CLEARED** | `sven-strict-gate-20260604` artifact, friend 3.0/grounded 3.0, gate 10/10 |
| Offline citation-F1 judge | **REAL** | `replay_harness.py` + `judge.py` |
| Drive/observe the live app over ws (`ws_observe`/`ws_trigger`) | **REAL, live-verified** | vibemix-dev MCP, 116 frames/3s (MAP-drive-app §1) |
| Debrief is headless + citation-grounded + cache-replayable | **REAL** | `--debrief` short-circuits audio; SHA cache; stripper gate (MAP-debrief §1,§8) |
| Viber keyless deterministic proof-of-life (`auto_crate`) | **REAL** | `library_cmds.rs:935`, no `--backend`, no login (MAP-viber §1) |

## WHAT IS MISSING / ASPIRATIONAL (the gaps that actually bite)

| Gap | Status | Where it bites |
|---|---|---|
| **ONE orchestrator** (capture → all judges → one `qa-verdict.json` → next-goal) | **MISSING** (verified absent) | The loop cannot "close" without it — it's literally the closing seam |
| **VISION / UX judge** (screenshot → legible / voice-status-shown / Learn-clear) | **MISSING, 0%** | The entire by-EYE half. No screenshot-judge anywhere in repo |
| **Headless screenshot capture** | **MISSING** | No in-app capture cmd; needs a display + a Playwright/screencapture driver (MAP-drive-app §5) |
| **Deterministic one-command launcher** + uv-race fix | **MISSING** | `cargo tauri dev` first-boot false "VIBEMIX-CORE STOPPED" at ~43 s vs ~80 s uv sync (MAP-drive-app §3) |
| **Time-warp replay** (3h = 3h wall clock) | **ABSENT** | Overnight = ONE 3h pass, no fast iteration (`_audio_replay.py:186` strict realtime) |
| **judge→next-Codex-goal contract** (`vibemix_qa_verdict_v1`) | **MISSING** | Loop measures but nothing turns a fail into the next lane's goal |

---

## WHERE IT WILL SILENTLY GIVE A FALSE PASS / FALSE FAIL (the dangerous part)

This is the section that matters most for a red-team. An autonomous loop that lies is
worse than no loop. Concrete failure modes, each cross-derived from the maps:

1. **FALSE PASS — Sven judged "grounded coach" while structurally a narrator.**
   MAP-sven is unambiguous: on a **master-only / no-controller** rig (which is EXACTLY
   what an audio-only 3h replay feeds — MAP-sven §0, §2), the only coaching signal
   (`_licensed_move_effect`) needs a connected MIDI controller, and the Vibe Judge +
   10-signal scorer **both abstain by construction** (`coach.py:474`,
   `deck_context.py:2880-2914`). So Sven falls to the `recent_moves[8s] is NONE` →
   "coach the music's direction" branch (`matrix.py:403`) = narration in coach clothing.
   The heartbeat judge scores PROSE. A line like "the lows just opened up, ride this
   energy" reads as coaching to an LLM judge and **passes the friend/voice dims** even
   though it is ungrounded narration. **The judge cannot see that no coaching evidence
   was in the prompt.** → A clean dim-mean pass that hides the #1 product gap.
   *Mitigation that does NOT exist yet:* MAP-sven §4.6 — emit a per-turn
   "carried-grounded-coaching-receipt vs fell-to-music-direction" signal the judge can
   read. Until that exists, **the prose judge will green-light narration.**

2. **FALSE PASS — replay grades the wrong audio.** The replayed feed is **downmixed
   MONO 16 kHz** (MAP-drive-app §4 caveat B; `recorder.py:251-253`), NOT the live
   4-channel deck-split. Any deck-attributed citation grounding is degraded to "global
   mix" on replay. A judge asserting "deck-attributed citations resolve" will pass on
   replay and **fail on the real multichannel rig** — the loop validates a path the
   real product does not run.

3. **FALSE PASS — `should_NOT_have_spoken == 0` on a short/quiet window.** The one
   captured realtime run showed LISTENING with **empty `transcript_delta`** in a 20 s
   window (MAP-audio-replay §PROOF, Gap 4). If the harness runs a short window or the
   speak-gate silences everything, the judge sees **zero lines**, `judged < min`, and
   either errors (honest) OR — if `--min-judged` is set too low — reports a vacuous
   "all clear." **No lines judged is not a pass; it must be a hard FAIL.** This is a
   trivially-tripped false pass if the orchestrator doesn't enforce a min-judged floor
   on the LONG set.

4. **FALSE PASS — Respan judge 401s silently treated as "no failures."** MAP-judge §10
   + MAP-respan §10: the judge needs `RESPAN_API_KEY` + a provider cred or it 401s.
   `RESPAN_API_KEY` is **absent from the shell env** (verified) — it's in `.env`, so the
   script must load it. If the orchestrator swallows a 401 as "0 judge errors," it
   reports PASS on zero actual judgments. The gate logic counts judge errors
   (`heartbeat:391-392`) — but **only if the orchestrator propagates the exit code.**
   A naive `try/except: pass` fan-out is a guaranteed false pass.

5. **FALSE FAIL — debrief errors out on empty evidence snapshot.** MAP-debrief §6.2:
   if `evidence_registry.json` is missing/empty (legacy sessions, or the 3.6h
   `20260529-150224` which predates current registry writing — its events.jsonl is only
   21 KB with 6 invocations), drills fail all-or-nothing → whole debrief ERRORs even
   though chapters + TLDR are fine. A QA gate that treats "debrief errored" as FAIL will
   **fail a session that is actually only missing optional drill evidence.** Pick a
   session with a populated registry (the 98-min `20260602-075843`, 178 invocations) or
   the gate lies.

6. **FALSE FAIL / NOISE — first-boot "VIBEMIX-CORE STOPPED" race.** MAP-drive-app §3:
   if the orchestrator launches via `cargo tauri dev` without a warm `uv sync`, the ws
   client latches "unreachable" at ~43 s while uv is still syncing (~80 s), surfacing a
   false crash. A health-check that reads that banner = false FAIL on a healthy boot.
   (Engine-only path `uv run python -m vibemix` sidesteps this — use it.)

7. **SILENT NO-OP — the Viber tool tape.** MAP-viber §3: the `[viber-tool]` tape
   depends on env crossing parent→Codex→MCP child; if Codex strips args, it silently
   no-ops (best-effort by contract). A judge asserting "agent fired grounded tools" sees
   an empty tape and can't tell "agent didn't ground" from "tape didn't propagate." Read
   the `VIBEMIX_TOOL_EVENTS_FILE` JSONL directly (MAP-viber §6.2), never scrape stderr.

8. **STRUCTURAL — UX/by-eye gives NO signal at all.** There is no vision judge. The
   single worst UX bug (MAP-ux-learn Part 1: the voice-readiness badge keys on dead id
   `moss-tts` while backend emits `chatterbox-voice` → badge **silently hidden** → user
   sees zero voice status) is **invisible to every judge that exists tonight.** The loop
   will report PASS on a product whose voice-status UI is dead. By-eye QA is not "weak"
   tonight — it is **absent**, so any "UX is fine" conclusion is unfounded.

---

## THE MINIMAL QA HARNESS THAT REMOVES THE HUMAN (by-EAR loop, achievable tonight)

Smallest trustworthy {drive-app, feeder, capture, judge} that yields no-human pass/fail
for the SVEN-PROSE + grounding axes (the soul). Sequenced, dependency-ordered:

```
STEP 0 [OWNER-GATE, ~30s]  Kaan designates ONE QA-safe recording.
  Recommend: 20260602-075843 (98.4 min, 178 invocations, populated events.jsonl).
  → unblocks the agent reading its fuel without violating the privacy HARD-RULE.

STEP 1 [drive-app, REAL]   Engine-only launch (NO Tauri, NO display, NO uv-race):
  uv sync  (warm, kills the §3 race)
  lsof -ti :8765 | xargs kill  (no auto-free exists)
  VIBEMIX_REPLAY_SESSION=<dir> VIBEMIX_TTS_ENGINE=off uv run python -m vibemix
  → real state loop + event_detector + Sven on the recorded audio, no human.
  (replay_live_runner.py already does most of this — reuse LiveReplayConfig.)

STEP 2 [capture, REAL]     Capture transcript + telemetry while it replays:
  - reuse the existing ws-capturer (the ws_capture_summary.json schema) for transcript_delta
  - events.jsonl + invocations/*/{meta,response,prompt} are written automatically
  → for the DESIGNATED session, judge its EXISTING invocations directly (no realtime needed).

STEP 3 [judge, REAL]       Score the real lines, exit-code gate:
  RESPAN_API_KEY=<from .env> uv run python scripts/eval/respan_sven_heartbeat_judge.py \
    --session <dir> --events ALL --require-quality --min-judged <N>
  + offline floor (no key): --dry-run --describe-bank-census
  + citation-F1: replay_harness.py over the corpus (after staging input.wav)

STEP 4 [GLUE — the missing seam, NEEDS-SMALL-WIRE]
  scripts/eval/qa_loop_run.py (NEW, ~1 evening): fan out STEP 3 judges,
  merge to one vibemix_qa_verdict_v1 (overall_pass + gates.*.pass + next_goal),
  PROPAGATE every exit code (no swallowed 401s), enforce min-judged floor,
  emit qa-verdict.json the next Codex lane reads.
```

### Component ledger (REAL / SMALL-WIRE / REAL-BUILD)

| Component | Verdict | Note |
|---|---|---|
| recorded-set feeder (`VIBEMIX_REPLAY_SESSION`) | **REAL** | wired + proven |
| 3h / 98-min fuel on disk | **REAL** | exists (maps wrong); just designate |
| engine-only headless launch | **REAL** | `uv run python -m vibemix` |
| transcript+telemetry capture | **REAL** | ws-capturer + invocations/events.jsonl |
| Sven-prose 5-dim judge + exit gate | **REAL** | `respan_sven_heartbeat_judge.py` |
| no-key deterministic floor | **REAL** | `--dry-run --describe-bank-census` |
| citation-F1 offline judge | **REAL** | `replay_harness.py` + `judge.py` |
| **orchestrator (fan-out→merge→verdict→goal)** | **NEEDS-SMALL-WIRE** | ~1 evening, no new judge logic |
| coach-vs-narrate per-turn signal (false-pass #1 fix) | **NEEDS-SMALL-WIRE** | MAP-sven §4.6; without it the judge green-lights narration |
| warm-launcher + uv-race fix | **NEEDS-SMALL-WIRE** | or just use engine-only path |
| **VISION / UX judge + screenshot driver** | **NEEDS-REAL-BUILD** | 0% today; the entire by-EYE half |
| time-warp replay | **NEEDS-REAL-BUILD** (risky) | desyncs detection windows; realtime is safe |

---

## ACHIEVABLE TONIGHT vs ASPIRATIONAL — plainly

**ACHIEVABLE TONIGHT (by-ear, the soul):**
- Kaan designates a QA-safe recording (30 s).
- Run the heartbeat judge `--require-quality` over its 178 real invocations → a no-human
  exit-code pass/fail on friend/grounded/earned/move/voice + should_speak.
- Add the citation-F1 + no-key gate-census as supporting signals.
- Write the ~1-evening `qa_loop_run.py` to merge them into one `qa-verdict.json`.
- This **removes Kaan from by-EAR QA tonight** — with the caveat that it judges PROSE,
  so it cannot catch false-pass #1 (narration-as-coaching) until the coach-vs-narrate
  signal is wired.

**ASPIRATIONAL (not tonight):**
- **By-EYE / UX / visual QA.** The vision judge is 0%, the screenshot driver is missing,
  and the worst UX bug (hidden voice badge) is invisible to every existing judge. "Kaan
  removed from by-EYE QA" is a **multi-evening real build**, not tonight.
- Fast iteration (time-warp) — overnight is ONE 3h pass; no quick inner loop.
- Live-online Sven eval (Lane B) — needs product instrumentation that doesn't exist +
  a privacy yes.
- Agent-ops watching the coding loop — would NOT have caught the reskin-drift anyway
  (category mismatch, MAP-respan §2c).

---

## BOTTOM LINE FOR THE ORCHESTRATOR

Close the **by-ear** loop tonight on the prose+grounding axes (real, ~1 evening of glue
+ a Kaan designation). Do **not** claim the by-eye loop closed — it's unbuilt. And do
**not** trust a green prose verdict as "Sven coaches" until the coach-vs-narrate signal
exists, or the loop will confidently certify a narrator as a coach (false-pass #1, the
exact failure the whole mission is trying to kill).
