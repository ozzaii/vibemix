# Phase 69: OSS Fully Integrated - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — `gsd-autonomous fully`)

<domain>
## Phase Boundary

Turn the OSS surface from "we have a license" into "a stranger can clone, install, contribute, and trust the proxy with their session." Five deliverables, each pinned by a presence test or integration test:

1. **OSS docs (OSS-01)** — `MAINTAINERS.md` ships at repo root (the only missing one of the four — `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` already exist). `CONTRIBUTING.md` is audited for the Bravoh privacy/IP carveout language ("the Bravoh proxy is closed-source by design — vibemix is Apache-2.0; the proxy is the commercial wedge"); add if missing. README links the four. `tests/repo/test_oss_presence.py::test_required_oss_files_exist` pins all four at repo root, asserts each is non-empty (≥ N bytes), confirms each is referenced from the README, and greps `CONTRIBUTING.md` for the carveout sentinel.

2. **Bravoh proxy + client-side graceful fallback (OSS-02)** — **client-side** is the vibemix repo's deliverable: when `api.altidus.world` is unreachable / 503 / 5xx / timeout, the coach surface emits a clean "co-host unavailable this session" message in the pill / mascot (NOT a crash, NOT a hallucinated coach line). Covered by `tests/integration/test_proxy_fallback.py` against a mocked-offline proxy via the existing `VIBEMIX_PROXY_BASE_URL` env var. **Server-side** hardening (per-install-UUID rate limit, token-bucket abuse handling, Prom `/metrics`, Sentry DSN) lives in the Bravoh ops repo at `api.altidus.world` — it does not edit vibemix source. Under `gsd-autonomous fully`, the server-side hardening routes to a new `KAAN-ACTION-LEGAL.md §V7-PROXY` cluster with the exact prom-metric spec + verification curl + 429-trigger contract pre-staged; engineering closes when the client-side fallback test is GREEN.

3. **Bring-Your-Own-Key path (OSS-03)** — `docs/byo-key.md` documents the BYO flow end-to-end: set `VIBEMIX_BRAVOH_PROXY=0` (or `VIBEMIX_LLM_MODE=direct`, which the codebase already honours at `runtime/session_loop.py:847`) + `GEMINI_API_KEY=<user-key>` → coach session runs against the user's own quota. The doc covers: where to get a Gemini key, how to set the env vars on macOS/Windows, verification with a smoke command, and a privacy note ("BYO mode bypasses the Bravoh proxy entirely — all calls go direct to `generativelanguage.googleapis.com`"). The fresh-account walk (`docs/byo-key-walk.md`) routes to `KAAN-ACTION-LEGAL.md §V7-LIVE` (one new cluster: `§V7-LIVE-11 — BYO fresh-account walk`) under autonomous mode — engineering closes when the doc validates against `tests/repo/test_byo_doc_shape.py`.

4. **Release publish (OSS-04)** — under `gsd-autonomous fully` and the unresolved Apple Dev + SignPath external signature clock, this REQ routes to the existing `KAAN-ACTION-LEGAL.md §SHIP-V4` cluster (already at line 3389) with the **exact `bash scripts/launch/cut_release.sh v0.1.0-rc1` invocation pre-staged** (no engineering step left to discover). Engineering deliverable: `scripts/launch/cut_release.sh` is verified runnable today via `--dry-run v0.1.0-rc1` (already exits 0 per State.md / Phase 39 ledger); add a §SHIP-V4 cross-link + a one-paragraph update to `docs/release-process.md` describing the autonomous-mode route. **v4.0 "SHIP" closes alongside this requirement ONLY when the real cut fires** — not in this milestone close under autonomous mode. The `gh release create` invocation itself is and remains Kaan's hand on the trigger (the script's load-bearing hard guard never invokes it).

