export const meta = {
  name: 'meta-audit-supplement',
  description: 'Recover the 3 meta-audit lenses lost to the rate limit, then re-synthesize the complete ranked board. Schema-less. Read-only. args:{good_lenses,critic} via _meta_supplement_input.json content.',
  phases: [
    { title: 'Recover', detail: 'rerun the 3 lost lenses (product-ready, surfaced-but-fake, packaging-ship-truth)' },
  ],
}

const RO = `READ-ONLY strategist. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain, HEAD ~173399ae).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app. ALLOWED: git read ops, ripgrep/grep, Read, codegraph, targeted \`uv run pytest\` (repo .venv). Evidence: file:line / packet / NOT-FOUND.
PRODUCT TRUTH: AI DJ co-host, "real DJ friend, no slop". MOSS is the only TTS (no cloud/fake spoken fallback). English-only at runtime. No fake fallback — abstain honestly. Goal = clean, maintainable, HONESTLY-shippable monetized app where every surviving capability is wired, visible, tested, honest.
READ: .planning/packets/2026-06-01/CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md, CLAUDE_LAST_DELTA_DRIFT.md, CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md, CODEX_VERIFICATION-cohost-grounding-tts-tags.md, CODEX_PACKAGE_SWEEP_STATUS.md, INDEX.md.
BUCKETS: SAFE_NOW | HOLD_WITH_GATE | DROP | RESEARCH_WITH_WORKFLOW.
Finding format: \`- **<title>** — \\\`[BUCKET]\\\` — <why, 1-2 sentences> — evidence: file:line/packet/NOT-FOUND — gate: <exact gate or "none">\``

const LOST = [
  { id: 'product-ready', focus: `WHAT IS TRULY PRODUCT-READY. Cross-check the inventory's WORKS_AND_PROVEN (108) + WORKS_SOURCE_ONLY (106) against the "real DJ friend, no slop" bar. Which capabilities are genuinely ready to ship to a paying user TODAY (grounded, honest, wired, tested)? Be strict — SOURCE_ONLY without a live path is NOT yet product-ready. List the ready core + what each still needs for a true PROVEN promotion.` },
  { id: 'surfaced-but-fake', focus: `SURFACED BUT FAKE / UNWIRED. Find any UI surface or spoken behavior that LOOKS real but is placeholder/demo/unwired: dead buttons, demo-scaffolding (sim.live/sim.idle, demo_mode, DEMO_SEQUENCE), honest-placeholder panels shown as live (GroundingPanel body), any fake fallback path. These directly break trust. Each → fix-wire or remove-the-fake, with file:line.` },
  { id: 'packaging-ship-truth', focus: `PACKAGING / SHIP TRUTH. The honest gap between "verified in source" and "a stranger installs the DMG and hears the co-host". Is the newest dist/ DMG current to HEAD or stale (check mtime vs commit times)? signed/notarized/stapled? Is the MOSS model bundled OR auto-downloaded on a fresh machine (or does the app boot mute)? Is the keyless Bravoh proxy live? List concretely what blocks an honest shippable build TODAY, each bucketed.` },
]

phase('Recover')
log('Recovering 3 rate-limited lenses.')
const recovered = (await parallel(LOST.map(l => () => agent(RO + `AUDIT LENS — ${l.id}.\n${l.focus}\nReturn a markdown "## <lens>" section with findings per the finding format. lens="${l.id}".`, { label: `lens:${l.id}`, phase: 'Recover' })))).filter(Boolean)

return { workflow: 'meta-audit-supplement', recovered_count: recovered.length, recovered }
