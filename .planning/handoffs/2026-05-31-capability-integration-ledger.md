# Capability Integration Ledger - 2026-05-31

Purpose: make sure the whole rebuild does not lose planned capability. Every
capability should end in exactly one state: integrated with proof, explicitly
deferred with evidence, or intentionally removed with rationale.

Status values:

- `unknown`: not audited yet.
- `candidate`: worth carrying forward, but not accepted.
- `integrating`: actively being rebuilt.
- `integrated`: rebuilt and accepted by verifier.
- `deferred`: deliberately later, with gate named.
- `drop`: intentionally removed.

## Verification Loop

Claude owns speed and breadth:

- fan out scouts;
- implement one bounded milestone at a time;
- update this ledger and the package checklist;
- hand Codex a verifier packet.

Codex owns acceptance:

- inspect current files, not summaries;
- rerun relevant checks;
- verify runtime/live claims with logs or websocket proof;
- verify package boundaries and dirty-file classification;
- reject vague, unproven, or mixed-scope milestones.

No row becomes `integrated` until Codex accepts the verifier packet.

## Ledger

| Capability | Status | Target Slice | Carry Forward Source | Proof Gate | Notes |
|---|---|---|---|---|---|
| Runtime audio truth | candidate | Runtime core | `src/vibemix/audio/*`, `src/vibemix/state/*`, live proof notes | Source-mode live audio + state/event tests | Live audio must outrank screen/model inference. |
| MusicState refresh ownership | candidate | Runtime core | `src/vibemix/state/refresh.py`, package checklist | State tests + architecture review | Preserve single writer invariant. |
| Event detection and drop timing | candidate | Runtime core | `state/event_detector.py`, `drop_predict.py`, Mix Timing Oracle lane | Focused state tests + live/audio timing proof | Separate demo claims from rebuild truth. |
| Evidence registry and citations | candidate | AI co-host core | `EvidenceRegistry`, citation linter, grounding-review skill | Citation tests + runtime cited event proof | No grounded claim without resolvable evidence. |
| AI-message observability | candidate | AI co-host core | `runtime/ai_observability.py`, `agent/dj_cohost.py`, `bench/run.py`, Learn observability files | Focused tests + fail-soft runtime proof | Strong carry-forward for verifier/audit timeline. |
| Model router / no hardcoded models | candidate | AI co-host core | `llm/model_router`, `_router_config.py`, no-hardcoded-model checks | LLM tests + model grep/check | Keep model choice behind router. |
| TTS chain and local/free voice | candidate | AI co-host core | Cartesia chain, Local MOSS hold lane | TTS tests + license/model/install/bundle proof | Do not ship local model without attribution and install story. |
| Vibe Judge voice evidence | candidate | AI co-host core | `intel/judge_voice.py`, `tests/intel/test_judge_voice.py`, move-grade lanes | Pure tests + runtime coach integration + grounding review | Engine line is not live speech until coach consumes it. |
| IPC schema and generated TS | candidate | UI bus | IPC packet, `messages.schema.json`, generated TS/validator, Python wrappers | `check_ipc_schema`, wiring checker, UI check/build | Preserve 72-count pruning unless rebuild intentionally changes it. |
| Tauri bridge and websocket bus | candidate | UI bus/Desktop | `runtime/ws_bus.py`, `session_loop.py`, Rust sidecar | Source-mode ws probe + Tauri UI proof | Source bus proof is not GUI proof. |
| Compact pill / next suggestion | candidate | UI UX | pill package, pill polish handoff | UI tests + screenshot/live bus proof | Keep compact visible text plus recoverable detail. |
| Settings/session/profile diagnostics | candidate | UI UX | Package 2, settings tests | UI tests + Tauri settings proof | Avoid subscription spam and stale profile fetches. |
| Library CLAP semantic search | candidate | Library/cue | library search/similar, real CLAP eval lane | Real CLAP fixture eval + model gate | Need real-ONNX coverage before broad safety claims. |
| Cue detection and provenance | candidate | Library/cue | smart_cues, ingest, cue_folder, move_grade | Cue tests + provenance visible through export/UI | Preserve source and number, do not fabricate cues. |
| Rekordbox/XML and M3U8 export | candidate | Library/cue | cue export/folder lanes | Export tests + import docs/proof | Additive files, no proprietary DB writes. |
| Serato Markers2 / Mixxx carrier | candidate | Library/cue | `export_serato.py`, `docs/mixxx.md`, `pyproject.toml` extra | Codec tests + golden vector or real app eye-check | GPL runtime dependency boundary must stay explicit. |
| Cue agreement flywheel | candidate | Library/cue/Eval | `library/cue_agreement.py`, cue agreement tests | Pure tests + privacy/ingest integration proof | Producer only until integration accepted. |
| Viber grounded tool spine | candidate | Library/Viber | Viber/library MCP tools, fetch/search constraints | Tool tests + UI/library proof | Preserve web_search -> fetch_url provenance. |
| Codex curation workflow | candidate | Library/Viber | `library/codex_curate.py` | Focused tests + CLI/UI consumer proof | Large candidate; keep grounded discovery boundaries. |
| Learn tutor observability | candidate | Learn core | `learn/observability.py`, `learn/runtime.py`, Learn tests | Learn evidence tests + runtime event proof | Authored tutor speech still belongs in AI-message timeline. |
| Learn/live data bridge | candidate | Learn core/Runtime core | Learn runtime, skill recognizer, AI-message observability, cue/judge evidence, deck/audio state | End-to-end Learn proof that live evidence becomes tutor/credit context | Learn must benefit from the same evidence spine as live co-host, not remain a silo. |
| Earned wall / mastery credit | candidate | Learn core | Package 9, Learn lanes | Learn tests + live event producer proof | Never show mastered without observable cited evidence. |
| Beatmatch producer gap | deferred | Learn core | `test_live_reality_pins.py`, beatmatch judge notes | Wire real producer or keep false-mastered pin | Consumer exists; producer remains the trap. |
| Debrief TLDR and drills | candidate | Debrief | `debrief/tldr.py`, `debrief/drills.py`, tests | Generation tests + citation resolution proof | Keep uncited output stripped/retried. |
| Real CLAP eval gate | candidate | Eval/proof | `scripts/eval/clap_retrieval.py`, real corpus fixtures | Eval command + target floor | Fixture is current proof, not full ONNX CI. |
| Live reality pins | candidate | Eval/proof | `tests/repo/test_live_reality_pins.py` | Pin tests + reviewed rationale | Useful to prevent false live claims during rebuild. |
| Binary freshness verification | candidate | Desktop/release | `verify_binary.py`, sidecar freshness scripts | Dist tests + packaging hook proof | Separate from runtime features. |
| Signing/notarization flow | candidate | Desktop/release | signing hold lane | Dry-run + full sign/notarize/staple proof | No secrets in logs or commits. |
| Dependency modernization | deferred | Dependencies | dependency modernization packet | Ring-specific checks | Wait until runtime/UI spine is green. |
| Launch/pricing collateral | deferred | Public claims | launch/pricing packages | Cost proof + claim review | Public copy must trail verified runtime/cost evidence. |
| Monetized product posture | candidate | Public claims/Release | final acceptance contract, launch/pricing docs, README/docs | Claim review + pricing/install proof | The app no longer has to preserve a fully open-source claim; license hygiene remains a constraint. |
| Visual shell/settings proof | candidate | UI UX | frontend proof lanes, screenshots | UI tests/build/screenshots | Mockups are not live product proof. |

## Unknown Sweep

Before final completion, run a sweep for:

- dirty files not listed in the package checklist;
- planned docs not represented in this ledger;
- tests that pin false current reality but were not re-evaluated after rebuild;
- demo-only notes that survived as product truth;
- stale generated files;
- dead worktrees and orphan generated assets;
- duplicated old modules that the rebuild no longer uses.

## Learn Integration Rule

Learn is a first-class rebuild slice, not a leftover teaching surface.

The rebuild should make live runtime evidence reusable by Learn:

- cue/judge/deck evidence should become tutor context when relevant;
- live skill observations should become cited mastery credit only when a real
  producer exists;
- Learn tutor speech should use the same `ai_message` observability stream as
  live co-host and bench runs;
- debrief drills should be able to feed back into Learn practice suggestions;
- Learn UI should consume the same bus discipline as the session UI;
- no lesson or mastery badge should claim progress that the live app cannot
  observe.

Claude workflow note: assign a dedicated Learn integration scout that reads the
runtime/evidence/cue/judge slices too. A Learn-only scout that reads only
`src/vibemix/learn/**` will miss the point.
