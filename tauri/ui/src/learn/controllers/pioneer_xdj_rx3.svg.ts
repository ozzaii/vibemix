// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 06 — XDJ-RX3 inline-SVG controller schematic.
//
// Provenance: Hand-authored from the XDJ-RX3 "Operating Instructions"
// appendix hardware-diagram (publisher: AlphaTheta Corp., ©2022 revision;
// Apache-clean derivative geometry — factual control layout only, NO
// vendor logo, NO faceplate photo-lift, NO brand-orange). The XDJ-RX3
// is the standalone-or-rekordbox all-in-one with an onboard screen +
// 2 physical CDJ-style deck strips that can address 4 software decks
// via deck-select toggle; profile declares 4 deck channels. The
// onboard screen surface is NOT rendered (only physical controls per
// UI-SPEC §Copywriting Contract — vibemix mirrors hardware, not
// software displays). Master FX section adds tap_tempo + filter_fx
// engage buttons (no hotcue bindings).
//
// CDJ-Whisper aesthetic: silk-22 strokes on warm-black void,
// currentColor throughout.
//
// Parity contract (RENDER-06): every data-control-id resolves to a
// binding in src/vibemix/midi/profiles/pioneer_xdj_rx3.json, and
// every profile binding resolves to a group here. The 43-entry set is:
//   - controls: vol/eq_hi/eq_mid/eq_low/tempo/filter per A,B,C,D
//                + xfader  (21 controls)
//   - buttons: play/cue/sync/jog_touch per A,B,C,D + tap_tempo
//                + filter_fx  (18 buttons)

