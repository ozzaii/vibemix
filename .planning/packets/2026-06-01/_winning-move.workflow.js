export const meta = {
  name: 'vibemix-winning-move',
  description: 'Meta-critique + license-strategy + codegraph wiring-gap + post-Codex future + the $$$ winning-move panel → master plan',
  phases: [
    { title: 'Critique', detail: 'what we lost / what is missing / where it could go deeper / honesty-debt' },
    { title: 'License', detail: 'Apache vs GPL — how much more can we snort from Mixxx if we flip' },
    { title: 'Wiring', detail: 'codegraph/LSP structural gaps — orphan producers/consumers, dead exports, NOT-FOUND' },
    { title: 'Future', detail: 'if Codex lands the whole queue, what do we have + the new packet backlog' },
    { title: 'Money', detail: '5 strategists + 3 judges → the play that makes this win real money' },
    { title: 'Synthesis', detail: 'one master doc tying it all into a sequenced winning plan' },
  ],
}

const REPO = '/Users/ozai/projects/dj-set-ai'
const HEAD = 'ed081570'
const PK = REPO + '/.planning/packets/2026-06-01'

const DOC = {
  critique: PK + '/CRITIQUE-LOST-AND-MISSING.md',
  license:  PK + '/LICENSE-STRATEGY-APACHE-VS-GPL.md',
  wiring:   PK + '/WIRING-GAP-MAP-CODEGRAPH.md',
  future:   PK + '/POST-CODEX-FUTURE-AND-PACKET-BACKLOG.md',
  money:    PK + '/THE-WINNING-MOVE.md',
  master:   PK + '/MASTER-WHERE-WE-WIN-2026-06-01.md',
}

const RULES = `
You are a READ-ONLY senior analyst on **vibemix** — a commercial AI DJ co-host (free Apache-licensed client + commercial Bravoh proxy). Repo: ${REPO}. HEAD: ${HEAD}.
HARD CONTRACT: never edit product code (src/, tauri/), never git stage/commit, never launch the app. You produce analysis + planning docs ONLY (writing under ${PK} is allowed).
GROUND every claim in file:line, codegraph evidence, a packet path, or an explicit "NOT-FOUND". No hand-waving, no AI slop, no flattery. Kaan EXPLICITLY wants the honest critic — if something is fantasy or wrong, say so and kill it. Truth over a tidy story.
TOOLS: use the codegraph MCP for wiring truth — call ToolSearch with query "codegraph" then use codegraph_search / codegraph_callers / codegraph_callees / codegraph_impact / codegraph_trace / codegraph_status. Use LSP via ToolSearch "select:LSP" for defs/refs when codegraph is thin. Use Grep/Glob/Read for source and WebSearch (ToolSearch "select:WebSearch") for external facts.
READ FIRST (under ${PK}): FEATURE-STATE-OF-THE-UNION.md (the per-feature truth map), GOLD-WIRING-MAP.md (orphaned-intelligence map), RED-TEAM-SHIP-REALITY.md (the 5 ways it dies), CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md (282-cap classified map), CLAUDE_LAND_QUEUE.md (Codex routing board), and the recovered/ subdir (workflow gold that may never have been built — the d9ddbeed EQ packet, the c297207c mixxx-goldmine map, creative-forge ideas).
The product's CORE VALUE: "a real DJ friend in your ear, grounded in real events, never AI slop." The anti-slop citation gate is the moat, not a constraint.
OUTPUT: markdown PROSE (no JSON, no StructuredOutput call). Be dense and specific.
`

const join = (arr) => arr.filter(Boolean).map((t, i) => '### Analyst input ' + (i + 1) + '\n\n' + t).join('\n\n---\n\n')

// ---------------------------------------------------------------- PHASE 1: CRITIQUE
phase('Critique')
log('Phase 1/6 — Critique: what we lost, what is missing, where it could go deeper')

