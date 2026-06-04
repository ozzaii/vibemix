# MAP — the QA JUDGE (scores a captured session with no human)

**Scope:** the "score it, no human" half of the overnight autonomous QA loop.
**Read & verified:** `scripts/eval/respan_sven_sim.py`, `scripts/eval/respan_sven_heartbeat_judge.py`,
`scripts/eval/judge.py`, `scripts/eval/replay_harness.py`, `scripts/eval/replay_live_runner.py`,
`src/vibemix/platform/_audio_replay.py`, `src/vibemix/audio/recorder.py` (capture schema),
`src/vibemix/agent/dj_cohost.py` (invocations dump), `src/vibemix/ui_bus/messages.py`
(`transcript_delta` / `TranscriptLine`), `src/vibemix/intel/transition_judge.py`,
`src/vibemix/intel/judge_voice.py`, `.claude/skills/vibemix-grounding-review/SKILL.md`,
plus a REAL on-disk capture (`~/Library/Application Support/vibemix/recordings/20260529-093254/`).

---

## TL;DR verdict

The headline mission question — *"Can `respan_sven_sim.py` score a REAL capture instead of a
simulation?"* — has a **clean answer: NO, by design — but its sibling already CAN.**

- `respan_sven_sim.py` is a **simulator** (authored synthetic scenarios → generate → judge). It
  does NOT read any capture (`scripts/eval/respan_sven_sim.py:104-199` — `SCENARIOS` is a
  hardcoded list of dicts; there is no `--session` / capture-reading code path at all).
- The **real-capture judge ALREADY EXISTS** and is wired today: `respan_sven_heartbeat_judge.py`
  takes `--session <recordings dir>`, reads the exact `invocations/*/{meta.json,response.txt,prompt.txt}`
  schema the live app writes, and runs the SAME 5-dim blind judge on Sven's ACTUAL spoken lines
  (`respan_sven_heartbeat_judge.py:196-232` load + `:253-299` judge). It even emits the
  decision-grade number Kaan cares about: `should_NOT_have_spoken` (fraction of real lines that
  should have been silence — `:495-504`).
- **REAL (works today):** a live-line judge over a real recorded session, with a machine pass/fail
  gate (`--require-quality`).
