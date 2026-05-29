// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 06 — DDJ-1000 inline-SVG controller schematic.
//
// Provenance: Hand-authored from the DDJ-1000 "Operating Instructions"
// appendix hardware-diagram (publisher: AlphaTheta Corp., ©2018 revision
// + 2020 reprint; Apache-clean derivative geometry — factual control
// layout only, NO vendor logo, NO faceplate photo-lift, NO brand-orange).
// The DDJ-1000 is the CDJ-style rekordbox-pro 4-deck flagship; profile
// declares 4 deck channels but the hotcue pad surface is bound to decks
// A/B only (the C/D layer is shift-accessed; out of vibemix v1 scope).
//
// CDJ-Whisper aesthetic: silk-22 strokes on warm-black void,
// currentColor throughout.
//
// Parity contract (RENDER-06): every data-control-id resolves to a
// binding in src/vibemix/midi/profiles/pioneer_ddj_1000.json, and
// every profile binding resolves to a group here. The 43-entry set is:
//   - controls: vol/eq_hi/eq_mid/eq_low/tempo/filter per A,B,C,D
//                + xfader  (21 controls)
//   - buttons: play/cue/sync/jog_touch per A,B,C,D
//                + hotcue:A + hotcue:B  (18 buttons)

export const PIONEER_DDJ_1000_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" class="learn-controller-schematic">
  <!-- Faceplate outline -->
  <rect x="40" y="60" width="1200" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.55"/>
  <rect x="60" y="80" width="1160" height="560" rx="10" ry="10"
        stroke="currentColor" stroke-width="1" fill="none" opacity="0.32"/>

  <!-- 4-deck column separators -->
  <line x1="280" y1="100" x2="280" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="500" y1="100" x2="500" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="780" y1="100" x2="780" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>
  <line x1="1000" y1="100" x2="1000" y2="620" stroke="currentColor" stroke-width="1" opacity="0.18"/>

  <text x="170" y="115" font-family="'JetBrains Mono', monospace" font-size="10"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK A</text>
  <text x="390" y="115" font-family="'JetBrains Mono', monospace" font-size="10"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK B</text>
  <text x="640" y="115" font-family="'JetBrains Mono', monospace" font-size="10"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MIXER</text>
  <text x="890" y="115" font-family="'JetBrains Mono', monospace" font-size="10"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK C</text>
  <text x="1110" y="115" font-family="'JetBrains Mono', monospace" font-size="10"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">DECK D</text>

  <!-- ============================================================= -->
  <!-- DECK A — CDJ-style jog + transport + 4 hotcue pads + tempo    -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:A" role="button" aria-label="jog wheel, deck A" tabindex="0"
     data-cx="170" data-cy="220">
    <circle cx="170" cy="220" r="80" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="170" cy="220" r="62" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="170" cy="220" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="170" y1="150" x2="170" y2="178" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:A" role="button" aria-label="play button, deck A" tabindex="0"
     data-cx="135" data-cy="345">
    <rect x="110" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="135" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:A" role="button" aria-label="cue button, deck A" tabindex="0"
     data-cx="185" data-cy="345">
    <rect x="160" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="185" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:A" role="button" aria-label="sync button, deck A" tabindex="0"
     data-cx="235" data-cy="345">
    <rect x="210" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="235" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Hot-cue pad grid A — 4 square performance pads in a 2x2 grid
       (the profile binds hotcue 1..4 on deck A, all reducing to the
       single wire-key hotcue:A per profile.field/kind reduction) -->
  <g data-control-id="hotcue:A" role="button" aria-label="hot-cue pads, deck A" tabindex="0">
    <rect x="110" y="390" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="174" y="390" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="110" y="436" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="174" y="436" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="170" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">HOT CUE 1-4</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:A" role="button" aria-label="pitch fader, deck A" tabindex="0"
     data-cx="260" data-cy="555">
    <rect x="253" y="500" width="14" height="140" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="245" y1="570" x2="275" y2="570" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="247" y="562" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK B                                                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:B" role="button" aria-label="jog wheel, deck B" tabindex="0"
     data-cx="390" data-cy="220">
    <circle cx="390" cy="220" r="80" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="390" cy="220" r="62" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="390" cy="220" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="390" y1="150" x2="390" y2="178" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:B" role="button" aria-label="play button, deck B" tabindex="0"
     data-cx="355" data-cy="345">
    <rect x="330" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="355" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:B" role="button" aria-label="cue button, deck B" tabindex="0"
     data-cx="405" data-cy="345">
    <rect x="380" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="405" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:B" role="button" aria-label="sync button, deck B" tabindex="0"
     data-cx="455" data-cy="345">
    <rect x="430" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="455" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="hotcue:B" role="button" aria-label="hot-cue pads, deck B" tabindex="0">
    <rect x="330" y="390" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="394" y="390" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="330" y="436" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <rect x="394" y="436" width="56" height="36" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="390" y="492" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.55">HOT CUE 1-4</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:B" role="button" aria-label="pitch fader, deck B" tabindex="0"
     data-cx="480" data-cy="555">
    <rect x="473" y="500" width="14" height="140" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="465" y1="570" x2="495" y2="570" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="467" y="562" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- MIXER — 4-channel EQ stacks + filters + faders + crossfader   -->
  <!-- ============================================================= -->

  <g data-control-id="eq_hi:A" role="button" aria-label="EQ-HI knob, deck A" tabindex="0"
     data-cx="525" data-cy="170">
    <circle cx="525" cy="170" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="525" y1="158" x2="525" y2="168" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_hi:B" role="button" aria-label="EQ-HI knob, deck B" tabindex="0"
     data-cx="585" data-cy="170">
    <circle cx="585" cy="170" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="585" y1="158" x2="585" y2="168" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_hi:C" role="button" aria-label="EQ-HI knob, deck C" tabindex="0"
     data-cx="695" data-cy="170">
    <circle cx="695" cy="170" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="695" y1="158" x2="695" y2="168" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_hi:D" role="button" aria-label="EQ-HI knob, deck D" tabindex="0"
     data-cx="755" data-cy="170">
    <circle cx="755" cy="170" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="755" y1="158" x2="755" y2="168" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <text x="640" y="195" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">HI</text>

  <g data-control-id="eq_mid:A" role="button" aria-label="EQ-MID knob, deck A" tabindex="0"
     data-cx="525" data-cy="225">
    <circle cx="525" cy="225" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="525" y1="213" x2="525" y2="223" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_mid:B" role="button" aria-label="EQ-MID knob, deck B" tabindex="0"
     data-cx="585" data-cy="225">
    <circle cx="585" cy="225" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="585" y1="213" x2="585" y2="223" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_mid:C" role="button" aria-label="EQ-MID knob, deck C" tabindex="0"
     data-cx="695" data-cy="225">
    <circle cx="695" cy="225" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="695" y1="213" x2="695" y2="223" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_mid:D" role="button" aria-label="EQ-MID knob, deck D" tabindex="0"
     data-cx="755" data-cy="225">
    <circle cx="755" cy="225" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="755" y1="213" x2="755" y2="223" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <text x="640" y="250" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">MID</text>

  <g data-control-id="eq_low:A" role="button" aria-label="EQ-LOW knob, deck A" tabindex="0"
     data-cx="525" data-cy="280">
    <circle cx="525" cy="280" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="525" y1="268" x2="525" y2="278" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_low:B" role="button" aria-label="EQ-LOW knob, deck B" tabindex="0"
     data-cx="585" data-cy="280">
    <circle cx="585" cy="280" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="585" y1="268" x2="585" y2="278" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_low:C" role="button" aria-label="EQ-LOW knob, deck C" tabindex="0"
     data-cx="695" data-cy="280">
    <circle cx="695" cy="280" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="695" y1="268" x2="695" y2="278" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="eq_low:D" role="button" aria-label="EQ-LOW knob, deck D" tabindex="0"
     data-cx="755" data-cy="280">
    <circle cx="755" cy="280" r="16" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="755" y1="268" x2="755" y2="278" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <text x="640" y="305" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">LOW</text>

  <!-- Filters (per-channel Color FX) -->
  <g data-control-id="filter:A" role="button" aria-label="filter knob, deck A" tabindex="0"
     data-cx="525" data-cy="340">
    <circle cx="525" cy="340" r="14" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="525" y1="330" x2="525" y2="338" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="filter:B" role="button" aria-label="filter knob, deck B" tabindex="0"
     data-cx="585" data-cy="340">
    <circle cx="585" cy="340" r="14" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="585" y1="330" x2="585" y2="338" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="filter:C" role="button" aria-label="filter knob, deck C" tabindex="0"
     data-cx="695" data-cy="340">
    <circle cx="695" cy="340" r="14" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="695" y1="330" x2="695" y2="338" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="filter:D" role="button" aria-label="filter knob, deck D" tabindex="0"
     data-cx="755" data-cy="340">
    <circle cx="755" cy="340" r="14" stroke="currentColor" stroke-width="1.3" fill="none"/>
    <line x1="755" y1="330" x2="755" y2="338" stroke="currentColor" stroke-width="1.3"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <text x="640" y="362" font-family="'JetBrains Mono', monospace" font-size="8"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor" opacity="0.55">FILTER</text>

  <!-- Channel faders A B C D -->
  <g data-control-id="vol:A" role="button" aria-label="channel fader, deck A" tabindex="0"
     data-cx="525" data-cy="490">
    <rect x="519" y="385" width="12" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="513" y="475" width="24" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="vol:B" role="button" aria-label="channel fader, deck B" tabindex="0"
     data-cx="585" data-cy="490">
    <rect x="579" y="385" width="12" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="573" y="475" width="24" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="vol:C" role="button" aria-label="channel fader, deck C" tabindex="0"
     data-cx="695" data-cy="490">
    <rect x="689" y="385" width="12" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="683" y="475" width="24" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
  <g data-control-id="vol:D" role="button" aria-label="channel fader, deck D" tabindex="0"
     data-cx="755" data-cy="490">
    <rect x="749" y="385" width="12" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <rect x="743" y="475" width="24" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- Crossfader -->
  <g data-control-id="xfader" role="button" aria-label="crossfader" tabindex="0"
     data-cx="640" data-cy="615">
    <rect x="540" y="608" width="200" height="14" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="640" y1="600" x2="640" y2="630" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="632" y="600" width="16" height="30" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK C — CDJ-style jog + transport + tempo                    -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:C" role="button" aria-label="jog wheel, deck C" tabindex="0"
     data-cx="890" data-cy="220">
    <circle cx="890" cy="220" r="80" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="890" cy="220" r="62" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="890" cy="220" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="890" y1="150" x2="890" y2="178" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:C" role="button" aria-label="play button, deck C" tabindex="0"
     data-cx="855" data-cy="345">
    <rect x="830" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="855" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:C" role="button" aria-label="cue button, deck C" tabindex="0"
     data-cx="905" data-cy="345">
    <rect x="880" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="905" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:C" role="button" aria-label="sync button, deck C" tabindex="0"
     data-cx="955" data-cy="345">
    <rect x="930" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="955" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:C" role="button" aria-label="pitch fader, deck C" tabindex="0"
     data-cx="980" data-cy="500">
    <rect x="973" y="400" width="14" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="965" y1="500" x2="995" y2="500" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="967" y="492" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK D                                                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:D" role="button" aria-label="jog wheel, deck D" tabindex="0"
     data-cx="1110" data-cy="220">
    <circle cx="1110" cy="220" r="80" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="1110" cy="220" r="62" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="1110" cy="220" r="32" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="1110" y1="150" x2="1110" y2="178" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:D" role="button" aria-label="play button, deck D" tabindex="0"
     data-cx="1075" data-cy="345">
    <rect x="1050" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1075" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:D" role="button" aria-label="cue button, deck D" tabindex="0"
     data-cx="1125" data-cy="345">
    <rect x="1100" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1125" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:D" role="button" aria-label="sync button, deck D" tabindex="0"
     data-cx="1175" data-cy="345">
    <rect x="1150" y="328" width="50" height="32" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1175" y="348" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:D" role="button" aria-label="pitch fader, deck D" tabindex="0"
     data-cx="1200" data-cy="500">
    <rect x="1193" y="400" width="14" height="200" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="1185" y1="500" x2="1215" y2="500" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="1187" y="492" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
</svg>`;
