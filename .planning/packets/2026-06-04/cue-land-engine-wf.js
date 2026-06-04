export const meta = {
  name: 'cue-land-engine',
  description: 'Observe the auto-cue to Rekordbox landing workflow, design the sexy permissioned UX, and generalize it into ONE reusable cue-landing engine other engines (Viber, semantic, learn, debrief) can call. No prelisten.',
  phases: [
    { title: 'Observe', detail: 'map the cue detect+export stack, the cross-engine consumers, the permissioned-landing UX' },
    { title: 'Design', detail: 'one reusable cue-landing engine + sexy preview->permission->land flow + call sites' },
    { title: 'Verify', detail: '3 adversarial lenses: provenance/safety, wire-not-build, cross-engine fit' },
    { title: 'Synthesis', detail: 'land CUE-LAND-ENGINE.md + a /goal' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host. THE MOAT (memory project_auto_cue_engine) = the auto-cue engine: offline audio -> CueAnchor (intro/build/breakdown/drop/outro) via CUE-DETR ONNX (MIT, torch-free) + smart_cues. The value Kaan just locked: **auto-detected cues land in the DJ's own software (Rekordbox first, then Serato/Mixxx) automatically, WITH the user's permission, non-destructively.** That is "IT". (A one-off prelisten-clip export was built this session only so Kaan could ear-check the cues; PRELISTEN IS NOT A PRODUCT FEATURE and is out of scope here.)
What exists already (read, do not edit): src/vibemix/library/smart_cues.py (SmartCue), cue_detr (CUE-DETR ONNX producer), src/vibemix/library/anlz_ingest.py (Rekordbox ANLZ real cues/PSSI phrase), src/vibemix/library/export_rekordbox.py (non-destructive Rekordbox XML, POSITION_MARK hot cues), src/vibemix/library/cue_export.py, src/vibemix/library/cue_folder.py (cue->Rekordbox/M3U8/Serato), src/vibemix/library/export_serato.py (Serato Markers2 UNIVERSAL carrier -> Mixxx+Serato+Rekordbox), src/vibemix/library/rekordbox.py, the CLI vibemix library export-set ... --allow-unvalidated (commit 2341da8b, exports brand-new local files), toolset.py cue tools, the doctor pyrekordbox check.
HARD RULES (memory + this session):
- NON-DESTRUCTIVE ONLY. Never write Rekordbox's private DB. The supported path is an importable XML (Rekordbox File > Preferences > Bridge > Imported Library), and the export_serato universal carrier for Serato/Mixxx. Direct-DB write is a scary "advanced" thing we do NOT default to.
- PROVENANCE: auto-detected cues must NEVER masquerade as DJ-authored. Preserve A-H slot semantics + a provenance tag (auto vs DJ). Do not overwrite a DJ's own saved cues.
- Grounded + honest confidence. CUE-DETR is validated on real techno/psy/house; honest-null where it is not confident.
The ask: SEE+OBSERVE the current cue-landing workflow, MAKE IT SEXY (the auto-cue -> preview -> one-click permissioned land UX), and MAKE IT REUSABLE for other engines (Viber set-prep, semantic/next-suggestion, learn, debrief).`

phase('Observe')

const observe = await parallel([
  () => agent(
    `Map the FULL current cue detect + export stack in vibemix code (read-only). ${CTX}

Trace, with file:line, the path from "audio/track" to "cues landed in the DJ's software":
- Cue PRODUCTION: CUE-DETR ONNX producer, smart_cues.py SmartCue, anlz_ingest.py (reading the DJ's existing real cues). What each emits, in what shape (CueAnchor / SmartCue / slots).
- Cue EXPORT/LANDING: export_rekordbox.py, cue_export.py, cue_folder.py, export_serato.py (universal carrier), rekordbox.py, the export-set CLI + the new --allow-unvalidated (2341da8b). What format each writes, destructive vs non-destructive, provenance handling.
- Use codegraph for callers/callees of the export functions and SmartCue.

Determine: is there ONE reusable "land cues into ecosystem" engine, or is it scattered across these modules with overlapping/duplicated logic? Name the seams. Identify exactly what a single reusable core would need to unify (a CueSet abstraction + a permissioned ExportTarget for rekordbox/serato/mixxx). Flag any provenance gap (where auto cues could be confused with DJ cues).

Output prose "## Current cue stack (code-grounded)": the production->landing trace with file:line, the scattered-vs-unified verdict, and the seams a reusable engine would unify. Do NOT edit any file.`,
    { label: 'observe:stack', phase: 'Observe' }
  ),
  () => agent(
    `Map the CROSS-ENGINE consumers of an auto-cue-landing capability in vibemix (read-only). ${CTX}

For each engine, determine concretely how "auto-detect cues -> land them in the DJ's software (permissioned, non-destructive)" would help, and WHERE it would be called (file:line of the natural call site):
- VIBER set-prep (src/vibemix/library/toolset.py, codex_curate.py, the build-set / curate / export-set path): would a DJ want Viber to auto-cue every track in a freshly built/curated set before exporting it to Rekordbox? That turns "here's a set" into "here's a set, beat-gridded and cued, ready to play." This is likely the #1 win.
- SEMANTIC / next-suggestion (next_suggestion.py, clap_engine.py): do cues feed better transition/cue-slot suggestions? Does landing cues improve the "cue A @ 1:23" the pill already shows?
- LEARN (cue_placement_judge.py): relationship between auto-cues and teaching cue placement.
- DEBRIEF: post-session, offer to land the cues from tracks played.
Cite the real modules. Rank the consumers by leverage (which gives the most value for least new wiring).

Output prose "## Cross-engine consumers (ranked)": per engine, the value + the call site + wire-vs-build. Name the single highest-leverage first integration. Do NOT edit any file.`,
    { label: 'observe:consumers', phase: 'Observe' }
  ),
  () => agent(
    `Design the SEXY, permissioned auto-cue -> Rekordbox/ecosystem landing UX for vibemix (read-only research + product design). ${CTX}

The flow Kaan wants: vibemix auto-detects cues -> the user sees a tight preview -> one click -> the cues land in their software, non-destructively, with their permission. NO prelisten clips.
Design it concretely:
- The PREVIEW surface: per track, the A-H cue slots with name + timecode + confidence + a clear AUTO badge (provenance, never masquerading as DJ-authored). What's the minimal, glanceable, on-brand (impeccable, no slop) preview? Selectable cues (accept/reject per slot)?
- The PERMISSION model: a single explicit consent ("Land these cues to Rekordbox") -> writes the importable XML -> opens/reveals it + the one-line "set it as Bridge Imported Library, import the playlist" instruction. Confirm the non-destructive route (Rekordbox Bridge Imported Library XML; Serato/Mixxx via the universal Markers2 carrier). Use WebSearch to confirm the current Rekordbox import-XML UX if useful.
- Multi-ecosystem: same consent, target picker (Rekordbox / Serato / Mixxx) off the existing export_serato universal carrier.
- The "automatic with permission" line: what is auto (detection, XML generation, reveal) vs what stays the user's hand (the final import click in their app). Be explicit that silent DB write is NOT the default.

Output prose "## Sexy permissioned landing UX": the preview, the consent flow, the multi-ecosystem target, and the auto-vs-user boundary. On-brand, specific, no slop, no prelisten. Do NOT edit any file.`,
    { label: 'observe:ux', phase: 'Observe' }
  ),
])

const oStack = observe[0] || '(stack map failed)'
const oConsumers = observe[1] || '(consumers map failed)'
const oUx = observe[2] || '(ux design failed)'

phase('Design')

const design = await agent(
  `Design ONE reusable cue-landing engine for vibemix, synthesizing the three observations below. ${CTX}

Commit to a concrete design:
- The unifying core: name the module + the abstraction (e.g. a CueSet {track, anchors[], provenance} + a permissioned land(target) over rekordbox/serato/mixxx) that unifies the scattered export modules WITHOUT rewriting what works. Reuse export_rekordbox / export_serato / cue_folder / the --allow-unvalidated path as the carriers; the engine is the seam above them.
- How the MOAT producers (CUE-DETR, smart_cues, anlz) feed the CueSet, provenance-tagged (auto vs DJ).
- The cross-engine call sites: how Viber set-prep, semantic, learn, debrief each call the SAME engine (the #1 first integration named explicitly, with its call site).
- The sexy permissioned UX bound to it (from the UX observation).
- For each piece: WIRE (exists, connect) vs BUILD (new), rough effort, and how to prove it (a bench / by-eye export that pyrekordbox re-parses, never DB mutation).

--- CURRENT STACK ---
${oStack}
--- CROSS-ENGINE CONSUMERS ---
${oConsumers}
--- SEXY UX ---
${oUx}
---

Output prose "## Reusable cue-landing engine (design)": the core abstraction, the producers, the cross-engine call sites, the UX binding, and the WIRE/BUILD/effort/proof per piece. Favor WIRE; protect provenance + non-destructive. Do NOT edit any file.`,
  { label: 'design', phase: 'Design' }
)

phase('Verify')

const verdicts = await parallel([
  () => agent(
    `Adversarial PROVENANCE + SAFETY judge. Default to skepticism. Review the cue-landing engine design below. Rule KEEP / KILL / REFRAME on: (1) does any part risk auto-cues masquerading as DJ-authored, or overwriting a DJ's own saved cues? (2) is every landing path NON-DESTRUCTIVE (importable XML / universal carrier), with zero default Rekordbox private-DB writes? (3) is confidence honest (honest-null where CUE-DETR is unsure)? Kill anything that mutates a DJ's library silently or blurs auto-vs-DJ provenance. ${CTX}

--- DESIGN ---
${design}
---
Output prose "## Verify - provenance/safety": per design element, verdict + one-line reason, and the exact provenance/non-destructive guard it must carry. Do NOT edit any file.`,
    { label: 'verify:provenance', phase: 'Verify' }
  ),
  () => agent(
    `Adversarial WIRE-NOT-BUILD / feasibility judge. Default to skepticism. For the design below, verify against the real code (read export_rekordbox.py, cue_export.py, cue_folder.py, export_serato.py, smart_cues.py, toolset.py, the export-set CLI; use codegraph) whether each "WIRE" claim is true or is secretly a BUILD. The carriers (Rekordbox XML, Serato Markers2 universal, --allow-unvalidated) already exist, so the reusable engine should be mostly a thin unifying seam + call sites. Rule KEEP / KILL / REFRAME per element, correct the effort, and name the smallest real first step. ${CTX}

--- DESIGN ---
${design}
---
Output prose "## Verify - wire-not-build": per element, verdict + the file:line evidence for whether the carrier exists + corrected effort + the smallest real first step. Do NOT edit any file.`,
    { label: 'verify:feasibility', phase: 'Verify' }
  ),
  () => agent(
    `Adversarial CROSS-ENGINE FIT judge. Default to skepticism. The ask is "make it useful for other engines (Viber, semantic, etc.)." For the design below, rule KEEP / KILL / REFRAME on whether each cross-engine integration is a REAL win a DJ wants, or a forced "reuse for reuse's sake." Be specific: would a DJ actually want Viber to auto-cue a built set before export (probably yes), or is wiring it into semantic/learn just architecture astronautics? Name the ONE first integration that is undeniably worth it and which proposed ones to defer. ${CTX}

--- DESIGN ---
${design}
---
Output prose "## Verify - cross-engine fit": per integration, verdict + one-line reason + the single first integration to ship. Do NOT edit any file.`,
    { label: 'verify:fit', phase: 'Verify' }
  ),
])

const vProv = verdicts[0] || '(provenance verify failed)'
const vFeas = verdicts[1] || '(feasibility verify failed)'
const vFit = verdicts[2] || '(fit verify failed)'

phase('Synthesis')

const report = await agent(
  `Write the file .planning/packets/2026-06-04/CUE-LAND-ENGINE.md for the vibemix founder, synthesizing the observations, the design, and the three adversarial verdicts below. Keep only what survives provenance/safety + feasibility, and lead with the single highest-leverage first integration that fit-judge endorsed. No prelisten anywhere.

Sections:
1. "## What this is" - one paragraph: auto-cues land in the DJ's software (Rekordbox first, Serato/Mixxx next), permissioned + non-destructive, generalized so every engine uses one core. State the provenance + non-destructive guarantee up front.
2. "## Current stack (what exists)" - the code-grounded map: producers (CUE-DETR/smart_cues/anlz) + carriers (export_rekordbox/export_serato/cue_folder/--allow-unvalidated) with file:line, and the scattered-vs-unified verdict.
3. "## The reusable cue-landing engine" - the unifying core (module + CueSet/land abstraction) that survived verification, WIRE vs BUILD per piece, effort, proof (pyrekordbox re-parse, never DB write).
4. "## Sexy permissioned UX" - the preview -> consent -> land flow, multi-ecosystem target, auto-vs-user boundary. On-brand, no slop.
5. "## Cross-engine: ship order" - the ONE first integration (Viber auto-cue-a-built-set is the likely winner) with its call site, then the deferred ones with why.
6. "## Owner-gates" - Kaan's calls (default target ecosystem, any direct-DB-write appetite = recommend NO, tier).
7. "## Next /goal - Cue-landing engine" - a tight copy-paste /goal naming the island (mostly src/vibemix/library/** + toolset.py for the Viber call site = Library/Engine lane; any UI preview is the Frontend lane + IPC schema Frontend-owned), proof = pyrekordbox re-parse + by-eye import, and embed this law verbatim at the end:
SHARED LAW - one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, Kaan Ozkan <rahipdotaci@gmail.com>.

--- CURRENT STACK ---
${oStack}
--- CROSS-ENGINE CONSUMERS ---
${oConsumers}
--- SEXY UX ---
${oUx}
--- DESIGN ---
${design}
--- VERIFY: PROVENANCE ---
${vProv}
--- VERIFY: FEASIBILITY ---
${vFeas}
--- VERIFY: FIT ---
${vFit}
---

Use only evidence from the inputs; no invented numbers. Anti-slop: no em-dashes, active voice, specific, commit to a position. Do NOT commit the file (the organizer commits after). After writing, return a tight chat-ready summary (~12 lines): what the engine is, the one first integration to ship, the sexy-UX one-liner, and the non-destructive/provenance guarantee. Markdown.`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return report
