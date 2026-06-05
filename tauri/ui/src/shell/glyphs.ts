// SPDX-License-Identifier: Apache-2.0
//
// The five bespoke nav marks — drawn FOR vibemix, not pulled from an icon
// library (DESIGN.md: hardware-feel engraved marks, no icon dependency). The
// unicode geometric glyphs they replace (◉ ▤ ◈ ◵ ⬡) fell back to whatever
// system symbol font the OS picked per codepoint, so the set rendered at wildly
// different optical weights (a heavy filled disc next to a hairline hexagon).
//
// These are one matched set instead: ONE 24x24 grid, ONE stroke weight, round
// caps/joins, and `currentColor` — so they read as a single engraved family AND
// inherit the nav's rose-on-active / warm-on-hover coloring for free. Sized in
// `em`, so the same string is crisp in the 14px rail, the 42px empty-state
// header, and the palette row. Only the deck mark carries a fill (its lit live
// pip — the co-host signal); the other four are pure line.

/** Wrap inner geometry in the shared <svg> shell so every mark is identical. */
function mark(inner: string): string {
  return (
    '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    inner +
    "</svg>"
  );
}

// deck — the live co-host as a listening eye; the one mark with a lit center
// pip (rose when active), echoing the brand ear's signal-dot language.
export const GLYPH_DECK = mark(
  '<circle cx="12" cy="12" r="8.25"/>' +
    '<circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/>',
);

// Viber — records filed in a box (the library + set-prep surface).
export const GLYPH_VIBER = mark(
  '<rect x="3.5" y="6" width="17" height="12" rx="1.6"/>' +
    '<path d="M8 9.5v5M12 9.5v5M16 9.5v5"/>',
);

// learn — a faceted skill node (the v11 "Earned" skill-tree), nested diamonds.
export const GLYPH_LEARN = mark(
  '<path d="M12 3.5 19.5 12 12 20.5 4.5 12Z"/>' + '<path d="M12 8.4 15.6 12 12 15.6 8.4 12Z"/>',
);

// debrief — the set's energy reviewed: where it dipped, where it landed.
export const GLYPH_DEBRIEF = mark('<path d="M3.5 16.5 8 11 12 14 16 7 20.5 10.5"/>');

// settings — mixer sliders: tuning what I listen to and how I sound.
export const GLYPH_SETTINGS = mark(
  '<path d="M3.5 8h17M3.5 12h17M3.5 16h17"/>' +
    '<path d="M9 6.2v3.6M15 10.2v3.6M11 14.2v3.6"/>',
);
