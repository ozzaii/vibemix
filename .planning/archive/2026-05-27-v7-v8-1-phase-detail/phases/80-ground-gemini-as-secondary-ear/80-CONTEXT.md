# Phase 80: GROUND — Gemini as Secondary Ear - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Let Gemini *also* hear the audio as a **secondary** grounding input ("if it can hear in hollow space, use it") — fed alongside the structured DSP evidence, **never as the primary perceiver** — hallucination-guarded throughout. The DSP/structured evidence remains authoritative (trust-the-audio, invariant #3); a Gemini claim that contradicts or isn't backed by the DSP evidence is guarded (strips / abstains). The reaction model is config-resolved via `model_router.resolve(...)` (zero hardcoded literals) so the bench's (P81) winning model swaps in by config alone.

- **GROUND-01** — the audio part is fed to Gemini alongside the structured evidence, hallucination-guarded; trust-the-audio still wins.
- **GROUND-02** — the reaction model is config-resolved via `model_router` (CI grep-gate holds); the bench's winning model is a config swap.

**Out (historical v8.1 live-reaction scope):** no new live-reaction AI
provider, no new ws port/IPC envelope, no making Gemini the primary perceiver,
no new DSP. Phase 90 later superseded library embeddings with local CLAP ONNX;
Viber set-prep/chat now uses local Codex for the current product path. Additive
— with the audio-secondary path gated OFF, the prompt + reaction are
byte-identical to the v8.0 baseline.
</domain>

<decisions>
## Implementation Decisions

### GROUND-01 — audio fed as a secondary grounding Part
- Feed the master-output audio to Gemini as a **secondary** input alongside the structured DSP evidence in the reaction path. The DSP evidence is PRIMARY/authoritative; the audio is a corroborating second ear, never the source of truth.
- **Hallucination guard:** Gemini's audio-derived claims go through the SAME citation-grounding gate (invariant #2) + trust-the-audio (invariant #3) — a claim not backed by the DSP `EvidenceRegistry` strips / abstains (to `<silence/>`). The audio can make a reaction *richer/more specific*, but cannot *fabricate* an event the DSP didn't detect.
- **Audio source:** reuse the existing clean audio buffer already maintained for the grounding/recall seam (the `_clean_audio_buf` family) — do NOT add a new capture path or ws port. The exact feed mechanism (audio Part on the generate_content-style call vs the LiveKit `RealtimeModel` session) is RESEARCH's job to confirm against the current live reaction path.
- **Gated:** a feature flag (default OFF) controls the audio-secondary path. Flag off → byte-identical to v8.0 (the cold path adds nothing). Flag is the additive seam.

### GROUND-02 — config-resolved reaction model
- The reaction model resolves via `model_router.resolve(...)` with NO hardcoded model literal (the CI grep-gate `test_model_literal_gate.py` must stay green).
- Expose the reaction model as a config-addressable alias so the bench (P81) can swap the winning model by config alone — no code change.
- Confirm whether the current reaction path already resolves via `model_router`; if a literal slipped in anywhere on this path, route it through the resolver.

### Citation grounding / trust-the-audio (invariants #2 + #3)
- The audio-secondary path MUST NOT weaken the gate. Pin a test: a Gemini claim about an event the DSP evidence does not support is stripped/abstained even with the audio Part present. Trust-the-audio wins.

### Claude's Discretion
- The exact flag name, where the audio Part is attached on the reaction call, audio encoding/length window (reuse the grounding/recall buffer's format + bound), and the config-alias name for the reaction model — planner's call after research confirms the live reaction path, smallest additive diff, follow `agent/` + `llm/` conventions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent/dj_cohost.py` — the LiveKit `RealtimeModel` session + the Gemini reaction path; already has the `_clean_audio_buf` + the Phase-77 grounding seam + Phase-65 recall seam (the off-loop "consult on track-aware events → inject" pattern audio-secondary can mirror).
- `llm/model_router.py` — config-driven model resolution (no hardcoded literals, CI grep-gated). GROUND-02's home.
- `state/evidence_registry.py` + the `CitationLinter` gate (lens-blind, registry-backed) — the hallucination guard the audio claims pass through.
- Prior art (retired POC, ported): the cascade pattern fed mic audio as a second multimodal Part (`feedback_mic_audio_as_multimodal_part`); the v4 lookahead fed a 3rd audio Part. The intuition is ported; verify the CURRENT path's mechanism.

### Established Patterns
- Additive gated design; cold-path byte-identity; trust-the-audio (live audio evidence authoritative; AI reacts to real detected events, never invents); single in-flight Gemini generation with stale-age force-clear.
- `model_router.resolve(...)` everywhere — never inline a model name.

### Integration Points
- `agent/dj_cohost.py` reaction path (audio Part attach + the hallucination guard).
- `llm/model_router.py` (config-addressable reaction-model alias).
- The citation-grounding gate (audio-claim guard test).

### Verification reality
- Unit-testable WITHOUT the API: flag-off byte-identity; the audio Part is attached when flagged on (assert the request shape with a fake client); an un-backed audio-derived claim strips via the gate (fake the model output, assert the linter strips it); model resolves via `model_router` (grep-gate). The "does the second ear actually make reactions better / is it worth the cost" judgment is the Phase-81 BENCH (the audio+DSP vs DSP-only cells) + Kaan's-ear (parked, never faked).
</code_context>

<specifics>
## Specific Ideas
- "If it can hear in hollow space, still use it" (Kaan's words) — the audio is a *bonus* grounding signal, not a crutch. The whole point of the milestone is that Gemini is the VOICE/interpreter, not the EAR; this phase lets it peek at the audio WITHOUT letting it hallucinate.
- The bench (P81) has an explicit input-grounding axis: raw-audio | DSP-only/no-audio | audio+DSP | audio+DSP+trajectory+genre. This phase builds the "audio+DSP" capability the bench measures, and the "no-audio" cell tests whether the intelligence resides in the structured evidence rather than the raw ear.
</specifics>

<deferred>
## Deferred Ideas
- The actual model CHOICE (which Gemini variant wins) → decided by Phase-81 BENCH; GROUND-02 only makes it a config swap.
- The Gemini Live `native-audio` Live-API path as the PRIMARY perceiver → explicitly out (Gemini is the voice, not the ear; native-audio path is a separate seam, gated out until the bench justifies it).
- Proving the second ear is worth it (audio+DSP vs DSP-only) → Phase-81 BENCH + Kaan's ear.
- Curator+co-host engine/taste unification → Phase 82.
</deferred>
