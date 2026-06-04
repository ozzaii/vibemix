# PILL — FAFO & LEVEL-UP

Synthesis of the streak reality probe, the pill capability census, the crafted level-up opportunities, and the three adversarial verdicts (grounding/anti-slop, product-fit, feasibility/wire-not-build). An opportunity survives only if no lens KILLed it on grounding or product-fit and feasibility confirms a real data source. Corrected efforts and the required grounding bindings are stated inline.

## Streak verdict — is it live?

**No. The streak has never reached you, and as of today's purge (`826fddc9`) its only renderer is deleted — but it was never a fake counter, it was a real-but-mis-counting one that lived and died DARK.**

The producer is genuinely grounded and STILL on the wire today: `_next_grade_progress` (`runtime/suggestion.py:1375-1420`) increments `streak` off `move_grade` derived deterministically from the real transition payload (`intel/move_grade.py:135-209`), and it rides every mascot frame via `current()` (`ws_bus.py:1320`). Pre-purge the pill actually read it (`streakMount`/`gradeStreak` in `git show 826fddc9^:tauri/ui/src/pill/index.ts`), so it WAS plumbed end-to-end from grounded grade to DOM. But it counted the wrong thing: `earned` ticks when the ENGINE rates its own un-played suggestion `clean`/`sexy`/`bomb`/`lit_aff` as you advance, not when you executed a transition a live judge graded clean from audio. So it is the engine applauding its own picks, one decision-class from "sessions opened." It never left a forensic trace (no `events.jsonl` / `~/.cache/vibemix` record of a streak firing), the gate is hard to trip on real audio, and `826fddc9` ("strip gamification") deleted the only consumer while leaving the backend emitting `grade_progress` into the void.

## Pill capability census

