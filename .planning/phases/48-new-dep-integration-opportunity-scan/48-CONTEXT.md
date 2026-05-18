<phase>48</phase>
<phase_name>New-Dep + Integration Opportunity Scan</phase_name>
<date>2026-05-18</date>
<mode>auto (gsd-autonomous fully)</mode>

<domain>
Surface every v3.1 candidate dep / integration on a single dated discovery artifact, rate each with the 4-color rubric (Red-constraint / Red-risk / Yellow-defer / Green-adopt), auto-flag constraint-violators Red via memory-enumerated exclusion set, emit ADR sidecars per Green adoption, produce zero (or near-zero) new runtime deps as v3.1 steady state. Build-time / test-time / docs-only surface — zero runtime POC edits.
</domain>

<canonical_refs>
**REQUIREMENTS:**
- `.planning/REQUIREMENTS.md` § OPP — REQ-IDs OPP-01..OPP-06 (the 6 lines this phase satisfies)
- `.planning/ROADMAP.md` § Phase 48 — goal + success criteria + invariants + Phase 49 hand-off

**Research baseline (read first):**
- `.planning/research/STACK.md` § Bucket 3 (lines for `Dante Via`, `Loopback Audio`, `Soundflower`, `Voicemeeter Banana`, `pyrekordbox`, `mixxx-osc`, `prodj-link`, `beat-this`, `cdj-link-py`, Numark/Hercules controllers, macOS 26+, Apple Silicon perf, Win11 24H2 WASAPI) — full verdict table already drafted; planner ports verbatim into `docs/dep-opportunities/2026-05-scan.md`
- `.planning/research/FEATURES.md` § OPPORTUNITY-SCAN — table-stakes / differentiator / anti-feature framing
- `.planning/research/ARCHITECTURE.md` § 6 — `docs/dep-opportunities/<YYYY-MM>-scan.md` + ADR sidecar pattern lives in here
- `.planning/research/PITFALLS.md` § 6 — opportunity-scan pitfalls (scope creep, Linux-only transitive, multi-provider AI)
- `.planning/research/SUMMARY.md` — v3.1 TL;DR (zero new runtime deps is the predicted outcome)

**Phase 46 outputs to EXTEND (not redesign):**
- `scripts/audit/dep_ratings.yaml` — extend with new top-level `opportunity_evaluations:` block
- `scripts/audit/dep_ratings_schema.json` — extend with `opportunity_evaluations` property; preserve existing schema (python/rust/js/decisions intact)
- `scripts/audit/gen_audit_md.py` — touch ONLY if README cross-link surface requires it; otherwise leave Phase 46 generator unchanged
- `docs/AUDIT.md` — Phase 46 owner; this phase writes a NEW sibling doc at `docs/dep-opportunities/2026-05-scan.md`

**Invariant-enforcement neighbors (do NOT modify; sibling-extend instead per `feedback_no_gsd_orchestra_for_trivial_tweaks` + Phase 47-resume sibling-script pattern):**
- `scripts/launch/check_no_ai_slop.py` — exports `AI_SLOP_BLOCKLIST` + `\bdeeply\s+\w+` regex; CONTRACT-PINNED to `scripts/dayzero/launch_copy/`. DO NOT widen the existing script's target paths. Create `scripts/audit/check_no_slop_opp.py` as a sibling that imports `AI_SLOP_BLOCKLIST` from `scripts.launch.check_no_ai_slop` and applies the same gate to `docs/dep-opportunities/`.
- `.github/workflows/anti-slop.yml` (if present) — sibling target wired alongside, not into the same job.

**ADR / Decisions location:**
- `.planning/decisions/` — top-level project-wide ADRs; emit `DEP-OPP-<N>-<slug>.md` per Green adoption. Existing tenant: `P85-OVERRIDE-RETIRED.md`.

