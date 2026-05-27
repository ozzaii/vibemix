# Phase 80: GROUND — Gemini as Secondary Ear - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 3 (2 modified, 1 created)
**Analogs found:** 3 / 3

## Scope reminder (read before planning)

Per RESEARCH (HIGH confidence, line numbers re-verified this session): the audio is **already** Part 1 of every reaction turn (`dj_cohost.py:1511-1514`), the model **already** resolves via `model_router.resolve("live_coach")` (`agent/config.py:25`), and the linter is **already** prompt/audio-blind (`dj_cohost.py:1973-1976`). This phase is NOT new construction — it is:
- **GROUND-01:** a gated secondary-ear *framing* clause in `build_parts_description` (flag default OFF → byte-identical) + a guard test proving an un-backed audio-derived claim strips to `<silence/>`.
- **GROUND-02:** a confirming test that the reaction model resolves via the router (no literal) + document `live_coach` as the bench-swap alias.
- **Wave-0 test file:** `tests/agent/test_dj_cohost_ground_secondary.py`.

The dominant pattern is **gated-additive (cold-path byte-identity)**, mirrored from Phase 77's grounding seam.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/prompts/matrix.py` (MODIFY — extend `build_parts_description`) | prompt-builder (pure fn) | transform | itself — the existing 4-way Part-label dispatch (`matrix.py:599-678`) | exact (extend in place) |
| `src/vibemix/agent/dj_cohost.py` (MODIFY — thread gated flag into the `build_parts_description` call) + `src/vibemix/agent/__init__.py` / `__main__.py` (flag read + kwarg) | agent / orchestrator wiring | request-response (reaction turn) | the existing `parts_clause` call site (`dj_cohost.py:1505-1514`) + Phase-77 grounding kwarg seam | exact |
| `tests/agent/test_dj_cohost_ground_secondary.py` (CREATE) | test | request-response (fake-stream assert) | `tests/agent/test_dj_cohost_mic_part.py` + `tests/agent/test_dj_cohost_grounding.py` + `tests/repo/test_model_literal_gate.py` | exact (build on `_build_agent`/`_async_iter`/`_FakeRecorder`) |

## Pattern Assignments

### `src/vibemix/prompts/matrix.py` — extend `build_parts_description` (prompt-builder, transform)

**Analog:** itself — the locked 4-way dispatch at `matrix.py:599-678`. This is a pure function with no side effects/globals; the secondary-ear framing belongs HERE (gated), not inline in `llm_node`, so the 4-way dispatch stays in one unit-pinned place (`tests/prompts/test_matrix_3part_labeling.py`).

