export const meta = {
  name: 'drift-verify-landing-readiness',
  description: 'Re-runnable drift-aware landing-readiness sweep: verify what Codex landed since a given ref, detect HOLD-bleed, scan current ship-blockers, re-check HOLD gates, refresh the next-slice board. Read-only; no product edits/stage/commit. args:{since:"<ref>"}.',
  phases: [
    { title: 'Delta', detail: 'snapshot current HEAD + new commits + staged + dirty since the input ref' },
    { title: 'Sweep', detail: 'per-new-commit verify + HOLD-bleed sentinel + ship-blocker scan + HOLD-gate recheck + board refresh' },
    { title: 'Verify', detail: 'adversarial skeptic on the bleed/blocker/gate claims' },
    { title: 'Report', detail: 'synthesize the DRIFT REPORT markdown' },
  ],
}

const SINCE = (args && args.since) || 'e5c0e34e'

const RULES = `
ABSOLUTE RULES (read-only verifier; Codex is the implementer):
- READ-ONLY. Do NOT edit ANY file, do NOT git add/stage/commit/amend/push, do NOT run codegen/formatters that rewrite files.
- ALLOWED: git show/log/diff/status, rg/grep, Read, and TARGETED test runs (uv run pytest <paths>, npm --prefix tauri/ui test -- <paths>, cargo test/check). Run only named tests + at most 1-2 related files; never the full suite.
- Repo: /Users/ozai/projects/dj-set-ai. The tree is MOVING (a concurrent Codex session lands signed commits + stages files while you read). Pin to the CURRENT HEAD reported by the Delta scout; use immutable 'git show <hash>' for commits. Note if anything looks unstable.
- Evidence discipline: every claim needs a file:line anchor, a test result, or explicit NOT-FOUND. No broad "all broken". Do NOT claim LIVE behavior (co-host speaks/reacts, audible deck, controller motion) or PACKAGED behavior (DMG/app) without fresh runtime/build proof — default such claims to UNPROVEN.
`

// The known HOLD register + ship-blocker checklist this utility watches. Update as the project evolves.
const WATCH = `
KNOWN HOLD REGISTER (gate must be satisfied before the item may land/ship):
  H-DROP   DROP-call live hype line — coach.py (~:696-718 mastered_speak(reaction_line(drop_cue)) then continue), state/event_detector.py (ceiling-priority DROP event), state/drop_predict.py (DROP_ARM_WINDOW_S=2.0 arm/cue). __main__.py (~:803 setdefault('VIBEMIX_DROP_CALL','1')) makes it ON BY DEFAULT vs its "dormant" comment.
           GATE: vibemix-grounding-review PASS + default flipped OFF (or Kaan sign-off) + live on-beat proof + predicted_drop_in_sec false-positive rate. This is NET-NEW SPEECH → HARD hold.
  H-MOSS   MOSS-only TTS (landed 440fcd56: MOSS is the ONLY voice source, no cloud fallback, fail=LocalTTSUnavailable).
           GATE (now a hard SHIP blocker): sentencepiece must be in BOTH PyInstaller specs (vibemix-core.{macos,windows}.spec) or a frozen build is SILENT + Kaan live ear-pass + Windows path + MOSS model present-or-degrade-gracefully.
  H-CUE    Cue-export "renders in Serato/Mixxx/Rekordbox" — code refuses to claim this (export_serato.py:25-26). GATE: human eye-check in a real build.
  H-WATCH  Packaged fs-watcher behavior. GATE: frozen-bundle proof the watchfiles native ext loads.
  H-BEAT   Beatmatch Mastered. GATE: a real BEATMATCH_GRADED producer + live owned-deck proof (currently intentionally uncreditable).
  H-PKG    ANY packaged/signed claim. GATE: rebuild/re-sign (latest signed artifact dist/fresh-20260601-latest predates the staleness-replay fix and the MOSS-only/sentencepiece state).

GROUND-STATE NOTES (corrections carried from the 2026-06-01 verification):
  - dirty-package checker must stay GREEN: uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary.
  - shared files need HUNK-level staging: __main__.py (~13 hunks/~10 lanes), coach.py (Package 9 prose hunks SAFE vs DROP speech block HOLD).
  - ipc.library.* is CONDITIONALLY both-ended (gated on 'if ipc_router is not None'), not pure-dead. Real library path = Tauri invoke().
  - watchfiles is NOT a declared pyproject dep (only possibly transitive).
  - No spoken fallback/slop may ship; guarded/eval-only text may be logged, never voiced.
`

