export const meta = {
  name: 'meta-audit-next-strategy',
  description: 'Read-only cross-silo strategic audit: right-goal check, fake fallbacks, duplicate paths, dead surfaces, Viber/Learn/packaging truth, Mixxx-goldmine adoption, shortest honest-ship path. Produces a ranked LAND/HOLD board. No product edits/stage/commit/app-launch.',
  phases: [
    { title: 'Lenses', detail: '8 cross-silo audit lenses in parallel' },
    { title: 'Critic', detail: 'completeness critic — what did the lenses miss?' },
    { title: 'Board', detail: 'synthesize CLAUDE_META_AUDIT_NEXT_STRATEGY.md — ranked board + gates' },
  ],
}

const RO = `READ-ONLY strategist. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app. ALLOWED: git read ops, ripgrep/grep, Read, codegraph, targeted \`uv run pytest\` (repo .venv). Evidence rule: file:line / test / doc anchor or NOT-FOUND.
PRODUCT TRUTH: vibemix is an AI DJ co-host — bar is "real DJ friend in your ear, no AI slop". MOSS is the only TTS (no cloud/fake spoken fallback). Anything changing what the co-host SAYS or WHEN it speaks is HOLD unless it has vibemix-grounding-review + proof. Do not assert live DJ/controller/deck causality without evidence.
READ FIRST (this run's upstream evidence, already written this session): .planning/packets/2026-06-01/CLAUDE_LAST_DELTA_DRIFT.md, .planning/packets/2026-06-01/CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md. ALSO: INDEX.md, CODEX_PACKAGE_SWEEP_STATUS.md, CODEX_GOLD_STRUCTURE.md, .planning/handoffs/2026-05-31-package-checklist.md.
`

const LENS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    lens: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] },
      title: { type: 'string' }, evidence: { type: 'string', description: 'file:line / doc anchor / NOT-FOUND' },
      recommendation: { type: 'string' }, land_or_hold: { type: 'string', enum: ['LAND', 'HOLD', 'DROP', 'INVESTIGATE'] },
      gate: { type: 'string' } }, required: ['severity', 'title', 'evidence', 'recommendation'] } },
    lens_summary: { type: 'string' },
  }, required: ['lens', 'findings', 'lens_summary'],
}

const LENSES = [
  { id: 'fake-fallbacks-slop', focus: `FAKE FALLBACKS / SLOP SURFACES. Hunt anything that fabricates: hardcoded "smart-sounding" fallbacks, ack-bank lines that could read as real reactions, any spoken text not grounded in real evidence, placeholder data shown as real, invented citations/timestamps, generic AI phrasing. Cross-check the anti-slop invariants (citation grounding, trust-the-audio). Rank by how badly each would break "real DJ friend, no slop".` },
  { id: 'duplicate-paths', focus: `DUPLICATE / REDUNDANT SYSTEMS. Find parallel implementations of the same job: two coach.py files, multiple TTS chain builders, overlapping event/cooldown logic, duplicate embedding/centroid caches, two config writers, parallel CLI vs GUI paths doing the same thing. For each: is the duplication intentional (BYO vs proxy) or debt to consolidate?` },
  { id: 'dead-buttons-hidden', focus: `DEAD BUTTONS / HIDDEN CAPABILITIES. One-ended IPC types (sender without handler or vice-versa), UI controls that do nothing, capabilities that exist in code but are unreachable from the app (CLI-only that should be surfaced), feature flags defaulting OFF that hide working features. Use the ipc both-end discipline.` },
  { id: 'viber-product-mismatch', focus: `VIBER / PRODUCT MISMATCH. Compare what the Viber curator/set-prep ACTUALLY does (toolset/codex_curate/mcp_server) vs what docs/launch copy claim. Freshness guards, fail-closed behavior, the Codex dependency (not bundled), the Telegram surface. Where does the product promise more than the code delivers? Where is a real capability under-surfaced?` },
  { id: 'learn-earned-reality', focus: `LEARN / EARNED REALITY. v11.0 "Earned" — does the lesson→Competent / cited-live-demo→Mastered gate actually work end-to-end, or are stages credited without real producers? The BEATMATCH_GRADED missing-producer honesty boundary. Is stored mastery honestly masked when no producer exists? What's the smallest real producer that unlocks the headline competency?` },
  { id: 'packaging-release-truth', focus: `PACKAGING / RELEASE TRUTH. Does the newest signed DMG match current HEAD? Is it signed/notarized/stapled/Gatekeeper-clean AND does its sidecar boot clean? Is the MOSS model bundled or downloadable on a fresh machine (or does the app go mute/crash)? Is the keyless proxy live with a real key? What is the HONEST gap between "verified in source" and "a stranger can run it and hear the co-host"?` },
  { id: 'mixxx-goldmine-adopt', focus: `MIXXX / GOLDMINE ADOPTION. From the recovered goldmine maps, which researched ideas are worth adopting NOW for the shortest honest-ship path (beatgrid/phrase, cue logic, key detection, EQ/filter, crossfader math)? Which are over-scope? GPL-2.0 = learn-from-spec only — flag any vendoring risk. Prioritize ideas that close a slop/grounding gap over net-new features.` },
  { id: 'goal-shortest-honest-ship', focus: `THE BIG QUESTION — are we optimizing the right goal? The goal is an honestly-shippable "real DJ friend in your ear" co-host, not a feature pile. Given the inventory + drift, what is the SHORTEST path to a product we can ship without lying? What must be TRUE (co-host speaks, grounded, MOSS audible, packaged, one real test set)? What is scope-creep that should be DEFERRED? Name the 3-5 things that actually block an honest ship vs the long tail.` },
]

