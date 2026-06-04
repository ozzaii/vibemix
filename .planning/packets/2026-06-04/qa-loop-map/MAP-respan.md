# MAP — RESPAN as the QA + agent-ops telemetry layer

> READ-ONLY map. Branch `ux-redesign-impeccable`. Probed live + file:line, not memory.
> Verdict legend: **REAL** = code on disk, runnable, proven. **ASPIRATIONAL** = planned, packet-only, not wired.

## TL;DR (one paragraph)

The RESPAN integration is **far more built than the plan packet implies**. The
plan (`RESPAN-INTEGRATION-PLAN.md`) reads as "decision-ready, mostly probes" — but
on disk there are **three real, runnable, test-covered eval scripts** plus a real
**overnight QA findings engine** wired into the deterministic replay harness. Respan
is used as a **REST gateway-as-judge + a request-log sink over plain `httpx`** (NOT
the `respan-ai` SDK — that dependency is **not installed and not in `pyproject.toml`/`uv.lock`**;
the scripts deliberately bypass the SDK's documented `base_url` bug). It is **observe/eval
mode, never gateway-on-the-live-path**. The provider-cred wall is **CLEARED** — a
2026-06-04 artifact proves a full Respan run scoring 10 Sven scenarios with real judge
means (friend 3.0 / grounded 3.0). For TONIGHT, Lane A (Sven offline/recorded evals as a
regression instrument) is **REAL and usable now**. Lane B (live online-eval) is gated on
a Kaan privacy yes AND product instrumentation that **does not exist yet**. Lane C (Viber
trace→Respan) is **NOT built**. Lane D (agent-ops MCP watching the Codex/Claude loop) is
**NOT wired** and would NOT have caught the 11h reskin-drift in its current form.

---

## 1. What is actually on disk (REAL)

### 1a. Three Respan eval scripts — REAL, runnable, tested
- `scripts/eval/respan_sven_sim.py` (31k) — synthetic deck-move scenario engine. Drives the
  **REAL product gate + persona + linter** (`decide_speak_gate`, `build_system_instruction`,
  `CitationLinter`) → Respan gateway generate → 5-dim Respan judge. `respan_sven_sim.py:44-58`
  imports live runtime primitives. Has a deterministic `--gate-only` path (no key, no model).
- `scripts/eval/respan_sven_heartbeat_judge.py` (15k) — judges Sven's **ACTUAL spoken lines**
  from a real recorded session (`invocations/<NNNN>/meta.json` + `response.txt`), on the live
  model via the Respan gateway, on the 5 dims + a `should_speak` verdict. `respan_sven_heartbeat_judge.py:196-232`
  (`load_rows`) + `:253-299` (`judge_one`). This is the "what fraction of real spoken lines
  should have been silence" instrument — the bench's structural blind spot.
- `scripts/eval/replay_harness.py` (53k) — the deterministic offline replay harness, and the
  **overnight QA findings engine**. It walks a corpus, time-warps `input.wav` through the REAL
  refresh tick + `EventDetector` (`replay_harness.py:206-284`), and — via `--quality-respan` —
  calls the heartbeat judge per session and folds the result into a `findings.json`
  (`replay_harness.py:884-951`, `_run_respan_quality_for_session` / `_attach_respan_quality`).

### 1b. A live-app replay runner — REAL (the loop-breaker's other half)
- `scripts/eval/replay_live_runner.py` (15k) — launches **current-source `python -m vibemix`**
  with `VIBEMIX_REPLAY_SESSION` pointed at a recorded session, isolates HOME + ports per
  instance, runs N seconds, SIGINTs, and writes `vibemix_live_replay_findings_v1` from
  stdout/stderr + the recording artifacts (`replay_live_runner.py:96-189`, `build_findings:192-269`).
  It flags `mute`, `citation_zero`, `slop_suppressed`, `late`, `no_music_meter`, `voice_not_muted`.
- The replay BACKEND it drives is REAL and wired: `src/vibemix/platform/_audio_replay.py`
  feeds `input.wav` into the capture callback (`_audio_replay.py:73,111,122,167`), replays
  `midi.jsonl` (`:190-231`) and `nowplaying.jsonl`, and **disables live MIDI** while active
  (`:205`). `__main__.py:1459` prints `-> replay capture:` confirming the wrap is selected.

### 1c. Integration mode = REST gateway + log sink over httpx (REAL)
- Both judge scripts hit **`https://api.respan.ai/api/chat/completions`** (gateway) for
  generate+judge and **`/api/request-logs/create`** for logging
  (`respan_sven_sim.py:60-62`, `respan_sven_heartbeat_judge.py:57-59`).
- The model id is resolved through the central router, NOT hardcoded:
  `resolve_model("live_coach_openrouter")` → `google/gemini-3.5-flash` → rewritten to
  `gemini/gemini-3.5-flash` for Respan (`respan_sven_sim.py:65-72`;
  `_router_config.py:43`). This keeps the grep-gate happy and means the judge runs on the
  **same model family as the live co-host**.
- URL is pinned to the Respan host (`_post` raises on any non-Respan URL —
  `respan_sven_sim.py:285`, `respan_sven_heartbeat_judge.py:238`). Key is **env-only**
  (`RESPAN_API_KEY`), never written to a file.
- **The `respan-ai` SDK is NOT a dependency.** `grep respan pyproject.toml uv.lock` → only the
  `keywords=[...]` field matches (a false hit, not the package). The plan's §7 SDK base_url
  bug finding is honored: everything runs on direct `httpx`. **This is correct and intentional.**

### 1d. Provider-cred wall = CLEARED, proven end-to-end (REAL)
The plan's #1 blocker ("add a provider key in Settings → Providers") is **resolved**. Artifact
`.planning/eval-runs/sven-strict-gate-20260604/respan-sven-sim-strict-gate.json` is a real run:
- config: `model=gemini/gemini-3.5-flash`, `strict_sven_gate=true`, all live-parity flags on
- judged means over 10 scenarios: `friend 3.0 / grounded 3.0 / earned 2.2 / move 2.2 / voice 2.6`
- `gate_ok: 10/10`, `n_results: 10`
⇒ the gateway-as-judge path **completes against real Gemini through Respan today**, with Kaan's
provider key present in the Respan account. Proof doc: `.../strict-sven-gate-20260604/strict-sven-gate-proof.md`.

### 1e. Tests exist and pass (REAL)
- `tests/eval/test_respan_sven_sim_quality_gate.py` (proof doc cites **19 passed**)
- `tests/eval/test_respan_sven_heartbeat_quality_gate.py`
- `tests/eval/test_replay_harness.py`, `test_replay_harness_phase_41.py`, `test_replay_harness_cooldowns.py`
- I **independently ran** `respan_sven_sim.py --gate-only` (no key): `gate routing: 9/9 matched`.
  The deterministic spine boots clean on current source.

---

## 2. What this gives us TONIGHT, per the question's three asks

### (a) Sven offline evals as a regression instrument — **REAL, usable now**
- Lane A is **constructible and proven** via the gateway-as-judge path. Two ways to run it tonight:
  1. **Synthetic gate+persona regression:** `respan_sven_sim.py --strict-sven-gate` →
     deterministic gate routing 10/10 + judged dim means with a `--require-quality` exit code
     (CI-gateable; `respan_sven_sim.py:723-730`). This is a **standing regression gate** TODAY.
  2. **Real-line judge:** `respan_sven_heartbeat_judge.py --session <recording> --events ALL`
     → per-line 5-dim + should_speak, with a `--require-quality` gate
     (`respan_sven_heartbeat_judge.py:518-525`).
- **Caveat (honest):** this is the **REST gateway-as-judge** version, NOT the "durable"
  Respan-native **Dataset + Evaluator + Experiment** objects the plan §7 line 113 calls the
  remaining build. So you get a re-runnable scored number + logged rows tonight, but NOT yet
  the versioned/diffable Experiment dashboard. For an overnight regression number, the
  gateway-as-judge is **fully sufficient**.
- **Verdict: REAL.** This is the strongest, ready-now piece of the whole RESPAN map.

### (b) Viber tool-call tracing — **NOT built (ASPIRATIONAL)**
- Lane C exists only as a plan paragraph (`RESPAN-INTEGRATION-PLAN.md:68-73`). I found **zero**
  Respan wiring touching `library/codex_curate.py` or `library/toolset.py`. The data source it
  names (`CodexChatResult.tool_trace` / `move_grades`) exists in the product, but **nothing maps
  it to a Respan span or a Respan evaluator.**
- **Verdict: ASPIRATIONAL.** Not available tonight. (Low effort to add, but it is not code yet.)

### (c) AGENT-OPS watching the Codex/Claude loop — **NOT wired; would NOT have caught the reskin-drift**
- Lane D (the Respan MCP server `claude mcp add … https://mcp.respan.ai/mcp`) is **not configured**
  — by design, because `claude mcp add` writes the key to a config file and the plan says **Kaan**
  runs it with the rotated key (`RESPAN-INTEGRATION-PLAN.md:81`). It is not in the agent config.
- Even if added, Lane D only surfaces traces that **Lanes A/B/C produce**. It watches **LLM-call
  telemetry** (Sven reactions, Viber curate calls). It does **NOT** watch the coding agent's
  edit/test/commit behavior. The 11h reskin-drift was *"UI-reskin + test-green, zero by-ear"* —
  a **process/output-quality** failure, not an LLM-trace anomaly. Respan as designed would NOT
  have flagged it: there were no bad Sven spans to find, the failure was "agent did the wrong
  *kind* of work and called it done."
- The thing that **would** catch reskin-drift is the **overnight QA findings loop**
  (`replay_harness.py:953-1072` + `replay_live_runner.py:build_findings`) producing a hard
  `verdict: fail` with `mute`/`citation_zero`/`slop`/`late` flags + Respan quality dims — i.e.
  "prove it works by-ear, automatically." Respan is the **quality scorer inside** that loop, not
  the agent-ops watcher itself. That distinction matters: **the loop-breaker is the findings
  harness; Respan is one (optional) scoring layer in it.**
- **Verdict: ASPIRATIONAL for agent-ops; and a category mismatch for the reskin-drift use case.**

---

## 3. Is RESPAN usable now as the QA telemetry sink? — **YES, partially, and not the bottleneck**

- **Ingestion sink:** REAL today. `/api/request-logs/create` returns 201 with the text-only
  span shape (plan §7 line 109); both judge scripts log every judge call with metadata
  (`respan_sven_heartbeat_judge.py:281-298`). No provider creds needed for log ingestion.
- **Scoring (gateway-as-judge):** REAL today — provider wall cleared (§1d).
- **What it is gated on:** for the **durable Dataset/Evaluator/Experiment** objects, nothing
  blocks creation (key has write scope) but you'd build payloads on direct REST (SDK base_url
  bug). That's a *build*, not a *gate*. For **online live-Sven eval (Lane B)**: gated on (1) a
  Kaan privacy yes (user-set text → cloud) AND (2) the manual text-only span instrumentation in
  `dj_cohost.py` reaction-emit chokepoint — **which does not exist yet** (the plan calls it a
  future CODEX_READY packet; I found no manual-span emit in product code).

