# Phase 61: Actionable-Not-Hype Coach Persona - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 5 modified + 4 test files (extend, not create)
**Analogs found:** 9 / 9 (all in-repo; this is a sharpen-and-fence phase)

> **Frozen-vs-updatable legend (load-bearing for this phase):**
> - **FROZEN** = byte-pinned hype goldens. NEVER touch to "make a test pass" (Pitfall 2). A trip = real regression → investigate the diff.
> - **UPDATABLE** = coach anchors/cells. Editing these IS the phase scope, but each anchor-pin change is a *deliberate, noted* decision made in lockstep (cell edit + test pin edit + comment citing Phase 61).

## File Classification

| Modified/New File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/prompts/matrix.py` (COACH_BEGINNER) | prompt-constant | transform (state→system-instruction) | `COACH_PRO` (same file, the strong cell) | exact (same role, same cell family) |
| `src/vibemix/prompts/matrix.py` (COACH_INTERMEDIATE) | prompt-constant | transform | `COACH_PRO` (same file) | exact |
| `src/vibemix/prompts/matrix.py` (COACH_PRO) | prompt-constant | transform | self (verb-anchor add only) | n/a — it is the target shape |
| `src/vibemix/state/coach.py` (`task_for_event` MIX_MOVE verb-align, AUDIT only) | service | event-driven | KEY_CLASH/TRANSITION arms (same file, Phase 60) | exact |
| `tests/prompts/test_matrix.py` (coach anchor + verb/prescribe/balance asserts) | test | request-response | the HYPE per-cell anchor + substrate tests (same file) | exact |
| `tests/state/test_coach.py` (NEW KEY_CLASH/TRANSITION voice assert) | test | event-driven | `test_task_mix_move_LOAD_BEARING_anti_slop_clause` (same file) | role-match |
| `tests/agent/test_dj_cohost_matrix_dispatch.py` (NEW dual-path assert) | test | request-response | `test_dispatch_06_gen_cfg_system_instruction_matches_dispatch` | role-match |
| `tests/agent/test_coach_prompt_grounding.py` (extend: anti-slop/cited) | test | event-driven | self (existing grounding scaffold pins) | exact |

## Pattern Assignments

### `src/vibemix/prompts/matrix.py` — COACH_BEGINNER (the headline COACH-01 work)

**Cell location:** `matrix.py:426-455` (constant `COACH_BEGINNER`).
**Analog / target shape:** `COACH_PRO` (`matrix.py:502-543`) — the strong cell that already carries the observed→impact→prescribe spine and the over-correction guard.

**The target pattern to copy from COACH_PRO** (`matrix.py:505-510`) — observed→impact→prescribe in one line + the balance arms:
```
• DESERVED CRITIQUE + FIX: ... name it AND say the fix in the SAME line.
  "kicks are colliding — pull deck B's low EQ" ... NEVER end on a bare
  weakness ("feels thin" ...) — that names a problem and walks away ...
  "thin lead — push 3-5k", "dry mids — touch of plate reverb"
• NUDGE FORWARD: ... "this is begging for a darker roller", "good spot to
  bring the sub back".
