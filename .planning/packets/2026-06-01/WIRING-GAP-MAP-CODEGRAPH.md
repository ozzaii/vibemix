# WIRING-GAP-MAP-CODEGRAPH.md — orphan-pair / dead-export / not-found synthesis

> The wiring synthesizer's union of three analyst passes (orphan-pairs · dead-exports · not-found-audit), **re-verified live against HEAD `b98dd885`** (the tree has moved 3 commits past the packets you were told to read). Every row is grep / codegraph / `ls` grounded at this HEAD. READ-ONLY — zero product files touched.
>
> Provenance HEADs: GOLD-WIRING-MAP `ce909a87`, FEATURE-STATE `ed081570`, analyst inputs `ed081570`/`b98dd885`. **Re-pin everything to `b98dd885` before routing.** The single commit that invalidates the read-first docs is `970e165b feat(intel): license grounded eq move effects`.

---

## 1. ONE-SCREEN VERDICT ON STRUCTURAL HEALTH

The codebase is structurally **rich and honest, not thin** — the intelligence is clean-room-built and broadly tested; the disease is **last-mile wiring**, not absent capability. But the two planning docs you were handed to act on (`GOLD-WIRING-MAP` Card 1, `FEATURE-STATE` §"PLANNED-ONLY") are **stale on their own #1 item**: the EQ-move physics keystone they call "the single highest-leverage first move / NOT-FOUND" was **built and fully wired** in `970e165b`. Verified at HEAD: `intel/eq_move_model.py` EXISTS (8.0k), imported at `state/deck_context.py:16`, called at `:1873`, and reaches the live guard `_licensed_move_effect` at `deck_context.py:2519` (`apply_live_claim_guard`). **Any plan still listing "build eq_move_model" as task #1 is chasing a ghost — re-baseline first.**

Structural health is **B+**. The orphan pattern is consistent and diagnosable: **Codex landed the pure graders/scorers (the leaf engines) but not the live producers that drive them.** You have graders without emitters (`grade_beatmatch`, `grade_cue_placement`), scorers without coach-loop call-sites (`score_transition`, `grade_move`), and a planner running only in a demo (`calculate_transition`). Exactly **2 modules are pure dead weight** (`runtime/demo_mode.py`, `learn/cue_placement_judge.py`). One dead grammar slot (`[tend:]`) is fail-safe but dishonest. And one **release-gating kill-shot stands untouched**: MOSS weights are neither bundled in the spec nor hostable by default → a fresh machine boots MUTE. The good news: the cheapest high-leverage wires (the two coach-orphan scorers) are pure, tested, and ~0.5d each.

---

## 2. ORPHAN PAIRS — consumer ↔ producer broken wiring

