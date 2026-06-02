export const meta = {
  name: 'everything-capability-inventory',
  description: 'Read-only deep inventory of every vibemix product capability across all silos, classified WORKS_AND_PROVEN..DROP_OR_DELETE with code/doc/test evidence. Schema-LESS prose output (robust for deep-work agents). No product edits/stage/commit/app-launch.',
  phases: [
    { title: 'Inventory', detail: '12 silo agents enumerate + classify capabilities, each returns a markdown section' },
    { title: 'Audit', detail: 'honesty auditor refutes over-claims + confirms CLAIMED_BUT_ABSENT across all sections' },
    { title: 'Synthesize', detail: 'assemble CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md body' },
  ],
}

const RO = `READ-ONLY agent. Repo: /Users/ozai/projects/dj-set-ai (branch live-tuning-or-brain).
HARD CONTRACT: NEVER edit, stage, commit, or launch/control the app (no \`python -m vibemix\`). ALLOWED: \`git show/log/diff/status\`, ripgrep/grep, Read, codegraph tools, and TARGETED \`uv run pytest -q <files>\` (repo .venv; system python3=3.14 lacks livekit). Tests are read-only verification, not the app.
CLASSIFY each capability with EXACTLY one label:
- WORKS_AND_PROVEN  (source + a passing test OR a captured live/eval artifact proves it end-to-end)
- WORKS_SOURCE_ONLY (source correct + unit-tested, but no live/packaged proof)
- WIRED_BUT_UNPROVEN (both ends wired but no test/proof it actually fires)
- CLI_ONLY          (works from CLI, not surfaced in the app/GUI)
- PRESENT_ORPHANED  (code exists but nothing calls it / no live call-site)
- CLAIMED_BUT_ABSENT (a doc/packet claims it but the code is missing or a stub)
- HOLD              (gated behind grounding-review / live proof / ear-pass)
- DROP_OR_DELETE    (dead, superseded, or a fake/placeholder that should go)
Be honest: prefer WORKS_SOURCE_ONLY over WORKS_AND_PROVEN unless you actually ran a proving test. MOSS is the only TTS; flag any cloud/fake spoken fallback as DROP_OR_DELETE. Durable archive of CLAIMED capabilities: .planning/packets/2026-06-01/INDEX.md, CODEX_PACKAGE_SWEEP_STATUS.md, CODEX_GOLD_STRUCTURE.md, .planning/handoffs/2026-05-31-package-checklist.md.

OUTPUT FORMAT — return a MARKDOWN SECTION ONLY (no schema, no tool call, your final text IS the deliverable):
## <silo-id>
_one-line silo state summary_

- **<capability name>** — \`[CLASS]\` — evidence: \`file:line\` / test / doc-anchor / NOT-FOUND — next: <recommended next package>
- ... (one bullet per distinct capability)

Keep each bullet to one line. Be THOROUGH (enumerate every distinct capability) but TIME-BOUNDED — return your section even if you could not open every file; mark unknowns honestly. Every bullet needs a real file:line / test / doc anchor or an explicit NOT-FOUND.
`