- **ASPIRATIONAL / NOT BUILT:** (a) a single "score this whole captured session" entrypoint that the
  overnight loop calls; (b) any **VISION / UX judge** (screenshot → "does this screen tell a new
  user what to do; is voice/TTS status visible; is Learn legible") — this does not exist anywhere
  in the repo; (c) a **judge-output-as-next-Codex-goal** contract.

**Net:** the Sven-prose judge is ~80% there and is NOT a blocker for tonight. The VISION/UX judge
is 0% there and is the real gap. The glue (one runner that feeds capture → judge → goal JSON) is
the missing ~20%.

---

## 1. What `respan_sven_sim.py` actually is (REAL: simulator, not capture-scorer)

The module docstring is explicit (`respan_sven_sim.py:3-21`):

> "Sven SIMULATION engine — controlled deck-move scenarios, no live set needed… synthetic
> scenario → REAL `decide_speak_gate` → REAL coach persona → model (Respan gateway) → 5-dim
> Respan judge."

Flow per scenario (`main()` `:618-689`):
1. Build a `MusicState` fixture from the scenario dict (`_state_for_scenario` `:202-209`).
2. Run the REAL speak-gate (`decide_speak_gate(ev)` `:624`).
3. If gate says speak: build the REAL coach persona (`build_system_instruction` `:591-596`),
   call the model via the Respan gateway (`_chat` `:298-306`), optionally run the live
   `CitationLinter` (`_live_linter_checked_line` `:354-399`), then judge the line (`_judge` `:309-327`).

**Why it's a simulator and not a capture-scorer:** the evidence text is **authored per scenario**
(`SCENARIOS` `:121-182`, e.g. `_HEAR = "hearing[rms=0.16 sub=0.62 …]"` `:106`). The docstring's own
validity boundary (`:18-21`): *"the evidence text is authored… there is no audio Part — so this
tests the GATE + PERSONA + move-coaching LOGIC… NOT audio-vibe grounding. For audio grounding,
judge real recorded lines (see respan_sven_heartbeat_judge.py)."*

So the sim is the **prompt/gate regression instrument** (the `--strict-sven-gate` standing gate,
`:534-542`), NOT the live-capture QA scorer. It cannot, and was never meant to, read an
`events.jsonl` + transcript.

The two are already linked: `respan_sven_sim.py` can shell out to the heartbeat judge via
`--heartbeat-session <dir>` (`_run_heartbeat_judge` `:252-281`, dispatched `:731-738`). That is the
existing seam where "sim + real capture" run together.

---

## 2. The real-capture judge that DOES exist — `respan_sven_heartbeat_judge.py` (REAL)

This is the engine the mission actually wants. It is built, wired, and runs on the live model.

### Input it reads = exactly what the live app writes
`load_rows()` (`:196-232`) walks `session/invocations/*/`, requiring `meta.json` + `response.txt`,
optionally reading `prompt.txt` for the real evidence bundle. Skips already-silent invocations
(empty `response.txt` → counted as `silent`, `:213-214`) — i.e. it judges only what Sven actually
SAID.

**Verified against a real capture on disk** (`~/Library/Application Support/vibemix/recordings/20260529-093254/invocations/0001_093304_HEARTBEAT/`):
- files present: `meta.json`, `response.txt` (99 chars), `prompt.txt`, `audio.wav`.
- `meta.json` keys: `event, ts, invoke_n, audible, deck, track, track_confidence, phase, rms, bpm,
  audio_bytes, audio_seconds, diet, llm_latency_s, llm_error, response_chars, suppression,
  slop_matches, citation_lint_valid, citation_lint_reason, citation_lint_missing, citation_action,
  head_yielded` — an exact match for the writer at `dj_cohost.py:4169-4205`.
- `prompt.txt` line 1 carries the real evidence bundle (`hearing[…] | track=… | deck=… | set_time=… |
  recent_moves[8s]: …`) — the judge parses this so a line citing a genuine `recent_moves` entry is
  graded grounded, not fabricated (`evidence_digest` `:156-193`, regexes `:150-153`).

### Dimensions it scores (the 5 product dims + a verdict)
`JUDGE_SYSTEM` (`:73-88`) + `DIMS` (`:90-96`). 0–3 each:
- `friend_not_narrator` (the friend dim — coach vs describe-bank)
- `grounded_not_fabricated` (the grounded dim — cited real evidence)
- `earned_not_constant` (the earned dim — worth interrupting for)
- `move_specific_not_spectrum` (the move dim — actionable next step)
- `voice_no_slop` (the voice dim — real DJ friend, not AI slop)
- **`should_speak` (true/false)** — the bench's structural blind spot; "should Sven have spoken at
  all, or stayed silent?" (`:84-85`). This is the highest-value signal for the #1 voice failure.

These map 1:1 onto Kaan's named judge axes (friend / grounded / earned / move / voice). The same
rubric is duplicated verbatim in `respan_sven_sim.py:74-85` (`JUDGE_SYSTEM`) — so sim and capture-
judge already share one rubric.

### Pass/fail output contract (REAL, machine-gradeable)
Printed report JSON (`:496-514`): `{session, events, judged, errors, dim_means{5 dims},
should_NOT_have_spoken, should_NOT_have_spoken_pct, worst_lines[8], quality{…}}`.

The gate is `--require-quality` (`:403-410`, `:518-525`). `quality_failures()` (`:365-393`) FAILs
(exit 1) unless:
- `friend_not_narrator >= 2.0`, `earned_not_constant >= 2.0`, `voice_no_slop >= 2.0`,
  `grounded_not_fabricated >= 2.4` (`QUALITY_MEAN_THRESHOLDS` `:98-103`)
- `judged >= --min-judged`, zero judge errors, and **`should_NOT_have_spoken == 0`** (`:391-392`).

This is a clean, no-human, exit-code pass/fail — exactly what an overnight loop needs.

### A deterministic, no-network pre-filter also exists
`describe_bank_census()` (`:112-143`) replays each recorded event type through the REAL
`decide_speak_gate` (`runtime/speak_gate.py`) and reports which lines TODAY's gate would have
silenced — `silenced_by_describe_bank_census` / `silenced_by_event`. Caveat baked in (`:106-109`):
it does NOT reconstruct old `event.extra`, so it is a no-payload census, not a full gate replay.
Useful as a cheap, offline, deterministic "would the current gate fix this?" signal with `--dry-run`.

---

## 3. The OTHER judge already wired: `replay_harness.py` + `judge.py` (REAL, offline, deterministic)

There is a second, fully-offline judge spine that is easy to miss:

- `replay_harness.py` (`:1-39`) walks a corpus of session dirs, loads each `input.wav` into a real
  `AudioBuffer` via `fill_from_wav`, drives the REAL runtime stack (EvidenceRegistry + EventDetector
  + CitationLinter — **not mocks**) at a 1Hz manual tick, and renders a scorecard. Offline-only by
  invariant (no sounddevice — `:30-32`). Exit 0 all-pass / 1 any-below-threshold (`:25-27`).
- `judge.py` (`:1-23`) is the 2-judge cross-check: Gemini-3-Pro 6-axis JSON
  (`groundedness, timing, substance, tone, relevance, brevity` — `:47-53`) + Gemini-3-Flash binary
  cross-check, aggregated `min(pro_f1, flash_f1)` to kill self-bias collusion (P42, `:5-15`).

**Note the axis mismatch:** `judge.py` uses a DIFFERENT 6-axis rubric (Pro/Flash, citation-F1
oriented) than the 5-dim Sven rubric in the two Respan judges. The Respan 5-dim rubric is the one
Kaan's mission names (friend/grounded/earned/move/voice). For the overnight loop, **standardize on
the Respan 5-dim rubric for Sven prose**; `replay_harness/judge.py` is the citation-grounding F1
gate (a different, complementary measurement — keep it, don't conflate).

---

## 4. The intel "judges" are a DIFFERENT thing (REAL, but not the QA judge)

`intel/transition_judge.py` and `intel/judge_voice.py` are NOT QA judges. They are the **runtime
Vibe Judge** — a deterministic move-quality engine that grades a live transition (harmonic clash,
bass collision) and abstains when it can't measure (`transition_judge.py:45-85`). It produces a
`TransitionVerdict` that gets VOICED to the DJ (`judge_voice.py:32-66`) and logged to `events.jsonl`
as `transition_judged` (`transition_judge.py:94-125`).

Relevance to QA: the Vibe Judge's `events.jsonl` records (`verdict_state`, `score`, `confidence`,
`risk_flags`, `abstain_reason`) are **capture telemetry the QA judge can READ** to check grounding
("did Sven voice a transition the Judge actually graded?"). They are an INPUT to QA, not the QA
judge itself. Do not wire these as the prose scorer.

---

## 5. How a captured session reaches the judge — the capture side (REAL but real-time)

The mission wants: launch the app → feed a recorded 3-hour set → capture utterances + telemetry +
screenshots. Status of each leg:

### Audio feed: REAL, but REAL-TIME (no time-warp) — this is the keystone constraint
`VIBEMIX_REPLAY_SESSION=<recorded session dir>` makes the live app replay that session's `input.wav`
through the SAME capture callback (`_audio_replay.py:30-44`, `ReplayAudioBackend` `:65-118`,
`ReplayCaptureStream._run` `:166-186`). MIDI (`midi.jsonl`) and nowplaying (`nowplaying.jsonl`) are
replayed too (`:189-198` + `__main__.py:1373-1394`).

**Hard limit:** playback is wall-clock real-time — `time.sleep(block.shape[0] / sample_rate)`
(`_audio_replay.py:186`). A 3-hour set takes **3 hours** to replay. `replay_live_runner.py` confirms
the intent and the limit in its docstring (`:9-11`): *"It does not judge Sven's prose and it does
not time-warp… prove the real app can hear a replayed set without physical audio hardware."*

**Also:** replay reads `input.wav` FROM an already-recorded session dir. To feed an arbitrary
3-hour DJ set you must first stage it as `<dir>/input.wav` (16kHz mono int16 — the format
`recorder.py:250-253` writes). There is no "ingest arbitrary WAV" flag; staging is trivial (drop a
correctly-formatted WAV as `input.wav`) but is a manual/scripted step today.

### Utterance + telemetry capture: REAL
The live app already writes everything the judge needs while replaying:
- `invocations/*/{meta.json,response.txt,prompt.txt,audio.wav}` (`dj_cohost.py:2718-2733`, `:4165-4210`)
- `events.jsonl` (`recorder.py:397-428`) + `session.json` (`:461-537`) + `evidence_registry.json`
  (`:549-567`) + `trace.jsonl` (when SessionTracer attached, `:211-216`).
- Live transcript is on the ws bus as `transcript_delta: tuple[TranscriptLine,…]`
  (`ui_bus/messages.py:321`, `TranscriptLine{role, text, ts}` `:293-297`), folded into
  `SessionSnapshotPayload` (`:314-327`, which also carries `grounded: bool`, `cohost_status`,
  `latency_ms`, `claim_policy`). So a UX/vision judge can read grounded/status from the wire, not
  just from disk.

### Screenshot capture: PARTIAL (machinery exists, not wired to a judge)
Playwright is a dev dep (`tauri/ui/package.json` `@playwright/test ^1.50.0`, `playwright ^1.50.0`),
with `.pw.ts` browser tests and a `test:e2e:visual` config (macbook playwright config). So the
ability to launch the UI and `screenshot()` exists. **But nothing captures app screenshots into a
QA artifact, and nothing judges them.** Confirmed: zero matches for a screenshot/vision JUDGE
anywhere under `scripts/` or `tauri/ui/tests/` (grep for `vision|take_screenshot.*judge|image_url`
returns nothing relevant).

---

## 6. PRECISE GAP TO A "LIVE-CAPTURE JUDGE" (the punch list)

What is REAL vs what must be built/wired:

| Need | Status | Evidence |
|---|---|---|
| 5-dim Sven prose judge on REAL recorded lines | **REAL** | `respan_sven_heartbeat_judge.py:73-299` |
| friend/grounded/earned/move/voice axes | **REAL** | `:90-96` |
| `should_speak` (silence-should-have-won) verdict | **REAL** | `:84-85`, `:495-504` |
| machine pass/fail exit code | **REAL** | `--require-quality` `:518-525`, thresholds `:98-103` |
| deterministic no-network gate pre-filter | **REAL** | `describe_bank_census` `:112-143` |
| offline citation-grounding F1 judge | **REAL** | `replay_harness.py` + `judge.py` |
| feed a recorded set into the live app | **REAL (real-time, no warp)** | `_audio_replay.py:166-186` |
| capture utterances+telemetry while replaying | **REAL** | `dj_cohost.py:4165-4210`, `recorder.py` |
| **ONE entrypoint: capture-dir → all judges → one verdict JSON** | **MISSING** | sim/heartbeat/harness are 3 separate CLIs; `replay_live_runner.py` does NOT judge prose (`:9`) |
| **VISION/UX judge (screenshot → legibility/status/Learn)** | **MISSING (0%)** | no screenshot-judge anywhere |
| **judge-output → next-Codex-goal contract** | **MISSING** | no consumer turns a failure into a goal increment |
| time-warp / faster-than-real-time replay | **MISSING** | `time.sleep` real-time `:186` (3h = 3h) |
| arbitrary-WAV ingest (no pre-staged session dir) | **MISSING (trivial)** | replay reads `<dir>/input.wav` only |

The single biggest gap is the **VISION/UX judge** — it does not exist at all, and UX is the
weakest product layer (Learn illegibility, invisible TTS status). Everything for the SVEN prose
judge already exists; it needs an overnight wrapper, not invention.

---

## 7. HOW TO ADD A VISION / UX JUDGE (the new build)

This is the genuinely new engine. Mirror the heartbeat judge's shape (blind judge + Respan/Gemini
gateway + 0–3 dims + exit-code gate), but feed an IMAGE instead of a text line.