phase('Lenses')
log(`Running ${LENSES.length} cross-silo audit lenses.`)
const lensResults = await parallel(LENSES.map(l => () => agent(RO + `AUDIT LENS — ${l.id}.\n${l.focus}\nGround every finding in file:line / doc anchor / NOT-FOUND. Give each a recommendation + LAND/HOLD/DROP/INVESTIGATE + gate. lens="${l.id}".`, { label: `lens:${l.id}`, phase: 'Lenses', schema: LENS_SCHEMA })))

phase('Critic')
const live = lensResults.filter(Boolean)
const critic = await agent(RO + `COMPLETENESS CRITIC. The 8 lenses produced the findings below. What did they MISS — an unaudited silo, an unverified strong claim, a cross-silo gap where two findings interact (e.g. a duplicate path that is ALSO a slop surface), a maintainability/architecture debt not captured, or a "shortest honest-ship" blocker no single lens owns? Return the gaps as additional findings with the same fields.
LENS FINDINGS:\n${JSON.stringify(live)}`, { label: 'critic:completeness', phase: 'Critic', schema: LENS_SCHEMA })

phase('Board')
const findings = { lenses: live, critic }
const docMarkdown = await agent(RO + `SYNTHESIS — write the FULL markdown body for CLAUDE_META_AUDIT_NEXT_STRATEGY.md. Structure: (1) "Are we on the right goal?" — a direct 1-paragraph verdict + the 3-5 things that actually block an honest ship; (2) RANKED IMPLEMENTATION BOARD — a table (Rank | Item | LAND/HOLD | Why it matters | Gate | Evidence) ordered by shortest-honest-ship value, SAFE_NOW/LAND first then HOLD; (3) Architecture / maintainability cleanup (duplicate paths, dead surfaces, fake fallbacks to remove) as its own LAND-able list; (4) Defer / out-of-scope list (what NOT to do now); (5) Mixxx-goldmine adopt shortlist. Reconcile/merge overlapping findings across lenses; fold in the critic's gaps. Keep it decisive and evidence-anchored. Output ONLY the markdown body (no outer fence, no preamble) — written verbatim to the doc.
EVIDENCE:\n${JSON.stringify(findings)}`, { label: 'board:synthesis', phase: 'Board' })

return { workflow: 'meta-audit-next-strategy', findings, docMarkdown }