const DELTA = { type: 'object', additionalProperties: false, properties: {
  head: { type: 'string' }, since: { type: 'string' },
  new_commits: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { hash: { type: 'string' }, title: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, signed_off: { type: 'boolean' } }, required: ['hash', 'title', 'files'] } },
  staged: { type: 'array', items: { type: 'string' } },
  dirty_product: { type: 'array', items: { type: 'string' } },
  package_checker_green: { type: 'boolean' },
  notes: { type: 'string' },
}, required: ['head', 'since', 'new_commits', 'staged', 'dirty_product', 'package_checker_green', 'notes'] }

const COMMIT_VERDICT = { type: 'object', additionalProperties: false, properties: {
  commit: { type: 'string' }, title: { type: 'string' },
  classification: { type: 'string', enum: ['ACCEPTED', 'PARTIAL', 'REJECTED', 'NEEDS_LIVE_PROOF'] },
  touches_speech_or_timing: { type: 'boolean' },
  hold_bleed: { type: 'boolean', description: 'did a HOLD-gated thing land in this commit without its gate?' },
  tests: { type: 'array', items: { type: 'string' } },
  evidence: { type: 'array', items: { type: 'string' } },
  proves: { type: 'string' }, does_not_prove: { type: 'string' }, remaining: { type: 'string' },
}, required: ['commit', 'title', 'classification', 'touches_speech_or_timing', 'hold_bleed', 'evidence', 'proves', 'does_not_prove'] }

const BLEED = { type: 'object', additionalProperties: false, properties: {
  clean: { type: 'boolean' },
  violations: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { item: { type: 'string' }, where: { type: 'string', description: 'commit hash / staged / dirty + file:line' }, severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MED'] }, why: { type: 'string' } }, required: ['item', 'where', 'severity', 'why'] } },
  notes: { type: 'string' },
}, required: ['clean', 'violations', 'notes'] }

const SHIPBLOCKER = { type: 'object', additionalProperties: false, properties: {
  blockers: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { name: { type: 'string' }, severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MED'] }, why: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['name', 'severity', 'why', 'evidence', 'fix'] } },
  notes: { type: 'string' },
}, required: ['blockers', 'notes'] }

const HOLDGATE = { type: 'object', additionalProperties: false, properties: {
  items: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { hold_item: { type: 'string' }, gate: { type: 'string' }, satisfied: { type: 'string', enum: ['YES', 'NO', 'PARTIAL'] }, evidence: { type: 'string' } }, required: ['hold_item', 'gate', 'satisfied', 'evidence'] } },
  notes: { type: 'string' },
}, required: ['items', 'notes'] }

const BOARDREFRESH = { type: 'object', additionalProperties: false, properties: {
  landed_since: { type: 'array', items: { type: 'string' }, description: 'board items now landed' },
  next_safe_now: { type: 'array', items: { type: 'object', additionalProperties: false, properties: { name: { type: 'string' }, files_in: { type: 'array', items: { type: 'string' } }, files_out: { type: 'array', items: { type: 'string' } }, value: { type: 'string' }, risk: { type: 'string', enum: ['low', 'med', 'high'] }, tests: { type: 'array', items: { type: 'string' } } }, required: ['name', 'value', 'risk'] } },
  notes: { type: 'string' },
}, required: ['landed_since', 'next_safe_now', 'notes'] }

const SKEPTIC = { type: 'object', additionalProperties: false, properties: {
  target: { type: 'string' },
  overclaims: { type: 'array', items: { type: 'string' } },
  missed: { type: 'array', items: { type: 'string' }, description: 'violations/blockers the scanner MISSED' },
  corrected: { type: 'string' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] }, notes: { type: 'string' },
}, required: ['target', 'overclaims', 'missed', 'corrected', 'confidence', 'notes'] }

const REPORT = { type: 'object', additionalProperties: false, properties: { markdown: { type: 'string' } }, required: ['markdown'] }

// ---------- Delta ----------
phase('Delta')
const delta = await agent(
  `${RULES}\n\n=== DELTA SCOUT ===\nSnapshot the current state at HEAD vs the input ref \`${SINCE}\`.\nRun: \`git rev-parse HEAD\`; \`git log --oneline ${SINCE}..HEAD\`; for each new commit \`git show --stat --format='%H%n%s%n%GS' <hash>\` (capture title, files, whether Signed-off-by present); \`git diff --cached --name-only\` (staged); \`git diff --name-only -- 'src/*' 'tauri/*'\` (dirty PRODUCT files only); and \`uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary\` (is it GREEN?).\nReturn the structured delta. new_commits = commits in ${SINCE}..HEAD (newest-first ok). If zero, return [].`,
  { schema: DELTA, label: 'delta-scout', phase: 'Delta' }
)
log(`HEAD=${(delta.head || '').slice(0, 8)} since=${SINCE} new_commits=${(delta.new_commits || []).length} staged=${(delta.staged || []).length} dirty_product=${(delta.dirty_product || []).length} pkg_green=${delta.package_checker_green}`)

