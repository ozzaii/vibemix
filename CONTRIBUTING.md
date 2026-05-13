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
2. Add `src/vibemix/midi/profiles/<your-controller-slug>.json` following the schema documented at `docs/midi-mapping.md`.
3. Add a smoke test under `tests/midi/` that loads the profile and asserts the CC/note map shape.
4. PR title: `feat(midi): add <vendor> <model> mapping`.
5. CI auto-merges non-conflicting profile additions once green.

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

## License

By contributing, you agree your work is licensed under Apache 2.0 and that you certify the DCO with each commit.

---

## Questions?

Open an issue or email ozai@bravoh.com.