**Signature pattern** (`matrix.py:599-603`):
```python
def build_parts_description(
    audio_seconds: float,
    has_mic_part: bool,
    has_lookahead_part: bool,
) -> str:
```
GROUND-01 adds one default-False kwarg (planner's discretion on name, e.g. `secondary_ear: bool = False`). Default-False keeps every existing call site + the 4 pinned strings byte-identical.

**Existing refrain already encodes the thesis** (`matrix.py:638-641`) — extend, don't reinvent:
```python
refrain = (
    "Your ears are the referee — "
    "the evidence above is grounded context."
)
```

**Baseline 1-Part string** (`matrix.py:644-649`) — the byte-identity target when the flag is OFF:
```python
if not has_mic_part and not has_lookahead_part:
    return (
        f"\n\nAttached: P1 = last {secs}s of live BlackHole audio "
        f"(audience perspective). {refrain}"
    )
```

**Framing extension pattern (gated):** when `secondary_ear` is True, append a short clause stating the audio is a *secondary grounding signal*, the structured evidence is authoritative, and never claim an event it doesn't list. Apply consistently across all 4 branches (or append to the common tail) so the flag's effect is uniform. Mirror the existing anti-prediction guard phrasing style (`matrix.py:665-667`: `"do NOT describe Part 2 as if it has played. Use it only to ground what you HEAR..."`). When the flag is OFF, every return value must equal the current strings exactly.

---

### `src/vibemix/agent/dj_cohost.py` — thread the gated flag (agent wiring, request-response)

**Analog:** the existing `parts_clause` build at `dj_cohost.py:1505-1514` + the Phase-77 grounding kwarg seam.

**Call site to extend** (`dj_cohost.py:1505-1509`) — pass the new flag through, do NOT touch the `contents` assembly:
```python
parts_clause = build_parts_description(
    audio_seconds=float(audio_seconds),
    has_mic_part=mic_attached,
    has_lookahead_part=lookahead_attached,
)
```

**DO NOT TOUCH — the Part attach (`dj_cohost.py:1511-1514`).** Part 1 is unconditional in v8.0; gating it breaks byte-identity (Pitfall 2). The flag gates only `parts_clause` framing:
```python
contents: list = [
    text_prompt + parts_clause + history_clause,
    types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"),  # Part 1 — UNCONDITIONAL, do not gate
]
```

**Shared-`contents` invariant (applies to both brain paths).** The OpenRouter path (`dj_cohost.py:1685-1690`) and the genai path (`dj_cohost.py:1692-1696`) consume the SAME `contents` list. Applying framing to `parts_clause`/`contents[0]` covers both — never branch path-specifically (Assumption A3).

**Flag plumbing pattern** — read in `__main__.py`, pass as a default-False kwarg to `DJCoHostAgent`. Mirror the established `VIBEMIX_*` flag convention:
```python
# Source: src/vibemix/__main__.py:1035 (VIBEMIX_RECALL_ENABLED pattern)
recall_enabled = os.environ.get("VIBEMIX_RECALL_ENABLED", "0").strip().lower() not in ("0", "false", "no", "off", "")
# GROUND-01 mirror: VIBEMIX_GROUND_SECONDARY_EAR, default OFF, DJCoHostAgent kwarg (default False)
```

---

### `tests/agent/test_dj_cohost_ground_secondary.py` — CREATE (test, request-response)

**Primary analog:** `tests/agent/test_dj_cohost_mic_part.py` — the fake-genai-stream + `Agent.__init__`-patch template. Reuse its helpers verbatim. **Secondary analogs:** `tests/agent/test_dj_cohost_grounding.py` (registry/citation-gate construction) + `tests/repo/test_model_literal_gate.py` (the resolve-via-router assert pattern).

**Helpers to copy** (`test_dj_cohost_mic_part.py:38-99`) — `_async_iter`, `_FakeRecorder`, `_build_state`, `_build_agent`, `_drive_llm_node`:
```python
def _async_iter(chunks):
    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()
    return gen()

def _build_agent(mocker, tmp_path, mic_audio_buf):
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=mocker.MagicMock(),
        state=state, recorder=recorder,
        llm_inst=mocker.MagicMock(), tts_inst=mocker.MagicMock(),
        mic_audio_buf=mic_audio_buf,
    )
    return agent, genai_client, recorder, state
```

**Test 1 — flag-OFF byte-identity** (`-k flag_off_byte_identical`). Mirror the 2-Part baseline assert at `test_dj_cohost_mic_part.py:111-131`:
```python
mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"RIFFFAKEWAVMIX")
mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
gen_client.aio.models.generate_content_stream = mocker.AsyncMock(return_value=_async_iter(["ok"]))
agent.set_next_event(Event(type="HEARTBEAT", state=state, extra={}))
_drive_llm_node(agent)
contents = gen_client.aio.models.generate_content_stream.call_args.kwargs["contents"]
assert len(contents) == 2
assert isinstance(contents[1], types.Part)
# byte-identity: with flag OFF, contents[0] must NOT contain the secondary-ear framing substring,
# and SHOULD still contain the v8.0 "(audience perspective)" + refrain.
```

**Test 2 — flag-ON audio framed** (`-k flag_on_audio_framed`). Same construction, flag ON, assert: Part 1 still present (`contents[1].inline_data.mime_type == "audio/wav"`, data starts `b"RIFF"` — mirror `test_dj_cohost_mic_part.py:269-275`) AND the secondary-ear framing substring is present in `contents[0]`.

**Test 3 — un-backed audio claim strips** (`-k unbacked_audio_claim_strips`). THE core guard. Fake the stream to return a reply with a citation atom for an event NOT in the registry snapshot (e.g. `[ev:PHANTOM_DROP@45.2]`), wire the linter, assert `llm_node` yields nothing (strip to `<silence/>`). Use the registry/`has()` construction from `test_dj_cohost_grounding.py:238-248`:
```python
reg = EvidenceRegistry()
# seed only real observations; PHANTOM_DROP is NOT seeded
assert reg.has("ev", "PHANTOM_DROP", 45.2) is False  # the atom will miss → whole turn strips
```
Linter chokepoint reference (`dj_cohost.py:1973-1976`): `self._linter.check(full_text, snapshot, mode="live")` → `lint_result.valid is False` → no yield. The audio Part is attached (Part 1) but cannot widen the citable set — that is the property under test.

**Test 4 — model resolves via router** (`-k model_via_router`). Assert no literal on the path; mirror `test_model_literal_gate.py` intent + assert resolution:
```python
from vibemix.llm.model_router import resolve
from vibemix.agent.config import LLM_MODEL
assert LLM_MODEL == resolve("live_coach")[0]  # config.py:25 — no hardcoded literal on the reaction path
```

**conftest fixtures to reuse:** `tests/audio/conftest.py::int16_sine` + `INPUT_SR_TARGET` (no new fixtures needed).

## Shared Patterns

### Gated additive — cold-path byte-identity
**Source:** Phase-77 grounding seam — `tests/agent/test_dj_cohost_grounding.py:195-214` (`test_cold_path_no_grounding_is_byte_identical`) + the `VIBEMIX_RECALL_ENABLED` flag read (`__main__.py:1035`).
**Apply to:** the `build_parts_description` extension + the `DJCoHostAgent` kwarg.
**Contract:** flag OFF → `parts_clause`/`contents` byte-identical to v8.0. New behavior rides a default-False kwarg; the cold path adds nothing.
```python
mocker.patch.object(Agent, "__init__", return_value=None)
agent = DJCoHostAgent(**_kwargs(mocker, tmp_path))
# ... cold path attempts no new work; default-False gate is a no-op seam
assert getattr(agent, "_grounding", None) is None
```

### Citation-grounding gate (the hallucination guard) — registry-backed, prompt/audio-blind
**Source:** `dj_cohost.py:1973-1976` (chokepoint) + `coach/citation_linter.py` (`check(text, registry_snapshot, mode)`) + `state/evidence_registry.py` (`has()` / `register_library`).
**Apply to:** GROUND-01 guard test (Test 3).
**Property:** the linter's only inputs are `(full_text, registry_snapshot)`. It never reads the prompt or the audio Parts. An audio-derived claim about an undetected event has no registry entry to cite → atom misses → `valid=False` → whole turn strips. Trust-the-audio (invariant #3) wins by construction.
```python
if self._linter_wired and self._linter is not None:
    lint_result = self._linter.check(full_text, snapshot, mode="live")
    # valid False if ANY citation atom misses the registry snapshot → strip to <silence/>
```

### Config-resolved model (no literals) — bench-swap alias
**Source:** `agent/config.py:25` (`LLM_MODEL: str = resolve("live_coach")[0]`), consumed at `dj_cohost.py:1693` (`model=LLM_MODEL`); allowlist table `llm/_router_config.py:27` (`"live_coach": ("gemini-3.5-flash", ServiceTier.STANDARD)`); CI grep-gate `tests/repo/test_model_literal_gate.py`.
**Apply to:** GROUND-02 confirming test + documenting `live_coach` as the Phase-81 bench-swap alias (a one-line `_router_config.py` edit, no code change).
```python
# agent/config.py:25 — the single resolution point; the reaction call passes model=LLM_MODEL
LLM_MODEL: str = resolve("live_coach")[0]
```
Note: `gemini-3.5-flash` is NOT matched by the grep-gate's `gemini-3-flash` ban pattern, and it lives in the single allowlisted file regardless — gate stays green.

## No Analog Found

None. Every file has a strong in-repo analog; this phase is framing + tests over existing, tested machinery.

## Metadata

**Analog search scope:** `src/vibemix/agent/`, `src/vibemix/prompts/`, `src/vibemix/llm/`, `src/vibemix/coach/`, `src/vibemix/state/`, `tests/agent/`, `tests/repo/`
**Files scanned (read this session):** `dj_cohost.py` (4 ranges), `prompts/matrix.py`, `agent/config.py`, `llm/_router_config.py`, `tests/agent/test_dj_cohost_mic_part.py`, `tests/agent/test_dj_cohost_grounding.py`, `tests/repo/test_model_literal_gate.py`
**Line numbers:** all verified against live source 2026-05-26 (match RESEARCH exactly: `1505-1514`, `1692-1696`, `1973-1976`; `config.py:25`; `matrix.py:599-678`; `_router_config.py:27`).
**Pattern extraction date:** 2026-05-26
