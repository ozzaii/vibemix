// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 06 — Hercules DJControl Inpulse 300 inline-SVG schematic.
//
// Provenance: Hand-authored from the Hercules DJControl Inpulse 300
// "Reference Manual" hardware-layout appendix (publisher: Guillemot Corp.,
// ©2020 revision; Apache-clean derivative geometry — factual control
// layout only, NO vendor logo, NO faceplate photo-lift). The Inpulse 300
// is the Hercules entry-level DJUCED-native 2-deck controller with
// Serato/Algoriddim cross-support; physical layout differs from Pioneer
// in two ways: (1) no jog touch-sensing — the jogs are plain encoders,
// the profile binds no `jog_touch` button; (2) prominent 4-pad
// performance grid per deck for hotcues 1-4 (mapped to a single
// `hotcue:<deck>` wire-key per profile.field/kind reduction).
//
// CDJ-Whisper aesthetic: silk-22 strokes on warm-black void, currentColor
// throughout so the P92 highlight pattern can flip `var(--learn-highlight)`
// on selected `<g>` groups in a single CSS-variable swap.
//
// Parity contract (RENDER-06): every `data-control-id` resolves to a
// binding in `src/vibemix/midi/profiles/hercules_inpulse_300.json`, and
// every profile binding resolves to a `<g>` here. The 21-entry set is:
//   - controls: vol:A vol:B eq_hi:A eq_hi:B eq_mid:A eq_mid:B
//     eq_low:A eq_low:B tempo:A tempo:B filter:A filter:B xfader
//   - buttons:  play:A play:B cue:A cue:B sync:A sync:B
//                hotcue:A hotcue:B
//
// MK2 detection: the Inpulse 300-MK2 shares this schematic in P91 — the
// rendered control set is functionally identical. The §LEARN-MK2-DETECTION
// KAAN-ACTION (P97) wires real-port-name detection later; until then both
// 300 and 300-MK2 land on this SVG.

