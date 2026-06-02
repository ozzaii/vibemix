export const meta = {
  name: 'meta-audit-next-board',
  description: 'Read-only cross-system audit → ranked Codex board (SAFE_NOW / HOLD_WITH_GATE / DROP / RESEARCH_WITH_WORKFLOW). Synthesizes code + packets + inventory + drift + ledger + Mixxx research. Schema-less. No product edits/stage/commit/app-launch.',
  phases: [
    { title: 'Lenses', detail: '8 cross-silo audit lenses in parallel' },
    { title: 'Critic', detail: 'completeness critic — what did the lenses miss?' },
    { title: 'Board', detail: 'ranked implementation board + coherent-first-product thesis' },
  ],
}

const RO = `READ-ONLY strategist. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain, HEAD ~173399ae).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app. ALLOWED: git read ops, ripgrep/grep, Read, codegraph, targeted \`uv run pytest\` (repo .venv). Evidence rule: file:line / packet path / test / NOT-FOUND.
PRODUCT TRUTH: vibemix is an AI DJ co-host — bar is "real DJ friend in your ear, no AI slop". MOSS is the only TTS (no cloud/fake spoken fallback). English-only at runtime. No fake fallback — abstain honestly when evidence is missing. Goal = a clean, maintainable, HONESTLY-shippable monetized app where every surviving capability is wired, visible, tested, honest.
SYNTHESIZE, don't re-explore aimlessly. READ FIRST (already written this session): .planning/packets/2026-06-01/CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md (282-cap map), CLAUDE_LAST_DELTA_DRIFT.md, CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md (if present), CODEX_VERIFICATION-cohost-grounding-tts-tags.md, INDEX.md, CODEX_PACKAGE_SWEEP_STATUS.md, CODEX_GOLD_STRUCTURE.md, .planning/handoffs/2026-05-31-package-checklist.md, and the recovered Mixxx-goldmine maps referenced in INDEX §2.
BUCKETS for every recommendation: SAFE_NOW | HOLD_WITH_GATE | DROP | RESEARCH_WITH_WORKFLOW.

OUTPUT FORMAT — return a MARKDOWN block ONLY. Each finding:
- **<title>** — \`[BUCKET]\` — <why it matters in 1-2 sentences> — evidence: \`file:line\`/packet/NOT-FOUND — gate: <for HOLD_WITH_GATE, the exact gate; else "none">`

