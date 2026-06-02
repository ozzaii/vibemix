# CODEX_READY — EQ-Move Physics Keystone (`intel/eq_move_model.py`)

> The narrator→coach unlock. Build the producer that lets the live guard LICENSE a causal claim ("your low-cut thinned the bass") instead of refusing all of them. Works on the **master-only rig everyone runs** (no per-deck routing needed). Spec recovered from `.planning/packets/2026-06-01/recovered/wf_d9ddbeed-f5f__ALT1__mixxx-eq-filter-dsp...md`; every live anchor re-verified at HEAD `ce909a87`.
> **Owner: Codex A.** Claude is read-only; produced this packet + will do the LIVE verification. Map: `GOLD-WIRING-MAP.md` (this is Step 1+3, the keystone).

## Why (the gap, precisely)
Today the live guard `apply_live_claim_guard` (`state/deck_context.py:2313`) **REFUSES every move→effect causal claim** — returns `LIVE_MOVE_EFFECT_HELD_REPLY` (`:2386`, `reason="dsp_delta_not_causal_proof"` `:2389`) — because no producer ties a MIDI move to its measured spectral effect. `render_move_effect_context` (`:2070`) even shows the band delta but stamps `rule=dsp_delta_not_causal_proof` (`:2098`). The low-kill guard `_has_unsupported_mixer_low_kill_claim` (`:2585`) checks only the **controller MIDI tier** and `return False` on a master-only rig. Net: the co-host can describe sound but is forbidden to say *your move caused it* → it narrates. This module supplies the missing producer.

## Scope (this packet = the EQ keystone only)
**IN:** EQ/filter move → predicted per-band dB → guard licenses the claim iff prediction direction ∧ measured band delta agree. **OUT (fast-follow, separate packet):** the xfader/level `mixxx_xfade_gains` sibling (`state/mixer_physics.py`) — same pattern, lower leverage. Build EQ first.

## 1. New module — `src/vibemix/intel/eq_move_model.py`
`intel/` is the correct home (import-light, no audio capture, no model clients, numpy-only). Clean-room from the **public RBJ audio-EQ cookbook** — NOT from Mixxx GPL source (coefficients/corner-freqs are parameters/facts, not copyrightable code; never vendor Mixxx).

```python
from __future__ import annotations
import numpy as np

# Mixxx-matched defaults (public cookbook params, clean-room):
LO_MID_CORNER = 246.0      # Hz  low|mid split
MID_HI_CORNER = 2484.0     # Hz  mid|high split
LOW_KILL_FC   = 99.0       # Hz
HIGH_KILL_FC  = 3700.0     # Hz
KILL_GAIN_DB  = -23.0
Q_KILL, Q_SHELF, Q_BOOST = 0.9, 0.4, 0.3

def predicted_band_gains(move: str, fs: int) -> dict[str, float]:
    """Predicted per-band gain (dB) of a known EQ/filter move, integrated |H|^2
    over the band windows used by band_features. e.g.
    predicted_band_gains('low_kill', 48000) -> {'sub':-23,'low':-21,'mid':-0.5,'high':0.0}
    Returns {} for an unrecognized move (caller treats {} as 'no prediction -> refuse')."""
```
- **Math:** derive biquad `(b, a)` via RBJ cookbook (~15 numpy lines per filter type: low/high-shelf, peaking, LP/HP). Magnitude `|H(e^jω)| = |polyval(b, z) / polyval(a, z)|`, `z = exp(-1j·2π·f/fs)` over a freq grid. Predicted band gain = `10·log10(∫|H|² over band / band_width)`. No scipy, no filtering of audio — just the predicted gain. Microseconds.
- **Bands MUST match the measurement side** — `audio/band_features.py:30 band_energy_ratios` uses `sub 20–100, low 100–300, mid 300–4000, high 4000–8000`. Integrate `|H|²` over exactly those windows.
- **Move vocabulary** (key off these — the stable `moves` strings from `event_detector.py:35/364`): `'killed' '_low:' '_mid:' '_hi:' '_filter:' 'xfader'`. Map e.g. low-kill→`low_kill`, low boost→`low_boost`, filter sweep→`filter_lp/hp`. Unknown → `{}`.

