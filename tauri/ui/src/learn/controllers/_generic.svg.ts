// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — Generic controller fallback (labeled-zone schematic).
//
// Renders when `find_mapping(port_name)` returns no match — the user
// plugged in a controller vibemix doesn't recognise yet. INSTEAD OF
// pretending to know the hardware, we show three dashed rectangles
// labelled DECK A / MIXER / DECK B so the user can still orient.
// Honest design: don't fake-realistic an unknown surface.
//
// No `<g data-control-id>` here — there are no profile bindings to mirror
// (the SVG↔profile parity gate in `test_svg_profile_parity.spec.ts`
// special-cases the `_generic` row).
//
// Aesthetic: CDJ-Whisper. Silk-22 dashed strokes + JetBrains Mono labels
// (centered in each rectangle). No Pioneer logo, no brand-orange, no
// photo-lift. Geometry viewBox-normalised to 1280×720 matching the
// other 10 SVGs.

export const GENERIC_CONTROLLER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" class="learn-controller-schematic">
  <!-- Faceplate outline (decorative, dashed — "we don't know which model this is") -->
  <rect x="60" y="60" width="1160" height="600" rx="16" ry="16"
        stroke="currentColor" stroke-width="1.5" stroke-dasharray="8 6"
        fill="none" opacity="0.55"/>

  <!-- DECK A zone — left third -->
  <rect x="120" y="160" width="320" height="400" rx="12" ry="12"
        stroke="currentColor" stroke-width="1.5" stroke-dasharray="8 6"
        fill="none" opacity="0.55"/>
  <text x="280" y="368" font-family="'JetBrains Mono', monospace" font-size="32"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor"
        opacity="0.72">DECK A</text>

  <!-- MIXER zone — center -->
  <rect x="480" y="160" width="320" height="400" rx="12" ry="12"
        stroke="currentColor" stroke-width="1.5" stroke-dasharray="8 6"
        fill="none" opacity="0.55"/>
  <text x="640" y="368" font-family="'JetBrains Mono', monospace" font-size="32"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor"
        opacity="0.72">MIXER</text>

  <!-- DECK B zone — right third -->
  <rect x="840" y="160" width="320" height="400" rx="12" ry="12"
        stroke="currentColor" stroke-width="1.5" stroke-dasharray="8 6"
        fill="none" opacity="0.55"/>
  <text x="1000" y="368" font-family="'JetBrains Mono', monospace" font-size="32"
        letter-spacing="0.18em" text-anchor="middle" fill="currentColor"
        opacity="0.72">DECK B</text>
</svg>`;
