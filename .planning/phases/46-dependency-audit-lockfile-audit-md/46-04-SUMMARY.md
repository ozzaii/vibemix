---
phase: 46-dependency-audit-lockfile-audit-md
plan: 04
status: complete
commit: 1044dcc
requirements: [DEPS-06, DEPS-08]
---

# Plan 46-04 Summary — Dep-cull surface + CycloneDX SBOM

## What shipped

- **Cull surface** documented in `scripts/audit/dep_ratings.yaml` `decisions:` block + rendered into `docs/AUDIT.md` § Decisions:
  - `cull-blocked-livekit-plugins-openai` — `rg` found 4 direct imports in `src/vibemix/agent/tts_chain.py:25` + 3 test files; cull blocked, Kaan-action surface.
  - `defer-google-cloud-speech` — zero direct imports; retained as transitive of livekit-plugins-google.
  - `defer-google-cloud-texttospeech` — same as above.
- `scripts/audit/dep_ratings_schema.json` — JSON Schema (draft 2020-12) validating dep_ratings.yaml (incl. decisions array with action enum: removed / retained-as-transitive / cull-deferred / cull-blocked).
- `scripts/audit/gen_cyclonedx.sh` — multi-ecosystem CycloneDX producer (cyclonedx-bom 7.3.0 + cargo-cyclonedx 0.5.7 + @cyclonedx/cdxgen 10.10.5), emits 3 per-ecosystem files + merged `vibemix.cdx.json` with jq fallback for merge.
- `.github/workflows/sbom.yml` — appended `cyclonedx-sbom` job (sbom.yml now has 2 jobs: syft SPDX + CycloneDX); both attach to release assets.
- `.github/workflows/dep-audit.yml` — appended `dep-cull-verify` job (now 6 jobs total).
- `tests/audit/test_dep_ratings_schema.py` (4 tests) + `tests/audit/test_dep_cull_complete.py` (4 tests) — schema + cull-surface assertions.
- `tests/audit/test_deny_toml_policy.py::test_dep_audit_workflow_has_three_jobs` rewritten to `test_dep_audit_workflow_has_required_jobs` — accommodates later plans adding more jobs without breaking the assertion.

## Verification

- `uv run pytest tests/audit/ -x` — 31/31 tests pass across 6 test files.
- `uv run python scripts/audit/gen_audit_md.py --check` — idempotent (in sync).
- `bash -n scripts/audit/gen_cyclonedx.sh` — clean syntax.
- `.github/workflows/dep-audit.yml` has 6 jobs; `sbom.yml` has 2 jobs.

## Deviations from plan

- **Cull of `livekit-plugins-openai` is BLOCKED, not applied.** Plan 04 Task 1 explicitly covers this branch: if `rg` finds direct imports, document as `cull-blocked` + add Kaan-action surface item. Direct imports found:
  - `src/vibemix/agent/tts_chain.py:25` — `from livekit.plugins.openai import tts as _openai_tts_mod`
  - 3 test files reference the same surface
  - Removal requires rewiring the TTS proxy fallback chain — explicitly out of scope for Phase 46.
- **uv.lock NOT regenerated** — no pyproject.toml mutation (cull blocked); uv.lock byte-stable.
- Google Cloud deps remain as transitives (zero direct imports — defer is correct).

## Kaan-action surface

- **CULL-BLOCKED — livekit-plugins-openai retained**: dep is in use by `src/vibemix/agent/tts_chain.py:25` for the TTS proxy fallback chain. To complete the cull, rewire the TTS chain to remove the OpenAI adapter path (out-of-scope Phase 46; suitable for a focused refactor phase post-v3.1).

## Files touched

```
scripts/audit/dep_ratings.yaml         (+38 lines, decisions: block)
docs/AUDIT.md                          (regenerated, 11,822 bytes, § Decisions populated)
scripts/audit/dep_ratings_schema.json  (new, 60 lines, draft 2020-12 schema)
scripts/audit/gen_cyclonedx.sh         (new, executable, 75 lines)
.github/workflows/sbom.yml             (+50 lines, cyclonedx-sbom job)
.github/workflows/dep-audit.yml        (+20 lines, dep-cull-verify job)
tests/audit/test_dep_ratings_schema.py (new, 4 tests)
tests/audit/test_dep_cull_complete.py  (new, 4 tests)
tests/audit/test_deny_toml_policy.py   (1 test rewritten — flexible job-set assertion)
```

Commit: `1044dcc`