• PROPS: when a move genuinely lands, call it and why — briefly, specific.
```

**What COACH_BEGINNER already has (keep — `matrix.py:437-439`):**
```
ONE THING PER TURN — don't dogpile. Pick the most actionable nudge. If
everything sounded clean, just say so briefly — don't invent a problem.
ENCOURAGING TONE — when something works, say it works. ...
```
(The ENCOURAGING TONE clause at `:439` IS the beginner balance rule — already present, keep it.)

**Gaps to sharpen (this cell needs the most):**
1. **No impact clause.** Anchors at `:428-436` jump observed→prescribe ("the cut felt early — try 8 bars later") or are bare ("more space", "rushing the blend"). Reframe to the full observed→impact→prescribe shape — the existing `"low boost muddied the breakdown"` (`:429`) is the in-cell model; extend the others to match.
2. **No DJ-verb vocabulary anchor.** Surface the canonical verb set (kill, swap, cut, filter, wait, tighten, ride, pull, push) — the same verbs the KEY_CLASH arm emits (`coach.py:284`).
3. **No deck/harmonic path.** Beginner cell never mentions decks/keys; add a gentle grounded-only framing ("those two tracks were fighting a bit — try cutting one in cleaner").

**ANCHOR_PHRASES to update in lockstep** (these are **UPDATABLE**, deliberate-noted): `tests/prompts/test_matrix.py:69-78` `ANCHOR_PHRASES[("beginner","coach")]` — the 8 anchors are byte-asserted by `test_prompt_01_each_cell_has_eight_anchor_phrases` (`:277-283`). Any cell-anchor edit MUST update this list in the same commit with a Phase-61 comment.

---

### `src/vibemix/prompts/matrix.py` — COACH_INTERMEDIATE (mostly there, add balance rule)

**Cell location:** `matrix.py:463-493`.
**Analog:** `COACH_PRO` (`:502-543`) for the missing balance arm; `COACH_BEGINNER`'s `ENCOURAGING TONE` (`:439`) is the smaller-scale balance model.

**Already actionable (keep — `matrix.py:474-476`):**
```
CONCRETE FEEDBACK — when something didn't work, name what + when. "Kicks
stepped on each other for a half-bar" beats "kicks were off". ...
HONEST — flattery is worse than silence. ... say what wasn't and how to fix.
```

**Gaps to sharpen:**
1. **No positive-callout balance rule** (unlike PRO's PROPS arm `:508` / beginner's ENCOURAGING TONE `:439`) — the over-correction-to-cold risk (Pitfall 3). Add a balance rule mirroring PRO.
2. **Prescribe-clause implied, not required** — tighten "say what wasn't and how to fix" toward PRO's "name it AND say the move in the SAME line" (`:506`).
3. **DJ-verb set absent** — surface the canonical verbs.

**ANCHOR_PHRASES (UPDATABLE):** `tests/prompts/test_matrix.py:79-88` `[("intermediate","coach")]`.

---

### `src/vibemix/prompts/matrix.py` — COACH_PRO (the analog itself — minimal edit)

**Cell location:** `matrix.py:502-543`. **Already strong** (DESERVED-CRITIQUE+FIX / NUDGE-FORWARD / PROPS arms + READ THE MOMENT anti-quota at `:520` + DELIVERY calm block at `:528`).

**Only gap:** surface the explicit canonical DJ-verb LIST (kill/swap/cut/filter/wait/tighten/ride/pull/push) so harmonic turns read in the same register. LOW-effort one-line verb anchor.

**ANCHOR_PHRASES (UPDATABLE):** `tests/prompts/test_matrix.py:89-98` `[("pro","coach")]` — but PRO anchors are already prescriptive ("phrase ended on the 3", "blend overstayed by 16"); likely no anchor change needed, only prose verb-anchor.

---

### `src/vibemix/state/coach.py` — `task_for_event` (AUDIT-FIRST; likely no edit)

**Analog / done-right reference:** the Phase-60 KEY_CLASH arm (`coach.py:267-290`) and TRANSITION_OPPORTUNITY arm (`:298-316`). These already own the deck/harmonic voice the grounded way.

**KEY_CLASH arm pattern to verb-align cells AGAINST** (`coach.py:280-290`):
```python
return (
    f"HARMONIC CLASH confirmed by the system (you do NOT decide this): "
    f"deck {a_side} is {a_cam}, deck {b_side} is {b_cam} — {gap}, "
    f"they're fighting where the two decks' melodies overlap. Tell Kaan "
    f"the move in DJ verbs (kill {b_side}'s mids, cut on the drop, "
    f"filter one out, don't ride the pads). Cite BOTH keys exactly: "
    f"[key:{a_side}:{a_cam}] and [key:{b_side}:{b_cam}]. Do NOT invent a "
    f"key and do NOT compute intervals ...")