| Capability | State | Data source | What the user sees today |
|---|---|---|---|
| Next-track suggestion (core "what mixes next") | LIVE | `next_suggestion` wire field (`ws_bus.py:1320`) from `SuggestionService.current_for_state`; CLAP cosine pick grounded by store∩library (Invariant #2) | A grounded next-track card from the user's own library, honest-null on empty library |
| reasons[] "why this pick" receipts | LIVE | `transition.reasons` (deterministic `score_transition_slate`, `next_suggestion.py:813`), sliced to 2 | Up to 2 why-chips when a grounded transition payload exists |
| "why" meta line (similar vibe · 8A · 128) | LIVE | `NextSuggestion.why` from `_why_for_entry` (`next_suggestion.py:871`) | Camelot/BPM/cue meta, degrades to bare "similar vibe" |
| Cue-slot / timing display | LIVE (conditional) | `transition.cue_slot` + `to_start_s` (`next_suggestion.py:800-802`) | "cue A @ 1:23" + timing rail when cue evidence resolves; numeric confidence NOT surfaced |
| Harmonic / Camelot match | LIVE (two paths) | deck chips `deck_state[side].camelot` + suggestion `why`; `harmonics.compatible` as candidate gate (`next_suggestion.py:159`) | Resulting key on chips/meta; NO explicit relationship verdict badge |
| Hover-reveal peek drawer (Dynamic-Island morph) | LIVE | gated on real `next_suggestion` (`index.ts:1137`); `COLLAPSED_PEEK_ENABLED=true` | Morph opens only when a grounded suggestion is present |
| choose-alternative / accept-keep-later feedback | LIVE (both ends) | ws actions `next_suggestion.choose`/`.feedback` (`ws_bus.py:1075/1094`) → live taste re-score | Working accept/later/choose controls that re-pivot taste (One Mind S3) |
| grade_progress (streak / total_xp / heat / level_up) | DARK | computed every frame `suggestion.py:1365-1434`, serialized into `next_suggestion`; ZERO shipped pill TS reads it | Nothing — `.pill__streak` is a dead hit-test selector, no CSS, no writer |
| move-grade vocabulary (SEXY / BOMB / overdrive) | MOCK/DEV | `pill/move-grade-vocabulary.ts`; only `pillDemoControlsEnabled()` demo path (`index.ts:494/547`) | Nothing in a shipped build (DEV + `VITE_VIBEMIX_DEMO_NEXT=1` only) |
| Demo next-suggestion / deck-state / reaction pads | MOCK/DEV | hardcoded `DEMO_*` behind `DEMO_NEXT_ENABLED` | Nothing shipped; real wire always wins |
| cohost-reaction hero + citation strip | LIVE | `cohost-reaction` wire frames, citation-registry grounded | The speaking surface (shares pill DOM, separate from the suggestion card) |

The shipped pill shows a grounded next-track card with an honest why/reasons/cue/timing line, deck-context key chips, and a working hover-peek with feedback; honest silence when nothing qualifies. It shows NO gamification.

## Surviving level-up moves (ranked)

Ranked by leverage (real-data wire wins first, then grounded builds gated by Kaan's "would a friend say this right now?" bar). All ten opportunities are grounded; the streak forks (Opp 2/3) and Opp 8 carry owner-gates, and Opp 2 was downgraded near-KILL on the pill by product-fit (see Killed/parked).

1. **Render full `reasons[]` in the EXPAND view** — WIRE. Effort S (trivial). The richest receipts already ride the wire; the pill hard-slices `nextReasonItems` to 2 in BOTH densities (`next-suggestion.ts:313`), so the fix is a density-aware slice (expand shows all, peek keeps 2). Grounding: `transition.reasons` from the deterministic scorer; honest-null already holds for embedding-only picks. Prove by-eye: expand on a real pick with section/cue evidence, cross-check chips against the suggestion payload. (REFRAMED: feasibility corrected the probe's "richest receipts only in certain densities" claim — false, both densities cap at 2; the win is even smaller than stated.)

2. **Trustable cue-confidence posture (3-state source label, NOT a %)** — WIRE. Effort S (feasibility corrected the probe's S-M down to S). `cue_source`/`cue_confidence`/`cue_slot` ride the wire but `cue_confidence` is not even declared in the TS interface. Render a coarse posture from `cue_source` (Rekordbox = high, detected = medium, estimated = low). Grounding: `transition.cue_source`; honest-null collapses the line when no cue resolves. Owner-gate: approve the 3-bucket vocabulary. Hard constraint from product-fit: it must NOT resurrect the purged precise percentage or the "needs review" self-doubt copy. Prove by-eye on a Rekordbox library with hand-placed cues vs detected-only tracks.

3. **Hover-reveal "the road not taken" (runner-up + why it lost)** — WIRE + thin render BUILD. Effort S-M. `transition_alternatives` (full ranked list with per-candidate scores) is serialized via `asdict` (`next_suggestion.py:66`) and `choose_alternative` still exists (`ws_bus.py:1080`), but the field is not declared in `NextSuggestionWire` and no pill TS reads it (the mock-transfer wire was purged). Add the field + render #2 + a losing-margin string from the two `scores`. Grounding: engine's real shortlist + `score_transition_slate` deltas; honest-null when only one candidate qualified. Owner-gate REQUIRED: returns ONLY as deep-hover depth, never the persistent "backup alternatives section" the purge killed. Prove by-eye: shown runner-up matches the actual payload #2.

4. **"Why nothing" honest-silence receipt on hover** — small two-ended BUILD (feasibility corrected the probe's "WIRE-light" — the engine returns a bare `None` today, no reason code is computed or carried). Effort S-M. Emit a distinct reason code (no library / now-playing not in library / no harmonic match) from the existing Invariant #2 resolution path and render it on hover. Grounding: computed-from-real-state null conditions (`resolve_seed_context → None`, library-cache gate). Owner-gate: terse vocabulary, Invariant #5 (idle ≠ fault) — never imply a fault at idle. Prove by-eye in three real null states, confirm a healthy pick still renders normally.

5. **Harmonic-compatibility verdict badge (8A → 9A · energy boost)** — WIRE + thin BUILD (feasibility corrected the probe's "WIRE-mostly" — the gate computes only a boolean drop/keep; the human verdict string is NOT computed anywhere). Effort M. `from_camelot`/`to_camelot` ride the wire (`next_suggestion.py:798-799`) and `harmonics.compatible`/`is_clash`/`semitone_distance` already run as the candidate gate. Add a small deterministic verdict function (keys → label), carry it, render it. Grounding: `state/harmonics.py` wheel math on both resolved keys at/above the deck cite-floor (mirror `renderDeckChips`); honest-null when either key absent; verdict text derived from the wheel functions, never hand-narrated. Prove by-eye against a known harmonic pair.

6. **Harmonic-path one-step lookahead ("opens toward 9A/9B next")** — BUILD. Effort M. Run the picked candidate's resolved key one hop through `harmonics.compatible`. Grounding: wheel math on the candidate's real key; strict honest-null on keyless candidates; must NOT be templated. Owner-gate REQUIRED ("would a friend bother to say this mid-mix?"): hover-reveal depth ONLY, never on the collapsed peek. (REFRAMED by both grounding and product-fit from a default-render to hover-only — risk is relevance/clutter, not fabrication.) Prove by-eye on a keyed library that the direction is wheel-correct and disappears for keyless picks.

7. **Detected-musical-moment transient pulse ("breakdown in 8 bars")** — BUILD (feasibility corrected the probe's "WIRE-to-BUILD" — the section-lookahead is computed only inside the model-prompt path `_source_context`/`context_for_state`, not on the pill wire, and there's no transient render path). Effort M to light-L. Strongest "real friend in your ear" candidate (Invariant #3). Grounding: HARD citation gate — every pulse must resolve an `EvidenceRegistry` section/cue citation to a real detected boundary on the audible deck + the live beat-clock; honest-silence otherwise. (REFRAMED by both grounding lenses to a citation-gated build: a bars-countdown printed without a resolved citation is Invariant #3 slop — do NOT ship on the timing math alone.) Owner-gate REQUIRED: which event types qualify (drops/breakdowns yes, minor phrase boundaries no) + rarity floor. Prove by-bus on a replayed set with known structure that it fires only on real boundaries with a resolvable citation.

## Killed / parked

- **Rewire streak to executed-and-judged transitions (Opp 2)** — PARKED to debrief, KILLED on the pill. Product-fit rated re-introduction risk HIGH: the keystone live event does not exist (feasibility resolved it from code — `BEATMATCH_GRADED` is practice-loop only and never fires over a live set per Invariant #3; the live `transition_judge_runtime` logs to the recorder, not a pill ws frame), so the natural failure mode is re-pointing the streak at the self-applauding candidate grade that was just purged. Corrected effort L (event plumbing + pill subscription + accumulator), not M-L. A persistent "clean exits" counter on the eyes-off overlay is also the Duolingo layer the purge explicitly killed. If it ever lives, it belongs in debrief (post-session, where a real audio-graded judge can run), not on the pill, and only bound to a cited `[ev:BEATMATCH_GRADED@…]` / `[judge:…]` event.
- **"Locked-in" momentary state dot (Opp 3)** — PARKED on ice behind Opp 2's missing keystone. No counter, so it dodges the points trap, but it consumes the same nonexistent live judge-event feed; a glow driven by the engine liking its own pick is slop in a quieter coat. Standalone effort = full Opp 2 cost (L), not the probe's S/M. Dies with Opp 2 if the live judge event never materializes.
- **Strip the orphaned `grade_progress` block from the wire (Opp 1)** — NOT killed; it is a confirmed cleanup, but it is owner-decision plumbing rather than a user-facing level-up, so it sits in the /goal as the prerequisite, not a ranked move. All three verifiers KEEP it: `grade_progress` is computed and serialized every frame (`suggestion.py:692-694`) with zero shipped TS readers. Strip the attach call-sites; keep `move_grade.py` (reused by the Viber build-set chat, a separate `library/index.ts` surface, unrelated to the pill).
- **XP badge / LV level bead / combo heat rail / overdrive halo / keep-later-timing feedback buttons / grade-verb badges** — STAY KILLED (purged in `826fddc9`). None reflect a musical event; they reward using the app. The grade verbs ("SEXY"/"BOMB"/"overdrive") survive only on the DEV-gated demo path and never reach a shipped user.

## Streak — the on-brand decision

Owner-gate for Kaan. Two parts:

1. **Kill it where it is now.** The current `grade_progress.streak` (`suggestion.py:1375-1434`) counts the engine rating its own un-played suggestions and is dark anyway. Decide: delete the attach entirely, or stop serializing it (keep computing only if a near-term rewire is planned). Default recommendation: strip it from the serialized frame so it can't be silently re-rendered as a fake counter.

2. **If you want the streak feel, it must count exactly one thing: consecutive EXECUTED transitions that the real live judge graded clean from real audio.** Each tick must resolve a cited `[ev:BEATMATCH_GRADED@…]` / `[judge:]` event from captured audio (a mix you actually pulled off), resettable by a graded mistake — the same earned-vs-mock line as Learn's "Mastered requires a cited live demonstration." A streak of suggestions-rated, advances-accepted, time-spent, or sessions is fake on every axis and never ships. Even the real version stays a quiet, rare, earned acknowledgment ("three clean exits in a row — you're locked in"), never a persistent HUD competing with the deck — and the cited per-transition live judge event it depends on does NOT exist on the bus today (it is practice-loop only or recorder-only), so this is L-effort new plumbing, debrief-first, not a pill quick-win.

## Next /goal — Pill

```
/goal Pill level-up — ship the surviving grounded moves. PREREQ (owner-gated): strip the
orphaned grade_progress block from the live frame (Opp 1) per Kaan's decision in
PILL-FAFO-AND-LEVELUP.md §Streak. Then land the ranked WIRE wins.

LANE SPLIT (one shared tree — stay in your island):
- FRONTEND lane (tauri/ui/src/pill/**): Opp 1-render-removal-consumer, Opp "reasons[] in
  expand" (density-aware slice in next-suggestion.ts), Opp "cue-confidence posture"
  (declare cue_confidence in NextSuggestionWire + 3-bucket render), Opp "runner-up hover"
  (declare transition_alternatives + render #2), Opp "why-nothing hover" (render reason
  code). The IPC schema (tauri/ui/src/ipc/messages.schema.json) is FRONTEND-lane-owned —
  if a new typed field is needed, it is added here, never from the engine lane.
- LIBRARY/ENGINE lane (src/vibemix/runtime/suggestion.py + src/vibemix/library/next_suggestion.py
  + src/vibemix/state/harmonics.py): Opp 1 strip the grade_progress attach in suggestion.py;
  Opp "harmonic-compatibility verdict" = new deterministic verdict fn in harmonics.py +
  carry through next_suggestion.py payload; Opp "why-nothing reason code" = emit the reason
  from the Invariant #2 null path; Opp "one-step lookahead" + Opp "detected-moment pulse" =
  carry section/harmonic-lookahead onto the next_suggestion wire (these two are owner-gated
  BUILDs, hover-only / citation-gated — do NOT ship without Kaan's "would a friend say this
  now?" approval).

DO NOT: revive any streak/XP/heat/level_up render. Opp "rewire streak to judge" + Opp
"locked-in dot" are PARKED to debrief, gated on a cited live judge event that does NOT
exist on the bus today — do not build them on the pill.

PROOF: by-bus snapshot of next_suggestion on dev-source (confirm grade_progress gone after
Opp 1; confirm new fields present) + by-eye on the real rig per each move's how-to-prove.
Run grounding-review on any change to what the co-host says or when. test-passing-but-dark = 0.

SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, Kaan Özkan <rahipdotaci@gmail.com>.
```