**Memory-enumerated exclusion set (verbatim in scan plan per OPP-03):**
- `feedback_no_clap_use_gemini_embedding` — "vibemix is Gemini-only; never propose CLAP / LAION-CLAP / MERT / OpenL3 even when research recommends it."
- `feedback_no_scope_creep_clean_utility` — "OUT: stem separation, CLAP, multi-provider AI, enterprise features. Optimize for minimum useful surface not feature parity."
- `project_one_click_install_hard_req` — "Mac+Win, app opens → auto-downloads deps → configures audio → ready. Every dep choice rated green/yellow/red on install impact."

**Yellow-defer destination:**
- `.planning/research/v3-buckets/` — Yellow candidates carry forward here for v3.x re-eval (per OPP-05). Existing tenants establish the pattern.
</canonical_refs>

<spec_lock>
**Locked requirements (from `.planning/REQUIREMENTS.md` § OPP — do NOT re-decide):**
- OPP-01: `docs/dep-opportunities/2026-05-scan.md` exists with candidate inventory.
- OPP-02: 4-color rubric (Red-constraint / Red-risk / Yellow-defer / Green-adopt) applied to every candidate.
- OPP-03: Exclusion set quoted verbatim from `feedback_no_clap_use_gemini_embedding` / `feedback_no_scope_creep_clean_utility` / `project_one_click_install_hard_req`; constraint-violators auto-Red.
- OPP-04: ADR sidecar `.planning/decisions/DEP-OPP-<N>-<slug>.md` per Green adoption.
- OPP-05: Zero (or near-zero) new runtime deps documented; Yellow → `.planning/research/v3-buckets/`.
- OPP-06: OBS browser-source mascot path docs-only in README + `docs/integrations/obs-browser-source.md`.

**Locked success criteria (from `.planning/ROADMAP.md` § Phase 48):**
1. Scan markdown exists + scan plan quotes exclusion set verbatim + `scripts/audit/scan_opportunities.py` auto-flags constraint-violators Red.
2. ADR sidecar per Green adoption with decision + rationale + integration plan + rollback path.
3. v3.1 final scan outcome = zero (or near-zero) new runtime deps; Yellow forwarded.
4. OBS browser-source landed as docs-only (no new runtime code).
5. `dep_ratings.json` schema extended with `opportunity_evaluations` block.

**Locked invariants (from ROADMAP Phase 48 invariants line):**
- Anti-slop blocklist gate extended to `docs/dep-opportunities/` (15-token + `\bdeeply\s+\w+`).
- ModelRouter seam preserved — scan output MUST NOT inline `gemini-*` literals.
- POC immutability — `cohost*.py` + `mascot.html` not edited.
- `feedback_no_scope_creep_clean_utility` upheld by auto-Red on stem separation / CLAP / multi-provider AI / DAW candidates.

Discussing implementation decisions only — WHAT to build is fully locked.
</spec_lock>

<decisions>

### Decision 1 — Single scan artifact at `docs/dep-opportunities/2026-05-scan.md`, NOT a multi-file dir tree

[auto] Discovery surface: ONE markdown file dated `2026-05-scan.md` (per OPP-01 literal path). Sibling scans in future months land at `docs/dep-opportunities/YYYY-MM-scan.md` (the ARCHITECTURE.md § 6 pattern). No per-candidate sub-files; each candidate is a row in the rubric table inside the single file.

**Rationale:** Per ARCHITECTURE.md § 6 (`docs/dep-opportunities/<YYYY-MM>-scan.md` is the contract); per `feedback_no_gsd_orchestra_for_trivial_tweaks` (avoid file-explosion theatre). The scan is a snapshot at a point in time — one file is the right grain.

### Decision 2 — `dep_ratings.yaml` extended with top-level `opportunity_evaluations:` block (NOT merged into per-ecosystem maps)

[auto] Schema extension keeps Phase 46's `python:` / `rust:` / `js:` ecosystem maps + `decisions:` array INTACT and BACKWARD-COMPATIBLE. Adds a 5th top-level key:

