# MIXXX MIXER + CROSSFADER CURVE MATH — clean-room spec for vibemix (Round 2)

LICENSE: learned-from-spec, no GPL code copied. All math re-derived in my own words. References cite Mixxx `file:line` as method-reference only.

---

## (1) THE ALGORITHM (reimplementable clean-room in numpy)

### 1A. Crossfader curve — the core (3 selectable laws)

Source of truth: `EngineXfader::getXfadeGains` (`/tmp/mixxx-src/src/engine/enginexfader.cpp:16-84`).

**Inputs:**
- `xfadePosition` ∈ [-1, +1] (Mixxx control range; -1 = full left/deck A, +1 = full right/deck B, 0 = center). Note: this differs from vibemix's [0,1] convention.
- `transform` = curve sharpness (`xFaderCurve`), clamped to `[kTransformMin=0.6, kTransformMax=1000.0]`, default `kTransformDefault=1.0` (`enginexfader.cpp:7-9`).
- `powerCalibration` = precomputed `pow(0.5, 1.0/transform)` (`getPowerCalibration`, `enginexfader.cpp:11-14`).
- `curve` = mode selector: `MIXXX_XFADER_ADDITIVE = 0.0` or `MIXXX_XFADER_CONSTPWR = 1.0` (`enginexfader.h:6-7`). The `xFaderMode` button picks between them (`enginemixer.cpp:485`).
- `reverse` = hamster/swap flag (`xFaderReverse`).
- Outputs `gain1` (right/B), `gain2` (left/A).

**The math, mode by mode:**

**ADDITIVE mode (`curve == 0`), the default "mixing" curve:**
```
xL = xR = xfadePosition          # no calibration shift
if xL < 0:   gain2 = 1 - pow(|xL|, transform)   else gain2 = 1.0   # left/A
if xR > 0:   gain1 = 1 - pow( xR , transform)   else gain1 = 1.0   # right/B
clamp both gains to >= 0          # "prevent phase reversal"
```
So at center (x=0) BOTH gains = 1.0 (full sum, +6 dB hot — this is additive). Moving toward one side attenuates only the *other* deck. `transform` shapes the attenuation: `transform=1` is a linear cut on the off-side; larger `transform` makes the cut sharper near the edges (a "fast cut / scratch" feel — the off-deck stays near full until you push to the very end). `transform<1` (down to 0.6) softens.

**CONSTANT-POWER mode (`curve == 1`), the "smooth blend" curve:**
```
x = xfadePosition * powerCalibration         # apply calibration scale
xL = x - powerCalibration
xR = x + powerCalibration
# same per-side attenuation as additive:
if xL < 0: gain2 = 1 - pow(|xL|, transform) else gain2 = 1.0
if xR > 0: gain1 = 1 - pow( xR , transform) else gain1 = 1.0
clamp both >= 0
# constant-power normalization — the key step:
if gain1 > gain2:  gain2 = 1 - gain1
else:              gain1 = 1 - gain2
gain = sqrt(gain1*gain1 + gain2*gain2)       # current vector magnitude
gain1 /= gain                                # renormalize so gain1^2+gain2^2 == 1
gain2 /= gain
```
The calibration `powerCalibration = 0.5^(1/transform)` is derived so that the -3 dB crossover point (where each gain = 0.5 before normalization) lands exactly at center. The `1 - gain1`/`1 - gain2` step enforces a complementary pair, then the `sqrt` renormalization forces `gain1² + gain2² = 1` for the whole sweep → constant *power* (loudness flat through the blend, 0.707/0.707 at center). Mixxx's comment (`enginexfader.cpp:66-77`) explains they chose to normalize as if the two signals are *uncorrelated* (measured ~0.707 across genres via ReplayGain 2.0 tests; ~0.66 only when mixing two parts of the same track) — i.e., they optimize loudness for the common "two different tracks" case, not the phase-coherent case.

**Reverse:** if `reverse`, swap `gain1 ↔ gain2` at the very end (`enginexfader.cpp:79-83`).

**vibemix's current port is a SIMPLIFICATION:** `_equal_power_gains` (`miniplayer.py:69-79`) uses the textbook `g_a = cos(xπ/2)`, `g_b = sin(xπ/2)`. That is a *valid* constant-power law (also gives `g_a²+g_b²=1`, 0.707 at center) but it is NOT Mixxx's law: it has no `transform` (curve sharpness) and no additive mode. The cos/sin and Mixxx-constpwr curves differ in shape away from center, and crucially vibemix has no way to model the additive/scratch curve a real DJ's hardware uses. To "grade real mixing" and to ground "you rode the crossfader," vibemix needs Mixxx's full `transform`-parameterized 3-mode law, not the fixed cos/sin.