**7a. Screenshot capture (reuse existing machinery).** Add a Playwright script under `scripts/e2e/`
(pattern already used by `tauri/ui/tests/.../*.pw.ts` + `test:e2e:visual`) that:
- launches the dev UI (or the packaged app), drives it to each target surface, and writes PNGs to
  `<capture>/screens/{first_run_empty, session_idle, session_active, learn_open, settings}.png`.
- Optionally pairs each PNG with the live `SessionSnapshotPayload` JSON from the ws bus
  (`ui_bus/messages.py:314-327`) so the judge can cross-check what the screen CLAIMS (e.g.
  `cohost_status`, `grounded`, voice/TTS status) against what it SHOWS.

**7b. The vision judge** — new `scripts/eval/respan_ux_vision_judge.py`. Use a multimodal model
through the same gateway pattern (`_post` pin to `RESPAN_BASE`, `heartbeat_judge.py:235-250`); the
google-genai / Gemini vision path takes an image part. Score 0–3 per dim (positive framing, per the
house prompt philosophy — describe the TARGET, never NOT-X):

- `new_user_knows_what_to_do`: a first-time user can name the single next action from this screen
  alone. (0=blank/ambiguous; 3=one obvious next step.)
- `voice_tts_status_legible`: voice/TTS state (muted / local-MOSS-ready / speaking / unavailable)
  is visible and unambiguous. (Directly targets the named "TTS/voice status not shown" defect.)
