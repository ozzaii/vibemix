# Phase 46 Discussion Log

**Mode:** `--auto` (gsd-autonomous fully). No interactive user prompts; every gray area resolved by the recommended-default rule with memory-anchor justification. This log is human-reference only — downstream agents read CONTEXT.md.

---

## Gray Areas Auto-Resolved

| # | Area | Recommended Default Selected | Memory Anchor |
|---|------|-----------------------------|---------------|
| 1 | Python lockfile strategy | uv-managed hermetic `uv.lock` regenerated inside `python:3.12-slim-bookworm` container | Pitfall 1 + research/STACK.md `uv==0.11.14` |
| 2 | Hermetic builder location | CI workflow `.github/workflows/dep-audit.yml` only — never `.venv` | Pitfall 1 |
| 3 | Preserve pyrekordbox `--no-deps` override | YES — already encoded in pyproject.toml; document in AUDIT.md rationale | pyproject.toml lines 28+ |
| 4 | AUDIT.md structure | Single file, 3 H2 sections (Py/Rust/JS) + § Decisions + § GH Actions | ROADMAP success criterion 3 |
| 5 | Table columns | Package, Version, License, Rationale, Install-Impact (G/Y/R emoji), Notes | `project_one_click_install_hard_req` |
| 6 | G/Y/R rubric | Green=pure-wheel/no-prompt; Yellow=native wheel with prebuilt binaries; Red=system extension/driver/manual install | `project_one_click_install_hard_req` |
| 7 | AUDIT.md generation | Hybrid: auto-generate version+license columns; rationale+rating from hand-authored `dep_ratings.yaml` | n/a (engineering judgment) |
| 8 | Freshness gate definition | git-log-based last-commit-time (NOT filesystem mtime — unstable on clones) | n/a (engineering judgment) |
| 9 | CI workflow surface | New `.github/workflows/dep-audit.yml`; extend existing `sbom.yml`; leave `python-cve.yml` + `rust-cve.yml` alone | research/STACK.md + existing CI inventory |
| 10 | Dep-cull verdict on 3 suspects | REMOVE all three (livekit-plugins-openai, google-cloud-speech, google-cloud-texttospeech) | `feedback_no_clap_use_gemini_embedding` + STACK.md observed list |
| 11 | SBOM dual-emit | BOTH CycloneDX + SPDX | ROADMAP success criterion 4 |
| 12 | Dependabot ecosystem split | Single `.github/dependabot.yml` with 4 ecosystem blocks; weekly cadence; NO auto-merge | n/a (engineering judgment) |

---

## Deferred Ideas

None proposed. The phase is build-time + CI + docs only; no scope-creep surface presented itself.

---

## Constraints Quoted Verbatim from Task Spec

- `uv==0.11.14` (Python lockfile)
- `cyclonedx-python==7.3.0` (CycloneDX SBOM)
- `pinact` v3.x (GH Actions SHA pin)
- cargo-deny license allowlist: Apache-2.0 / MIT / BSD / ISC / Unicode-DFS-2016 / MPL-2.0; GPL banned
- Hermetic lockfile generation in `python:3.12-slim-bookworm` container

---

## Notes for Downstream Agents

- **gsd-phase-researcher:** read `.planning/research/PITFALLS.md` § Pitfall 1 first; then existing CI workflow inventory under `.github/workflows/`; then `pyproject.toml` overrides block (lines 28+ — pyrekordbox `--no-deps` recipe is load-bearing).
- **gsd-planner:** six-plan decomposition is locked in CONTEXT.md § Plan Decomposition. Honor sequencing notes; preserve POC + ModelRouter + anti-slop + privacy + worktree-subagent invariants in every plan.
- **gsd-plan-checker:** reject any plan whose subagent prompt skeleton lacks the Step-0 `git merge origin/main` block (per `feedback_worktree_must_sync_main_first`).