### 1B. Per-channel gain staging (the full signal chain to master)

The gain that multiplies each deck buffer before it sums into the master is a product of several stages:

1. **Pregain / ReplayGain** (`EnginePregain::process`, `enginepregain.cpp:67-163`): `totalGain = pregainPot * clamp(replayGainCorrection, 0, 10)`, then a **vinyl speed-gain emulation** multiply: `speedGain = log10(|speed|·4 + 1) / log10(1·4+1)` (normalized to 1.0 at speed=1), limited so total never exceeds `kMaxTotalGainBySpeed=0.9` (≈ -1 dB headroom against clipping). Constants: `kSpeedGainMultiplier=4.0`, measured curve "-6 dB at 0.3×, 0 dB at 1×, +3.5 dB at 2.5×". Gain changes are **ramped** sample-by-sample across the block (`applyRampingGain`) to avoid click discontinuities — vibemix should do the same when a fader/EQ moves mid-block.

2. **Channel volume fader × orientation gain** (`OrientationVolumeGainCalculator::getGain`, `enginemixer.h:167-176`): `channelGain = volumePot × orientationGain`. The channel volume pot is a `ControlAudioTaperPot(-20, 0, 1)` (`enginemixer.cpp:854-855`) — i.e. a dB-tapered fader from -20 dB to 0 dB, neutral at the top.

3. **Orientation gain** = the crossfader contribution, routed by which side the channel is assigned to (`gainForOrientation`, `enginemixer.h:82-95`): LEFT → `crossfaderLeftGain`, RIGHT → `crossfaderRightGain`, CENTER → `1.0` (center-assigned channels bypass the crossfader entirely). The mixer sets `m_mainGain.setGains(crossfaderLeftGain, 1.0, crossfaderRightGain)` once per block (`enginemixer.cpp:492`), then mixes the three orientation buses and sums them (`copy3WithGain`, `enginemixer.cpp:539-546`).

4. **Master gain** (`m_pMainGain`, `enginemixer.cpp:592` etc.): another `ControlAudioTaperPot(-14, +14, 0.5)` applied to the summed main bus.

**The dB taper law** (`ControlAudioTaperPotBehavior`, `controlbehavior.cpp:170-229`): the fader is parameterized so the position→gain mapping is dB-linear over `[minDB, maxDB]`, with `0 dB` pinned at `neutralParameter` of the throw, and a linear overlay near the bottom so it reaches true zero (silence) at the very bottom instead of `db2ratio(minDB)`. The conversions are `db2ratio(db) = 10^(db/20)` and `ratio2db(r) = 20·log10(r)`. This is the curve that makes a DJ fader "feel right" — most of the useful travel is in the top few dB. vibemix's MiniDeck currently has NO per-deck volume fader at all (only `rate` + global `xfader`), so it cannot model gain staging.

### 1C. PFL / headphone cue + split routing (cueing a track before bringing it in)

Source: `enginemixer.cpp:387-435, 811-845`.

- **PFL select**: each channel has a `pfl` toggle (`enginechannel.cpp:22, 58-64`). PFL-enabled channels are summed into a separate headphone buffer at unity (`PflGainCalculator` returns a flat gain, `enginemixer.h:140-152`) — pre-fader, so you hear the cued deck regardless of its volume fader/crossfader position. This is exactly the "cue the next track in your headphones while the crowd hears the current one" workflow.
- **Head Mix knob** (`m_pHeadMix` ∈ [-1,+1]): blends PFL vs main in the cans. `pflGain = 0.5·(-cf+1)`, `mainGain = 0.5·(cf+1)` (`enginemixer.cpp:392-394`). At -1 you hear only PFL (cue), at +1 only main (program), at 0 a 50/50 mix. (Note: this is a *linear* blend, not constant-power.)
- **processHeadphones**: adds the main mix into the head buffer at `mainMixGainInHeadphones` (ramped), then applies the head-gain pot (`enginemixer.cpp:814-844`).
- **Head Split** (`m_pHeadSplitEnabled`, `enginemixer.cpp:826-834`): mono-sums PFL into the LEFT ear and mono-sums the main/program into the RIGHT ear: `ph[i]=(ph[i]+ph[i+1])/2; ph[i+1]=(pm[i]+pm[i+1])/2`. This is the classic "split cue" — cue in one ear, program in the other.

