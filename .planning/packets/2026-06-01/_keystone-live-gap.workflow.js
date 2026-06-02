export const meta = {
  name: 'keystone-live-gap',
  description: 'Root-cause why the eq_move keystone does not gate the live causal coach line (LIVE-captured), produce a Codex fix packet',
  phases: [
    { title: 'Investigate', detail: 'keystone→prompt wiring · why audio_delta empty · LLM-causal-without-license gap' },
    { title: 'Verify', detail: 'adversarial check of the root-cause chain' },
    { title: 'Packet', detail: 'write the CODEX_VERIFICATION fix packet' },
  ],
}

const REPO = '/Users/ozai/projects/dj-set-ai'
const HEAD = 'e49b2f63'
const PK = REPO + '/.planning/packets/2026-06-01'
const OUT = PK + '/CODEX_VERIFICATION-keystone-not-gating-live-causal-line.md'

// LIVE ground truth captured this session on Kaan's real rig (FLX4 + Rekordbox, dev-source).
const LIVE = args || {}
const EVIDENCE = `
## LIVE GROUND TRUTH (captured 2026-06-02, Kaan's rig, HEAD ${HEAD}, dev-source engine)
- Event PHASE (resp 0002_080213). Co-host SPOKE a causal coach line, EMITTED with citation_count=1:
  raw: "The kick drum got thin and boomy when you [midi:A_low:_flat_to_boost_small_twist@203.2] pushed that low EQ past flat; next time, keep it at center to preserve the weight of that vocal track."
- The ONLY citation that resolved = [midi:A_low:_flat_to_boost_small_twist@203.2] (a MOVE-HAPPENED midi citation), action=emit.
- The live prompt for that turn (invocations/0002_080213_PHASE/prompt.txt) carried:
  - hearing[rms=0.161 sub=0.70 low=0.21 mid=0.08 high=0.01 bpm=103]  (sub is STRONG)
  - recent_moves[8s]: A_low killed->deep-cut->cut->flat->boost (a full low-EQ sweep, ~6s prior)
  - grounding_refs / live_evidence: [midi:A_low:_*] move citations + [mix:deck_route=A_dominant+B_muted] + deck-route refs
  - deck_audio_context: source=global_mix isolated_decks=false routing=A=dominant(0.70) B=muted(0.00) support=single_deck_A ; deck_audio_parts=0
  - **NO move_effect_context[...] anywhere in the prompt. NO rule=move_effect_prediction_and_measurement_agree. audio_delta: [] (EMPTY).**
- The SLOP it let through: Kaan pushed low flat->BOOST (more lows) and measured sub=0.70 (strong), yet the model said the kick "got THIN" — boost should THICKEN, not thin. A plausible-but-direction-wrong causal claim — exactly what the keystone's measured double-gate should have caught/corrected.
- Anti-slop gate DID work elsewhere same session: a later MIX_MOVE causal line (resp 0004) was action=strip -> empty; a describe-only HEARTBEAT (resp 0003) stayed descriptive count=0.
- Source state: keystone IS wired (codegraph) — eq_move_model.predicted_band_gains/canonical_eq_move imported deck_context.py:16, _licensed_move_effect:1892, guard call apply_live_claim_guard:2519, render_move_effect_context:2371. So it's wired but NOT reaching the live prompt on this low-EQ move.
- Extra args: ${JSON.stringify(LIVE)}
`

const RULES = `
You are a READ-ONLY senior engineer debugging vibemix (AI DJ co-host). Repo ${REPO}, HEAD ${HEAD}.
HARD: never edit product code, never commit. Read source + the LIVE evidence below; reason from file:line + codegraph. No slop, no flattery, be the honest debugger.
Use codegraph (ToolSearch "codegraph") for call paths and Read/Grep for source. The question is concrete and the answer must be exact file:line.
The keystone's intended contract (from CODEX_READY-eq-move-physics-keystone.md + GOLD-WIRING-MAP.md under ${PK}): a MIDI EQ/filter move -> predicted_band_gains -> double-gate vs the MEASURED post-move band delta -> license a causal claim ([move_effect:...]) ONLY when predicted∧measured agree, else REFUSE; the refuse text is LIVE_MOVE_EFFECT_HELD_REPLY. render_move_effect_context emits rule=move_effect_prediction_and_measurement_agree (license) or rule=dsp_delta_not_causal_proof (refuse).
${EVIDENCE}
OUTPUT: dense markdown prose, file:line grounded. Return your findings (no JSON).
`

phase('Investigate')
log('Root-causing why the eq_move keystone did not gate the live causal coach line')