const critiqueLenses = await parallel([
  () => agent(`${RULES}
LENS = **LOST GOLD**. Kaan: "we ran a billion workflows and the findings ended up as more custom code + planning packets, not wired features. What did we LOSE?"
Hunt every piece of intelligence that was DISCOVERED in a workflow / research / handoff and then NEVER built, abandoned, or deleted. Sources: ${PK}/recovered/*, ${REPO}/.planning/handoffs/*, ${REPO}/.planning/research/*, ${REPO}/.planning/archive/*, and the memory pointers in the FEATURE-STATE idea-graveyard.
For EACH lost item: (a) what the workflow proved/designed, (b) codegraph-confirm it does NOT exist in src/ (NOT-FOUND), (c) why it died (GPL? scope? forgotten?), (d) revive cost (hours/days) and leverage. Rank by (leverage / cost). This is the "buried treasure" list.`,
    { label: 'lens:lost-gold', phase: 'Critique' }),

  () => agent(`${RULES}
LENS = **MISSING PRODUCT**. Compare what a winning live DJ co-host MUST have against what vibemix actually ships (use FEATURE-STATE + inventory). What capability would a real DJ expect that we simply don't have — at the perception layer (what it hears/sees), the reaction layer (what it says/does), and the loop (memory, learning, personalization)? Separate "missing because hard" from "missing because never attempted". Be concrete: name the feature, the user moment it serves, and whether the building blocks already exist orphaned.`,
    { label: 'lens:missing-product', phase: 'Critique' }),

  () => agent(`${RULES}
LENS = **GO DEEPER**. For the engines that DO exist and work (the Vibe Judge, intel scorers transition_scorer/taste_model, CLAP retrieval + mean-centering, the skill-tree, the citation/evidence grounding spine), ask: where could each go 10x deeper / more alive / more "real DJ friend"? Where are we shipping a shallow version of something that could be the moat? Ground each in the actual module (file:line) and codegraph-confirm it's reachable. Distinguish "deepen the existing engine" from "new build".`,
    { label: 'lens:go-deeper', phase: 'Critique' }),

  () => agent(`${RULES}
LENS = **HONESTY DEBT** (adversarial). Find every place the product/docs CLAIM more than the code delivers — start from the inventory's 17 CLAIMED_BUT_ABSENT + RED-TEAM's claim≠real list, then go hunting for more. For each: the claim, the reality (file:line / NOT-FOUND), the severity if a paying user hits it, and the cheapest honest fix (deliver it, scope the copy, or cut the claim). This is what would get us roasted on launch — surface it brutally.`,
    { label: 'lens:honesty-debt', phase: 'Critique' }),
])

const critiqueSummary = await agent(`${RULES}
You are the CRITIQUE SYNTHESIZER. Below are 4 analyst lenses (lost-gold, missing-product, go-deeper, honesty-debt). De-dup, reconcile contradictions, and WRITE a single founder-readable doc to EXACTLY this path: ${DOC.critique}
Structure: (1) one-screen verdict, (2) LOST GOLD ranked table [item | what it was | NOT-FOUND evidence | why it died | revive cost | leverage], (3) MISSING (product gaps) ranked, (4) GO-DEEPER opportunities ranked, (5) HONESTY DEBT table [claim | reality | severity | cheapest fix], (6) the 5 highest-leverage moves across all four lenses.
Every row needs file:line / codegraph / packet / NOT-FOUND. No slop. After writing, RETURN a ≤300-word executive summary of the doc (this is all that propagates forward).

${join(critiqueLenses)}`,
  { label: 'write:critique', phase: 'Critique' })

// ---------------------------------------------------------------- PHASE 2: LICENSE
phase('License')
log('Phase 2/6 — License: how much more can we take from Mixxx if we flip Apache→GPL')

