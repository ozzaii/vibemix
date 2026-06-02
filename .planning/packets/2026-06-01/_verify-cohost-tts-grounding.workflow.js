export const meta = {
  name: 'verify-cohost-grounding-tts',
  description: 'Read-only verification of Codex cohost grounding/TTS-tag commits (de9a55f5/a9cb2193/c88d5f56) at HEAD c88d5f56 + next package board. No product edits/stage/commit/app-control. args:{head:"<sha>"}.',
  phases: [
    { title: 'Verify', detail: '3 commits + 3 grounding/TTS contract checks, each with file:line + test evidence' },
    { title: 'Refute', detail: 'adversarial skeptic per finding + dedicated sanitizer-bypass / raw-vs-clean hunters' },
    { title: 'Board', detail: 'next-3 package board (SAFE_NOW vs HOLD) + shared-file risk' },
  ],
}

const HEAD = (args && args.head) || 'c88d5f566ee0658c88f9e3fdc4229851fec6ed41'
const SHORT = HEAD.slice(0, 8)

const PREAMBLE = `READ-ONLY verification agent. Repo: /Users/ozai/projects/dj-set-ai.
HARD CONTRACT: you MUST NOT edit, stage (git add), commit, or launch/stop/control the app (never run \`python -m vibemix\` or \`uv run python -m vibemix\`). ALLOWED: \`git show <sha>\`, \`git log\`, \`git status --porcelain <file>\`, \`git diff\`, ripgrep/grep, Read, codegraph tools (codegraph_context/trace/callers/callees/search), and TARGETED test runs for verification only (\`uv run pytest -q <files>\` or \`PYTHONPATH=src python3 -m pytest -q <files>\`) — tests are NOT the app.
PINNED HEAD: ${SHORT} (${HEAD}). Verify committed behavior via immutable \`git show <sha>\`; verify current behavior by reading the working tree — and for any target file, run \`git status --porcelain <file>\` and note whether it is CLEAN (== committed) or DIRTY (un-landed working-tree change), because the tree is shared with a concurrent session.
EVIDENCE RULE: every claim carries a file:line anchor, a test result, or an explicit NOT-FOUND. Do not over-claim packaged or live-audio behavior you cannot observe from source/tests. Be precise and skeptical.

`

const EVIDENCE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    item_id: { type: 'string' },
    verdict: { type: 'string', enum: ['ACCEPTED', 'PARTIAL', 'REJECTED', 'PRESENT', 'ABSENT', 'MIXED'] },
    one_line: { type: 'string' },
    evidence: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          file: { type: 'string' }, line: { type: 'string' },
          kind: { type: 'string', enum: ['source', 'test', 'grep', 'git-show', 'codegraph', 'NOT-FOUND'] },
          detail: { type: 'string' },
        }, required: ['file', 'kind', 'detail'],
      },
    },
    tests: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: { cmd: { type: 'string' }, result: { type: 'string' } }, required: ['cmd', 'result'],
      },
    },
    file_cleanliness: { type: 'string', description: 'per-file CLEAN/DIRTY vs committed for the targets touched' },
    caveats: { type: 'array', items: { type: 'string' } },
  },
  required: ['item_id', 'verdict', 'one_line', 'evidence'],
}

const SKEPTIC_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    item_id: { type: 'string' },
    upheld: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    refutation: { type: 'string', description: 'what you tried to break it with and what you found' },
    holes: { type: 'array', items: { type: 'string' } },
    corrected_verdict: { type: 'string', description: 'the verdict that actually holds after refutation' },
  },
  required: ['item_id', 'upheld', 'confidence', 'refutation', 'corrected_verdict'],
}

const BYPASS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    scope: { type: 'string' },
    bypass_found: { type: 'boolean' },
    spoken_paths: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          path: { type: 'string', description: 'symbol/file:line of the spoken or user-visible emit' },
          field: { type: 'string', description: 'which string it emits (sanitized vs raw)' },
          sanitized: { type: 'boolean' },
          detail: { type: 'string' },
        }, required: ['path', 'sanitized', 'detail'],
      },
    },
    findings: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          file: { type: 'string' }, line: { type: 'string' },
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] },
          detail: { type: 'string' },
        }, required: ['file', 'severity', 'detail'],
      },
    },
    conclusion: { type: 'string' },
  },
  required: ['scope', 'bypass_found', 'conclusion'],
}