```yaml
opportunity_evaluations:
  - id: "DEP-OPP-01"
    date: "2026-05-18"
    candidate: "OBS browser-source mascot path"
    category: "integration"
    rating: "green-adopt"
    install_impact: "green"
    rationale: "Tauri webview WS port 8765 already serves; docs-only adoption."
    adr_sidecar: ".planning/decisions/DEP-OPP-01-obs-browser-source.md"
    integration_surface: "docs-only"
    rejected_constraints: []
  - id: "DEP-OPP-02"
    candidate: "CLAP / LAION-CLAP / MERT / OpenL3"
    rating: "red-constraint"
    rejected_constraints:
      - memory: "feedback_no_clap_use_gemini_embedding"
        quote: "vibemix is Gemini-only; never propose CLAP..."
  # ...one row per candidate enumerated below
```

`rating` enum extends to `green-adopt | yellow-defer | red-constraint | red-risk` (NOT the original `green | yellow | red` — this is a different axis: the original is install-impact only, this is the 4-color outcome rubric per OPP-02). Both axes co-exist: each Green-adopt row ALSO carries `install_impact: green|yellow|red` from the Phase 46 axis.

**Rationale:** Phase 46 schema is `additionalProperties: false` at the top level — extending requires a schema bump. New top-level key avoids polluting the python/rust/js maps with non-package entries (Mixxx OSC, OBS, etc. are integrations, not Python deps).

### Decision 3 — `dep_ratings_schema.json` extended; `additionalProperties: false` preserved on root, new key added to `required`

[auto] Schema delta:
- Add `"opportunity_evaluations"` to root `required` array (so an empty array `[]` is still a valid scan-not-yet-run state, but the key MUST be present).
- Add `properties.opportunity_evaluations` referencing new `$defs.opportunity_entry` with required fields: `id`, `date`, `candidate`, `category`, `rating`, `install_impact`, `rationale`, `integration_surface`, `rejected_constraints` (array, possibly empty), `adr_sidecar` (string, possibly empty for non-Green rows).
- `rating` enum: `["green-adopt", "yellow-defer", "red-constraint", "red-risk"]`.
- `category` enum: `["python-dep", "rust-dep", "js-dep", "integration", "os-support", "hardware-support"]`.
- `integration_surface` enum: `["runtime", "build-time", "test-time", "docs-only", "ci-only"]`.
- Existing `python`/`rust`/`js`/`decisions` defs UNTOUCHED.

**Rationale:** Backward-compatible additive schema bump. Phase 49 installer companion reads ONLY Green-adopt rows from `opportunity_evaluations` (success criterion 5: "Phase 49 installer companion fetches drivers from the Green-rated subset ONLY"); explicit `integration_surface` lets the companion filter to driver-relevant rows without misclassifying docs-only OBS path as a fetchable dep.

### Decision 4 — Sibling anti-slop checker at `scripts/audit/check_no_slop_opp.py`, NOT a target-path extension of `scripts/launch/check_no_ai_slop.py`

[auto] Per Phase 47-resume sibling-script pattern (and the explicit prompt-level guidance: "if extending the anti-slop scanner — write phase-scoped sibling scripts ... instead of redesigning shared tooling mid-execute"):

- NEW: `scripts/audit/check_no_slop_opp.py` — imports `AI_SLOP_BLOCKLIST` from `scripts.launch.check_no_ai_slop` (single source of truth preserved), applies same 15-token + `\bdeeply\s+\w+` regex gate to `docs/dep-opportunities/*.md`. Standalone exit 0/1; argparse `--dir` for future-month extensibility.
- NEW: `.github/workflows/opp-anti-slop.yml` (or extend `dep-audit.yml` from Phase 46 — planner picks per inspection of `dep-audit.yml` job count) — wires the sibling check.
- DO NOT TOUCH: `scripts/launch/check_no_ai_slop.py` (contract-pinned to `scripts/dayzero/launch_copy/`).

