export const meta = {
  name: 'drift-refresh',
  description: 'Read-only drift refresh: verify the new commits since the last drift baseline up to current HEAD; HOLD-bleed + FLX4-proof-hold sentinel. Schema-less prose. No product edits/stage/commit/app-launch. args:{since}.',
  phases: [
    { title: 'Verify', detail: 'commit verification + HOLD-bleed/FLX4 sentinel' },
    { title: 'Synthesize', detail: 'drift-update markdown block' },
  ],
}

const SINCE = (args && args.since) || 'f29defb6'

const RO = `READ-ONLY agent. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app. ALLOWED: \`git show/log/diff/status\`, ripgrep/grep, Read, codegraph, TARGETED \`uv run pytest -q <files>\` (repo .venv; system python3=3.14 lacks livekit). Evidence rule: file:line / test result / NOT-FOUND. LAND/HOLD posture: anything changing what the co-host SAYS or WHEN it speaks is HOLD unless it has vibemix-grounding-review + proof. MOSS is the only TTS; English-only must be runtime-enforced, not just prompt. No fake fallback — abstain honestly. Return MARKDOWN only (your final text is the deliverable).`

phase('Verify')
log(`Drift refresh ${SINCE}..HEAD`)
const lanes = (await parallel([
  () => agent(RO + `COMMIT VERIFIER. Run \`git rev-parse HEAD\` then \`git log --oneline ${SINCE}..HEAD\`. For EACH commit in that range: read it (\`git show <sha>\`), state what it changes at file:line, run its touched tests (targeted), and classify LAND (clean, in-posture) / HOLD (changes speech/timing without grounding-review) / CONCERN (missing proof / over-claim). Pay special attention to: 6556e23a (bound auto cues to audible material), b8d19ba2 (split freshness watcher module), c2cb9aaa (sequence novelty dial), d321eef5 (close drift guard expectations — a cohost test: what does it now assert?), 4ac30b5d + 173399ae (planning-doc HOLD records — confirm they only RECORD holds, not land speech). Return a markdown "### Commit verification" list.`, { label: 'drift:commits', phase: 'Verify' }),
  () => agent(RO + `HOLD-BLEED + FLX4 SENTINEL. (1) Is the DROP-call live hype SPEECH block still DIRTY-ONLY (not committed)? Check \`git show HEAD:src/vibemix/runtime/coach.py | rg -n "reaction_line|drop_cue|mastered_speak"\` and the dirty diff. (2) Did any commit in ${SINCE}..HEAD introduce a NEW spoken trigger or relax a grounding gate without a review trail? (3) FLX4 proof status: read the latest FLX4 hold record (commit 173399ae / .planning/handoffs/*flx4* / .planning/packets/2026-06-01/CODEX_HOLD-flx4-live-acceptance-current.md). Confirm the HONEST hold reason: deck_state unresolved + BlackHole 16ch proved only A_active+B_silent (not both deck lanes). Is the hold recorded honestly (no false "accepted" claim)? Return a markdown "### HOLD-bleed + FLX4 sentinel" block with file:line + an explicit bleed_found yes/no.`, { label: 'drift:sentinel', phase: 'Verify' }),
  () => agent(RO + `CHECKER + STALE-CLAIM. (1) Run \`python3 scripts/check_dirty_package_plan.py --strict-assignments --summary\` → GREEN/RED. (2) Run \`uv run pytest -q tests/repo\` → report pass/fail (the prior drift flagged tests/repo/test_no_seen_relaxation.py RED — is it still RED at HEAD, or fixed by d321eef5?). (3) Re-confirm the two prior resolved findings still hold at HEAD: english-only runtime guard (src/vibemix/agent/language_guard.py wired in dj_cohost.py) and citation-out-of-TTS (src/vibemix/agent/tts_sanitizer.py wired in dj_cohost.py) — give file:line. Return a markdown "### Checker + stale-claim recheck" block.`, { label: 'drift:checker', phase: 'Verify' }),
])).filter(Boolean)

phase('Synthesize')
const block = await agent(RO + `Write a concise markdown UPDATE section titled "## Update — drift through current HEAD (${SINCE}..HEAD)" merging the three lane reports below. Lead with a one-line verdict (SAFE to keep landing? any CRITICAL? is the tests/repo regression fixed?). Then the commit table, the HOLD-bleed+FLX4 verdict, and the checker/stale-claim status. Keep it tight and evidence-anchored. Output ONLY the markdown (no fence, no preamble).
LANES:\n\n${lanes.join('\n\n')}`, { label: 'drift:synth', phase: 'Synthesize' })

return { workflow: 'drift-refresh', since: SINCE, lanes, docMarkdown: block }