const BOARD_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    packages: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' },
          disposition: { type: 'string', enum: ['SAFE_NOW', 'HOLD'] },
          rank: { type: 'number' },
          value: { type: 'string' },
          risk: { type: 'string' },
          shared_files: { type: 'array', items: { type: 'string' } },
          gate: { type: 'string' },
          evidence: { type: 'string' },
        }, required: ['name', 'disposition', 'value', 'risk'],
      },
    },
    shared_file_risk: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          file: { type: 'string' }, exists: { type: 'boolean' }, dirty_now: { type: 'boolean' },
          contending_lanes: { type: 'string' }, caution: { type: 'string' },
        }, required: ['file', 'caution'],
      },
    },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['packages', 'shared_file_risk'],
}

// ---- Phase 1 evidence items (3 commits + 3 contract checks) ----
const EVIDENCE_ITEMS = [
  {
    id: 'commit-de9a55f5',
    prompt: `Verify commit \`de9a55f5\` "fix(cohost): block no-move coaching advice". Read it immutably: \`git show de9a55f5\`.
CLAIM: the co-host must NOT emit coaching advice that asserts a controller/EQ/fader MOVE or causality when there is no real move evidence (e.g. recent_moves empty). Touched files: src/vibemix/state/coach.py, src/vibemix/prompts/matrix.py, src/vibemix/agent/dj_cohost.py, src/vibemix/state/deck_context.py + tests/agent/test_dj_cohost_linter.py, tests/prompts/test_matrix.py, tests/state/test_deck_context.py, tests/agent/test_coach_prompt_grounding.py.
CONFIRM with file:line: (a) the exact mechanism that blocks no-move advice (a citation/linter? a prompt-matrix instruction? a deck_context guard on recent_moves?); (b) the new tests actually assert the block; (c) run those tests now: \`uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/prompts/test_matrix.py tests/agent/test_coach_prompt_grounding.py\`.
VERDICT: ACCEPTED only if source + passing tests prove the no-move block; PARTIAL if partial; REJECTED if not. item_id="commit-de9a55f5".`,
  },
  {
    id: 'commit-a9cb2193',
    prompt: `Verify commit \`a9cb2193\` "fix(cohost): strip internal voice tags from speech". \`git show a9cb2193\`.
Touched: src/vibemix/agent/emote_parser.py + tests/agent/test_dj_cohost.py, tests/agent/test_dj_cohost_streaming_pipe.py, tests/agent/test_emote_parser.py.
CONFIRM with file:line: (a) emote_parser now strips internal/voice tags from spoken text — name the exact function and the precise set of tags it strips; (b) it PRESERVES citation tokens like \`[aud:rms@12.0]\` (the strip regex/logic must NOT match citation forms [aud:...]/[src:...]); (c) run the tests: \`uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_streaming_pipe.py\`.
VERDICT: ACCEPTED iff source strips internal tags AND preserves citations, proven by passing tests. item_id="commit-a9cb2193".`,
  },
  {
    id: 'commit-c88d5f56',
    prompt: `Verify commit \`c88d5f56\` "fix(cohost): stop prompting moss voice tags" (== HEAD ${SHORT}). \`git show c88d5f56\`.
Touched: src/vibemix/agent/dj_cohost.py, src/vibemix/prompts/matrix.py + tests/agent/test_dj_cohost.py, tests/prompts/test_matrix.py.
CONFIRM with file:line: (a) the live instruction/system prompt no longer INSTRUCTS the model to emit voice/emote tags — show the before→after (what tag-prompting text was removed/replaced); (b) the tests assert the assembled prompt is tag-free; (c) run: \`uv run pytest -q tests/agent/test_dj_cohost.py tests/prompts/test_matrix.py\`.
VERDICT: ACCEPTED iff the system/instruction prompt no longer prompts for voice tags, proven by tests. item_id="commit-c88d5f56".`,
  },
  {
    id: 'contract-no-legacy-tts-tags',
    prompt: `CONTRACT CHECK (current source at HEAD ${SHORT}): the live DJCoHostAgent instruction/system prompt must NOT contain legacy Gemini TTS emotion tags \`[chill]\`, \`[excited]\`, \`[fast]\`, \`[whisper]\`.
Grep the prompt-assembly path: src/vibemix/agent/dj_cohost.py and everything under src/vibemix/prompts/ (matrix.py, filter.py, negative_dict.py). Use codegraph_trace/codegraph_context on the DJCoHostAgent prompt/instruction assembly to find where the outgoing prompt STRING is built.
CRITICAL DISTINCTION: a literal appearing only in a TEST fixture, or in a negative_dict / strip-list (i.e. a list of tags to REMOVE), is NOT a violation. A literal injected INTO the outgoing instruction/system prompt IS a violation.
Report PRESENT (=violation, a legacy tag is in the live prompt) or ABSENT (=clean), with file:line for EVERY hit and its context classified (live-prompt | test-fixture | strip-list | comment). item_id="contract-no-legacy-tts-tags".`,
  },
  {
    id: 'contract-audio-vibe-grounding',
    prompt: `CONTRACT CHECK: the audio-vibe / grounding contract must STILL EXIST after these 3 commits (the tag cleanup must not have gutted grounding).
Confirm the live prompt still injects REAL audio evidence (RMS / vibe / energy / phase) and still demands citation grounding (cardinal Invariant #2 — every citation resolves in EvidenceRegistry; un-cited reactions strip to ack-bank). Read: src/vibemix/state/coach.py (evidence-grounded prompt build), src/vibemix/state/evidence_registry.py, src/vibemix/coach/citation_linter.py, src/vibemix/prompts/matrix.py.
Confirm with file:line that the audio-evidence fields + citation grammar (e.g. \`[aud:rms@...]\`) are STILL assembled into the prompt and were NOT removed by the tag cleanup. Cross-check \`git show\` of the 3 commits to ensure none deleted grounding scaffolding.
VERDICT: PRESENT (contract intact) / PARTIAL (weakened) / ABSENT (removed). item_id="contract-audio-vibe-grounding".`,
  },
  {
    id: 'contract-no-persona-hardcode',
    prompt: `CONTRACT CHECK: NO psytrance / "Hard Tek" (hardtek/hard-techno) persona HARDCODE may remain in the DEFAULT speech prompts. Genre DETECTOR / profile infrastructure (e.g. genre/ detectors, taste model) is OK; a hardcoded default persona that makes the co-host SPEAK as if every set is psytrance/hardtek is NOT.
Grep src/vibemix/prompts/ (matrix.py, filter.py), src/vibemix/state/coach.py, src/vibemix/agent/dj_cohost.py, src/vibemix/coach/ for: psytrance, psy-trance, hardtek, "hard tek", hardtech, "hard techno". For each hit classify: DEFAULT-PROMPT-HARDCODE (violation) vs DETECTOR/PROFILE/EXAMPLE/TEST (allowed). Trace whether any matched string flows into the default (no-genre-detected) outgoing prompt.
VERDICT: PRESENT (a default-persona hardcode remains = violation) / ABSENT (clean — any hits are detector/profile only), with file:line + classification for each. item_id="contract-no-persona-hardcode".`,
  },
]

