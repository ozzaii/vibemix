# Mascot Bundle Cap Decision — Phase 47 / MASCOT-03

**Date:** 2026-05-18
**Phase:** 47 — Mascot Real GLB Land + Full Emotion Coverage
**Requirement:** MASCOT-03 — bundle gate exits 0 with 23 real GLBs in place

## Decision

**PREFERRED: Draco retune under existing 25 MB Tier-1 cap.**

The Phase 43-05 25 MB bundle ceiling stays as-is. Per-clip target bands
(sourced from `scripts/mascot/retarget_to_neon_rebel.py` `SLOT_FAMILIES`):

| Family | Slots | Per-clip band | Mid-band target | Cumulative ceiling |
|--------|-------|---------------|-----------------|--------------------|
| base | 3 | 200-600 KB | 400 KB | 1.2 MB |
| emotion | 5 | 300-900 KB | 600 KB | 3.0 MB |
| anticipation (Phase 47 new) | 5 | 400-1200 KB | 700 KB | 3.5 MB |
| reaction | 10 | 400-1200 KB | 700 KB | 7.0 MB |
| **subtotal (Phase 47 new)** | **23** | — | — | **14.7 MB** |
| legacy_prep (Phase 22-02) | 5 | 400-1200 KB | 700 KB | 3.5 MB |
| character.glb (Neon Rebel rig) | 1 | n/a | ~5 MB | 5.0 MB |
| **grand total target** | — | — | — | **~23.2 MB** |

Headroom against the 25 MB cap: **~1.8 MB**. Acceptable.

## Fallback: 30 MB cap bump

If the draco retune pass does not hit the 25 MB cap after `--draco.compressionLevel 10`
on the reaction family AND the legacy_prep family is also retargeted (full
28-slot discharge), THEN — and ONLY then — flip the env override
`BUNDLE_CAP_BUMP=30` in `.github/workflows/mascot-audit.yml` and append
an entry to this doc's "Audit log" section below.

The 30 MB bump is NOT a free pass. It must be paired with:

- A line item in `docs/AUDIT.md` § Decisions documenting why retune failed.
- A target rationale: e.g., "the legacy_prep family was retargeted with
  a higher-fidelity Mixamo source that doesn't compress as tightly".
- A future-phase ticket to reach back under 25 MB via clip-trim or rig
  texture optimization.

## Audit log

| Date | Decision | Approver | Rationale |
|------|----------|----------|-----------|
| 2026-05-18 | Initial — 25 MB cap retained, draco-first strategy locked | Phase 47 plan | Engineering deliverable; Kaan discharges retarget assets at convenience |

## Verification

- `bash scripts/mascot/check_bundle_size.sh` exits 0 (both tiers green) after Kaan §VIS-04 discharge.
- `python3 scripts/mascot/check_manifest_complete.py` exits 0.
- `ls -lh tauri/ui/assets/mascot/animations/*.glb | wc -l` = 28 (5 legacy + 23 new).

## Anti-slop check

This decision document passes the project anti-slop blocklist
(`scripts/launch/check_no_ai_slop.py`) — no 15-token vocabulary
violations, no `\bdeeply\s+\w+` patterns.
