export const meta = {
  name: 'open-question-decision-ledger',
  description: 'Read-only: harvest unresolved vibemix questions; for each → decision LAND/HOLD/DROP/RESEARCH + why + evidence file:line + risk + exact Codex package. Schema-less prose. No product edits/stage/commit/app-launch.',
  phases: [
    { title: 'Decide', detail: '11 question agents, each researches one open question → a decision block' },
    { title: 'Ledger', detail: 'assemble the ranked decision ledger' },
  ],
}

const RO = `READ-ONLY decision researcher. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain, HEAD ~173399ae).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app. ALLOWED: \`git show/log/diff/status\`, ripgrep/grep, Read, codegraph, TARGETED \`uv run pytest -q <files>\` (repo .venv; system python3=3.14 lacks livekit). Evidence rule: every claim has a file:line, packet path, test result, or explicit NOT-FOUND.
PRODUCT PRINCIPLES: MOSS is the only TTS (no cloud/fake spoken fallback). Co-host English-only at RUNTIME (not just prompt). No fake fallback — if evidence is missing, abstain / show an honest reason. Priority = a clean, maintainable app where every surviving capability is wired, visible, tested, and honest.
CONTEXT DOCS to read as needed: .planning/packets/2026-06-01/CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md, CLAUDE_LAST_DELTA_DRIFT.md, CODEX_VERIFICATION-cohost-grounding-tts-tags.md, NEXT-LAND-BOARD-after-c88d5f56.md, INDEX.md, CODEX_PACKAGE_SWEEP_STATUS.md, .planning/handoffs/2026-05-31-package-checklist.md.

OUTPUT FORMAT — return a MARKDOWN block ONLY (your final text is the deliverable), exactly:
### <n>. <question title>
- **Decision:** LAND | HOLD | DROP | RESEARCH
- **Why:** <1-3 sentences, decisive>
- **Evidence:** \`file:line\` / packet / test / NOT-FOUND (2-5 anchors)
- **Risk:** <what breaks if wrong, or the slop/honesty risk>
- **Codex package:** <exact, narrow next package — title + files-in/out + gate, or "none / close-out">
Be decisive. If the question is already resolved at HEAD, say so (Decision: LAND/close-out) with the commit that resolved it. If it needs investigation you cannot finish read-only, Decision: RESEARCH with the specific spike.`

const QUESTIONS = [
  { id: 'q1-english-only-backstop', q: `English-only RUNTIME backstop. Is non-English spoken output now blocked at runtime (not just prompt)? Codex landed b5916eb0 + agent/language_guard.py — verify it is wired on the spoken path (dj_cohost.py), tested, and actually prevents non-English reaching TTS/transcript. Decide LAND/close-out vs RESEARCH (precision gap).` },
  { id: 'q2-citation-atoms-tts', q: `Citation atoms reaching MOSS. Are [aud:rms@..]/[ev:..] atoms stripped from the TTS input while preserved on the visible transcript/receipt? Codex landed 54ec38be + agent/tts_sanitizer.py (model_text_for_tts). Verify wiring + tests. Decide LAND/close-out vs RESEARCH.` },
  { id: 'q3-deck-identity-source', q: `Deck identity source. What resolves deck_state / which deck is which (MIDI vs Rekordbox-live vs screen-vision vs BlackHole lane)? This is the core of the FLX4 hold (deck_state unresolved, 16ch proved only A_active+B_silent). Map the current resolver(s) at file:line and decide the path: LAND a deterministic resolver, HOLD pending hardware, or RESEARCH a spike.` },
  { id: 'q4-blackhole-rekordbox-setup-ux', q: `BlackHole / Rekordbox setup UX. Today routing is manual (Audio MIDI Setup, route only the DJ app into BlackHole). Is there an in-app setup/verify flow (wizard probe)? Should there be a guided setup + a "your routing is wrong" honest detector? Decide LAND a setup-verify surface vs RESEARCH vs HOLD.` },
  { id: 'q5-screen-vision-vs-rekordbox', q: `Screen vision vs Rekordbox live source. The co-host can read the DJ-app screen (Quartz crop) AND/OR Rekordbox state. Which is authoritative live, are both wired, do they conflict, and is one redundant? Decide: keep both, DROP one, or RESEARCH the arbitration.` },
  { id: 'q6-viber-fs-watcher', q: `Viber filesystem watcher. Is there an event-driven library fs-watcher (so a mid-session re-export refreshes freshness beyond the 10s poll)? Note b8d19ba2 "split freshness watcher module" — verify what it actually does (real watchfiles watcher vs just a refactor). Decide LAND (finish the watcher) vs close-out.` },
  { id: 'q7-viber-tool-surfaces', q: `Viber tool surfaces. Inventory the grounded MCP tools (toolset/mcp_server) — which are wired + tested, which are claimed-but-absent, which are CLI-only vs surfaced in the GUI crate. Decide which to LAND/surface, DROP, or leave.` },
  { id: 'q8-mixxx-goldmine-adopt', q: `Mixxx goldmine ideas worth adopting. From the recovered goldmine maps (beatgrid/phrase, cue logic, key detection, EQ/filter DSP, crossfader math, tempo/phase sync), which 1-3 are highest-value for the shortest honest-ship path and close a real grounding/slop gap? GPL-2.0 = learn-from-spec only (flag vendoring risk). Decide RESEARCH/ADOPT per idea.` },
  { id: 'q9-beatmatch-producer', q: `Beatmatch producer. BEATMATCH_GRADED has a consumer + payload builder but NO real-time owned-deck producer (Mastered uncreditable by design). Decide: HOLD (needs hardware producer + live proof) vs RESEARCH the smallest producer that honestly unlocks the headline competency. Give the gate.` },
  { id: 'q10-drop-speech-hold', q: `DROP speech hold. The DROP-call live hype line is dirty-only, gated. 4ac30b5d records the hold. Decide: keep HOLD (with the exact gate: grounding-review + on-beat live proof + FP rate) vs DROP the feature vs LAND (only if the gate is somehow already met). Be specific on the gate.` },
  { id: 'q11-learn-module-reality', q: `Learn module reality. v11.0 Earned: does lesson→Competent / cited-live-demo→Mastered actually work end-to-end, or are stages credited without real producers? Which competencies have real producers vs honest-masked? Decide what to LAND (close real gaps), HOLD (honesty-masked, needs producer), or DROP (over-scope).` },
]

phase('Decide')
log(`Deciding ${QUESTIONS.length} open questions (schema-less).`)
const blocks = (await parallel(QUESTIONS.map((it, i) => () => agent(RO + `OPEN QUESTION ${i + 1}/${QUESTIONS.length}.\n${it.q}\nReturn the decision block per OUTPUT FORMAT (number it ${i + 1}).`, { label: `q:${it.id}`, phase: 'Decide' })))).filter(Boolean)

phase('Ledger')
const doc = await agent(RO + `Assemble the FULL markdown BODY for CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md from the ${blocks.length} decision blocks below. Start with (1) a one-line summary of the decision spread (how many LAND/HOLD/DROP/RESEARCH); (2) a compact decision table (Question | Decision | Codex package); (3) then all decision blocks verbatim, ordered LAND → HOLD → RESEARCH → DROP. Output ONLY the markdown body (no fence, no preamble).
DECISION BLOCKS:\n\n${blocks.join('\n\n')}`, { label: 'ledger:assemble', phase: 'Ledger' })

return { workflow: 'open-question-decision-ledger', question_count: blocks.length, blocks, docMarkdown: doc }
