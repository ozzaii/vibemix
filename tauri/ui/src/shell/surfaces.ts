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
  GLYPH_CRATE,
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
    id: "crate",
    label: "Crate",
    kbd: "2",
    glyph: GLYPH_CRATE,
    hint: "library and Viber",
    wire: "shell.surface.crate",
    empty: {
      title: "Nothing loaded yet.",
      sub: "Open Rekordbox or drop a folder. I learn your crate by ear, then tell you what's next.",
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
    hint: "post-set review",
    wire: "shell.surface.debrief",
    empty: {
      title: "Your set review lands here.",
      sub: "After a real set, I turn cited moments into a timeline, skill receipts, and the next move.",
      proof: [
        { label: "Timeline", value: "drops, recoveries, energy shape" },
        { label: "Receipts", value: "why a praise or critique was grounded" },
        { label: "Next move", value: "practice drill or crate follow-up" },
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
    empty: {
      title: "Not set up yet.",
      sub: "Audio routing, voice, and persona. Change what I listen to and how I sound.",
    },
  },
];

export function surfaceById(id: SurfaceId): SurfaceDef | undefined {
  return SURFACES.find((surface) => surface.id === id);
}