**Rationale:** Phase 47 stall root cause was mid-execute redesign of a contract-pinned shared script. Sibling-script avoids it entirely. Per-script stall budget per the autonomous-mode anti-stall discipline.

### Decision 5 — `scripts/audit/scan_opportunities.py` is the auto-Red engine, NOT a free-form generator

[auto] Per OPP-03 success criterion ("auto-flags any candidate that names CLAP / MERT / OpenL3 / a non-Gemini provider / stem-sep / DAW as Red-constraint"):

`scripts/audit/scan_opportunities.py` is a VALIDATOR, not a content writer. Pipeline:
1. Parse `docs/dep-opportunities/2026-05-scan.md` candidate table (markdown table with columns: `candidate | category | rating | rationale | adr_sidecar`).
2. Cross-check each row's `candidate` string against a hard-coded `CONSTRAINT_VIOLATORS` tuple (CLAP, LAION-CLAP, MERT, OpenL3, Anthropic API, OpenAI direct, GPT-4, Demucs, Spleeter, Spleeter-as-a-service, Ableton API, FL Studio API, Logic Pro API, ProDJ Link, cdj-link-py, prodj-link, Dante Via, Loopback Audio, Soundflower, Linux-only-libs).
3. If a `CONSTRAINT_VIOLATORS` match is found in a row's `candidate` but the row's `rating` is NOT `red-constraint`, exit 1 with stderr naming the offending row. (The scan markdown author MUST explicitly mark these Red.)
4. Validate every `green-adopt` row has a non-empty `adr_sidecar` path that exists on disk under `.planning/decisions/`.
5. Validate `dep_ratings.yaml` `opportunity_evaluations` block is in sync with the markdown table (md ↔ yaml parity gate; Phase 46 `check_audit_freshness.sh` is the prior-art pattern).

