# MIXXX ROUND 2 — Controller Mapping Engine + Device Catalog (clean-room spec for vibemix)

## SCOPE NOTE / CORPUS CAVEAT
Only `/tmp/mixxx-src/src/` was cloned. The community device-mapping zoo (`res/controllers/*.midi.xml` + `*.js`, the hundreds of mappings) is NOT on disk — I read the ENGINE that consumes them, plus the XML schema parser (`legacymidicontrollermappingfilehandler.cpp`), which fully specifies the file format vibemix would generate/ingest. No GPL source vendored; all below is algorithm-in-my-own-words. Tools note: Glob/Grep are unavailable in this subagent — used Bash `ls/grep` instead.

---

## (1) THE ALGORITHM (reimplement clean-room in Python)

### 1A. Mapping architecture: raw MIDI → control action (signal flow)
Mixxx's pipeline (`midicontroller.cpp::receivedShortMessage` → `processInputMapping`):

1. **Decode status byte.** `opcode = status & 0xF0`; if `opcode == 0xF0` the whole byte IS the opcode (system messages have no channel). `channel = status & 0x0F`. (`midiutils.h:8-23`)
2. **Build a 16-bit lookup key.** `MidiKey.key = (status << 8) | control` — status in the high byte, CC#/note# in the low byte (a union/bitfield, `midimessage.h:166-182`). Mappings are stored in a **multimap** keyed by this 16-bit value (multiple actions can bind one input).
3. **Drop clock spam early.** `status == 0xF8` (timing clock, 24 ppqn) is discarded before any dispatch (`midicontroller.cpp:288`).
4. **Look up + dispatch every binding** for that key via `equal_range` (multimap → fan-out). Each binding is either a `ConfigKey` (XML static binding) or a JS function (script binding).
5. **Per-binding value transform** (`processInputMapping`, the core): if `options` has `Script`, call the JS function with `(channel, control, value, status, group)`; otherwise resolve the target `ControlObject`, compute the cooked value, run soft-takeover gate, then `setValueFromMidi`.

### 1B. The MidiOption bitfield (the decode-mode catalog — `midimessage.h:107-134`)
A 16-bit flag set; vibemix's `axis` enum is a narrow subset. Full Mixxx set with semantics:

| Flag | bit | meaning / math |
|---|---|---|
| `Invert` | 0x0001 | `127 - value` |
| `Rot64` | 0x0002 | relative-from-64 encoder (see 1C) |
| `Rot64Invert` | 0x0004 | same, reversed sign |
| `Rot64Fast` | 0x0008 | `prev + (value-64)*1.5`, clamped 0..127 |
| `Diff` | 0x0010 | 7-bit two's-complement relative: if `v≥64: v-=128`, then `new = prev + v` |
| `Button` | 0x0020 | `value = (value != 0)`; forces opcode→NoteOn |
| `Switch` | 0x0040 | `value = 1` always (latch); forces opcode→NoteOn |
| `Spread64` | 0x0080 | `value - 64` (centered relative; non-linear scaling stubbed) |
| `HercJog` | 0x0100 | Hercules range-correct: if `v>64: v-=128`, then `prev + v` |
| `SelectKnob` | 0x0200 | two's-complement relative like Diff but does NOT inherit prev (selection-only) |
| `SoftTakeover` | 0x0400 | enable soft-takeover gate (see 1D) |
| `Script` | 0x0800 | route to a JS function instead of a ControlObject |
| `FourteenBitLSB` | 0x1000 | this message carries the low 7 bits of a 14-bit pair |
| `FourteenBitMSB` | 0x2000 | this message carries the high 7 bits |
| `HercJogFast` | 0x4000 | `prev + value*3` after the `v>64 → v-=128` correction |

`computeValue` (`midicontroller.cpp:495-595`) is a flag-ordered cascade. Reimplement each branch verbatim.

### 1C. Rot64 relative-encoder math (the one vibemix is MISSING — `midicontroller.cpp:508-530`)
```
diff = value - 64
if diff == -1 or diff == 1:   diff /= 16        # fine 1-tick → 1/16 step (slow-twist precision)
else:                          diff += (-1 if diff>0 else +1)   # de-bias the ±1 dead-step
result = clamp(prev + diff, 0, 127)             # Rot64; subtract for Rot64Invert
```
This is the proper "endless knob/jog" decode: an absolute-ish accumulator with a fine-step near center and coarse steps farther out. vibemix's `relative` axis is much cruder (any non-64 → ±1.0 full-strength event). **Rot64 is the missing precise encoder model.**

