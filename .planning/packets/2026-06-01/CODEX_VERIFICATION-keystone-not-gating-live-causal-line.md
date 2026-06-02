# CODEX_VERIFICATION — Keystone wired but does NOT gate the live causal line

> Status: VERIFICATION packet (read-only swarm → Codex). HEAD `e49b2f63`. Rig: FLX4 + Rekordbox dev-source, mode=coach, master-only single-deck. Live capture 2026-06-02, Kaan's rig.
> Gate before any fix lands: **vibemix-grounding-review** (§7).

---

## 1. One-line verdict

**The EQ-move-physics keystone WORKS LIVE on the master-only rig — but only INTERMITTENTLY, and the cold window is the bug.** Corrected against fuller live data (§2b): the keystone DOES reach the prompt and DOES license (`rule=move_effect_prediction_and_measurement_agree`, captures 0026/0027) and refuse (`rule=dsp_delta_not_causal_proof`, 0019/0028) on the master-only single-deck rig. It is **NOT inert.** The defect is a **timing/sampling gap**: its measured arm (`effect_signals` / `audio_delta`) is a *tick-to-tick* diff with a 10% floor (`deck_context.py:1858` / `refresh.py:1078` / `deltas.py:84`), so the keystone fires only when a refresh tick happens to catch the move's band-change mid-flight above the floor; when the move is already **settled by reaction time** (the cold/early window — capture 0002) the delta is `[]`, the double-gate at `deck_context.py:2688` abstains into a no-op, and a direction-wrong causal claim ("kick got thin" on a low-EQ BOOST) emits ungated at `citation_count=1`. Two downstream phrasing nets (`_MOVE_EFFECT_CAUSAL_VERDICT_RE`, `_LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE`) have lexical holes that let the cold-window claim through. **The fix is to make the measurement move-aligned (RANK 1) so the keystone sees every move, not only the ones a tick catches — plus the phrasing-independent safety net (RANK 2).** The keystone source + physics are sound and PROVEN firing.

---

## 2. The LIVE evidence

Event PHASE, response `0002_080213`, `citation_count=1`, `action=emit`. The co-host spoke:

> "The kick drum got thin and boomy when you `[midi:A_low:_flat_to_boost_small_twist@203.2]` pushed that low EQ past flat; next time, keep it at center to preserve the weight of that vocal track."

The ONLY citation that resolved: `[midi:A_low:_flat_to_boost_small_twist@203.2]` — a **MOVE-HAPPENED** midi atom, not a move-CAUSED atom.

The prompt (`invocations/0002_080213_PHASE/prompt.txt`) carried:
- `hearing[rms=0.161 sub=0.70 low=0.21 mid=0.08 high=0.01 bpm=103]` — sub is STRONG.
- `recent_moves[8s]: A_low killed->deep-cut->cut->flat->boost` — a full low-EQ sweep, ~6s prior.
- `deck_audio_context: source=global_mix isolated_decks=false routing=A=dominant(0.70) B=muted(0.00) support=single_deck_A ; deck_audio_parts=0`.
- **`audio_delta: []` (EMPTY). NO `move_effect_context[...]`. NO `rule=move_effect_prediction_and_measurement_agree`. NO `rule=dsp_delta_not_causal_proof`.** The keystone packet was omitted entirely — not even the refuse form.

**The direction-wrong tell:** Kaan pushed low **flat → BOOST** (more lows); measured `sub=0.70` (strong). The model said the kick "got **THIN**." A boost THICKENS; thin is the opposite direction. This is the exact plausible-but-direction-wrong causal claim the keystone's measured double-gate exists to catch or correct — emitted instead with one move-existence citation.

**The anti-slop gate DID work elsewhere the same session** (so this is a hole, not a dead system): a later MIX_MOVE causal line (resp `0004`) was `action=strip` → empty; a describe-only HEARTBEAT (resp `0003`) stayed descriptive at `count=0`.

## 2b. The LICENSING proof — the keystone fires live (corrects the original "inert" read)

Later in the SAME session, with `audio_delta` populated, the keystone licensed and refused correctly on the master-only rig. Per-prompt `move_effect_context` audit:

| Turn | event | `move_effect_context` | `rule` |
|---|---|---|---|
| 0019 | MIX_MOVE | present | `dsp_delta_not_causal_proof` (REFUSE) |
| 0026 | HEARTBEAT | present | **`move_effect_prediction_and_measurement_agree` (LICENSE)** |
| 0027 | PHASE | present | **`move_effect_prediction_and_measurement_agree` (LICENSE)** |
| 0028 | HEARTBEAT | present | `dsp_delta_not_causal_proof` (REFUSE) |

- **0026 (LICENSED + EMITTED, `citation_count=2`):** prompt carried `move_effect_context[window=recent_moves moves=3 deltas=sub energy fell 33% (clear); low energy rose 10%; mid energy rose 13%; onset density fell 11% **license=high_boost:mid:pred_rose_4db:measured_rose rule=move_effect_prediction_and_measurement_agree**]`. The co-host spoke a **grounded** causal coaching line: *"You pushed the low, mid, and high EQs on Deck B all into a boost `[midi:B_low:...][midi:B_hi:...]` which pushed the signal right to the edge of redlining—keep those EQs flat next time to prevent distorting."* Narrator→coach, licensed by predicted(+4 dB)∧measured(rose) agreement. **This is the keystone working as designed on the master-only rig.**
- **0027 (LICENSED in prompt, but co-host ABSTAINED `action=strip`):** keystone licensed `license=filter_lp:high:pred_fell_7db:measured_fell`, yet a HIGHER guard (`LIVE_AUDIO_SOURCE_DETAIL_HELD_REPLY` — deck source unresolved) held the reply: *"I only have a broad listener read from the audio here, not source-level proof."* Layered humility — no over-claim even with a license.

So the measured arm DOES populate and the keystone DOES gate on master-only — **intermittently**, exactly when a refresh tick catches the per-tick band-change above the 10% floor (0026's `sub fell 33%` clears it; 0002's settled sweep does not). The bug is the **cold/settled window** (0002), not structural inertness.

---

## 3. ROOT CAUSE — exact file:line chain

### 3a. The operative gate ran on PHASE and abstained — `deck_context.py:2688`

