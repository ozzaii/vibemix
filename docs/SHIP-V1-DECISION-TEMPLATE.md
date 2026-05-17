<!--
  SHIP-V1-DECISION decision template (canonical schema).

  Plan: 45-04 / SHIP-13
  Status: locked structure — both consumers depend on this shape:
    - scripts/release/audit_ship_v1_decision.py (writes pre-filled report from this skeleton)
    - KAAN-ACTION-LEGAL.md §SHIP-13 runbook (cites this template as the decision-of-record schema)

  DO NOT REORDER OR RENAME the four H3 evidence sections, the 5-row decision rubric, the 3-way
  decision checkbox block, or the Kaan sign-off line. tests/release/test_audit_ship_v1_decision.py
  pins those invariants. Any addition lands at the bottom of the rubric / above the sign-off line.

  Decision is Kaan's. The audit script ONLY pre-fills the four "Evidence" sections + the
  "Current" column of the rubric. The 3-way decision checkbox + sign-off + free-form notes are
  manual additions Kaan writes at T+30 below the auto-generated divider.
-->

# v3.0 SHIP-V1-DECISION — <release_tag>

**Audit date:** <YYYY-MM-DD>
**Release published:** <published_at>
**Bake window:** <published_at> → <audit_date> (<N> days)

## Evidence — pre-filled by audit_ship_v1_decision.py

### 1. Distribution metrics

- Downloads (aggregate): <download_count>
- DMG downloads: <dmg_count>
- MSI downloads: <msi_count>

### 2. Server health (Bravoh)

- healthz uptime: <uptime_pct>% (<ok>/<total>; target ≥99.5%)
- Stale-cron incidents: <stale_count>

### 3. Ear-tests (Plan 42-03)

- Total sessions: <ear_test_count>
- Genres covered: <genres_csv>
- "Felt slop" flagged: <slop_count>
- "Felt scripted" flagged: <scripted_count>

### 4. Crash / Bug reports

- Total issues opened in bake window: <issue_count>
- Crash-labelled: <crash_count> (<open>/<closed>)
- Oldest open crash issue: <oldest_age_days> days

## Decision rubric (Kaan-discharge)

| Metric                       | Green  | Yellow   | Red  | Current       |
| ---------------------------- | ------ | -------- | ---- | ------------- |
| Downloads ≥100 in 14d        | ≥100   | 50-99    | <50  | <pre-filled>  |
| Healthz uptime ≥99.5%        | ≥99.5  | 98-99.5  | <98  | <pre-filled>  |
| Ear-test slop incidents      | 0      | 1-2      | ≥3   | <pre-filled>  |
| Open crash issues            | 0      | 1-2      | ≥3   | <pre-filled>  |
| Anti-slop community reports  | 0      | 1        | ≥2   | <manual>      |

## Decision

- [ ] Cut v1.0.0 (all green or 1 yellow; no red)
- [ ] Cycle v3.0.0-rc2 (≥1 red OR ≥3 yellow)
- [ ] Pause (catastrophic — pull RC binaries per docs/launch-rotation.md)

**Kaan sign-off:** _____________ **Date:** _____________

**Notes:** <free-form Kaan-fills>