const licenseInputs = await parallel([
  () => agent(`${RULES}
ROLE = **MIXXX ARSENAL**. Kaan: "if we can snort even further from Mixxx we can go GPL too, who cares?" Inventory exactly what Mixxx (GPL-2.0+) contains that vibemix would kill for. Use WebSearch (ToolSearch "select:WebSearch") on the Mixxx source tree / docs.
★ LEAD WITH THE LIBRARY-FORMAT READERS — Kaan flagged THIS as the killer find ("Mixxx has Rekordbox readers, Serato readers, the insane things we found"). Mixxx's src/library/ ships battle-tested PARSERS for every major DJ ecosystem: **Serato** (crates + Database V2 + GEOB cue/beatgrid/color markers), **Rekordbox** (the .pdb binary DB + collection XML + ANLZ analysis files), **Traktor** (collection.nml), **iTunes/Apple Music** XML, **Engine DJ / Denon** (the SQLite m.db), **VirtualDJ**. THE GAP: vibemix today reads ONLY Rekordbox collection.xml (via pyrekordbox) and only WRITES Serato Markers2 — it CANNOT READ a Serato / Traktor / Engine / VirtualDJ library at all (src/vibemix/library/sources/ contains only rekordbox.py; no serato/traktor reader exists — NOT-FOUND). THE UNLOCK: "import your existing crates, cues, beatgrids, and play history from ANY DJ app" = universal ingest = the discovery/onboarding wedge (the user's whole library + taste lands in vibemix in one click). For EACH reader: Mixxx source path, the on-disk format, its license, and the honest build choice — keyless clean-room Python reimplement (formats are facts, reverse-engineered specs exist e.g. for Serato/pdb) vs straight GPL vendor — and the effort delta between them.
THEN the rest of the arsenal: beatgrid + BPM analyzer (engine/analyzer), key detection (libKeyFinder — find its OWN license, likely GPL/LGPL), the sync/phase engine, EQ + filter + isolator DSP (engine/filters, the biquad/RBJ implementations we are currently re-deriving clean-room), waveform/spectral analysis, AutoDJ + key-aware mixing, the controller-mapping JS engine.
For EACH item: module/path in Mixxx, its license, what vibemix gap it would fill (cross-ref GOLD-WIRING-MAP + FEATURE-STATE), and port difficulty if we were ALLOWED to vendor it. Be precise about which of OUR current "clean-room re-derive from spec" efforts (e.g. eq_move_model.py's RBJ coeffs) would become a straight copy if we went GPL. Rank the whole arsenal by (leverage / port-cost) — and state plainly whether the library-readers or the DSP is the bigger prize.`,
    { label: 'license:mixxx-arsenal', phase: 'License' }),

  () => agent(`${RULES}
ROLE = **APACHE COST / GPL UNLOCK**. Today the client is Apache-2.0 explicitly so "Bravoh internal reuse" is permitted (see CLAUDE.md + LICENSE + the SPDX header in __main__.py). Map precisely: (1) what Apache-2.0 currently FORBIDS (vendoring any GPL Mixxx source → we must clean-room everything, which is slow and lossy). (2) what flipping the CLIENT to GPL-3.0 (or GPL-2.0+) would UNLOCK — direct vendoring of Mixxx engine/analyzer/DSP, instant beatgrid+key+sync. (3) The exact mechanics: GPL is fine for a shipped desktop binary; the keyless proxy/server is SEPARATE (network use ≠ distribution unless AGPL). Quantify the unlock in dev-time saved and capability gained. Be a realist, not a hype-man.`,
    { label: 'license:cost-unlock', phase: 'License' }),

  () => agent(`${RULES}
ROLE = **THE ADVERSARY** — argue AGAINST flipping to GPL, hard, so Kaan sees the real cost before he says "fuck it". Surface what genuinely breaks: (1) Bravoh internal reuse — CLAUDE.md says Apache "permits Bravoh internal reuse"; if the client is GPL, can Bravoh (a commercial product) still link/reuse this code, or is it forced to keep an arm's-length runtime-import boundary or open its own surface? (2) the public product copy "Apache-licensed client" is a stated commitment — what's the cost of changing it / does it matter for a co-host whose value is the hosted brain? (3) any third-party Apache/MIT deps that DON'T compose with GPL distribution. (4) the "runtime-import-not-vendor is the line" rule from memory project_vibemix_gpl_runtime_dep_ok — does wholesale vendoring cross a line Kaan already drew? Steelman STAY-APACHE. Then concede honestly where the flip still wins.`,
    { label: 'license:adversary', phase: 'License' }),
])

