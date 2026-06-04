export const meta = {
  name: 'opportunity-scan-1',
  description: 'Baseline opportunity-completeness scan of the repo: dark-gold, dead-wire, quick-wins, missed-integrations, adversarially filtered to ship-blocking-miss vs post-ship vs not-real',
  phases: [
    { title: 'Scan', detail: '4 parallel sweeps: dark-gold, dead-wire, quick-wins, missed-integrations' },
    { title: 'Filter', detail: 'adversarial: tag each ship-blocking-miss / post-ship / not-real, protect the ship' },
    { title: 'Synthesis', detail: 'land MISSED-OPPORTUNITIES-SCAN-1.md' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host, in the SHIP-FINISH endgame (two Codex sessions slicing the ship critical path; Claude scans for missed opportunities + does last checks). Quality bar: "real DJ friend, no AI slop"; grounding is law. Kaan wants to be SURE no opportunity was missed before shipping, WITHOUT scope-creep that delays the ship.
Read FIRST (build on, do not re-derive): .planning/packets/2026-06-04/STATE-OF-ALL-LANES-EOD.md, SHIP-READINESS-2026-06-04.md, NEXT-MOVES-VERIFIED.md, SHIP-FINISH-PLAN.md, PILL-FAFO-AND-LEVELUP.md, CUE-LAND-ENGINE.md. The known critical path is already captured there; your job is what those MISSED.
Already-known and OWNED (do NOT re-report as new): the 5 RED persona tests, auto_crate stop-reason gate, tsc gate, the stale DMG, the keystone capture, the in-GUI Gemini-key field, the cue-landing engine + Cue Tray, the pill streak rebind, the organism morph layer.
Read-only: code + git + codegraph + the packets. Do NOT launch the live sidecar. Be specific with file:line. The deliverable protects the ship: distinguish "we'd regret NOT shipping this" from "nice post-ship idea."`

phase('Scan')

const scans = await parallel([
  () => agent(
    `Hunt DARK GOLD: built-but-dark or 0-caller modules that hold real shippable value NOT already in the ship critical path. ${CTX}
Use codegraph (callers/0-caller functions) + grep across src/vibemix/** to find substantial modules/functions that are implemented + tested but have no live call site or no shipped surface, and that a user would actually benefit from at launch. Examples of the KIND (already known, find OTHERS): a scorer/engine computed but never surfaced, an export/format that exists but is unreachable, an intel primitive with no consumer. For each: what it is (file:line), what value it would add at ship, why it's dark, and the rough effort to light it.
Output "## Dark gold (built-but-unreached)": a list, each with file:line + value + why-dark + effort. Exclude the already-known/owned items listed in context. Do NOT edit any file.`,
    { label: 'scan:dark-gold', phase: 'Scan' }
  ),
  () => agent(
    `Hunt DEAD-WIRE: state/values that are COMPUTED from real data but never surfaced to the human (a cheap wire-win), beyond the already-known ones. ${CTX}
Look at what the engines compute and serialize vs what the frontend/voice actually consume: ws-bus fields emitted but never read, evidence atoms built but never shown, music_state/decision fields computed but dark. (The pill grade_progress + organism morph are already known — find OTHERS.) For each: the computed source (file:line), where it dies, and the cheap wire that would surface it at ship.
Output "## Dead-wire (computed but unsurfaced)": a list with computed-source file:line + death point + cheap-wire effort. Exclude already-known items. Do NOT edit any file.`,
    { label: 'scan:dead-wire', phase: 'Scan' }
  ),
  () => agent(
    `Hunt QUICK-WINS: small, high-leverage flips that materially improve the ship for little effort. ${CTX}
Cross-ref NEXT-MOVES-VERIFIED.md leftovers + scan for: honest-null gaps, missing one-line guards, copy that still overstates, a config default that should flip for ship, a feature gated OFF that should be ON for launch, a small UX honesty fix. Each must be <~0.5d and ship-relevant.
Output "## Quick-wins (<0.5d, ship-relevant)": a list, each with the change + file:line + why it matters at ship. Exclude already-known items. Do NOT edit any file.`,
    { label: 'scan:quick-wins', phase: 'Scan' }
  ),
  () => agent(
    `Hunt MISSED-INTEGRATIONS: cross-engine reuse or connections not yet exploited that would make the shipped product noticeably more coherent. ${CTX}
The cue->Viber integration is already designed (CUE-LAND-ENGINE). Find OTHER connections: an engine output that another engine could consume but doesn't (taste<->suggestion, library<->learn, debrief<->profile, intel scorer<->pill, key/camelot<->next-suggestion), or a capability that exists on one surface and should appear on another. For each: the two sides (file:line), what the connection buys at ship, wire-vs-build, effort.
Output "## Missed integrations": a list, each with both endpoints file:line + value + wire/build + effort. Exclude already-known items. Do NOT edit any file.`,
    { label: 'scan:missed-integrations', phase: 'Scan' }
  ),
])

const sDark = scans[0] || '(dark-gold scan failed)'
const sWire = scans[1] || '(dead-wire scan failed)'
const sQuick = scans[2] || '(quick-wins scan failed)'
const sIntegr = scans[3] || '(missed-integrations scan failed)'

phase('Filter')

const filtered = await agent(
  `You are the adversarial SHIP-PROTECTION filter. Default to "post-ship" unless an item clearly belongs in v1. Review every candidate from the four scans below and tag EACH one:
- SHIP-BLOCKING-MISS: we would genuinely regret shipping v1 WITHOUT this (real user-facing value or honesty/grounding risk), AND it is feasible inside the ship window. Be stingy — these feed the two Codex lanes and compete with the ship.
- POST-SHIP-BACKLOG: real and worth doing, but after v1. Most items land here.
- NOT-REAL: speculative, ungrounded, duplicate of an already-owned item, or scope-creep dressed as opportunity. Kill it.
Verify feasibility/value claims against the real repo where you doubt them (read the cited file:line). Kill duplicates of the already-owned ship items. Protect the ship: a long SHIP-BLOCKING list is a failure of this filter. ${CTX}

--- DARK GOLD ---
${sDark}
--- DEAD-WIRE ---
${sWire}
--- QUICK-WINS ---
${sQuick}
--- MISSED INTEGRATIONS ---
${sIntegr}
---
Output "## Filtered verdicts": per candidate, the tag + a one-line reason + (for SHIP-BLOCKING) which Codex lane (A frontend / B backend) it belongs to. Lead with the SHIP-BLOCKING-MISS items (should be few). Do NOT edit any file.`,
  { label: 'filter', phase: 'Filter' }
)

phase('Synthesis')

const report = await agent(
  `Write the file .planning/packets/2026-06-04/MISSED-OPPORTUNITIES-SCAN-1.md for the vibemix founder. Synthesize the filtered verdicts below into a tight, ship-protecting scan report.

Sections:
1. "## Did we miss anything ship-blocking?" - the blunt answer (likely "a few / none"), then the SHIP-BLOCKING-MISS list ONLY: each with what it is, file:line, value, the Codex lane (A/B) to route it to, and effort. If none, say so plainly.
2. "## Post-ship backlog" - the POST-SHIP items, one line each (so they are remembered, not lost, and not built now).
3. "## Killed (not real / duplicate)" - one line each, so they are not re-proposed next scan.
4. "## Scan coverage" - one line on what this scan swept (dark-gold, dead-wire, quick-wins, integrations) so the next scan can go deeper elsewhere.

Use only evidence from the inputs; no invented numbers. Anti-slop: no em-dashes, active voice, specific. Do NOT commit the file (the organizer commits after). After writing, return a tight chat-ready summary (~10 lines): the blunt did-we-miss-anything answer, the SHIP-BLOCKING items (with lane), and the count of post-ship vs killed. Markdown.

--- FILTERED VERDICTS ---
${filtered}
---`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return report
