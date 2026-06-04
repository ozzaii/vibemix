# Sven live-linter parity grounding review

Date: 2026-06-04
Review target: live-linter parity for Respan sim plus measured `KICK_DENSITY_SHIFT`
fallback.

## Surface

- `src/vibemix/state/prompt_builder.py`
  - Full and compact prompts now append the current event's registered `ev:` atom
    when the `EvidenceRegistry` snapshot contains it.
  - `KICK_DENSITY_SHIFT` still grounds only on measured `prev_density`,
    `new_density`, and `delta`; the prompt asks for one forward nudge and the
    current event bracket when that measured shift is the reason to speak.
- `src/vibemix/agent/dj_cohost.py`
  - Invalid model output can fall back only for `KICK_DENSITY_SHIFT`, only when
    the same linter snapshot contains the registered event citation.
  - The fallback text is rechecked by `CitationLinter.check(..., mode="live")`
    before any audio can emit.
  - Existing strip and bypass behavior remains unchanged for uncited or
    unregistered model output.
- `scripts/eval/respan_sven_sim.py`
  - `--match-live-linter` now mirrors the live response-level linter and the
    registered KICK event fallback.
  - The KICK target carries the real `grounding_refs[[ev:KICK_DENSITY_SHIFT@1281.0]]`
    citation path instead of scoring uncited text.

## Invariant review

- Citation grounding: pass. No citation source list or grammar source was changed;
  emitted fallback text must resolve against `EvidenceRegistry` and the live linter.
- Trust-the-audio: pass. The fallback is based only on the event type plus measured
  density delta already carried on `Event.extra`; it does not infer track, deck,
  phrase, transition, or controller causality.
- Rare + earned speak moat: pass. `decide_speak_gate` was not loosened; deterministic
  sim routing remains `10/10` only with the opt-in KICK target.
- Speech source: pass. No TTS provider or model route changed; spoken text still goes
  through the existing local MOSS path.
- One socket: pass. No runtime socket code changed; no sidecar was launched for this
  review.

## Evidence

- `uv run pytest -q tests/agent/test_dj_cohost_scaffold_repair.py tests/state/test_coach.py tests/eval/test_respan_sven_sim_quality_gate.py`
  - `126 passed`
- `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/prompt_builder.py scripts/eval/respan_sven_sim.py tests/agent/test_dj_cohost_scaffold_repair.py tests/state/test_coach.py tests/eval/test_respan_sven_sim_quality_gate.py`
  - clean
- `uv run python scripts/eval/respan_sven_sim.py --gate-only --include-kick-density-target --match-live-linter --no-log`
  - gate routing `10/10`
- `uv run python scripts/eval/respan_sven_sim.py --match-live-persona --match-live-linter --include-kick-density-target --require-quality --out .planning/eval-runs/sven-live-linter-parity-20260604/respan-sven-sim-live-linter-parity-strict-quality.json`
  - quality gate PASS
  - gate routing `10/10`
  - generated means: friend `3.0`, grounded `3.0`, earned `2.2`, move `2.4`,
    voice `2.6`
  - `phase_with_cue_lookahead`: friend `3`, grounded `3`, voice `3`
  - `track_change_with_cue_lookahead`: friend `3`, grounded `3`, voice `3`
  - `kick_density_shift_sparser`: friend `3`, grounded `3`, earned `2`,
    move `2`, voice `2`
  - KICK linter action: `event_fallback_emit`, one resolved
    `[ev:KICK_DENSITY_SHIFT@1281.0]` citation
- `uv run python scripts/eval/respan_sven_heartbeat_judge.py --session "$HOME/Library/Application Support/vibemix/recordings/20260603-175859" --events ALL --describe-bank-census --concurrency 4 --require-quality --min-judged 1 --out .planning/eval-runs/sven-live-linter-parity-20260604/respan-sven-heartbeat-live-linter-parity-strict-quality.json`
  - quality gate PASS
  - friend `2.0`, grounded `3.0`, earned `2.0`, move `3.0`, voice `2.0`
  - describe-bank census: `20/21` silenced, `1` kept

## Boundary

This review proves current-source prompt/linter parity and the recorded-set
threshold. The heartbeat judge replays old `response.txt` lines, so it remains a
standing real-set threshold check rather than proof that the old spoken KICK line
would regenerate. A sustained driven live set remains the outer Sven validation
gate.