phase('Verify')
log(`Verifying ${EVIDENCE_ITEMS.length} items (3 commits + 3 contracts) at HEAD ${SHORT}, each adversarially refuted.`)

const verified = pipeline(
  EVIDENCE_ITEMS,
  it => agent(PREAMBLE + it.prompt, { label: `verify:${it.id}`, phase: 'Verify', schema: EVIDENCE_SCHEMA }),
  (ev, it) => agent(
    PREAMBLE + `ADVERSARIAL REFUTATION. Try HARD to break this verification finding for "${it.id}": find a missed file, an over-claim, a test that does not actually assert what is claimed, a regex that over/under-matches, or a path that contradicts it. Re-read the actual code/tests yourself; do not trust the finding's word.
FINDING JSON:
${JSON.stringify(ev)}

If you cannot refute it, UPHOLD it (upheld=true) and state your confidence. Default to skepticism: if a claim is unproven, mark upheld=false and say why. Always fill corrected_verdict with the verdict that actually holds. item_id="${it.id}".`,
    { label: `skeptic:${it.id}`, phase: 'Refute', schema: SKEPTIC_SCHEMA },
  ).then(sk => ({ item_id: it.id, evidence: ev, skeptic: sk })),
)

// ---- Phase 2 dedicated cross-cutting hunters (the highest-value adversarial work) ----
const huntSanitizerBypass = () => agent(
  PREAMBLE + `ADVERSARIAL READ-ONLY HUNT — the single most important check. Try to DISPROVE "every spoken/user-visible co-host output is sanitized (internal tags stripped, citations preserved, English-only)".
Find ALTERNATE co-host paths that BYPASS emote_parser/the sanitizer, or that send RAW full_text / response.text to TTS, to the transcript (ws_bus transcript_delta), or to ai_message.message.
Search and codegraph-trace: src/vibemix/agent/dj_cohost.py (llm_node, tts_node, the streaming pipe, any chunk yield), src/vibemix/agent/tts_chain.py, src/vibemix/agent/local_tts.py, src/vibemix/state/coach.py (mastered_speak / reaction_line / ack-bank fallback / any direct speak), src/vibemix/runtime/ws_bus + the transcript_delta emitter, and any \`full_text\` / \`raw\` / \`response.text\` / \`.text\` usage that reaches a spoken or displayed surface. Use codegraph_callers on the sanitizer and on the TTS/transcript emitters to enumerate ALL feeders.
For EACH spoken/user-visible path: does it provably pass through the sanitizer? DEFAULT to sanitized=false / bypass_found=true if you cannot PROVE sanitization from source. Severity-rank any bypass (CRITICAL if raw model text can reach TTS/transcript). scope="sanitizer-bypass".`,
  { label: 'hunt:sanitizer-bypass', phase: 'Refute', schema: BYPASS_SCHEMA },
)

