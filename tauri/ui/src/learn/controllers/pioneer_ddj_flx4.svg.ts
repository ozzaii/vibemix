// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — DDJ-FLX4 inline-SVG controller schematic.
//
// Provenance: Hand-authored from the DDJ-FLX4 "Operating Instructions"
// appendix hardware-diagram (publisher: AlphaTheta Corp., ©2023 revision;
// Apache-clean derivative geometry — factual control layout only, NO
// vendor logo, NO faceplate photo-lift, NO brand-orange).
// CDJ-Whisper aesthetic: silk-22 strokes on warm-black void, currentColor
// throughout so the P92 highlight pattern can flip `var(--learn-highlight)`
// on selected `<g>` groups in a single CSS-variable swap (RENDER-04).
//
// Geometry: viewBox 0 0 1280 720 (matches Learn-window inner_size + the
// SVG-1:1 design grid declared in UI-SPEC §Design System). The faceplate
// preserves the 16:9 hardware aspect (FLX4 is 482×272 mm); margins are
// transparent space.
//
// Layout:
//   Deck A (x ~120-420)     Mixer (x ~440-840)         Deck B (x ~860-1160)
//   ─────────────────       ──────────────────         ─────────────────
//   Jog wheel + transport   2-channel mixer            Jog wheel + transport
//   Pitch fader             EQ stacks per deck         Pitch fader
//   Loop in/out             Channel faders             Loop in/out
//                           Crossfader
//                           Filter knobs per deck
//
// Every interactive control is wrapped in:
//   g data-control-id="<field>:<deck>" role="button"     (one <g> per control)
//      aria-label="<from _aria-labels>" tabindex="0"
//      data-cx="<center-x>" data-cy="<center-y>"
//     <factual geometry>
//     <g class="cue-color"></g>   ← P92 highlight slot (color channel)
//     <g class="cue-shape"></g>   ← P92 highlight slot (shape channel)
//   /g
//
// Parity contract (RENDER-06): every `data-control-id` resolves to a
// binding in `src/vibemix/midi/profiles/pioneer_ddj_flx4.json`, and
// every profile binding resolves to a `<g>` here. The 25-entry set is:
//   - controls: vol:A vol:B eq_hi:A eq_hi:B eq_mid:A eq_mid:B
//     eq_low:A eq_low:B tempo:A tempo:B filter:A filter:B xfader
//   - buttons:  play:A play:B cue:A cue:B sync:A sync:B
//     jog_touch:A jog_touch:B loop_in:A loop_in:B loop_out:A loop_out:B