5. **Homebrew tap + Scoop bucket scaffolds (OSS-05)** — `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` check into the repo with deterministic URL/SHA placeholders that resolve against the v0.1.0-rc1 artifacts (or a pinned fixture if OSS-04 hasn't fired yet). CI workflow `.github/workflows/packaging-audit.yml` runs `brew audit --new packaging/homebrew/Formula/vibemix.rb` + `scoop checkver -d packaging/scoop/vibemix.json` — both exit 0. `docs/release-process.md` gains a "Tap/Bucket publish — future milestone" section documenting the split rationale ("the actual tap/bucket push is the user-visible install upgrade and earns its own milestone — pushing to `bravoh-ai/homebrew-tap` + `bravoh-ai/scoop-bucket` are out of v7.0 scope"). `tests/repo/test_packaging_scaffolds_present.py` pins the two files + the doc section + the workflow.

**Out of scope** (acid test held — "does this turn an existing engineering-green capability into something a stranger can install, verify, contribute to, or see — without growing the surface?"):
- New product capabilities (no coach prompt changes, no new evidence sources, no new emission paths). Zero `src/vibemix/{coach,llm,state,memory,recall,decks,grounding}/` edits except the minimum needed for OSS-02 client-side fallback (likely 1 try/except in the proxy client + 1 pill emission string).
- New dependencies. Stdlib-only for the test surfaces; `brew audit` + `scoop checkver` are CI-runner-installed (no Python deps).
- New ws ports / new IPC envelopes (one-socket invariant + zero-touch on reaction path held).
- Actual tap/bucket publish (split to future milestone per OSS-05 explicit success criterion).
- Server-side proxy hardening source edits (separate repo; documented in §V7-PROXY).
- The real `gh release create v0.1.0-rc1` fire (Kaan-action gated on signatures; routes to §SHIP-V4).

</domain>

<decisions>
## Implementation Decisions

### OSS Docs — Four-File Inventory + Carveout Audit (OSS-01)
- **MAINTAINERS.md** — NEW file at repo root (≤80 lines). Sections: "Active Maintainers" (Kaan as `@bravoh-ai` / `kaan@bravoh.tech`), "How to Reach Us" (GitHub issues primary, SECURITY.md for vuln reports), "Decision Process" (Apache-2.0 / SPDX, lazy consensus, merge bar = 1 maintainer approval + CI green), "Release Cadence" (RC tags per `docs/release-process.md`), "On-Call / Response Time" (best-effort, vibemix is Kaan's OSS side-project alongside Bravoh).
- **CONTRIBUTING.md** — already exists (5.0k); audit for the Bravoh carveout sentinel. If absent, ADD a "Scope: vibemix vs Bravoh" section: ~1 paragraph stating "vibemix is Apache-2.0. The Bravoh-side Gemini proxy at `api.altidus.world` is closed-source by design — it is the commercial wedge that funds Bravoh's main product. Contributions to vibemix should target the client-side code in this repo; proxy bugs / quota issues are reported via `SECURITY.md` and triaged by the Bravoh team."
- **CODE_OF_CONDUCT.md** — already exists (1.6k); presence-test only (no audit).
- **SECURITY.md** — already exists (4.0k); presence-test only (no audit, already covers Bravoh disclosure channel per file mtime 2026-05-16 / Phase 33 work).
- **README link audit** — README must reference all four (search for `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md` + `MAINTAINERS.md`). Add a one-line "Community" section to README if any link is missing.
- **Presence test shape** — `tests/repo/test_oss_presence.py` (NEW or extended if exists):
  - `test_required_oss_files_exist` — asserts each of the 4 files exists at repo root, is ≥ 200 bytes, and is referenced ≥ once in README.md.
  - `test_contributing_has_bravoh_carveout` — greps `CONTRIBUTING.md` for the sentinel string "Bravoh proxy is closed-source by design" (exact match; rename triggers test failure → forces a deliberate update).

### Client-Side Proxy Fallback (OSS-02 — vibemix side)
- **Fallback surface** — the pill (primary per v5.0 P62) AND the mascot (secondary per v5.0 P62) surface "Co-host unavailable this session" when:
  - Proxy returns 5xx (502 / 503 / 504),
  - Proxy times out (any `httpx.TimeoutException`),
  - Proxy returns a non-JSON body when JSON expected,
  - Proxy connection refused (network down / proxy down).
- **NOT triggered by** 4xx (auth/quota — those surface their own per-error messaging from existing code per `runtime/session_loop.py` proxy_client paths; per v3.x SHIP-CUT). 429 also has its own existing path (rate-limit-specific message — must not be conflated with "unavailable").
- **Implementation locus** — wrap the existing `proxy_client.py` (in `src/vibemix/agent/`) generate call in a `try/except` that catches the 4 trigger classes above, returns a sentinel `ProxyUnavailable` exception, and pushes a single pill emission `{"type": "pill", "text": "Co-host unavailable this session", "severity": "warn"}` + mascot mood change. NO retries (`gsd-autonomous fully` + anti-slop: refusing to lie when grounding is missing is on-thesis; silently retrying = slop).
- **Mascot mood** — re-use the existing "muted" / "offline" mood from v5.0 P62 mascot states; no new mood asset needed.
- **Coach loop behavior on fallback** — the coach loop continues running (state collection, evidence packets) but skips LLM emission for the duration the proxy is unavailable. Re-tries every 60s (the existing session loop poll cadence) via a single canary call to `/health` (NOT a real LLM call). When `/health` returns 200, the fallback flag clears and a single one-time pill emission `{"text": "Co-host back online"}` lands; LLM emissions resume.
- **Test shape** — `tests/integration/test_proxy_fallback.py` (NEW), marker `@pytest.mark.integration`:
  - `test_proxy_503_emits_unavailable_pill` — mocks proxy as 503, runs one coach turn, asserts the pill emission shape (text + severity) + NO coach line emitted.
  - `test_proxy_timeout_emits_unavailable_pill` — mocks `httpx.TimeoutException`, asserts the same emission.
  - `test_proxy_connection_refused_emits_unavailable_pill` — mocks `httpx.ConnectError`, asserts the same emission.
  - `test_proxy_recovery_emits_back_online_pill` — proxy returns 503 → 200, asserts the "back online" one-time emission.
- **Server-side hardening route** — `KAAN-ACTION-LEGAL.md §V7-PROXY` cluster (NEW), mirroring the §V7-LIVE cluster shape (6 sections: Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off block). The fix path pre-stages:
  - Per-install-UUID rate limit middleware (token bucket; recommended: `slowapi` or in-house FastAPI dependency; the Bravoh repo is FastAPI per CLAUDE.md).
  - Prom `/metrics` endpoint with `rate_limit_hits_total{install_uuid="..."}` + `tokens_remaining_bucket{install_uuid="..."}`.
  - Sentry DSN environment variable wired in the Bravoh service config.
  - Verification commands: `curl https://api.altidus.world/metrics` returns Prom-formatted body; synthetic abuse with a test install-UUID triggers a 429 within 60s.

### BYO-Key Documentation (OSS-03)
- **`docs/byo-key.md`** — NEW file, ≤200 lines. Sections (in order):
  - "Why BYO" — privacy + cost rationale (your own Gemini quota + bypass Bravoh telemetry).
  - "Get a Gemini API key" — 5-line walk to https://aistudio.google.com/apikey + free-tier reminder.
  - "Set the env vars" — three-platform table (macOS `.zshrc`, Windows PowerShell `$env:`, Linux `.bashrc`):
    - `VIBEMIX_LLM_MODE=direct` (the existing code path at `runtime/session_loop.py:847` — `proxy` mode is the default; `direct` opts out).
    - `GEMINI_API_KEY=<your-key>`.
  - "Verify" — `uv run python -m vibemix --health` smoke (or equivalent — check if `--health` exists or pick a runnable smoke; if none, document the `uv run python -c "from vibemix.agent.client import build_client; build_client(); print('OK')"` line).
  - "Switch back to Bravoh proxy" — `unset VIBEMIX_LLM_MODE` + `unset GEMINI_API_KEY`, restart vibemix.
  - "Privacy note" — BYO mode sends data direct to `generativelanguage.googleapis.com` (Google's TOS apply); no Bravoh telemetry hop.
  - "Limits" — Gemini free tier rate limits, what happens on quota exhaustion (the existing 429 path fires, surfaces its own message — see OSS-02 fallback behavior).
- **`tests/repo/test_byo_doc_shape.py`** (NEW) — pins the 6 required sections, the 2 env var names, and the `aistudio.google.com/apikey` URL. Doc rot → test fails.
- **Fresh-account walk** — routes to `KAAN-ACTION-LEGAL.md §V7-LIVE-11 — BYO fresh-account walk` cluster (NEW), discharge artifact = `docs/byo-key-walk.md` (Kaan's account / friend's account walk-through with screenshots). Soft Kaan-discharge under autonomous mode — does not gate engineering close.

### Release Publish Surface (OSS-04 — routes to §SHIP-V4)
- **Engineering deliverable** — verify `bash scripts/launch/cut_release.sh --dry-run v0.1.0-rc1` exits 0 today on the current tree (no regressions from P39 ship); if any gate has drifted, fix the drift. Verify the non-dry-run path `bash scripts/launch/cut_release.sh v0.1.0-rc1` would gate correctly when signatures land (verified by reading the script's gate logic, not by running it — running without signatures = expected FAIL).
- **§SHIP-V4 update** — append a one-paragraph "v7.0 OSS-04 autonomous-mode route" sub-section to the existing `KAAN-ACTION-LEGAL.md §SHIP-V4` cluster (line 3389), containing:
  - The exact pre-staged invocation: `bash scripts/launch/cut_release.sh v0.1.0-rc1`.
  - The post-pre-flight Kaan command (lifted from cut_release.sh's stdout block): the `gh release create v0.1.0-rc1 --repo bravoh/vibemix --title "vibemix v0.1.0-rc1" --notes-file CHANGELOG-v0.1.0-rc1.md --draft --target main dist/*.dmg dist/*.msi dist/*.pkg dist/*.exe` invocation.
  - The hard-guard reminder: cut_release.sh NEVER invokes `gh release create` itself — the hand-on-trigger is Kaan, post-pre-flight.
  - The v4.0-closes-alongside note: when this fires, `MILESTONES.md` v4.0 entry flips to "SHIPPED" with the published release URL.
- **`docs/release-process.md` update** — add a "Autonomous-mode release path" section: under `gsd-autonomous fully`, OSS-04 ships engineering-complete in v7.0 via §SHIP-V4 deferral; the actual cut is Kaan's clock; the test surface for the deferral is `tests/repo/test_ship_v4_section_exists.py` (NEW — pins §SHIP-V4 section in KAAN-ACTION-LEGAL.md + the v7.0 OSS-04 sub-section + the exact pre-staged invocation string).
- **NO source edits to `cut_release.sh`** — the script was P39-verified and §SHIP-CUT-locked; touching it requires its own dedicated phase.

### Homebrew + Scoop Scaffolds (OSS-05)
- **`packaging/homebrew/Formula/vibemix.rb`** (NEW, ≤60 lines) — Ruby Formula class with deterministic URL/SHA placeholders pointing at `https://github.com/bravoh-ai/vibemix/releases/download/v0.1.0-rc1/vibemix-v0.1.0-rc1-macos.dmg` + SHA256 = sentinel `0000…0000` (replaced at real-cut time by a `scripts/launch/sync_packaging.sh` helper — NEW, ≤40 lines). Formula uses standard `class Vibemix < Formula` pattern with `desc` / `homepage` / `url` / `sha256` / `version` / `install do`. Pinned by `tests/repo/test_packaging_scaffolds_present.py`.
- **`packaging/scoop/vibemix.json`** (NEW, ≤50 lines) — JSON manifest with `homepage` / `description` / `version` / `architecture: { 64bit: { url: ..., hash: sha256:... } }` / `bin: ["vibemix.exe"]` / `checkver` block / `autoupdate` block. Same sentinel SHA pattern. Pinned by the same test.
- **CI workflow** — `.github/workflows/packaging-audit.yml` (NEW, ≤90 lines, mirrors `full-test-matrix.yml` shape from 67P04 — SHA-pinned actions, `permissions.contents: read`, fork-PR safe, fail-fast: false, timeout-minutes: 15). Two jobs:
  - `brew-audit` (runs-on `macos-14`) — `brew install` if not cached, then `brew audit --new packaging/homebrew/Formula/vibemix.rb`. Pass = exit 0.
  - `scoop-checkver` (runs-on `windows-latest`) — `scoop install` if not cached, then `scoop checkver -d packaging/scoop/vibemix.json` against a deterministic fixture (since OSS-04 isn't live yet, point at the existing P39 dry-run artifacts in `dist/` if present, OR a `packaging/fixtures/v0.1.0-rc1-stub.zip` checked in).
- **`docs/release-process.md` section** — add "Homebrew + Scoop publish — split rationale" section explaining: the scaffolds ship in v7.0; the actual tap/bucket publish (`git push bravoh-ai/homebrew-tap` + `git push bravoh-ai/scoop-bucket`) is a user-visible install upgrade that earns its own milestone, gated on the v0.1.0 (non-RC) tag.
- **Anti-drift** — `tests/repo/test_packaging_scaffolds_present.py` pins:
  - `packaging/homebrew/Formula/vibemix.rb` exists, class name `Vibemix`, URL contains `bravoh-ai/vibemix/releases/download`.
  - `packaging/scoop/vibemix.json` exists, valid JSON, `bin` includes `vibemix.exe`.
  - `.github/workflows/packaging-audit.yml` exists, contains both `brew-audit` and `scoop-checkver` job names.
  - `docs/release-process.md` contains the "Homebrew + Scoop publish — split rationale" section header.

### Plan Decomposition (Recommended Wave Split)
- **Wave 0 — Repo-presence baseline** (1 plan, fast): MAINTAINERS.md + CONTRIBUTING.md carveout audit + `test_oss_presence.py`. Single atomic commit pattern (per the 68P01 precedent). DEV-01 / OSS-01 closed.
- **Wave 1 — BYO doc + presence test** (1 plan): `docs/byo-key.md` + `tests/repo/test_byo_doc_shape.py` + §V7-LIVE-11 cluster. OSS-03 closed engineering-side.
- **Wave 2 — Client-side proxy fallback** (1 plan, biggest): `proxy_client.py` try/except + pill emission + mascot mood hookup + `test_proxy_fallback.py` 4-test parametrize + §V7-PROXY cluster. OSS-02 closed engineering-side (server-side rides §V7-PROXY).
- **Wave 3 — Packaging scaffolds** (1 plan): `packaging/homebrew/Formula/vibemix.rb` + `packaging/scoop/vibemix.json` + `packaging-audit.yml` workflow + `sync_packaging.sh` helper + `test_packaging_scaffolds_present.py` + `docs/release-process.md` split-rationale section. OSS-05 closed engineering-side.
- **Wave 4 — §SHIP-V4 wiring** (1 plan, small): cut_release.sh `--dry-run v0.1.0-rc1` re-verify + §SHIP-V4 v7.0 sub-section append + `docs/release-process.md` autonomous-mode-route section + `test_ship_v4_section_exists.py`. OSS-04 closed (routes to Kaan-clock).

Total: 5 plans, mirrors Phase 67/68's Wave 0..4 cadence. Each wave is independently shippable (no inter-wave dependencies).

### Claude's Discretion
- Exact wording of pill / mascot fallback message — pick "Co-host unavailable this session" as the default per the success criterion text; tune during planning if a shorter form lands better with the existing v5.0 pill style.
- Whether to bundle the CONTRIBUTING.md carveout-add into Wave 0 or its own commit — pick whichever feels cleaner during planning.
- Exact form of the `/health` canary endpoint check in OSS-02 recovery path — if the proxy doesn't have one today, document it as a §V7-PROXY discharge item and skip the recovery emission until then (failure-case = the next real LLM call surfaces the recovery once the proxy is back).
- File names for any new contributor-facing artifacts — follow Phase 68 precedent (snake_case for scripts, kebab-case for .md).
- Whether to extract the cut_release.sh `--dry-run v0.1.0-rc1` verification into its own `tests/release/test_cut_release_dry_run_green.py` (pinned in CI) or just run it manually as part of the Wave 4 SUMMARY — pick during planning. The CI version is stronger anti-drift but adds a slow test (the script runs all gates).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/vibemix/agent/proxy_client.py`** — existing Bravoh proxy client wrapper; the OSS-02 fallback wraps this.
- **`src/vibemix/runtime/session_loop.py:847-862`** — existing `VIBEMIX_LLM_MODE` branch (`direct` vs `proxy`), already wired to honour BYO via `GEMINI_API_KEY`. OSS-03 documents what the code already does.
- **`src/vibemix/runtime/sec_check.py`** — references `api.altidus.world` / `api.bravoh.altidus.world` (3 URLs); reading-only, no edits needed for Phase 69.
- **`scripts/launch/cut_release.sh`** — P39-verified, `--dry-run v0.1.0-rc1` exits 0 today; touched only for verification in Wave 4, not edited.
- **`KAAN-ACTION-LEGAL.md §SHIP-V4`** (line 3389) — existing cluster; Wave 4 appends a v7.0 OSS-04 sub-section, does NOT create a new top-level cluster.
- **`KAAN-ACTION-LEGAL.md §V7-LIVE` template** (lines 3653, 3889, 3938, 3995, 4052) — 6-section cluster shape (Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off block). Wave 1 (§V7-LIVE-11) + Wave 2 (§V7-PROXY) mirror this template verbatim.
- **`.github/workflows/full-test-matrix.yml`** (Phase 67P04) — SHA-pinned action pattern + concurrency cancel-in-progress + security-correct trigger shape; Wave 3's `packaging-audit.yml` lifts the same template.
- **`tests/repo/test_readme_shape.py` + `tests/repo/test_no_silent_skips.py`** — existing presence-test patterns; Wave 0 / 1 / 3 / 4 test files follow the same shape (AST-walk or grep-based asserts, ≤150 lines each).
- **Phase 68 plan/wave cadence** — 5 waves (P01 .. P05), each independently shippable, atomic commits per task; Phase 69's recommended decomposition mirrors this.

### Established Patterns
- **Pillar-sized phases** — 4-pillar v7.0 has one phase per pillar; each phase decomposes into ~5 waves (per Phase 68 precedent: 68P01..68P05). Plan granularity is "single deliverable per wave", not "task per file".
- **Anti-drift via repo-presence tests** — every new artifact (doc / formula / workflow) gets a `tests/repo/test_<name>_*.py` shape that fails red on deletion or shape change (per Plan 67P03 `test_no_silent_skips.py` / `test_no_silent_flakes.py` + Plan 68P02 `test_profile_contracts.py` precedent).
- **Autonomous-mode routes** — KAAN-discharge surfaces go to `KAAN-ACTION-LEGAL.md` clusters (§V7-LIVE-NN / §SHIP-V4 / §V7-PROXY), each cluster mirrors the 6-section template; engineering ships green; live discharge rides Kaan's clock.
- **Zero `src/vibemix/{coach,llm,state,memory,recall,decks,grounding}/` edits except where strictly required** — Phase 69 touches `src/vibemix/agent/proxy_client.py` (OSS-02 try/except) and possibly `src/vibemix/runtime/ws_bus.py` (pill emission); no coach prompts, no evidence sources, no reaction-path modules. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by construction.
- **CI workflow shape** — SHA-pinned actions, `permissions.contents: read`, `on: pull_request` (NOT `pull_request_target` — fork-PR security), `fail-fast: false`, `timeout-minutes: NN`, workflow-prefixed concurrency cancel-in-progress group.

### Integration Points
- **CONTRIBUTING.md** — repo root, referenced from README. Wave 0 audits + optionally adds carveout section.
- **MAINTAINERS.md** — NEW at repo root. Wave 0 ships.
- **README.md** — Wave 0 adds a "Community" section linking the four OSS docs if not already linked.
- **`docs/byo-key.md`** — NEW; Wave 1 ships. README does NOT link it directly (BYO is for self-hosters; docs/ is the discovery path).
- **`docs/release-process.md`** — Waves 3 + 4 each append a section (split rationale + autonomous-mode-route).
- **`src/vibemix/agent/proxy_client.py`** — Wave 2 wraps the generate call in try/except.
- **`src/vibemix/runtime/ws_bus.py`** (likely) — Wave 2 adds a pill emission helper for the "Co-host unavailable" message if not already exposed.
- **`KAAN-ACTION-LEGAL.md`** — Waves 1, 2, 4 append (§V7-LIVE-11, §V7-PROXY, §SHIP-V4 sub-section).
- **`packaging/`** — NEW directory; Wave 3 creates `homebrew/Formula/vibemix.rb` + `scoop/vibemix.json`.
- **`.github/workflows/packaging-audit.yml`** — NEW; Wave 3 ships.
- **`scripts/launch/sync_packaging.sh`** — NEW; Wave 3 ships (helper for real-cut SHA replacement).
- **`tests/repo/test_oss_presence.py`** + `test_byo_doc_shape.py` + `test_packaging_scaffolds_present.py` + `test_ship_v4_section_exists.py` — NEW; one per wave.
- **`tests/integration/test_proxy_fallback.py`** — NEW; Wave 2 (`@pytest.mark.integration`, mirrors Phase 68 hot-plug / audio-backend matrix shape).

</code_context>

<specifics>
## Specific Ideas

- **Bravoh carveout language** — exact sentinel string: `"the Bravoh proxy is closed-source by design"` (lowercase "the", not capitalized — keeps the prose voice). Tested via grep.
- **Fallback message** — `"Co-host unavailable this session"` (exact case + spacing — pinned by `test_proxy_fallback.py`).
- **Recovery message** — `"Co-host back online"` (one-time emission when proxy returns 200 from /health canary).
- **CHANGELOG file** — `CHANGELOG-v0.1.0-rc1.md` at repo root (per cut_release.sh's fallback path; the template at `scripts/launch/changelog_template.md` is the source if the dedicated file isn't created — Wave 4 SUMMARY notes which path is taken).
- **§V7-PROXY cluster name** — `§V7-PROXY` (not `§V7-PROXY-HARDENING` — short form mirrors §SHIP-V4, §V7-LIVE).
- **§V7-LIVE-11 cluster name** — `§V7-LIVE-11 — BYO fresh-account walk` (continues the 11-12-13 sequence from 67P02..68P05's §V7-LIVE-01..10).
- **`packaging/` directory** — top-level under repo root (not `dist/packaging/` — `packaging` is OSS-convention for static manifests; `dist/` stays for built artifacts).

</specifics>

<deferred>
## Deferred Ideas

- **Actual tap/bucket publish** (`git push bravoh-ai/homebrew-tap` + `git push bravoh-ai/scoop-bucket`) — split off explicitly per OSS-05 success criterion; earns its own future milestone gated on v0.1.0 (non-RC) tag.
- **Real `gh release create v0.1.0-rc1`** — gated on Apple Dev Agreement (Francesco) + SignPath OSS Foundation cert (Kaan); routes to §SHIP-V4 under autonomous mode; closes alongside v4.0 "SHIP" when fires for real.
- **Server-side proxy production hardening source edits** — lives in the separate Bravoh ops repo (not vibemix); routes to §V7-PROXY for Kaan's coordination clock.
- **BYO fresh-account walk** — Kaan or trusted user runs the doc on a fresh Mac/Win account, records `docs/byo-key-walk.md`; routes to §V7-LIVE-11; soft Kaan-discharge under autonomous mode.
- **`tests/release/test_cut_release_dry_run_green.py`** — slow-CI anti-drift wrap of `cut_release.sh --dry-run v0.1.0-rc1` (decided during Wave 4 plan whether to ship the test or run manually).
- **Apache-2.0 NOTICE file curation** — the `cut_release.sh` Gate-2 references it as a release asset; if missing, route to a Wave 4 sub-task OR a §SHIP-V4 cluster sub-item. Decided during planning.
- **README "Community" section content** — if README already links all four OSS docs, no change; if missing, Wave 0 adds a single line per missing doc. Decided during planning.

</deferred>
