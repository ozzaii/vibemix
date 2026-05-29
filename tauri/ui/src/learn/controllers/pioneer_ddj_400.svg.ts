// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 06 — DDJ-400 inline-SVG controller schematic.
//
// Provenance: Hand-authored from the DDJ-400 "Operating Instructions"
// appendix hardware-diagram (publisher: AlphaTheta Corp., ©2019 revision;
// Apache-clean derivative geometry — factual control layout only, NO
// vendor logo, NO faceplate photo-lift, NO brand-orange). The DDJ-400 is
// the rekordbox-entry 2-channel controller; its mixer matches the FLX4
// chassis MINUS per-deck filter knobs (the DDJ-400 ships no Sound Color
// FX surrogate per the rekordbox-default mapping).
//
// CDJ-Whisper aesthetic: silk-22 strokes on warm-black void, currentColor
// throughout so the P92 highlight pattern can flip `var(--learn-highlight)`
// on selected `<g>` groups in a single CSS-variable swap (RENDER-04).
//
// Parity contract (RENDER-06): every `data-control-id` resolves to a
// binding in `src/vibemix/midi/profiles/pioneer_ddj_400.json`, and
// every profile binding resolves to a `<g>` here. The 23-entry set is:
//   - controls: vol:A vol:B eq_hi:A eq_hi:B eq_mid:A eq_mid:B
//     eq_low:A eq_low:B tempo:A tempo:B xfader
//     (no filter:A/B — DDJ-400 has no Color FX section)
//   - buttons:  play:A play:B cue:A cue:B sync:A sync:B
//     jog_touch:A jog_touch:B loop_in:A loop_in:B loop_out:A loop_out:B

export const PIONEER_DDJ_400_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" class="learn-controller-schematic">
  <!-- Faceplate outline (non-interactive, decorative) -->
  <rect x="60" y="60" width="1160" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.55"/>
  <rect x="80" y="80" width="1120" height="560" rx="10" ry="10"
        stroke="currentColor" stroke-width="1" fill="none" opacity="0.32"/>

  <!-- Decorative deck-A / mixer / deck-B section separators (silk hairlines) -->
  <line x1="430" y1="100" x2="430" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="850" y1="100" x2="850" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>

  <!-- Section labels (decorative — JetBrains Mono) -->
  <text x="270" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK A</text>
  <text x="640" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MIXER</text>
  <text x="1010" y="115" font-family="'JetBrains Mono', monospace" font-size="11"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK B</text>

  <!-- ============================================================= -->
  <!-- DECK A — jog wheel, transport, pitch fader, loop in/out      -->
  <!-- ============================================================= -->

  <!-- Jog wheel A -->
  <g data-control-id="jog_touch:A" role="button" aria-label="jog wheel, deck A" tabindex="0"
     data-cx="265" data-cy="280">
    <circle cx="265" cy="280" r="100" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="265" cy="280" r="78" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="265" cy="280" r="42" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
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

  <!-- Pitch fader A (tempo) -->
  <g data-control-id="tempo:A" role="button" aria-label="pitch fader, deck A" tabindex="0"
     data-cx="395" data-cy="320">
    <rect x="388" y="220" width="14" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="380" y1="320" x2="410" y2="320" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="382" y="312" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- MIXER — EQ stacks + channel faders + crossfader              -->
  <!-- (DDJ-400 omits Color FX filter knobs)                         -->
  <!-- ============================================================= -->

  <!-- EQ HI A -->
  <g data-control-id="eq_hi:A" role="button" aria-label="EQ-HI knob, deck A" tabindex="0"
     data-cx="500" data-cy="220">
    <circle cx="500" cy="220" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="201" x2="500" y2="217" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="270" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ HI B -->
  <g data-control-id="eq_hi:B" role="button" aria-label="EQ-HI knob, deck B" tabindex="0"
     data-cx="780" data-cy="220">
    <circle cx="780" cy="220" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="201" x2="780" y2="217" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="270" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID A -->
  <g data-control-id="eq_mid:A" role="button" aria-label="EQ-MID knob, deck A" tabindex="0"
     data-cx="500" data-cy="305">
    <circle cx="500" cy="305" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="286" x2="500" y2="302" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="355" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ MID B -->
  <g data-control-id="eq_mid:B" role="button" aria-label="EQ-MID knob, deck B" tabindex="0"
     data-cx="780" data-cy="305">
    <circle cx="780" cy="305" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="286" x2="780" y2="302" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="355" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW A -->
  <g data-control-id="eq_low:A" role="button" aria-label="EQ-LOW knob, deck A" tabindex="0"
     data-cx="500" data-cy="395">
    <circle cx="500" cy="395" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="500" y1="376" x2="500" y2="392" stroke="currentColor" stroke-width="1.5"/>
    <text x="500" y="445" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- EQ LOW B -->
  <g data-control-id="eq_low:B" role="button" aria-label="EQ-LOW knob, deck B" tabindex="0"
     data-cx="780" data-cy="395">
    <circle cx="780" cy="395" r="24" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <line x1="780" y1="376" x2="780" y2="392" stroke="currentColor" stroke-width="1.5"/>
    <text x="780" y="445" font-family="'JetBrains Mono', monospace" font-size="9"
          letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>
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

  <!-- Transport row B -->
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
