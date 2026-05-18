---
phase: 46-dependency-audit-lockfile-audit-md
plan: 01
status: complete
commit: b5400a4
requirements: [DEPS-01]
---

# Plan 46-01 Summary — Hermetic uv.lock regen + dep-audit CI scaffold

## What shipped

- `scripts/audit/regen_uv_lock.sh` — runs `uv lock` inside `python:3.12-slim-bookworm` container against the workspace bind mount; never against Kaan's `.venv`. Hard-pins `uv==0.11.14`.
- `scripts/audit/__init__.py` + `tests/audit/__init__.py` — package markers.
- `.github/workflows/dep-audit.yml` — new workflow with `uv-regen-diff` job; triggers on pyproject.toml + uv.lock + scripts/audit/** changes.
- `tests/audit/test_regen_uv_lock_smoke.py` — 6 static-string assertions pinning the image + uv version + bash strict mode + no `pip freeze` in executable lines + docker bind mount.

## Verification

- `bash -n scripts/audit/regen_uv_lock.sh` — clean.
- `uv run pytest tests/audit/test_regen_uv_lock_smoke.py` — 6/6 passed.
- `uv run python -c "import yaml; ... 'dep-audit.yml'"` — workflow parses + has `uv-regen-diff` job.
- `uv.lock` baseline (revision=3) preserved; cull targets (`google-cloud-speech`, `google-cloud-texttospeech`, `livekit-plugins-openai`) remain (7 mentions) — Plan 04 removes them.

## Deviations from plan

- Test `test_no_pip_freeze_anywhere` renamed to `test_no_pip_freeze_in_executable_lines` after detecting that the script's banner comment legitimately cites Pitfall 1's "pip freeze" by name as the forbidden path. Test now inspects only non-comment lines.

## Kaan-action surface

- Hermetic uv.lock regen step deferred to CI (no docker pull on this autonomous run). First PR that triggers `dep-audit.yml::uv-regen-diff` runs the same logic and fails on drift if any exists. No drift expected since pyproject.toml is unchanged.

## Files touched

```
.github/workflows/dep-audit.yml  (new)
scripts/audit/__init__.py        (new)
scripts/audit/regen_uv_lock.sh   (new, executable)
tests/audit/__init__.py          (new)
tests/audit/test_regen_uv_lock_smoke.py (new)
```

Commit: `b5400a4`