CI surfaces this via the same `dep-audit.yml` workflow as Phase 46 (extend Phase 46's workflow with a new job, OR add the call to an existing job — planner picks per Phase 46 workflow shape).

**Rationale:** Auto-Red is a verification gate, not a content writer — the scan markdown is human-curated (lifted verbatim from STACK.md § Bucket 3). The script ENFORCES that constraint violators carry the Red label. Same pattern as `check_audit_freshness.sh` (verifies AUDIT.md ↔ lockfile parity without generating either).

### Decision 6 — OBS browser-source is the ONE expected Green-adopt; ADR + integration doc + README cross-link

[auto] Per the prompt-level expected outcome + OPP-06 + memory `project_mascot_as_vtuber_personality_surface`:

- ADR: `.planning/decisions/DEP-OPP-01-obs-browser-source.md`
  - Decision: "Adopt OBS browser-source mascot path as docs-only integration."
  - Rationale: "Tauri webview already serves WS at `ws://127.0.0.1:8765` (mascot bus); OBS browser-source plugin can subscribe directly. Zero new runtime code."
  - Integration plan: "User points OBS browser-source to `http://127.0.0.1:8765/mascot` (the existing Tauri webview mascot route); OBS captures the rendered Three.js canvas as an overlay."
  - Rollback: "Delete `docs/integrations/obs-browser-source.md` + README cross-link; no code surfaces to revert."
- Integration doc: `docs/integrations/obs-browser-source.md` — step-by-step OBS Studio setup + screenshots + troubleshooting (port 8765 firewall, scene-aspect-ratio guidance). Passes anti-slop blocklist.
- README cross-link: a single short paragraph under existing README "Integrations" or "Streaming" section (planner inspects current README structure to pick the right anchor) with link to the docs/integrations file. README change passes existing anti-slop + hero-lock CI.

NO mascot code changes. NO new IPC. NO new Tauri webview routes (the mascot route already exists per v3.0 baseline).

**Rationale:** Per memory + OPP-06: "no new runtime code required (docs-only adoption)". The mascot bus port 8765 is the existing v3.0 surface — OBS browser-source plugs into it without any vibemix-side work.

### Decision 7 — Yellow-defer carry-forward via stub files in `.planning/research/v3-buckets/`

[auto] Per OPP-05: Yellow candidates carry forward. Each Yellow-defer row gets a single stub markdown at `.planning/research/v3-buckets/v3.x-<slug>.md` with:
- Candidate name + category
- Why deferred (link back to scan row)
- Re-eval trigger (memory + roadmap conditions that would flip it Green)
- Originating scan: `docs/dep-opportunities/2026-05-scan.md`

Expected Yellow-defer set per STACK.md § Bucket 3 + memory `project_v2_open_candidates`:
- `v3.x-mixxx-osc.md` (Mixxx OSC controller adapter)
- `v3.x-controller-map-transpiler.md`
- `v3.x-pyrekordbox-depth.md` (deeper Rekordbox library features)
- `v3.x-beat-this.md` (Rust beat-grid sidecar)
- `v3.x-voicemeeter-banana.md` (Win virtual audio extended; advanced-user wizard tier)
- `v3.x-numark-hercules-controllers.md` (controller library expansion via map transpile path)
- `v3.x-macos-26-support.md` (next-major-OS verification, contingent on release timing)
- `v3.x-win11-24h2-wasapi-verify.md`

**Rationale:** Existing `.planning/research/v3-buckets/` is the established forward-carry surface; Yellow stubs are the audit-trail mechanism for the "carry forward into v3-buckets/" success criterion.

### Decision 8 — Auto-Red set (explicit candidate list with verbatim memory quote per row)

[auto] Per OPP-03 ("auto-flags any candidate that names CLAP / MERT / OpenL3 / a non-Gemini provider / stem-sep / DAW as Red-constraint"):

Expected Red rows in `docs/dep-opportunities/2026-05-scan.md`:

**Red-constraint (memory violation):**
- CLAP / LAION-CLAP — quote `feedback_no_clap_use_gemini_embedding`: "vibemix is Gemini-only; never propose CLAP/LAION-CLAP/MERT/OpenL3 even when research recommends it."
- MERT — same quote.
- OpenL3 — same quote.
- OpenAI direct API — quote `feedback_no_scope_creep_clean_utility`: "OUT: ... multi-provider AI". (Note: `livekit-plugins-openai` is a TRANSITIVE TTS-proxy fallback, NOT direct OpenAI use — Phase 46 logged it as cull-blocked. Distinct from this Red row which excludes direct OpenAI adoption as a new AI provider.)
- Anthropic API direct — same quote.
- Demucs / Spleeter / stem-sep libs — same memory: "OUT: stem separation".
- Ableton Link / DAW API integration — same memory: "OUT: ... DAW".
- Linux-only deps — project no-Linux constraint (`/Users/ozai/CLAUDE.md` Platforms: macOS + Windows in v1; Linux explicitly excluded).

**Red-risk (install-impact failure):**
- Pioneer ProDJ Link / cdj-link-py / prodj-link — Java runtime + LAN config violates one-click install (`project_one_click_install_hard_req`); wrong market (CDJ hardware, not bedroom DJs).
- Dante Via — commercial ($60), proprietary.
- Loopback Audio — commercial ($99); BlackHole free + open-source.
- Soundflower — abandonware (2014), unsigned; supplanted by BlackHole.
- Auto-Rig Pro — paid ($40) Blender plugin; Mixamo auto-rig free + already scaffolded.

### Decision 9 — Phase 49 hand-off contract: `dep_ratings.yaml::opportunity_evaluations` is the canonical green-set for installer companion

[auto] Per Phase 48 success criterion 5 ("Phase 49 installer companion fetches drivers from the Green-rated subset ONLY (auditable trail from rating → install-time fetch)"):

- Phase 49's `installer/companion/driver_manifest.json` MUST cite an `opportunity_evaluations.id` field for each driver entry (BlackHole, VB-CABLE).
- BlackHole + VB-CABLE are NOT in Phase 48's opportunity scan (they are Phase 49-internal companion-driver concerns per Phase 46 yaml comment line 14: "Driver-level deps ... are Phase 49 installer-companion concerns"). They get their own Phase 49 rating; Phase 48 does NOT pre-rate them.
- The hand-off mechanic: Phase 49 READS Phase 48's `opportunity_evaluations` to confirm "OBS browser-source is docs-only, NOT a fetchable dep" (i.e., negative confirmation). Positive companion fetches in Phase 49 stay scoped to BlackHole + VB-CABLE.

**Rationale:** Phase 48 ≠ driver registry. Phase 49 owns driver pin/fetch — and `feedback_no_scope_creep_clean_utility` blocks Phase 48 from creeping into driver territory.

### Decision 10 — Anti-slop gate extension via sibling script (Decision 4 above is the mechanic)

Already captured under Decision 4. Re-cited here for the CI surface: `dep-audit.yml` from Phase 46 picks up a new job `opp-anti-slop` (or `opp-scan-validate`) that runs `python scripts/audit/check_no_slop_opp.py` + `python scripts/audit/scan_opportunities.py`. Both exit 0 = job green.

</decisions>

<implementation_constraints>

**MUST do:**
- Extend `dep_ratings.yaml` + `dep_ratings_schema.json` with `opportunity_evaluations` block (backward-compatible additive — `python`/`rust`/`js`/`decisions` keys preserved).
- Create `docs/dep-opportunities/2026-05-scan.md` with candidate inventory verbatim from `.planning/research/STACK.md` § Bucket 3 + verbatim memory quotes per Decision 8.
- Create `scripts/audit/scan_opportunities.py` (auto-Red validator + md↔yaml parity gate) + `scripts/audit/check_no_slop_opp.py` (anti-slop sibling) + extend `.github/workflows/dep-audit.yml` (or new `opp-audit.yml` — planner picks).
- Create `.planning/decisions/DEP-OPP-01-obs-browser-source.md` + `docs/integrations/obs-browser-source.md` + README cross-link.
- Create 8 Yellow-defer stubs under `.planning/research/v3-buckets/v3.x-<slug>.md` per Decision 7.
- Anti-slop check must pass on ALL generated prose: scan markdown, ADR, OBS docs, Yellow stubs, commit messages.

**MUST NOT do:**
- Edit `scripts/launch/check_no_ai_slop.py` (contract-pinned to `scripts/dayzero/launch_copy/`).
- Edit `cohost*.py` POC files (POC immutability).
- Edit `mascot.html` (POC immutability).
- Inline `gemini-*` model literals in scan / ADR / docs (ModelRouter seam).
- Add new runtime Python/Rust/JS deps (the Green outcome is docs-only OBS).
- Add new IPC wrappers (38-wrapper schema frozen).
- Push to remote / create PRs / force-push.
- Modify Phase 46's `python:` / `rust:` / `js:` / `decisions:` sections of `dep_ratings.yaml`.
- Touch `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` paths (privacy rule).

**Worktree Step-0 invariant (per memory `feedback_worktree_must_sync_main_first`):**
- Every subagent prompt MUST include Step-0 `git fetch origin main && git merge origin/main --no-edit` block + verify. Plan-checker rejects any plan lacking this.

**Per-plan stall budget:**
- If a plan's check command can't complete in ~5 minutes, defer the plan with a Kaan-action note in STATE.md + plan's SUMMARY.md. Do NOT let a single plan stall the whole phase.

</implementation_constraints>

<code_context>

**Reusable assets:**
- Phase 46 `scripts/audit/gen_audit_md.py` pattern — reads `dep_ratings.yaml`, joins versions/licenses from lockfile, writes `docs/AUDIT.md`. Phase 48's `scan_opportunities.py` mirrors the pattern (read yaml + scan md, validate parity, exit 0/1).
- Phase 46 `scripts/audit/check_audit_freshness.sh` pattern — verifies AUDIT.md ↔ lockfile parity. Phase 48's parity gate mirrors this for scan.md ↔ dep_ratings.yaml.
- `scripts/launch/check_no_ai_slop.py::AI_SLOP_BLOCKLIST` + `\bdeeply\s+\w+` regex — imported by `check_no_slop_opp.py`.
- ARCHITECTURE.md § 6 — `docs/dep-opportunities/<YYYY-MM>-scan.md` + ADR-sidecar location pattern.
- `.planning/decisions/P85-OVERRIDE-RETIRED.md` — existing ADR sets file naming + structure precedent for `DEP-OPP-01-obs-browser-source.md`.

**Patterns to copy:**
- ADR format: front-matter (id, date, status, supersedes) + sections (Context, Decision, Rationale, Consequences, Rollback).
- Yellow-defer stub format: short YAML front-matter (candidate, status: deferred, originating_scan, re_eval_trigger) + 2-3 paragraph body.

**Existing Tauri webview mascot route (for OBS browser-source):**
- Mascot WS bus at `ws://127.0.0.1:8765` per v3.0 baseline; OBS browser-source plugs into the same surface. No new code needed.

</code_context>

<deferred_ideas>
- Mixxx OSC adapter — Yellow stub, v3.x re-eval (OPP-02 candidate)
- Controller map transpiler — Yellow stub, v3.x
- pyrekordbox depth extension — Yellow stub, v3.x (current Phase-46 pin is shallow XML parsing only)
- Beat This! Rust crate — Yellow stub, v3.x
- Voicemeeter Banana (advanced-user wizard tier) — Yellow stub, v3.x
- Numark / Hercules controller maps — Yellow stub, v3.x (Mixxx-corpus-transpile path)
- macOS 26+ verification — Yellow stub, v3.x (contingent on Apple release timing)
- Win11 24H2 WASAPI verify — Yellow stub, v3.x
- `obs-websocket-py` event uplink (CODE adoption beyond docs) — explicit v3.x stretch per `.planning/REQUIREMENTS.md` § "Future Requirements"
- `/hatch` user-gen mascot — v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`
</deferred_ideas>

<success_handoff>
**Planner picks up:**
1. Read this CONTEXT.md + STACK.md § Bucket 3 + REQUIREMENTS.md § OPP + ROADMAP.md § Phase 48.
2. Generate 5-7 plans covering:
   - **48-01:** Schema extension (`dep_ratings_schema.json` + `dep_ratings.yaml` `opportunity_evaluations` block)
   - **48-02:** Scan markdown (`docs/dep-opportunities/2026-05-scan.md` with candidate inventory + 4-color rubric + verbatim memory quotes)
   - **48-03:** Auto-Red validator (`scripts/audit/scan_opportunities.py`) + anti-slop sibling (`scripts/audit/check_no_slop_opp.py`) + CI wiring
   - **48-04:** OBS browser-source Green adoption (ADR `.planning/decisions/DEP-OPP-01-obs-browser-source.md` + integration doc `docs/integrations/obs-browser-source.md` + README cross-link)
   - **48-05:** Yellow-defer stubs (8 files under `.planning/research/v3-buckets/`)
   - **48-06:** Phase-level VERIFICATION.md + SUMMARY.md hand-off to Phase 49

Every plan carries the Step-0 worktree-sync invariant + per-plan stall budget.

**Phase 49 readiness signal:** ✅ Phase 49 depends on Phase 46 (lockfile + dep_ratings schema — done) + Phase 48 (this phase). On Phase 48 close, Phase 49 dispatches.
</success_handoff>