```
Verbs emitted: **kill, cut, filter, ride** — the COACH cell prose must use the SAME set so a harmonic turn reads identically to a MIX_MOVE turn. The `:266` comment is explicit: *"Phase 61 owns the persona voice; this phase keeps to the grounded FACTS."*

**MIX_MOVE arm** (`coach.py:238-251`) — SHARED across hype+coach, byte-pinned. The knob-ban is GONE ("Name the EQ, filter, or move … you decide what matters this moment"). **Prefer NOT editing** (Pitfall 1 — shared arm edit shifts hype too). If verb-consistency forces a tweak, it trips `test_coach.py:279-298` → deliberate cross-mode noted decision.

**Default action:** leave all `task_for_event` arms; align verbs in the mode-specific COACH cells only (research Assumption A2).

---

### `tests/prompts/test_matrix.py` — extend coach asserts (Wave 0)

**Analog for the new per-cell asserts:** the existing per-cell anchor + substrate test family:
- `test_prompt_01_each_cell_has_eight_anchor_phrases` (`:277-283`) — the anchor-presence pattern.
- `test_prompt_01_coach_mode_includes_feedback_bias` (`:374-380`) — the coach-marker pattern (extend to assert the positive-callout BALANCE rule).

**Pattern to copy** (`tests/prompts/test_matrix.py:374-380`):
```python
@pytest.mark.parametrize("skill", ["beginner", "intermediate", "pro"])
def test_prompt_01_coach_mode_includes_feedback_bias(skill: str) -> None:
    body = build_system_instruction(skill, "coach")
    markers = ["coach", "feedback", "improve", "honest"]
    assert any(m in body.lower() for m in markers), ...
```

**New asserts to add (parametrized over the 3 coach skills):** (a) DJ-verb vocabulary present (kill/swap/cut/filter/tighten/ride), (b) a prescribe-clause / "same line" rule present, (c) a positive-callout balance rule present, (d) coach mode routes to `COACH_TAG_DSL_BLOCK` (no `[excited]`/`[fast]`).

**FROZEN — DO NOT TOUCH:**
- `ANCHOR_PHRASES[("intermediate","hype")]` (`:46-58`), `[("beginner","hype")]` (`:36-45`), `[("pro","hype")]` (`:59-68`).
- `test_prompt_01_hype_intermediate_byte_identical_to_persona` (`:155-180`), `test_q_v4_byte_identity_preserved_at_constant_level` (`:436-462`), `test_double_opt_out_byte_identical_to_cell` (`:570-583`).

**UPDATABLE (deliberate, in lockstep with cell edits):** the three coach `ANCHOR_PHRASES` entries (`:69-98`).

---

### `tests/state/test_coach.py` — NEW KEY_CLASH/TRANSITION voice assert (Wave 0 gap)

**Confirmed gap:** `grep` finds NO KEY_CLASH / TRANSITION_OPPORTUNITY / harmonic test in `test_coach.py`. Add one.

**Analog to copy** — `test_task_mix_move_LOAD_BEARING_anti_slop_clause` (`tests/state/test_coach.py:279-298`):
```python
def test_task_mix_move_LOAD_BEARING_anti_slop_clause():
    out = AICoach.task_for_event(
        _ev("MIX_MOVE", {"moves": ["A_play→ON", "A_low: cut→killed (big twist)"]})
    )
    assert "A move just landed [A_play→ON, ...]" in out
    assert "CHANGE point" in out
    assert "Do NOT name faders/EQs/knobs/decks/controls" not in out
    assert "Name the EQ" in out
    assert "you decide what matters" in out
    assert "output a single space to stay silent" in out
```
**New test shape (KEY_CLASH):** build `_ev("KEY_CLASH", {a_side,a_camelot,b_side,b_camelot,semitones})`; assert the DJ-verb move present ("kill"/"cut"/"filter"), BOTH keys cited (`[key:A:8A]` + `[key:B:...]`), and the no-invent guard ("Do NOT invent a key"). This FENCES the harmonic voice so a future cell edit can't silently break it.

**FROZEN goldens in this file (verify still green after every edit):** `test_task_heartbeat_LOAD_BEARING_anti_silence_clause` (`:301-309`, byte-pinned `==`), `test_task_layer_arrival_exact_string` (`:271-276`, byte-pinned `==`), the MIX_MOVE asserts (`:279-298`).

---

### `tests/agent/test_dj_cohost_matrix_dispatch.py` — NEW dual-path assert (COACH-02 proof point)

**Integration point (verified):** `dj_cohost.py:447` sets `self._gen_cfg.system_instruction = prompt_body` (genai path) and `dj_cohost.py:813-819` calls `stream_or(..., system_instruction=self._prompt_body, ...)` (OpenRouter path). BOTH derive from the SAME `build_system_instruction(...)` body — sharpening the COACH cell propagates to both paths with zero path-specific code.

**Analog to copy** — `test_dispatch_06_gen_cfg_system_instruction_matches_dispatch` (`:180-205`):
```python
def test_dispatch_06_gen_cfg_system_instruction_matches_dispatch(mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "beginner")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    mocker.patch.object(Agent, "__init__", return_value=None)
    agent = DJCoHostAgent(...)
    assert agent._gen_cfg.system_instruction.startswith(_coach_rendered(COACH_BEGINNER))
    assert "[ev:" in agent._gen_cfg.system_instruction
