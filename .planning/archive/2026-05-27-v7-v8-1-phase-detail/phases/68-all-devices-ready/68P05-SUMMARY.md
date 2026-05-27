---
phase: 68-all-devices-ready
plan: 05
subsystem: kaan-action-discharge-surface
tags: [docs, kaan-action, v7-live, soft-discharge, dev-03, dev-04, dev-05, autonomous-fully]
requirements:
  - DEV-03
  - DEV-04
  - DEV-05
provides:
  - "KAAN-ACTION-LEGAL.md §V7-LIVE section extended from 6 clusters (01..06) to 10 clusters (01..10)"
  - "§V7-LIVE-07 cluster — controller-recipe <30-min smoke discharge route (DEV-05)"
  - "§V7-LIVE-08 cluster — macOS BlackHole 2ch/16ch live capture discharge route (DEV-04)"
  - "§V7-LIVE-09 cluster — Windows WASAPI loopback live capture discharge route (DEV-04)"
  - "§V7-LIVE-10 cluster — live Pioneer DDJ-FLX4 plug/unplug ear-pass discharge route (DEV-03)"
  - "Phase 68 (DEV · All Devices Ready) ENGINEERING-COMPLETE — all 5 plans shipped, DEV-01..05 closed engineering-side"
affects:
  - KAAN-ACTION-LEGAL.md (§V7-LIVE section: +4 clusters, +4 rows in discharge tracking table, +4 lines in sign-off block, TOTAL line updated)
tech-stack:
  added: []
  patterns:
    - "Cluster shape mirrors §V7-LIVE-01..06 baseline (Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off) per 68-RESEARCH Wave 0 reference"
    - "Discharge-surface-only edit — no engineering code touched, zero src/vibemix/ edits, zero new tests, zero net-new deps"
key-files:
  created:
    - .planning/phases/68-all-devices-ready/68P05-SUMMARY.md
  modified:
    - KAAN-ACTION-LEGAL.md
  deleted: []
decisions:
  - "Inserted the 4 new clusters AFTER §V7-LIVE-06 body but BEFORE the shared 'Discharge tracking' table + 'Sign-off block' — so the table and sign-off block could be extended once to cover all 10 clusters (mirrors how §V7-LIVE-05 + 06 were folded into the shared tracking surface by 67P04/67P05 rather than getting per-cluster tables)"
  - "Each new cluster carries Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off — same 6-section shape as §V7-LIVE-01..06 baseline (read live before authoring to confirm)"
  - "§V7-LIVE-07 sign-off shape extended beyond the baseline date/SHA/result triad to capture (controller, profile_id, wall-clock minutes, friction points) — the smoke discharge IS the wall-clock measurement, so the sign-off must record it"
  - "§V7-LIVE-08/09/10 sign-off shapes extended with device_name / device index / cycles completed fields — the live confirmations are wall-clock multi-field artifacts, not single-bit pass/fail like §V7-LIVE-01..05"
  - "Discharge tracking TOTAL extended via a sub-clause ('... + 4 P68 live clusters') rather than recomputing all 14 entries into a single number — keeps the 67P05 lineage (`11 tests + 1 workflow + 1 recurring`) readable and the new 4 P68 entries grouped"
  - "Did NOT touch src/vibemix/ or any test file — Threat T-68P05-04 gate held (KAAN-ACTION-LEGAL.md is text-only and not pytest-collected; default-grid baseline preserved EXACTLY)"
  - "Did NOT redefine §V7-LIVE-07/08/09/10 section numbering once chosen — strict canonical order after §V7-LIVE-06 ensures 11 → 10 line numbers go 3837 (06) → 3889 (07) → 3938 (08) → 3995 (09) → 4052 (10), monotonic increasing"
metrics:
  duration: ~8 min (16:25 → 16:33 TRT)
  completed_date: 2026-05-23
  files_touched: 1
  insertions: 252
  deletions: 8
  baseline_before: 4147 passed / 26 skipped / 4 xpassed / 0 failed (post-Wave-3)
  baseline_after: 4147 passed / 26 skipped / 4 xpassed / 0 failed
  baseline_delta: "+0 tests (KAAN-ACTION-LEGAL.md not pytest-collected); 26 skipped + 4 xpassed unchanged; 0 failed; wall-clock 215.53s within Wave-3 baseline sd"
  task1_commit_sha: 8ba2992
  v7live_cluster_count_before: 6 (§V7-LIVE-01..06)
  v7live_cluster_count_after: 10 (§V7-LIVE-01..10)
  v7live_07_line: 3889
  v7live_08_line: 3938
  v7live_09_line: 3995
  v7live_10_line: 4052
