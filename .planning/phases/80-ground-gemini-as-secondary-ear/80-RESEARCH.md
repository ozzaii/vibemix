# Phase 80: GROUND — Gemini as Secondary Ear - Research

**Researched:** 2026-05-26
**Domain:** Live LLM reaction path (google.genai multimodal generate_content_stream), audio-Part grounding, citation-linter anti-hallucination gate, config-driven model resolution
**Confidence:** HIGH (all findings verified against live source; suite baseline green)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
**GROUND-01 — audio fed as a secondary grounding Part**
- Feed the master-output audio to Gemini as a **secondary** input alongside the structured DSP evidence in the reaction path. The DSP evidence is PRIMARY/authoritative; the audio is a corroborating second ear, never the source of truth.
- **Hallucination guard:** Gemini's audio-derived claims go through the SAME citation-grounding gate (invariant #2) + trust-the-audio (invariant #3) — a claim not backed by the DSP `EvidenceRegistry` strips / abstains (to `<silence/>`). The audio can make a reaction *richer/more specific*, but cannot *fabricate* an event the DSP didn't detect.
- **Audio source:** reuse the existing clean audio buffer already maintained for the grounding/recall seam (the `_clean_audio_buf` family) — do NOT add a new capture path or ws port. The exact feed mechanism (audio Part on the generate_content-style call vs the LiveKit `RealtimeModel` session) is RESEARCH's job to confirm against the current live reaction path.
- **Gated:** a feature flag (default OFF) controls the audio-secondary path. Flag off → byte-identical to v8.0 (the cold path adds nothing). Flag is the additive seam.

**GROUND-02 — config-resolved reaction model**
- The reaction model resolves via `model_router.resolve(...)` with NO hardcoded model literal (the CI grep-gate `test_model_literal_gate.py` must stay green).
- Expose the reaction model as a config-addressable alias so the bench (P81) can swap the winning model by config alone — no code change.
- Confirm whether the current reaction path already resolves via `model_router`; if a literal slipped in anywhere on this path, route it through the resolver.