### 1D. Signal-flow summary (master output)
```
deck_buffer
  → EnginePregain (replaygain × pregain × speed-emu, ramped, clamp ≤0.9)
  → × volume_fader (dB taper -20..0)
  → × orientation_gain (xfader L/C/R from getXfadeGains)
  → effects (post-fader)
  → sum into orientation bus[L|C|R]
  → copy3WithGain into m_main (all unity)
  → × master_gain (dB taper -14..+14)
  → main out
PFL branch: pfl channels → sum @ unity → head buffer → +main@headMix → headGain → (optional split L/R) → headphones out
```

---

## (2) MIXXX FILE:LINE REFERENCES (method-reference, GPL — not copied)

- Crossfader curve law: `/tmp/mixxx-src/src/engine/enginexfader.cpp:11-84` (`getPowerCalibration` :11-14, `getXfadeGains` :16-84); curve-mode constants `/tmp/mixxx-src/src/engine/enginexfader.h:6-7`; transform clamps `enginexfader.cpp:7-9`.
- Crossfader → orientation gain wiring: `/tmp/mixxx-src/src/engine/enginemixer.cpp:481-504` (`getXfadeGains` call :483-487, `setGains` :492); `gainForOrientation` + `OrientationVolumeGainCalculator` `/tmp/mixxx-src/src/engine/enginemixer.h:82-95, 159-190`.
- Per-channel orientation/PFL/main-mix controls: `/tmp/mixxx-src/src/engine/channels/enginechannel.cpp:22-117`.
- Pregain / ReplayGain / vinyl speed-gain emulation: `/tmp/mixxx-src/src/engine/enginepregain.cpp:11-19, 67-163`.
- dB-taper fader law (`db2ratio`/`ratio2db`, neutral-param + linear-overlay): `/tmp/mixxx-src/src/control/controlbehavior.cpp:170-229`; pot construction `/tmp/mixxx-src/src/control/controlaudiotaperpot.cpp:5-19`; volume pot `-20..0` `/tmp/mixxx-src/src/engine/enginemixer.cpp:854-855`; master/booth/head pots `-14..+14` `enginemixer.cpp:65-70`.
- PFL/headphone cue + head-mix + split: `/tmp/mixxx-src/src/engine/enginemixer.cpp:387-435, 811-845`; PFL select `enginechannel.cpp:58-64`.
- Channel mix + ramped gain (anti-click): `/tmp/mixxx-src/src/engine/channelmixer.cpp:25-98`.

---

## (3) TORCH-FREE FEASIBILITY

100% torch-free, numpy-only, trivially cheap. The entire spec is scalar arithmetic + `pow`/`cos`/`sin`/`log10`/`sqrt` (all in `math`/`numpy`) plus per-block vector multiplies vibemix already does in `render_block`. No model, no FFT, no torch/transformers/librosa. The crossfader law is ~15 lines of pure Python; the dB taper is two one-liners (`db2ratio = lambda db: 10**(db/20)`). Per-block ramped gain (old→new linear interp over n samples) is one `np.linspace` multiply. Zero new dependencies. The only "cost" is matching Mixxx's [-1,+1] xfader convention and the `transform`/calibration parameters — pure refactor.

---

## (4) THE VIBEMIX GAP + NEAREST INTEGRATION POINT (verified)

**Two distinct wins, both verified against the repo:**

### Gap A — MiniDeck is a toy mixer; upgrade it to a faithful practice mixer
`MiniDeck` (`/Users/ozai/projects/dj-set-ai/src/vibemix/audio/miniplayer.py:99-145`, confirmed via codegraph `MiniDeck class @ miniplayer.py:99`) today has only: two source slabs, per-deck `rate`, one global `xfader`, and `_equal_power_gains` = fixed `cos/sin` (`miniplayer.py:69-79`). It is missing, relative to Mixxx:
- **Per-deck volume faders** (the `ControlAudioTaperPot(-20,0)` dB taper) — without these the learning engine cannot grade "you used the line fader to bring it in" vs "you used the crossfader," which are different skills in the Earned skill-tree.
- **The real Mixxx crossfader law** — replace `cos/sin` with `getXfadeGains(position, transform, mode)` so the practice mixer matches what the student's actual hardware (the 10-controller MIDI catalog `midi/profiles/`) does. Add `transform` (curve) + `mode` (additive vs const-power) as MiniDeck attributes mirroring `m_pXFaderCurve`/`m_pXFaderMode`.
- **Orientation routing** (deck assigned LEFT/RIGHT/CENTER) — so "channel assigned to center bypasses the xfader" is gradeable.