The reaction-time guard `apply_live_claim_guard` is invoked on the GENERATED text regardless of event type: `agent/dj_cohost.py:2964`, with `audio_delta_items = render_audio_delta_items(live_claim_state)` computed at `agent/dj_cohost.py:2339` (returned `[]` because state's `audio_delta` was empty). It ran. The move-effect fork:

```python
# src/vibemix/state/deck_context.py:2688
effect_claim = bool(
    moves
    and effect_signals          # ← [] on this rig → whole expression False
    and ((_MOVE_EFFECT_CONTROL_RE & _MOVE_EFFECT_CAUSAL_VERDICT_RE) or _MOVE_EFFECT_BARE_VERDICT_RE)
)
```

`effect_signals` (`deck_context.py:2653`) `= effect_deltas + capture_effect_deltas`. Both empty:
- `effect_deltas = render_audio_delta_items(state)` = `[]` (master-level `audio_delta` empty — see 3b).
- `capture_effect_deltas = _deck_audio_delta_text_items(audio_capture_context)` = `[]` (`deck_audio_parts=0`, per-deck capture off — see 3b).

→ `effect_claim = False` → the entire `_licensed_move_effect` license branch (`deck_context.py:2700-2717`, call at `:2701`) AND the `LIVE_MOVE_EFFECT_HELD_REPLY` refuse branch (`deck_context.py:2723-2728`) are **skipped before any regex runs**. The double-gate degenerates to a no-op: with no measured delta there is nothing to gate against, so it abstains silently rather than refusing. This is the same condition that makes `render_move_effect_context` (`deck_context.py:2371`) early-return `None` at `deck_context.py:2390` (`if not deltas and not deck_delta and not deck_window: return None`) — which is why the PHASE prompt had no `move_effect_context` block and no `rule=...` line at all.

### 3b. Why the measured arm is empty — two delta channels, two distinct failures

**Channel 1 — per-deck `deck_audio_*` (`deck_audio_parts=0`): STRUCTURALLY dead on master-only.** `audio/deck_signal.py:43`: `buf = capture.buffers.get(side) if routing_enabled else None`. On a master-only rig `routing_enabled` is False by construction (`deck_signal.py:36-39`, `effective_enabled()`); `buf=None → bands=None`, no per-lane `band_energy_ratios` is ever computed (`band_features.py:30`). This is deliberate and test-pinned: `tests/audio/test_deck_signal.py:99 test_e2e_master_only_rig_abstains` (`routing(enabled=False)` → `verdict_state=="abstained"`, `abstain_reason=="routing_disabled"`), and the `coach.py:351-355` docstring states the master-only abstain is "the honest-null default, not a bug." Downstream, `_deck_audio_delta_text_items` (`deck_context.py:2040`) and `_move_deck_audio_delta_token` (`deck_context.py:2413`) both short-circuit to empty on `not deck_audio_capture_enabled`. The keystone's intended per-deck post-move band delta is unreachable on this rig.

**Channel 2 — master-level `audio_delta` (printed `[]`): a tick-window mismatch, empty by design for a slow move.** This channel is NOT routing-gated and DOES run on master-only (`refresh.py:1026-1027`, `use_cached=False`). But its diff window is **one refresh tick**, not the ~6s move window: `render_audio_delta_items` (`deck_context.py:1828`) returns cached `state.audio_delta`, and `render_delta(label, cur, prev.get(key), floor=DELTA_FLOOR)` (`deck_context.py:1858`) diffs current `state.bands` against `state.prev_perceive` — which `refresh.py:1078-1088` writes as the LAST action of EACH tick (the single-writer "next tick diffs current-vs-this" comment). `render_delta` abstains unless the per-tick relative change clears `DELTA_FLOOR = 0.10` (`deltas.py:24, 81-85`). A flat→boost sweep over ~6s, once settled, leaves current ≈ prior-tick bands → every band line abstains → `audio_delta=[]`, even though cumulative `sub` ended strong at 0.70. **There is no move-aligned pre/post band-delta window on the master path** — the "post-move band delta" the keystone contract assumes simply is not computed for master-only audio anywhere.

### 3c. The causal-without-license gap — move-existence citation + two lexical net holes

The `[midi:...]` citation resolves on timestamp tolerance ALONE — it proves only that the move happened, never that it caused the sound. `coach/citation_linter.py:51` puts `midi` in `_TIME_KEYED_SOURCES`; `_validate_atom` (`citation_linter.py:174`, midi branch `:198-208`) does `valid = any(abs(t_obs - t_target) <= tol ...)` and nothing else — no causal predicate, no sentence inspection. With that one atom resolving and no others, `LintResult(valid=True)` (`citation_linter.py:160`) → `citation_count=1, action=emit`.

The two downstream nets that COULD have caught the texture claim both miss this phrasing (verified by running the actual regexes against the live text):
- **Move-effect verdict regex misses the construction.** `_MOVE_EFFECT_CAUSAL_VERDICT_RE` (`deck_context.py:128`) and `_MOVE_EFFECT_BARE_VERDICT_RE` return `None` on "got thin and boomy **when you** pushed that low EQ" — a temporal-causal juxtaposition with none of the banned verdict verbs. (Even had this branch been reached with non-empty signals, the regex miss means it would NOT have fired — so re-routing PHASE→MIX_MOVE does NOT fix it.)
- **Source-detail catch-all misses the adjectives.** `_unsupported_audio_source_detail_reason` (`deck_context.py:2843`) requires BOTH a noun match (`_LIVE_AUDIO_SOURCE_DETAIL_NOUN_RE` matches `kick drum`, `vocal`) AND a claim-verb match (`_LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE`, `deck_context.py:160`). That claim lexicon lacks **"thin", "boomy", "weight", "preserve"** → `.search(text)` returns `None` → returns `None` at `deck_context.py:2855`, the held-reply (`:2730-2738`) never fires.

The system prompt is actually correct on policy — `prompts/matrix.py:345` forbids "fixed, cleaned, tightened, opened, or caused"; `:441`/`:522` repeat OBSERVED→IMPACT→PRESCRIBE-needs-proof; `:327` says audio is not proof a move caused the sound — but the prohibition is verb-specific and does not cover the "X got Y **when you** did Z" temporal-causal pattern. The result-boundary guard exists precisely to catch failures without depending on phrasing (`deck_context.py:2636` docstring), but its catching branches were gated out per 3a.

### 3d. STATE-BLIND move reasoning — the keystone sees the MOVE delta, never the deck STATE (Kaan, live 2026-06-02)

Distinct from the cold-window timing gap (§3a–b): even when the keystone LICENSES, it reasons about the move's *direction of change* and is blind to the *absolute* deck state and absolute band energy. Live proof from the licensed turn 0026:

- `intel/eq_move_model.py:46` — `predicted_band_gains(move: str, fs: int)` takes ONLY the move label + sample rate. No absolute EQ knob position, no current band energy, no track baseline. It predicts the move's marginal direction from an implied neutral baseline.
- `state/deck_context.py:1892+` `_licensed_move_effect` licenses iff `predicted_direction == measured_direction` (`:37`, `context_token = f"{canonical}:{band}:{pred_token}:measured_{direction}"` `:40`). **Direction-only. No absolute-significance check.**
- Turn 0026 absolute state: deck B `eq_low=79 eq_mid=79 eq_hi=78` (all already ABOVE center 64 — already boosted before the twist); `hearing[rms=0.045 sub=0.14 low=0.55 mid=0.26 high=0.05 bpm=167]` — **rms=0.045 is a quiet moment and absolute high=0.05 is LOW**. The move was a `small twist` on an already-boosted knob.
- The keystone licensed `high_boost:mid:pred_rose:measured_rose` (direction agreed on a tiny +13% tick), and the co-host coached: *"...pushed the signal right to the edge of redlining—keep those EQs flat next time to prevent distorting."* **The absolute reality contradicts the framing:** nothing is redlining at rms=0.045 / high=0.05; the knob was already up, so "you pushed it into a boost" attributes an elevated state to a small twist. The direction-only license passed a significance-wrong, framing-wrong coach line.

**The PRESCRIPTIVE version (Kaan, same session, sharper): the co-host advises moving a band in a direction it is ALREADY at.** It says, in effect, "raise/boost X" (or "keep it flat") on a band whose absolute knob is already boosted (`eq_*≈78` on B) — *"arttır diyor ama yüksekti zaten"* ("it tells me to increase it, but it was already high"). The prescription is direction-blind to the current position: the `mixer_context` absolute tiers (`boost/flat/killed`) ARE in the prompt, but neither the move_effect license nor any guard checks the COACHING ADVICE against them, so the co-host can prescribe a move that the deck state contradicts. Advising "boost the highs" when the high knob already sits at +boost (and absolute `high=0.05` is quiet) is state-blind coaching — the most visible slop to a real DJ, because the advice is actionably wrong.

**The gap (both forms):** move→effect grounding — descriptive AND prescriptive — needs deck-STATE awareness: the absolute knob position (`mixer_context` tiers) AND the absolute band energy (`hearing[...]`), to gate SIGNIFICANCE, FRAMING, and ADVICE-DIRECTION, not just the change-direction. A small twist on an already-boosted knob in a quiet passage is not "edge of redlining," and "boost it more" on an already-boosted band is wrong advice. This is why **deck-move-visible ≠ deck-state-aware** — the keystone wired the MOVE channel but the STATE channel never reaches the move→effect/coaching reasoning.

### Chain summary (decisive line first)
1. `deck_context.py:2688` — gate conditioned on `effect_signals`; empty → license (`:2701`) and refuse (`:2724` `LIVE_MOVE_EFFECT_HELD_REPLY`) both dead.
2. `audio/deck_signal.py:43` — Channel 1 routing-gated off on master-only → `deck_audio_parts=0`.
3. `deck_context.py:1858` + `refresh.py:1078` + `deltas.py:84` — Channel 2 tick-window/floor mismatch → `audio_delta=[]` for a slow settled sweep.
4. `coach/citation_linter.py:198-208` — midi atom = move-happened only, no causal predicate.
5. `deck_context.py:128` / `:160` — verdict + source-detail regexes miss "got thin … when you" / "thin/boomy/weight".
6. `eq_move_model.py:46` + `deck_context.py:1892` (direction-only license) — **state-blind**: the move→effect reasoning never reads the absolute knob position or absolute band energy (both already in the prompt), so even a LICENSED line can be significance-wrong ("redlining" at rms 0.045) and the coaching ADVICE can push a band the way it is already set ("boost it" when already boosted). §3d.

---

## 4. What is CORRECT — do NOT over-fix

- **The anti-slop strip/describe paths work.** Same session, resp `0004` (MIX_MOVE causal) → `action=strip` → empty; resp `0003` (HEARTBEAT describe-only) → `count=0`. The citation-linter strip path is healthy. Do not touch it.
- **The keystone SOURCE is sound.** Imports + call sites are correct: `predicted_band_gains`/`canonical_eq_move` imported `deck_context.py:16`; `_licensed_move_effect` `deck_context.py:1892`; `render_move_effect_context` `deck_context.py:2371`; guard invocation `dj_cohost.py:2964`; live-path guard call `deck_context.py:2519`. `predicted_band_gains` would have computed `low/sub → rose` for `A_low:_flat_to_boost...` and correctly licensed or refused — IF given a measured delta. The physics is not the bug.
- **The master-only abstain is the honest-null default by design** (`coach.py:351-355`, `test_deck_signal.py:99`). Do NOT "fix" Channel 1 by forcing per-deck routing on a master-only rig — that would fabricate isolation that does not exist.
- **The citation linter's move-existence-only semantics for `midi` are correct** for "did this event happen." It is the right tool for the wrong job here — do not bolt causal reasoning into the linter.
- **The system prompt policy (`matrix.py:345/441/522/327`) is correct.** The leak is a guard-coverage hole, not a prompt-policy hole — do not rewrite the persona prompt as the primary fix.

---

## 5. FIX SURFACE for Codex — concrete, ranked

The core defect: **a move-HAPPENED citation must not be allowed to license a move-CAUSED claim, and the gate that should enforce that abstains into a no-op when no measurement exists.** Two complementary directions; #1 is the structural fix, #2 is the safety net that holds even when #1 cannot measure.

**RANK 1 (structural, master-only): supply a move-aligned measured band-delta on the master path so the keystone can LICENSE or REFUSE on a real measurement.**
The keystone is starved because the only delta available is a tick-to-tick diff (`deck_context.py:1858` vs `refresh.py:1078`), which collapses to `[]` for a slow settled sweep. Provide a pre→post band snapshot keyed to the move window (e.g. the ~6s spanned by `recent_moves`/the cited midi timestamp), on the master mix, independent of per-deck routing. Feed that into `effect_signals` (`deck_context.py:2653`) so `effect_claim` at `:2688` becomes True on a real low-kill/boost, then `_licensed_move_effect` (`:2701`) compares `predicted_band_gains` direction vs the measured master-band direction and either emits `rule=move_effect_prediction_and_measurement_agree` (license, direction-checked) or `rule=dsp_delta_not_causal_proof` (refuse via `LIVE_MOVE_EFFECT_HELD_REPLY`). This makes the boost/thin direction error a hard REFUSE on the master-only rig — the rig the keystone was built for. Do NOT reach for Channel 1 (per-deck) — it is correctly off on master-only; the measurement must come from the master mix.

**RANK 2 (safety net, phrasing-independent): suppress LLM move→effect causal attribution when the move-effect license is ABSENT.**
Independent of whether a measurement exists, a sentence that (a) cites a `[midi:...]` move atom AND (b) makes a texture/effect claim about the resulting sound must NOT emit unless an explicit move-effect LICENSE is present. Today the absence of license is silent (no refuse). Close it at the guard: when `moves` is non-empty and the text asserts a sound-effect about the move with no licensed `move_effect` atom, route to the held-reply rather than emit. This requires broadening the catch beyond the current lexical nets:
- Add the temporal-causal pattern ("X got/became Y **when you** Z") to the move-effect verdict matcher (`_MOVE_EFFECT_CAUSAL_VERDICT_RE`, `deck_context.py:128`), and
- Add the texture adjectives **thin, boomy, thick, weight, preserve** (and siblings) to `_LIVE_AUDIO_SOURCE_DETAIL_CLAIM_RE` (`deck_context.py:160`) so a kick/vocal texture claim is caught regardless of event type.
This is the net that holds even when RANK 1 has no measurement to offer — it enforces the cardinal rule (move-existence ≠ move-causation) directly.

**RANK 3 (state-awareness, the §3d gap): ground move→effect SIGNIFICANCE, FRAMING, and ADVICE against the absolute deck state, not just the change-direction.**
The keystone (`predicted_band_gains(move, fs)`, `eq_move_model.py:46`) and the license (`_licensed_move_effect`, `deck_context.py:1892`, direction-only) are state-blind — they never read the absolute knob position or absolute band energy that ARE already in the prompt (`mixer_context` tiers + `hearing[...]`). Two enforcement gaps follow, both LIVE-observed on turn 0026:
- **Significance/framing:** a small twist that agrees in direction gets licensed and coached as "edge of redlining" while absolute `rms=0.045 / high=0.05` (quiet). Gate the move_effect verdict (and any redline/distort framing) on absolute level: a direction-agreeing delta on a band whose absolute energy is low must NOT license a "redlining/too hot" claim. Pass the absolute band energy + the `mixer_context` tier into the move_effect significance check.
- **Prescription:** the coaching ADVICE must be consistent with the current knob tier — do not advise "boost/raise X" when `mixer_context` shows X already at `+boost`, nor "cut X" when already killed. Add an advice-vs-state consistency check (the absolute tiers are already computed for `mixer_context`; reuse them) so a prescription that pushes a band the way it is already set is held or inverted. This is the most DJ-visible slop and the cheapest to gate, because the absolute state is already in hand.

**Do NOT** "fix" by re-routing PHASE→MIX_MOVE (adversarial verdict: the verdict-regex miss means the same line still ships) or by widening `prompts/matrix.py` (policy is already correct; the failure is enforcement coverage). For RANK 3, do NOT just add a prompt instruction "consider the current EQ position" — the leak is enforcement; the absolute-state check must be a guard, not only persona text.

---

## 6. Acceptance

**SRC (offline, deterministic):**
- A constructed master-only MIX_MOVE/PHASE turn with a low-kill on a bass track and a populated move-window master band-delta produces `rule=move_effect_prediction_and_measurement_agree` from `render_move_effect_context` (`deck_context.py:2371`) when predicted (`predicted_band_gains`) and measured directions agree; and `rule=dsp_delta_not_causal_proof` (refuse, `LIVE_MOVE_EFFECT_HELD_REPLY`) when they disagree.
- The exact live text "the kick drum got thin and boomy when you `[midi:A_low:...]` pushed that low EQ" routed through `apply_live_claim_guard` (`deck_context.py:2519`) returns the held-reply (strip/refuse), NOT emit — with `effect_signals` populated AND with `effect_signals` empty (RANK 2 must catch it either way).
- Existing green paths unchanged: resp-`0004`-style strip and resp-`0003`-style describe-only still behave; `test_deck_signal.py:99` master-only abstain still passes (RANK 1 must not flip routing on).

**LIVE re-test (drive-vibemix, dev-source, master-only FLX4 + Rekordbox):**
- Play a bass-heavy track; do a low-EQ KILL on deck A. The co-host's reaction either says nothing causal OR emits a `rule=move_effect_prediction_and_measurement_agree`-backed line whose direction matches the measured master band-delta.
- Repeat the flat→BOOST sweep that produced this capture: the "kick got thin" direction error MUST NOT recur — a boost-then-thin causal claim must be refused/stripped, not emitted at `citation_count=1`.

---

## 7. Gate

**vibemix-grounding-review** — mandatory before any change to `state/deck_context.py`, `agent/dj_cohost.py`, `coach/citation_linter.py`, `prompts/matrix.py`, `state/refresh.py`, or `audio/deck_signal.py` lands. This packet touches the reaction loop and the citation grammar — the release-blocking anti-slop gate applies.
