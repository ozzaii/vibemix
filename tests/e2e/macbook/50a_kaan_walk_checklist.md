# 50a Kaan-Walk Checklist

**Goal:** Validate the SHIPPED `.dmg` end-to-end on Kaan's MacBook with real DJ-set audio. Subjective Kaan-ear pass per memory `project_phase_16_kaan_dj_testing` — NOT a formal 30-session replay harness.

**Pre-flight:**
- [ ] Signed `.dmg` from §SHIP-CUT installed at `/Applications/vibemix.app`
- [ ] BlackHole 2ch driver visible in Audio MIDI Setup
- [ ] djay Pro or rekordbox is the current audio source
- [ ] Real DJ-set audio loaded (≥ 10 min of mixed tracks Kaan would actually play)
- [ ] Screen recorder armed (see `scripts/e2e/record_50a_walk.sh`)
- [ ] No other AI tools (LM Studio, OZ wake, Hermes) actively writing — privacy invariant

## Step 1 — Cold launch
- [ ] Open `vibemix.app` from Launchpad
- [ ] First-run dialog appears (or none if already onboarded)
- [ ] Time-to-first-mascot-frame  ≤ 3s   note: ___s
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 2 — Audio loopback connect
- [ ] Library page loads with prior session history (or empty state if first run)
- [ ] Audio meter shows live signal as soon as DJ-set plays
- [ ] Mascot transitions from `base_idle` to `base_breathe` on first signal
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 3 — Start live session
- [ ] Click "Start session"
- [ ] Live-session page loads in ≤ 1s
- [ ] Mascot persona switches per `EVENT_LAYER_PRIORITY_MAP` rules
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 4 — Mascot reaction #1 (build / drop transition)
- [ ] Spin a track up to a clear build → drop transition
- [ ] Mascot fires a reaction within 1.5s of the drop landing  note: ___ms
- [ ] Reaction sounds grounded — NOT scripted / NOT generic AI slop
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 5 — Mascot reaction #2 (smooth blend)
- [ ] Execute a slow blend over 4 bars
- [ ] Mascot reaction sounds patient — does NOT fire mid-blend
- [ ] If it does fire, the comment grounds itself in the actual blend
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 6 — Mascot reaction #3 (long deep section)
- [ ] Hold a single deep track for 90+ seconds with minimal motion
- [ ] Mascot stays quiet OR emits one quiet observation (not chatty)
- [ ] No hallucinated "you just dropped X" type comments
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 7 — Hallucination spot-check
- [ ] Listen to all 3 reactions on the screencast playback
- [ ] Zero false-positives (reactions tied to events that DID NOT happen)
- [ ] Zero "deeply" / "thoughtfully" / "crafted" / "delight" type slop
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 8 — Nielsen 10 spot-check
Run through `tests/e2e/macbook/nielsen_10_checklist.json` on Tier-1 surfaces:
- [ ] Library page — visibility / match / consistency / error / recovery
- [ ] Live session — visibility / match / consistency / error / recovery
- [ ] Settings — visibility / match / consistency / error / recovery
- [ ] Zero HIGH findings — note any MEDIUM finding for follow-up

## Step 9 — Clean shutdown
- [ ] Close vibemix via Cmd+Q
- [ ] App quits in ≤ 1s
- [ ] No leftover audio routing — system audio plays normally
- [ ] BlackHole still configured at 48000 Hz (run `installer/companion/audio_config.py --probe-48k`)
- [ ] Status: [ ] PASS  [ ] FAIL — reason: _______________

## Step 10 — Screencast hand-off
- [ ] Transcode `.mov` → `.webm` via the printed ffmpeg command
- [ ] Verify size < 25 MB (else `git lfs track 'docs/e2e/*.webm'`)
- [ ] Save final at `docs/e2e/2026-05-walk.webm`
- [ ] Commit: `chore(e2e): land 50a Kaan-walk screencast`

---

**Overall verdict:**  [ ] PASS — v3.1 close go  /  [ ] FAIL — block + re-run after fixes

**Notes:** ____________________________________________________________
________________________________________________________________________

**Walk date:** ____________   **Set length:** ___ min   **Tracks played:** ___