---

# Phase 68 Plan 05: Wave 4 §V7-LIVE-07..10 Discharge Surface Summary

**One-liner:** Closed the Phase 68 wrap by appending 4 new clusters (§V7-LIVE-07..10) to `KAAN-ACTION-LEGAL.md §V7-LIVE` — formalizing the soft Kaan-discharge routes for the live-hardware confirmations of DEV-03 (FLX4 plug/unplug ear) + DEV-04 (BlackHole macOS + WASAPI Windows live capture) + DEV-05 (contributor-recipe <30-min smoke). Under `gsd-autonomous fully` these are SOFT discharges — Phase 68 ENGINEERING-COMPLETE (all 5 plans shipped, DEV-01..05 closed engineering-side); live confirmations ride Kaan's clock without blocking P69 OSS. Pure discharge-surface edit — 1 file changed, 252 insertions, 8 deletions, 1 commit, zero `src/vibemix/` edits, zero new tests, zero net-new deps, default `uv run pytest -q` baseline preserved EXACTLY at 4147 passed / 26 skipped / 4 xpassed / 0 failed.

## Objective

Wave 4 of Phase 68 (DEV · All Devices Ready). Waves 0-3 (68P01..68P04) shipped engineering-side: catalog reconciled (Wave 0), 10×2 parametrized contract + smoke tests (Wave 1), 3-profile hot-plug matrix + 4-fixture audio backend matrix (Wave 2), 3-artifact contributor recipe (Wave 3). Wave 4 closes the milestone-shape loop by routing the live-hardware confirmations that CI cannot run (no real BlackHole kext, no Win 11 desktop SKU, no real DDJ-FLX4 USB hardware, no contributor's wall-clock minutes) into structured KAAN-ACTION-LEGAL.md entries:

1. **§V7-LIVE-07 — Controller-recipe <30-min smoke** (DEV-05): Kaan or a trusted DJ uses `docs/contributing/add-a-controller.md` (P68P04 / 173 lines) to add 1 new profile on a controller-of-opportunity from cold-start to PR-ready in under 30 minutes; outcome recorded in `docs/contributing/add-a-controller-smoke.md` (the discharge artifact, created at discharge time).

2. **§V7-LIVE-08 — macOS BlackHole 2ch / 16ch live capture** (DEV-04): real BlackHole on Kaan's Mac, real 48kHz capture stream, real `RMS > 0` during music playback — confirms the P68P03 mock-matrix shape against real CoreAudio behavior.

3. **§V7-LIVE-09 — Windows WASAPI loopback live capture** (DEV-04): real Win 11 desktop SKU on Kaan's Parallels/UTM VM, real WASAPI loopback open, real `RMS > 0` during system audio playback — confirms the P68P03 mock-matrix shape against real WASAPI behavior on the actual desktop SKU (not Server 2022).

4. **§V7-LIVE-10 — Live FLX4 plug/unplug ear pass** (DEV-03): real Pioneer DDJ-FLX4 over USB, 3× plug → move → unplug → wait → replug cycles across a 5-minute window, with the AI co-host staying alive (no crash, no fabricated reactions, `id(ControllerState)` preserved per v4.0 P53 invariant) — confirms the P68P03 3-row hot-plug parametrize shape against real USB jitter + driver re-init latency + felt-quality anti-slop bar.

The engineering side for all 4 routes is already GREEN — see Wave 2 (68P03) + Wave 3 (68P04). What this plan ships is the **structured fix-path documentation** so each live confirmation has a sign-off slot Kaan can fill in when he runs it.

## What Shipped

**One commit — single atomic file edit (the 4 clusters are a coherent unit; appending them in one commit per the plan):**

| Task | Commit | File | Lines added | Lines removed |
| ---- | ------ | ---- | ----------- | ------------- |
| 1 | `8ba2992` — `docs(68-05): add §V7-LIVE-07..10 KAAN-ACTION clusters for P68 soft discharges` | `KAAN-ACTION-LEGAL.md` | 252 | 8 |

**Net stats:** 1 file modified · 252 insertions · 8 deletions · 1 commit.

### Cluster line positions in `KAAN-ACTION-LEGAL.md`

| Cluster | Line | Owner-clock | DEV-NN |
| ------- | ---- | ----------- | ------ |
| §V7-LIVE-01 | 3653 | Kaan's Mac (BlackHole installed) | TEST-02 (Phase 67) |
| §V7-LIVE-02 | 3682 | Kaan's Win 11 VM + FLX4 | TEST-02 |
| §V7-LIVE-03 | 3723 | Kaan's Mac + plugged FLX4 | TEST-02 |
| §V7-LIVE-04 | 3753 | Kaan's Mac, manual one-shot | TEST-02 |
| §V7-LIVE-05 | 3787 | Kaan — first push to GitHub | TEST-04 |
| §V7-LIVE-06 | 3837 | Kaan — pre-release or quarterly | TEST-03 |
| **§V7-LIVE-07** | **3889** | **Kaan or trusted DJ — controller-of-opportunity** | **DEV-05 (Phase 68)** |
| **§V7-LIVE-08** | **3938** | **Kaan's Mac (BlackHole installed)** | **DEV-04 (Phase 68)** |
| **§V7-LIVE-09** | **3995** | **Kaan's Win 11 VM (Parallels/UTM)** | **DEV-04 (Phase 68)** |
| **§V7-LIVE-10** | **4052** | **Kaan's Mac + Pioneer DDJ-FLX4 USB** | **DEV-03 (Phase 68)** |

All 4 new clusters land in canonical numerical order after §V7-LIVE-06; monotonic line-number progression 3837 → 3889 → 3938 → 3995 → 4052 verified via `awk '/^### §V7-LIVE-/{print NR, $0}'` (acceptance gate).

### Discharge tracking table (extended in-place)

The shared `### Discharge tracking` table just below §V7-LIVE-06 was extended with 4 new rows (one per new cluster) and the TOTAL line updated from `11 tests + 1 workflow + 1 recurring` (67P05 lineage) to `11 tests + 1 workflow + 1 recurring + 4 P68 live clusters` — keeping the lineage readable and the new 4 P68 entries visibly grouped. Mirrors how §V7-LIVE-05 (67P04) and §V7-LIVE-06 (67P05) folded into the shared tracking surface rather than getting per-cluster tables.

### Sign-off block (extended in-place)

The shared `### Sign-off block` at the bottom of the §V7-LIVE section was extended with 4 new `V7-LIVE-NN` lines, each formatted to capture the cluster's specific field-set:

```
V7-LIVE-07 Controller-recipe <30-min smoke (DEV-05) on: _________   (date — Kaan or trusted DJ, controller ____, wall-clock ____ min)
V7-LIVE-08 macOS BlackHole live capture (DEV-04)    on: _________   (date — Kaan, SHA ____)
V7-LIVE-09 Windows WASAPI live capture (DEV-04)     on: _________   (date — Kaan, SHA ____)
V7-LIVE-10 Live FLX4 plug/unplug ear (DEV-03)       on: _________   (date — Kaan, SHA ____, 3 cycles ____)
```

§V7-LIVE-07's sign-off captures the wall-clock measurement (the smoke IS the measurement); §V7-LIVE-10's sign-off captures cycles completed (the ear-pass is a 3× cycle artifact, not a single binary pass). §V7-LIVE-08/09 follow the §V7-LIVE-01..04 baseline shape with a date + SHA.

### Cross-references landed (verified by grep)

| Reference | Count after | Used by clusters |
| --------- | ----------- | ---------------- |
| `docs/contributing/add-a-controller.md` | 3 | §V7-LIVE-07 (recipe entry point) |
| `tests/integration/test_audio_backends.py` | 2 | §V7-LIVE-08 + §V7-LIVE-09 (5-fixture mock matrix that the live runs confirm) |
| `tests/integration/test_hotplug_matrix.py` | 1 | §V7-LIVE-10 (3-row hot-plug parametrize that the live ear-pass confirms) |
| `scripts/discover_midi_port.py` | 3 | §V7-LIVE-07 (recipe Step 1) + §V7-LIVE-10 (port discovery on plug) |
| `pioneer_ddj_flx4.json::port_name_hints` | 1 | §V7-LIVE-10 (port name expected to match) |
| `vibemix.platform._midi_common::handle_port_change_single_state` | 1 | §V7-LIVE-10 (v4.0 P53 single-state callback) |
| `vibemix.midi.state::ControllerState.mark_disconnected` | 1 | §V7-LIVE-10 (v4.0 P53 ring-clear) |
| `tests/midi/test_disconnect_reconnect.py` | 1 | §V7-LIVE-10 (FLX4-focused helpers source) |
| `tests/test_midi_macos_live.py` | 1 | §V7-LIVE-10 (BRINGUP-03 sequence docstring) |
| §V7-LIVE-01 cross-link | 1 | §V7-LIVE-08 (same BlackHole kext lineage) |
| §V7-LIVE-02 cross-link | 1 | §V7-LIVE-09 (same windows-latest=Server2022 lineage) |
| §V7-LIVE-03 cross-link | 1 | §V7-LIVE-10 (same FLX4 USB lineage; -10 extends with full plug-cycle ear-pass) |

## Verification

```bash
# Cluster header counts (each new cluster appears exactly once):
$ grep -c "^### §V7-LIVE-07" KAAN-ACTION-LEGAL.md
1
$ grep -c "^### §V7-LIVE-08" KAAN-ACTION-LEGAL.md
1
$ grep -c "^### §V7-LIVE-09" KAAN-ACTION-LEGAL.md
1
$ grep -c "^### §V7-LIVE-10" KAAN-ACTION-LEGAL.md
1

# Total §V7-LIVE clusters (was 6, now 10):
$ grep -c "^### §V7-LIVE-" KAAN-ACTION-LEGAL.md
10

# Canonical order (07..10 all after §V7-LIVE-06):
$ awk '/^### §V7-LIVE-/ {print NR, $0}' KAAN-ACTION-LEGAL.md
3653 ### §V7-LIVE-01 — BlackHole 2ch kext cannot load on hosted macOS runners
3682 ### §V7-LIVE-02 — `windows-latest` GitHub-hosted ≠ Windows 11 desktop SKU
3723 ### §V7-LIVE-03 — Real Pioneer DDJ-FLX4 over USB (macOS side)
3753 ### §V7-LIVE-04 — Live full-stack smoke (env-gated and/or real port binding)
3787 ### §V7-LIVE-05 — First-CI-green confirmation for `full-test-matrix.yml`
3837 ### §V7-LIVE-06 — Periodic 10× flake-hunt re-baseline
3889 ### §V7-LIVE-07 — Controller-recipe <30-min smoke
3938 ### §V7-LIVE-08 — macOS BlackHole 2ch / 16ch live capture
3995 ### §V7-LIVE-09 — Windows WASAPI loopback live capture
4052 ### §V7-LIVE-10 — Live FLX4 plug/unplug ear pass

# Cross-references to engineering artifacts:
$ grep -c "add-a-controller.md" KAAN-ACTION-LEGAL.md      # ≥1 (Wave 3 artifact)
3
$ grep -c "test_audio_backends.py" KAAN-ACTION-LEGAL.md   # ≥1 (Wave 2 artifact)
2
$ grep -c "test_hotplug_matrix.py" KAAN-ACTION-LEGAL.md   # ≥1 (Wave 2 artifact)
1
$ grep -c "discover_midi_port.py" KAAN-ACTION-LEGAL.md    # ≥1 (Wave 3 artifact)
3

# Default suite GREEN (zero regressions — KAAN-ACTION-LEGAL.md not pytest-collected):
$ uv run pytest -q
... 4147 passed, 26 skipped, 4 xpassed, 13 warnings in 215.53s (0:03:35)
```

All acceptance criteria from the plan: PASS.

## Deviations from Plan

### Auto-fixed Issues

None applicable — pure doc append in a non-load-bearing file. Zero Rule 1/2/3/4 deviations triggered.

### Notes on per-cluster shape adaptation

The plan's "Cluster shape" block specified a 7-section template (Heading / Status line / Source phase + REQ-ID / Routing rationale / Discharge owner / Discharge command + steps / Sign-off block). Reading the existing §V7-LIVE-01..06 clusters in `KAAN-ACTION-LEGAL.md` showed the real baseline shape uses **Tests / Why it can't ship green in CI / Fix path / Owner-clock / Cross-reference / Sign-off** — a 6-section shape with a slightly different vocabulary. Chose to mirror the **live baseline** in the repo over the plan's reference text. This is a literal "read the live siblings first" application of Threat T-68P05-02 mitigation. The 6-section shape captures every concept the plan's 7-section shape did (Status → embedded in Sign-off block ☐ pending; Source phase + REQ-ID → embedded in the Tests line + Cross-reference; Routing rationale → "Why it can't ship green in CI"; Discharge owner → "Owner-clock"; Discharge command/steps → "Fix path"; Sign-off → "Sign-off").

## Phase 68 ENGINEERING-COMPLETE Confirmation

All 5 Phase 68 plans (68P01..68P05) have shipped:

| Plan | Wave | Commit(s) | REQ closed | Status |
| ---- | ---- | --------- | ---------- | ------ |
| 68P01 | Wave 0 — atomic catalog reconciliation | `52405a4` | DEV-02 | SHIPPED 2026-05-23 |
| 68P02 | Wave 1 — contract tests + synthetic-MIDI smokes (10×2) | `9427fee` + `613f23e` | DEV-01 (a)+(b)+(c) | SHIPPED 2026-05-23 |
| 68P03 | Wave 2 — hot-plug matrix + audio backend matrix | `5f243d1` + `f12edbb` | DEV-03 + DEV-04 (engineering side) | SHIPPED 2026-05-23 |
| 68P04 | Wave 3 — contributor recipe (3 artifacts) | `aea6f26` + `d504c71` + `da78fec` | DEV-05 (engineering side) | SHIPPED 2026-05-23 |
| **68P05** | **Wave 4 — §V7-LIVE-07..10 KAAN-ACTION clusters** | **`8ba2992`** | **DEV-03/04/05 live-discharge routes** | **SHIPPED 2026-05-23** |

**DEV-01 + DEV-02 + DEV-03 + DEV-04 + DEV-05 — all 5 Phase 68 requirements CLOSED engineering-side.** The 4 §V7-LIVE-07..10 clusters route the live confirmations to Kaan's clock without blocking forward progress.

**Phase 68 ENGINEERING-COMPLETE. Ready for Phase 69 (OSS Fully Integrated) to start.**

## What's Next

Phase 69 (OSS Fully Integrated) — OSS-01..05 (5 reqs). Depends on Phase 68 ENGINEERING-COMPLETE (which this plan finalizes — no broken or duplicated controller catalog is being shipped; the bundled-10 are contract + smoke + hot-plug + audio-matrix tested; the contributor recipe is verified). OSS-04 has the external Apple Dev + SignPath signature clock — under `gsd-autonomous fully`, routes to KAAN-ACTION §SHIP-V4 if signatures haven't landed by execution; OSS-01/02/03/05 ship unblocked.

Under autonomous mode, the 4 new §V7-LIVE-07..10 clusters are SOFT discharges — Phase 68 closes here, P69 starts on top, and live confirmations ride Kaan's clock without ever pausing the milestone.

## Self-Check: PASSED

Files verified to exist:
- `.planning/phases/68-all-devices-ready/68P05-SUMMARY.md` — FOUND (this file)
- `KAAN-ACTION-LEGAL.md` — FOUND (modified, +252 / -8 from `8ba2992`)

Commits verified to exist:
- `8ba2992` — FOUND (`docs(68-05): add §V7-LIVE-07..10 KAAN-ACTION clusters for P68 soft discharges`)

All acceptance gates from the plan: PASS (10 clusters total, 4 new headers each appearing exactly once, canonical order preserved, cross-references to add-a-controller.md + test_audio_backends.py + test_hotplug_matrix.py + discover_midi_port.py all present, default `uv run pytest -q` 4147 passed / 26 skipped / 4 xpassed / 0 failed unchanged from Wave 3 baseline).
