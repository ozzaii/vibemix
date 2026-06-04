export const meta = {
  name: 'ship-readiness',
  description: 'Honest ship-readiness audit across all parallel sessions: is everything integrated on HEAD, can a stranger actually run+hear it, what is left, polish the democratization + the shortest path to see the latest+greatest now',
  phases: [
    { title: 'Assess', detail: '5 dimensions: integration/HEAD, build+packaging, live keystone, democratization, see-it-now' },
    { title: 'Verify', detail: 'adversarial: kill optimistic "ready", enforce proof tiers SRC!=PKG!=LIVE' },
    { title: 'Synthesis', detail: 'land SHIP-READINESS + critical path + DO-THIS-to-see-it-now' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host (local macOS/Windows app: listens to master audio, watches DJ-software screen, MIDI, talks back; library/Viber set-prep; learn teaching; pill next-suggestion). Quality bar: "real DJ friend, no AI slop"; grounding is law. It has been in build a LONG time; Kaan wants it SHIPPED (no rushing, but for real), and is worried that many parallel Claude+Codex sessions ran on ONE shared tree (ux-redesign-impeccable) so work may be fragmented, uncommitted, or dark.
Read .planning/packets/2026-06-04/STATE-OF-ALL-LANES-EOD.md (today's verified all-lanes audit) and NEXT-MOVES-VERIFIED.md FIRST and build on them - do NOT re-census features. Focus on SHIP.
THREE PROOF TIERS (do not conflate): SRC (green tests) != PKG (it's in the shipped bundle/DMG) != LIVE (a real user runs it and it works by-ear/by-eye). "test-passing-but-dark = 0."
Known ship facts to VERIFY against current source/artifacts (do not trust, check):
- A signed+notarized DMG existed (dist/vibemix-0.0.1.dmg); the DMG is rebuilt SEPARATELY from the sidecar binary, so a sidecar fix does NOT refresh the DMG (the "165-commit-stale DMG" trap). Today release gates were added (MOSS bundle present, learn wavs bundled, signing, updater manifest, source-freshness manifest).
- Speech: local MOSS TTS = never-mute product voice (bundled). A new Chatterbox-Turbo MLX voice landed GATED + default-OFF (mlx-audio NOT in project venv, so chatterbox_available()=False -> falls to MOSS).
- The keyless Gemini proxy (api.altidus.world, Bravoh prod) was deployed for the embedded-key problem; needs a valid Gemini key to actually serve.
- KEYSTONE (the #1 ship-blocker per EOD): can a stranger hear the co-host over a REAL set? The audio doctor flips BlackHole 2ch vs 16ch between runs on the same rig; rms=0.0 when routing is wrong. Nothing has crossed "stranger heard it over a real set."
- DEMOCRATIZATION: Viber set-prep currently runs on local Codex (BYO ChatGPT login + VIBEMIX_CODEX_ALLOW_SHELL) - is that usable by a non-dev stranger? CLAP/CUE/MOSS models need download. First-run wizard. The export-set --allow-unvalidated (2341da8b) is part of the democratization theme.
Read-only audit: code + git + artifacts (dist/, build TOC, spec files, scripts/release gates, .planning/eval-runs). Do NOT launch the live sidecar (one socket, parallel agents). Recommend live probes; do not run them.`

const DIMS = [
  { key: 'integration-head', prompt: `Assess INTEGRATION REALITY: is all the parallel-session work actually committed, on HEAD, and integrated - or is it fragmented / uncommitted / dark / behind? ${CTX}
Check: git status (uncommitted/untracked product code on the shared tree right now), git log today (are the lanes' commits all on HEAD ux-redesign-impeccable, single-parent, none orphaned), and any built-but-not-wired feature that should be in the ship but is dark (cross-ref the EOD packet's DARK items: organism morph unreachable, learn HEAD-unproven, pill grade_progress, chatterbox not in venv, auto_crate stop_reason RED gate). Is the full test suite green at HEAD (run it: source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q, report pass/fail counts; if too slow, run the repo + a couple of lane suites). Is the IPC schema codegen current (npm run codegen:ipc would be a no-op)?
Output "## Integration & HEAD reality": uncommitted/dark census, is-everything-on-HEAD verdict, test-suite state at HEAD, and the single biggest integration risk to a clean ship.` },
  { key: 'build-packaging', prompt: `Assess BUILD + PACKAGING ship-state. ${CTX}
Check the shippable artifact path: dist/ (is there a current DMG? its date vs HEAD - is it stale?), the PyInstaller specs (vibemix-core.{macos,windows}.spec) and what they bundle (grep the build TOC if present), the release gate scripts (MOSS model bundle gate, learn wavs gate, signing/Developer-ID, notarization, updater manifest, source-freshness manifest). Is the sidecar binary current vs source? Can a fresh DMG actually be produced and is it gated against shipping missing audio/voice/signature? Windows path state.
Output "## Build & packaging": the artifact-freshness verdict (is the current DMG shippable or stale), what the release gates now enforce, the gaps before a clean signed+notarized current DMG, and whether Windows is real or stubbed.` },
  { key: 'live-keystone', prompt: `Assess the LIVE PRODUCT PATH - can a real stranger RUN it and HEAR the co-host over a real set? This is the #1 ship gate. ${CTX}
Check (code + the committed audio-doctor eval-runs, NOT by launching): the BlackHole capture keystone (the 2ch-vs-16ch doctor instability, the rms=0.0 failure mode, the route-doctor that names the fix), MOSS never-mute voice readiness in a packaged context, the Gemini key/proxy path (does direct mode need a key in .env; is the proxy /register live; are the embedded keys dead). What exactly stands between install and "a stranger hears a grounded co-host line over their own set." Be concrete and ordered.
Output "## Live keystone (stranger-hears-it)": the ordered blockers from install to first grounded spoken line, which are code (ours) vs setup (user) vs external (key/proxy), and the single fix that unblocks the most.` },
  { key: 'democratization', prompt: `Assess + polish DEMOCRATIZATION - can a non-dev stranger actually use the powerful features without insider setup? Kaan explicitly wants this polished. ${CTX}
Check each power feature's setup barrier: Viber set-prep (needs local Codex + ChatGPT login + VIBEMIX_CODEX_ALLOW_SHELL - is there a non-dev path, or is Viber dev-only today?), the Gemini key (the proxy is the democratization answer - is it wired so a stranger needs no key?), local models (CLAP/CUE/MOSS auto-download via library models --install, or manual?), the first-run wizard (does it set skill level + route audio + fetch models?), the export-set --allow-unvalidated cue/set export. For each: is it democratic (works for a stranger) or gated (needs dev setup)? Name the concrete polish to make each one-click for a normal DJ.
Output "## Democratization": per power-feature, democratic-vs-gated verdict + the specific polish to make it stranger-usable, ranked by how much it blocks shipping.` },
  { key: 'see-it-now', prompt: `Determine the SHORTEST RELIABLE PATH for Kaan to SEE the latest+greatest version with ALL work integrated, RIGHT NOW. ${CTX}
He wants to open the current app with everything in. Figure out: does the bundled DMG/sidecar reflect HEAD or is it stale (so opening the .app shows old work)? Is the right move to run dev-source (VIBEMIX_DEV_SIDECAR=1 / uv run --extra ai-local python -m vibemix + the Tauri shell) so he sees current HEAD, vs rebuilding the DMG? What exact commands/flags give him the fullest current experience (local TTS on, drop-debug, the extras), and what will look dark/wrong if he opens the stale packaged app instead. Account for the one-socket rule and the frozen-sidecar caveat.
Output "## See latest+greatest now": the exact DO-THIS command sequence to run the current HEAD app with all features lit, what each flag enables, and the honest caveat about what is still dark even on HEAD (so he is not surprised).` },
]

phase('Assess')

const results = await pipeline(
  DIMS,
  (d) => agent(d.prompt, { label: `assess:${d.key}`, phase: 'Assess' }),
  (assessment, d) => agent(
    `Adversarial ship-readiness verifier. Default to skepticism. Review the assessment below for the "${d.key}" dimension. Kill optimistic "ready/done" claims that are only SRC-green (test-passing) but not PKG (in the bundle) or LIVE (a real user experiences it). Verify the specific blockers and freshness claims against the real repo/artifacts (git, dist/, specs, eval-runs). Correct any overclaim or missed blocker. Be ruthless and concrete: a clean test suite is NOT a shippable app. ${CTX}

--- ASSESSMENT (${d.key}) ---
${assessment}
---
Output "## Verify - ${d.key}": the corrected ship-truth, each claim tagged SRC/PKG/LIVE, the real blockers that survive, and anything the assessment missed or overstated. Do NOT edit any file.`,
    { label: `verify:${d.key}`, phase: 'Verify' }
  )
)

phase('Synthesis')

const parts = results.map((r, i) => `### ${DIMS[i].key}\n${r || '(failed)'}`).join('\n\n')

const report = await agent(
  `Write the file .planning/packets/2026-06-04/SHIP-READINESS-2026-06-04.md for the vibemix founder. Synthesize the five verified ship dimensions below into one honest ship-readiness verdict. No hype, no "we're ready" unless LIVE-true. Lead with the blunt answer.

Sections:
1. "## Are we ready to ship? (blunt)" - one honest paragraph + a single readiness line (e.g. "engine + features strong at SRC; NOT shippable until X, Y, Z cross PKG/LIVE"). Give a rough % only if you qualify it by tier.
2. "## Where we are" - a compact table: dimension | SRC | PKG | LIVE | the one blocker. Five rows (integration, build/packaging, live-keystone, democratization, see-it-now).
3. "## What's left to ship (ordered critical path)" - the ordered list of what must happen to ship, each tagged who-owns-it (engineering vs Kaan-setup vs external), with the single keystone first. No rushing - honest effort per item.
4. "## SEE IT NOW - latest + greatest" - the exact DO-THIS command sequence to run the current HEAD app with all features lit today, plus the honest list of what is still dark even on HEAD.
5. "## Democratization polish (ship-blocking subset)" - the specific changes that make the power features stranger-usable, ranked.
6. "## Integration health" - is all parallel-session work on HEAD + green, or is something fragmented/uncommitted/dark. State it plainly.
7. "## Owner-gates" - Kaan's calls (Gemini key for the proxy, keystone capture sign-off, Viber democratization path, mlx-audio dep, Windows scope, free-vs-Pro tier).

--- VERIFIED DIMENSIONS ---
${parts}
---

Use only evidence from the inputs; no invented numbers. Anti-slop: no em-dashes, active voice, specific, commit to a position. Do NOT commit the file (the organizer commits after). After writing, return a tight chat-ready summary (~14 lines): the blunt ready-or-not, the ordered critical path (top 4), the DO-THIS-to-see-it-now command, and the top democratization polish. Markdown.`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return report