const SILOS = [
  { id: 'app-ui', focus: `APP SHELL + UI SURFACES. tauri/ui/src/** (DesktopShell, session, settings drawer, library webview, pill, debrief window), mascot.html overlay, tauri/src-tauri Rust commands. Enumerate every user-facing surface/control and whether it is live-wired to a backend handler (ipc.* both-end). Flag dead buttons / blank panels / unwired controls.` },
  { id: 'runtime-ipc', focus: `RUNTIME / SESSION LOOP / TRANSPORT. src/vibemix/runtime/** (ws_bus, session_loop, wizard, suggestion service, soak, ttft), ws bus 127.0.0.1:8765, ipc message schema + register_handler/emitIpc, __main__ orchestrator. Inventory each loop + each IPC channel: both-end wired? fired in a test?` },
  { id: 'cohost-brain', focus: `CO-HOST BRAIN. src/vibemix/state/** (music_state, refresh single-writer, event_detector typed events + cooldowns, coach prompt build, evidence_registry, deck_*), prompts/** (matrix, filter, negative_dict), coach/citation_linter, agent/dj_cohost reaction path. Inventory each event type, the grounding/citation contract, the anti-slop guards.` },
  { id: 'tts-voices', focus: `TTS / VOICES. agent/tts_chain (_build_direct_chain, build_proxy_tts_chain), agent/local_tts (MOSS-TTS-Nano ONNX), agent/proxy_client, agent/line_voice, agent/emote_parser sanitizer, agent/tts_sanitizer (citation-out-of-tts, new), agent/language_guard (english-only, new). Confirm MOSS is the ONLY provider in both modes; flag any cloud/fake spoken fallback as DROP_OR_DELETE.` },
  { id: 'viber-curation', focus: `VIBER / SET-PREP CURATION. library/toolset (grounded tool core), codex_curate, mcp_server (MCP STDIO), telegram_bridge, the chat/curate/build-set/export-set CLI. Codex is the product backend. Inventory each grounded MCP tool, seen-set anti-hallucination, freshness/fail-closed guards, Telegram surface.` },
  { id: 'library-clap-cue', focus: `LIBRARY / EMBEDDINGS / CUE. library/clap_engine (ONNX Xenova 512-dim, mean-centering), sqlite-vec vibe search, next_suggestion pill engine, ingest/embed-folder, cue engine (CUE-DETR ONNX, cue_folder, export_serato), rekordbox import, library stats/budget/models CLI. Inventory search/similar/ingest/cue-export and proof state.` },
  { id: 'learn-earned', focus: `LEARN / EARNED SKILL-TREE (v11.0). learn/** (courses, prompts, beatmatch_judge, skill_recognizer), the Competent←lessons / Mastered←cited-live-demo two-stage gate, Earned Wall refresh, Mastered vocal. Inventory each competency + producer/consumer; flag the BEATMATCH_GRADED missing-producer honesty boundary.` },
  { id: 'packaging-release', focus: `PACKAGING / RELEASE / SIGNING. PyInstaller specs (vibemix-core.{macos,windows}.spec), build_sidecar, sidecar freshness guard, dist/ DMG, code-sign/notarize/staple flow, the Bravoh keyless proxy (api.altidus.world). Does the SHIPPED artifact match current HEAD? signed/notarized? boots clean? MOSS model bundled-or-downloadable on a fresh machine?` },
  { id: 'flx4-live-platform', focus: `FLX4 / MIDI / LIVE-PROOF / PLATFORM. midi/** (10-controller profiles, state), platform/_audio_*.py (macOS BlackHole / Windows WASAPI), deck capture/signal, live-context proof actions, FLX4 acceptance. Inventory controller decode, audio capture, deck identity, and the live-acceptance proof state (proven vs aspirational).` },
  { id: 'eval-intel-judge', focus: `EVAL GATES / INTEL / JUDGE. intel/** (claims/decision contracts, transition_scorer, taste_model, musical_ontology, transition_judge / judge_voice), scripts/eval/** (clap_retrieval, cue_detect), bench/ harness. Inventory each eval gate + the Vibe Judge (deterministic-decides / Gemini-voices / abstains) + its live-artifact proof state.` },
  { id: 'mixxx-goldmine-research', focus: `MIXXX / GOLDMINE RESEARCH ADOPTION. The recovered Mixxx goldmine maps + sub-specs (beat-detection/beatgrid, tempo/phase sync, cue logic, key detection, EQ/filter DSP, controller-mapping, crossfader curve math, loop/beatjump, waveform RGB). Classify each researched idea: ADOPTED (in code, give file:line), PARTIAL, RESEARCH_ONLY (design doc only — use CLAIMED_BUT_ABSENT or PRESENT_ORPHANED), or DROP. GPL-2.0 = learn-from-spec only — flag any vendored-source risk.` },
  { id: 'memory-observability', focus: `MEMORY / RECALL / OBSERVABILITY. memory/** (memory.db copilot store, sqlite-vec, VIBEMIX_RECALL_ENABLED default off), the AI-message observability spine (record_session_ai_message, events.jsonl, ai_observability, response_path artifacts), debrief/** post-session review. Inventory recall fragment injection, the observability writers, the debrief UI.` },
]

phase('Inventory')
log(`Inventorying ${SILOS.length} silos (schema-less prose sections).`)
const sections = (await parallel(SILOS.map(s => () => agent(RO + `SILO INVENTORY — ${s.id}.\n${s.focus}\nReturn the markdown section per the OUTPUT FORMAT. silo id = "${s.id}".`, { label: `inv:${s.id}`, phase: 'Inventory' })))).filter(Boolean)

phase('Audit')
const audit = await agent(RO + `HONESTY AUDITOR. Below are ${sections.length} silo inventory sections. Your job: (1) refute any over-claim — if a capability is tagged WORKS_AND_PROVEN but the evidence is only source/unit-level (no live/eval artifact), call it out as "downgrade to WORKS_SOURCE_ONLY"; (2) confirm or refute every CLAIMED_BUT_ABSENT (grep/codegraph hard — a renamed symbol is not absent); (3) scan the durable packets for any capability they claim WORKS that these sections suggest is actually absent/stub/orphaned. Return a markdown "## Honesty audit" section: a short list of corrections, each as \`- <silo> / <capability>: <correction> (evidence file:line)\`. Be terse and evidence-anchored.
SECTIONS:\n\n${sections.join('\n\n')}`, { label: 'audit:honesty', phase: 'Audit' })

phase('Synthesize')
const doc = await agent(RO + `SYNTHESIS — write the FULL markdown BODY for CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md. You are given ${sections.length} silo sections + an honesty audit. Structure:
(1) one-paragraph state-of-the-product summary;
(2) a count table: how many capabilities fall in each of the 8 classes (count them across all sections, AFTER applying the audit's downgrades);
(3) all ${sections.length} silo sections, verbatim but WITH the honesty-audit corrections applied inline (adjust the \`[CLASS]\` tag where the audit downgraded it; append " — AUDIT: <note>" to corrected bullets);
(4) a "## DROP_OR_DELETE / dead surfaces" rollup list;
(5) a "## CLAIMED_BUT_ABSENT (doc says yes, code says no)" rollup list — the honesty gaps;
(6) a "## Top recommended next packages" rollup (the highest-value next steps pulled from the per-capability 'next:' fields).
Output ONLY the markdown body (no outer code fence, no preamble) — it is written verbatim to the doc.
HONESTY AUDIT:\n${audit}\n\nSILO SECTIONS:\n\n${sections.join('\n\n')}`, { label: 'synth:inventory', phase: 'Synthesize' })

return { workflow: 'everything-capability-inventory', section_count: sections.length, sections, audit, docMarkdown: doc }