// ---------- Sweep ----------
phase('Sweep')
const commitTasks = (delta.new_commits || []).map((c) => () => agent(
  `${RULES}\n${WATCH}\n\n=== VERIFY NEW COMMIT ${c.hash} — "${c.title}" ===\nFiles: ${(c.files || []).join(', ')}.\nRead the diff (git show ${c.hash}) + the touched source at HEAD. Run its included/related tests (targeted). Classify ACCEPTED/PARTIAL/REJECTED/NEEDS_LIVE_PROOF. CRITICAL: set touches_speech_or_timing=true if it changes WHAT the co-host says or WHEN (coach speech, dj_cohost, prompts/, event_detector timing, drop_predict, heartbeat). Set hold_bleed=true if any HOLD-register item (H-DROP/H-MOSS/H-CUE/H-WATCH/H-BEAT/H-PKG) landed in this commit WITHOUT its gate satisfied (e.g. DROP-call speech committed without grounding-review; MOSS-only shipped without sentencepiece-in-specs; a packaged claim without rebuild). Give proves / does_not_prove / remaining.`,
  { schema: COMMIT_VERDICT, label: `commit:${c.hash.slice(0, 8)}`, phase: 'Sweep' }
))

const scannerTasks = [
  () => agent(
    `${RULES}\n${WATCH}\n\n=== HOLD-BLEED SENTINEL ===\nThe single most important check: did a HOLD-gated item land or get staged WITHOUT its gate? Inspect the NEW COMMITS (${(delta.new_commits || []).map((c) => c.hash.slice(0, 8)).join(', ') || 'none'}), the STAGED set (${(delta.staged || []).join(', ') || 'none'}), and dirty PRODUCT files. For EACH HOLD item in the register, check current source/git:\n- H-DROP: did coach.py:~696-718 DROP speech / event_detector DROP event / drop_predict arm get committed or staged? Is VIBEMIX_DROP_CALL still default-on (__main__.py ~:803)? Was vibemix-grounding-review run (any evidence)? A committed/staged DROP speech without grounding-review + default-off = CRITICAL violation.\n- H-MOSS: MOSS-only landed (440fcd56). Is sentencepiece NOW in BOTH PyInstaller specs (rg sentencepiece vibemix-core.{macos,windows}.spec)? If NOT and a packaged build is implied/attempted = CRITICAL (silent co-host).\n- H-CUE/H-WATCH/H-BEAT/H-PKG: any commit/doc claiming the gated behavior without proof?\nReturn clean=true ONLY if zero violations. Cite where (hash/staged/dirty + file:line).`,
    { schema: BLEED, label: 'hold-bleed', phase: 'Sweep' }
  ),
  () => agent(
    `${RULES}\n${WATCH}\n\n=== SHIP-BLOCKER SCAN (current HEAD) ===\nWhat would make a packaged/signed build FAIL, go SILENT, or SLOP right now? Check current source:\n1. sentencepiece in BOTH PyInstaller specs (MOSS-only is landed → missing = silent co-host = CRITICAL). rg sentencepiece + onnxruntime + tokenizers in vibemix-core.{macos,windows}.spec.\n2. Any committed speech change lacking grounding-review (DROP-call etc.) = slop risk.\n3. dirty-package checker GREEN? (delta says ${delta.package_checker_green}).\n4. Latest signed artifact staleness (dist/fresh-20260601-latest predates MOSS-only/sentencepiece + staleness-replay → any packaged claim is stale).\n5. Gemini key / live brain presence for the live path (source-level only — note, do not over-claim).\nRank each CRITICAL/HIGH/MED with evidence + the concrete fix. Be specific and current.`,
    { schema: SHIPBLOCKER, label: 'ship-blocker', phase: 'Sweep' }
  ),
  () => agent(
    `${RULES}\n${WATCH}\n\n=== HOLD-GATE RE-CHECKER ===\nFor EACH HOLD item (H-DROP, H-MOSS, H-CUE, H-WATCH, H-BEAT, H-PKG), is its gate NOW satisfied at current HEAD? Check current source/git for concrete evidence:\n- H-MOSS: sentencepiece in both specs? (the main movable gate)\n- H-DROP: grounding-review evidence? default flipped to OFF?\n- H-WATCH: does a watcher exist + is watchfiles declared in pyproject?\n- H-BEAT: does a BEATMATCH_GRADED producer exist? (grep)\n- H-PKG: any fresh rebuild/re-sign newer than the MOSS-only commit?\nMark satisfied YES/NO/PARTIAL with file:line/NOT-FOUND evidence. This tells us which holds are clearing.`,
    { schema: HOLDGATE, label: 'hold-gate-recheck', phase: 'Sweep' }
  ),
  () => agent(
    `${RULES}\n${WATCH}\n\n=== BOARD-HEAD REFRESH ===\nGiven what landed since ${SINCE}, refresh the next-clean-slice board. The prior board (NEXT-LAND-BOARD-current-head.md) listed SAFE_NOW: settings-nav fix (likely landed b16a9bf2), cue-export GUI (surface the moat — check rg serato|cue-export|export-cued in tauri/ui + library_cmds.rs, NOT-FOUND last pass), freshness badge, real-audio cue eval; source-safe watcher (P0 freshness, watchfiles not declared).\nReport: landed_since = which prior board items are now committed (verify via git log/grep). next_safe_now = the remaining + any NEW clean slices, each with files_in/files_out/value/risk/tests. Confirm the cue-export GUI is still missing (the highest-value moat surface) by current grep. Read-only — propose, don't implement.`,
    { schema: BOARDREFRESH, label: 'board-refresh', phase: 'Sweep' }
  ),
]