const findings = await parallel([
  () => agent(`${RULES}
TASK A — **KEYSTONE → PROMPT wiring.** The licensed/refused move_effect atom from render_move_effect_context (deck_context.py:2371) — does it actually reach the LIVE PROMPT for a PHASE / MIX_MOVE event? Trace the path: who calls render_move_effect_context, does its output get composed into the prompt the live coach sends (state/coach.py prompt builder -> dj_cohost), and under what CONDITIONS is it included vs dropped? The LIVE prompt for a PHASE event with a fresh A_low sweep had NO move_effect_context at all. Pinpoint the exact branch/condition that excluded it (event-type filter? requires a MIX_MOVE not PHASE? requires audio_delta non-empty? requires isolated decks?). Give the file:line of the gate that dropped it.`,
    { label: 'inv:wiring-trace', phase: 'Investigate' }),

  () => agent(`${RULES}
TASK B — **WHY IS audio_delta EMPTY** on a clear low-EQ sweep? The keystone's measured side needs a post-move band delta. Trace what populates audio_delta / the measured band-delta window: render_audio_delta_items (deck_context.py ~:1794), deck_audio_window_context (~:571), band_energy_ratios (audio/band_features.py:30). On the COMMON rig the live evidence shows (deck_audio_context: source=global_mix, isolated_decks=false, deck_audio_parts=0, routing=A_dominant+B_muted, support=single_deck_A) — does the measured band-delta window EVER populate? Is it gated on per-deck/isolated audio that a master-only single-deck rig never provides? This is the likely root cause: the keystone's measurement half is unreachable on the master-only rig it was supposed to work on. Confirm or refute with file:line — what exactly makes audio_delta empty here.`,
    { label: 'inv:audio-delta-rootcause', phase: 'Investigate' }),

  () => agent(`${RULES}
TASK C — **THE LLM-CAUSAL-WITHOUT-LICENSE GAP.** The model emitted "kick got thin WHEN YOU pushed low EQ" grounded ONLY on a [midi:A_low:_flat_to_boost] move-HAPPENED citation (citation_count=1, emit) — NOT on a move_effect license. So a "the move happened" citation is being treated as sufficient to assert "the move CAUSED this sound." Examine: (1) does apply_live_claim_guard (deck_context.py:2313+) actually intercept a move->effect CAUSAL claim in a PHASE-event reaction, or does it only guard specific phrasings/paths? (2) does the citation linter (coach/citation_linter.py) only check that [midi:] resolves (move happened) without gating the causal ATTRIBUTION? (3) do the prompt instructions (prompts/matrix.py + state/coach.py) tell the model it MAY narrate move->effect causation from a move citation alone? Find where the causal claim slipped the gate, file:line. Note the correctness tell: low->BOOST + measured sub=0.70 but model said "thin" (direction wrong) — evidence the claim was ungated inference, not measured proof.`,
    { label: 'inv:llm-causal-gap', phase: 'Investigate' }),
])

phase('Verify')
log('Adversarially verifying the root-cause chain')
const verdict = await agent(`${RULES}
You are the ADVERSARIAL VERIFIER. Below are three investigation findings (wiring-trace, audio_delta-rootcause, llm-causal-gap). Try to REFUTE the combined root-cause. Specifically pressure-test: is audio_delta REALLY unreachable on a master-only rig, or did it just happen to be empty this turn (timing)? Is the keystone REALLY excluded from PHASE events, or would a MIX_MOVE event have included it (note: the live capture's resp 0004 WAS a MIX_MOVE and got action=strip — what does that tell us)? Is the "LLM causal without license" a real gate gap or working-as-intended? Resolve the contradictions, state which findings hold and which overreach, and give the SINGLE most-likely root cause with the highest-confidence file:line evidence.

${findings.filter(Boolean).map((f, i) => '### Finding ' + (i + 1) + '\n' + f).join('\n\n---\n\n')}`,
  { label: 'verify:adversarial', phase: 'Verify' })

phase('Packet')
log('Writing the CODEX_VERIFICATION fix packet')
const packet = await agent(`${RULES}
You are the PACKET WRITER. Using the three findings + the adversarial verdict, WRITE a Codex-actionable verification packet to EXACTLY: ${OUT}
Structure: (1) one-line verdict (keystone wired but does NOT gate the live causal line — why); (2) the LIVE evidence (quote the captured line + the empty audio_delta + the direction-wrong "thin" tell); (3) ROOT CAUSE with the exact file:line chain (keystone→prompt gate + why audio_delta empty + the causal-without-license gap); (4) what's CORRECT (don't over-fix: the anti-slop strip/describe paths work; the keystone source is sound); (5) the FIX SURFACE for Codex — concrete, ranked: e.g. populate the measured band-delta on the master-only single-deck path so the keystone can license OR refuse on a real measurement, AND/OR suppress LLM move→effect causal attribution when the move_effect license is absent (a move-HAPPENED citation must not license a move-CAUSED claim); (6) acceptance (SRC + the LIVE re-test: a low-kill on a bass track must produce rule=move_effect_prediction_and_measurement_agree, and the boost/thin direction error must not recur); (7) gate = vibemix-grounding-review. Brutally honest, every claim file:line. After writing, RETURN a ≤350-word executive summary.

### Findings
${findings.filter(Boolean).map((f, i) => '#### ' + (i + 1) + '\n' + f).join('\n\n')}

### Adversarial verdict
${verdict}`,
  { label: 'write:packet', phase: 'Packet' })

return { packet, doc: OUT }
