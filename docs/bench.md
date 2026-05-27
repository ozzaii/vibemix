# Bench — the validation instrument

The bench is vibemix's **dev/eval instrument**: a multi-dimensional experiment
that proves the architecture. It runs the reaction stack across a matrix of
**model × grounding × prompting × contexting × lens × taste**, scores each cell
with an automated first-pass, and lays the cells out on a clean surface for
**Kaan's ear** — the final judge (the Phase-16 rule).

It is **not** a shipped runtime feature. It never runs during a live session and
never touches the reaction loop. It opens no new ws port, adds no IPC envelope,
and uses no AI provider other than Gemini.

The central question it answers: **does the intelligence reside in the structured
evidence (the EAR) or in Gemini's raw ear?** The decisive `dsp_only` "no-audio"
cell sends a fully-populated DSP evidence body with *zero* audio attached — if
Gemini still grounds a sharp reaction, the EAR is doing the work.

## What it is

```
the 6-D matrix (model × grounding × prompting × contexting × lens × taste)
        │
        ├─ STUDY_A  — architecture axis at ONE fixed model alias
        │             (sweep grounding × prompting × contexting × lens × taste)
        ├─ STUDY_B  — model axis: the best-arch cell over router aliases
        └─ NO_AUDIO_CELL — the decisive dsp_only cell (the empirical heart)
                │
                ▼
        bench run ──▶ bench_run.json  (recorded cells: prompt + output + dsp_snapshot + usage + error)
                │
                ▼
        score_cell / rank_cells ──▶ groundedness · specificity · lens_fidelity (a SORT, not a verdict)
                │
                ▼
        render_review ──▶ a KAAN-ACTION Markdown surface with an EMPTY verdict
```

The harness can *express* the full 4×2×2×3×2 matrix; the documented **runs** are
the two focused studies plus the no-audio cell — not the full cartesian product
(cost + readability).

## Offline gate — the honest-green proof

The entire instrument is proven offline, with a **fake genai client** and
**fixture cells**, zero API calls:

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/bench/
```

This proves:

- **BENCH-01** — the dimension sweep + per-cell prompt assembly (composed from
  the *real* product seams: `model_router.resolve`, `build_lens_instruction`,
  `build_system_instruction` flags, the `MusicState` trajectory fields, the
  evidence snapshot) + the results recorder + the per-cell 429 fail-safe.
- **BENCH-02** — the three scorers (`groundedness` reuses `CitationLinter.check`
  verbatim — the product's anti-slop gate; `specificity`; `lens_fidelity`) and
  the `rank_cells` SORT — all deterministic on fixture cells.
- **BENCH-03** — the `render_review` surface generation (ranked, grouped, the
  literally-EMPTY verdict, errored cells → parked).

No model literal lives anywhere under `src/vibemix/bench/`
(`tests/bench/test_no_model_literal.py` + `scripts/release/check_no_hardcoded_model.sh`
enforce). The model axis sweeps router **aliases** only.

## The produce step — KAAN-ACTION

The real cells come from one bounded, documented invocation on the funded key:

```bash
uv run python -m vibemix bench run --study A
```

- **Key:** read from `.env` (`GEMINI_API_KEY`); `load_dotenv(override=True)`
  (Phase 77) ensures the funded key wins. The command never prints or logs the
  key — recorded cells carry prompt + output + scores only (T-81-04 / T-81-11).
- **Cost-bounded:** the two focused studies on a few real tracks at Gemini Flash
  pricing — low single-digit euro-cents one-time (`SessionMeter.summary()`
  reports € per router path post-run). Well within the ~50 €/mo dev budget. This
  is *not* a full library run.
- **Fail-safe:** a per-cell 429 / auth / network error parks that cell as
  `{"error": ...}` (output stays empty), and the sweep **continues** — it never
  fabricates output, never aborts, and never blocks the milestone. The offline
  harness + eval + the existing floor data still ship the capability if the live
  run can't complete. The studies are `A`, `B`, and `no-audio`.

## The review surface

```
bench_run.json ──▶ render_review(results, scores) ──▶ a Markdown KAAN-ACTION artifact
```

`render_review` is a **pure** JSON→Markdown transform (no clock, no randomness,
no I/O — the caller writes the file; same inputs → byte-identical output). It:

- ranks cells by their auto-score (strongest first, via `rank_cells`),
- groups them by the grounding (architecture) dimension,
- renders each cell's 6-D coordinates + the three auto-scores + the assembled
  prompt + the recorded output,
- renders an **errored cell as `ERRORED — parked`** — never as fabricated
  output (T-81-10), and
- ends with a verdict section that is **literally empty**:

  ```markdown
  ## VERDICT (Kaan fills this)
  > _Kaan fills this in — the auto-rank is a sort, not a decision._
  ```

  No code path writes a winner, picks an architecture, or synthesizes a verdict
  (T-81-09). The auto-score *ranks*; Kaan's ear *decides*.

## THE HARD HUMAN GATE — KAAN-ACTION (read this)

Autonomous **produces and ranks**; it never judges. Three items are parked as
**KAAN-ACTION** — never automated, never faked (cross-ref
[`81-VALIDATION.md` → Manual-Only Verifications](../.planning/archive/2026-05-27-v7-v8-1-phase-detail/phases/81-bench-the-validation-instrument/81-VALIDATION.md)):

1. **KAAN-ACTION — the real run.** Run `uv run python -m vibemix bench run
   --study A` (and `--study B`, `--study no-audio`) on the funded key to produce
   real cells. Cost-bounded + fail-safe; if the key has issues the run parks and
   the milestone still ships on the offline gate + floor data.
2. **KAAN-ACTION — Kaan's-ear VERDICT.** Read the review surface and judge: *did
   it click / is it slop / which architecture + model wins?* Fill in the empty
   `## VERDICT (Kaan fills this)` section. The winning architecture + model
   selection feeds GROUND-02's `live_coach` alias + the default architecture as a
   follow-up. Autonomous **never** fills this in.
3. **KAAN-ACTION — the final taste-rubric wording.** The `TASTE_RUBRIC` constant
   in `src/vibemix/bench/matrix.py` is a placeholder stand-in. The real "what
   'clicked' means" wording is Kaan's IP (like the authored persona prompts) —
   replace the placeholder with Kaan's own wording.

**In one line:** autonomous produces the surface + the auto-ranking; Kaan decides
the verdict; nothing is faked.