const licenseSummary = await agent(`${RULES}
You are the LICENSE-STRATEGY SYNTHESIZER. Inputs: mixxx-arsenal, apache-cost/gpl-unlock, the adversary. WRITE a decision doc to EXACTLY: ${DOC.license}
Structure: (1) the question in one line, (2) MIXXX ARSENAL table [Mixxx module | license | vibemix gap it fills | port difficulty | leverage], (3) what Apache costs us + what GPL unlocks (quantified), (4) what genuinely BREAKS if we flip (the Bravoh-reuse cost especially — this is the crux), (5) a 3-option DECISION MATRIX: **STAY APACHE (clean-room only)** vs **DUAL-LICENSE / module-split** vs **FLIP CLIENT TO GPL**, each with what it unlocks, what it costs, and who it affects (client / Bravoh / proxy). (6) A clear recommendation WITH the honest tradeoff stated — this is a Kaan business decision, give him the sharpest version of it. RETURN a ≤300-word summary + the recommended option.

${join(licenseInputs)}`,
  { label: 'write:license', phase: 'License' })

// ---------------------------------------------------------------- PHASE 3: WIRING (codegraph/LSP)
phase('Wiring')
log('Phase 3/6 — Wiring: codegraph/LSP structural gap map')

const wiringInputs = await parallel([
  () => agent(`${RULES}
ROLE = **ORPHAN PAIRS**. Use codegraph (ToolSearch "codegraph") to find broken producer↔consumer pairs. (a) CONSUMERS WITHOUT PRODUCERS: e.g. BEATMATCH_GRADED is consumed by skill_recognizer.py but never emitted — find ALL such (event types in event_detector that have a handler but no emitter, intel claim types validated but never produced, evidence sources cited-for but never registered). (b) PRODUCERS WITHOUT CONSUMERS: engines that compute a result nothing live reads. For each pair: the two symbols, codegraph_callers/callees proof, and the one missing wire. This is the actionable wiring backlog.`,
    { label: 'wiring:orphan-pairs', phase: 'Wiring' }),

  () => agent(`${RULES}
ROLE = **DEAD / ORPHANED EXPORTS**. Use codegraph_callers across src/vibemix to find modules/functions that are importable and tested but have ZERO callers on the LIVE path (reached only by tests/demos/CLI). Cross-check the intel/ package (16 modules — which actually reach the coach loop?), the library scorers, learn/ engines. Distinguish "dead (delete)" from "orphaned-gold (wire it)". Give the codegraph evidence (caller count + who the callers are) for each. Flag anything that is pure dead weight bloating the bundle.`,
    { label: 'wiring:dead-exports', phase: 'Wiring' }),

  () => agent(`${RULES}
ROLE = **NOT-FOUND AUDIT**. Go through the packet pile (CODEX_READY-*, GOLD-WIRING-MAP, recovered/*) and the FEATURE-STATE PLANNED-ONLY/ABSENT rows. For every symbol/module/file a packet says "should exist" or "build this", verify with codegraph_search + ls/Grep whether it now EXISTS at HEAD ${HEAD} (Codex may have landed some). Produce a crisp ledger: [referenced symbol | packet that wants it | EXISTS? (file:line) or NOT-FOUND | if exists, is it WIRED?]. This tells us what Codex already closed vs what's still open — the truth behind the queue.`,
    { label: 'wiring:not-found-audit', phase: 'Wiring' }),
])

const wiringSummary = await agent(`${RULES}
You are the WIRING SYNTHESIZER. Inputs: orphan-pairs, dead-exports, not-found-audit. WRITE to EXACTLY: ${DOC.wiring}
Structure: (1) one-screen verdict on structural health, (2) ORPHAN PAIRS table [consumer | producer | which is missing | codegraph proof | the one wire], (3) DEAD vs ORPHANED-GOLD exports table [symbol | live callers | verdict delete/wire | evidence], (4) NOT-FOUND LEDGER [wanted symbol | packet | exists? | wired?], (5) the ranked wiring backlog (cheapest high-leverage wires first). Pure codegraph/LSP/grep evidence. RETURN a ≤300-word summary.

${join(wiringInputs)}`,
  { label: 'write:wiring', phase: 'Wiring' })

// ---------------------------------------------------------------- PHASE 4: FUTURE
phase('Future')
log('Phase 4/6 — Future: if Codex lands everything, what do we have + the new packet backlog')