## 2. Guard wiring — `state/deck_context.py::apply_live_claim_guard` (`:2313`)
At the move-effect refusal branch (the path that returns `LIVE_MOVE_EFFECT_HELD_REPLY` at `:2386`), BEFORE refusing:
1. Detect an EQ-effect claim in the reaction text (extend/sit beside `_has_unsupported_mixer_low_kill_claim:2585`).
2. Find a matching EQ move in `moves` (the `extra["moves"]` tuple, `event_detector.py:377`).
3. `pred = predicted_band_gains(move, fs)`. Measure the band delta over the **post-move window** (`deck_audio_window_context`, `deck_context.py:571`) via `render_audio_delta_items:1794` / `band_energy_ratios` — **NOT the instant frame** (coefficient-ramp + isolator group delay lag the move ~1 buffer; comparing the instant frame REFUTES a true kill that hasn't settled).
4. **Double-gate (the anti-slop core):** LICENSE only iff `pred` direction **and** the measured `sub+low` (etc.) delta agree in sign beyond `DELTA_FLOOR=0.10` (`state/deltas.py:24`).
   - Match → **license:** emit the causal atom into `render_move_effect_context` (`:2085`), replacing `rule=dsp_delta_not_causal_proof` (`:2098`) for THIS licensed case with `[move_effect: A_low_kill -> sub_-20dB ✓measured_-18dB]`; register it in `EvidenceRegistry` (`evidence_registry.py:222`, permissive — new source `"move_effect"`, no schema change) so it surfaces in `grounding_refs` and the citation passes.
   - No match / bands flat (the **breakdown with no bass** case) / move absent → **keep current refuse** → `LIVE_MOVE_EFFECT_HELD_REPLY`. Abstain-first preserved.

## 3. Hard guardrails (do NOT regress — this IS the anti-slop surface, Invariant #2/#3)
- **Default stays refuse.** Licensing is the *exception* gated by the double-match. Never license on prediction alone or measurement alone.
- **Must REFUTE the breakdown false-accept:** controller says "low at kill tier" but no bass present → bands don't move → REFUSE. This is the headline correctness test.
- Keep `_DECK_AUDIO_DELTA_CONTEXT_FORBIDDEN_ATOMS` (`:327`) as the default; only the licensed `move_effect` atom is exempt (add a narrow `_MOVE_EFFECT_LICENSED_RE` exemption).
- Don't touch single-writer `MusicState`, the citation grammar, or the abstain-first posture. No new third-party dep, no PyInstaller spec change.

## 4. Acceptance
**SRC (Codex, required to land):**
- `tests/intel/test_eq_move_model.py`: `predicted_band_gains` returns correct sign+approx magnitude for low_kill/high_kill/low_boost/filter sweep; `{}` for unknown move; band keys match `band_features`.
- `tests/state/test_deck_context.py` (extend): guard LICENSES when predicted∧measured agree (cites `move_effect`); guard REFUSES when measured bands flat (breakdown); guard REFUSES when move absent; existing guard/abstain tests stay green.
- `ruff` clean; full suite green.

**LIVE (Claude verifies on Kaan's rig — the real gate):** on the master-only rig, via the ws bus:
- Real low-cut on a track WITH bass → co-host emits a grounded causal line ("your low-cut pulled the sub down"), `slop_ratio<1`, cites `[move_effect:...]`. **Narrator→coach proven.**
- Low-cut on a breakdown with no bass → co-host does NOT claim the effect (stripped/held). **False-accept refused.**

**Proof tiers:** SRC (Codex) → LIVE (Claude, post-merge) → PKG (normal build). Don't conflate.

## 5. Gate
**`vibemix-grounding-review` REQUIRED** — this changes what the co-host SAYS and is the anti-slop boundary. The review must confirm the double-gate can't license a false claim (esp. the breakdown case) and that the default refuse path is intact. Effort ~1–1.5 days (EQ-band half + the guard double-gate; xfader sibling deferred).

---
*Spec source: `recovered/wf_d9ddbeed-f5f__ALT1__mixxx-eq-filter-dsp-the-r-slop-grounding-unlock-round-2.md`. Live anchors re-verified: guard `deck_context.py:2313`, refuse `:2386/:2389`, low-kill `:2585`, `render_move_effect_context:2070/:2098`, `render_audio_delta_items:1794`, forbidden-atoms `:327`, `LIVE_MOVE_EFFECT_HELD_REPLY:374`, `band_energy_ratios` band_features.py:30, `DELTA_FLOOR` deltas.py:24, move vocab event_detector.py:35/364, registry evidence_registry.py:222.*
