# RED-TEAM — the OVERNIGHT ORCHESTRATION design

**Author:** red-team agent (read-only; only this file written).
**Branch:** `ux-redesign-impeccable`. **Date:** 2026-06-04.
**Method:** read all 8 substrate maps (`MAP-*.md`) + verified the orchestration-critical
claims against the live repo (worktree list, port :8765, corpus contents, `.mcp.json`,
key presence, orchestrator-script existence). Every hazard below is grounded in a map
quote or a live repo check, not assertion.

---

## VERDICT IN ONE LINE

The design's **core instinct is right** — pre-written queues + a self-QA gate + a
commit-marker done-signal is the correct way to route around a flaky Claude. But it
**will NOT run unattended as drawn tonight**, for three concrete reasons that the maps
already prove: (1) the **self-QA harness does not exist yet** (the orchestrator script
`scripts/eval/run_overnight_qa.py` is absent — verified), so the gate every lane depends
on is itself the first thing that must be built, which means the lanes have a hard
serial dependency the design treats as parallel; (2) **lanes sharing ONE working tree
will eat each other's commits** — the single-owner-file hazard is real and I found the
exact files dirty/contended right now; (3) the **launch half of drive-app is a race, not
a command** (`MAP-drive-app` TL;DR: *"there is **no deterministic, race-free,
agent-owned one-command launcher**"*), and :8765 is **held by a running app right now**
(PID 50326, verified) — a lane that tries to self-QA by launching the app will hit the
fatal exit-2 port sentinel with no auto-free.

The fix is not to abandon the design — it is to **(a) build the gate FIRST as a
gate-0 dependency, (b) put each lane in its own git worktree so there is NO shared
tree, and (c) make the gate degrade to keyless/offline + engine-only headless** so it
never depends on a GUI launch or a live key at 3am.

---

## PART 1 — THE CORRECT DEPENDENCY ORDER (what must land before any lane can self-QA)

The design says "each lane has a self-QA gate so no lane waits on Claude." But a
**self-QA gate the lanes share does not exist yet** and is built "early in the night" —
which means there IS a wait, and it is on the gate, not on Claude. Sequence it
explicitly. Nothing in GATE-0 is invention; it is **wiring existing parts** (every map
agrees the judges/feed are built — the glue is the ~20% missing).

### GATE-0 — build the shared harness BEFORE lanes start (serial, ~1–2h, blocking)

These are prerequisites. A lane that "self-QAs" before these land is self-QA-ing against
nothing.

0a. **The 3-hour (or designated) replay set must exist on disk.** This is the keystone
    blocker every map names. `MAP-respan` §4: *"the QA machinery is built and proven;
    the fuel … is missing. This is the keystone blocker for the autonomous loop."*
    Verified live: `eval/corpus/sessions/*/` contains only `.gitkeep` / `genre.txt` —
    **zero `input.wav`**. `MAP-audio-replay` item 1: drop a WAV as `<dir>/input.wav`
    (format is forgiving, `_read_wav_float32` resamples any rate/channels — **no code**).
    **Owner: Kaan** (must designate which recording is QA-safe — privacy rule; the 503
    real recordings under `~/Library/Application Support/vibemix/recordings/` are
    privacy-sensitive and must not be auto-read). *Without this, all three lanes self-QA
    against silence.*

0b. **The launcher script** `scripts/qa/launch_replay.sh` (`MAP-drive-app` §7 item 1):
    `uv sync` warm pre-step (kills the ~43s-latch-vs-~80s-uv-cold-sync race —
    `MAP-drive-app` §3), free :8765 if held (`lsof -ti :8765 | xargs kill` — there is
    **no auto-free**, the second launch hits *"sidecar-crashed reason=port-in-use … no
    retry"*, `MAP-drive-app` §2), launch **ENGINE-ONLY headless** (`uv run python -m
    vibemix`, the only display-free path — *"no headless/offscreen launch path anywhere
    in tauri/"*), poll `sidecar_status()` until `ws_reachable` with a generous ~120s
    budget.

0c. **The overnight orchestrator + verdict schema** `scripts/eval/run_overnight_qa.py`
    + `vibemix_qa_verdict_v1` (`MAP-judge` §8/§9 item 1+4; `MAP-respan` §6 item 2 —
    *"There is NO single runner tying replay_live_runner + respan_sven_heartbeat_judge +
    replay_harness into one … command"*). Verified: the file does not exist. This is a
    fan-out + merge, **no new judge logic**. It writes `qa-verdict.json` with
    `overall_pass` + per-gate `pass` + a routed `next_goal` per lane — this is the
    thing each lane's self-QA actually calls.

0d. **Wire the vibemix-dev MCP into the repo** `.mcp.json` (`MAP-drive-app` §7 item 5).
    Verified: **no `.mcp.json` exists** — the dev MCP is registered only in
    `~/.claude.json` under the main project path. *"A fresh Codex/Claude worktree would
    NOT inherit it."* If lanes run in worktrees (Part 2), they get **no ws_observe /
    ws_trigger / sidecar_status** unless `.mcp.json` is committed with `--repo-root`.

GATE-0 is the **only true serial section**. Run it as ONE Claude task (or Kaan-assisted
for 0a) before spawning lanes. Everything after is parallel.

### TIER-1 — lanes can self-QA once GATE-0 lands (parallel)

Each lane's self-QA = "launch via 0b → feed the 0a set → run the 0c orchestrator →
read `qa-verdict.json` → only commit if the gate it owns passes (or improves)."

- **Lane 1 (Sven):** gate = `respan_sven_heartbeat_judge.py --require-quality`
  (`MAP-judge` §2 — REAL, exit-code, friend/grounded/earned/move/voice + should_speak).
  **Hard caveat that reorders this lane:** `MAP-sven` §2 proves that on a master-only
  *audio replay* (no controller, no per-deck stems) **Sven has zero grounded coaching
  evidence** — the eq-move guard needs a controller, the Judge + scorer abstain two-deck.
  So a naive replay will score Sven as a *narrator by construction*, and the lane will
  "fix" a non-bug. **Lane 1 must FIRST land `MAP-sven` item #1 (voice the master-mix
  energy read with no A/B requirement) OR feed a replay set that includes `midi.jsonl`
  with real EQ moves** — otherwise its self-QA measures the rig limitation, not the prose.

- **Lane 2 (AI/engines = Debrief + Viber):**
  - Debrief self-QA needs `GEMINI_API_KEY` (present in `.env` — verified) OR a pre-seeded
    cache fixture (`MAP-debrief` §6.1: *"the harness MUST have a working GEMINI_API_KEY …
    OR pre-seed session_debrief.json + .mp3 to hit the cache path"*). Debrief is
    **headless-safe** (`--debrief` short-circuits audio init — good for unattended) and
    is the **best-wired secondary engine** — low risk.
  - Viber self-QA must use the **keyless `auto_crate`** path (`MAP-viber` §6 item 1 —
    *"needs NO Codex login, returns structured JSON"*). The Codex-backed curate/chat/build
    path is gated on `codex login` (present on this machine but a hard external
    precondition); **do not put the agentic Codex path on the unattended critical path** —
    if login expires at 2am the lane stalls. Restrict autonomous Viber QA to `auto_crate`
    + reading the `VIBEMIX_TOOL_EVENTS_FILE` JSONL.

- **Lane 3 (UX via impeccable):** gate = the **VISION/UX judge — which does NOT exist**
  (`MAP-judge` §6: *"VISION/UX judge … 0% there and is the real gap"*; §7 is the build).
  AND the screenshot capture has **no headless source** (`MAP-drive-app` §5:
  *"Screenshots are not a built capability … the UX/visual half of the judge has no
  headless data source today"*). **This is the single weakest lane.** Two honest options:
  (i) Lane 3's self-QA runs the **Playwright UI build** (`npm run build && npm test`,
  ~886 vitest tests — that IS a real headless gate) + the existing
  `grounding-failure.spec.ts` invariant, and **defers the vision judge** to a human pass;
  or (ii) build the vision judge in GATE-0 (it is genuine new work + a fresh-rubric risk,
  `MAP-judge` §10 — *"the one piece with NO existing reference in-repo to crib from"*).
  **Recommendation: option (i) tonight.** Lane 3's *biggest real win is keyless and
  test-gateable anyway*: the MOSS→Chatterbox rename (`MAP-ux-learn` Part 1 — the badge
  keys on dead `model.id === "moss-tts"`, backend emits `chatterbox-voice`, badge silently
  hidden). That fix is a rename+reroute proven by the existing (currently dead-contract-
  locking) vitest pins — no live app, no vision judge needed.

### TIER-2 — depends on Tier-1 (do not start unattended)

Lane B live-Sven Respan span (privacy-gated, not instrumented — `MAP-respan` §6 item 3),
session→lesson loop (`MAP-debrief` §6.4), time-warp replay (`MAP-audio-replay` item 2 —
risky, desyncs detector windows; *"do not silently warp"*). These are NOT tonight.

---

## PART 2 — COMMIT / COLLISION HAZARD MITIGATIONS

This is the design's **most under-specified risk** and the one most likely to silently
corrupt the night.

### The hazard, verified live

CLAUDE.md is explicit and I confirmed the mechanism on disk: *"`git commit` is shared
across concurrent Claude sessions on this tree … `git commit` absorbs **every** file
staged across all sessions, regardless of who staged it."* The design names the
single-owner files (`__main__.py`, `session_loop.py`, `config_store.py` = backend;
`messages.schema.json` = frontend) — all four **exist and are real** (verified). Worse,
the tree is **already dirty** right now (`__main__.py`, `session_loop.py`,
`CLAUDE_LAND_QUEUE.md`, a test spec — 4 modified, per `git status`), so a lane that runs
`git add -A` tonight will absorb pre-existing uncommitted work from *this* session and
whatever else is in flight.

This is not theoretical for the proposed lanes:
- **Lane 1 (Sven)** will touch `runtime/coach.py`, `runtime/speak_gate.py`,
  `prompts/matrix.py`, and — per `MAP-sven` item #4 — **`__main__.py:1503-1507`**
  (deck-capture default). That is a **single-owner backend file**.
- **Lane 2 (Viber/Debrief)** touches `debrief/main.py` and — per `MAP-viber` item #4 +
  `MAP-ux-learn` install fix — `__main__.py` (live auto-cue, `--install` choices) and
  `library_cmds.rs`. **`__main__.py` again.**
- **Lane 3 (UX)** touches `tauri/ui/src/.../*.ts` AND — for the install-target fix —
  **`messages.schema.json`** (then `npm run codegen:ipc`, which regenerates the
  pre-compiled validator) AND `library_cmds.rs`. **`messages.schema.json` is the
  frontend single-owner file**, and `library_cmds.rs` is now contended by BOTH Lane 2
  and Lane 3.

So **two of the three lanes want `__main__.py`, and two want `library_cmds.rs`.** A
shared tree guarantees a collision.

### Mitigation A (STRONGLY PREFERRED) — one git worktree per lane, NO shared tree

The repo **already uses worktrees heavily** (verified: 30+ under `.claude/worktrees/`
plus `/private/tmp/vibemix-*` build worktrees, and two named Codex lanes at
`dj-set-ai-codex-b-land` / `dj-set-ai-codex-b-safe-now`). The infra is proven. Give each
lane its own worktree off `ux-redesign-impeccable`:

- `git worktree add ../qa-lane1-sven   -b qa/lane1-sven`
- `git worktree add ../qa-lane2-engine -b qa/lane2-engine`
- `git worktree add ../qa-lane3-ux     -b qa/lane3-ux`

Then `git commit` in a lane absorbs **only that lane's files** — the shared-commit hazard
**vanishes** because there is no shared index. Claude's async audit reads each branch by
`git log qa/laneN-sven` and verifies the commit marker. Kaan (or a morning Claude) merges
the three branches with normal conflict resolution on `__main__.py` / `library_cmds.rs`
ONCE, awake, instead of three robots racing an index at 3am.
**Cost:** each worktree's first `uv run` does a cold sync (the §3 race) — so GATE-0's
`uv sync` warm step must run **per worktree**. And `.mcp.json` (GATE-0 0d) must be
committed so each worktree inherits the dev MCP. **Both are one-time and cheap.**

### Mitigation B (FALLBACK if worktrees are rejected) — file-island discipline + serial single-owner edits

If lanes must share one tree:
1. **NEVER `git add -A` / `git add .`** — only `git add <explicit-path>`, and verify
   `git diff --cached --name-only` matches the intended set before every commit
   (CLAUDE.md rule). Bake this into each lane's queue as a literal pre-commit step.
2. **Disjoint file islands by ownership:**
   - Lane 1 owns: `runtime/coach.py`, `runtime/speak_gate.py`,
     `runtime/transition_verdict_voice.py`, `prompts/matrix.py`, `state/evidence_registry.py`.
   - Lane 2 owns: `debrief/*`, `library/auto_crate.py`, `intel/move_grade.py`.
   - Lane 3 owns: `tauri/ui/src/shell/*`, `tauri/ui/src/settings/*`, `tauri/ui/src/wizard/*`,
     `tauri/ui/src/library/api.ts` + its `*.test.ts`.
3. **The single-owner files are a LOCK, not an island.** `__main__.py`,
   `session_loop.py`, `config_store.py`, `messages.schema.json`, `library_cmds.rs` may be
   edited by **ONE lane at a time, serially, with a file-level lock** (e.g. a sentinel file
   `/tmp/vibemix-qa-locks/__main__.py.lock`). The orchestrator hands the lock; a lane that
   wants a locked file but can't get it **defers that queue item** and continues with its
   island work. This is fragile (a crashed lane can hold a stale lock — add a timeout).
4. **`messages.schema.json` is special:** editing it requires `npm run codegen:ipc`
   (pre-compiled `validator.generated.mjs`, stale = new fields rejected). Only Lane 3
   touches it, and it must regen + commit the generated file in the **same** commit.

**Mitigation A is dramatically safer and the repo already supports it. Recommend A. Use
B only if Kaan wants a single tree for review simplicity.**

---

## PART 3 — FAILURE MODES (ranked, each with a mitigation)

1. **The gate doesn't exist when lanes start → lanes self-QA against nothing → commit
   green-but-dark work.** (Exactly the 11h reskin-drift failure class — `MAP-respan` §2c:
   *"UI-reskin + test-green, zero by-ear … the agent did the wrong kind of work and called
   it done."*) **Mitigation:** GATE-0 is blocking; no lane spawns until `qa-verdict.json`
   can be produced for a known-good baseline. The verdict's `verify` command (`MAP-judge`
   §8) is the contract that makes "green" mean "by-ear-passed", not "tests pass."

2. **:8765 collision.** Verified: the port is held RIGHT NOW (PID 50326). Two lanes that
   both launch the app → the second hits the fatal exit-2 sentinel, no retry
   (`MAP-drive-app` §2). **Mitigation:** lanes do NOT each launch a full app. Either (a)
   the orchestrator owns ONE engine-only app instance and lanes drive it via the MCP, or
   (b) lanes use the `replay_live_runner.py` per-instance `VIBEMIX_WS_PORT` isolation
   (`MAP-audio-replay`: runner sets per-instance ports + isolated HOME) — never the bare
   default port. Worktrees (Mitigation A) make per-instance ports natural.

3. **uv cold-sync false "STOPPED".** First `uv run` in a fresh worktree blows past the
   ~43s ws-unreachable latch (real cumulative time, the "~30s" comment is stale —
   `MAP-drive-app` §3). A lane watching boot will conclude the app is dead and either
   retry-storm or mark its task failed. **Mitigation:** GATE-0 0b `uv sync` warm step per
   worktree; the engine-only headless path doesn't render the banner anyway (the banner is
   a Rust/webview artifact), so prefer engine-only for unattended QA.

4. **Live-key / network dependency at 3am.** Debrief drills + TLDR are **hard-gated on a
   live Gemini key** (`MAP-debrief` §6.1) and the Sven/Respan judges need `RESPAN_API_KEY`
   (verified **NOT in shell env** — only the strict-gate artifact proves it ran once with
   the key present). If the key 401s or rate-limits overnight, the gate errors and lanes
   stall or commit on a failed gate. **Mitigation:** (a) every gate must have a keyless
   deterministic fallback — `respan_sven_sim.py --gate-only` (9/9 gate routing, no key,
   verified this session), `describe_bank_census --dry-run`, the offline
   `replay_harness.py` citation-F1, and a pre-seeded debrief cache. (b) Confirm
   `RESPAN_API_KEY` + `GEMINI_API_KEY` are in the **launched process env** (not just the
   shell) before the night starts — `open -a` strips env; launch the sidecar from a shell
   that exports them (CLAUDE.md packaged-GUI note).

5. **Compaction eats the queue mid-lane.** The substrate is flaky/compacting (the premise).
   A lane that holds its queue only in context loses it on compaction. **Mitigation:** the
   pre-written queue must be an **on-disk file** (e.g. `.planning/packets/2026-06-04/
   qa-loop-map/QUEUE-lane1.md`) that the lane re-reads at the top of every step, and each
   completed item is checked off **on disk** (append to a `DONE.log`), so a recovered lane
   resumes from disk, not memory. The done-signal (Part 4) is also on disk for the same
   reason.

6. **Sven lane "fixes" a non-bug.** On master-only audio replay Sven narrates *by
   construction* (`MAP-sven` §2). If the lane's queue says "make Sven coach not narrate"
   and the gate scores narration, the lane may over-edit prompts/gate chasing a score that
   the rig limitation caps. **Mitigation:** Lane 1's FIRST queue item is the `MAP-sven` #1
   energy-read receipt (gives the replay something to coach from); the gate's `next_goal`
   evidence must distinguish "no grounded receipt available" from "had a receipt, narrated
   anyway" (`MAP-sven` item #6 — log coach-vs-narrate signal).

7. **The done-marker is forged / premature.** An agent that times out mid-task might emit
   the success marker anyway (the reskin-drift pathology). **Mitigation:** the marker is
   **machine-derived, not agent-asserted** — see Part 4. The marker is only valid if it
   carries the `qa-verdict.json` `overall_pass`/gate hash the orchestrator computed; Claude's
   audit recomputes it.

8. **Claude's async audit itself dies (flaky substrate).** The verifier is on the same
   flaky substrate as the lanes. **Mitigation:** the audit must be **stateless + resumable**
   — it reads commit markers + `qa-verdict.json` from disk, verifies, writes a verdict file,
   and exits. A relaunched audit re-reads disk and continues. Never hold audit state in
   context. Run it as a cron/`loop` on an interval (the maps' "ASYNC audit workflows"), not
   a long-lived session.

9. **`messages.schema.json` stale-validator trap.** Lane 3 edits the schema but forgets
   `codegen:ipc` → new IPC fields rejected at runtime → the feature looks dead → the UX
   gate (rightly) flags it → lane churns. **Mitigation:** Lane 3's queue bakes
   `npm run codegen:ipc` as a mandatory post-schema-edit step, committed in the same commit;
   the `ipc-wiring-checker` skill is the pre-commit gate.

---

## PART 4 — THE SAFEST DONE-SIGNAL / HANDBACK PROTOCOL

The design's instinct is correct: **a structured commit marker, NOT a Codex-waits-on-
Claude ping** (Claude's substrate is flaky, so a synchronous handshake deadlocks the
night). Make it concrete and forgeproof:

### The marker = a structured git trailer + an on-disk verdict, machine-derived

When a lane completes a queue item, its commit message ends with a trailer the audit
parses (never free prose):

```
QA-LANE: lane1-sven
QA-ITEM: voice-energy-read-master-mix
QA-VERDICT: .planning/eval-runs/qa-20260604-NNNN/qa-verdict.json
QA-GATE: sven_prose
QA-PASS: true
QA-VERIFY: uv run python scripts/eval/respan_sven_heartbeat_judge.py --session <dir> --events ALL --require-quality
```

Properties that make it survive a flaky substrate:
- **Asynchronous by construction.** The lane commits and moves on. It does NOT wait for
  Claude. Claude's audit polls `git log --all --grep '^QA-LANE:'` on an interval.
- **Machine-derived, not asserted.** `QA-PASS` is only trusted if the referenced
  `qa-verdict.json` exists, its `gates.<QA-GATE>.pass` matches `QA-PASS`, and the audit
  can **re-run `QA-VERIFY` and reproduce it** (or, when keyless, re-check the deterministic
  gate). A marker without a reproducible verdict = treated as FAIL, not done. This is the
  direct antidote to the reskin-drift "tests-green = done" lie.
- **Idempotent + resumable.** Both the lane (reads its on-disk `QUEUE-laneN.md` +
  `DONE.log`) and the audit (reads commit markers + verdict files) are stateless across
  compaction. A relaunched session re-derives state from disk.

### Queue replenishment = the verdict's `next_goal`, written to disk

Claude does NOT push goals to lanes (synchronous, flaky). Instead the orchestrator's
`qa-verdict.json` already emits a routed `next_goal` per lane (`MAP-judge` §8 — lowest
dim + worst evidence rows + `where` hint + `verify` command). Claude's audit **appends
that `next_goal` to the lane's on-disk queue file** and updates a `STATUS.md` board. The
lane, at the top of its loop, **re-reads its queue file** and picks up the appended goal.
No ping, no wait — the queue file IS the channel, disk is the bus.

### Handback to Kaan in the morning = ONE board

A single `.planning/packets/2026-06-04/qa-loop-map/OVERNIGHT-STATUS.md` that the audit
maintains: per-lane last-commit SHA, last verdict, gates passing/failing, items done /
deferred (with reason — e.g. "deferred: needs `__main__.py` lock" or "deferred: vision
judge not built"), and the merge order for the three lane branches. Kaan wakes to a
board + three branches to merge, not a forensic dig through 3am commit soup.

### What the protocol explicitly does NOT do

- No lane waits on a Claude ack (deadlock-proof against flaky Claude).
- No `git add -A` (commit-soup-proof — Mitigation A/B).
- No "tests pass" as a done-criterion (reskin-drift-proof — must reproduce the by-ear
  verdict).
- No GUI-launch or live-key on the critical path of the *done-check* (keyless gate is the
  floor; the keyed gate is a bonus when the key is alive).

---

## BOTTOM LINE FOR KAAN

The design is the right shape. To make it actually run unattended: **(1) build GATE-0
first** — designate a replay set (you, privacy), then the launcher + orchestrator +
`.mcp.json` (Claude, ~1–2h) — *because the self-QA gate every lane leans on does not exist
yet and is the real serial dependency the design hides*; **(2) one git worktree per lane,
not one shared tree** — the repo already runs 30+ worktrees, and a shared tree guarantees
`__main__.py` and `library_cmds.rs` collisions between two of your three lanes; **(3) every
gate keyless-degradeable and engine-only headless** — :8765 is held right now and there's
no GUI-headless path, so a lane that self-QAs by launching the GUI or calling a live key at
3am will stall. The vision/UX judge does not exist (0%) — Lane 3 should self-QA on the
existing vitest/Playwright build + the keyless MOSS→Chatterbox rename, and defer vision to a
human morning pass. The done-signal is correctly a commit marker — make it a structured git
trailer + a *reproducible* `qa-verdict.json`, so "done" means "by-ear gate reproduced", not
"tests green."