const futureInputs = await parallel([
  () => agent(`${RULES}
ROLE = **POST-CODEX STATE**. Read CLAUDE_LAND_QUEUE.md + every CODEX_READY-*.md packet + the wiring not-found ledger. Project forward: IF Codex lands the entire current queue (all SAFE_NOW + the gated HOLDs that clear + the eq-move keystone), what product do we actually have? Walk it surface by surface (co-host / Viber / library / learn / cue / debrief). Then the sharp part: what is STILL missing AFTER the whole queue lands? Where does the queue stop short of "a real DJ friend that makes you better and that strangers pay for"? Be specific about the residual gap.`,
    { label: 'future:post-codex-state', phase: 'Future' }),

  () => agent(`${RULES}
ROLE = **NEW PACKET BACKLOG**. Kaan: "what do we want for Codex right now today based on what's already done? What new packets?" Using the critique + wiring findings (read ${DOC.critique} and ${DOC.wiring}), propose the NEW CODEX_READY packets Claude should write today — the ones not already in the queue. For each: a one-line spec, the exact gap it closes, the proof tier (SRC/PKG/LIVE), the gate (e.g. vibemix-grounding-review), rough effort, and a $-leverage score. Rank them. Separate "wire existing gold (cheap, big)" from "new build". This is the actionable shopping list for Codex.
EXPLICITLY weigh a **universal-library-ingest packet** (read Serato crates/markers + Traktor NML + Engine DJ SQLite, not just Rekordbox — see the license doc's Mixxx-arsenal) as a candidate; it may be the highest-onboarding-leverage new build. Also weigh wiring the orphaned readers/scorers from the wiring doc.`,
    { label: 'future:new-packets', phase: 'Future' }),
])

const futureSummary = await agent(`${RULES}
You are the FUTURE SYNTHESIZER. Inputs: post-codex-state, new-packet-backlog (+ read ${DOC.critique}, ${DOC.wiring}, ${DOC.license} summaries). WRITE to EXACTLY: ${DOC.future}
Structure: (1) POST-CODEX product walkthrough (what we'll have when the queue clears), (2) the RESIDUAL GAP (what's still missing after), (3) the NEW PACKET BACKLOG ranked table [packet name | gap closed | wire-or-build | proof tier | gate | effort | $-leverage], (4) the recommended TOP 5 packets to write today. RETURN a ≤300-word summary + the top-5 packet names.

${join(futureInputs)}`,
  { label: 'write:future', phase: 'Future' })

// ---------------------------------------------------------------- PHASE 5: MONEY
phase('Money')
log('Phase 5/6 — Money: 5 strategists + 3 judges → the play that wins real $')

const ANGLES = [
  { key: 'viral-wedge', brief: 'the consumer/viral wedge — the AI hypes your set and auto-clips the best moment to TikTok/IG/Reels; free→viral loop; how vibemix becomes a thing bedroom DJs share. Lowest CAC, biggest top-of-funnel. Also consider the ONBOARDING wedge: "one-click import your whole library + cues from Serato/Rekordbox/Traktor/Engine" (universal ingest) as the zero-friction hook that gets a DJ in.' },
  { key: 'pro-coach', brief: 'the pro tool — the grounded coach that genuinely makes you a better DJ (Learn/Earned as the paid product, the skill-tree → mastery). Willingness-to-pay test, €4.99/€9.99 tiers. The anti-slop coaching no competitor can fake.' },
  { key: 'creator-economy', brief: 'the streamer/creator co-host — Twitch/YouTube DJ streamers get a live AI co-host that reacts on-air; the audience-facing hype layer; sponsorship/affiliate; the co-host as content.' },
  { key: 'b2b-education', brief: 'B2B / education / events — sell to DJ schools, clubs, festivals, labels; the curriculum + debrief + grounded-feedback engine as a teaching product; per-seat or per-venue licensing.' },
  { key: 'moat-defensibility', brief: 'the MOAT play — what makes this uncopyable: the grounded-not-slop citation engine + Mixxx-deep musical intelligence (incl. universal library-format readers that ingest Serato/Traktor/Engine/Rekordbox, which pyrekordbox alone cannot) + on-device CLAP/MOSS (no per-use cloud cost). How to compound the data/taste flywheel — every imported library deepens the taste model — so a fast-follower can never catch up.' },
]

