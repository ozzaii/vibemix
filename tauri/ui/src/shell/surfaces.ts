// SPDX-License-Identifier: Apache-2.0
//
// The surface registry: the five opaque surfaces that fold into the cohesive
// shell as keep-alive routes (the floating pill, the click-through overlay, and
// the mascot stay separate transparent windows, so they are NOT here). One word
// per surface, used as both the nav label and the route id, avoiding Bravoh's
// route-vs-label split (see docs/design/vibemix-translation-layer.md).
//
// This module is pure data. DesktopShell renders the placeholder regions and
// owns the keep-alive mounting; each surface carries a `wire` anchor so the real
// surface (session/library/learn/debrief/settings) wires in during a later
// phase without moving the structure.

import {
  GLYPH_VIBER,
  GLYPH_DEBRIEF,
  GLYPH_DECK,
  GLYPH_LEARN,
  GLYPH_SETTINGS,
} from "./glyphs.js";
import type { SurfaceId } from "./shell-store.js";

/**
 * The at-rest copy for a surface before its real interior wires in. Written in
 * the co-host's voice (first person, short, specific, grounded) so an unfilled
 * surface reads like a powered deck waiting for input, not an unfinished stub.
 * Deck owns its own idle/live hero, so it carries no empty state here.
 */
export interface SurfaceEmptyState {
  /** One serif line, the state of the surface (e.g. "Nothing loaded yet."). */
  readonly title: string;
  /** One grounded co-host line on what unlocks it. No marketing, no slop. */
  readonly sub: string;
  /** Optional compact proof rows for surfaces whose value is invisible at rest. */
  readonly proof?: readonly SurfaceEmptyProofRow[];
}

export interface SurfaceEmptyProofRow {
  readonly label: string;
  readonly value: string;
}

export interface SurfaceDef {
  readonly id: SurfaceId;
  /** Single word, used as both the nav label and the route name. */
  readonly label: string;
  /** Command-palette / Cmd+<kbd> accelerator. */
  readonly kbd: string;
  /** Bespoke engraved mark — an inline-SVG string from ./glyphs (no icon
   * library; one matched hardware-feel set per DESIGN.md). */
  readonly glyph: string;
  /** One-line description shown in the palette and collapsed-rail tooltip. */
  readonly hint: string;
  /** data-wire anchor where the real surface mounts in a later phase. */
  readonly wire: string;
  /** At-rest empty state. Absent on the deck (it owns its idle/live hero). */
  readonly empty?: SurfaceEmptyState;
}

export const SURFACES: readonly SurfaceDef[] = [
  { id: "deck", label: "Deck", kbd: "1", glyph: GLYPH_DECK, hint: "the live co-host", wire: "shell.surface.deck" },
  {
    id: "viber",
    label: "Viber",
    kbd: "2",
    glyph: GLYPH_VIBER,
    hint: "library and set prep",
    wire: "shell.surface.viber",
    empty: {
      title: "Viber is ready for your library.",
      sub: "Add a music folder or bring in a DJ library. I can build sets and solve transitions.",
      proof: [
        { label: "Build", value: "set arcs from indexed tracks" },
        { label: "Mix", value: "deck-backed transitions only" },
        { label: "Find", value: "deep cuts without repeats" },
      ],
    },
  },
  {
    id: "learn",
    label: "Learn",
    kbd: "3",
    glyph: GLYPH_LEARN,
    hint: "lessons",
    wire: "shell.surface.learn",
    empty: {
      title: "No lesson running.",
      sub: "Pick a course. I'm watching your hands on the controller, beat for beat.",
    },
  },
  {
    id: "debrief",
    label: "Debrief",
    kbd: "4",
    glyph: GLYPH_DEBRIEF,
    hint: "post-set debrief",
    wire: "shell.surface.debrief",
    empty: {
      title: "Your set debrief lands here.",
      sub: "After a real set, I turn key moments into a timeline, skill notes, and the next move.",
      proof: [
        { label: "Timeline", value: "drops, recoveries, energy shape" },
        { label: "Why", value: "what made a praise or critique real" },
        { label: "Next move", value: "practice drill or Viber follow-up" },
      ],
    },
  },
  {
    id: "settings",
    label: "Settings",
    kbd: "5",
    glyph: GLYPH_SETTINGS,
    hint: "setup and tuning",
    wire: "shell.surface.settings",
    // State-neutral: wireSettingsNav routes every settings navigation to the
    // drawer, so this fallback rarely paints — and when it does it must never
    // lie ("Not set up yet." was unconditional regardless of actual setup).
    empty: {
      title: "Settings live in the drawer.",
      sub: "Audio routing, voice, and persona. Change what I listen to and how I sound.",
    },
  },
];

export function surfaceById(id: SurfaceId): SurfaceDef | undefined {
  return SURFACES.find((surface) => surface.id === id);
}