**Citation grounding / trust-the-audio (invariants #2 + #3)**
- The audio-secondary path MUST NOT weaken the gate. Pin a test: a Gemini claim about an event the DSP evidence does not support is stripped/abstained even with the audio Part present. Trust-the-audio wins.

### Claude's Discretion
- The exact flag name, where the audio Part is attached on the reaction call, audio encoding/length window (reuse the grounding/recall buffer's format + bound), and the config-alias name for the reaction model — planner's call after research confirms the live reaction path, smallest additive diff, follow `agent/` + `llm/` conventions.

### Deferred Ideas (OUT OF SCOPE)
- The actual model CHOICE (which Gemini variant wins) → decided by Phase-81 BENCH; GROUND-02 only makes it a config swap.
- The Gemini Live `native-audio` Live-API path as the PRIMARY perceiver → explicitly out (Gemini is the voice, not the ear; native-audio path is a separate seam, gated out until the bench justifies it).
- Proving the second ear is worth it (audio+DSP vs DSP-only) → Phase-81 BENCH + Kaan's ear.
- Curator+co-host engine/taste unification → Phase 82.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GROUND-01 | The audio part is fed to Gemini alongside the structured evidence, hallucination-guarded. | **Already mechanically present** — `_clean_audio_buf` master audio is attached as Part 1 to every reaction `generate_content_stream` call (`dj_cohost.py:1400, 1511-1514`). The phase's real work is the **secondary-ear framing + guard test + gated flag**, not adding a new capability. See §Critical Findings. |
| GROUND-02 | The reaction model is config-resolved via `model_router` and chosen by the bench result. | **Already resolved via router** — `LLM_MODEL = resolve("live_coach")[0]` (`agent/config.py:25`), consumed at `dj_cohost.py:1693`. No hardcoded literal on the path; CI grep-gate green. The bench-swap alias is `live_coach` in `_router_config.py`. See §GROUND-02. |
</phase_requirements>

## Summary

The single most important question — *how does the live reaction path call Gemini, and can a second audio Part be fed* — resolves decisively in the phase's favor. **The live reaction is NOT the LiveKit `RealtimeModel` continuous-audio session.** `DJCoHostAgent.llm_node` deliberately **hijacks** LiveKit's `llm_node` hook and calls `self._genai_client.aio.models.generate_content_stream(...)` directly with a `contents` list of discrete `types.Part` objects (`dj_cohost.py:1692-1696`). The module docstring states this verbatim: *"Hijacks `llm_node` to bypass LiveKit's text-only cascade and call `google.genai` directly with the last INVOKE_AUDIO_SECONDS of audio attached as a multimodal Part. The LLM literally hears the music."*

This means **discrete audio Parts are the native mechanism** — there is no RealtimeModel constraint to work around. In fact the master-output audio is **already** Part 1 of every reaction call (`audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)` → `types.Part.from_bytes(data=audio_wav, mime_type="audio/wav")`), and the prompt already labels it `"P1 = last {secs}s of live BlackHole audio (audience perspective)"`. Gemini already hears the master. The agent additionally supports a mic Part (P2) and a source-file lookahead Part (P3) via the same `contents.append(...)` pattern.

**Therefore GROUND-01 is NOT "add audio to a path that has none."** It is: (a) make the secondary-ear *framing* explicit and *gated* so the audio-as-grounding-signal contract is deliberate and flag-controlled (flag OFF → byte-identical v8.0); (b) **prove with a test** that the citation-linter gate (invariant #2) still strips any audio-derived claim not backed by the DSP `EvidenceRegistry`. The linter validates citations against the registry snapshot **only** — it never reads the prompt or the audio Parts — so an audio Part structurally **cannot** bypass the gate. That is the load-bearing safety property and the phase's core deliverable.

**GROUND-02 is essentially already satisfied** and needs only a confirming test + (optionally) the bench-swap alias documented. `LLM_MODEL` resolves through `model_router.resolve("live_coach")` at import; the reaction call passes `model=LLM_MODEL`; the CI grep-gate is green; there is no hardcoded literal on the path.

**Primary recommendation:** Implement GROUND-01 as a gated *framing + guard* change on the existing Part-1 audio, NOT a new audio capture. Add a default-OFF `VIBEMIX_GROUND_SECONDARY_EAR` flag that toggles only the secondary-ear *prompt framing* (and, if desired, whether Part 1 is presented as a grounding signal vs the existing "audience perspective" label). Pin three tests: (1) flag-OFF byte-identity of the `contents` request shape vs v8.0; (2) flag-ON attaches/frames the audio Part as asserted against a fake genai client; (3) an audio-derived claim citing an un-registered event strips the whole turn via `CitationLinter`. GROUND-02: pin a test that the reaction model resolves via `model_router` and document `live_coach` as the bench-swap alias.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Perceive what's playing (events, BPM, key, genre, deck) | DSP/state engine (`state/`, `library/`) | — | Invariant #3 "trust the audio": the deterministic DSP/embedding stack is the authoritative EAR. Gemini never owns perception. |
| Feed raw master audio to Gemini | Agent reaction path (`agent/dj_cohost.py` `llm_node`) | — | The audio Part rides the same direct `generate_content_stream` call the agent already owns. No new tier. |
| Interpret/voice the reaction | Gemini (via agent) | audio Part (secondary grounding) | Gemini is the VOICE; the audio is a corroborating *second ear*, never the primary perceiver. |
| Guard hallucination | `coach/citation_linter.py` + `state/evidence_registry.py` | — | Registry-backed, lens-blind, prompt-blind. Validates citations against observations only — audio Parts cannot bypass it. |
| Resolve the reaction model | `llm/model_router.py` + `llm/_router_config.py` | — | Single allowlisted literal table; CI grep-gated. The bench-swap alias lives here. |

## Standard Stack

No new dependencies. This phase is additive wiring on the existing stack.

### Core (already present, pins in `pyproject.toml`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | (pinned) | The reaction call is `client.aio.models.generate_content_stream` with `types.Part.from_bytes(...)` audio Parts. | The sole AI provider (Gemini-only, locked). Already the live reaction path. |
| `numpy` / `scipy` | (pinned) | `snapshot_wav` peak-normalizes + WAV-encodes the ring snapshot. | Already the DSP/audio-encode path. |

**Installation:** none — no packages added or removed this phase.

**Package Legitimacy Audit:** N/A — this phase installs zero external packages. Confirmed: the only imports added (if any) are intra-package (`vibemix.*`) and stdlib.

## Critical Findings (the questions the orchestrator asked)

### 1. How does the live reaction path call Gemini? — VERIFIED

**It is a direct `google.genai` `generate_content_stream` call with discrete audio Parts — NOT the LiveKit `RealtimeModel`.** [VERIFIED: src/vibemix/agent/dj_cohost.py]

- `DJCoHostAgent` subclasses `livekit.agents.Agent` but **overrides `llm_node`** (`dj_cohost.py:1161`). The override bypasses LiveKit's text-only cascade entirely. Module docstring lines 1-7 state this explicitly.
- The LLM invocation is at **`dj_cohost.py:1692-1696`**:
  ```python
  stream = await self._genai_client.aio.models.generate_content_stream(
      model=LLM_MODEL,
      contents=contents,
      config=gen_cfg,
  )
  ```
- `contents` is a plain Python list built at **`dj_cohost.py:1511-1552`**:
  ```python
  contents: list = [
      text_prompt + parts_clause + history_clause,            # element 0: the grounded text packet
      types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),  # Part 1: master/mix audio (ALWAYS)
  ]
  if mic_attached:    contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))      # P2
  if lookahead_attached: contents.append(types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav"))  # P3
  if screen_jpeg and not skip_screen: contents.append(types.Part.from_bytes(data=screen_jpeg, mime_type="image/jpeg"))
  ```
- **The master-output audio is already attached as Part 1 to every reaction turn.** `audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)` (`dj_cohost.py:1400`). So GROUND-01's audio feed already exists mechanically; the phase work is the *secondary-ear framing + guard test + gated flag*, not a new capability.
- There is a second brain path: when `or_client is not None`, the stream comes from `stream_or(...)` (OpenRouter, OpenAI-compat) with the **same `contents`** list (`dj_cohost.py:1676-1690`). The OpenRouter adapter passes inline audio through to Gemini, so the audio-Part contract holds on both paths. Any GROUND-01 framing change must apply to the `contents` list (shared by both), not a path-specific branch.

**Feasibility verdict: GROUND-01 is straightforward.** The discrete-Part mechanism is already the live mechanism. No RealtimeModel-stream workaround is needed. (Note: a `RealtimeModel`/native-audio Live-API path is mentioned in the agent layer but is **out of scope** per CONTEXT Deferred Ideas — Gemini is the voice, not the primary ear.)

### 2. What audio buffer is available to feed? — VERIFIED

`self._clean_audio_buf` is the canonical source and is **already used** for both the live reaction Part and the off-loop grounding embed. [VERIFIED: src/vibemix/agent/dj_cohost.py, src/vibemix/audio/constants.py]

- **Format:** `snapshot_wav(buf, seconds)` (`audio/features.py:93`) returns peak-normalized **WAV bytes** (`b"RIFF"...`), `mime_type="audio/wav"`. The 48k→16k resample is handled upstream in the capture backend; `clean_audio_buf` auto-sizes to `INVOKE_AUDIO_SECONDS + 5s`.
- **Length window:** `INVOKE_AUDIO_SECONDS = 60.0` (full path) or `DIET_AUDIO_SECONDS = 6.0` (ack-eligible events) (`audio/constants.py:20`, `dj_cohost.py:104`). The live reaction already chooses the window per event type at `dj_cohost.py:1356`.
- **Lock discipline:** `AudioBuffer` is lock-protected; `snapshot()` / `snapshot_wav()` are cheap synchronous reads safe to call from the event loop. The off-loop grounding seam (`_maybe_dispatch_grounding`, `dj_cohost.py:1000`) snapshots the SAME buffer synchronously and hands bytes to the executor — the established "no second capture path" pattern (key-decision A3 in 77-04-SUMMARY).
- **Encodable as a Gemini audio Part with no new path:** YES — it already is (`dj_cohost.py:1513`). No new ws port, no new capture, no new IPC envelope.

### 3. The hallucination guard — VERIFIED that an audio Part CANNOT bypass it

The gate is **registry-backed and prompt/audio-blind**. [VERIFIED: src/vibemix/coach/citation_linter.py, src/vibemix/state/evidence_registry.py]

- The post-stream gate runs at **`dj_cohost.py:1973-1976`**:
  ```python
  if self._linter_wired and self._linter is not None:
      lint_result = self._linter.check(full_text, snapshot, mode="live")
  ```
- `CitationLinter.check(text, registry_snapshot, mode)` (`citation_linter.py:94`) parses every citation atom out of the reply text and validates each against the `EvidenceRegistry` **snapshot** — `has(source, key, t, tol)` / existence-check. **It never reads the prompt, the audio Parts, or anything Gemini "heard."** Decision is response-level binary: one un-grounded atom → whole turn strips (`citation_linter.py:139-173`).
- **Why an audio Part cannot bypass the gate (structural):** the linter's inputs are `(full_text, registry_snapshot)`. The audio Part influences only what Gemini *says* (the `full_text`), and every claim it wants credit for must carry a citation atom (`[ev:KICK_SWAP@45.2]`, `[track:<id>]`, etc.) that resolves in the registry. The registry is written ONLY by the DSP single-writer loop + `EventDetector` + `register_library` (invariant #1). So an audio-derived claim about an event the DSP never detected has **no registry entry to cite** → the atom misses → `valid=False` → strip to `<silence/>` at `dj_cohost.py:2055`. Trust-the-audio (invariant #3) wins by construction.
- **The provable test (GROUND-01 guard, unit, no API):** fake the genai stream to return a reply containing `[ev:PHANTOM_DROP@<t>]` (an event NOT in the registry snapshot), with the audio Part attached. Assert `CitationLinter.check(...)` returns `valid=False, reason="invalid_atoms"` and that `llm_node` yields nothing (strip). This proves the audio Part does not widen what Gemini can claim. Mirror `tests/agent/test_dj_cohost_grounding.py` construction.

### 4. GROUND-02 — VERIFIED already satisfied

[VERIFIED: src/vibemix/agent/config.py, src/vibemix/llm/_router_config.py, suite green]

- `agent/config.py:25`: `LLM_MODEL: str = resolve("live_coach")[0]` — the reaction model resolves through `model_router` at import time. No hardcoded literal in `dj_cohost.py`; the call passes `model=LLM_MODEL` (`dj_cohost.py:1693`).
- `_router_config.py:27`: `"live_coach": ("gemini-3.5-flash", ServiceTier.STANDARD)`. **`gemini-3.5-flash` is NOT matched by the CI grep-gate pattern** (verified: the pattern bans `gemini-3-flash` literally, which does not match `gemini-3.5-flash`) — so even the config table entry is "clean", but it lives in the single allowlisted file regardless.
- **The bench-swap alias is `live_coach`.** Phase-81 swaps the winning model by editing the `live_coach` tuple in `_router_config.py` (a one-line edit, no code change) — exactly the "SKU bump is a one-file edit" contract documented in `agent/config.py:12-17`.
- GROUND-02 work reduces to: (a) a test asserting the reaction model resolves via `model_router.resolve("live_coach")` (not a literal); (b) document `live_coach` as the bench alias. The CI grep-gate (`tests/repo/test_model_literal_gate.py`, 22 passing) already enforces no-literal.

## Architecture Patterns

### System Architecture Diagram (reaction turn, with secondary-ear framing)

```
 master output (BlackHole/WASAPI)            MIDI / screen / nowplaying
        |                                            |
        v                                            v
  capture backend (48k->16k)                  DSP detectors + EventDetector
        |                                            |  (invariant #1: single writer)
        v                                            v
  clean_audio_buf (ring, lock)            MusicState + EvidenceRegistry (observations)
        |   \                                        |
        |    \ (off-loop, run_in_executor)           | snapshot() per turn
        |     v                                      v
        |   Grounding.on_event  -> [track:<id>]   AICoach.build_prompt -> grounded text packet
        |     latch                  injected           (deltas, confidence, trajectory, genre, recall)
        |        \____________________   __________/
        v                             \ /
  snapshot_wav(audio_seconds)          v
        |                    contents = [ text_packet + parts_clause + history,
        |------------------>             Part1 = master audio (audio/wav)  <-- SECONDARY EAR
                                         (P2 mic, P3 lookahead, optional) ]
                                              |
                                              v
                  genai.aio.models.generate_content_stream(model=LLM_MODEL=resolve("live_coach"))
                            (or OpenRouter stream_or with same contents)
                                              |
                                              v  full_text (streamed)
                          +----------------------------------------+
                          | silence/slop gate -> CitationLinter.check(full_text, registry_snapshot)
                          |   registry-backed, PROMPT/AUDIO-BLIND   |
                          +----------------------------------------+
                                   |                       |
                              valid -> emit           invalid -> strip to <silence/>
                                                       (audio-derived un-cited claim dies here:
                                                        trust-the-audio invariant #3 wins)
```

The audio Part influences only the `full_text`; the gate downstream validates that text against the DSP registry. The audio is a *grounding bonus*, structurally incapable of fabricating an event.

### Pattern 1: Gated additive framing (cold-path byte-identity)
**What:** Add a default-OFF env flag that toggles ONLY the secondary-ear *framing* of the existing Part-1 audio (and any new prompt language). Flag OFF → the `contents` list + prompt are byte-identical to v8.0.
**When to use:** Every GROUND-01 change. This is the milestone-wide additive-gated invariant.
**Example (mirror the existing flag-read convention):**
```python
# Source: src/vibemix/__main__.py:619, 892, 918, 1035 (established VIBEMIX_* flag pattern)
ground_secondary_ear = os.environ.get("VIBEMIX_GROUND_SECONDARY_EAR", "0").strip().lower() in ("1", "true", "yes", "on")
# pass as a kwarg to DJCoHostAgent (default False) — gates only the framing, never the Part attach
```
Note: because Part 1 (master audio) is *already* attached unconditionally, the flag should NOT gate the Part attach itself (that would change v8.0 behavior). It gates the **secondary-ear prompt framing** and the grounding-signal label. Confirm byte-identity by asserting the v8.0 `parts_clause` / `contents[0]` string when the flag is OFF.

### Pattern 2: Part-aware prompt suffix via the locked builder
**What:** Prompt framing for attached Parts is centralized in `build_parts_description(audio_seconds, has_mic_part, has_lookahead_part)` (`prompts/matrix.py:599`). It already labels Part 1 `"live BlackHole audio (audience perspective)"` and carries the anti-slop refrain `"Your ears are the referee — the evidence above is grounded context."`
**When to use:** The secondary-ear framing belongs HERE (extend the builder, gated), not inline in `llm_node`. Keeps the 4-way Part-labeling dispatch in one tested place (`tests/prompts/test_matrix_3part_labeling.py`).
**Key insight:** The existing refrain *already encodes the secondary-ear thesis* ("ears are the referee, evidence is grounded context"). GROUND-01 framing extends this, it does not invent it.

### Pattern 3: Off-loop consult → latch → inject (the Phase-77 / Phase-65 seam)
**What:** Track-aware events pre-dispatch an expensive consult OFF the event loop (`run_in_executor` + `asyncio.wait_for(deadline)`), latch the result, and `llm_node` pulls the cheap latch and injects a citation. Cancel+replace prior in-flight; clear on timeout/turn-end.
**When to use:** If GROUND-01 needs any *new* audio-derived consult (it does NOT, per the decision to reuse Part 1). Documented here because it is the canonical pattern any future audio-secondary enrichment must mirror — see `_maybe_dispatch_grounding` (`dj_cohost.py:949-1047`) and 77-04-SUMMARY.
**Caution:** Do NOT inline-await any embed/consult in `llm_node` — it regresses TTFT (the entire reason the pre-dispatch+latch+pull pattern exists).

### Anti-Patterns to Avoid
- **Gating the Part-1 attach behind the flag.** Part 1 is attached in v8.0; gating it changes cold-path behavior and breaks byte-identity. Gate the *framing*, not the attach.
- **Adding a second audio capture / ws port / IPC envelope.** Explicitly OUT (CONTEXT + milestone acid test). Reuse `_clean_audio_buf` + `snapshot_wav`.
- **Inlining a model literal on the reaction path.** The CI grep-gate fails the PR. Always `resolve("live_coach")`.
- **Trusting the audio Part as primary perception.** Gemini is the voice; the DSP registry is the truth. Any claim must cite a registry observation.
- **Treating the RealtimeModel/native-audio Live API as the GROUND-01 mechanism.** It is a deferred, separate seam (CONTEXT Deferred Ideas). The live reaction is the direct `generate_content_stream` Part path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio → Gemini Part encoding | A new resample/WAV encoder | `snapshot_wav(self._clean_audio_buf, seconds)` (`audio/features.py:93`) | Already peak-normalizes + emits `audio/wav` RIFF bytes; reused by the live Part + the off-loop grounding embed. |
| Hallucination guard | A prompt-side "only say what's real" instruction or an audio-content check | `CitationLinter.check` against `EvidenceRegistry.snapshot()` | Registry-backed binary gate is the load-bearing invariant #2; prompt instructions are advisory and bypassable. |
| Part-attach prompt labeling | Inline f-strings in `llm_node` | `build_parts_description(...)` (`prompts/matrix.py:599`) | The locked 4-way dispatch is unit-pinned; the secondary-ear refrain already lives there. |
| Model selection | A literal `"gemini-..."` anywhere on the path | `model_router.resolve("live_coach")` | CI grep-gated; the bench-swap alias is the single config edit point. |
| Feature flag plumbing | A new config system | `os.environ.get("VIBEMIX_...", "0")` read in `__main__.py`, passed as a default-False kwarg | Matches the 6 existing `VIBEMIX_*` flags; cold path stays byte-identical. |

**Key insight:** Nearly every primitive GROUND-01 needs already exists and is tested. The phase is *framing + a guard test + a gated flag* over existing machinery, not new construction.

## Common Pitfalls

### Pitfall 1: Believing the audio feed must be built from scratch
**What goes wrong:** Planning a new audio capture / Part-attach as if the reaction path has no audio.
**Why it happens:** The CONTEXT phrasing ("let Gemini *also* hear the audio") reads as net-new; the milestone framing emphasizes "Gemini is the voice not the ear."
**How to avoid:** Recognize Part 1 (`audio_wav`) is already attached every turn. Scope GROUND-01 to framing + guard + gate. Verify by reading `dj_cohost.py:1400, 1511-1514`.
**Warning signs:** A task that adds `types.Part.from_bytes(audio_wav, ...)` as if new, or a new buffer.

### Pitfall 2: Gating the Part attach (breaking cold-path byte-identity)
**What goes wrong:** Flag OFF removes Part 1 → v8.0 behavior changes → the byte-identity test fails and the live co-host loses its audio.
**Why it happens:** Conflating "the secondary-ear *framing*" with "the audio Part itself."
**How to avoid:** The flag toggles prompt framing / labeling ONLY. Part 1 stays attached unconditionally on both flag states. Pin a flag-OFF `contents`-shape byte-identity test.
**Warning signs:** Any `if flag: contents.append(audio_part)`.

### Pitfall 3: Linter bypass via prompt or audio
**What goes wrong:** Assuming the audio Part lets Gemini "see more" and therefore say more without citations.
**Why it happens:** Intuition that richer input = looser gate.
**How to avoid:** The linter reads `(full_text, registry_snapshot)` only. Pin the un-backed-claim-strips test. Audio enriches phrasing, never the citable set.
**Warning signs:** A test that asserts an un-cited audio-derived claim is emitted.

### Pitfall 4: TTFT regression
**What goes wrong:** Adding an inline audio analysis / consult in `llm_node` before the stream.
**Why it happens:** Wanting the audio to "inform" the prompt synchronously.
**How to avoid:** Reuse the off-loop pre-dispatch+latch pattern if any new consult is ever needed (it is not for GROUND-01). The Part-1 snapshot is already a cheap synchronous read.
**Warning signs:** `await some_embed(...)` between `set_next_event` and the stream call.

### Pitfall 5: Model-literal regression
**What goes wrong:** Hardcoding `"gemini-..."` while wiring the bench alias.
**Why it happens:** Convenience during the bench-swap plumbing.
**How to avoid:** Always `resolve("live_coach")`. The grep-gate (`tests/repo/test_model_literal_gate.py`) catches it; run it before commit.
**Warning signs:** Gate test red; `_MODEL_LITERAL_RE` match outside `_router_config.py`.

## Runtime State Inventory

Not a rename/refactor/migration phase — this is additive feature wiring. Section omitted per the greenfield/additive rule. (No stored data, OS-registered state, or build artifacts carry phase-specific identifiers that would drift.)

## Code Examples

### The reaction call (the GROUND-01 / GROUND-02 chokepoint)
```python
# Source: src/vibemix/agent/dj_cohost.py:1511-1514, 1692-1696
contents: list = [
    text_prompt + parts_clause + history_clause,                    # grounded DSP text packet (PRIMARY)
    types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),    # Part 1: master audio (SECONDARY EAR)
]
# ... optional P2 mic, P3 lookahead, screen ...
stream = await self._genai_client.aio.models.generate_content_stream(
    model=LLM_MODEL,        # = resolve("live_coach")[0] — GROUND-02 config-resolved
    contents=contents,
    config=gen_cfg,
)
```

### The hallucination gate (the GROUND-01 guard)
```python
# Source: src/vibemix/agent/dj_cohost.py:1973-1976  +  coach/citation_linter.py:94
if self._linter_wired and self._linter is not None:
    lint_result = self._linter.check(full_text, snapshot, mode="live")
    # lint_result.valid is False if ANY citation atom misses the registry snapshot
    # -> whole turn strips to <silence/> (dj_cohost.py:2055). Audio Part cannot widen this.
```

### Flag read (mirror for the new gate)
```python
# Source: src/vibemix/__main__.py:1035 (VIBEMIX_RECALL_ENABLED pattern)
recall_enabled = os.environ.get("VIBEMIX_RECALL_ENABLED", "0").strip().lower() not in ("0", "false", "no", "off", "")
# GROUND-01 mirror: VIBEMIX_GROUND_SECONDARY_EAR, default OFF, passed as DJCoHostAgent kwarg (default False)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ask Gemini to perceive genre/structure raw | Ground perception in DSP/embeddings; Gemini interprets | v8.1 charter (2026-05-25) | The 3-model genre disagreement (raw-audio bench floor) proved Gemini's raw ear unreliable → audio is *secondary*, DSP is *primary*. |
| Audio as the only signal (early POC cascade) | Audio Part + structured evidence packet + citation gate | Phases 10/18/20 → 77/78/79 | The structured evidence (deltas/confidence/trajectory/genre) is the intelligence; audio corroborates. P81 bench's "no-audio" cell tests exactly this. |

**Deprecated/outdated:**
- The retired-POC `cohost_v4.py` "swap pattern" for Part assembly — `build_parts_description` deliberately diverges (`prompts/matrix.py:650` docstring). Do not port the v4 swap.
- Treating `INVOKE_AUDIO_SECONDS` as 18s — it is **60.0** today (`audio/constants.py:20`, Kaan-tuned 2026-05-21). Diet path is 6s.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The intended GROUND-01 deliverable is *framing + guard test + gated flag* over the existing Part-1 audio, not a new audio capability. | Summary / Pitfall 1 | If Kaan actually wants a *distinct* second audio stream (e.g. a different window or a separate "grounding-only" Part alongside the existing audience-perspective Part), the plan needs an additional Part. The CONTEXT decision ("reuse the existing clean audio buffer... do NOT add a new capture path") strongly supports A1, but the *exact* framing (relabel Part 1 vs add a framed duplicate) is Claude's-discretion — planner decides smallest additive diff. LOW risk; resolved by the discretion clause. |
| A2 | `VIBEMIX_GROUND_SECONDARY_EAR` is an acceptable flag name. | Pattern 1 | Cosmetic — flag name is explicitly Claude's discretion. None. |
| A3 | The OpenRouter brain path (`or_client`) must receive the same framing since it shares `contents`. | Critical Findings #1 | If the framing were applied path-specifically, the OR path would diverge. Verified `contents` is shared (`dj_cohost.py:1688`), so applying framing to `contents[0]`/`parts_clause` covers both. LOW. |

## Open Questions

1. **Relabel Part 1 vs explicit secondary-ear framing string** — *What we know:* Part 1 is labeled "audience perspective" today and the refrain already says "ears are the referee, evidence is grounded context." *What's unclear:* whether GROUND-01 wants new prompt language naming the audio as a *secondary grounding signal* explicitly, or whether the existing framing already satisfies the requirement and the phase reduces to the flag + guard test. *Recommendation:* Add a gated framing extension to `build_parts_description` (a short "this audio is a secondary grounding signal; the structured evidence above is authoritative — never claim an event it doesn't list" clause) so the requirement is *visibly* satisfied and bench-measurable, while keeping flag-OFF byte-identical. Low-stakes; planner's call.

2. **Does the bench (P81) need a *second* `live_coach` alias** (e.g. `live_coach_bench`) to swap models without touching the live default? — *What we know:* `live_coach` is the live alias; editing it swaps the live model too. *What's unclear:* whether P81 wants an isolated alias. *Recommendation:* Defer to P81 BENCH; GROUND-02 only needs `live_coach` resolvable via the router (it is). If P81 wants isolation, it adds an alias to `_router_config.py` then — out of scope here.

## Environment Availability

Skipped — no external tool/service/runtime dependencies beyond the already-installed `google-genai` + `numpy`/`scipy`. The unit tests run with NO API key (verified: the sampled agent suite passed offline). Live e2e (real Gemini key) is a KAAN-ACTION/Phase-81 concern, never faked.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (markers in `[tool.pytest.ini_options]`, `pyproject.toml`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_grounding.py tests/repo/test_model_literal_gate.py -q` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GROUND-01 | Flag OFF → reaction `contents` request shape byte-identical to v8.0 (cold path) | unit (fake genai client, assert `contents` list shape + `contents[0]` string) | `pytest tests/agent/test_dj_cohost_ground_secondary.py -k flag_off_byte_identical -x` | ❌ Wave 0 |
| GROUND-01 | Flag ON → audio Part attached + secondary-ear framing present | unit (fake client, assert Part 1 `mime_type="audio/wav"` + framing substring in `contents[0]`) | `pytest tests/agent/test_dj_cohost_ground_secondary.py -k flag_on_audio_framed -x` | ❌ Wave 0 |
| GROUND-01 | Audio-derived claim citing an un-registered event strips the whole turn | unit (fake stream returns `[ev:PHANTOM@t]` not in registry; assert linter `valid=False` + no chunks yielded) | `pytest tests/agent/test_dj_cohost_ground_secondary.py -k unbacked_audio_claim_strips -x` | ❌ Wave 0 |
| GROUND-02 | Reaction model resolves via `model_router.resolve("live_coach")`, no literal on the path | unit + repo-gate | `pytest tests/repo/test_model_literal_gate.py tests/agent/test_dj_cohost_ground_secondary.py -k model_via_router -x` | partial (gate exists; resolve-assert ❌ Wave 0) |

### Sampling Rate
- **Per task commit:** quick run command above (the new test file + the model gate).
- **Per wave merge:** full suite (`pytest -q`) — baseline is GREEN offline (sampled: 22 passed; full v8.0 baseline 4451 passed per 77-04-SUMMARY).
- **Phase gate:** full suite green + flag-OFF byte-identity proven before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/agent/test_dj_cohost_ground_secondary.py` — covers GROUND-01 (flag-off byte-identity, flag-on framing, un-backed-claim-strips) + GROUND-02 (resolve-via-router). Build on the construction helpers in `tests/agent/test_dj_cohost_mic_part.py` (`_build_agent`, `_async_iter`, `_FakeRecorder`) — the exact fake-client + Agent.__init__-patch pattern.
- [ ] No framework install needed; no new conftest fixtures required (reuse `tests/audio/conftest.py::int16_sine` + `tests/agent/test_dj_cohost_mic_part.py` helpers).

## Security Domain

`security_enforcement` is ABSENT in `.planning/config.json` → treated as enabled. Threat surface for this phase is narrow and additive.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface added; Gemini key handling unchanged. |
| V3 Session Management | no | No session/token change. |
| V4 Access Control | no | No new access path. |
| V5 Input Validation | yes | The audio Part is local master-output bytes (not user-supplied network input); the citation atoms Gemini emits are validated by `CitationLinter` (existing). No new untrusted input. |
| V6 Cryptography | no | No crypto; never hand-roll. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Audio Part lets Gemini fabricate an un-grounded claim | Tampering (trust the AI's perception over the DSP truth) | `CitationLinter` registry-backed gate — structurally prompt/audio-blind; un-backed claim strips. Pinned by the GROUND-01 guard test. |
| Model-literal regression leaks a non-router model onto the live path | Tampering / config drift | CI grep-gate `test_model_literal_gate.py` + `model_router.resolve("live_coach")`. |
| Secret leakage via error logs on the audio/LLM path | Information disclosure | Existing `_emit_connection_error` uses `str(err)[:300]` + coarse key-free classification (`dj_cohost.py:766-838`) — no new log surface added by this phase. |

## Sources

### Primary (HIGH confidence — read this session)
- `src/vibemix/agent/dj_cohost.py` — reaction path, `llm_node`, `contents`/Part assembly (1511-1552), `generate_content_stream` call (1692-1696), linter chokepoint (1973-1976), strip-to-silence (2055), grounding off-loop seam (949-1047).
- `src/vibemix/agent/config.py` — `LLM_MODEL = resolve("live_coach")[0]` (line 25).
- `src/vibemix/llm/model_router.py` + `src/vibemix/llm/_router_config.py` — router + the `live_coach` alias (line 27).
- `src/vibemix/coach/citation_linter.py` — registry-backed, prompt/audio-blind binary gate (94-213).
- `src/vibemix/state/evidence_registry.py` — observation store, snapshot, `register_library` (single source of citable truth).
- `src/vibemix/audio/constants.py` — `INVOKE_AUDIO_SECONDS=60.0`, `DIET_AUDIO_SECONDS`, mic-part constants.
- `src/vibemix/prompts/matrix.py:599` — `build_parts_description` (Part-labeling + secondary-ear refrain).
- `tests/agent/test_dj_cohost_mic_part.py`, `tests/agent/test_dj_cohost_grounding.py`, `tests/repo/test_model_literal_gate.py` — the construction + assert patterns to mirror.
- `scripts/release/check_no_hardcoded_model.sh` — CI grep-gate (verified `gemini-3.5-flash` is not banned).
- `.planning/phases/77-wire-connect-the-islands/77-04-SUMMARY.md` — the off-loop consult→inject seam GROUND-01 mirrors.

### Secondary (MEDIUM)
- `.planning/research/one-mind-charter.md`, `.planning/research/gemini-audio-truth-test.md`, `.planning/REQUIREMENTS.md` — milestone intent + raw-ear floor data.

### Tertiary (LOW)
- None — all claims verified against live source this session.

## Metadata

**Confidence breakdown:**
- Reaction-path mechanism (the critical unknown): **HIGH** — read the exact `generate_content_stream` call + `contents` Part assembly; it is the direct genai path, not RealtimeModel.
- Audio buffer reuse: **HIGH** — `_clean_audio_buf` + `snapshot_wav` already feed Part 1; confirmed in code.
- Hallucination guard non-bypass: **HIGH** — linter inputs are `(text, registry_snapshot)`; structurally prompt/audio-blind.
- GROUND-02 already satisfied: **HIGH** — `LLM_MODEL = resolve("live_coach")[0]`; grep-gate green (22 tests pass).
- Exact framing scope (relabel vs new clause): **MEDIUM** — Claude's-discretion per CONTEXT; A1/Open-Q1 flag it.

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (stable internal codebase; re-verify `dj_cohost.py` line numbers if the file is refactored before planning).