- `learn_legible`: on the Learn surface, the current lesson + the one action it asks for are
  readable without guessing. (Targets "you open Learn and cannot tell what to do".)
- `grounding_honest`: the screen does NOT show a fake fault at idle (Invariant #5, `grounding-failure.spec.ts`)
  and does not claim activity it isn't doing. (Cross-checked against the snapshot `grounded`/`cohost_status`.)
- `visual_no_slop`: the surface reads as deliberate craft, not generic AI-app filler.

Output (mirror heartbeat shape): per-screen `{dims…, blocking_issue: str|null, why: "<=12 words"}`
+ rollup `{dim_means, screens_failing, worst_screens}`. Gate `--require-quality`: e.g.
`new_user_knows_what_to_do >= 2`, `voice_tts_status_legible >= 2`, `learn_legible >= 2`,
`grounding_honest == 3` (idle-fault is a hard zero), exit 1 on any miss.

**7c. Anti-self-grading guard.** The same model wrote neither the screen nor (ideally) the rubric;
keep the judge blind (image + minimal context, NO design-spec leakage) the way the prose judge
hides the persona (`heartbeat_judge.py:20-22`).

---

## 8. JUDGE OUTPUT THAT FEEDS THE NEXT CODEX GOAL (the new contract)

Define ONE machine-readable verdict file that the overnight orchestrator writes and the next Codex
lane reads. Proposed `<capture>/qa-verdict.json`:

```jsonc
{
  "schema": "vibemix_qa_verdict_v1",
  "session_dir": ".../recordings/20260604-…",
  "overall_pass": false,
  "gates": {
    "sven_prose":   {"pass": false, "dim_means": {"friend_not_narrator": 1.4, "grounded_not_fabricated": 2.5, "earned_not_constant": 1.8, "move_specific_not_spectrum": 1.9, "voice_no_slop": 2.1}, "should_NOT_have_spoken": 6, "judged": 41},
    "citation_f1":  {"pass": true,  "f1": 0.91},
    "ux_vision":    {"pass": false, "dim_means": {"new_user_knows_what_to_do": 1.0, "voice_tts_status_legible": 0.0, "learn_legible": 1.0, "grounding_honest": 3.0, "visual_no_slop": 2.0}, "screens_failing": ["learn_open", "session_idle"]}
  },
  "next_goal": {
    "lane": "sven",                      // sven | frontend | learn | engine | organism (Kaan's 4 lanes + sven)
    "priority": "blocker",
    "title": "Cut the 6 should-NOT-have-spoken HEARTBEAT lines",
    "evidence": {
      "worst_lines": [{"id":"0007_…_HEARTBEAT","line":"a metallic synth dominated the highs","why":"describe-bank, no move"}],
      "failing_dim": "friend_not_narrator",
      "measured": 1.4, "target": 2.0
    },
    "where": "src/vibemix/runtime/speak_gate.py + src/vibemix/prompts/matrix.py",
    "verify": "uv run python scripts/eval/respan_sven_heartbeat_judge.py --session <dir> --events ALL --require-quality"
  }
}
```

Key properties for autonomy:
- **`overall_pass`** = single boolean the loop branches on.
- **`gates.*.pass`** = each judge's existing exit-code, captured as data.
- **`next_goal`** = the lowest-passing dim, its worst evidence rows (`worst_lines` already produced by
  `heartbeat_judge.py:505-509`), the routed lane (map dim→lane: prose→`sven`,
  ux_vision.learn_legible→`learn`, ux_vision.*→`frontend`, citation_f1→`engine`), and a copy-paste
  `verify` command so the next Codex run can prove its own fix the same way the loop measured it.
- **`where`** = a hint, not a mandate (the lane agent re-derives the real call-site).

This makes the loop closed: judge measures → lowest dim becomes the goal → Codex fixes → same judge
re-measures. The verify command is the contract that prevents "test-green-but-dark" regressions.

---

## 9. CONCRETE "what must be built/wired and where" list

Ordered by leverage for the overnight loop:

1. **Overnight orchestrator** `scripts/eval/qa_loop_run.py` (NEW). Inputs: a capture dir (or a WAV
   to stage as `input.wav`). Steps: (a) optionally launch the app with `VIBEMIX_REPLAY_SESSION`
   (reuse `replay_live_runner.py:LiveReplayConfig`) — OR accept an already-recorded dir; (b) run
   `respan_sven_heartbeat_judge.py --events ALL --require-quality --out` on it; (c) run the UX
   vision judge (item 3); (d) optionally run `replay_harness.py` for citation-F1; (e) merge into
   `qa-verdict.json` (item 4). NO new judge logic — it's a fan-out + merge.
2. **Time-warp / segment replay** for `_audio_replay.py:166-186` (NEW, optional but high-value).
   A 3h real-time replay is fine overnight, but add a `VIBEMIX_REPLAY_SPEED` or a segment window so
   iteration during the day is minutes not hours. Touch only `ReplayCaptureStream._run` (the
   `time.sleep`), keeping the same callback contract.
3. **`scripts/eval/respan_ux_vision_judge.py`** (NEW, the real build — §7). Plus a Playwright
   screenshot driver under `scripts/e2e/` that writes `<capture>/screens/*.png` paired with
   `SessionSnapshotPayload` JSON.
4. **`vibemix_qa_verdict_v1` schema** (NEW, §8) — the judge→goal contract. Implement as a small
   merge in the orchestrator; pin with a unit test so the shape can't drift.
5. **Arbitrary-WAV stager** (NEW, trivial) — a helper that resamples any WAV to 16kHz mono int16
   and drops it as `<dir>/input.wav` (format per `recorder.py:250-253`) so a fresh 3h set needs no
   prior recording. Reuse `vibemix.audio.resample.resample_audio`.
6. **Standardize the rubric**: keep the 5-dim Respan rubric (`heartbeat_judge.py:73-88`) as THE
   Sven-prose rubric; document that `judge.py`'s 6-axis is the separate citation-F1 gate. No code
   change — a one-line note in the orchestrator + verdict schema so lanes don't confuse the two.

**Nothing in items 1, 4, 5, 6 requires inventing a judge — they wire existing parts.** Only items 2
(time-warp) and 3 (vision judge) are genuine builds, and only #3 is on the critical path for the UX
weakness Kaan named.

---

## 10. Honest caveats (so the loop isn't trusted blindly)

- The Sven judge needs `RESPAN_API_KEY` and the Respan account must have a Gemini provider cred or
  the model calls 401 (per memory `project_respan_observability`). The `--gate-only` /
  `--describe-bank-census --dry-run` paths are the deterministic, no-key fallbacks.
- `describe_bank_census` does NOT replay `event.extra` (`:106-109`) — it's a no-payload census, so
  it under-counts what a full live gate would have kept. Treat it as a floor, not the truth.
- Replay is real-time and reads only `input.wav` — a 3h overnight run is one 3h app process, which
  also exercises long-run stability (a bonus), but offers no fast inner loop until time-warp lands.
- The vision judge is the one piece with NO existing reference in-repo to crib from; its rubric is a
  fresh authoring risk — keep it positive-framed and blind, and validate it against a couple of
  hand-labeled screens before trusting its gate.
