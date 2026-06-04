export const meta = {
  name: 'pill-fafo-levelup',
  description: 'FAFO the pill: trace whether the streak feature is actually live, census every pill capability, then craft + adversarially verify grounded level-up moves and land a packet',
  phases: [
    { title: 'Reality', detail: 'streak end-to-end trace + capability census + grounding/product-fit lens' },
    { title: 'Craft', detail: 'level-up opportunities grounded in what is actually wired' },
    { title: 'Verify', detail: '3 adversarial lenses: grounding/anti-slop, fit-vs-purge, wire-not-build' },
    { title: 'Synthesis', detail: 'write PILL-FAFO-AND-LEVELUP.md + streak verdict + pill /goal' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host. The PILL is the small live UI element that shows "what mixes next" (next-track suggestion with reasons[] + cue-confidence) and hover-reveals detail. Quality bar: "real DJ friend in your ear, no AI slop" — grounding is the law: nothing un-caused reaches the human (Invariant: every reaction/recommendation ties to a real detected event or computed-from-real-state value; no hallucinated picks, no fake counters).
KEY CONTEXT for this probe:
- Today (commit 826fddc9) a purge removed ~4254 lines from the pill and "9 gamification mock-transfer wires." The EOD audit (.planning/packets/2026-06-04/STATE-OF-ALL-LANES-EOD.md) flagged that src/pill/move-grade-vocabulary.ts ("SEXY"/"overdrive"/grade verbs) still ships but is reachable ONLY via a DEV-gated demo path (pill/index.ts:494/547) — shipped users never see it.
- So gamification (streaks, grade verbs, combos) appears to have been MOCK-wired (demo/dev data, not real session data) and largely stripped. Kaan has NEVER seen a streak fire live and is asking: is it even live?
- The pill code lives under tauri/ui/src/pill/. The "what's next" engine is src/vibemix/runtime/suggestion.py (SuggestionService) + src/vibemix/library/next_suggestion.py. Camelot/harmonic = src/vibemix/state/harmonics.py. Cue confidence + reasons come from the engine.
- Read-only probe: code-trace + git history + grep/codegraph ONLY. Do NOT launch the live sidecar (127.0.0.1:8765 is one-socket and other agents run in parallel). If a live by-bus probe is needed, RECOMMEND it as a next move; do not run it here.`

phase('Reality')

const reality = await parallel([
  () => agent(
    `You are tracing ONE question to the ground for the vibemix founder: IS THE PILL "STREAK" FEATURE ACTUALLY LIVE, and has a streak ever fired on REAL session data (not a dev/demo mock)? ${CTX}

Do the forensics. Working dir = repo root.
- grep/codegraph the WHOLE repo (Python + tauri/ui/src TS) for: "streak", "Streak", "combo", "consecutive", "count_up", any counter/tally that increments on events. Find every definition and every reference.
- For each streak-like mechanism, trace END TO END: where is the value computed/incremented? what increments it (a real detected event, or hardcoded/demo/random/mock data)? does it persist across the session? does it cross the IPC bus to the pill frontend? does any SHIPPED (non-DEV-gated) frontend path render it? Name exact files:lines.
- Use git to find when streak code was added and what commit 826fddc9 (and any sibling purge commits today) removed. Was the streak ever wired to real events, or was it always a mock/demo transfer? git log -S"streak" --oneline and git show the relevant commits.
- Distinguish clearly: LIVE (fires on real events, shipped path) vs DARK (built, wired to real events, but never reaches the human) vs MOCK-ONLY (only ever driven by demo/dev/random data) vs PURGED (removed today).

Output a tight prose verdict section "## Streak — does it live?" with: the one-line verdict (LIVE / DARK / MOCK-ONLY / PURGED, pick one), the exact end-to-end trace with file:line evidence, what 826fddc9 did to it, and the honest answer to "why has Kaan never seen one." Be specific and evidence-backed; if you cannot find a streak mechanism at all, say so plainly with the grep evidence. Do NOT edit any file. Do NOT launch the sidecar.`,
    { label: 'reality:streak-trace', phase: 'Reality' }
  ),
  () => agent(
    `You are taking a complete census of the vibemix PILL's capabilities and their REAL wired state. ${CTX}

Read tauri/ui/src/pill/** (index.ts and siblings), src/vibemix/runtime/suggestion.py (SuggestionService), src/vibemix/library/next_suggestion.py, src/vibemix/state/harmonics.py. Use codegraph for callers/callees.
For EACH distinct pill capability you find (e.g. next-track suggestion, reasons[]/why-this-pick receipts, cue-confidence display, harmonic/Camelot match, hover-reveal/Dynamic-Island morph, any grade-vocabulary, any gamification remnant), determine its real state:
- LIVE: computed from real detected state + rendered on the shipped path. Cite the event/state source and the render site (file:line).
- DARK: computed but never reaches the human, OR rendered but never receives real data.
- MOCK/DEV: only driven by demo/dev-gated/placeholder data.
- DEAD: defined, zero callers.
Be precise about what feeds each one (which ws-bus message / which engine field) and whether the data is real or placeholder.

Output a prose census "## Pill capability census" as a clear list, each item: name, state (LIVE/DARK/MOCK/DEAD), data source, render site, one-line note. End with a 2-line "what the shipped pill actually shows a user today" summary. Do NOT edit any file. Do NOT launch the sidecar.`,
    { label: 'reality:capability-census', phase: 'Reality' }
  ),
  () => agent(
    `You are the grounding + product-fit lens for the vibemix PILL. ${CTX}

The tension to resolve: today's purge (826fddc9) stripped gamification mock-wires as "slop/dev chrome," yet Kaan is excited about reviving the streak idea. The product bar is "real DJ friend, no AI slop" and the grounding law (nothing un-caused reaches the human). Read the EOD audit's Frontend+Organism section and the pill notes; consider the project's anti-slop stance.

Reason through (read-only): which kinds of pill behavior are GROUNDED-and-good (tied to real detected events, earn their place, feel like a real DJ friend noticing something true) versus GAMIFICATION-SLOP (counters/streaks/grade-verbs that reward usage rather than reflect real musical events — the kind a voice-assistant-doing-music-commentary would show)? Specifically: can a "streak" ever be grounded and on-brand, and if so what would it have to COUNT to be real (e.g. consecutive harmonically-correct transitions detected live, clean beatmatched mixes graded by the real judge) versus fake (sessions opened, time spent, arbitrary points)? Where is the line for THIS product?

Output a prose section "## Grounding & product-fit lens" with: the grounded-vs-slop line for the pill, a direct verdict on whether streaks belong in this product at all and under what grounding condition they could, and 2-3 principles any new pill capability must satisfy to be on-brand. Specific, opinionated, anti-slop. Do NOT edit any file.`,
    { label: 'reality:grounding-fit', phase: 'Reality' }
  ),
])

const streakTrace = reality[0] || '(streak trace failed)'
const census = reality[1] || '(census failed)'
const groundingFit = reality[2] || '(grounding-fit failed)'

phase('Craft')

const craft = await agent(
  `You are crafting level-up opportunities for the vibemix PILL, grounded in the reality probe below. ${CTX}

Given (1) the streak verdict, (2) the capability census, and (3) the grounding/product-fit line, craft 6-10 concrete opportunities to make the pill smarter and more alive WITHOUT becoming slop. Cover both: (a) what to DO about the streak idea specifically (resurrect-but-ground it / replace it with a grounded equivalent / kill it for good — take a clear position consistent with the grounding lens), and (b) net-new pill exploration capabilities that fit "real DJ friend" (e.g. richer grounded "why this pick" receipts, harmonic-path foresight, live confidence the user can trust, hover-reveal depth, surfacing a genuinely-detected musical moment).

For EACH opportunity give: a short title, what it buys the user, whether it is WIRE (engine/data already exists, just connect/render) or BUILD (genuinely new), rough effort, the grounding source it ties to (which real event/field), and HOW TO PROVE it (by-bus / by-eye on the real rig, never green tests alone). Flag any that need an owner decision.

--- STREAK VERDICT ---
${streakTrace}
--- CAPABILITY CENSUS ---
${census}
--- GROUNDING & PRODUCT-FIT LENS ---
${groundingFit}
---

Output prose "## Crafted pill level-up opportunities" — a numbered list, each with the fields above. Be specific and feasible; favor WIRE over BUILD; no gamification slop unless you can ground it. Do NOT edit any file.`,
  { label: 'craft', phase: 'Craft' }
)

phase('Verify')

const verdicts = await parallel([
  () => agent(
    `You are an adversarial GROUNDING / ANTI-SLOP reviewer. Default to disbelief. Review every crafted pill opportunity below and rule each KEEP / KILL / REFRAME purely on grounding: does it tie to a REAL detected event or computed-from-real-state value, or is it a fabricated counter / un-caused animation / generic-AI-assistant flourish? Kill anything that would put an un-grounded number or claim in front of the user. For REFRAME, say exactly what grounding source it must bind to. ${CTX}

--- CRAFTED OPPORTUNITIES ---
${craft}
---
Output prose "## Verify — grounding/anti-slop": per opportunity, the verdict + one-line reason. Be ruthless; a plausible-but-ungrounded idea must die. Do NOT edit any file.`,
    { label: 'verify:grounding', phase: 'Verify' }
  ),
  () => agent(
    `You are an adversarial PRODUCT-FIT reviewer with one specific job: catch contradictions with the direction the product just took. TODAY the team purged gamification mock-wires from the pill (826fddc9) as slop/dev-chrome. Review every crafted opportunity below and rule KEEP / KILL / REFRAME on whether it fits "real DJ friend, no AI slop" and does NOT quietly re-introduce the gamification the team just removed. A "streak" or grade-verb revival must clear a high bar: it is only KEEP if it counts something a real DJ would actually care about and that is detected live. Flag anything that reads like a usage-reward, a points system, or voice-assistant-doing-music-commentary. ${CTX}

--- CRAFTED OPPORTUNITIES ---
${craft}
---
Output prose "## Verify — product-fit vs the gamification purge": per opportunity, verdict + one-line reason, and an explicit note on any opportunity that risks undoing today's purge. Do NOT edit any file.`,
    { label: 'verify:product-fit', phase: 'Verify' }
  ),
  () => agent(
    `You are an adversarial FEASIBILITY / WIRE-NOT-BUILD reviewer. For every crafted pill opportunity below, verify against the real codebase whether the claimed data/engine actually exists (read tauri/ui/src/pill/**, src/vibemix/runtime/suggestion.py, src/vibemix/library/next_suggestion.py, src/vibemix/state/harmonics.py; use codegraph). Rule KEEP / KILL / REFRAME on feasibility: is the "WIRE" claim true (the field/event already exists) or is it secretly a BUILD? Kill or downgrade anything that claims a source that does not exist. Correct the effort estimate where wrong. Prefer the smallest real change that ships. ${CTX}

--- CRAFTED OPPORTUNITIES ---
${craft}
---
Output prose "## Verify — feasibility/wire-not-build": per opportunity, verdict + the real file:line evidence for whether its data source exists + corrected effort. Do NOT edit any file.`,
    { label: 'verify:feasibility', phase: 'Verify' }
  ),
])

const vGround = verdicts[0] || '(grounding verify failed)'
const vFit = verdicts[1] || '(product-fit verify failed)'
const vFeas = verdicts[2] || '(feasibility verify failed)'

phase('Synthesis')

const report = await agent(
  `Write the file .planning/packets/2026-06-04/PILL-FAFO-AND-LEVELUP.md for the vibemix founder, synthesizing the pill reality probe, the crafted opportunities, and the three adversarial verdicts below. An opportunity only survives if it is not KILLed by the grounding or product-fit lens and its data source is real per feasibility. State corrected efforts and required grounding bindings inline.

Sections:
1. "## Streak verdict — is it live?" — lead with the blunt one-line answer to Kaan's question (is the streak live / has he ever been able to see one / why not), then the end-to-end evidence in 4-6 lines.
2. "## Pill capability census" — a compact table or tight list: capability | state (LIVE/DARK/MOCK/DEAD) | data source | what the user actually sees today.
3. "## Surviving level-up moves (ranked)" — only opportunities that survived all three verifiers. Each: title, WIRE/BUILD, effort, grounding source, how-to-prove (by-bus/by-eye). Rank by leverage. Note any that were REFRAMEd and how.
4. "## Killed / parked" — opportunities the verifiers killed, with the one-line reason (so they are not re-proposed).
5. "## Streak — the on-brand decision" — the grounded position: kill it, or resurrect it bound to a real detected thing (say exactly what it must count), as an owner-gate for Kaan.
6. "## Next /goal — Pill" — a tight copy-paste /goal block for the pill work, naming the file-island (pill capabilities span tauri/ui/src/pill/** which is the FRONTEND lane, plus any engine field in runtime/suggestion.py + library/next_suggestion.py which is the LIBRARY/Engine lane — state which surviving move belongs to which lane and that the IPC schema is Frontend-owned), proof = by-bus/by-eye, and embed this law verbatim at the end:
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, Kaan Özkan <rahipdotaci@gmail.com>.

--- STREAK TRACE ---
${streakTrace}
--- CAPABILITY CENSUS ---
${census}
--- GROUNDING & PRODUCT-FIT LENS ---
${groundingFit}
--- CRAFTED OPPORTUNITIES ---
${craft}
--- VERIFY: GROUNDING ---
${vGround}
--- VERIFY: PRODUCT-FIT ---
${vFit}
--- VERIFY: FEASIBILITY ---
${vFeas}
---

Anti-slop: no em-dashes, active voice, specific, no invented numbers (use only evidence from the inputs). Do NOT commit (the organizer commits after). After writing the file, return a tight chat-ready summary (~12 lines) leading with the blunt STREAK verdict, then the top 3 surviving level-up moves and the streak on-brand decision. Markdown.`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return report
