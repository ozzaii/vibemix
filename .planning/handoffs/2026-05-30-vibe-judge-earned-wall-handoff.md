# ✶ HANDOFF — The Vibe Judge + Earned Wall, and the road to SHIP (2026-05-30)

> The single "read me first" for the next session. Written ship-first: the North
> Star is a **shipped vibemix** (free OSS AI DJ co-host, Bravoh's first OSS
> release). The constellation work is the engine; the SHIP is the point. Every
> open item below is graded by what it does for the release, not for novelty.
>
> This handoff distills **four multi-agent investigations (~175 agents total)** so
> their findings never evaporate with the tmp files. Read this, then open the five
> durable companion docs only when you need the depth.

---

## 0. Who & spirit (don't lose this)

Kaan, founder of vibemix. We pulled an all-nighter 2026-05-29→30. The deal:
**"You keep me honest — that's the deal between us"** (from `~/Downloads/cosmic-dj-archive.md`:
cosmic barista → Zephyr → BRAVOH → vibemix; Veridis Quo = safe space; "very disco /
fuck status quo"). **We are the first vibe DJs** — mixing on the semantic/energetic
layer, grounded so the AI never lies. The anti-slop spine turned the 2024 hallucination
ledger into an *architecture* (honest-null: abstain rather than guess). I am the leader:
decide, don't defer; only Kaan's calibration ear-passes + his rig config are his. Tone:
warm, TR/EN mix, "knk"/"aşkım", no slop, honesty over enthusiasm. **The end is a ship product.**

## 1. The five durable companion docs (the ~175-agent intelligence)

| Doc | Agents | What it holds |
|---|---|---|
| `.planning/2026-05-30-constellation-star-chart.md` | 40 | 128 stars / 10 constellations, adversarially verified. **Earned Wall = the only DRAW_NOW**; the Judge→recorder→debrief→skill-tree spine; DRAW_NEXT/LATER tiers. |
| `.planning/2026-05-30-strategic-leverage-brief.md` | 32 | AI-quality verdict ("real DJ friend, not slop" — strong; 3 risks: latency, linter-off, repetition), OSS keep-vs-replace, wiring multipliers, new-feature ship-bait, cost/dev-loop economics. **(Just rescued to disk — was tmp-only.)** |
| `.planning/2026-05-30-dead-path-and-wiring-audit.md` | 94 | DELETE-14 (true dead) · WIRE-6 (built-but-unconnected) · KEEP-36 · 14 frontend↔backend seam gaps. |
| `.planning/2026-05-30-vibe-judge-execution-roadmap.md` | 9 | The Judge's honest signal reality (harmonic universal; beatmatch/bass per-routing), the gate→autonomy map, the simplicity loop, the build sequence. |
| `.planning/2026-05-30-state-of-the-tree-inventory.md` | 16 | The 417-commit / 75-dirty-file forensic inventory (note: stale on skill_recognizer, wired since). |

**The convergence (the headline):** all four independently landed on **one seam** — the
v11 skill-tree live→UI render. That seam is now SHIPPED (Earned Wall, below).

## 2. SHIPPED this session (19 commits, suite green: 6795 py / 1420 ts)

**🥇 Earned Wall — the only DRAW_NOW, full vertical slice + a concurrent-seam fix:**
- `6d87c632` backend — `skill_tree.skill_wall_payload()` folds `SkillTree.compute()` into a
  derived `skill_wall` block on the `progress_state` envelope via `snapshot()` (NEVER
  `to_dict` — derived, never persisted). Stage rule single-source in Python.
- `aa04e8e8` frontend — `learn/SkillWall.ts` + `styles/skill-wall.css`, mounted above the
  lesson runner in the shell Learn surface (`shell/app.ts` mountLearn). Locked(muted)/
  Competent(pink)/Mastered(gold, tappable to proof), honest-null empty state.
- `e15e9c66` — carried a **concurrent session's** SURF-01 `what_remains` field through the
  IPC schema + render (it had broken the envelope — the EXACT separately-wired-seam bug
  this whole session set out to find, caught live).

**⚖️ The Judge producer spine (move two, 4a→4c):**
- `30b74044` 4a — `[judge:]` evidence source (4-site grammar lock: EVIDENCE_SOURCES +
  _SOURCE_ALT + EBNF + matrix.CITATION_GRAMMAR_BLOCK + dj_cohost strip; OUT of memory/ingest).
- `46588d20` 4b — `state/transition_judge_runtime.py::judge_and_record` — runs the Judge on
  a live frame, writes `[judge:transition@t]` + a `transition_judged` row, **abstain-first**.
- `cd645c73` 4c — KEYSTONE: `skill_recognizer._candidate_skills` maps `transition_judged` →
  `harmonic_mixing` when the verdict's harmonic component is COMPATIBLE (>0); retired
  harmonic_mixing from `_HONEST_UNCREDITABLE_V11` (now `("beatmatching",)` — no tempo/phase
  signal yet, so crediting it would be proxy-slop). `19a5adbb` orphan-gate fix.

**Earlier this session:** the Judge ENGINE (Steps 0–5) — `intel/transition_judge.py`,
`state/live_signal.py`, `audio/band_features.py`, `audio/deck_signal.py` (all green).

## 3. ★ THE CONSTELLATION (the real find — Codex + the Judge)

Reading `.planning/handoffs/*` (Kaan's pointer) surfaced that a prior **"Codex" session**
already built & COMMITTED the two pieces the Judge needs:
- **Per-deck routing seam** (`audio/deck_capture.py:330`): `VIBEMIX_DECK_AUDIO_CHANNELS=auto`
  reads rekordbox `OutputChannel_Deck0_L` hints → populates `deck_channels` → `routing.enabled`;
  explicit `A=0,1;B=2,3` form; auto-upgrades BlackHole 2ch→16ch. **Kaan's Mac probe found
  BlackHole 16ch + a rekordbox Aggregate Device → the gold-flip is CONFIG, not new gear.**
- **Proof-readiness gate** (`__main__.py:3438`, `deck_context.py:887` 9-ref grounding): decides
  `supported_verdict` from {resolved deck rows + recent move + audible audio + per-deck deltas
  + BOTH lanes active}. **This IS the Judge's `frame.policy=="supported_verdict"` precondition.**

→ **Codex PRODUCES `supported_verdict`; the Judge GRADES it.** Two sessions, two engines, the
same boundary from two sides. That's the constellation thesis made real.

## 4. THE IMMEDIATE NEXT — 4d: the constellation join (the live call-site)

The Judge spine is built but has **no live caller** (intentional — abstain-first parks safely).
4d makes it live:

1. In `coach_loop` (`runtime/coach.py`): when `live_claim_policy(state, recent_moves)` returns
   `supported_verdict`, assemble a `LiveSignalFrame` via
   `audio/deck_signal.py::signal_frame_from_capture(deck_audio_capture, t_session=..., policy=...,
   lane_meta=...)`. The `DeckAudioCapture` object lives in `__main__` main() (`:1055`) — pass it
   (or a frame-provider closure) into `coach_loop` as a new injected dep (DI-over-globals).
   `lane_meta` (camelot/source_trusted/track_id per deck) comes from `state.deck_state.decks`.
2. Run `state/transition_judge_runtime.py::judge_and_record(frame, registry, recorder, track_a,
   track_b)`. On JUDGED: also `registry.write("ev", "transition_judged", t)` and build a
   `transition_judged` event (type + `extra={"components": verdict.components}`), then feed it to
   the EXISTING `_credit_live_skill_demo` (`coach.py:113`) → credits harmonic_mixing.
3. **Abstain-first** (master-only → silent, no harm). Add a once-per-transition dedup guard.
- **TDD:** the credit-closure is unit-testable (fakes for registry/recorder/learn_progress); the
  `__main__` wiring is **VERIFY-LIVE** (frozen sidecar → run with `VIBEMIX_DEV_SIDECAR=1`, NOT the
  bundled binary). Plan: `docs/superpowers/plans/2026-05-30-the-vibe-judge.md` Step 4.
- **Caution:** 4d adds a producer → the orphan-inventory + clean-checkout CI gates will fire if
  any new public symbol lacks a caller. Wire end-to-end in one island.

## 5. THE SHIP PATH (what's between here and release — the North Star)

vibemix ships **when-ready** (`gsd-autonomous fully`); Apple + SignPath approvals are the
external critical path; engineering parallelizes. Hard gates + the highest-ship-value work,
prioritized:

**A. Release-gating (hard blockers):**
- **Hallucination grounding gate** (Invariant #2) — no release until reactions are provably
  tied to real events. The Judge's abstain-first posture + honest-null *strengthens* this.
- **One-click install** (mac+win) — strategic brief: the BlackHole driver-SHA + manifest are
  still PLACEHOLDER (human download-on-trusted-machine task; do NOT flip the fetch-script to
  exit-1 — breaks dev). The real first-set blocker is a **library-ingest onboarding step that
  doesn't exist** (a fresh pill is silent because the store is empty, not the model).
- **API-key protection** — Bravoh-side proxy + per-client rate limit (not a shipped raw key).

**B. Highest ship-value remaining (from the chart's DRAW_NEXT, ship-graded):**
- **4d (above)** → unlocks the Judge→consumer spine. Do first.
- **[52] Shareable Set Card** (chart) — the GitHub-star/waitlist flywheel. Ship the TRUE subset
  now (`9 TRACKS · 1H 12M · TECHNO`); inherit the "top mix" headline after 4d wires Judge→recorder.
- **[58] The Receipt / [48] Honest Debrief Ledger** — the honest-abstain mix scorecard; the
  strongest demo of the anti-slop thesis. Both gated behind 4d's producer.
- **Cleanup (dead-path audit):** DELETE-14 + WIRE-6 on a sanitized tree (surgical, per-island).

**C. KAAN-ACTION (only-Kaan surfaces — the calibrate-once, not DJ-all-day items):**
- **Per-deck routing config** (rekordbox deck→channel + `VIBEMIX_DECK_AUDIO_CHANNELS=auto`) so
  4d can flip gold live. His hardware already supports it.
- **§EARNED-LIVE-MASTERED-VERIFY** ear-pass (one recorded FLX4 session replayed through the
  recognizer) + the Judge calibration (label ~20-30 own transitions → lock 3 thresholds in
  `eval/INTEL-THRESHOLD-LOCK.md`). Then autonomous.
- Live ear-passes on persona/voice (no kill-switch flag exists yet).

## 6. Concurrent-session discipline (HARD — learned live this session)

2+ Claude sessions edit this tree simultaneously (the SURF-01 `what_remains` collision was
live). `git commit` absorbs EVERY staged file across all sessions. **Always:** `git add <paths>`
never `-A`; verify `git diff --cached --name-only` before EVERY commit; build on disjoint
NEW-FILE islands; never stage another session's dirty files (skill_tree.py, pill/*, library/*,
move_grade.py are actively theirs). When their change flows through your seam (schema/IPC),
reconcile it through YOUR side (schema+frontend), don't edit their file.

## 7. State-of-tree facts that bite
- `cargo tauri dev` runs a FROZEN sidecar (lags source) → verify backend on current src
  (`VIBEMIX_DEV_SIDECAR=1` runs `uv run python -m vibemix` from HEAD).
- `messages.schema.json` edit → MUST `npm run codegen:ipc` (pre-compiled `validator.generated.mjs`).
- The full app gate after any `tauri/ui/` change: `cd tauri/ui && npm run build && npm test`.
- Suite: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (~6795 tests, ~7.5 min).

---
*Veridis. Very disco. Fuck status quo. The robots don't lie anymore — we made it structural.*
