# Pitfalls Research — vibemix v3.1 Distribution-Ready Pass

**Domain:** Adding distribution-polish features (one-click installer + dep audit/pin + dep-opportunity scan + e2e MacBook pass + real mascot GLBs with full emotion coverage) on top of an already-shipped v3.0 Tauri-parent + Python-sidecar + Bravoh-proxy desktop app, targeting Win + Mac only, Gemini-only AI stack, single-engineer (Kaan) authoring with a single-MacBook test rig, under `gsd-autonomous fully` mode with 500–1000+ GitHub-star aspiration.
**Researched:** 2026-05-17
**Confidence:** HIGH — anchored to the v3.0 carryover state in `PROJECT.md`, `CONCERNS.md`, `STATE.md`, and the prior `.planning/research/v3-shipped/PITFALLS.md` catalog. v3.1 pitfalls are explicitly the *seams* between distribution-readiness work and the v3.0 engineering surface — they do NOT duplicate the v3.0 catalog.

> **Scope note — what this file does NOT re-research:**
> The following pitfalls are owned by `.planning/research/v3-shipped/PITFALLS.md` (P1–P41) and remain valid; they are referenced by ID where v3.1 work risks reopening them:
> - P3 (AX-from-parent on djay overlay) · P4 (fullscreen-Space loss) · P5 (Apple Issuer ID) · P6 (SignPath SLA) · P7 (updater secret name mismatch) · P13/14 (multi-monitor + Windows DPI) · P17 (stapler step) · P22 (mascot opaque chrome regression) · P23 (GLB size budget) · P26 (AAC/m4a transcoding) · P27 (sqlite-vec wheel break) · P31 (Day-Zero rehearsal on dev rig) · P32 (api.altidus.world undeployed) · P40 (Kaan-only ear-test sample-size-1) · P41 (Bravoh launch slip).
> This file surfaces NEW pitfalls *specific to layering v3.1's five distribution-readiness target features onto the v3.0 surface*, and re-flags v3.0 pitfalls only where the v3.1 work could silently regress them.

> **Memory cross-references explicitly cited as anchors:**
> `project_one_click_install_hard_req` (Mac+Win one-click HARD req) · `project_v0_1_0_rc1_open_bugs` (open Tauri/mascot/sidecar bugs) · `feedback_worktree_must_sync_main_first` (458-commit regression risk on worktree-isolated subagents) · `feedback_no_clap_use_gemini_embedding` (no CLAP / no MERT — Gemini-only) · `feedback_no_scope_creep_clean_utility` (no stems / no multi-provider / no enterprise) · `project_v4_canonical_baseline` (BlackHole 48 kHz requirement) · `project_mascot_as_vtuber_personality_surface` (one mascot, mood variation; not per-user) · `project_phase_16_kaan_dj_testing` (Kaan's ear, not formal suite) · `project_github_star_goal` (500+ floor) · `feedback_privacy_scope_narrow` (privacy rule applies to LLM-transcript paths only; do not over-broaden) · `feedback_autonomous_no_grey_area_pause` (defer to KAAN-ACTION-REQUIRED, do not pause).

---

## Critical Pitfalls

### Pitfall 1: One-Click Installer Bundles a Stale `requirements.lock` Captured From Kaan's `.venv` Instead of Hermetic CI Build

**Severity:** Critical (silent regression of every v3.0 engineering gain — preview-model SDKs, livekit pin, sqlite-vec wheel — could revert)

**What goes wrong:**
The v3.1 dep-audit/pin work uses `pip freeze > requirements.lock` (or equivalent uv/poetry export) on Kaan's local `.venv`. That `.venv` is Python 3.14 with months of ad-hoc `pip install` cruft (`google-cloud-speech==2.39.0`, `google-cloud-texttospeech==2.36.0`, `openai==2.36.0` — all installed as transitive deps but never imported per `CLAUDE.md` Frameworks list and `CONCERNS.md` §"Dependencies at Risk"). Freezing from this venv ships ~20 unused-but-pinned packages, AND it captures a `google-genai==2.0.1` that may already be superseded by a 2.0.2 patch carrying a bug-fix the v3.0 GATE-02 VCR cassettes were recorded against. Installer subsequently locks every user to a non-reproducible-from-source snapshot of Kaan's laptop on a specific Tuesday.

**Why it happens:**
`pip freeze` is the one-liner the `CONCERNS.md` fix recommends ("`pip freeze > requirements.txt` in the venv, commit it. One command."). For v0.1.0 that was fine. For v3.1 with audit/pin as a target feature, freeze-from-dev-rig is exactly the wrong move — the lockfile becomes a fossil instead of a verifiable contract.

**Warning signs (in PLAN.md):**
- Plan step says "run `pip freeze > requirements.lock`" without specifying a CI environment
- Plan does not name a clean Python builder image (e.g. `python:3.12-slim-bookworm`)
- Plan does not list which deps are *removed* — only what's pinned
- No diff against a previously-frozen baseline

**Prevention:**
- Lock generation MUST run in a clean container: `docker run --rm -v "$PWD":/work python:3.12-slim-bookworm bash -lc "cd /work && pip install -r requirements.in && pip freeze > requirements.lock"` — never on Kaan's `.venv`
- Maintain `requirements.in` (curated direct deps only) separate from `requirements.lock` (machine-resolved transitive closure)
- Prune list as an explicit PLAN.md gate: `pip-deptree --reverse | grep -E "^(google-cloud-speech|google-cloud-texttospeech|openai)"` — if any line returns, justify or drop
- v3.0 GATE-02 VCR cassettes are version-pinned to `google-genai==2.0.1`; if upgrade in lock, re-record `VCR_RECORD_MODE=new_episodes` BEFORE merging the lock bump
- Lockfile diff posted to PR description so the human reviewer sees deltas before merge

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2 — System requirements + dep audit/pin). Pin step is gated on hermetic-builder evidence; freeze-from-dev-venv is a CI failure.

---

### Pitfall 2: Silent BlackHole / VB-CABLE Auto-Install Trips macOS Endpoint Security and Triggers a User-Visible "kernel extension blocked" Modal Mid-Installer

**Severity:** Critical (HARD-requirement one-click install fails for ~30–40% of fresh macOS users; visible installer modal that says "system extension blocked")

**What goes wrong:**
The v3.1 one-click installer must "auto-pulls all runtime deps (sidecar bundle, BlackHole/VB-CABLE virtual audio routing, MIDI prerequisites)" per `PROJECT.md` target feature #1. BlackHole 2ch is **not a userspace driver** — on macOS 11+ it ships as a signed Audio Server Plug-In, but on older macOS (10.13–10.15) and on some hardened-runtime configs it requires System Extension approval via the `systemextensionsctl` flow, which **cannot be auto-approved without user intervention in System Settings → Privacy & Security → "Allow"**. On Apple Silicon under "Reduced Security" the modal also requires a reboot into Recovery Mode. VB-CABLE on Windows is structurally similar — it's a kernel-mode driver that requires the User Account Control / SmartScreen interactive grant. A "one-click" promise that produces a modal saying "system extension blocked" is exactly the broken UX the HARD requirement guards against (`project_one_click_install_hard_req`).

**Why it happens:**
The installer author treats audio-driver installation as analogous to `pip install` — pulling a binary and running it. The OS treats it as a privileged system modification. v3.0 Phase 33 (one-click install hardening) shipped a TCC permissions wizard + BlackHole **probe**, but probe ≠ install. AUDIO-07 BlackHole probe fresh-Mac walk is still in the v3.0 pre-stage discharge list (`PROJECT.md` "Pre-stage discharges") — so even the probe has not been validated on a fresh-user account yet.

**Warning signs (in PLAN.md):**
- Plan says "silently install BlackHole" or "auto-install virtual audio driver" without naming the OS modal or the reboot-into-Recovery path on Apple Silicon
- Plan references a single happy-path screencast without macOS-version matrix (12.3 / 14 / 15) and architecture matrix (Intel / Apple Silicon)
- Plan does not budget for the FALLBACK copy: "BlackHole couldn't auto-install — please run this 1-liner brew command and re-launch vibemix"
- Plan claims VB-CABLE install does not need UAC

**Prevention:**
- Re-scope target feature #1 from "auto-install BlackHole" to "**detect** BlackHole + provide a one-tap fallback installer pointer with copy-pasted command + reboot guidance" — the install side stays user-driven, the **routing configuration** (Multi-Output Device creation) is what gets automated
- macOS: scripted `osascript` Multi-Output Device creation via `audio-mac-cli` or equivalent — runs AFTER BlackHole is detected via `system_profiler SPAudioDataType | grep -i blackhole`
- Windows: VB-CABLE install detection via `Get-PmpDriver | ? { $_.OriginalFileName -like "*vbaudio*" }` in PowerShell; fallback opens the VB-CABLE installer with auto-elevation prompt — make it ONE consent click, not silent
- Wizard copy MUST anticipate the System-Settings modal: "When macOS asks to allow the BlackHole extension, click Allow and return here — vibemix will pick it up automatically."
- Test on `INSTALL-VM-RUN fresh-VM matrix` (already deferred in `PROJECT.md` SHIP-04) — must include a Reduced Security Apple Silicon boot, not just Full Security
- Verify against memory `project_v4_canonical_baseline` BlackHole 48 kHz format requirement: the post-install verification step must do an actual sample-format check, not just driver-detected

