---
status: pending_kaan_measurement
phase: 23
plan: 23-01
pitfall: 25
gates: [v2.0-rc1]
---

# DDJ-FLX4 Sync Note Sniff — Verdict

## Session Metadata

| Field | Value |
| --- | --- |
| Date | PENDING — Kaan-action required |
| Duration | 300s target (5 min) |
| Hardware | Pioneer DDJ-FLX4 (firmware version TBD — read off djay Pro `Device Info` panel during session) |
| Port name | PENDING — observed via `--list` |
| Operator | Kaan |
| Purpose | Resolve Pitfall 25: cohost_v4 inferred `note 0x60` vs Mixxx canonical `note 0x58` for the FLX4 Sync button. Hardware-grounded verdict required before v2.0-rc1 cut. |

## Verdict

**PENDING — Kaan-action required, Day-1 sniff not yet performed.**

The three possible outcomes are documented for completeness. The first
hardware session will collapse this to exactly one:

| Outcome | Action for FLX4 JSON | Rationale |
| --- | --- | --- |
| `0x60 ONLY` | Keep `note: 96` for `sync_a` / `sync_b`. Mark `verified: true`. Add `sniff_log: 'FLX4-SNIFF.md'`. | Confirms cohost_v4 capture. Mixxx XML is stale / wrong for this firmware. |
| `0x58 ONLY` | Change to `note: 88`. Mark `verified: true`. Reference cohost_v4.py line 598 as "POC inferred wrong, hardware-resolved". | Confirms Mixxx canonical. cohost_v4 captured a different button (likely Shift+Sync) and mislabelled. |
| `BOTH (different sync paths)` | Ship both bindings: `sync_a` = note 96, `sync_a_alt` = note 88 (both `kind: "sync"`, both `verified: true`). Same for deck B. | The DDJ-FLX4 has Shift-layered buttons — plain Sync and Shift+Sync route through different note numbers. Both are real, both must fire MIX_MOVE events. |

## Evidence

Pending capture. The session is expected to record:

- 3x plain Sync taps on Deck A → expected note(s): `0x60` and/or `0x58`, channel `0`.
- 3x plain Sync taps on Deck B → expected note(s): `0x60` and/or `0x58`, channel `1`.
- 2x Shift+Sync on Deck A → expected: same or different note vs plain Sync.
- 2x Shift+Sync on Deck B → expected: same or different note vs plain Sync.
- Cross-reference frames for EQ knobs, faders, jog, play, cue (incidental capture during session).

Raw JSONL excerpts (5-10 lines around each Sync event) will be pasted under
a per-gesture subheading once the hardware session completes:

```jsonl
# Deck A plain Sync — pending
# Deck A Shift+Sync — pending
# Deck B plain Sync — pending
# Deck B Shift+Sync — pending
```

## Action for Plan 02

**Until the hardware sniff lands**, Plan 23-02 ships the FLX4 JSON with the
defensive both-bindings fallback (D-LOCKED in CONTEXT):

> FLX4 JSON `sync_a` / `sync_b` note: `96` (cohost_v4 baseline, `verified: false`, `status: "pending-verdict"`)
> FLX4 JSON `sync_a_alt` / `sync_b_alt` note: `88` (Mixxx canonical, `verified: false`, `status: "pending-verdict"`)
> Both reference `sniff_log: 'FLX4-SNIFF.md (PENDING)'`.
> Re-run sniff before v2.0-rc1 cut; replace this block with the verdict outcome above and flip `verified: true` on the winning binding(s).

After the hardware session completes, Kaan replaces this section with an
unambiguous one-line instruction matching one of the three verdict
outcomes in the table above.

## Other Notable Findings

_(Reserved for non-Sync surprises captured during the session — e.g. jog
wheel on different channel than expected, hidden Shift-layer notes on EQ
knobs, FX paddles routing through CC vs note. Plan 23-02 folds these
into the FLX4 JSON; Plan 23-03+ folds findings on Shift-layered notes
into the FLX6/FLX10 inferred mappings.)_