export const PIONEER_DDJ_FLX4_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" class="learn-controller-schematic">
  <!-- Faceplate outline (non-interactive, decorative) -->
  <rect x="60" y="60" width="1160" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.55"/>
  <rect x="80" y="80" width="1120" height="560" rx="10" ry="10"
        stroke="currentColor" stroke-width="1" fill="none" opacity="0.32"/>

  <!-- Decorative deck-A / mixer / deck-B section separators (silk hairlines) -->
  <line x1="430" y1="100" x2="430" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="850" y1="100" x2="850" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>

  <!-- Deck-A label (decorative — JetBrains Mono) -->
  <text x="270" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK A</text>
  <text x="640" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MIXER</text>
  <text x="1010" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK B</text>

  <!-- ============================================================= -->
  <!-- DECK A — jog wheel, transport, pitch fader, loop in/out      -->
  <!-- ============================================================= -->

  <!-- Jog wheel A — circular touch-sensitive platter -->
  <g data-control-id="jog_touch:A" role="button" aria-label="jog wheel, deck A" tabindex="0"
     data-cx="265" data-cy="280">
    <circle cx="265" cy="280" r="100" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="265" cy="280" r="78" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="265" cy="280" r="42" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <!-- Index notch (the spin indicator) -->
    <line x1="265" y1="195" x2="265" y2="225" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Transport row A: PLAY · CUE · SYNC -->
  <g data-control-id="play:A" role="button" aria-label="play button, deck A" tabindex="0"
     data-cx="200" data-cy="430">
    <rect x="170" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="200" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:A" role="button" aria-label="cue button, deck A" tabindex="0"
     data-cx="265" data-cy="430">
    <rect x="235" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="265" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:A" role="button" aria-label="sync button, deck A" tabindex="0"
     data-cx="330" data-cy="430">
    <rect x="300" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="330" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Loop in/out row A -->
  <g data-control-id="loop_in:A" role="button" aria-label="loop-in button, deck A" tabindex="0"
     data-cx="180" data-cy="490">
    <rect x="155" y="470" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <text x="180" y="491" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">LOOP IN</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="loop_out:A" role="button" aria-label="loop-out button, deck A" tabindex="0"
     data-cx="235" data-cy="490">
    <rect x="210" y="470" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <text x="235" y="491" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">LOOP OUT</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Pitch fader A (tempo) — vertical bipolar slider on far-right edge of deck A -->
  <g data-control-id="tempo:A" role="button" aria-label="pitch fader, deck A" tabindex="0"
     data-cx="395" data-cy="320">
    <rect x="388" y="220" width="14" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <!-- Center detent line (bipolar 0%) -->
    <line x1="380" y1="320" x2="410" y2="320" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <!-- Thumb (centered = bypass; transform-only updates at runtime) -->
    <rect x="382" y="312" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- MIXER — EQ stacks, channel faders, crossfader, filter knobs   -->
  <!-- ============================================================= -->

  <!-- EQ HI A -->
  <g data-control-id="eq_hi:A" role="button" aria-label="EQ-HI knob, deck A" tabindex="0"
     data-cx="500" data-cy="200">
    <circle cx="500" cy="200" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <!-- Index marker (rotates at runtime via transform on the parent <g>) -->
    <line class="knob-indicator" x1="500" y1="183" x2="500" y2="197" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="248" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ HI B -->
  <g data-control-id="eq_hi:B" role="button" aria-label="EQ-HI knob, deck B" tabindex="0"
     data-cx="780" data-cy="200">
    <circle cx="780" cy="200" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="780" y1="183" x2="780" y2="197" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="248" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID A -->
  <g data-control-id="eq_mid:A" role="button" aria-label="EQ-MID knob, deck A" tabindex="0"
     data-cx="500" data-cy="280">
    <circle cx="500" cy="280" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="500" y1="263" x2="500" y2="277" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="328" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID B -->
  <g data-control-id="eq_mid:B" role="button" aria-label="EQ-MID knob, deck B" tabindex="0"
     data-cx="780" data-cy="280">
    <circle cx="780" cy="280" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="780" y1="263" x2="780" y2="277" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="328" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW A -->
  <g data-control-id="eq_low:A" role="button" aria-label="EQ-LOW knob, deck A" tabindex="0"
     data-cx="500" data-cy="360">
    <circle cx="500" cy="360" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="500" y1="343" x2="500" y2="357" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="408" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW B -->
  <g data-control-id="eq_low:B" role="button" aria-label="EQ-LOW knob, deck B" tabindex="0"
     data-cx="780" data-cy="360">
    <circle cx="780" cy="360" r="22" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="780" y1="343" x2="780" y2="357" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="408" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Filter A — single bipolar knob below EQ stack -->
  <g data-control-id="filter:A" role="button" aria-label="filter knob, deck A" tabindex="0"
     data-cx="500" data-cy="448">
    <circle cx="500" cy="448" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="500" y1="433" x2="500" y2="445" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">FILTER</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Filter B -->
  <g data-control-id="filter:B" role="button" aria-label="filter knob, deck B" tabindex="0"
     data-cx="780" data-cy="448">
    <circle cx="780" cy="448" r="20" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line class="knob-indicator" x1="780" y1="433" x2="780" y2="445" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">FILTER</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Channel fader A — vertical unipolar slider (the volume) -->
  <g data-control-id="vol:A" role="button" aria-label="channel fader, deck A" tabindex="0"
     data-cx="580" data-cy="430">
    <rect x="573" y="220" width="14" height="220" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <!-- Thumb at bottom = 0% gain (unipolar) -->
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

  <!-- Crossfader — horizontal bipolar slider at mixer bottom -->
  <g data-control-id="xfader" role="button" aria-label="crossfader" tabindex="0"
     data-cx="640" data-cy="540">
    <rect x="490" y="533" width="300" height="14" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <!-- Center detent line (A/B balance) -->
    <line x1="640" y1="525" x2="640" y2="555" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <!-- Thumb (centered = balanced) -->
    <rect x="632" y="525" width="16" height="30" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK B — jog wheel, transport, pitch fader, loop in/out      -->
  <!-- ============================================================= -->

  <!-- Jog wheel B -->
  <g data-control-id="jog_touch:B" role="button" aria-label="jog wheel, deck B" tabindex="0"
     data-cx="1015" data-cy="280">
    <circle cx="1015" cy="280" r="100" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="1015" cy="280" r="78" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="1015" cy="280" r="42" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="1015" y1="195" x2="1015" y2="225" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Transport row B: PLAY · CUE · SYNC -->
  <g data-control-id="play:B" role="button" aria-label="play button, deck B" tabindex="0"
     data-cx="950" data-cy="430">
    <rect x="920" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="950" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:B" role="button" aria-label="cue button, deck B" tabindex="0"
     data-cx="1015" data-cy="430">
    <rect x="985" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1015" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:B" role="button" aria-label="sync button, deck B" tabindex="0"
     data-cx="1080" data-cy="430">
    <rect x="1050" y="410" width="60" height="40" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1080" y="436" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Loop in/out row B -->
  <g data-control-id="loop_in:B" role="button" aria-label="loop-in button, deck B" tabindex="0"
     data-cx="985" data-cy="490">
    <rect x="960" y="470" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <text x="985" y="491" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">LOOP IN</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="loop_out:B" role="button" aria-label="loop-out button, deck B" tabindex="0"
     data-cx="1040" data-cy="490">
    <rect x="1015" y="470" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <text x="1040" y="491" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">LOOP OUT</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Pitch fader B (tempo) -->
  <g data-control-id="tempo:B" role="button" aria-label="pitch fader, deck B" tabindex="0"
     data-cx="885" data-cy="320">
    <rect x="878" y="220" width="14" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="870" y1="320" x2="900" y2="320" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="872" y="312" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
</svg>`;