**The real bottleneck is NOT Respan.** It is **the corpus** (see §4). Respan can score whatever
lines you feed it; the gap is the *set to feed.*

---

## 4. THE SINGLE BIGGEST GAP — no replayable set in the corpus

- `eval/corpus/sessions/{techno_01,techno_02,house_01,house_02,hard_tek_01,hard_tek_02}/` each
  contain ONLY `genre.txt`, `source.txt`, and a **0-byte `events.jsonl`**. **There is NO
  `input.wav` anywhere in `eval/corpus/`** (`find eval/corpus -name "*.wav"` → empty).
  `tests/eval/fixtures` holds only `synthetic_session` / `phase_41_synthetic` (5s sines, not a set).
- The replay harness, the live runner, AND the heartbeat judge are all **input-starved**: they
  need a session dir with a real `input.wav` (+ optional `midi.jsonl`, `nowplaying.jsonl`,
  `invocations/`). The corpus has none.
- **What DOES exist:** 503 real recorded sessions under
  `~/Library/Application Support/vibemix/recordings/*/input.wav` (durations 1.4s–504s; **none is a
  3-hour set**, longest seen ~8min). The live runner CAN drive these today
  (`VIBEMIX_REPLAY_SESSION=<dir>`). BUT: (1) they're short, not a 3-hour set; (2) they live under
  a path that overlaps the privacy-sensitive recordings posture — **I did not read their contents**
  (CLAUDE.md HARD RULE), only listed durations. Kaan must designate which recordings are QA-safe
  fixtures.