const LENSES = [
  { id: 'product-ready', focus: `WHAT IS TRULY PRODUCT-READY. Cross-check the inventory's WORKS_AND_PROVEN + WORKS_SOURCE_ONLY against the "real DJ friend, no slop" bar. Which capabilities are genuinely ready to ship to a paying user TODAY (grounded, honest, wired, tested)? Be strict — SOURCE_ONLY without a live path is NOT yet product-ready. List the ready core.` },
  { id: 'built-not-surfaced', focus: `BUILT BUT NOT SURFACED. From the inventory's CLI_ONLY + PRESENT_ORPHANED + WIRED_BUT_UNPROVEN: what real capability exists in code but a user can't reach or see it in the app? Each is either a quick surface-it win or a delete. Rank the highest-value "hidden capability to surface".` },
  { id: 'surfaced-but-fake', focus: `SURFACED BUT FAKE / UNWIRED. Find any UI surface or spoken behavior that LOOKS real but is placeholder/demo/unwired (dead buttons, demo-scaffolding like sim.live, honest-placeholder panels shown as live, any fake fallback). These directly break trust. Each → fix-wire or remove-the-fake.` },
  { id: 'valuable-but-drop', focus: `VALUABLE BUT SHOULD BE DROPPED. What is genuinely interesting but is scope-creep / maintenance debt / dilutes the coherent first product (e.g. mascot path, over-built silos, duplicate systems, research-only modules masquerading as features)? Recommend DROP or DEFER with the reasoning — a smaller honest product beats a big half-wired one.` },
  { id: 'duplicate-architecture', focus: `DUPLICATE PATHS / ARCHITECTURE DEBT. Two coach.py files, multiple TTS builders (direct vs proxy), overlapping event/cooldown logic, duplicate caches, parallel CLI-vs-GUI doing the same job. For each: consolidate, or justify the split. Maintainability is a product priority.` },
  { id: 'coherent-first-product', focus: `WHAT MAKES THE FIRST SHIPPABLE MONETIZED APP COHERENT. Given monetization (Free / €4.99 Pro / €9.99 Studio per the knowbook), what is the MINIMUM coherent feature set that is honest + grounded + maintainable + demoable? What must be TRUE end-to-end (co-host speaks grounded via MOSS, English-only, library/Viber that works, one honest live proof)? Name the coherent v1 spine and what's outside it.` },
  { id: 'packaging-ship-truth', focus: `PACKAGING / SHIP TRUTH. The honest gap between "verified in source" and "a stranger installs the DMG and hears the co-host". Is the newest DMG current? signed/notarized? MOSS model bundled/downloadable on a fresh machine? proxy live? What concretely blocks an honest shippable build TODAY?` },
  { id: 'mixxx-goldmine-leverage', focus: `MIXXX GOLDMINE LEVERAGE. From the recovered goldmine research, which 1-3 ideas (beatgrid/phrase, cue logic, key detection, EQ/filter, crossfader math) most cheaply close a real grounding/slop gap and shorten the honest-ship path? GPL-2.0 = learn-from-spec only — flag vendoring risk. Everything else = RESEARCH_WITH_WORKFLOW or DROP.` },
]

phase('Lenses')
log(`Running ${LENSES.length} cross-system audit lenses (schema-less).`)
const lensBlocks = (await parallel(LENSES.map(l => () => agent(RO + `AUDIT LENS — ${l.id}.\n${l.focus}\nReturn a markdown "## <lens>" section with findings per OUTPUT FORMAT. lens="${l.id}".`, { label: `lens:${l.id}`, phase: 'Lenses' })))).filter(Boolean)

phase('Critic')
const critic = await agent(RO + `COMPLETENESS CRITIC. The ${lensBlocks.length} lenses below produced these findings. What did they MISS — an unaudited area, an unverified strong claim, a cross-silo gap where two findings interact (e.g. a duplicate path that is ALSO a fake surface), an honesty/slop risk no lens owns, or a "shortest honest-ship" blocker? Return a markdown "## Critic — gaps" section with the same finding format.
LENS FINDINGS:\n\n${lensBlocks.join('\n\n')}`, { label: 'critic:gaps', phase: 'Critic' })

phase('Board')
const doc = await agent(RO + `Write the FULL markdown BODY for CLAUDE_META_AUDIT_NEXT_BOARD.md. Structure:
(1) "## Are we building the right thing?" — a direct 1-paragraph verdict + the coherent-first-product spine (from the coherent-first-product lens) + the 3-5 things that actually block an honest ship;
(2) "## Ranked implementation board" — a single table ranked by shortest-honest-ship value: columns [Rank | Item | Bucket (SAFE_NOW / HOLD_WITH_GATE / DROP / RESEARCH_WITH_WORKFLOW) | Why | Gate | Evidence], SAFE_NOW first;
(3) "## Architecture & honesty cleanup" — duplicate paths, dead/fake surfaces, things to delete (LAND-able maintainability wins);
(4) "## Drop / defer" — scope-creep to cut for the coherent v1;
(5) "## Research-with-workflow" — the open questions that need a spike, each with the workflow to run.
Merge/dedupe overlapping findings across lenses; fold in the critic's gaps. Decisive + evidence-anchored. Output ONLY the markdown body (no fence, no preamble).
LENSES:\n\n${lensBlocks.join('\n\n')}\n\nCRITIC:\n${critic}`, { label: 'board:synth', phase: 'Board' })

return { workflow: 'meta-audit-next-board', lensBlocks, critic, docMarkdown: doc }