const sweep = await parallel([...commitTasks, ...scannerTasks])
const commitVerdicts = sweep.slice(0, commitTasks.length).filter(Boolean)
const [bleed, shipblocker, holdgate, board] = sweep.slice(commitTasks.length)

// ---------- Verify (adversarial on the 3 high-stakes scanners) ----------
phase('Verify')
const toVerify = [
  { name: 'hold-bleed', data: bleed },
  { name: 'ship-blocker', data: shipblocker },
  { name: 'hold-gate-recheck', data: holdgate },
].filter((x) => x.data)
const verdicts = await parallel(toVerify.map((t) => () => agent(
  `${RULES}\n${WATCH}\n\n=== ADVERSARIAL SKEPTIC: ${t.name} ===\nChallenge this scanner's output. Did it MISS a violation/blocker (false-clean)? Did it OVER-claim one (false-alarm)? Spot-check the 2-3 most load-bearing items yourself (git show/diff, rg, Read). For hold-bleed especially: independently confirm whether a HOLD item actually landed/staged without its gate — default to "violation present" if uncertain about a speech/packaging gate. Output overclaims, missed, corrected verdict, confidence.\nScanner output (JSON):\n${JSON.stringify(t.data)}`,
  { schema: SKEPTIC, label: `verify:${t.name}`, phase: 'Verify' }
)))

// ---------- Report ----------
phase('Report')
const report = await agent(
  `${RULES}\n\n=== SYNTHESIZE THE DRIFT REPORT (markdown) ===\nWrite a tight, decision-grade DRIFT REPORT for Kaan + Codex. Lead with the verdict in 2-3 lines (is the tree safe to keep landing? any CRITICAL bleed/blocker?). Then sections:\n1. What landed since ${SINCE} (the new commits + per-commit class + any touches_speech_or_timing/hold_bleed flags).\n2. HOLD-BLEED verdict (clean or the violations, with the skeptic's corrections folded in — be conservative).\n3. Ship-blockers RIGHT NOW (ranked CRITICAL/HIGH/MED + the concrete fix each).\n4. HOLD-gate status (which gates moved/cleared).\n5. Refreshed next-slice board (landed_since + next SAFE_NOW).\n6. One-line "Codex, do this next".\nUse file:line anchors. No over-claim; mark anything live/packaged as UNPROVEN unless proven. Keep it under ~120 lines. Return only the markdown.\n\n=== INPUTS ===\nDELTA: ${JSON.stringify(delta)}\nCOMMIT VERDICTS: ${JSON.stringify(commitVerdicts)}\nHOLD-BLEED: ${JSON.stringify(bleed)}\nSHIP-BLOCKER: ${JSON.stringify(shipblocker)}\nHOLD-GATE: ${JSON.stringify(holdgate)}\nBOARD: ${JSON.stringify(board)}\nSKEPTIC VERDICTS: ${JSON.stringify(verdicts)}`,
  { schema: REPORT, label: 'drift-report', phase: 'Report' }
)

return {
  head: delta.head, since: SINCE,
  new_commit_count: (delta.new_commits || []).length,
  package_checker_green: delta.package_checker_green,
  bleed_clean: bleed ? bleed.clean : null,
  critical_blockers: (shipblocker && shipblocker.blockers || []).filter((b) => b.severity === 'CRITICAL').map((b) => b.name),
  report_md: report.markdown,
  raw: { delta, commitVerdicts, bleed, shipblocker, holdgate, board, verdicts },
}
