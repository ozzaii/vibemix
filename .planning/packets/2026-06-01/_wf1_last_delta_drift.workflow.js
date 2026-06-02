export const meta = {
  name: 'last-delta-drift',
  description: 'Read-only drift audit: verify what changed since the last accepted packet/head; catch HOLD bleed, stale packet claims, checker/verifier regressions. No product edits/stage/commit/app-launch. args:{since,head}.',
  phases: [
    { title: 'Delta', detail: 'commits since baseline + dirty product hunks + checker status' },
    { title: 'Sweep', detail: 'verify speech + non-speech commits, HOLD-bleed sentinel, stale-claim, checker-regression' },
    { title: 'Verify', detail: 'adversarial skeptic on bleed / regression / finding-fix claims' },
    { title: 'Report', detail: 'synthesize CLAUDE_LAST_DELTA_DRIFT.md body' },
  ],
}

const SINCE = (args && args.since) || 'c88d5f56'
const HEAD = (args && args.head) || '26da514f'

const RO = `READ-ONLY agent. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain).
HARD CONTRACT: NEVER edit, stage (git add), commit, or launch/control the app (no \`python -m vibemix\`). ALLOWED: \`git show/log/diff/status --porcelain\`, ripgrep/grep, Read, codegraph tools, and TARGETED \`uv run pytest -q <files>\` (use the repo .venv — system python3 is 3.14 and cannot import livekit). Tests are read-only verification, NOT the app.
EVIDENCE RULE: every claim carries a file:line anchor, a test result, or an explicit NOT-FOUND. LAND/HOLD posture: anything changing what the co-host SAYS or WHEN it speaks is HOLD unless it has vibemix-grounding-review + proof. MOSS is the only TTS source; no cloud/fake spoken fallback is acceptable. Do not assert live DJ/controller/deck causality without evidence.
`

const SCOUT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    baseline: { type: 'string' }, head_now: { type: 'string' },
    commits: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      sha: { type: 'string' }, subject: { type: 'string' },
      touches_speech_or_timing: { type: 'boolean' }, files: { type: 'string' } }, required: ['sha', 'subject', 'touches_speech_or_timing'] } },
    dirty_product_files: { type: 'array', items: { type: 'string' } },
    staged_now: { type: 'array', items: { type: 'string' } },
    checker_status: { type: 'string', description: 'GREEN/RED + detail from scripts/check_dirty_package_plan.py --strict-assignments' },
  }, required: ['baseline', 'head_now', 'commits', 'dirty_product_files', 'checker_status'],
}

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    lane: { type: 'string' },
    verdict: { type: 'string', enum: ['CLEAN', 'CONCERN', 'REGRESSION', 'MIXED'] },
    items: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] },
      title: { type: 'string' }, file: { type: 'string' }, line: { type: 'string' },
      detail: { type: 'string' }, disposition: { type: 'string' } }, required: ['severity', 'title', 'detail'] } },
    summary: { type: 'string' },
  }, required: ['lane', 'verdict', 'summary'],
}

phase('Delta')
log(`Drift audit: ${SINCE}..HEAD (~${HEAD}). Scouting commits + dirty hunks + checker.`)
const scout = await agent(RO + `DELTA SCOUT. Establish the delta from baseline \`${SINCE}\` to the CURRENT HEAD (run \`git rev-parse HEAD\`).
1. \`git log --oneline ${SINCE}..HEAD\` — list every commit (sha, subject); mark touches_speech_or_timing=true if it edits src/vibemix/agent/dj_cohost.py, state/coach.py, runtime/coach.py, prompts/*, state/event_detector.py, state/drop_predict.py, agent/emote_parser.py, agent/tts_chain.py, agent/local_tts.py.
2. \`git status --porcelain\` — list DIRTY product files (src/**, tauri/**).
3. \`git diff --cached --name-only\` — staged now?
4. Run \`python3 scripts/check_dirty_package_plan.py --strict-assignments --summary\` and report GREEN (exit 0, all dirty paths lane-assigned) or RED (with the unassigned paths).
Return the structured scout.`, { label: 'delta:scout', phase: 'Delta', schema: SCOUT_SCHEMA })