- **Net:** the QA *machinery* is built and proven; the *fuel* (a long, designated, replayable set
  + its ground-truth `events.jsonl`) is missing. **This is the keystone blocker for the autonomous
  loop, and it is upstream of Respan, not inside it.**

---

## 5. Is RESPAN a BLOCKER for the autonomous QA loop tonight?

**NO — Respan is not the blocker. Lane A is ready; the blocker is the corpus + (for live-eval) a privacy yes.**

- The autonomous loop can run TONIGHT in this shape, all REAL:
  `replay_live_runner.py` (feed a designated recording → real app hears it → findings v1 with
  mute/slop/late/citation flags) **+** `respan_sven_heartbeat_judge.py --require-quality`
  (score the real lines, exit-code gate) **+** `replay_harness.py --use-detector-predictions
  --findings-json --quality-respan` (offline detector + Respan quality fold-in).
- It is **degraded, not dead**, without each missing piece: no long set (corpus gap) → you can
  only QA short recordings; no live online-eval (Lane B not instrumented + privacy gate) → you
  judge recorded lines, not a live continuous stream; no Viber trace (Lane C) / agent-ops MCP
  (Lane D) → no Viber-quality or in-agent visibility.

---

## 6. WHAT MUST BE BUILT/WIRED, AND WHERE (concrete)