const strategies = await parallel(ANGLES.map((a) => () => agent(`${RULES}
You are a world-class product+GTM strategist. First READ ${DOC.future} and ${PK}/FEATURE-STATE-OF-THE-UNION.md so you pitch on the REAL product (what's built + what lands), NOT fantasy.
YOUR ANGLE: **${a.key}** — ${a.brief}
Deliver: (1) the play in 3 sentences, (2) who pays and why, (3) the revenue model + concrete path to first $1k → $100k → $1M (what each milestone requires), (4) the wedge feature that triggers adoption (must be groundable in what's built or cheaply wireable — name the file/engine), (5) **the honest kill-shot: why this might fail** + what would have to be true for it to work. Be specific to vibemix, not generic SaaS advice. Kaan wants the honest critic — do NOT oversell.`,
  { label: 'strat:' + a.key, phase: 'Money' })))

const judgeLenses = ['feasibility given what is actually built+landing', 'revenue ceiling / realistic $ size', 'defensibility / moat / why a fast-follower cant copy it']
const judgeVerdicts = await parallel(judgeLenses.map((lens, i) => () => agent(`${RULES}
You are JUDGE ${i + 1}, scoring 5 money strategies for vibemix on ONE lens: **${lens}**.
Read the 5 strategies below. Score each 1-10 on your lens with a one-line justification grounded in what's actually built (FEATURE-STATE). Then rank them 1-5 on your lens and name the single best + single weakest. Be a harsh, honest judge — penalize fantasy, reward what's executable on the real codebase. Do NOT be diplomatic.

${join(strategies)}`,
  { label: 'judge:' + (i + 1), phase: 'Money' })))

const moneySummary = await agent(`${RULES}
You are the MONEY SYNTHESIZER — the final call. You have 5 strategies and 3 judge panels (feasibility / revenue-ceiling / defensibility). WRITE the winning-move doc to EXACTLY: ${DOC.money}
Do this: (1) aggregate the judge scores into a ranked table, (2) pick THE winning play, (3) GRAFT the best ideas from the runner-ups into it (a sequenced strategy can use the viral wedge for top-funnel AND the pro-coach for revenue — show the combined motion), (4) give the concrete 90-day execution sequence grounded in what's built/landing (cite the engines + packets), (5) the realistic money model: path to first $1k, $100k, $1M with the assumptions each requires, (6) the single biggest risk + how to de-risk it cheaply. This is the doc that decides where the product goes to win. RETURN a ≤400-word executive summary naming the winning play + the first concrete move.

${join(strategies)}

## JUDGE PANELS
${join(judgeVerdicts)}`,
  { label: 'write:money', phase: 'Money' })

// ---------------------------------------------------------------- PHASE 6: SYNTHESIS
phase('Synthesis')
log('Phase 6/6 — Synthesis: one master plan tying critique → license → wiring → future → money')

const master = await agent(`${RULES}
You are the MASTER SYNTHESIZER. Read ALL five section docs you have summaries for: ${DOC.critique}, ${DOC.license}, ${DOC.wiring}, ${DOC.future}, ${DOC.money} (read the files from disk for full detail). WRITE the single master plan to EXACTLY: ${DOC.master}
This is the one doc Kaan reads to know "where we win and what to do Monday". Structure:
(1) THE THESIS in 3 sentences — is vibemix a rich product behind bad wiring, or a thin one? Verdict with evidence.
(2) WHAT WE LOST + the buried treasure worth reviving (top 5, from critique).
(3) THE LICENSE CALL — stay Apache / dual / flip GPL — with the one-line recommendation + the honest cost.
(4) THE WIRING TRUTH — what's orphaned-gold (wire it) vs dead (cut it), top moves.
(5) THE WINNING MOVE — the money play + the 90-day sequence, grounded.
(6) WHAT TO HAND CODEX TODAY — the ranked new-packet backlog (top 5) + which existing queue items matter most.
(7) THE ONE NEXT MOVE — if Kaan does exactly ONE thing after reading this, what is it and why.
Tie everything together; no contradictions between sections. Brutally honest, dense, every claim grounded.
RETURN a ≤600-word executive summary for Kaan (this is what I relay to him).`,
  { label: 'write:master', phase: 'Synthesis' })

return {
  master,
  critiqueSummary,
  licenseSummary,
  wiringSummary,
  futureSummary,
  moneySummary,
  docs: Object.values(DOC),
}