const huntRawVsClean = () => agent(
  PREAMBLE + `ADVERSARIAL READ-ONLY. The rule: the RAW model response MAY be LOGGED raw (events.jsonl / observability artifacts), but the user-VISIBLE message and the SPOKEN characters MUST be clean (internal tags stripped, citations like [aud:rms@12.0] preserved, English-only).
Identify which field is logged raw vs which is spoken/displayed. Confirm NO path accidentally promotes the raw-logged field into TTS, transcript_delta, or ai_message.message. Check observability writers (events.jsonl, any debrief/recording capture) — raw there is fine; raw on a spoken/visible surface is a finding.
Also check the ENGLISH-ONLY constraint: is there any prompt or path that could produce non-English spoken text? Where is English enforced (prompt instruction? filter?)?
Report with file:line. bypass_found=true if any raw field reaches a user-visible/spoken surface OR if English-only is unenforced on the spoken path. scope="raw-vs-clean-and-english".`,
  { label: 'hunt:raw-vs-clean', phase: 'Refute', schema: BYPASS_SCHEMA },
)

const hunters = parallel([huntSanitizerBypass, huntRawVsClean])

// ---- Phase 3 package board ----
phase('Board')
const board = agent(
  PREAMBLE + `READ-ONLY PACKAGE-BOARD REFRESH. Read .planning/handoffs/2026-05-31-package-checklist.md (large ~248k — grep section headers first with \`rg -n "^#" \`, then read the relevant lanes). For continuity ALSO read these existing board docs if present: .planning/packets/2026-06-01/NEXT-LAND-BOARD-current-head.md, .planning/packets/2026-06-01/CODEX_READY-next-land-board.md, .planning/packets/2026-06-01/DRIFT-current-head.md, .planning/packets/2026-06-01/INDEX.md.
TASK: identify the NEXT 3 safest + highest-value packages for Codex to land NEXT (after HEAD ${SHORT}). Split SAFE_NOW vs HOLD; for every HOLD give the EXACT gate that must clear first. For each package: name, disposition, rank, value, risk, shared_files touched, gate, evidence (lane/file ref).
Then build a SHARED-FILE RISK register for EXACTLY these files — verify each exists (there may be BOTH src/vibemix/state/coach.py AND src/vibemix/runtime/coach.py; check), and run \`git status --porcelain\` to mark dirty_now: src/vibemix/__main__.py, src/vibemix/runtime/coach.py, src/vibemix/state/coach.py, src/vibemix/agent/dj_cohost.py, src/vibemix/prompts/matrix.py. For each: exists, dirty_now, contending_lanes, and the hunk-staging caution (whole-file \`git add\` risks bleeding another lane's hunks or a HOLD item into a LAND commit).
Be concrete and current — cross-check the live dirty tree, do not just restate old docs.`,
  { label: 'board:next-3', phase: 'Board', schema: BOARD_SCHEMA },
)

const [evResults, huntResults, boardResult] = await Promise.all([verified, hunters, board])

return {
  head: HEAD,
  short: SHORT,
  branch: 'live-tuning-or-brain',
  commits_verified: ['de9a55f5', 'a9cb2193', 'c88d5f56'],
  evidence: evResults,
  hunters: huntResults,
  board: boardResult,
}