1. **[KEYSTONE — corpus] Designate a long replayable QA set + ground truth.** Place (or symlink)
   a real `input.wav` (+ `midi.jsonl`, `nowplaying.jsonl` if available) under
   `eval/corpus/sessions/<name>/` and author its `events.jsonl` ground truth (currently 0 bytes).
   Owner: **Kaan** (designate which recording is QA-safe — privacy). Without this, every harness is
   input-starved. *(This is the loop-breaker, not Respan.)*
2. **[orchestrator] One overnight wrapper script.** There is NO single runner tying
   `replay_live_runner.py` + `respan_sven_heartbeat_judge.py` + `replay_harness.py` into one
   "run all, emit one findings.json, exit code" command (no `scripts/*.sh`, no CI job found).
   Build `scripts/eval/run_overnight_qa.py` (or `.sh`) that fans out over the corpus and merges
   the three findings shapes. Owner: Claude packet → Codex.
3. **[Lane B] Live text-only manual span.** Emit a Respan span (event_id + evidence digest +
   reaction text + citation_strip + grounded flag, **no audio/screen**) at the reaction-emit
   chokepoint in `src/vibemix/agent/dj_cohost.py` (live genai call at `:2747` inside `llm_node`
   from `:1973`). Product code → CODEX_READY packet. **Gated on Kaan §0 privacy yes.**
4. **[Lane C] Viber trace → Respan.** Map `CodexChatResult.tool_trace` / `move_grades`
   (`library/codex_curate.py`) → `/api/request-logs/create` spans + a Viber-grounding evaluator.
   Small CODEX_READY packet. Low privacy gate (dev data).
5. **[Lane A durable] Native Dataset/Evaluator/Experiment objects.** Replace the one-shot
   gateway-as-judge with persistent Respan objects (32 fixtures × 5 dims × persona variants) on
   direct REST (SDK base_url bug). Builds the versioned/diffable A/B dashboard. Owner: Claude.
   *(Optional polish — the gateway-as-judge already gives a usable nightly number.)*
6. **[Lane D] Agent-ops MCP — Kaan runs `claude mcp add` with the ROTATED key.** Only useful once
   Lanes A/B/C spans flow. **Note: this does NOT watch the coding-agent loop** — for reskin-drift
   protection, rely on the overnight findings `verdict: fail` gate (item 2), not the MCP.
7. **[security] Rotate BOTH keys** (Respan + the Tier-2 Gemini provider key) — flagged in the plan
   (§7 line 114) and the packet header. Owner: Kaan.

---

## 7. Sources (file:line)

- Plan: `.planning/packets/2026-06-03/RESPAN-INTEGRATION-PLAN.md` (esp. §7 line 107-118 live results).
- Scripts: `scripts/eval/respan_sven_sim.py:44-72,285-327,723-730`;
  `scripts/eval/respan_sven_heartbeat_judge.py:57-69,196-232,253-299,518-525`;
  `scripts/eval/replay_harness.py:206-284,884-951,953-1072,1362-1404`;
  `scripts/eval/replay_live_runner.py:96-189,192-269`.
- Replay backend: `src/vibemix/platform/_audio_replay.py:73,111,122,167,190-231,205,349`;
  `src/vibemix/__main__.py:1459`.
- Router: `src/vibemix/llm/_router_config.py:43`.
- Dependency: `pyproject.toml` / `uv.lock` — `respan-ai` **absent** (only `keywords=[...]` matches).
- Proof: `.planning/eval-runs/sven-strict-gate-20260604/respan-sven-sim-strict-gate.json`
  (means friend 3.0/grounded 3.0/earned 2.2/move 2.2/voice 2.6, gate 10/10) +
  `strict-sven-gate-proof.md` (19 tests passed).
- Corpus gap: `eval/corpus/sessions/*/` = genre.txt + source.txt + 0-byte events.jsonl, **no input.wav**.
- Replayable-but-short recordings: 503 × `~/Library/Application Support/vibemix/recordings/*/input.wav`
  (durations listed only — contents NOT read, privacy rule).
- Independent run: `respan_sven_sim.py --gate-only` → `gate routing: 9/9 matched` (this session).