### 1D. Soft-takeover (the headline UX algorithm — `softtakeover.cpp:15-88`, `softtakeover.h:13-60`)
Purpose: a physical fader/knob whose hardware position differs from the software value would cause an audible JUMP the instant you touch it. Soft-takeover **ignores** controller values until the hardware "catches up" to (crosses) the software value.

State per control: `prev_param` (last received, normalized 0..1), `last_accept_time`, `threshold = 3/128 ≈ 0.0234` (tuned experimentally; `softtakeover.h:20`).

`willIgnore(current_software_param, new_param, now)` returns True (ignore the move) iff:
1. First value ever (`m_time == kFirstValueTime`) → **ignore** (avoids the boot jump). After first, store a sentinel time so this only fires once.
2. Else if `now < last_accept_time + 50ms` (`kSubsequentValueOverrideTime`) → **accept** (return False). This is the "fast whip" exception: rapid consecutive moves are let through so quick gestures still work.
3. Compute `difference = current - new`, `prevDiff = current - prev`.
4. **Opposite sides** (`sign(prevDiff) != sign(difference)`, i.e. the knob crossed the software value) → **accept**. The hardware caught up.
5. **Same side** but `|difference| ≤ threshold OR |prevDiff| ≤ threshold` (close enough) → **accept**.
6. Otherwise (far away, same side, not whipping) → **ignore**.

`ignore()` wraps `willIgnore` and updates `prev_param` every call but `last_accept_time` ONLY on accept. The truth table is in the source comment (`softtakeover.cpp:34-40`). Soft-takeover is only enabled on potmeter-type controls (continuous), never buttons (`midicontroller.cpp:481-491`).

### 1E. 14-bit (high-res) decode — `midicontroller.cpp:390-470`
Two CCs combine into one 14-bit value (0x0000–0x3FFF) for high-res faders/jogs:
- Messages arrive as separate MSB and LSB CCs. The first to arrive is **queued** (`m_fourteen_bit_queued_mappings`, a pending list keyed by ConfigKey); the second completes the pair.
- `MSB-first: combined = (value << 7) | queued_lsb`. `LSB-first: combined = (queued_lsb << 7) | value`. (7-bit halves, top bit always 0 in MIDI data bytes.)
- **The normalization quirk (NOTE rryan, line 435-440):** `newValue = combined / 128.0`, then `min(newValue, 127.0)`. Dividing by **128 (not 129/0x81)** maps the 14-bit center 0x2000 EXACTLY to 0x40 (64) — so a center-detented hi-res control lands on the same 64 a 7-bit control would. Cooked value stays in 0..127 like 7-bit.
- Mismatch guards: a non-14-bit message arriving mid-pair clears the queue (warns); mismatched MSB/MSB or LSB/LSB options drop both.
- **Pitch-bend (`0xE0`)** is handled identically: `combined = (value<<7) | control` (the two data bytes ARE the 14-bit value), then `/128.0`.

### 1F. The XML mapping file format (the device-catalog schema — `legacymidicontrollermappingfilehandler.cpp`)
This is the exact format every community mapping uses, and the spec vibemix needs to ingest/emit Mixxx-scale coverage:
```
<controller>
  <controls>
    <control>
      <status>0xB0</status>          # status byte (hex/oct/dec auto via toInt base 0)
      <midino>0x07</midino>          # CC# or note#  (absent/0xFF for sysex)
      <group>[Channel1]</group>      # target group  (deck/master/etc.)
      <key>filterHigh</key>          # target control name
      <description>...</description> # optional
      <options>
        <invert/> <soft-takeover/> <fourteen-bit-msb/> ...   # option element names below
      </options>
    </control>
  </controls>
  <outputs>
    <output>
      <status>.../<midino>.../<group>.../<key>...
      <on>0x7F</on> <off>0x00</off>          # LED on/off bytes (defaults shown)
      <minimum>0.0</minimum> <maximum>1.0</maximum>   # value→LED thresholds
    </output>
  </outputs>
</controller>
```
**Option element name → flag map** (`legacy...filehandler.cpp:76-105`): `invert, rot64, rot64inv, rot64fast, diff, button, switch, hercjog, hercjogfast, spread64, selectknob, soft-takeover, script-binding, fourteen-bit-msb, fourteen-bit-lsb`. "normal" = no options. Output defaults: `on=0x7F, off=0x00, min=0.0, max=1.0`.