| Consumer | Producer | Which is missing | Codegraph / grep proof @ `b98dd885` | The one wire |
|---|---|---|---|---|
| `skill_recognizer.py:154` `if ev_type=="BEATMATCH_GRADED"` (credits beatmatching mastery; reached live via `runtime/coach.py:177` `recognize`) | **none** — no `Event("BEATMATCH_GRADED")` / `registry.write(…,"BEATMATCH_GRADED")` anywhere | **PRODUCER MISSING** | `grep BEATMATCH_GRADED src/**.py` = only docstrings + the consumer branch (`beatmatch_judge.py:146/151/153`, `skill_recognizer.py:100/103/154`, `skill_tree.py:147`). Zero emitter. | Build `learn/practice_loop.py` (NOT-FOUND, confirmed `ls`) → drive `MiniDeck` → `grade_beatmatch` → `registry.write(("ev","BEATMATCH_GRADED",t))` + `Event(...)`. ★ headline orphan |
| `_licensed_move_effect` move→sound license (`deck_context.py:1847`), reached by `apply_live_claim_guard:2519` | `intel/eq_move_model.py::predicted_band_gains/canonical_eq_move` | **NEITHER — both present + wired** | import `deck_context.py:16`; call `:1873`; guard call `:2519`. Landed `970e165b`. | **ALREADY WIRED.** Open work = LIVE rig verify only (the `drive-vibemix` narrator→coach capture), NOT a build. |
| `[tend:<fact>]` offered to live model (`matrix.py:126`); in grammar `evidence_registry.py:184`; one of 12 `EVIDENCE_SOURCES` `:130` | **none** — no `registry.write(…,"tend",…)` | **PRODUCER MISSING** | `grep registry.write … tend` = empty (verified). `tend` is existence-only (`citation_linter.py`) so every `[tend:…]` the model emits is **always stripped**. | Either register `tend` atoms at profile-build (`profile/builder.py` → `("tend",fact,t)`) OR cut the dead slot from `matrix.py:126` + `EVIDENCE_SOURCES`. Fail-safe today, dishonest grammar. |
| `score_transition` (transition quality scorer) | `intel/transition_scorer.py::score_transition` | **CONSUMER MISSING in coach** | live callers = `library/next_suggestion.py`, `library/toolset.py` only (verified). `grep score_transition src/vibemix/runtime src/vibemix/state/coach.py src/vibemix/agent` = **empty**. | Coach-loop call-site on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY` → `task_for_event`. ★ cheapest high-leverage |
| `grade_move` (move-quality grade) | `intel/move_grade.py::grade_move` | **CONSUMER MISSING in Python coach** | grep `grade_move` non-test in `src/vibemix` = **empty** (only TS caller `tauri/ui/src/pill/index.ts:1955 syncMoveGrade`). | If the grade should inform what the co-host *says*: add a coach consumer. Else it's UI-only by design — DECIDE intent. |
| `calculate_transition` ("16 bars to bring B in") | `state/transition_clock.py::calculate_transition` | **CONSUMER = DEMO ONLY** | callers = `runtime/automix_demo.py` (demo) + self-ref in `transition_clock.py` (verified). | Coach-loop call-site; depends on live beatgrid (same gap as beatmatch). |
| `grade_cue_placement` | `learn/cue_placement_judge.py::grade_cue_placement` | **BOTH ENDS MISSING** | grep non-test callers = **empty**; no producer event, no consumer. Built+tested grader, fully unplugged. | Needs a live cue-placement event producer AND a consumer — or delete (see §3). |

---

## 3. DEAD vs ORPHANED-GOLD exports

| Symbol / module | Live callers @ `b98dd885` | Verdict | Evidence |
|---|---|---|---|
| `runtime/demo_mode.py` (`DEMO_SEQUENCE`, `load_sequence`) | **0** — `ls` = **NOT-FOUND (deleted)** | **CLOSED ✓ (already deleted)** | Input 1/2 flagged for delete; HEAD `b98dd885` confirms gone. |
| `debrief/ear_test_capture.py` | **0** — `ls` = NOT-FOUND (deleted `ce909a87`) | **CLOSED ✓ (already deleted)** | live path is Rust `ear_test_cmds.rs`. |
| `learn/cue_placement_judge.py::grade_cue_placement` | **0 non-test** (verified grep) | **DELETE or WIRE** — no producer, no consumer | EXISTS (`ls` ✓), imports `BeatGrid`, tested only. Same shape as `grade_beatmatch`. |
| `intel/transition_scorer.py::score_transition` | live in pill+Viber (`next_suggestion`, `toolset`); **0 in coach** | **WIRE to coach (ORPHANED-GOLD)** | pure, heavily tested. GOLD Card 4. ~0.5d. |
| `intel/move_grade.py::grade_move` | TS pill only (`pill/index.ts:1955`); **0 Python** | **WIRE or confirm UI-only (ORPHANED-GOLD)** | no Python coach caller. |
| `state/transition_clock.py::calculate_transition` | demo only (`automix_demo.py`) | **WIRE to coach (ORPHANED-to-demo)** | GOLD Card 6. needs beatgrid. |
| `learn/beatmatch_judge.py::grade_beatmatch` | **0 src** (all 6 callers in `tests/`) | **WIRE+BUILD producer (ORPHANED-GOLD, the moat)** | consumer `skill_recognizer.py:154` waits; own docstring `beatmatch_judge.py:151` admits "a future owned-deck practice loop must fire BEATMATCH_GRADED". |
| `audio/grid.py::BeatGrid` + `.from_anlz` | only `beatmatch_judge.py:21` + `cue_placement_judge.py:15` (both orphan graders) | **ORPHANED-GOLD (rides the beatmatch wire)** | **NOTE:** the live ingest path uses a *different* class `library/anlz_ingest.py::AnlzBeatGrid` + `anchors_from_anlz` — do NOT conflate. `BeatGrid` itself reaches no live path. (Corrects an interim grep that matched the wrong `from_anlz`.) |
| `intel/gold_labels/gold_sampling/gold_validation`, `taste_model.score_taste` | `scripts/eval/*` + tests only | **KEEP (eval-only, correct by design)** | ships in DMG via `collect_submodules` — trivial bloat, not a bug. (`load_taste_model` IS live — `dj_cohost.py:891`; only `score_taste` is eval-only.) |
| `intel/eq_move_model.py` `predicted_band_gains`/`canonical_eq_move` | `deck_context.py:16/1873`, guard `:2519` | **LIVE — do NOT touch (stale docs say BUILD)** | codegraph false-negative "6 callers all tests" = import-symbol edge it didn't record; grep is ground truth. |
| `intel/judge_voice.py::verdict_evidence_line` | `runtime/coach.py:327 _run_live_judge` | **LIVE — stale MEMORY note "#1 NEXT build it" is wrong** | already wired. |

---

## 4. NOT-FOUND LEDGER — packet-referenced symbols vs HEAD `b98dd885`

| Wanted symbol | Packet | Exists? | Wired? |
|---|---|---|---|
| `intel/eq_move_model.py` `predicted_band_gains` | GOLD Card 1 / EQ-keystone / FEATURE PLANNED-ONLY | **EXISTS** `eq_move_model.py` (`970e165b`) | **WIRED** → guard `deck_context.py:2519`, agent `dj_cohost.py:2964` |
| `canonical_eq_move` | EQ-keystone | **EXISTS** `:79` | **WIRED** `deck_context.py:1870` |
| `state/mixer_physics.py` | EQ-keystone fast-follow | **NOT-FOUND** (verified `ls`) | — deferred sibling |
| `transition_scorer.score_transition` → coach | GOLD Card 4 | EXISTS | **STILL ORPHANED** (library/Viber only) |
| `transition_clock.calculate_transition` → coach | GOLD Card 6 | EXISTS | **STILL ORPHANED to demo** |
| `learn/beatmatch_judge.grade_beatmatch` → live | GOLD Card 5 / goldmine H1 | EXISTS `:83` | **ORPHANED** (test-only callers) |
| `BEATMATCH_GRADED` emitter | FEATURE ABSENT / goldmine H1 | **NOT-FOUND** | consumer waits |
| `learn/practice_loop.py` / `practice_runtime.py` (H1 producer) | goldmine H1 / FEATURE PLANNED-ONLY | **NOT-FOUND** (verified `ls`) | — the keystone producer |
| `MiniDeck.seek()` | goldmine H1 step-1 | **NOT-FOUND** | — |
| `BeatGrid.from_anlz` (H2) | goldmine H2 | **EXISTS** `audio/grid.py:39` — goldmine map STALE | **ORPHANED** (orphan graders only) |
| `cue_placement_judge.grade_cue_placement` (H3) | goldmine H3 | **EXISTS** — goldmine map STALE | **ORPHANED** (test-only) |
| `sync_adjustment` (H4), `grade_blend` (H6), `phase_align` (H7), `library/detect_key.py` (H8) | goldmine H4/H6/H7/H8 | **NOT-FOUND** | — correctly still planned |
| `audio/lufs.py` (LUFS receipt, GOLD Card 2) | GOLD Card 2 | **NOT-FOUND** (verified `ls`) — only `library/energy.py::_loudness_dbfs` exists, library-only | — Card 2 open |
| `audio/xfade.py` → guard | LAND_QUEUE H2 | **EXISTS** | **NOT WIRED** into `deck_context.py` (the `xfader` refs there are the old 0-127 label path, not the equal-power engine) |
| `runtime/demo_mode.py` (S3) | LAND_QUEUE S3 | **NOT-FOUND** (deleted) | **CLOSED ✓** |
| `debrief/ear_test_capture.py` (S6) | LAND_QUEUE S6 | **NOT-FOUND** (deleted) | **CLOSED ✓** |
| `NOTICE`/`THIRD_PARTY_LICENSES.md` (S2) | LAND_QUEUE S2 | **EXISTS** | **CLOSED ✓** |
| dead `ipc.library.*` ws types (S5) | LAND_QUEUE S5 | dead ones **GONE**; only 5 live types remain | **CLOSED ✓** |
| MOSS weights in `vibemix-core.macos.spec` datas | RED-TEAM ① / B-1 | **NOT-FOUND** — `grep moss-tts spec` empty; `moss_model_installable()` (`library/model_assets.py:573`) returns True **only if** `VIBEMIX_MOSS_TTS_ARCHIVE_URL` env set; no URL/SHA pinned, nothing bundled | **OPEN — KILL-SHOT STANDS.** Fresh machine = mute. |

---

## 5. RANKED WIRING BACKLOG — cheapest high-leverage first

| # | Pair | Wire | Class | Effort | Leverage |
|---|---|---|---|---|---|
| 0 | (re-baseline) | re-pin all packets to `b98dd885`; re-tag `eq_move_model` EXISTS+WIRED; **verify the keystone runs correctly on a real rig** (`drive-vibemix`), do NOT rebuild | VERIFY | — | unblocks routing |
| 1 | `score_transition` ↔ no coach consumer | coach-loop call-site on `TRACK_CHANGE`/`TRANSITION_OPPORTUNITY` → `task_for_event` | WIRE | ~0.5d | ★★ pure+tested, live transition reads |
| 2 | `[tend:]` grammar ↔ no producer | register `tend` atoms at profile-build OR cut the dead slot | WIRE-or-CUT | ~5min–0.5d | ★ honesty cleanup / small personalization |
| 3 | Vibe Judge abstains on master-only | single-stream mix inference (GOLD Card 3) — keystone dep now BUILT, so closer than docs think | FINISH | ~1d | ★★ makes the one live engine speak on the common rig |
| 4 | `BEATMATCH_GRADED` consumer ↔ no emitter | build `learn/practice_loop.py` (MiniDeck→grade_beatmatch→Event+registry write) — also lights `BeatGrid`, `xfade`, `cue_placement_judge`, `calculate_transition` cluster | BUILD | ~1.5d (grid feed is the cost) | ★★★ unlocks Mastered beatmatching + the whole own-player cluster |
| 5 | `grade_move` ↔ pill-only | confirm intent: UI-only (fine) or add coach consumer | DECISION | low | low |
| 6 | `calculate_transition` ↔ demo-only | coach-loop call-site (needs beatgrid, rides #4) | WIRE+dep | low-med | "16 bars to bring B in" |
| — | **MOSS bundle/host (kill-shot ①)** | pin `VIBEMIX_MOSS_TTS_ARCHIVE_URL`+SHA or bundle weights in spec datas | RELEASE-GATE | external | ★★★★ blocks "a stranger hears it" — NOT a wire, a packaging/ops decision |

**Note:** #4 (the H1 producer) is the one BUILD that cascades — it is the single producer that lights `grade_beatmatch`, `BeatGrid`, `xfade`, `cue_placement_judge`, and `calculate_transition` all at once. Everything else is a call-site, a 5-min cut, or an external ops gate.