export const PIONEER_XDJ_RX3_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" role="img" aria-label="Pioneer XDJ-RX3 schematic" class="learn-controller-schematic">
  <!-- Faceplate outline -->
  <rect x="40" y="60" width="1200" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.55"/>
  <rect x="60" y="80" width="1160" height="560" rx="10" ry="10"
        stroke="currentColor" stroke-width="1" fill="none" opacity="0.32"/>

  <!-- 4-deck column separators (silk hairlines marking deck A | B | mixer | C | D) -->
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
  <!-- DECK A — jog wheel + transport + tempo                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:A" role="button" aria-label="jog wheel, deck A" tabindex="0"
     data-cx="170" data-cy="240">
    <circle cx="170" cy="240" r="75" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="170" cy="240" r="58" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="170" cy="240" r="30" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="170" y1="175" x2="170" y2="200" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:A" role="button" aria-label="play button, deck A" tabindex="0"
     data-cx="130" data-cy="400">
    <rect x="105" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="130" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:A" role="button" aria-label="cue button, deck A" tabindex="0"
     data-cx="180" data-cy="400">
    <rect x="155" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="180" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:A" role="button" aria-label="sync button, deck A" tabindex="0"
     data-cx="230" data-cy="400">
    <rect x="205" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="230" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:A" role="button" aria-label="pitch fader, deck A" tabindex="0"
     data-cx="260" data-cy="540">
    <rect x="253" y="448" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="245" y1="540" x2="275" y2="540" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="247" y="532" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK B — jog wheel + transport + tempo                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:B" role="button" aria-label="jog wheel, deck B" tabindex="0"
     data-cx="390" data-cy="240">
    <circle cx="390" cy="240" r="75" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="390" cy="240" r="58" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="390" cy="240" r="30" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="390" y1="175" x2="390" y2="200" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:B" role="button" aria-label="play button, deck B" tabindex="0"
     data-cx="350" data-cy="400">
    <rect x="325" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="350" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:B" role="button" aria-label="cue button, deck B" tabindex="0"
     data-cx="400" data-cy="400">
    <rect x="375" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="400" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:B" role="button" aria-label="sync button, deck B" tabindex="0"
     data-cx="450" data-cy="400">
    <rect x="425" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="450" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:B" role="button" aria-label="pitch fader, deck B" tabindex="0"
     data-cx="480" data-cy="540">
    <rect x="473" y="448" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="465" y1="540" x2="495" y2="540" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="467" y="532" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- MIXER — 4-channel EQ stacks + faders + crossfader + master FX -->
  <!-- ============================================================= -->

  <!-- EQ HI: A B C D (4 columns, x=520/580/700/760) -->
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

  <!-- EQ MID -->
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

  <!-- EQ LOW -->
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

  <!-- Master FX strip: tap_tempo + filter_fx engage (XDJ-RX3 Beat FX section) -->
  <g data-control-id="tap_tempo" role="button" aria-label="tap tempo button" tabindex="0"
     data-cx="610" data-cy="395">
    <rect x="585" y="378" width="50" height="34" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="610" y="400" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">TAP</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="filter_fx" role="button" aria-label="master filter FX" tabindex="0"
     data-cx="675" data-cy="395">
    <rect x="645" y="378" width="60" height="34" rx="4" ry="4"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="675" y="400" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">FILTER FX</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK C — jog wheel + transport + tempo                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:C" role="button" aria-label="jog wheel, deck C" tabindex="0"
     data-cx="890" data-cy="240">
    <circle cx="890" cy="240" r="75" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="890" cy="240" r="58" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="890" cy="240" r="30" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="890" y1="175" x2="890" y2="200" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:C" role="button" aria-label="play button, deck C" tabindex="0"
     data-cx="850" data-cy="400">
    <rect x="825" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="850" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:C" role="button" aria-label="cue button, deck C" tabindex="0"
     data-cx="900" data-cy="400">
    <rect x="875" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="900" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:C" role="button" aria-label="sync button, deck C" tabindex="0"
     data-cx="950" data-cy="400">
    <rect x="925" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="950" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:C" role="button" aria-label="pitch fader, deck C" tabindex="0"
     data-cx="980" data-cy="540">
    <rect x="973" y="448" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="965" y1="540" x2="995" y2="540" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="967" y="532" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <!-- ============================================================= -->
  <!-- DECK D — jog wheel + transport + tempo                        -->
  <!-- ============================================================= -->

  <g data-control-id="jog_touch:D" role="button" aria-label="jog wheel, deck D" tabindex="0"
     data-cx="1110" data-cy="240">
    <circle cx="1110" cy="240" r="75" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <circle cx="1110" cy="240" r="58" stroke="currentColor" stroke-width="1" fill="none" opacity="0.5"/>
    <circle cx="1110" cy="240" r="30" stroke="currentColor" stroke-width="1" fill="none" opacity="0.35"/>
    <line x1="1110" y1="175" x2="1110" y2="200" stroke="currentColor" stroke-width="1.5"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="play:D" role="button" aria-label="play button, deck D" tabindex="0"
     data-cx="1070" data-cy="400">
    <rect x="1045" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1070" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">PLAY</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="cue:D" role="button" aria-label="cue button, deck D" tabindex="0"
     data-cx="1120" data-cy="400">
    <rect x="1095" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1120" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">CUE</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="sync:D" role="button" aria-label="sync button, deck D" tabindex="0"
     data-cx="1170" data-cy="400">
    <rect x="1145" y="382" width="50" height="34" rx="3" ry="3"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
    <text x="1170" y="404" font-family="'JetBrains Mono', monospace" font-size="8"
          letter-spacing="0.16em" text-anchor="middle" fill="currentColor" opacity="0.62">SYNC</text>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>

  <g data-control-id="tempo:D" role="button" aria-label="pitch fader, deck D" tabindex="0"
     data-cx="1200" data-cy="540">
    <rect x="1193" y="448" width="14" height="180" rx="3" ry="3"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <line x1="1185" y1="540" x2="1215" y2="540" stroke="currentColor" stroke-width="1" opacity="0.4"/>
    <rect x="1187" y="532" width="26" height="16" rx="2" ry="2"
          stroke="currentColor" stroke-width="1" fill="none"/>
    <g class="cue-color"></g>
    <g class="cue-shape"></g>
  </g>
</svg>`;