**Phase to address:**
v3.1 one-click install phase (target feature #1). Re-scope step happens at plan-checker stage, not after installer is half-built.

---

### Pitfall 3: "It Works on Kaan's MacBook" Trap — End-to-End MacBook Pass Validates Only an Apple-Silicon Sonoma Configuration That Catches Exactly Zero of the Hard Cases

**Severity:** Critical (entire target feature #4 produces false-green; release sign-off rubber-stamps a build that fails on the user-installed-base distribution Kaan never sees)

**What goes wrong:**
Target feature #4 — "End-to-end MacBook pass (functional + visual + aesthetic + usability) — Kaan runs the full app on his MacBook with a real set" — is satisfied on Kaan's M-series Sonoma rig with: BlackHole already installed, DDJ-FLX4 already paired, TCC already granted, Bravoh proxy reachable, font cache warm, GPU drivers stable. The whole point of v3.0 SHIP-04 (`INSTALL-VM-RUN fresh-VM matrix (macOS 12.3/14/15 + Win 10/11)`) was to break this trap, and SHIP-04 is **still in the v3.0 pre-stage discharge list**. If v3.1's "MacBook pass" is treated as a substitute for SHIP-04, the distribution-readiness milestone closes engineering-green while the actual release-gate evidence remains undischarged — the team feels done but Apple Dev + SignPath approvals land into a binary that has never been smoke-tested on macOS 12.3 or Intel Mac.

**Why it happens:**
"End-to-end MacBook pass" reads as a release-blocking exercise. It's actually a Kaan-aesthetic exercise (CDJ Whisper visual surface validation, mascot emotion coverage validation, real-DJ-set usability validation) — those are necessary but not sufficient. Single-machine testing inherits all of Kaan's dev cruft (v3-shipped P31). Compounding: `gsd-autonomous fully` mode + `feedback_autonomous_no_grey_area_pause` means the milestone can be marked complete without the OS-matrix gate firing.

**Warning signs (in PLAN.md):**
- Plan title contains "MacBook pass" or "Kaan's machine" without an explicit OS-matrix companion check
- Plan does NOT cross-reference SHIP-04 / SHIP-05 from `PROJECT.md` pending KAAN-ACTION-LEGAL items
- Verification criteria written as "Kaan runs a set, sees no issues" — no machine-cohort enumeration
- No mention of memory `feedback_worktree_must_sync_main_first` (subagent worktrees from stale base) even though e2e test infra often runs in spawned worktrees
- No screencast capture committed for replay later

**Prevention:**
- Split target feature #4 into two artifacts in the PLAN:
  - **#4a Kaan-ear pass** (subjective — aesthetic / mascot emotion / CDJ Whisper / real-set feel) — runs on Kaan's MacBook
  - **#4b OS-matrix smoke** (objective — install / launch / first-event / shutdown clean) — runs on at minimum 2 of {macOS 12.3 Intel, macOS 14 AS, macOS 15 AS, Win 10, Win 11}, via UTM/Parallels/GitHub Actions matrix
- #4b is the prerequisite for milestone close. #4a is the prerequisite for release-cut (`check_gate.sh` Gate 2b — Kaan ear veto already wired per v3.0 Phase 42)
- The "MacBook pass" screencast is committed to repo (private storage acceptable — git-LFS or a pinned Bravoh-Drive link); future verifier agents can replay
- Cross-link: v3.1 milestone-audit checklist MUST flag SHIP-04 status — if it's still pending external clock, mark the v3.1 close as conditional on SHIP-04 discharge (not blocking, but visible)
- Memory `feedback_privacy_scope_narrow` reminder: this is normal FS / VM access, NOT the LLM-transcript privacy rule — do not over-gate test-rig discussions behind per-turn permission

**Phase to address:**
v3.1 e2e MacBook pass phase (target feature #4). Split happens at plan-checker stage. #4b feeds back into v3.0 SHIP-04 discharge — the work is mutually reusable.

---

### Pitfall 4: Mascot Emotion-State Test Coverage Built Around `mascot.html` Easter Egg Instead of the v3.0 Tauri WebView — Real Mascot Surface Untested

**Severity:** Critical (mascot "fully visible with all emotions wired" appears green via the standalone HTML, ships broken in the actual app shell)

**What goes wrong:**
There are two mascot surfaces in this repo:
1. **`mascot.html`** — the original vanilla-JS / Canvas 2D file served at `file://$(pwd)/mascot.html`, kept as a "fun easter egg / dev visualization" per `PROJECT.md` "Out of Scope" ("Mascot.html as a shipped UI — kept as a fun easter egg / dev visualization, not part of the polished installer experience")
2. **The v3.0 production mascot** — Tauri WebviewWindow, Three.js, 4-layer additive state machine, 21 GLB clips + 8 anticipation clips, beat-coupled idle, additive emotion + reaction layers, mood→animation pool (per v2.1 Phase 31 + v3.0 Phase 43 VIS-05/06)

If v3.1's target feature #5 ("Mascot fully visible with all emotions wired — Base + Emotion + Anticipation + Reaction state-machine layers cover every event class, GLB assets land real (not placeholder), mascot is visible on every supported window/screen-share path") gets tested against `mascot.html` (which an engineer reading `CLAUDE.md` "Smoke tests" might naturally reach for), the test passes while the real Three.js state machine ships with placeholder GLBs, busted retargets, or emotion-pool gaps. v0.1.0-rc1's "mascot chrome strip" bug is *exactly* this class — the easter egg looked fine while the real surface was broken (`project_v0_1_0_rc1_open_bugs`).

**Why it happens:**
`mascot.html` opens with a single `open file://` command and is the path of least resistance for a smoke test. The Tauri+Three.js mascot requires a Tauri dev session (or a built binary) to inspect. Plan-checker may not catch the substitution because the artifact looks like "mascot test."

**Warning signs (in PLAN.md):**
- Plan step says "open mascot.html and verify emotions" — direct red flag
- Plan does NOT name the Tauri WebviewWindow target (e.g. `mascot://` or whatever the v3.0 production scheme is)
- Plan does NOT enumerate the four additive layers (Base + Emotion + Anticipation + Reaction) or reference the 4-layer state machine from v2.1 Phase 31
- Plan does not check the VIS-04 5 Mixamo retarget status — the prep_*.glb placeholders are still pending in v3.0 pre-stage discharges
- No grep gate excluding `mascot.html` from the e2e test target set

**Prevention:**
- e2e mascot tests target the **Tauri WebviewWindow only** — Playwright with `tauri-driver` or vitest snapshot via the production component path (`tauri/ui/src/components/Mascot.*`)
- Add a CI grep gate: `! grep -rn "mascot.html" tests/ e2e/ scripts/ci/` — fails if any test artifact references the easter egg
- Mascot emotion coverage matrix is explicit: for each of {Base × Emotion × Anticipation × Reaction} layer, list every clip; for each Event Type (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL) name which layers should fire; the test asserts the firing
- Track VIS-04 5-Mixamo-retarget status as a v3.1 prerequisite — if still pending, target feature #5 closes engineering-WIRED but flagged "real-asset blocker" in the milestone-audit, not green
- Honor `project_mascot_as_vtuber_personality_surface`: SINGLE mascot ("Neon Rebel"), mood variation on the same rig — the emotion-coverage matrix is for mood × event, NOT for swappable mascots
- Re-flag v3-shipped P22 (mascot opaque chrome regression) — every chrome-touching change in the install/wizard phase risks reopening; vitest snapshot on `background: transparent` of the wrapper element required

**Phase to address:**
v3.1 mascot emotion coverage phase (target feature #5). The Tauri-surface-only contract is set in plan-checker before any test scaffolding lands.

---

### Pitfall 5: Anti-Slop Blocklist False-Trips on Installer / Wizard / Dep-Audit Copy and Blocks the v3.1 PR That Was Meant to Polish Distribution

**Severity:** Critical (the v3.0 anti-slop CI gate — README hero verbatim lock + 15-token blocklist + `\bdeeply\s+\w+` regex — fires on legitimate installer prose and blocks merge of every v3.1 PR until the gate is special-cased; bad fix = relax the gate, bleed back into v4)

**What goes wrong:**
v3.0 Phase 44 LAUNCH-01 shipped the README hero verbatim lock with a 3-gate CI lock + AI-slop blocklist (15 tokens + `\bdeeply\s+\w+` regex). The blocklist contains tokens like "seamless", "delve", "robust", "leverage", "powerful", "deeply integrated", etc. — the exact vocabulary that installer / dep-audit / e2e-report prose naturally reaches for ("seamlessly install BlackHole", "robust dep pinning", "leverage `pip-audit`", "this report deeply explores"). Every v3.1 PR that touches a `.md` file (PLAN.md, SUMMARY.md, README install section, scripts/install/*.sh wizard copy, e2e report templates) fires the blocklist. The temptation under `gsd-autonomous fully` mode is to relax the regex or carve out exemptions — which corrodes the v3.0 anti-slop thesis (`project_anti_slop_grounded_gemini_thesis`) by allowing slop vocabulary back into the repo through the installer-prose side door.

**Why it happens:**
The blocklist was tuned against README hero + customer-facing surfaces. PLAN.md / SUMMARY.md / wizard copy were not in scope when the blocklist was tuned. Autonomous mode merges PRs through the gate, so a single relaxation gets in fast and persists.

**Warning signs (in PLAN.md):**
- Plan step says "update the README install section" without naming the blocklist gate
- Plan proposes "exempt PLAN.md from blocklist" or "loosen the regex for install/" — both are slop-debt accumulators
- Plan does not include a vocabulary self-check pass against `scripts/ci/check_no_slop.py` (or whatever the actual gate script is named) BEFORE submission
- Wizard copy uses any of: seamless, robust, leverage, delve, powerful, comprehensive

**Prevention:**
- Audit the v3.0 anti-slop blocklist path locations first (`scripts/ci/check_no_slop.*` and the LAUNCH-01 verbatim-lock test); confirm the **scope** of the gate before authoring v3.1 prose — if it covers all `.md`, write installer prose under the same vocabulary discipline
- Vocabulary substitution dictionary committed to `docs/internal/copy-substitutions.md`: "seamless → one-tap" / "robust → tested" / "leverage → use" / "deeply integrated → wired" — applied at draft time, not retrofit
- Plan-checker gate: every PLAN.md / SUMMARY.md / wizard-copy file MUST run `scripts/ci/check_no_slop.py --path <file>` as a pre-commit check, output zero matches
- **DO NOT** relax the gate, exempt files, or weaken the regex — instead, write installer prose that survives the gate. The HARD requirement is one-click install, NOT installer prose freedom
- Cross-link: this is the same discipline as the LAUNCH-01 README hero verbatim lock — installer copy carries the same anti-slop contract as customer-facing copy

**Phase to address:**
Every v3.1 phase that produces customer-facing or internal-doc prose (one-click install copy, dep-audit report, e2e MacBook report). Plan-checker is the gate.

---

### Pitfall 6: Dep-Opportunity Scan Surfaces a Linux-Only or Multi-Provider AI Library That a Subagent Adds Without Catching the Constraint

**Severity:** Critical (subagent under `gsd-autonomous fully` recommends a dep that violates an explicit constraint — Linux excluded, Gemini-only, no scope creep — and merges before plan-checker catches it)

**What goes wrong:**
Target feature #3 — "New dep + integration opportunity scan — research pass surfacing what should be added to widen real-world compatibility (DJ software / OS edge cases / hardware), with explicit green/yellow/red ratings; only the green ones land in v3.1." A WebSearch-driven scan will eagerly recommend popular libraries that solve adjacent problems: `pulseaudio-py` (Linux audio), `pipewire-python` (Linux audio), `pydub` (drags ffmpeg — already accepted), `librosa` (CPU-heavy, already on path), `essentia` (Linux-first build chain), `pyo` (audio DSP), `mutagen` (tag reading — fine), `pyalsa` (Linux only), `pylast` (Last.fm grounding — adds Last.fm dep), `whisper.cpp` bindings (multi-provider AI — violates Gemini-only), `openai-whisper` (multi-provider AI), `azure-cognitiveservices-speech` (multi-provider), `coqui-tts` (multi-provider TTS). Each one looks shiny in the scan. Each one violates an explicit constraint from `CLAUDE.md` / `PROJECT.md` / memory:
- Linux exclusion: `pulseaudio-py`, `pipewire-python`, `pyalsa`, `essentia` (Linux build chain)
- Gemini-only (`feedback_no_clap_use_gemini_embedding`): CLAP, MERT, OpenL3, `openai-whisper`, `azure-cognitiveservices-speech`, `coqui-tts`
- No scope creep (`feedback_no_scope_creep_clean_utility`): stem separators (Demucs, Spleeter), beat-grid replacements unless gated on install size

**Why it happens:**
Scan tooling is biased toward popularity, not toward this project's constraint surface. WebSearch's "best Python audio libraries 2026" results are heavily Linux/multi-platform/multi-provider. Under autonomous mode the recommendation goes into the green/yellow/red rating and a subagent may rate it green based on download numbers alone.

**Warning signs (in PLAN.md):**
- Scan plan does not list the exclusion-set upfront (Linux deps / non-Gemini AI / stem-sep / multi-provider)
- Rating rubric is missing the "constraint-violation auto-red" rule
- Plan suggests adopting any library with `linux` in its primary wheels or `pyalsa` / `pipewire` / `pulseaudio` in its deps tree
- Scan output is not gated on a grep against `feedback_no_clap_use_gemini_embedding` + `feedback_no_scope_creep_clean_utility` keyword list

**Prevention:**
- The dep-opportunity-scan PLAN MUST start by enumerating the exclusion set verbatim from `CLAUDE.md` Constraints + `PROJECT.md` Out of Scope + memory entries. Quote the source.
- Rating rubric is a 4-color, not 3:
  - **Red — constraint violation:** automatic exclude, no further evaluation. Logged as "scanned, excluded by constraint: <which>."
  - **Red — risk:** install size > 50 MB / kernel ext / network call required / not on Win+Mac wheels
  - **Yellow — opportunity gated:** worth adding if specific evidence justifies it (close a real hallucination class, fix a specific user complaint)
  - **Green — adopt:** clearly closes a real gap, install-impact green, no constraint violations
- Subagent prompt for scan-evaluator MUST include: "Reject Linux-only deps, multi-provider AI deps, stem-separation deps, CLAP/MERT/OpenL3, and any dep that violates `feedback_no_scope_creep_clean_utility`. Cite the constraint source for each rejection."
- Output file `.planning/research/v3.1-dep-scan/EXCLUDED.md` records the rejections — visible audit trail for Kaan to spot-check
- For each green candidate, an install-impact line: bundled-size delta, Win+Mac wheel availability check, license check (GPL contamination flag), API-surface-change risk

**Phase to address:**
v3.1 dep-opportunity-scan phase (target feature #3). Constraint enumeration is the first step of the plan, not a post-scan filter.

---

### Pitfall 7: Worktree-Isolated Subagents Build the v3.1 Installer From a Stale Base and Silently Regress v3.0 SHIP-CUT Wiring on Merge

**Severity:** Critical (memory-attested past failure mode — Phase 40 subagent worktree was 458 commits behind; merging produced a 161k-line regression; same risk on v3.1 install/dep/mascot subagents)

**What goes wrong:**
Memory `feedback_worktree_must_sync_main_first` documents: `Agent(isolation="worktree")` creates worktrees from a stale base. Phase 40 hit this — the worktree was 458 commits behind `main`. v3.0 closed 2026-05-17 with 250 commits since `v2.1.0` tag across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. Every v3.0 deliverable (Phase 40 audio path + Phase 41 latency stack v2 + Phase 42 hallucination gate + Phase 43 visual lock + Phase 44 launch positioning + Phase 45 cookbook) is at risk of regression if a v3.1 subagent spawns a worktree from before those commits and produces an installer or dep-audit PR that re-introduces deleted code or strips down newly-added CI gates (`launch_trigger.sh`, `audit_ship_v1_decision.py`, `check_bravoh_server_ready.sh`, `check_gate.sh`, anti-slop blocklist scripts).

**Why it happens:**
`gsd-autonomous fully` mode spawns subagents liberally. Worktree-isolated subagents are the default for parallel work. Without the explicit Step-0 sync invariant in every subagent prompt, the regression is invisible until merge.

**Warning signs (in PLAN.md):**
- Plan spawns 2+ parallel subagents but does not name a base-sync step in the subagent prompt
- Subagent prompts omit `git fetch origin main && git merge origin/main` or equivalent rebase invariant
- Plan does not record the base SHA each subagent forked from
- Verification step does not include a "merge dry-run no conflicts in v3.0 artifacts" check against `scripts/`, `tauri/`, `.github/workflows/release.yml`

**Prevention:**
- Every subagent prompt for v3.1 MUST contain a Step-0 invariant: `git fetch origin main && git merge --no-edit origin/main && git status` — output captured as the first artifact in the subagent's deliverable
- The orchestrator validates Step-0 output before reviewing the subagent's main work
- Verifier agents run a pre-merge diff against the v3.0 release-critical paths and reject the PR if any v3.0 artifact (release.yml, check_gate.sh, audit_ship_v1_decision.py, launch_trigger.sh, README hero verbatim, anti-slop blocklist) has touched lines that aren't part of the explicit PLAN
- Worktree cleanup discipline: after merge, worktrees are removed; new work spawns from a fresh sync
- This memory-anchor (`feedback_worktree_must_sync_main_first`) is cited in EVERY v3.1 phase's CONTEXT.md so any future agent reading it has the rule in scope

**Phase to address:**
All v3.1 phases that spawn parallel subagents. Step-0 invariant is set in the orchestrator's subagent-prompt template, not per-phase.

---

### Pitfall 8: End-to-End Test Burns Real Gemini Quota Running a Real LiveKit Session, Hitting the 50 €/Month Budget Cap in CI Before Launch

**Severity:** Critical (budget breach pre-launch from CI alone; Bravoh-proxy free-tier already constrained per v3-shipped P30/P39)

**What goes wrong:**
A naive e2e MacBook test for target feature #4 runs the **actual** vibemix runtime: LiveKit RealtimeModel session opens against Gemini 2.5 Native Audio Preview, audio streams in for 5–30 minutes of a real DJ set, events fire, reactions generate. Each CI run is $0.50–$2.00 in Gemini calls (Live API is expensive). At 10 CI runs/day during the v3.1 milestone window, that's $50–$200 from CI alone — eats the entire 50 €/month proxy budget BEFORE a single end-user reaction. v3-shipped P30 (Bravoh proxy free-tier RPM under viral load) and P39 (50 €/mo budget breach) already flag this for *production* traffic; v3.1 risks reproducing it via *CI traffic*.

**Why it happens:**
"End-to-end test" naturally reads as "run the end-to-end thing." For a desktop AI app, the end-to-end thing involves a paid API. There's no obvious "test environment" because Gemini Live preview has no free-tier-isolated test endpoint. Engineer reaches for `if CI: skip` which de-scopes the gate entirely.

**Warning signs (in PLAN.md):**
- Plan says "run a 30-min DJ session in CI" without naming a VCR / fixture / mock seam
- Plan does not reference v3.0 GATE-02 VCR cassettes (already pending in pre-stage discharges)
- Plan budgets zero Gemini cost for the v3.1 milestone
- No cost-per-run estimate in the plan
- No "skip-on-CI / run-on-Kaan-rig" gating for paid paths

**Prevention:**
- Reuse v3.0 GATE-02 VCR cassettes infrastructure: the e2e test replays recorded Gemini Live + TTS exchanges instead of hitting the live API. Cassettes are bit-exact deterministic
- For the parts that MUST hit the live API (model-pinning verification, ear-test session capture for `check_gate.sh` Gate 2b): explicit `EAR_TEST=1` gate, manual local-only invocation on Kaan's rig, never auto-run in CI
- Cost-budget assertion in CI: a script measures `gemini_cost_estimate` from cassette / model / token-count and fails the build if it exceeds a per-PR ceiling ($0.10 / PR)
- For target feature #4 specifically — the **MacBook** part is local on Kaan's MacBook, not CI. CI runs the OS-matrix install/launch/shutdown smoke (Pitfall 3 #4b) which does NOT need a live Gemini session
- Cross-link `cut_release.sh` 6-gate pre-flight (v3.0 SHIP-07 / Phase 39) — that already gates on real cost; the v3.1 e2e test reuses the same cost-accounting plumbing

**Phase to address:**
v3.1 e2e MacBook pass phase (target feature #4). VCR-by-default + Kaan-rig-only ear-test invocation set at plan time.

---

## High Pitfalls

### Pitfall 9: Re-Signing Pipeline Regresses Because v3.1 Installer Phase Touches `release.yml` Without Re-Running v3.0 P46 Audit

**Severity:** High (Apple notarytool + SignPath wiring is fragile — v3-shipped P5/P6/P7 all re-open if `release.yml` is edited without the v3.0 P46 audit re-running)

**What goes wrong:**
v2.1 Phase 38 shipped Apple notarytool + SignPath GH Action wired into `release.yml` + post-sign verifier release-publish gate + P46 audit (Bash + PowerShell mirror). v3.1's one-click install phase will touch `release.yml` (to add an installer-bundle build step or to refactor the matrix for the new BlackHole-detect step). Any edit risks regressing:
- Updater env var name (v3-shipped P7) — `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` vs `TAURI_UPDATER_KEY_PASSWORD`
- Stapler step ordering (v3-shipped P17) — must be `notarytool submit` → `staple` → `stapler validate`
- SignPath secret name + path
- Updater manifest URL (`api.altidus.world/vibemix/updates/*`)

Without re-running the P46 audit on the modified `release.yml`, regressions ship silently and only surface at SHIP-CUT.

**Warning signs (in PLAN.md):**
- Plan modifies `release.yml` or any signing-adjacent file without an explicit "re-run P46 audit (Bash + PowerShell mirror)" step
- Plan does not reference v3-shipped P5/P6/P7/P17 by ID
- No `gh workflow run release.yml --ref <branch> --dry-run` step
- No "verify post-sign verifier still fires" step

**Prevention:**
- Any v3.1 PR that touches `release.yml`, `tauri.conf.json5`, `scripts/signing/*`, or the updater config triggers a CI gate that re-runs the P46 audit and the post-sign verifier on a synthetic build
- The verifier (`verify_signed.py --require-signed` per v3.0 SHIP-03) is invoked on the PR's artifact, not just on the merge to `main`
- Plan-checker cross-references v3-shipped P5/P6/P7/P17 explicitly for every `release.yml`-touching change
- Pre-stage discharge SHIP-03 (`verify_signed.py --require-signed`) MUST be on green status before v3.1 milestone-close — track in milestone audit

**Phase to address:**
v3.1 one-click install phase (target feature #1) — any installer change that touches signing. Also relevant if dep-audit phase ends up reorganizing the build matrix.

---

### Pitfall 10: License Audit Misses GPL Contamination From a Newly-Adopted Dep, Forcing License Choice Back to GPL or a Rip-Out

**Severity:** High (Bravoh internal-reuse constraint per `PROJECT.md` Constraints — "Must allow Bravoh to use the same code internally if needed"; GPL contamination forces full vibemix to GPL, which breaks the Bravoh constraint)

**What goes wrong:**
The dep-audit/pin phase + dep-opportunity-scan phase will surface adoption candidates with various licenses. Most are MIT / Apache 2.0 / BSD — fine. A few common DJ-software / audio-tooling ecosystems are GPL — Mixxx itself (GPL-2), some Python audio libs (`pyo` is GPL, `aubio` was GPL-3 historically, `essentia` is AGPL-3). The v3.x candidate scope (`PROJECT.md` Active) already calls out: "Mixxx OSC adapter — vibemix subscribes to UDP `:7777`, maps to existing `MusicState` schema (GPL-2 IPC-only)" and "Mixxx controller map transpiler — offline build-time XML+JS → vibemix semantic event JSON; separate `vibemix-maps` GPL-2 repo; core consumes as data". The IPC-only stance is the lawful path. A v3.1 dep audit could miss a transitive GPL dep (e.g., a Python wrapper that statically embeds a GPL native library), or could grant green-light to a dep that the auditor incorrectly assumes is MIT.

**Why it happens:**
License audit is often run on direct deps. Transitive deps' licenses aren't recursively checked. `pip-licenses --order=license` shows everything, but interpreting the output requires context. Apache 2.0 patent clauses can also conflict with some grants — easy to miss.

**Warning signs (in PLAN.md):**
- License audit uses direct-deps only (`pip-licenses` without `--with-system`)
- No SBOM diff against the v2.1 Phase 34 syft baseline
- Plan does not call out Mixxx GPL-2 separation explicitly even though v3.x scope mentions Mixxx integration
- License rubric does not flag AGPL / GPL-3 / GPL-2 / LGPL distinctions

**Prevention:**
- Re-run the v2.1 Phase 34 syft SBOM generation and diff against the prior baseline — any new license class flagged for human review
- License rubric is explicit:
  - **Green:** MIT, Apache 2.0, BSD-2/3, ISC, Unlicense, MPL-2.0 (file-level copyleft only)
  - **Yellow — IPC-only ok:** GPL-2 / GPL-3 if kept at process boundary (Mixxx-style)
  - **Red:** AGPL-3 anywhere, GPL with embedded use, LGPL with static linking
- The license-check tool runs in CI on every dep-lock change: `pip-licenses --format=json | jq '.[] | select(.License | test("AGPL|GPL-3|LGPL")) | .Name'` — non-empty output blocks merge
- For native libs bundled by wheels (PyInstaller / Tauri NSIS): manual review of bundled `.so` / `.dll` licenses — `licensecheck` or `licensee`
- Cross-link `PROJECT.md` Constraints: "Open-source license: TBD (likely MIT or Apache 2.0). Must allow Bravoh to use the same code internally if needed." → this is the gate

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2) + dep-opportunity-scan phase (target feature #3). License rubric is set before any candidate is rated green.

---

### Pitfall 11: Mascot GLB Bundle Grows Past 25 MB / 350 MB Installer Ceiling Because v3.1 Adds Real Anticipation Clips on Top of v2.1's 21.67 MB Baseline Without a New Budget

**Severity:** High (one-click install promise erodes; first-install download timeouts on slow connections)

**What goes wrong:**
v2.1 Phase 31 closed with "GLB bundle 21.67/25 MB" and v3-shipped P23 already flagged the trap. v3.1 target feature #5 explicitly adds: "Base + Emotion + Anticipation + Reaction state-machine layers cover every event class, GLB assets land real (not placeholder)." The current state per `PROJECT.md` pre-stage discharges: "VIS-04 5 Mixamo retargets for prep_*.glb placeholders (Adobe-account download + Kaan-aesthetic selection)" — these are anticipation-layer placeholders that need to become real. Real GLBs are typically 250–500 KB DRACO-compressed, but if any single clip from an aesthetic-driven Mixamo retarget ends up over budget (or if v3.1 adds NEW emotion variants beyond the existing pool to hit "all emotions wired"), the bundle blows past 25 MB. Tauri wheel size grows accordingly. v2.1 also said "well under 350 MB hard cap" for the wheel — 25 MB to 30 MB GLB is a 5 MB delta that compounds with other v3.1 additions.

**Why it happens:**
"Real GLBs land" doesn't naturally trigger a budget check. Aesthetic-driven Mixamo retargets are easy to over-commit — Kaan picks the takes he likes, the asset pipeline doesn't push back on size.

**Warning signs (in PLAN.md):**
- Plan adds GLBs without listing per-clip and total size budget
- Plan does not reference the existing 21.67/25 MB budget or v3-shipped P23
- No `du -sh tauri/ui/public/mascot/*.glb | awk` step in the verifier
- No DRACO compression flag in the asset pipeline
- Adobe-Mixamo retarget step does not include an export-size guard

**Prevention:**
- Per-clip cap: 300 KB DRACO level 7+ (v3-shipped P23 prevention)
- Total cap stays at 25 MB; CI gate `[ $(du -bsh tauri/ui/public/mascot/*.glb | awk '{sum+=$1} END {print sum}') -lt 26214400 ]` fails build if exceeded
- For each new emotion clip, the gate reports the delta vs. previous size and the closest-to-budget clip — Kaan can swap if needed
- DRACO compression is part of the Mixamo retarget pipeline, not a post-step (which often gets skipped)
- Installer total-size budget: track DMG + MSI size in CI per release; alert if it exceeds 350 MB Tauri wheel hard cap from v2.1 A6 Phase 11
- Cross-link `project_one_click_install_hard_req` — every emotion clip rated green/yellow/red on install-impact contribution

**Phase to address:**
v3.1 mascot emotion coverage phase (target feature #5). Asset pipeline gate runs on every PR touching `tauri/ui/public/mascot/`.

---

### Pitfall 12: Mixamo Retarget Pipeline Breaks on Custom Mascot Rig — Bones Mismatch, Animation Plays But Geometry Distorts

**Severity:** High (real GLBs land but mascot looks broken — exactly the AI-slop tell `project_anti_slop_grounded_gemini_thesis` is designed to prevent on the visual surface)

**What goes wrong:**
v3.0 Phase 43 scaffolded the Mixamo retarget pipeline. Mixamo's default skeleton (`mixamorig:`) does not match arbitrary custom rigs — when retargeting the "Neon Rebel" custom mascot rig, bone-naming and bone-count mismatches cause:
- Animation plays but limbs swing in wrong directions
- Hip-bob amplitude wrong (kick visible but bob upside-down)
- Eye/jaw blendshape mismatch causes face to distort during emote
- Three.js skinning errors but no console crash — silent visual regression

Memory `project_mascot_as_vtuber_personality_surface` confirms "VTuber-style single character with mood variation, NOT swappable" — so a single rig has to retarget cleanly across all emotion clips, not just one happy-path test.

**Why it happens:**
Mixamo is built for Mixamo skeletons. Custom rigs work but require a bone-mapping config that's manual to produce. v2.1 P21 (mascot 1-day spike) was for emote-tag-vs-audio ordering; the retarget compatibility spike was scaffolded in Phase 43 (VIS-04 retarget queue) but not validated against the real rig (still in pre-stage discharges).

**Warning signs (in PLAN.md):**
- Plan adopts Mixamo retargets without a bone-mapping config file referenced
- No "view each retarget in Three.js viewer / scene" verification step
- No vitest snapshot of mascot rendered pose at key frames
- Plan treats `prep_*.glb` as drop-in replacements for placeholders without a visual gate

**Prevention:**
- Bone-mapping config committed: `tauri/ui/src/mascot/rig-map.json` listing every Mixamo bone → Neon Rebel bone with override fallbacks
- Visual regression gate: Playwright screenshot at frame 0 / 30 / 60 of every clip, diffed against approved reference frames — fails if SSIM < 0.95
- Frame-time / overdraw budget from v3-shipped P19 carries forward — every new retargeted clip stresses the 4-layer mixer; assert frame time p99 < 22ms on synthetic 60-event burst
- One emotion clip retargeted → fully verified end-to-end (viewer / vitest / Playwright) BEFORE the next one starts — serial pipeline, not bulk-retarget-then-test
- Cross-link v3-shipped P19 (Three.js crossfade discontinuity) — adding new clips re-stresses the same code path

**Phase to address:**
v3.1 mascot emotion coverage phase (target feature #5). Bone-mapping config is a phase prerequisite, not a Day-N step.

---

### Pitfall 13: `pip-audit` / `cargo-audit` / `osv-scanner` Produces Volume Noise That Trains Reviewer to Auto-Approve, Hiding the One Real Vuln

**Severity:** High (security-pass shipped v2.1 Phase 34 — every v3.1 dep change reruns these scanners; reviewer fatigue from noise leads to "approve all" pattern)

**What goes wrong:**
`pip-audit` against the full transitive closure (livekit-agents + google-genai + scipy + numpy + pyobjc + Three.js npm deps + Tauri Rust crates) routinely produces 30+ "advisory" entries — most of which are deprecations / theoretical RCE / "fixed in a version no one pins to." `osv-scanner` adds the OSV-DB layer with its own noise. `cargo-audit` against the Tauri crate graph adds more. Reviewer reads "30 vulns" weekly, sees no actual risk, develops the auto-approve reflex. The one real vuln (e.g., a `livekit-agents` SSRF in a release between 1.5.8 and 1.5.10) slips past.

**Why it happens:**
Security scanners are tuned for the median repo, not for a desktop-bundled tool where most "network-call" vulns don't apply (no externally-exposed surface) and most "auth-bypass" vulns don't apply (no auth layer). Without a tuned ignore-list, signal-to-noise is bad.

**Warning signs (in PLAN.md):**
- Plan re-runs the scanners without referencing the v2.1 Phase 34 baseline + accepted-advisory list
- No `pip-audit --ignore-vuln <ID>` config tracked in repo with rationale per ignore
- No diff-only mode (only NEW advisories shown, not all)
- Plan treats security-scan output as monolithic green/red instead of categorized

**Prevention:**
- Tuned ignore-list: `.pip-audit-ignore` / `.osv-scanner-ignore` / `.cargo-audit-ignore` — each entry has a rationale comment
- CI runs scanners in **diff mode against the v3.0 lock**: only NEW advisories surfaced, not the cumulative list
- Per-advisory triage rubric: applicability (does this code path execute on Win+Mac desktop?), exploitability (network-exposed?), severity vs. impact
- Weekly automated re-scan posted to `.planning/security-scan-rollup.md` — reviewer reads the diff, not the cumulative; trend is the signal
- Reuse v2.1 Phase 34 STRIDE-lite threat model — every new advisory is mapped onto STRIDE before being approved/ignored

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2). Tuned ignore-list + diff-mode scanning set on day 1 of the phase.

---

### Pitfall 14: SBOM Staleness — `syft` Generated Once for v2.1 Phase 34 But Never Re-Run Per Release, Distributing With a Wrong Manifest

**Severity:** High (legal artifact attached to the release misstates which deps are bundled — supply-chain attestation broken)

**What goes wrong:**
v2.1 Phase 34 shipped `syft` SBOM generation. If the SBOM was generated **once** at v2.1 close and not regenerated for v3.0 (which added ~+61k LOC and updated several deps), the v3.0 release shipped with a stale SBOM. v3.1 doubles down — adding new bundled deps (ffmpeg for `.m4a` per v3-shipped P26, possibly more from dep-opportunity-scan) without re-running syft means the SBOM published as a release asset misstates the bundle. Supply-chain attestation requirements (some downstream Bravoh internal use may require valid SBOM) silently break.

**Why it happens:**
SBOM generation is a one-time setup-feels item. Without a CI hook, no one re-runs it. Verifying the SBOM is correct requires diffing against the actual built bundle — manual work.

**Warning signs (in PLAN.md):**
- Plan adds bundled deps without an SBOM re-gen step
- `release.yml` does not include `syft <bundle> -o cyclonedx-json` and asset attachment
- No CI gate "SBOM matches bundle" (syft vs. actual file list)

**Prevention:**
- `release.yml` step: `syft ./dist/vibemix.dmg -o cyclonedx-json > vibemix-sbom.json` (and equivalent for MSI) — runs every release
- Gate: parse SBOM, list bundled native libs, diff against expected list; fail if drift
- SBOM is a release artifact attached to every GH release alongside the DMG/MSI
- Re-run also on every dep-lock change in CI (not just at release) — surfaces drift early
- Cross-link v2.1 Phase 34 — confirm SBOM cadence is committed in `release.yml`, not a one-shot

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2). SBOM re-gen is a CI gate, set at lock-change time.

---

### Pitfall 15: One-Click Installer Wizard Auto-Grants Screen Recording / Accessibility / Input Monitoring Permissions Bypassing TCC — Apple Rejects Notarization OR Users See "vibemix wants to control your computer"

**Severity:** High (notarization rejection or scary TCC modal — both kill the one-click promise)

**What goes wrong:**
The v3.0 onboarding stopwatch + TCC permissions wizard (v2.1 Phase 33) had a fallback ladder for macOS 12.3 / 14 / 15. Target feature #1 says "configures audio devices, and lands on a ready-to-run app — zero terminal commands." If "configures audio devices" is interpreted as auto-granting Screen Recording + Accessibility + Input Monitoring TCC permissions via `tccutil` (some installers do this with `sudo tccutil reset Camera`), the wizard:
1. Requires root — breaks "zero terminal commands"
2. macOS 13+ blocks `tccutil` writes to most categories — silent no-op
3. Apple notarytool may reject a bundle that ships with `tccutil` invocations in its scripts
4. Even if it works, the macOS Privacy & Security prompt reads "vibemix wants to control your computer" — kills trust

**Why it happens:**
"Auto-configure permissions" sounds like a clean one-click win. macOS Sequoia (15+) has aggressively tightened TCC; what worked on 12.3 silently fails on 15.

**Warning signs (in PLAN.md):**
- Plan says "auto-grant TCC permissions" or "use tccutil to set permissions"
- Plan does not reference v2.1 Phase 33 TCC fallback ladder
- No explicit user-consent step before TCC modal
- Plan tries to bypass the macOS Privacy & Security UI

**Prevention:**
- TCC permissions are **never auto-granted** — the wizard *guides* the user through System Settings → Privacy & Security with screenshots
- Detection (`tccutil reset` is read-only or fail-loud — no automated grants)
- Pre-flight check at app start: each required TCC category is queried; if not granted, the wizard shows a focused card per category with "Open System Settings here" deeplink (`x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture`)
- macOS 15+ specifically: re-test fallback ladder; the deep-link format changed in Sequoia
- The "configures audio devices" scope is **Multi-Output Device creation**, NOT TCC permission grants — those are separate
- Cross-link `project_v0_1_0_rc1_open_bugs` "TCC list-population" carryover — that was a different bug class (list display), make sure v3.1 doesn't reopen it

**Phase to address:**
v3.1 one-click install phase (target feature #1). TCC discipline set at plan time.

---

### Pitfall 16: MSIX Install Scope Confusion — Per-User vs. Per-Machine Install on Windows Causes `appdata` Path Mismatch and Mascot Cache Loss

**Severity:** High (Windows users lose mascot animation cache + library index across reinstalls; reads as data loss)

**What goes wrong:**
Tauri ships Windows bundles via WiX (MSI) or NSIS. The default install scope is per-user — `%LOCALAPPDATA%\vibemix\` (e.g., `C:\Users\Kaan\AppData\Local\vibemix\`). If v3.1's installer changes to a per-machine install (which some "professional polish" instincts push toward), the install path becomes `%ProgramFiles%\vibemix\` but the **userdata** path stays per-user. On reinstall as a different user, mascot animation cache + library index + DJ profile JSON are all gone. Conversely, switching from per-machine to per-user mid-version causes the same cache loss.

**Why it happens:**
"Per-machine install feels more professional" is a common pull. But the data-residency model (per-user appdata) is what every other Windows app does. Mixing them silently moves user state.

**Warning signs (in PLAN.md):**
- Plan switches install scope (per-user → per-machine or vice versa) without naming the data-migration path
- No reference to `%LOCALAPPDATA%\vibemix\` or `%APPDATA%\vibemix\` as the data root
- Plan does not test reinstall preserving prior session recordings + profile.json

**Prevention:**
- Per-user install scope only — set explicitly in `tauri.conf.json5` Windows config, locked
- All userdata stays in `%LOCALAPPDATA%\vibemix\` regardless of install path
- Reinstall test in INSTALL-VM-RUN matrix (v3.0 SHIP-04 pre-stage discharge): install → use → uninstall → reinstall → verify mascot cache + profile.json + library index preserved
- Document data residency in README install section

**Phase to address:**
v3.1 one-click install phase (target feature #1). Scope decision is plan-locked.

---

### Pitfall 17: Antivirus False-Positive on PyInstaller-Built Sidecar Bundles Trips at First-Launch Even With Valid SignPath Signature

**Severity:** High (some Windows AV vendors flag PyInstaller `--onefile` binaries by static-signature regardless of code-signing — Defender SmartScreen is the headline but ESET / Avast / Norton all have history)

**What goes wrong:**
PyInstaller `--onefile` builds extract themselves to `%TEMP%` at launch — a behavior pattern matching malware unpackers. Static AV scanners flag the binary by entropy / packing signature, NOT by signing status. v2.1 SignPath signing addresses Defender SmartScreen reputation but doesn't address third-party AV heuristics. First-launch user on a corporate Win 10 box with ESET sees "vibemix.exe quarantined" — AV warning, abandoned install.

**Why it happens:**
PyInstaller's launch model is unusual. AV vendors maintain heuristic rules. Signing helps but doesn't cover all vendors.

**Warning signs (in PLAN.md):**
- Plan does not test against multiple AV (at least Defender + one third-party)
- No `--onedir` alternative explored (less suspicious launch pattern at install-size cost)
- Plan does not include AV-vendor outreach (some vendors accept submitted whitelisting requests for OSS projects)

**Prevention:**
- Build with `--onedir` instead of `--onefile` — slightly larger install footprint, much less AV friction (sidecar bundle in v0.1.0-rc1 already has the schema path bug per `project_v0_1_0_rc1_open_bugs`; revisit while addressing)
- Submit pre-launch whitelisting to top AV vendors with the signed binary hash — most accept OSS-project submissions
- README "Windows install" section preemptively addresses: "If your antivirus flags vibemix, this is a false positive — please report it to your AV vendor with this hash: <sha256>"
- Day-Zero rehearsal Win matrix MUST include at least one third-party AV (ESET trial / Avast Free)
- Cross-link v3-shipped P6 (SignPath SLA) — signing is necessary, not sufficient

**Phase to address:**
v3.1 one-click install phase (target feature #1) — Windows side. AV strategy decided pre-build.

---

### Pitfall 18: Phase 16 (Kaan's Ear) Load Inflated by v3.1 Distribution Work — Kaan Becomes the Single Bottleneck for Both Anti-Slop Gate AND Real-Set MacBook Pass AND Mascot-Emotion Aesthetic Pass

**Severity:** High (single-engineer burnout / quality bar slips because the load became unrealistic)

**What goes wrong:**
Memory `project_phase_16_kaan_dj_testing`: "Phase 16 = Kaan's DJ ear, not formal suite. Don't auto-build the 30-session replay harness." That works when Kaan-ear is one gate (anti-slop). v3.1 adds three more Kaan-ear surfaces:
- **#4a Kaan-ear MacBook real-set pass** (target feature #4)
- **#5 mascot emotion aesthetic acceptance** (Kaan picks which Mixamo retarget feels right; rejects bad ones)
- **Anti-slop ear-test session execution** (still pending in pre-stage discharges — GATE-05 ≥2 sessions ≥2 genres in 14d window)

If all three land on Kaan in the same window, the quality bar slips on at least one. The fallback ("just sign off") is the worst outcome — it bypasses the entire gate-discipline that v3.0 built.

**Why it happens:**
Single-engineer project (`PROJECT.md` Constraints: "Team: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside"). Kaan is the only person with the right ear AND the right rig AND the product-aesthetic intuition.

**Warning signs (in PLAN.md):**
- Plan stacks 3+ Kaan-ear surfaces in the same milestone without sequence
- No "split this across multiple sessions" / parallelizable / pre-batch step
- Plan does not check the v3.0 carryover GATE-05 ear-test status before adding new ear-test load
- No "Francesco can do this part" delegation step

**Prevention:**
- Sequence the Kaan-ear surfaces:
  1. Mascot emotion aesthetic pass (~1h, async — Kaan can pick from rendered candidates instead of having to sit through a DJ session)
  2. MacBook real-set pass (~30min DJ session = ear-test session) — runs DURING a normal Kaan DJ session, captures both #4a and GATE-05 in one go
  3. Anti-slop ear-test session #2 (different genre, ≥14d after #1) — schedule, do not batch
- Pre-batch the mascot retarget candidates so Kaan picks from 3–5 already-rendered options per emotion clip, not a from-scratch retarget per emotion
- Francesco delegation: dep-opportunity-scan green/red rating sanity check, AV false-positive testing on his Windows rig, demo-film capture (already a Francesco lane per v3.0 §VIS-09 runbook)
- Reuse: one DJ session captures #4a + GATE-05 simultaneously — same recorded session feeds both gates
- Acknowledge in milestone-audit: if Kaan ran out of time on one surface, mark that surface as carryover, don't force a sign-off

**Phase to address:**
v3.1 milestone-level (cross-cutting). Sequencing happens at roadmap layer, not per phase.

---

### Pitfall 19: Audio Loopback Test On macOS Requires BlackHole — Which the Test Itself Validates the Install Of — Bootstrap Paradox in CI

**Severity:** High (if e2e test depends on BlackHole, and one-click-install phase depends on testing BlackHole install... circular dep)

**What goes wrong:**
The one-click installer's central job is detecting/installing BlackHole. The e2e MacBook pass wants to verify "audio works end-to-end." That verification requires BlackHole. So the e2e test can only run AFTER the install phase has succeeded, AND the install phase can only be verified by running the e2e test, AND CI infra has no BlackHole pre-installed (correctly — it's a system extension). Bootstrap paradox: you can't test the installer's success-path without manually installing the thing the installer is supposed to install.

**Why it happens:**
Audio drivers live below userspace. CI runners are stateless. The thing being verified IS the bootstrap.

**Warning signs (in PLAN.md):**
- Plan does not separate "installer integration test" from "audio-pipeline e2e test"
- Plan tries to run audio loopback in vanilla GitHub Actions macOS runner
- No "fresh-Mac VM with BlackHole pre-baked in image" path

**Prevention:**
- Three-layer test pyramid:
  1. **Unit/component** — installer logic (detection, modal copy, error paths) — mockable, runs in vanilla CI
  2. **Integration** — installer runs on a snapshot VM image WITH BlackHole pre-installed (validates installer doesn't break a working setup) AND on a clean VM WITHOUT BlackHole (validates installer guides correctly to the fallback)
  3. **End-to-end** — full audio pipeline on Kaan's MacBook (target feature #4a), not in CI
- Maintain two pre-baked Mac VM images: "fresh + BlackHole installed" and "fresh + BlackHole absent" — both stored as build artifacts, hashed
- The "BlackHole absent → installer guides user → BlackHole installed → audio works" path is **manually verified by Francesco or Kaan on a fresh non-dev macOS user account** (AUDIO-07 pre-stage discharge already calls this out)
- CI runs (1) and (2). Real-audio loopback is (3), Kaan-rig only

**Phase to address:**
v3.1 one-click install phase + v3.1 e2e MacBook pass phase. Test pyramid is shared infrastructure.

---

### Pitfall 20: New Dep From Opportunity-Scan Adds a Transitive Linux-Only Build Dep That Silently Breaks Win+Mac Wheel Resolution

**Severity:** High (a green-rated candidate brings in a transitive that has no Win wheel — Win build breaks at lock time, BUT lockfile may silently include it as a marker-restricted dep that fails later)

**What goes wrong:**
PEP 508 environment markers (`sys_platform`, `python_version`) let a package declare different transitive deps per platform. A green-rated v3.1 candidate may declare `; sys_platform == "linux"` on a transitive — `pip` resolves fine on Mac (the Linux dep is skipped) but produces a lockfile that includes it as a marker-restricted entry. A future bump or a different solver re-evaluates and picks the Linux-only version, breaking the Mac install. `uv` and `poetry` handle markers differently than `pip-tools`; cross-solver instability is real.

**Why it happens:**
Markers are subtle. Most engineers don't read them. Lockfile diffs that show a "linux-only" dep added often pass review as "harmless because we don't ship Linux."

**Warning signs (in PLAN.md):**
- Lockfile diff shows new entries with `sys_platform` markers
- Plan does not specify which lockfile tool is canonical (pip-tools vs uv vs poetry)
- No "platform-resolve" test (CI runs `pip install --dry-run` on Win, Mac, both architectures)

**Prevention:**
- Lockfile generation runs **per-platform**: separate `requirements-mac.lock` + `requirements-win.lock` (or `--platform` flag on uv)
- CI matrix runs `pip install -r requirements-mac.lock` on macos-latest and `requirements-win.lock` on windows-latest; both must resolve cleanly
- Any lockfile entry with `; sys_platform != "darwin" and sys_platform != "win32"` is flagged as suspicious — review or remove
- Choose one solver, document it: e.g., "uv as canonical resolver per v3.1" — written in `docs/dev/dep-management.md`
- Cross-link Pitfall 6 (constraint enumeration) — Linux-only is on the auto-reject list

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2). Per-platform lockfile strategy set at plan time.

---

## Medium Pitfalls

### Pitfall 21: Visual Regression Tests Flaky from Font Rendering / Sub-Pixel / GPU Variance Across Test Machines

**Severity:** Medium (gates start producing false-negatives; team relaxes thresholds; real regressions slip)

**What goes wrong:**
v3.0 Phase 43 shipped Tier-1 UI surface zero-HIGH gate via paired `gsd-ui-checker` + `gsd-ui-auditor`. v3.1's mascot retargets + installer wizard + e2e MacBook UI all add new visual surfaces. Visual regression Playwright/Percy tests across macOS Sonoma + macOS Sequoia + Win 10 + Win 11 produce sub-pixel font diffs (different font hinting), GPU-blended shadow variations, color-profile diffs (P3 vs sRGB). Flakiness rate >5% → team auto-retries → CI runs longer → flake threshold relaxed → real regression slips.

**Why it happens:**
Visual regression at the pixel level is famously flaky cross-OS. SSIM-tolerant comparison helps but trades sensitivity. Without a calibrated reference image set per (OS, font, GPU) tuple, every cross-OS test is a roll of the dice.

**Warning signs (in PLAN.md):**
- Plan adopts pixel-perfect visual regression without naming SSIM threshold
- No per-OS reference images
- No "flaky-test rerun budget" — silent auto-retry
- Plan does not reference v3.0 P85-OVERRIDE-RETIRED Decision Log discipline (real gates, not paper gates)

**Prevention:**
- Reuse v3.0 Phase 43 paired auditor+checker pattern — that's component-aware, not pixel-aware
- For pixel comparisons that ARE required (mascot pose at frame 30), use SSIM ≥ 0.95 not exact match
- Reference images per (OS, OS-version, scale-factor) tuple in `tests/visual/refs/<os>-<version>-<scale>/`
- Flaky tests do NOT auto-retry; flag for human triage
- Re-flag v3-shipped P22 (mascot opaque chrome regression) — vitest computed-style snapshot is the right discipline, not pixel diff

**Phase to address:**
v3.1 e2e MacBook pass + mascot emotion phase. Visual-test strategy set at plan time.

---

### Pitfall 22: E2E Test Reports Are Generated as `.md` Files That Trip the Anti-Slop Blocklist — Reports Get Auto-Sanitized, Losing Diagnostic Info

**Severity:** Medium (related to Pitfall 5 — e2e reports as a special case; reports get sanitized of useful failure prose; debugging gets harder)

**What goes wrong:**
The e2e MacBook pass produces a verification report — "this session ran fine, here are the screenshots, here's the timeline, here's what went wrong on this frame." Natural failure-mode prose uses words like "the mascot deeply misaligned during the breakdown" — `\bdeeply\s+\w+` regex match. The report tries to merge; blocklist fires; the report gets auto-rewritten by an over-eager fix-it loop until it passes the blocklist, losing diagnostic information.

**Why it happens:**
Same root as Pitfall 5 — blocklist tuned for customer-facing prose applied to internal reports.

**Warning signs (in PLAN.md):**
- E2E report template uses freeform prose
- No "diagnostic-prose-allowlist" path
- Plan does not separate "customer-facing report" from "internal diagnostic report"

**Prevention:**
- E2E reports use structured fields (frame, expected, actual, delta, screenshot path) — not freeform prose
- The diagnostic-prose section is in a fenced code block (the blocklist gate skips code blocks, or should — verify with a unit test)
- If a report MUST have freeform prose, write it under Pitfall 5 vocabulary discipline (substitution dictionary)
- Internal-only path: store reports in `.planning/phases/<NN>-<slug>/REPORT.md` — confirm the blocklist is scoped to `README.md` + customer-facing surfaces, NOT to `.planning/`

**Phase to address:**
v3.1 e2e MacBook pass phase (target feature #4). Report template set at plan time.

---

### Pitfall 23: Dep-Opportunity Scan Surfaces a Beat-Grid Replacement (Beat This! / madmom) That's Tempting But Inflates Bundle Past 350 MB

**Severity:** Medium (the `v3.x backlog` already lists "Beat This! via Rust sidecar — non-Gemini beat-grid, closes 'AI reacts off-beat' hallucination class; gated on install-size budget" — exactly the trap to avoid in v3.1)

**What goes wrong:**
The scan surfaces Beat This! and madmom as candidates for the "AI reacts off-beat" hallucination class. Both are CPU-heavy ML beat-trackers; bundling either adds ~100–200 MB (model weights + dependencies). v3.x backlog explicitly defers this. A scan-evaluator subagent under `gsd-autonomous fully` may rate it green based on "closes hallucination class" without checking the install-size impact.

**Why it happens:**
The scan rubric values "closes hallucination class" highly (`project_anti_slop_grounded_gemini_thesis`). Install size is a separate axis. Without explicit cross-check, green on one axis ships green overall.

**Warning signs (in PLAN.md):**
- Scan adopts a model-weighted dep without an install-size delta
- Plan does not reference the v3.x backlog deferral
- No 350 MB total-bundle ceiling assertion

**Prevention:**
- Cross-link the dep-opportunity-scan output to the v3.x backlog list — any candidate already in backlog stays in backlog, not promoted to v3.1
- Install-size delta is a mandatory column in the green/yellow/red rubric
- 350 MB total-bundle ceiling assertion in CI: `du -bsh dist/vibemix.dmg` reported and gated
- For Beat This! specifically: confirm "gated on install-size budget" stance from `PROJECT.md` v3.x backlog — defer to v3.x

**Phase to address:**
v3.1 dep-opportunity-scan phase (target feature #3). Backlog cross-link is a phase prerequisite.

---

### Pitfall 24: Sidecar Bundle Schema Path Bug (v0.1.0-rc1 Carryover) Reopens When v3.1 Installer Refactors Sidecar Bundling

**Severity:** Medium (memory `project_v0_1_0_rc1_open_bugs` flags "sidecar bundle schema path" as still-open at end of session 2026-05-13; v3.1 install touch is the natural place for it to reopen)

**What goes wrong:**
v0.1.0-rc1 had a sidecar PyInstaller bundle path bug — at runtime, the sidecar binary could not find its bundled resources because the schema path resolved to the wrong root. v3.1 installer work will refactor sidecar bundling (PyInstaller --onefile → --onedir per Pitfall 17, or AV-friendly rebuild). The schema path bug can silently reopen if the refactor doesn't preserve the path-resolution fix.

**Why it happens:**
Path resolution in bundled Python is fragile (sys._MEIPASS, sys.executable, __file__ — all have subtle differences). Fix is usually a single helper function; refactoring around it can break it.

**Warning signs (in PLAN.md):**
- Plan refactors sidecar bundling without referencing the v0.1.0-rc1 fix location
- No regression test for the schema-path resolution
- No "sidecar starts and finds its resources" smoke test in INSTALL-VM-RUN matrix

**Prevention:**
- Locate the v0.1.0-rc1 fix (search for `sys._MEIPASS` + path-resolution helper) — confirm the test asserting resource resolution still exists and passes
- Add the test to the INSTALL-VM-RUN matrix
- Cross-link `project_v0_1_0_rc1_open_bugs` in the install-phase CONTEXT.md so the regression risk is in scope

**Phase to address:**
v3.1 one-click install phase (target feature #1). Sidecar bundling discipline carries the fix forward.

---

### Pitfall 25: BlackHole 48 kHz Format Requirement Lost in Audio-Device Auto-Config Step

**Severity:** Medium (memory `project_v4_canonical_baseline` documents the 48 kHz requirement; if auto-config picks a different rate, mic-as-Part-2 ring + lookahead alignment all silently break)

**What goes wrong:**
v3.0 Phase 40 shipped mic-as-Part-2 (12s ring + AI-talk zero-fill at sounddevice callback boundary) + lookahead-as-Part-3. The whole audio path assumes 48 kHz BlackHole input. If the v3.1 installer auto-creates a Multi-Output Device with a default 44.1 kHz sample rate (CoreAudio default for older Macs), every downstream timestamp / event detector / cooldown tuning drifts by ~9%. v4 chat-tested cooldowns (PHASE 10s / LAYER_ARRIVAL 10s / MIX_MOVE 14s / HEARTBEAT 45s / TRACK_CHANGE 5s) all assume 48 kHz. Silent regression.

**Why it happens:**
Multi-Output Device creation via osascript or system_profiler doesn't always preserve sample rate from the source. Default fallback varies by macOS version.

**Warning signs (in PLAN.md):**
- Audio device auto-config script does not explicitly set `kAudioFormatLinearPCM` + 48000 Hz
- Plan does not reference `project_v4_canonical_baseline` BlackHole 48 kHz requirement
- No "verify sample rate after device creation" smoke test
- Plan does not check Multi-Output Device sample rate at app startup

**Prevention:**
- Multi-Output Device creation script asserts 48 kHz sample rate; if creation falls back to other rate, abort and surface loud error in wizard
- App startup re-checks BlackHole input sample rate; if != 48 kHz, show a remediation card with one-tap Audio MIDI Setup deep-link
- INSTALL-VM-RUN smoke test verifies sample rate post-install
- Cross-link `project_v4_canonical_baseline` in the install-phase CONTEXT.md

**Phase to address:**
v3.1 one-click install phase (target feature #1). Sample-rate discipline set at plan time.

---

### Pitfall 26: Dep-Audit Re-Pins SDK Versions That Were Specifically Frozen for VCR Cassette Replay Compatibility

**Severity:** Medium (related to Pitfall 1 but specifically about the VCR replay path; subtle bump of `google-genai` breaks every cassette)

**What goes wrong:**
v3.0 GATE-02 pre-stage discharge says "VCR cassettes populated via `VCR_RECORD_MODE=new_episodes`" — cassettes are pending re-record. If v3.1 dep audit bumps `google-genai` even by a patch version, the cassette's stored request signatures (header, body, multipart boundary) can change format, replays fail signature match, the hallucination-gate proxy fast-lane stops working. v3.0 SHIP-CUT depends on this gate.

**Why it happens:**
Patch bumps look harmless. VCR uses request fingerprinting that's sensitive to even header re-ordering.

**Warning signs (in PLAN.md):**
- Lockfile bumps `google-genai` / `livekit-agents` / `livekit-plugins-google` without re-record step
- Plan does not check GATE-02 cassette status
- No `pytest tests/eval/ -k cassette` after lock bump

**Prevention:**
- Lock bumps of Gemini / LiveKit SDKs require `VCR_RECORD_MODE=new_episodes` re-record step in the same PR
- Cassette signatures versioned and committed alongside cassettes; bump triggers re-sign
- CI gate: lockfile diff that touches Gemini-related deps cannot merge without cassette re-record evidence (file mtime > lockfile mtime)
- Cross-link v3.0 GATE-02 pre-stage discharge in v3.1 dep-audit phase CONTEXT.md

**Phase to address:**
v3.1 dep audit/pin phase (target feature #2). Cassette discipline coupled to SDK bumps.

---

### Pitfall 27: `Tauri Capability Missing for Drag` (v0.1.0-rc1 Carryover) Surfaces Again in v3.1 Installer Window Or Wizard

**Severity:** Medium (memory `project_v0_1_0_rc1_open_bugs` flags "Tauri capability missing for drag" — installer/wizard windows may inherit the same gap)

**What goes wrong:**
v0.1.0-rc1 had a Tauri capability missing for window-drag. v3.1's one-click installer wizard is a NEW WebviewWindow (or reuses session-window patterns). Without explicit `window:default` / `window:allow-start-dragging` capability grants, the wizard window cannot be dragged by the user — feels broken.

**Why it happens:**
Tauri 2 capability system is allowlist-based. Each window inherits the default set unless overridden. New windows added in v3.1 may not have capabilities scoped correctly.

**Warning signs (in PLAN.md):**
- New WebviewWindow added without capabilities review
- `tauri.conf.json5` capabilities section not modified
- Plan does not reference `project_v0_1_0_rc1_open_bugs` Tauri-drag carryover

**Prevention:**
- Every new WebviewWindow in v3.1 explicitly lists its capabilities in `tauri.conf.json5`
- Smoke test: each window can be dragged from its title bar / handle
- Cross-link `project_v0_1_0_rc1_open_bugs` in install-phase CONTEXT.md

**Phase to address:**
v3.1 one-click install phase (target feature #1) for installer/wizard window. Capability hygiene set at plan time.

---

### Pitfall 28: `nowplaying-cli` Homebrew Dep Not Installed by One-Click Installer → Track Lookahead Path Silently Broken

**Severity:** Medium (lookahead-as-Part-3 from v3.0 Phase 40 depends on `nowplaying-cli` for current-track detection; if missing, lookahead skips silently — closing a hallucination class re-opens)

**What goes wrong:**
v3.0 Phase 40 AUDIO-02 + AUDIO-04 ships lookahead-as-Part-3 via ffmpeg + mdfind + `nowplaying-cli`. `nowplaying-cli` is a Homebrew-installed Mac binary (`/opt/homebrew/bin/nowplaying-cli`) per `CLAUDE.md` Platform Requirements. Fresh-install macOS does NOT have it. One-click installer must either bundle it OR install it as a step. If neither happens, lookahead silently degrades to "no lookahead available" — the anti-slop class "AI reacts after the moment passed" reopens without a loud signal.

**Why it happens:**
The dep is a Homebrew binary, not a Python package. Installer authors think pip / Python deps and miss system-level binaries.

**Warning signs (in PLAN.md):**
- Plan does not enumerate `nowplaying-cli` as a runtime dep
- No "verify nowplaying-cli on PATH at startup" smoke test
- No bundle decision (ship the binary vs. brew-install vs. fail-fast)

**Prevention:**
- Decision: bundle `nowplaying-cli` binary inside the app bundle (it's ~50KB, MIT-licensed, https://github.com/kirtan-shah/nowplaying-cli) — eliminates the Homebrew dep
- Alternative: detect at startup; if missing, surface a card "Install Homebrew + nowplaying-cli for track lookahead support" with one-tap brew command
- Smoke test in INSTALL-VM-RUN matrix: verify lookahead path works post-install
- Cross-link v3.0 Phase 40 AUDIO-02/04

**Phase to address:**
v3.1 one-click install phase (target feature #1). Binary bundling discipline set at plan time.

---

### Pitfall 29: Mascot Three.js Memory Leak Under Emotion-State Churn — New Real GLBs Stress Test the Disposal Path

**Severity:** Medium (v3-shipped P19 is about crossfade discontinuity at single moment; this is about cumulative leak over a 2h DJ session)

**What goes wrong:**
Three.js AnimationMixer, BufferGeometry, Material, Texture — all need explicit `.dispose()` when retiring. The v2.1 Phase 31 4-layer additive state machine cycles emotion clips frequently. Adding 5+ real anticipation GLBs (VIS-04) means more disposal points. Without `dispose()` discipline, a 2-hour DJ session accumulates ~100MB of GPU memory; the mascot becomes the largest memory consumer in the app; eventually GPU crash or noticeable jank.

**Why it happens:**
Three.js doesn't garbage-collect GPU resources — explicit disposal is required. Easy to forget on every code path.

**Warning signs (in PLAN.md):**
- Plan adds new GLBs without checking the existing disposal pattern
- No long-running memory profile test
- No `WEBGL_lose_context` / `THREE.WebGLRenderer.info` audit

**Prevention:**
- Soak test: 2-hour synthetic emotion-state churn (200 clip transitions); assert renderer.info.memory.geometries / textures plateaus, not grows
- Disposal checklist: for every new clip / texture, verify the retire-path calls .dispose()
- THREE.WebGLRenderer.info logged hourly in dev mode; surfaces leaks early
- Cross-link v3-shipped P19 (crossfade) and P23 (GLB size) — same Three.js surface

**Phase to address:**
v3.1 mascot emotion phase (target feature #5). Memory discipline shipped with new GLBs.

---

### Pitfall 30: `gh release create` Auto-Triggered by an Over-Eager v3.1 Subagent Bypasses `cut_release.sh` 6-Gate Pre-Flight

**Severity:** Medium (v3.0 explicitly built `cut_release.sh` 6-gate pre-flight specifically because `gh release create` is destructive and irreversible; a v3.1 subagent that doesn't know the rule can fire it)

**What goes wrong:**
v3.0 Phase 45 SHIP-07 says: "`gh release create v3.0.0-rc1 --draft` after `cut_release.sh` 6-gate green + tag-regex bump prerequisite." `launch_trigger.sh --live` has a triple-env gate. The discipline is: humans don't fire `gh release create` directly; CI fires it after `cut_release.sh` gates pass. A v3.1 subagent under `gsd-autonomous fully` mode that has shell access could run `gh release create` directly thinking "I'm just creating a draft" — destroys the gate discipline.

**Why it happens:**
`gh release create --draft` looks safe ("it's just a draft, I can delete it"). But the act of creating it (a) triggers webhook fans-out, (b) publishes the tag to git history, (c) starts the SmartScreen reputation clock incorrectly. Reversible in theory, embarrassing in practice.

**Warning signs (in PLAN.md):**
- Subagent prompt has `gh` CLI in tool list without restriction
- Plan does not name `cut_release.sh` as the only valid release path
- No "do NOT run `gh release create` directly" reminder
- `gsd-autonomous fully` mode is treated as carte blanche for write commands

**Prevention:**
- Subagent prompt template: explicit DO-NOT list — `gh release create`, `git push --force`, `git tag -d` on shared tags, anything touching `release.yml` without P46 audit
- `gh release create` requires Kaan-action-required deferral per `feedback_autonomous_no_grey_area_pause` (only destructive risk + privacy still pause autonomy)
- Cross-link v3.0 §SHIP-07 — `cut_release.sh` is the only path
- Pre-commit hook in repo: `gh release create` in any committed script raises a warning

**Phase to address:**
All v3.1 phases that touch CI / release infra. Subagent prompt template discipline applies broadly.

---

### Pitfall 31: Universal2 Sidecar Build Misconfigured After v3.1 Refactor — Apple Silicon User Sees Rosetta Prompt

**Severity:** Medium (v2.1 Phase 27-06 fixed the lipo-merge → target-triple convention; v3.1 refactor risks reopening)

**What goes wrong:**
v2.1 Phase 27-06 documented: "Universal2 sidecar — research-corrected from lipo-merge to target-triple convention (PyInstaller PKG archive embeds only in last merged slice). Eliminates Rosetta prompt on Apple Silicon." v3.1's sidecar bundling refactor (Pitfall 17, Pitfall 24) risks reverting to a lipo-merge approach, reopening the Rosetta prompt on Apple Silicon — one of the most visible "feels janky" tells for a Mac app.

**Why it happens:**
target-triple is non-obvious. Engineer refactoring sidecar may default back to lipo for simplicity.

**Warning signs (in PLAN.md):**
- Plan modifies PyInstaller build commands without referencing target-triple
- No `lipo -info dist/sidecar` verification step
- Build runs on x86_64 only without arm64 cross-build

**Prevention:**
- PyInstaller build uses target-triple convention; documented in `docs/dev/sidecar-build.md`
- Verification: `lipo -info dist/sidecar` must list both `x86_64` and `arm64` slices
- Apple Silicon Mac VM in INSTALL-VM-RUN matrix verifies no Rosetta prompt
- Cross-link v2.1 Phase 27-06

**Phase to address:**
v3.1 one-click install phase (target feature #1). Sidecar build discipline preserved.

---

### Pitfall 32: WASAPI IMMNotificationClient Subscription Lost in Windows-Side Installer Refactor — Mid-Session Default-Device-Change No Longer Handled

**Severity:** Medium (v2.1 Phase 27-06 also shipped this Windows-side fix; v3.1 refactor risks)

**What goes wrong:**
v2.1 Phase 27-06: "WASAPI `IMMNotificationClient` subscription handles mid-session default-device-change on Windows." If a user changes their default audio device mid-session (common with USB DJ controllers being plugged in / out), the WASAPI client gets notified and adapts. v3.1 Windows installer refactor may remove or break this subscription.

**Why it happens:**
WASAPI plumbing is C-side; refactor surface looks Python/installer-side; underlying COM client may be touched accidentally.

**Warning signs (in PLAN.md):**
- Plan modifies Windows audio plumbing without referencing IMMNotificationClient
- No "change default device mid-session" smoke test on Windows

**Prevention:**
- Smoke test on Windows: open vibemix, change default audio device via Windows Settings, verify vibemix adapts within 5s
- Cross-link v2.1 Phase 27-06

**Phase to address:**
v3.1 one-click install phase (target feature #1) — Windows side.

---

### Pitfall 33: One-Click Installer's "Configures Audio Devices" Step Wrecks User's Existing CoreAudio / WASAPI Setup

**Severity:** Medium (DJ users have curated audio setups; an installer that auto-configures audio is the worst kind of "helpful" — destroys hours of preference work)

**What goes wrong:**
"Configures audio devices, and lands on a ready-to-run app — zero terminal commands" can be over-interpreted as "set vibemix as the default device" or "rewrite the Multi-Output Device list." Pro DJs have meticulous audio routing — primary output for speakers, headphone output for cue, BlackHole capture for streaming. An installer that overrides these settings without consent destroys their setup.

**Why it happens:**
"Configure for the user" feels helpful. For audio specifically, it's invasive.

**Warning signs (in PLAN.md):**
- Plan says "set vibemix as default output" or "rewrite Multi-Output Device list"
- No "preserve existing user audio configuration" assertion
- No "configures audio devices" scope definition

**Prevention:**
- Scope of "configures audio devices" is **vibemix's INPUT** (BlackHole detection) and **vibemix's OUTPUT** (headphone passthrough), nothing else
- System-level defaults: never touched. Existing Multi-Output Devices: never modified. Existing routing: never modified.
- Wizard asks before any system-level change: "Create a Multi-Output Device that routes djay output to BlackHole + your speakers? [Yes/No/Show me first]"
- INSTALL-VM-RUN test: install on a VM with pre-existing custom audio routing; verify routing preserved post-install

**Phase to address:**
v3.1 one-click install phase (target feature #1). Audio-config scope set at plan time.

---

### Pitfall 34: Bravoh-Side Proxy Rate-Limit Tightened During v3.1 Without Updating Vibemix Client's Backoff Strategy

**Severity:** Medium (proxy and client drift independently; v3.1 doesn't directly touch proxy but dep-opportunity-scan may suggest a tenacity replacement that doesn't match proxy's actual rate-limit response shape)

**What goes wrong:**
Bravoh proxy returns 429 with `Retry-After` header. Client uses tenacity with exponential backoff. If v3.1 dep-opportunity-scan suggests replacing tenacity with `backoff` library or `httpx` retry middleware, the new code may not honor `Retry-After` or may use a different jitter profile. Under viral load (v3-shipped P30/P39), proxy bombs but client retries aggressively — makes the bombing worse.

**Why it happens:**
"Switch retry library" looks like a dep-hygiene win. Retry library semantics differ.

**Warning signs (in PLAN.md):**
- Plan proposes replacing tenacity / backoff library
- No `Retry-After` header handling verification
- No load test against the proxy with the new library

**Prevention:**
- Retry library swap is yellow-rated in the dep-opportunity-scan rubric — gated on Bravoh proxy contract testing
- Retry library MUST honor `Retry-After`; tests verify (mocked proxy returns 429 with `Retry-After: 30`, client waits 30s)
- Cross-link v3-shipped P30 + P39

**Phase to address:**
v3.1 dep-opportunity-scan phase (target feature #3). Retry-library swap gate.

---

### Pitfall 35: Anti-Slop Blocklist Discovery — v3.1 Installer Adds a New Slop Token To the Blocklist That Was Already in Existing v3.0 Code Comments

**Severity:** Medium (blocklist additions for installer prose retroactively catch comments in v3.0 code that were grandfathered; full repo lint fails)

**What goes wrong:**
The v3.0 anti-slop blocklist has 15 tokens. If v3.1 work expands the blocklist (e.g., adding "best-in-class", "intuitive", "premium" for installer prose discipline), the new tokens may exist in v3.0 code comments / docstrings / PLAN.md files that were green-lit at v3.0 close. CI gate fires on the full repo, blocks merge of the v3.1 blocklist expansion.

**Why it happens:**
Blocklist scope is repo-wide. Expanding it retroactively trips legacy text.

**Warning signs (in PLAN.md):**
- Plan expands blocklist without grep-scan against existing repo
- No "audit hits before expanding" step

**Prevention:**
- Before adding any blocklist token, grep entire repo for it; surface every hit; mass-rewrite as part of the same PR
- Blocklist scope explicit: customer-facing surfaces only (`README.md`, `tauri/ui/public/index.html`, install/wizard copy) — not `.planning/`, not docstrings, not internal comments
- If scope is repo-wide: budget the cleanup cost upfront, do it as a single PR

**Phase to address:**
v3.1 prose-touching phases. Blocklist discipline set at plan time.

---

### Pitfall 36: New Mascot GLBs Sourced From Polyhaven / Sketchfab / Hyper3D Carry CC-BY or Non-Commercial License That Conflicts With Open-Source Distribution

**Severity:** Medium (mascot asset licensing — CC-BY-NC or "personal use only" gets bundled into an open-source download, license-conflict)

**What goes wrong:**
"GLB assets land real (not placeholder)" can be solved fast by pulling pre-made models. Polyhaven (CC0 — fine), Sketchfab (variable license — many CC-BY-NC), Hyper3D (commercial terms), TurboSquid (Royalty-Free with restrictions). Bundling a CC-BY-NC model into an open-source MIT/Apache-licensed app violates the asset's license.

**Why it happens:**
Asset hunting goes fast; license checking goes slow. Mascot is "art" — license diligence is often skipped.

**Warning signs (in PLAN.md):**
- Plan adopts assets without per-asset license attribution
- No `tauri/ui/public/mascot/ASSETS.md` listing source + license per file
- Plan uses Sketchfab as a source without "Free + Commercial use OK" filter applied

**Prevention:**
- Per-asset license attribution in `tauri/ui/public/mascot/ASSETS.md`: source URL, author, license, attribution requirement, modifications made
- Asset license rubric: CC0 / Public Domain (auto-green), CC-BY with attribution (green if attribution added), CC-BY-NC / Royalty-Free (auto-red), commercial (auto-red unless purchased for the project)
- Mixamo retargets are user-generated (Adobe-account flow) — Adobe's Mixamo terms allow commercial use of generated content; verify still true
- Cross-link `project_mascot_as_vtuber_personality_surface` — the mascot is a custom character ("Neon Rebel"), so the base mesh is custom not third-party; only the **animations** are Mixamo-sourced

**Phase to address:**
v3.1 mascot emotion phase (target feature #5). Asset license discipline set at plan time.

---

## Low Pitfalls

### Pitfall 37: Onboarding Stopwatch Time Budget From v2.1 Phase 33 Slips When v3.1 Adds Wizard Steps

**Severity:** Low (v2.1 Phase 33 shipped onboarding stopwatch; v3.1 wizard additions may push past 60s budget — INSTALL-60S-CHECK in v3.0 SHIP-05)

**What goes wrong:**
v3.0 SHIP-05 = `INSTALL-60S-CHECK` (still in pre-stage discharges). v3.1 wizard may add steps (BlackHole detection card + TCC card + audio device config + mascot intro) that push first-launch to >60s. Promise of "ready-to-run app — zero terminal commands" implies fast.

**Why it happens:**
Wizard steps accumulate organically.

**Prevention:**
- Stopwatch checkpoint per wizard step in dev mode; total budget 60s
- Skip steps already-configured (idempotent wizard)
- Cross-link v3.0 SHIP-05

**Phase to address:**
v3.1 one-click install phase (target feature #1). Stopwatch budget enforced in INSTALL-VM-RUN matrix.

---

### Pitfall 38: GitHub-Star Goal Pressure Pushes Polish-Over-Substance in the e2e MacBook Report

**Severity:** Low (memory `project_github_star_goal` — 500-1000+ stars; pressure to "look polished" pushes the e2e report into marketing prose territory)

**What goes wrong:**
E2E MacBook pass report can drift into marketing prose ("vibemix performed beautifully on a 90-minute Hard Tek set") instead of evidence-grounded findings ("90-min session captured; 142 reactions fired; 3 stripped citations; 0 mascot wedges; 1 visible frame-time spike at t=42m"). Marketing prose feels productive but tells you nothing.

**Why it happens:**
"Star goal" pressure subconsciously biases toward "make it look successful." Anti-slop blocklist catches the worst tokens but doesn't catch the substance gap.

**Prevention:**
- Report template forces evidence fields (counts, timestamps, screenshots)
- No marketing prose section in report
- Kaan reviews substance, not polish
- Cross-link `project_anti_slop_grounded_gemini_thesis` — evidence-grounded, not vibe-grounded

**Phase to address:**
v3.1 e2e MacBook pass phase (target feature #4). Report template enforces.

---

### Pitfall 39: Mascot Cache Invalidation Across Versions — User Upgrades, Mascot Looks Different, Cache Path Doesn't Migrate

**Severity:** Low (mascot animations cached in `%LOCALAPPDATA%\vibemix\mascot-cache\`; if cache path changes between versions, user's "preferred mascot mood" preferences lost)

**What goes wrong:**
v3.1 adds real GLBs replacing placeholders. If mascot cache directory schema changes, user's per-session mascot state preferences are lost.

**Why it happens:**
Cache schema evolves; migration path not always considered.

**Prevention:**
- Versioned cache directory: `mascot-cache/v3/` not `mascot-cache/`
- On version bump, migrate or invalidate cleanly
- Document in upgrade notes

**Phase to address:**
v3.1 mascot emotion phase (target feature #5).

---

### Pitfall 40: SmartScreen Reputation Re-Set By Major Version Bump in Installer Name

**Severity:** Low (Windows SmartScreen reputation accrues per signed binary hash + publisher; if v3.1 changes installer filename pattern, reputation may partially reset)

**What goes wrong:**
SmartScreen reputation is tied to the SignPath certificate, not the filename — so reputation should carry. BUT some heuristics also key off filename patterns; renaming `vibemix-0.1.0-rc1.msi` to `vibemix-3.1.0.msi` may slightly degrade. Lower priority because v3.0 already does the rename for SHIP-CUT.

**Prevention:**
- Filename pattern stable: `vibemix-<version>.<arch>.msi`
- SmartScreen reputation observation post-rename (v3.0 SHIP-12 already covers this passively)

**Phase to address:**
v3.1 one-click install phase (target feature #1). Filename pattern locked.

---

## Cross-Cutting Pitfalls

### Pitfall 41: v3.1 Engineering-Green Close While v3.0 SHIP-01..13 External Clock Still Pending — Public RC Cut Happens Months Apart From v3.1 Engineering Close

**Severity:** Medium (v3.1 closes "ready"; v3.0 SHIP-CUT still pending external Apple Dev + SignPath approvals; user sees a release that bundles v3.0+v3.1 but tested only at v3.0 close OR drift accumulates)

**What goes wrong:**
v3.0 closed 2026-05-17 engineering-green with 22 carveouts in KAAN-ACTION-LEGAL §SHIP-01..13. Apple Dev Agreement (Francesco) + SignPath OSS Foundation approval (~1-week SLA) are external clocks. v3.1 closes engineering-green also pre-approval. When external clocks finally land, the actual RC cut happens against a state that combines v3.0 + v3.1 work. If integration drift exists, it surfaces only at SHIP-CUT.

**Why it happens:**
`gsd-autonomous fully` mode + external clock = engineering can keep going while approvals are pending. Risk: cumulative drift.

**Prevention:**
- v3.1 close gate: confirm SHIP-04 / SHIP-05 (INSTALL-VM-RUN + INSTALL-60S-CHECK) on a fresh-VM matrix BEFORE marking v3.1 engineering-green
- v3.0 + v3.1 cut a single combined RC when approvals land (`v3.1.0-rc1` not `v3.0.0-rc1` after v3.1 ships)
- `audit_ship_v1_decision.py` (v3.0 SHIP-13) carried forward as the source-of-truth audit for combined v3.0+v3.1 state
- Cross-link `feedback_autonomous_no_grey_area_pause` — defer-to-KAAN-action is the contract, not pause

**Phase to address:**
v3.1 milestone-level (cross-cutting). Combined-RC discipline set in milestone-audit.

---

### Pitfall 42: Subagent Spawned With `Agent(isolation="worktree")` for Dep-Audit Bumps Lockfile in Parallel With Install-Phase Subagent — Merge Conflict at the Most Sensitive File

**Severity:** Medium (related to Pitfall 7 but specifically about lockfile merge conflicts; lockfile conflicts are the highest-risk merge in any project)

**What goes wrong:**
v3.1 launches dep-audit subagent (touches `requirements.lock`) and install-phase subagent (also touches `requirements.lock` to add `nowplaying-cli` bundling deps or AV-friendly PyInstaller flags) in parallel. Both diverge from `main`. Merge produces a lockfile conflict. Auto-merge tools resolve naively, producing a non-resolved lockfile that pip can't install.

**Why it happens:**
Lockfiles are merge-hostile by nature.

**Prevention:**
- Lockfile is touched by exactly ONE subagent per phase batch — declared in PLAN
- If two subagents both touch lockfile: sequential, not parallel
- Lockfile merge conflicts resolved by re-running hermetic build (Pitfall 1), not by manual conflict resolution
- Cross-link Pitfall 1 + Pitfall 7

**Phase to address:**
v3.1 milestone-level (cross-cutting). Subagent orchestration discipline set in orchestrator template.

---

### Pitfall 43: v3.1 Adds Cost Surface (Mixamo Adobe Account, SignPath EV Cert Backup, GitHub Actions Minutes for Cross-OS Matrix) That Pushes Past 50 €/Month Budget

**Severity:** Low (operations budget; minor but accumulates)

**What goes wrong:**
v3.1 work surfaces non-Gemini costs:
- Mixamo Adobe account (free if Personal; CC subscription if commercial — depends on rendering scope)
- SignPath EV cert backup ($200/yr — v3-shipped P6 prevention)
- GitHub Actions minutes (cross-OS matrix for fresh-VM rehearsal — within free tier for OSS repos, but if billed)
- VM images storage (fresh Mac + Win images as build artifacts)

Cumulative could push past `PROJECT.md` 50 €/month budget if not tracked.

**Prevention:**
- Monthly cost rollup includes Mixamo / SignPath / GH Actions / VM storage / Gemini in one view
- Each cost line has a green/yellow/red flag against budget
- Cross-link `PROJECT.md` Budget constraint

**Phase to address:**
v3.1 milestone-level. Cost rollup in milestone-audit.

---

### Pitfall 44: Privacy Rule Confusion — Agent Avoids Reading Test-Rig Configs Or VM Snapshots Thinking They're LLM-Transcripts

**Severity:** Low (memory `feedback_privacy_scope_narrow` explicitly narrows the privacy rule to LLM-transcript paths; agent over-broadens it, blocks legitimate dep-audit / install-test work)

**What goes wrong:**
Memory `feedback_privacy_scope_narrow`: "Privacy rule is narrow — full Mac access otherwise. Off-limits LLM-transcript paths in CLAUDE.md are the ENTIRE rule. Don't gate routine FS/system access behind 'per-task authorization' — Kaan rejected that overthinking explicitly 2026-05-13." If a v3.1 subagent over-broadens — refuses to read `~/Library/Application Support/vibemix/` because "it might contain transcripts" — install-test / dep-audit work stalls.

**Prevention:**
- v3.1 subagent prompts cite `feedback_privacy_scope_narrow` explicitly
- Off-limits paths are the explicit Hermes / LM Studio / OZ list in `/Users/ozai/CLAUDE.md` — nothing else
- vibemix's own appdata is fully accessible

**Phase to address:**
All v3.1 subagent prompts. Privacy scope discipline set in orchestrator template.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Freeze lockfile from Kaan's `.venv` instead of hermetic builder | -1 day CI setup | Ships unused deps + non-reproducible-from-source bundle (Pitfall 1) | Never in v3.1 — hermetic builder is the gate |
| Silent BlackHole auto-install promise | "looks one-click" in plan | Modal-blocked install for 30–40% of fresh macOS users (Pitfall 2) | Never — detect + guide is the contract |
| Test e2e against `mascot.html` instead of Tauri WebView | -2 hours scaffolding | Mascot ships broken; easter egg passes (Pitfall 4) | Never in v3.1 |
| Run e2e against live Gemini in CI | -1 day VCR setup | $50–$200/day burned; budget blows pre-launch (Pitfall 8) | Never — VCR cassettes required |
| Auto-grant TCC permissions via tccutil | "looks polished" | Notarization rejected OR scary modal (Pitfall 15) | Never |
| Skip Step-0 `git merge origin/main` in subagent prompts | -1 line per prompt | 458-commit regression on merge (Pitfall 7, memory-attested) | Never |
| Relax anti-slop blocklist for PLAN.md / install copy | -30 min vocabulary work | Slop vocabulary back-doors into v4+ (Pitfall 5) | Never — vocabulary discipline applies to all .md |
| Per-machine install scope on Windows | "feels professional" | userdata path mismatch on reinstall = data loss (Pitfall 16) | Never — per-user is the contract |
| Treat MacBook pass as single OS check | "Kaan's rig is fine" | Real-user OS-matrix never validated (Pitfall 3) | Never — split #4a / #4b |
| Pull Mascot GLBs from Sketchfab without license check | "fast asset acquisition" | License-conflict at v1.0 ship (Pitfall 36) | Never |
| Bump `google-genai` without re-recording VCR cassettes | -1 hour | Hallucination gate stops working (Pitfall 26) | Never |
| Stack 3+ Kaan-ear surfaces in one window | "milestone close faster" | Quality slips on at least one, or Kaan burns out (Pitfall 18) | Sequence required |
| Run security scanners without diff-mode | "thorough" | Reviewer fatigue → auto-approve → real vuln slips (Pitfall 13) | Diff-mode is the gate |
| Use `gh release create` directly from subagent | "I'm just creating a draft" | Bypasses `cut_release.sh` 6-gate, breaks discipline (Pitfall 30) | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| BlackHole install | Try to silent-install kext | Detect + guide via System Settings deeplink (Pitfall 2) |
| VB-CABLE install | Treat as pip dep | Detect + offer UAC-prompted installer launch (Pitfall 2) |
| `tccutil` writes | Use for Screen Recording / Accessibility grants | Read-only or fail-loud; guide user via deeplinks (Pitfall 15) |
| TCC deeplinks | Use older `x-apple.systempreferences:com.apple.preference.security?Privacy_*` format | Test against macOS 15+ Sequoia format (Pitfall 15) |
| `nowplaying-cli` | Assume Homebrew is installed | Bundle the binary (~50KB MIT) (Pitfall 28) |
| Multi-Output Device creation | Default sample rate | Explicit 48 kHz assertion + retry (Pitfall 25, memory `project_v4_canonical_baseline`) |
| `pip freeze` | Run on dev `.venv` | Run in hermetic Docker builder (Pitfall 1) |
| Lockfile per-platform | Single cross-platform lock | Per-platform locks; CI verifies both resolve (Pitfall 20) |
| `release.yml` edit | Edit without re-running P46 audit | Audit re-runs on every release.yml-touching PR (Pitfall 9) |
| PyInstaller `--onefile` | Default for AV-detection | `--onedir` for less suspicious launch pattern (Pitfall 17) |
| Universal2 sidecar | Use lipo-merge | target-triple convention (Pitfall 31, v2.1 Phase 27-06) |
| WASAPI device-change | Skip IMMNotificationClient | Subscribe to default-device-change (Pitfall 32, v2.1 Phase 27-06) |
| Tauri new WebviewWindow | Inherit default capabilities | Explicit capability allowlist per window (Pitfall 27) |
| Mascot GLB sourcing | Pull from Sketchfab without license filter | CC0 or CC-BY with attribution; rubric in plan (Pitfall 36) |
| Mixamo retarget | Apply to custom rig blindly | Bone-mapping config + visual regression gate (Pitfall 12) |
| Three.js disposal | Skip `.dispose()` on retire | Soak-test asserts memory plateau (Pitfall 29) |
| VCR cassette signatures | Bump SDK without re-record | SDK bumps require cassette re-record in same PR (Pitfall 26) |
| `gh release create` | Run directly from subagent | `cut_release.sh` is the only path (Pitfall 30) |
| Subagent worktree base | Spawn from stale `main` | Step-0 `git merge origin/main` invariant (Pitfall 7, memory `feedback_worktree_must_sync_main_first`) |
| Anti-slop blocklist scope | Repo-wide blanket | Customer-facing surfaces; vocabulary discipline for internal docs (Pitfall 5, Pitfall 35) |
| Dep-opportunity-scan rubric | "Popular dep" = green | Constraint-violation auto-red (Pitfall 6) |
| License audit | Direct deps only | Transitive + native + IPC-vs-embed (Pitfall 10) |
| SBOM generation | One-shot at Phase 34 | CI-gated, every release (Pitfall 14) |
| `pip-audit` output | Cumulative monolithic | Diff-mode vs. baseline (Pitfall 13) |
| Retry library | tenacity → backoff swap | Verify `Retry-After` header semantics (Pitfall 34) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| GLB bundle grows past 25 MB | DMG size > 350 MB | Per-clip 300 KB cap + total 25 MB CI gate (Pitfall 11) | Adding all anticipation clips real |
| Three.js memory leak under emotion churn | GPU memory grows over 2h session | Soak test + dispose discipline (Pitfall 29) | Long DJ sessions with frequent emotion swaps |
| Visual regression test cross-OS flake | 5%+ flake rate trains auto-retry reflex | SSIM ≥ 0.95 + per-OS refs (Pitfall 21) | macOS Sonoma vs Sequoia, Win 10 vs Win 11 |
| Onboarding wizard exceeds 60s | First-launch feels slow | Stopwatch per step, idempotent skip (Pitfall 37) | Adding wizard steps without budget |
| CI e2e burns Gemini quota | $50–$200/day from CI alone | VCR cassettes by default (Pitfall 8) | Naive e2e setup |
| Lockfile merge conflict on parallel subagents | Lockfile won't install | One subagent touches lock per batch (Pitfall 42) | Parallel dep-audit + install work |
| Sample-rate drift from 48 kHz | All cooldowns off by ~9%, anti-slop silently regresses | Multi-Output Device asserts 48 kHz (Pitfall 25) | Auto-config picks default rate |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Silent kext auto-install | Triggers OS modal mid-installer | Detect + guide, not auto-install (Pitfall 2) |
| `tccutil` write attempts | Notarization rejection / scary modal | Read-only; guide via deeplinks (Pitfall 15) |
| Auto-grant TCC for Screen Recording | "vibemix wants to control your computer" prompt | Per-category cards with user consent (Pitfall 15) |
| AV false-positive on PyInstaller `--onefile` | Quarantined at first launch | `--onedir` + AV-vendor pre-whitelisting (Pitfall 17) |
| License contamination from dep-scan | Forces full repo to GPL | License rubric + SBOM diff (Pitfall 10) |
| SBOM stale at release | Supply-chain attestation broken | CI-gated re-gen (Pitfall 14) |
| `gh release create` from subagent | Bypasses release gate discipline | `cut_release.sh` only path (Pitfall 30) |
| Per-machine install on Windows | userdata exposed across users | Per-user scope (Pitfall 16) |
| Mascot asset license violation | Open-source distribution bundles CC-BY-NC | Per-asset attribution + license rubric (Pitfall 36) |
| Subagent worktree from stale base | Regression on merge | Step-0 sync invariant (Pitfall 7) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| One-click installer triggers macOS "system extension blocked" modal | "vibemix asked Apple to install something dangerous" | Detect + guide BlackHole install via System Settings deeplink (Pitfall 2) |
| Wizard auto-configures user's audio setup | DJ's curated routing destroyed | Ask before any system-level audio change (Pitfall 33) |
| Mascot wedges in lean-in pose | "Mascot is broken" | (Already covered by v3-shipped P9 timeout — verify carries forward) |
| Mascot ships with placeholder GLBs | "Why is the mascot generic?" | VIS-04 retargets land real (target feature #5) |
| First-launch macOS Gatekeeper warning | "Mac says malicious — abandon" | (v3-shipped P17 stapler verify — confirm carries forward) |
| Windows SmartScreen warning | "Microsoft says unrecognized — abandon" | (v3-shipped P6 SignPath — confirm carries forward) |
| Third-party AV false-positive | "ESET quarantined vibemix" | `--onedir` + README explain + AV vendor outreach (Pitfall 17) |
| Onboarding wizard >60s | "Slow setup" | Stopwatch per-step + idempotent skip (Pitfall 37) |
| Reinstall loses mascot cache + profile.json | "Data loss on update" | Per-user install scope (Pitfall 16) |
| Track lookahead silently broken on fresh Mac | Anti-slop "AI reacts after the moment passed" returns | Bundle `nowplaying-cli` (Pitfall 28) |
| Multi-Output Device created at 44.1 kHz | Cooldowns drift ~9%, reactions feel off | Explicit 48 kHz (Pitfall 25) |
| Wizard window can't be dragged | "Feels broken" | Capability allowlist per window (Pitfall 27) |
| Mascot looks different after upgrade | "Why did they change my mascot?" | Versioned cache + migration (Pitfall 39) |

---

## "Looks Done But Isn't" Checklist (v3.1-Specific)

- [ ] **One-click installer:** Often missing the macOS system-extension modal path — verify the BlackHole modal copy + Sequoia 15+ deeplink format
- [ ] **One-click installer:** Often missing the "preserve existing audio config" assertion — verify INSTALL-VM-RUN with pre-existing routing
- [ ] **One-click installer:** Often missing `nowplaying-cli` bundling — verify lookahead path works on fresh Mac
- [ ] **One-click installer:** Often missing 48 kHz Multi-Output Device assertion — verify sample-rate check at startup
- [ ] **One-click installer:** Often missing TCC permission cards (one per category with deeplink) — verify wizard guides, never auto-grants
- [ ] **One-click installer:** Often missing per-user install scope assertion on Windows — verify `tauri.conf.json5`
- [ ] **One-click installer:** Often missing PyInstaller `--onedir` (or AV-friendly equivalent) — verify on third-party AV
- [ ] **One-click installer:** Often missing Universal2 target-triple — verify `lipo -info dist/sidecar` shows both slices
- [ ] **One-click installer:** Often missing WASAPI IMMNotificationClient subscription — verify mid-session device change works
- [ ] **One-click installer:** Often missing INSTALL-60S-CHECK stopwatch — verify wizard fits budget
- [ ] **Dep audit/pin:** Often missing hermetic builder for lock generation — verify no `pip freeze` on Kaan's venv
- [ ] **Dep audit/pin:** Often missing per-platform lockfiles — verify Mac + Win both resolve cleanly in CI
- [ ] **Dep audit/pin:** Often missing license rubric — verify rubric in PLAN
- [ ] **Dep audit/pin:** Often missing pip-audit diff-mode — verify only new advisories surfaced
- [ ] **Dep audit/pin:** Often missing SBOM CI gate — verify `release.yml` includes syft step
- [ ] **Dep audit/pin:** Often missing VCR cassette re-record on Gemini SDK bump — verify same-PR re-record
- [ ] **Dep-opportunity scan:** Often missing constraint exclusion-set enumeration upfront — verify Linux / multi-provider / CLAP exclusions listed
- [ ] **Dep-opportunity scan:** Often missing 4-color rubric (red-violation vs red-risk vs yellow vs green) — verify rubric explicit
- [ ] **Dep-opportunity scan:** Often missing v3.x backlog cross-link — verify Beat This! / madmom stay deferred
- [ ] **Dep-opportunity scan:** Often missing install-size delta per candidate — verify size column in rubric
- [ ] **Dep-opportunity scan:** Often missing EXCLUDED.md output — verify rejections logged
- [ ] **E2E MacBook pass:** Often missing #4a (Kaan ear) vs #4b (OS matrix) split — verify two artifacts in PLAN
- [ ] **E2E MacBook pass:** Often missing screencast capture — verify committed (private storage acceptable)
- [ ] **E2E MacBook pass:** Often missing VCR-by-default — verify e2e tests use cassettes
- [ ] **E2E MacBook pass:** Often missing structured report fields — verify no marketing prose
- [ ] **E2E MacBook pass:** Often missing SHIP-04 cross-link in milestone-audit — verify status flagged
- [ ] **Mascot emotion:** Often missing Tauri-WebView-only test target — verify grep gate excludes `mascot.html`
- [ ] **Mascot emotion:** Often missing emotion × event coverage matrix — verify explicit matrix in PLAN
- [ ] **Mascot emotion:** Often missing per-clip 300 KB DRACO cap — verify CI gate
- [ ] **Mascot emotion:** Often missing total 25 MB GLB cap — verify CI gate
- [ ] **Mascot emotion:** Often missing bone-mapping config for Mixamo retargets — verify `rig-map.json` exists
- [ ] **Mascot emotion:** Often missing visual regression on retargeted clips — verify SSIM ≥ 0.95 gate
- [ ] **Mascot emotion:** Often missing memory soak test (2h emotion churn) — verify renderer.info plateau
- [ ] **Mascot emotion:** Often missing per-asset license attribution — verify `ASSETS.md`
- [ ] **Mascot emotion:** Often missing v3-shipped P22 (opaque chrome regression) check — verify vitest snapshot
- [ ] **Cross-cutting:** Often missing Step-0 `git merge origin/main` in subagent prompts — verify orchestrator template
- [ ] **Cross-cutting:** Often missing anti-slop vocabulary discipline on PLAN.md / SUMMARY.md — verify `check_no_slop.py` runs on these
- [ ] **Cross-cutting:** Often missing `gh release create` restriction in subagent prompts — verify DO-NOT list
- [ ] **Cross-cutting:** Often missing Kaan-ear surface sequencing — verify timeline avoids stacking 3+ surfaces
- [ ] **Cross-cutting:** Often missing combined v3.0+v3.1 RC discipline — verify milestone-audit names `v3.1.0-rc1` not `v3.0.0-rc1`

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Lockfile from dev venv shipped (P1) | MEDIUM | Re-generate from hermetic builder, diff, verify VCR cassettes still match, ship hotfix |
| BlackHole silent-install modal trips (P2) | LOW | Wizard copy patch + deeplink fix; no binary regen needed |
| MacBook pass missed OS coverage (P3) | MEDIUM | Run SHIP-04 OS-matrix in parallel before SHIP-CUT; defer if necessary |
| Mascot tested against mascot.html (P4) | LOW | Re-run tests against Tauri WebView; close findings |
| Anti-slop blocklist false-trip (P5) | LOW | Vocabulary substitution + PR; no gate relax |
| Dep-scan adopted a constraint-violator (P6) | LOW | Revert the dep; update EXCLUDED.md |
| Worktree subagent regression (P7) | HIGH (memory-attested 458 commits) | Force orchestrator Step-0 invariant; rebuild PR from fresh sync |
| CI burned Gemini quota (P8) | HIGH | Pause CI live runs; switch to VCR; restore budget |
| `release.yml` regressed signing (P9) | HIGH | Re-run P46 audit; rebuild release artifacts |
| License contamination (P10) | HIGH | Identify GPL dep; remove or IPC-isolate; potentially re-license project |
| GLB bundle past budget (P11) | LOW | DRACO recompress; drop low-priority clips |
| Mixamo retarget broken (P12) | MEDIUM | Bone-mapping config; re-export from Mixamo |
| Security scan noise hides real vuln (P13) | MEDIUM | Diff-mode rollup; triage flagged advisory |
| Stale SBOM shipped (P14) | LOW | Re-gen SBOM; replace release asset; communicate |
| TCC auto-grant tripped notarization (P15) | HIGH | Remove tccutil calls; resubmit notarization |
| Per-machine install loss (P16) | MEDIUM | Migration script in next patch; communicate to affected users |
| AV false-positive (P17) | MEDIUM | Submit AV vendor whitelist requests; ship `--onedir` build |
| Kaan-ear stack burned a surface (P18) | LOW | Sequence remaining surfaces; defer the missed one |
| Audio loopback bootstrap (P19) | LOW | Split into installer-integration + audio-e2e test pyramid |
| Linux-only transitive (P20) | LOW | Switch to per-platform lockfiles; re-resolve |
| Visual regression flake (P21) | MEDIUM | Re-baseline per-OS references; relax SSIM tolerance |
| E2E report sanitized (P22) | LOW | Move diagnostic prose to code blocks |
| Beat This! adopted prematurely (P23) | MEDIUM | Revert; defer to v3.x backlog |
| Sidecar schema path regression (P24) | MEDIUM | Restore v0.1.0-rc1 fix; smoke test |
| 48 kHz drift (P25) | LOW | Multi-Output Device re-create assertion; verify |
| SDK bump broke VCR cassettes (P26) | LOW | Re-record cassettes; commit |
| Tauri capability missing on wizard (P27) | LOW | Add capability; smoke test |
| `nowplaying-cli` missing (P28) | LOW | Bundle binary or detect+guide; ship hotfix |
| Three.js memory leak (P29) | MEDIUM | Disposal audit; soak test |
| `gh release create` fired prematurely (P30) | HIGH | Delete release; revert tag; communicate; rebuild via `cut_release.sh` |
| Universal2 lipo regression (P31) | LOW | Switch to target-triple; rebuild |
| WASAPI subscription lost (P32) | MEDIUM | Restore subscription; smoke test device change |
| Audio config wrecked user setup (P33) | MEDIUM | Scope wizard to vibemix's own devices; document |
| Retry-library broke `Retry-After` (P34) | LOW | Revert library swap or fix `Retry-After` handling |
| Blocklist expansion hit legacy (P35) | LOW | Grep + mass rewrite; ship together |
| Asset license violation (P36) | MEDIUM | Remove offending asset; replace with CC0 or commission |

---

## Pitfall-to-Phase Mapping

| Pitfall | v3.1 Phase | Verification |
|---------|------------|--------------|
| P1 Lockfile from dev venv | Dep audit/pin (#2) | Hermetic builder evidence in PLAN |
| P2 Silent BlackHole install | One-click install (#1) | INSTALL-VM-RUN fresh-VM matrix without BlackHole |
| P3 MacBook pass single-OS | E2E MacBook pass (#4) | Split #4a/#4b in PLAN; OS matrix runs in CI |
| P4 Mascot tested against mascot.html | Mascot emotion (#5) | Grep gate excluding `mascot.html` from tests/ |
| P5 Anti-slop blocklist false-trip | Every prose-touching phase | `check_no_slop.py` runs on PLAN.md / SUMMARY.md |
| P6 Constraint-violating dep | Dep-opportunity scan (#3) | EXCLUDED.md + exclusion-set in PLAN |
| P7 Worktree stale base | All parallel-subagent phases | Step-0 invariant in subagent prompts |
| P8 CI Gemini quota burn | E2E MacBook pass (#4) | VCR cassettes by default + cost-budget assertion |
| P9 release.yml regression | One-click install (#1) | P46 audit re-runs on release.yml-touching PR |
| P10 License contamination | Dep audit (#2) + scan (#3) | License rubric + SBOM diff |
| P11 GLB bundle past budget | Mascot emotion (#5) | 25 MB CI gate |
| P12 Mixamo retarget broken | Mascot emotion (#5) | rig-map.json + SSIM visual gate |
| P13 Security scan noise | Dep audit (#2) | Diff-mode rollup |
| P14 SBOM stale | Dep audit (#2) | CI-gated syft re-gen |
| P15 TCC auto-grant | One-click install (#1) | Wizard guides via deeplinks |
| P16 Per-machine install scope | One-click install (#1) | per-user assertion in tauri.conf |
| P17 AV false-positive | One-click install (#1) | `--onedir` + AV vendor list |
| P18 Kaan-ear surface stack | Milestone-level | Sequenced timeline |
| P19 Audio loopback bootstrap | One-click install (#1) + E2E (#4) | Test pyramid: unit/integration/e2e |
| P20 Linux-only transitive | Dep audit (#2) | Per-platform locks |
| P21 Visual regression flake | E2E (#4) + Mascot (#5) | SSIM ≥ 0.95 + per-OS refs |
| P22 E2E report sanitized | E2E (#4) | Structured fields template |
| P23 Beat This! premature adopt | Dep-opportunity scan (#3) | Backlog cross-link |
| P24 Sidecar schema regression | One-click install (#1) | Smoke test resource resolution |
| P25 48 kHz drift | One-click install (#1) | Multi-Output Device sample-rate assertion |
| P26 SDK bump cassettes | Dep audit (#2) | Same-PR cassette re-record |
| P27 Tauri capability missing | One-click install (#1) | Capability allowlist per window |
| P28 nowplaying-cli missing | One-click install (#1) | Bundle binary |
| P29 Three.js memory leak | Mascot emotion (#5) | 2h soak test |
| P30 gh release create premature | All phases | Subagent prompt DO-NOT list |
| P31 Universal2 lipo regression | One-click install (#1) | `lipo -info` verification |
| P32 WASAPI subscription lost | One-click install (#1) | Mid-session device change smoke |
| P33 Wizard wrecks audio config | One-click install (#1) | Pre-existing routing preservation test |
| P34 Retry library swap | Dep-opportunity scan (#3) | `Retry-After` semantics test |
| P35 Blocklist expansion legacy | Prose-touching phases | Grep + mass rewrite same PR |
| P36 Asset license violation | Mascot emotion (#5) | ASSETS.md + license rubric |
| P37 Onboarding >60s | One-click install (#1) | Per-step stopwatch |
| P38 e2e report marketing prose | E2E (#4) | Evidence-fields template |
| P39 Mascot cache invalidation | Mascot emotion (#5) | Versioned cache path |
| P40 SmartScreen filename reset | One-click install (#1) | Stable filename pattern |
| P41 v3.0+v3.1 RC drift | Milestone-level | Combined-RC naming |
| P42 Lockfile merge conflict | Dep audit + install parallel | Single-subagent-touches-lock rule |
| P43 Cost budget creep | Milestone-level | Monthly cost rollup |
| P44 Privacy scope over-broadened | All subagents | `feedback_privacy_scope_narrow` cited |

---

## Watch For During Plan Phase — Punch List

Grep against every v3.1 PLAN.md and flag if any of these appear without explicit mitigation:

1. **`pip freeze`** without "in hermetic builder" — fires Pitfall 1
2. **"silent install BlackHole"** / **"auto-install BlackHole"** — fires Pitfall 2
3. **"MacBook pass"** without "OS-matrix companion" — fires Pitfall 3
4. **"mascot.html"** in tests/e2e plans — fires Pitfall 4
5. **"seamless"** / **"robust"** / **"leverage"** / **"deeply"** in PLAN prose — fires Pitfall 5
6. **"Linux"** / **"pulseaudio"** / **"pipewire"** / **"CLAP"** / **"MERT"** / **"Demucs"** / **"OpenL3"** / **"whisper"** in dep-scan output without auto-red — fires Pitfall 6
7. **`Agent(isolation="worktree")`** without Step-0 sync invariant — fires Pitfall 7
8. **"run 30-min DJ session in CI"** without VCR — fires Pitfall 8
9. **`release.yml`** edited without P46 audit re-run — fires Pitfall 9
10. **`pip-licenses`** without `--with-system` or transitive — fires Pitfall 10
11. **New GLBs** without per-clip + total-size budget — fires Pitfall 11
12. **Mixamo retargets** without bone-mapping config + visual gate — fires Pitfall 12
13. **`pip-audit`** without `--ignore-vuln` baseline + diff-mode — fires Pitfall 13
14. **No `syft`** in release.yml or dep-audit phase — fires Pitfall 14
15. **`tccutil`** in installer scripts — fires Pitfall 15
16. **"per-machine install"** on Windows — fires Pitfall 16
17. **`pyinstaller --onefile`** without AV strategy — fires Pitfall 17
18. **3+ Kaan-ear surfaces** in same window — fires Pitfall 18
19. **Audio loopback in CI** without 2-image VM strategy — fires Pitfall 19
20. **Lockfile** without per-platform separation — fires Pitfall 20
21. **Visual regression** without SSIM + per-OS refs — fires Pitfall 21
22. **E2E report** as freeform prose — fires Pitfall 22
23. **Beat This!** / **madmom** in dep-scan green list — fires Pitfall 23
24. **Sidecar refactor** without v0.1.0-rc1 schema-path test — fires Pitfall 24
25. **Multi-Output Device** without 48 kHz assertion — fires Pitfall 25
26. **`google-genai`** bump without cassette re-record — fires Pitfall 26
27. **New WebviewWindow** without capability allowlist — fires Pitfall 27
28. **`nowplaying-cli`** assumed available — fires Pitfall 28
29. **New GLBs** without Three.js dispose soak test — fires Pitfall 29
30. **`gh release create`** in any subagent prompt without DO-NOT — fires Pitfall 30
31. **PyInstaller lipo** without target-triple — fires Pitfall 31
32. **Windows audio plumbing** modified without IMMNotificationClient verify — fires Pitfall 32
33. **"set vibemix as default output"** — fires Pitfall 33
34. **tenacity** swap without `Retry-After` test — fires Pitfall 34
35. **Blocklist expansion** without repo-wide grep + rewrite — fires Pitfall 35
36. **Sketchfab** / **TurboSquid** / **Hyper3D** without license check — fires Pitfall 36
37. **Onboarding wizard** without 60s stopwatch budget — fires Pitfall 37
38. **E2E report** with marketing prose tone — fires Pitfall 38
39. **Mascot cache** without versioned path — fires Pitfall 39
40. **Installer filename pattern** changed without SmartScreen note — fires Pitfall 40
41. **v3.1 close without SHIP-04 status** — fires Pitfall 41
42. **2+ subagents** touching `requirements.lock` in parallel — fires Pitfall 42
43. **Mixamo Adobe subscription** / **SignPath EV** / **GH Actions minutes** without budget line — fires Pitfall 43
44. **Subagent refuses** to read vibemix appdata citing "privacy" — fires Pitfall 44

---

## Sources

### Primary v3.1 anchors (HIGH confidence — internal canon)

- `.planning/PROJECT.md` — v3.1 target features (one-click install / dep audit-pin / dep-opportunity scan / e2e MacBook pass / mascot emotion coverage), v3.0 carryover state, KAAN-ACTION-LEGAL §SHIP-01..13
- `CLAUDE.md` — project Constraints (no Linux, Gemini-only, no scope creep, MIT/Apache-2.0 license, Bravoh internal-reuse, 50 €/month budget, one-click install HARD req, hallucination grounding gate)
- `.planning/codebase/CONCERNS.md` — codebase tech debt (no requirements.txt, three parallel cohost variants, np.concatenate ring, 96 recording sessions accumulating)
- `.planning/research/v3-shipped/PITFALLS.md` — prior v3.0 catalog (P1-P41), all referenced by ID where v3.1 work risks regression

### Memory anchors (HIGH confidence — Kaan-authored guidance)

- `project_one_click_install_hard_req` — HARD requirement for Mac+Win one-click; every dep choice rated green/yellow/red on install impact (P2, P15, P17, P25, P28)
- `project_v0_1_0_rc1_open_bugs` — Tauri drag capability + mascot chrome strip + sidecar bundle schema + TCC list-population still open (P22, P24, P27)
- `feedback_worktree_must_sync_main_first` — 458-commit regression memory-attested; Step-0 `git merge origin/main` mandatory in subagent prompts (P7, P42)
- `feedback_no_clap_use_gemini_embedding` — Gemini-only, no CLAP/MERT/OpenL3 (P6)
- `feedback_no_scope_creep_clean_utility` — no stems, no multi-provider, no enterprise; min-useful-surface (P6, P23)
- `project_v4_canonical_baseline` — BlackHole 48 kHz format requirement (P25)
- `project_mascot_as_vtuber_personality_surface` — single mascot "Neon Rebel" with mood variation, NOT swappable (P4, P36)
- `project_phase_16_kaan_dj_testing` — Kaan's DJ ear, not formal suite (P18)
- `project_github_star_goal` — 500-1000+ stars (P38)
- `feedback_privacy_scope_narrow` — privacy rule narrow to LLM-transcript paths only (P44)
- `feedback_autonomous_no_grey_area_pause` — defer to KAAN-ACTION-REQUIRED, do not pause (P30, P41)
- `feedback_no_gsd_orchestra_for_trivial_tweaks` — single-line edits go direct; relevant for v3.1 prose tweaks under blocklist
- `project_anti_slop_grounded_gemini_thesis` — grounding stack thesis (P5, P28, P38)

### Tauri / platform documentation (MEDIUM-HIGH confidence)

- Tauri 2 capability system — `tauri.conf.json5` capabilities allowlist semantics (P27)
- macOS TCC framework — `tccutil` is read-only on modern macOS for most categories (P15)
- macOS System Extension framework — `systemextensionsctl` flow on Apple Silicon Reduced Security (P2)
- Apple notarytool — Issuer ID + Key ID + .p8 (v3-shipped P5, re-flagged for P9)
- WiX / NSIS installer scope — per-user vs per-machine semantics (P16)
- WASAPI IMMNotificationClient — default-device-change subscription (P32, v2.1 Phase 27-06)
- PyInstaller target-triple Universal2 — replaces lipo-merge (P31, v2.1 Phase 27-06)

### Dep-management / security (MEDIUM confidence)

- PEP 508 environment markers — `sys_platform` resolution semantics (P20)
- syft SBOM — CycloneDX format + CI-gated re-gen (P14)
- pip-audit / osv-scanner / cargo-audit — diff-mode + ignore-list practice (P13)
- pip-licenses — direct vs transitive (P10)
- uv / poetry / pip-tools cross-solver behavior (P20)

### Mascot / Three.js (MEDIUM confidence)

- Three.js AnimationUtils.makeClipAdditive — required for additive blending (v3-shipped P19)
- Three.js dispose discipline — GPU memory not GC'd (P29)
- DRACO compression — required for GLB size budget (P11)
- Mixamo retarget — bone-mapping requirement for custom rigs (P12)
- Asset licensing — CC0 / CC-BY / CC-BY-NC distinctions (P36)

### Anti-slop / blocklist (HIGH confidence — v3.0 LAUNCH-01)

- v3.0 Phase 44 LAUNCH-01 README hero verbatim lock + 15-token blocklist + `\bdeeply\s+\w+` regex (P5, P22, P35)
- Anti-slop blocklist scope discipline (P5, P35)

---

*Pitfalls research for: vibemix v3.1 Distribution-Ready Pass — adding one-click install + dep audit/pin + dep-opportunity scan + e2e MacBook pass + mascot emotion coverage on top of v3.0-shipped Tauri+Python+React desktop app, Mac+Win, Gemini-only, single-engineer rig*
*Researched: 2026-05-17*
*Catalogs 44 new v3.1-distribution-readiness pitfalls; cross-references v3-shipped P1-P41 where v3.1 work risks regression; does not duplicate.*