```

**New dual-path assert:** a coach `_prompt_body` substring (e.g. a new COACH verb-anchor phrase) appears in BOTH `agent._gen_cfg.system_instruction` AND `agent._prompt_body` (the value handed to `stream_or`). Use the existing `_build_state` / `_FakeRecorder` / `_coach_rendered` helpers (`:29-82`) — same construction scaffold, no new fixture.

---

### `tests/agent/test_coach_prompt_grounding.py` — extend with anti-slop/cited assert (Wave 0)

**Analog:** the file's own existing scaffold-pin pattern. Markers already defined (`:36-37`): `CITATION_GRAMMAR_MARKER = "--- CITATION GRAMMAR"`, `ANTI_SLOP_FOOTER_MARKER = "DO NOT SAY"`. Real `EvidenceRegistry` snapshot helper at `:52-59`.

**Anti-slop structural guarantee to lean on (COACH-04):** `src/vibemix/coach/citation_linter.py:41-54` — `key` is in the EXISTENCE-ONLY set (absent from `_TIME_KEYED_SOURCES`); a fabricated `[key:A:12B]` never observed by the poller fails `body in snapshot["key"]` → the WHOLE turn is stripped, response-level binary. **DO NOT modify the linter** — the persona phase relies on it. Add a coach-context assertion that the cited-only contract holds (the existing linter tests live in `tests/coach/test_citation_linter.py` — reference, do not duplicate).

## Shared Patterns

### Persona dual-path propagation (COACH-02)
**Source:** `src/vibemix/agent/dj_cohost.py:447` (genai `_gen_cfg.system_instruction`) + `:813-819` (OpenRouter `stream_or(system_instruction=self._prompt_body)`).
**Apply to:** every COACH cell edit — no path-specific code; one body feeds both. DO NOT TOUCH `dj_cohost.py`; only confirm via the new dual-path test.

### Anti-slop structural strip (COACH-04)
**Source:** `src/vibemix/coach/citation_linter.py:41-54` (existence-only `[key:...]` whole-turn strip).
**Apply to:** all prescriptive coach prose — "prescriptive but grounded" is enforced by code, not prompt-trust. Persona layer teaches the voice only.

### observed → impact → prescribe == the citation contract
**Source:** `matrix.CITATION_GRAMMAR_BLOCK` (`matrix.py:101-138`) + the `[ev:]`/`[key:]` grammar. Hype stops at *observed* and celebrates; coach continues to *impact + prescribe*. Same grounding, different verb. Do NOT bolt on a separate SBI/AID framework.
**Apply to:** all three COACH cell edits.

### Calm-only coach TTS tag routing (COACH-04, Pitfall 5)
**Source:** `matrix.py:789-793` — `build_system_instruction` routes coach mode to `COACH_TAG_DSL_BLOCK` (`matrix.py:209-223`, calm set `[chill]/[whisper]/[slow]/[laugh]`), hype keeps full `TTS_TAG_DSL_BLOCK`. **Do NOT undo this gate.**
**Apply to:** assert in the new test_matrix coach tag test.

### Coach closing recency directive (warmth preservation, Pitfall 3)
**Source:** `COACH_CLOSING_BLOCK` (`matrix.py:231-241`) appended LAST in coach mode (`matrix.py:801-802`) — "trust your own ears and judgment". Keep it intact; it's the over-correction-to-cold anchor.

## No Analog Found

None — every modified file and new test has an in-repo analog. This is a sharpen-and-fence phase on an existing, green (122-test) substrate.

## Metadata

**Analog search scope:** `src/vibemix/prompts/`, `src/vibemix/state/`, `src/vibemix/agent/`, `src/vibemix/coach/`, `tests/prompts/`, `tests/state/`, `tests/agent/`, `tests/coach/`.
**Files scanned:** matrix.py, coach.py, dj_cohost.py, citation_linter.py + 5 test files (read directly; line-anchored).
**Pattern extraction date:** 2026-05-21