export const HERCULES_INPULSE_300_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" role="img" aria-label="Hercules DJControl Inpulse 300 schematic" class="learn-controller-schematic">
  <!-- Faceplate outline (non-interactive, decorative) -->
  <rect x="60" y="60" width="1160" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.55"/>
  <rect x="80" y="80" width="1120" height="560" rx="10" ry="10"
        stroke="currentColor" stroke-width="1" fill="none" opacity="0.32"/>

  <!-- Section separators -->
  <line x1="430" y1="100" x2="430" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="850" y1="100" x2="850" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>

  <text x="270" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK A</text>
  <text x="640" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MIXER</text>
  <text x="1010" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK B</text>

  <!-- ============================================================= -->
  <!-- DECK A — jog encoder + transport + pad grid + pitch fader     -->
  <!-- ============================================================= -->

  <!-- Jog A (Hercules: non-touch-sensing encoder; the profile binds no
       jog_touch button, so this is a decorative reference circle — no
       data-control-id) -->
  <circle cx="265" cy="245" r="85" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.7"/>
  <circle cx="265" cy="245" r="65" stroke="currentColor" stroke-width="1" fill="none" opacity="0.4"/>
  <circle cx="265" cy="245" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.3"/>
  <line x1="265" y1="170" x2="265" y2="195" stroke="currentColor" stroke-width="1.5"/>
  <text x="265" y="350" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.45">JOG</text>

  <!-- Transport row A: PLAY · CUE · SYNC -->
  <g data-control-id="play:A" role="button" aria-label="play button, deck A" tabindex="0"
     data-cx="200" data-cy="395">
    <rect x="170" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="200" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:A" role="button" aria-label="cue button, deck A" tabindex="0"
     data-cx="265" data-cy="395">
    <rect x="235" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="265" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:A" role="button" aria-label="sync button, deck A" tabindex="0"
     data-cx="330" data-cy="395">
    <rect x="300" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="330" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Hot-cue pad grid A — 4 square pads (the profile binds hotcue_1
       through hotcue_4 on deck A, all reducing to the single wire-key
       hotcue:A per profile.kind without distinct .field). Layout: 4
       pads in a row, the Hercules signature pad-strip aesthetic. -->
  <g data-control-id="hotcue:A" role="button" aria-label="hot-cue pads, deck A" tabindex="0">
    <rect x="155" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="220" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="285" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="350" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="280" y="513" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">HOT CUE 1-4</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Pitch fader A (tempo) -->
  <g data-control-id="tempo:A" role="button" aria-label="pitch fader, deck A" tabindex="0"
     data-cx="395" data-cy="280">
    <rect x="388" y="190" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="380" y1="280" x2="410" y2="280" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="382" y="272" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- MIXER — EQ stacks + channel faders + crossfader + filter     -->
  <!-- ============================================================= -->

  <!-- EQ HI A -->
  <g data-control-id="eq_hi:A" role="button" aria-label="EQ-HI knob, deck A" tabindex="0"
     data-cx="500" data-cy="200">
    <circle cx="500" cy="200" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="183" x2="500" y2="197" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="248" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ HI B -->
  <g data-control-id="eq_hi:B" role="button" aria-label="EQ-HI knob, deck B" tabindex="0"
     data-cx="780" data-cy="200">
    <circle cx="780" cy="200" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="183" x2="780" y2="197" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="248" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID A -->
  <g data-control-id="eq_mid:A" role="button" aria-label="EQ-MID knob, deck A" tabindex="0"
     data-cx="500" data-cy="280">
    <circle cx="500" cy="280" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="263" x2="500" y2="277" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="328" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID B -->
  <g data-control-id="eq_mid:B" role="button" aria-label="EQ-MID knob, deck B" tabindex="0"
     data-cx="780" data-cy="280">
    <circle cx="780" cy="280" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="263" x2="780" y2="277" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="328" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW A -->
  <g data-control-id="eq_low:A" role="button" aria-label="EQ-LOW knob, deck A" tabindex="0"
     data-cx="500" data-cy="360">
    <circle cx="500" cy="360" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="343" x2="500" y2="357" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="408" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW B -->
  <g data-control-id="eq_low:B" role="button" aria-label="EQ-LOW knob, deck B" tabindex="0"
     data-cx="780" data-cy="360">
    <circle cx="780" cy="360" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="343" x2="780" y2="357" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="408" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Filter A -->
  <g data-control-id="filter:A" role="button" aria-label="filter knob, deck A" tabindex="0"
     data-cx="500" data-cy="448">
    <circle cx="500" cy="448" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="433" x2="500" y2="445" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">FILTER</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Filter B -->
  <g data-control-id="filter:B" role="button" aria-label="filter knob, deck B" tabindex="0"
     data-cx="780" data-cy="448">
    <circle cx="780" cy="448" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="433" x2="780" y2="445" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">FILTER</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Channel fader A -->
  <g data-control-id="vol:A" role="button" aria-label="channel fader, deck A" tabindex="0"
     data-cx="580" data-cy="430">
    <rect x="573" y="220" width="14" height="220" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="565" y="420" width="30" height="18" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Channel fader B -->
  <g data-control-id="vol:B" role="button" aria-label="channel fader, deck B" tabindex="0"
     data-cx="700" data-cy="430">
    <rect x="693" y="220" width="14" height="220" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="685" y="420" width="30" height="18" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Crossfader -->
  <g data-control-id="xfader" role="button" aria-label="crossfader" tabindex="0"
     data-cx="640" data-cy="540">
    <rect x="490" y="533" width="300" height="14" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="640" y1="525" x2="640" y2="555" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="632" y="525" width="16" height="30" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK B — jog encoder + transport + pad grid + pitch fader    -->
  <!-- ============================================================= -->

  <!-- Jog B (decorative reference circle — no jog_touch binding) -->
  <circle cx="1015" cy="245" r="85" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.7"/>
  <circle cx="1015" cy="245" r="65" stroke="currentColor" stroke-width="1" fill="none" opacity="0.4"/>
  <circle cx="1015" cy="245" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.3"/>
  <line x1="1015" y1="170" x2="1015" y2="195" stroke="currentColor" stroke-width="1.5"/>
  <text x="1015" y="350" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.45">JOG</text>

  <!-- Transport row B -->
  <g data-control-id="play:B" role="button" aria-label="play button, deck B" tabindex="0"
     data-cx="950" data-cy="395">
    <rect x="920" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="950" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:B" role="button" aria-label="cue button, deck B" tabindex="0"
     data-cx="1015" data-cy="395">
    <rect x="985" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1015" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:B" role="button" aria-label="sync button, deck B" tabindex="0"
     data-cx="1080" data-cy="395">
    <rect x="1050" y="375" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1080" y="401" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Hot-cue pad grid B -->
  <g data-control-id="hotcue:B" role="button" aria-label="hot-cue pads, deck B" tabindex="0">
    <rect x="905" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="970" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="1035" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="1100" y="450" width="55" height="38" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1030" y="513" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">HOT CUE 1-4</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Pitch fader B (tempo) -->
  <g data-control-id="tempo:B" role="button" aria-label="pitch fader, deck B" tabindex="0"
     data-cx="885" data-cy="280">
    <rect x="878" y="190" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="870" y1="280" x2="900" y2="280" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="872" y="272" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
</svg>`;