Concrete shape: extend `DeckState` (`miniplayer.py:83-96`) with `vol_a`, `vol_b`, `xfader_curve`, `xfader_mode`; rewrite `_equal_power_gains` into a `mixxx_xfade_gains(position, transform, mode)` clean-room of `enginexfader.cpp`; in `render_block` (`miniplayer.py:130-135`) compute `gain_a = vol_a · g_left`, `gain_b = vol_b · g_right` with ramped interpolation across the block (the `applyRampingGain` anti-click behavior). The tests at `tests/audio/test_miniplayer.py` (`test_minideck_center_xfader_mixes_both_decks_equal_power`, `_equal_power_gains` imported there) will need updating to the new law — they currently pin the cos/sin behavior.

### Gap B (THE BIG ONE) — ground "you rode the crossfader / brought the fader up" by COMPUTING the spectral/level effect
This is the R-SLOP path. The live-claim guard machinery is in `/Users/ozai/projects/dj-set-ai/src/vibemix/state/deck_context.py`: `apply_live_claim_guard` (`:2239`), `live_claim_policy`, `_has_unsupported_mixer_low_kill_claim` (`:2267`), and the fader/xfader regexes (`:106-107, 133, 150, 155`). Today the guard catches an *ungrounded* crossfader/fader claim and downgrades it to `LIVE_MOVE_EFFECT_HELD_REPLY` — it can say "I won't claim that move did X" but it **cannot affirmatively compute what the move DID**, because it has no model of the gain math. The `_xfader_factor` heuristic (`deck_context.py:3254-3267`) is a crude 0-127 bucket, not the real curve.

The Mixxx crossfader + gain-stage law is exactly the missing physics: given the known move (xfader went 64→112, or line-fader-A came up) and the deck audio in the window (vibemix already attaches `deck_mixer` + `audio_window` + `audio_delta` to the `ai_message` snapshot — see `deck_context.py:1661` `volatile=deck_state+deck_mixer+recent_moves+audio_delta+audio_window`), vibemix can compute the *expected* level/spectral change: e.g. "deck B orientation gain went from `1-pow(0.5^(1/t)·..., t)` ≈ 0.13 to ≈ 0.92 → +17 dB on deck B's contribution," then **confirm it against the measured `audio_delta`** (the RMS/band-energy change already in the window). That turns "you rode the crossfader and brought the energy up" from an ungrounded causal claim into a grounded one (Invariant #2 / #3): the claim is licensed only when computed-expected-effect ∧ measured-effect agree in sign and rough magnitude.

Nearest integration point: a new pure helper (e.g. `state/mixer_physics.py` — import-light, sits next to `intel/`) implementing `mixxx_xfade_gains` + `db_taper_gain` + `expected_move_effect(move, deck_mixer, audio_window) → ExpectedEffect`, called from `live_claim_policy`/`apply_live_claim_guard` in `deck_context.py:2239-2278` so the guard can *license* a move-effect claim instead of only suppressing it. Same helper backs the MiniDeck rewrite (Gap A) — one clean-room of `enginexfader.cpp` serves both the practice mixer and the live grounding gate.

Files: practice mixer = `/Users/ozai/projects/dj-set-ai/src/vibemix/audio/miniplayer.py` (+ `tests/audio/test_miniplayer.py`); live grounding = `/Users/ozai/projects/dj-set-ai/src/vibemix/state/deck_context.py` (`apply_live_claim_guard` @ :2239, `_has_unsupported_mixer_low_kill_claim` @ :2267, `_xfader_factor` @ :3254); proposed shared physics module `src/vibemix/state/mixer_physics.py` (new).

(Cleanup note: I wrote two scratch probe files into the repo root during tool bring-up — `/Users/ozai/projects/dj-set-ai/_mixxx_probe.txt` and `/Users/ozai/projects/dj-set-ai/_mx_grep.txt` — both untracked; delete them.)
