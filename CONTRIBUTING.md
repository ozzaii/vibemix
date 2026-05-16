# Contributing to vibemix

Welcome — and thanks for considering a contribution.

vibemix is open-source under Apache 2.0. Bug fixes, controller mappings, and prompt template additions are all welcome. This document describes the contribution paths and the DCO sign-off requirement.

---

## Developer Certificate of Origin (DCO)

Every commit must be signed off using the DCO. The DCO is a per-commit attestation that you have the right to submit your contribution under Apache 2.0. Sign off with:

```bash
git commit -s -m "your commit message"
```

This appends a `Signed-off-by: Your Name <your@email>` trailer. CI rejects PRs whose commits lack the trailer.

If you forget, fix it with: `git commit --amend -s --no-edit` (single commit) or `git rebase --signoff <base>` (multiple commits).

---

## Contribution Paths

> **For hallucinated reactions or anti-slop violations**, please use the [AI misbehavior issue template](.github/ISSUE_TEMPLATE/ai_misbehavior.yml) instead of a generic bug report — it captures the grounding evidence we need to actually fix the underlying prompt or detector.

### 1. Bug fix or feature improvement (standard PR)

1. Fork the repo, create a topic branch.
2. Make the change. Keep PRs focused — one fix per PR.
3. Add or update tests where appropriate.
4. Run the local gates:
   - `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`
   - `cd tauri/ui && npx vitest run` (if you touched frontend)
   - `cargo check` (if you touched Rust)
5. Sign off (`git commit -s`) and open a PR. Link the issue you're fixing.

### 2. New controller mapping

Adding support for a controller we haven't curated? You'll add one JSON profile and a smoke test.

1. Open a `new_controller` issue first so we don't get duplicates.
2. Capture the controller's MIDI shape with our sniff tool. Plug the controller in, then run:

   ```bash
   source .venv/bin/activate
   python3 scripts/sniff_controller.py --device "Your Controller Name"
   ```

   The tool listens for ~30s while you exercise every knob, fader, button, and jog wheel. It writes a JSON skeleton to stdout — the shape that goes into the profile file.
3. Add `src/vibemix/midi/profiles/<your-controller-slug>.json` following the schema documented at `docs/midi-mapping.md`. Use the sniff output as the starting point and label every CC / note with what it does.
4. Add a smoke test under `tests/midi/` that loads the profile and asserts the CC/note map shape.
5. PR title: `feat(midi): add <vendor> <model> mapping`.
6. CI auto-merges non-conflicting profile additions once green.

### 3. New prompt template

Prompts are where vibemix's personality lives. New templates need human review to keep the anti-slop standard intact.

1. Open a `feature_request` issue first describing the cell you're targeting (skill × mode × language?).
2. Add the template under `src/vibemix/prompts/templates/`.
3. Ensure it respects the anti-slop dictionary at `src/vibemix/prompts/negative_dict.py`.
4. Manual review by a maintainer (currently Kaan).
5. Prompts are merged after live audition on a real DJ session.

---

## Coding style

- Python: ruff + black defaults (no formatter config currently — match existing files).
- TypeScript: project uses vanilla TS with vitest. Match `tauri/ui/src/` patterns.
- Rust: `cargo fmt` before commit.
- Tests are required for behavior changes. Documentation-only changes don't need tests.
- No new pip / npm / cargo dependencies without prior discussion in an issue.

---

## What we don't accept

- Telemetry, analytics, or any code that exfiltrates user data.
- New AI providers — vibemix is Gemini-only (Bravoh decision).
- Linux ports — out of v1 scope.
- Stem separation / track ripping / DRM-circumvention features.

---

## Reporting AI misbehavior

vibemix's central thesis is "real DJ friend in your ear, no AI slop." Broken AI reactions — hallucinations, generic AI slop, late reactions, wrong-vocabulary-for-skill-level, talking over your mic — matter more to us than feature requests. They're the product's central failure mode.

**Use the [AI misbehavior issue template](.github/ISSUE_TEMPLATE/ai_misbehavior.yml).** The two highest-leverage fields are:

1. **What did the AI say?** — the literal voice line.
2. **What actually happened?** — your real musical move, the real track, the real controller action.

That pair is what lets us replay the moment and verify the grounding chain. Without it we're guessing.

If you can also attach the last 30-60 lines of `recordings/<latest-session>/events.jsonl` covering the misbehavior window, we can typically reproduce within an hour. Without those events, it's mostly archaeology.

This report channel is treated as P0 in triage. We'd rather close a hallucination class than ship a new feature.

---

## License

By contributing, you agree your work is licensed under Apache 2.0 and that you certify the DCO with each commit.

---

## Questions?

Open an issue or email ozai@bravoh.com.