### 1G. Scripting hooks (the JS engine surface — `controllerscriptinterfacelegacy.h`)
The `engine` object exposed to controller JS. The DJ-meaningful subset (the verbs vibemix can MODEL as grounded events):
- `getValue/setValue/getParameter/setParameter(group, name, …)` — read/write any control.
- `softTakeover(group,name,bool)`, `softTakeoverIgnoreNextValue`, `softTakeoverWillIgnore` — script-side soft-takeover control (same engine as 1D).
- `scratchEnable(deck, intervalsPerRev, rpm, alpha, beta, ramp)` / `scratchTick(deck, interval)` / `scratchDisable` — **alpha-beta filter** jog-scratch (an AlphaBetaFilter integrates jog ticks into a velocity; this is the proper jog→pitch model, far richer than vibemix's ±1 nudge).
- `brake(deck, on, factor, rate)` / `spinback(deck,on,factor=1.8,rate=-10)` / `softStart` — turntable-stop/start ramps.
- `makeConnection(group, name, callback)` — register a callback fired on any control change (LED feedback path).
- Anonymous-function input handlers (`midicontroller.cpp:643` `makeInputHandler`): `midi.makeInputHandler(status, control, fn)` binds a JS callback directly to a raw MIDI key, returning a disconnectable handle. This is how complex controllers (shift layers, banks) decode beyond static XML.

---

## (2) MIXXX FILE:LINE REFERENCES (method references, not code to lift)
- Raw-MIDI dispatch + value cooking: `src/controllers/midi/midicontroller.cpp:274-595` (`receivedShortMessage` :274, `processInputMapping` :323, 14-bit :390-470, pitchbend :457, `computeValue` :495).
- Opcode/channel extraction, two-byte test, clock test: `src/controllers/midi/midiutils.h:8-54`.
- MidiOption bitfield + MidiKey/MidiInputMapping/MidiOutput structs: `src/controllers/midi/midimessage.h:107-254`.
- Soft-takeover algorithm + thresholds: `src/controllers/softtakeover.cpp:15-88`, `src/controllers/softtakeover.h:20,54-55` (threshold `3/128`, override-window `50ms`).
- XML mapping schema parse/serialize + option-name table: `src/controllers/midi/legacymidicontrollermappingfilehandler.cpp:36-426` (option map :76-105, output defaults :6-9).
- Script API surface: `src/controllers/scripting/legacy/controllerscriptinterfacelegacy.h:58-115`.
- MIDI-learn temporary-mapping flow: `src/controllers/midi/midicontroller.cpp:220-272`, `src/controllers/learningutils.cpp` (not read; the deduction engine).
- HID path (separate, for non-MIDI controllers): `src/controllers/hid/` (`hidcontroller.cpp`, `hidreportdescriptor.cpp` — report-descriptor parse; not mined deeply this round).

---

## (3) TORCH-FREE FEASIBILITY
**Fully torch-free and dependency-free.** Everything in (1) is integer bit-twiddling, scalar float arithmetic, dict lookups, and one `time.monotonic()` comparison. No numpy needed (vibemix's `state.py` decoder is already pure-Python). Soft-takeover is ~30 lines of pure Python; the MidiOption cascade is a flag-ordered if-chain; 14-bit pairing is a small pending-dict. The XML parser would use stdlib `xml.etree.ElementTree` (already implied by vibemix's stdlib-only posture). Zero new deps; aligns with `onnxruntime + tokenizers + PyAV + numpy` baseline.

---

## (4) THE VIBEMIX GAP + NEAREST INTEGRATION POINTS (verified by grep/read)

### GAP A — Relative-encoder decode is crude (HIGH value, the jog/select-knob class)
vibemix `state.py::_compute_magnitude` maps **any** `relative` tick (`v != 64`) to `±1.0` (`state.py:290-294`). The FLX4 profile comment even notes jog ticks arrive as 63/65 around center. Mixxx's **Rot64** (1C) and **scratchTick alpha-beta** models turn ticks into a *magnitude-aware* velocity (1-tick = 1/16 step; de-biased ±1). Without this, vibemix cannot tell a slow nudge from a hard spin, and cannot accumulate a select-knob into a position.
- **Integration point:** `src/vibemix/midi/state.py:276-297` (`_compute_magnitude`) + add `axis: "rot64" | "diff" | "selectknob"` to `_VALID_AXES` in `src/vibemix/midi/profile.py:59`. Carry a per-binding accumulator in `ControllerState` (it already has `self.deck[deck][field]` to hold `prev`). This is additive and backward-compatible (existing `relative` axis untouched → FLX4 golden decode preserved).

### GAP B — No soft-takeover model (MEDIUM, but the R-SLOP unlock)
vibemix has zero soft-takeover (`grep soft.?takeover src/vibemix/midi` → empty). vibemix only OBSERVES the controller (never writes back to the DJ app), so it doesn't need takeover to prevent jumps — BUT the *concept* is directly useful for grounding: a fader move whose hardware was far from the software value is a **"catch-up / no audible effect yet"** move, while a crossing move is a **"this is the one that takes over the sound"** move. That distinction is exactly what `apply_live_claim_guard` (deck_context.py:2239) needs to stop R-SLOP. Today the guard is REGEX-based (`_NO_MOVE_CONTROL_ACTION_RE`, `_MOVE_EFFECT_*_RE` at deck_context.py:104-162) — it catches the *words* of an ungrounded causal claim but has no *signal* proving the move did/didn't change the audio.
- **Integration point:** add a `would_ignore`-style classifier in `state.py` per CC event (port the `willIgnore` truth table, 1D) and surface it on `MidiEvent` (new field, e.g. `takeover_phase: "catching_up" | "crossed" | "engaged"`). Then `apply_live_claim_guard` (deck_context.py:2239) can upgrade a causal claim from "ungrounded → strip to ack-bank" to "grounded → allowed" only when the move's `takeover_phase == "crossed"/"engaged"` AND a corroborating `audio_delta` exists. This is the precise grounding the THE BIG ONE asks for: it converts "you brought the faders up [recent_moves=[]]" slop into a move that is allowed to claim effect ONLY when the controller signal proves the move actually reached/crossed the live value.

### GAP C — 14-bit high-res decode missing (LOW-MEDIUM)
vibemix has no MSB/LSB pairing (`grep -i fourteen/14-bit src/vibemix/midi` → empty). Pro controllers (DDJ-1000, FLX10, XDJ-RX3 — already in the catalog as JSON-only) send 14-bit tempo faders. vibemix reads only the MSB CC, losing fine pitch resolution. Port the pairing queue (1E) into `state.py::handle_msg` and add `fourteen_bit_msb/lsb` to the profile `axis`/option vocabulary.
- **Integration point:** `src/vibemix/midi/state.py:299-371` (`handle_msg` CC branch) + `profile.py` schema.

### GAP D — Catalog scale: 11 profiles vs Mixxx's hundreds (HIGH for coverage)
vibemix ships 11 hand-written JSON profiles (`profiles/`: hercules ×3, numark, pioneer ×7). Mixxx's format (1F) is a strict superset of vibemix's JSON schema (`profile.py`). **The leverage move:** write a one-shot `mixxx_xml → vibemix_json` transcoder. Mixxx `<status>/<midino>` → vibemix `channel = status & 0x0F` + `cc/note`; `<options>` element names → vibemix `axis` (rot64/diff→`relative`, none→`unipolar`, the existing mapping) + future option flags; `<group>` like `[Channel1]/[Channel2]` → deck `A/B`; `<key>` like `filterHigh/volume/rate` → vibemix `field`. This bootstraps Mixxx-scale device coverage from the (GPL-data, but mappings are user-contributed config not Mixxx code — license-check each, do NOT bulk-vendor) community catalog by re-deriving the channel/cc/field mapping, not copying source.
- **Integration point:** new `src/vibemix/midi/import_mixxx.py` emitting into `src/vibemix/midi/profiles/*.json`; consumed unchanged by `registry.find_mapping` (registry.py:23) which already does port-name-hint substring matching analogous to Mixxx's product matching.

### GAP E — Generic-MIDI fallback is positional-only (LOW)
vibemix's `_handle_generic` (state.py:466) emits `cc_<ch>_<cc>` labels with no semantics — fine as a floor. Mixxx's MIDI-learn (`learningutils.cpp`, `dlgcontrollerlearning`) auto-DEDUCES option flags (button vs knob vs encoder) by watching value patterns during a learn gesture. A future "learn my controller" wizard for vibemix would port that deduction (not mined deeply this round; flagged for round 3).

**Net:** Gaps A + B are the highest-leverage and both land in the same two files (`state.py` decoder + `deck_context.py::apply_live_claim_guard`). B is the direct R-SLOP fix — soft-takeover's crossing-detection is the controller-side signal that lets the live-claim guard ground (not just regex-block) a "that move changed the sound" claim.
