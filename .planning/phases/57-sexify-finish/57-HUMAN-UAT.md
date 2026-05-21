---
status: partial
phase: 57-sexify-finish
source: [57-VERIFICATION.md, 57-UI-REVIEW.md]
started: 2026-05-21T11:15:00Z
updated: 2026-05-21T11:15:00Z
---

## Current Test

[awaiting human testing — Kaan on real Mac]

## Tests

### 1. Window drag works on the real app (POLISH-02a)
expected: The window can be dragged by the drag region; `[data-no-drag]` elements (buttons) don't initiate a drag. Capability `core:window:allow-start-dragging` + JS `startDragging()` are pinned in code.
why_human: Real-app interaction confirmation on the Mac.
result: [pending]

### 2. Mascot chrome strip is gone (POLISH-02b)
expected: No window-chrome strip renders on the mascot overlay (it's fully transparent). `chrome.css` `display:none` pinned.
why_human: Visual confirmation on the real overlay.
result: [pending]

### 3. macOS Privacy/TCC list populates (POLISH-02c)
expected: On first-run/setup, the macOS Privacy permissions list populates (mic/screen). `_prime_tcc_registration` fires from `boot()` (pinned). The "empty list" may have been a stale observation.
why_human: Needs a real (ideally fresh-ish) macOS account to watch the Privacy list populate.
result: [pending]

### 4. Tier-1 surfaces look peak / "sexy" — felt visual sign-off (POLISH-01)
expected: Session view + mascot overlay feel polished + CDJ-Whisper-consistent under a live session. Engineering proved zero-HIGH ui-auditor (22/24) + held Saira/JetBrains Mono + amber discipline; this is the felt beauty call.
why_human: Beauty under a live session is Kaan's eye (he asked to review the impeccable pass).
result: [pending]

### 5. Fresh macOS account first-run → first-session has no friction (POLISH-03)
expected: A fresh account walks first-run to audio-live with no dead-ends/confusing steps. Audit found a clean code-path walk + a continuity smoke; this is the felt confirmation.
why_human: Real fresh-account walk on the Mac.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

None — engineering is green (9/9 must-haves; ui-auditor 0 HIGH). These five are the documented Kaan-action real-hardware/felt-quality carveouts. Sidecar binary rebuild is deferred to Phase 58 (noted in the friction audit).