phase('Sweep')
const sweepLanes = await parallel([
  () => agent(RO + `SPEECH-COMMIT VERIFIER. Verify every commit in \`${SINCE}..HEAD\` that touches the co-host SPEECH/TTS/prompt surface. For EACH: read it (\`git show <sha>\`), confirm what it does at file:line, run its touched tests, and judge whether it is sound and stays within HOLD/LAND posture (a fixed-text or prompt change is LAND; a new spoken trigger is HOLD).
SPECIFICALLY CONFIRM these two — they fix findings from the prior verification:
- \`b5916eb0 fix(cohost): enforce english-only spoken output\` — does it add a RUNTIME backstop (not just a prompt line) that prevents non-English text from reaching TTS/transcript? Where (file:line)? Is it tested?
- \`54ec38be fix(cohost): keep citation atoms out of tts\` — does it strip citation atoms ([aud:rms@..]/[ev:..]) from the TTS input while keeping them on the visible transcript/receipt? Where? Tested?
Also verify a8562375 (prevent invented audio citation timestamps), de520ed9 (disable audio output when moss muted), 26da514f (require proof for control-praise phrases). Report per-commit with severity (INFO if sound). lane="speech-commits".`, { label: 'sweep:speech-commits', phase: 'Sweep', schema: FINDINGS_SCHEMA }),
  () => agent(RO + `NON-SPEECH-COMMIT VERIFIER. Verify the remaining commits in \`${SINCE}..HEAD\` that do NOT touch the speech surface: c1b85304 (reject stale rekordbox deck routing hints), 1b51ef89 + 4bc30e66 (live-context operator proof actions / release reuse), 4446f674 (accept live flx4 b-jog cc34). For each: read it, confirm at file:line, run touched tests, flag any over-claim of live/packaged behavior. lane="non-speech-commits".`, { label: 'sweep:non-speech-commits', phase: 'Sweep', schema: FINDINGS_SCHEMA }),
  () => agent(RO + `HOLD-BLEED SENTINEL — the highest-value check. Determine whether any GATED/HOLD item has LANDED or been STAGED without its gate. Specifically: (1) the DROP-call live hype SPEECH block — \`git show HEAD:src/vibemix/runtime/coach.py | rg -n "reaction_line|mastered_speak|drop_cue"\` — is the spoken DROP block COMMITTED at HEAD, or still dirty-only? (2) Is anything in the dirty tree staged that carries a HOLD hunk (DROP speech, MOSS-only-without-model, ungated new spoken trigger)? (3) Did any commit since ${SINCE} introduce a NEW spoken trigger without a grounding-review trail? Default to bleed_found=true if you cannot PROVE a gated item stayed out. lane="hold-bleed".`, { label: 'sweep:hold-bleed', phase: 'Sweep', schema: FINDINGS_SCHEMA }),
  () => agent(RO + `STALE-CLAIM CHECKER. Re-read the durable packets and flag any claim now CONTRADICTED by current HEAD. Read: .planning/packets/2026-06-01/INDEX.md, CODEX_VERIFICATION-cohost-grounding-tts-tags.md, NEXT-LAND-BOARD-after-c88d5f56.md, DRIFT-current-head.md, CODEX_PACKAGE_SWEEP_STATUS.md. For each stale claim, cite the doc line and the contradicting code/commit (e.g. the prior verification's MEDIUM 'English-only unenforced' and 'citation-in-TTS open question' may now be RESOLVED by b5916eb0/54ec38be — confirm and mark them resolved). lane="stale-claims".`, { label: 'sweep:stale-claims', phase: 'Sweep', schema: FINDINGS_SCHEMA }),
  () => agent(RO + `CHECKER/VERIFIER REGRESSION. Run the read-only repo guards and report pass/fail: (1) \`python3 scripts/check_dirty_package_plan.py --strict-assignments --summary\`; (2) the model-literal grep gate (rg for hardcoded model names outside model_router — check tests/ for the gate name); (3) tests/repo/* guards (clean-checkout imports, retired-poc scrub) — \`uv run pytest -q tests/repo\`; (4) any IPC codegen parity check. Report each GREEN/RED with the exact command + tail. lane="checker-regression".`, { label: 'sweep:checker-regression', phase: 'Sweep', schema: FINDINGS_SCHEMA }),
])

phase('Verify')
const skeptics = await parallel(
  sweepLanes.filter(Boolean).map(lane => () => agent(RO + `ADVERSARIAL SKEPTIC on the "${lane.lane}" drift finding. Try to break it: a missed bleed, an over-claim that a finding was "resolved", a regression mislabeled CLEAN, a test that does not assert what is claimed. Re-check the code yourself.
FINDING JSON:
${JSON.stringify(lane)}
Return upheld=true/false with confidence and corrected verdict.`, { label: `skeptic:${lane.lane}`, phase: 'Verify', schema: { type: 'object', additionalProperties: false, properties: { lane: { type: 'string' }, upheld: { type: 'boolean' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] }, refutation: { type: 'string' }, corrected: { type: 'string' } }, required: ['lane', 'upheld', 'confidence', 'refutation'] } }))
)

phase('Report')
const findings = { scout, sweepLanes: sweepLanes.filter(Boolean), skeptics: skeptics.filter(Boolean) }
const docMarkdown = await agent(RO + `SYNTHESIS. Write the FULL markdown body for CLAUDE_LAST_DELTA_DRIFT.md from the evidence below. Sections: (1) Verdict line (is the tree SAFE to keep landing? any CRITICAL?), (2) Delta table (commits ${SINCE}..HEAD + dirty product files + checker status), (3) Commit verification (speech + non-speech, with the two finding-fixes b5916eb0/54ec38be explicitly confirmed-or-not), (4) HOLD-bleed verdict, (5) Stale packet claims now resolved/contradicted, (6) Checker/verifier regression status, (7) file:line evidence for anything non-INFO. Use the skeptic verdicts to temper claims. Be concise and decisive. Output ONLY the markdown body (no code fences around the whole thing, no preamble) — it is written verbatim to the doc.
EVIDENCE:
${JSON.stringify(findings)}`, { label: 'report:synthesis', phase: 'Report' })

return { workflow: 'last-delta-drift', baseline: SINCE, findings, docMarkdown }
