/* blackhole-banner.ts — Step 2 macOS-only conditional banner (UI-SPEC §8 / CDJ Whisper v5).
 *
 * Glass shell from `.vmx-tile .vmx-tile--banner` (tokens.css) — supplies
 * the amber border + amber-22 inset glow + outer glow-soft. This
 * component owns only the 3-column grid + the heading/body/caption
 * type styles + the actions column. Critique 2026-05-14: dropped the
 * duplicate shadow stack.
 *
 * Left: 24px BlackHole waveform glyph (inline SVG) in --amber.
 * Center: heading "BLACKHOLE NOT FOUND" + body "vibemix needs blackhole
 * to hear your master output. it's free, takes 30 seconds." (VERBATIM
 * from UI-SPEC §Step 2).
 * Right: stacked [ Open install page ↗ ] (primary armed) +
 * [ ↻ Recheck ] (secondary).
 *
 * postClickState true → primary disabled with caption "opened in browser
 * — install then click Recheck below" (Saira body 11px --silk-65). */

import { registerStyle } from "./_style-registry.js";
import { BLACKHOLE_SVG } from "../icons/speaker.svg.js";
import { Button } from "./button.js";

export interface BlackHoleBannerProps {
  onOpenInstall: () => void;
  onRecheck: () => void;
  postClickState?: boolean;
}

const CSS = `
  .cmp-bh-banner {
    display: grid;
    grid-template-columns: 24px 1fr auto;
    align-items: center;
    gap: var(--sp-4);
    padding: var(--sp-4) var(--sp-5);
    margin-bottom: var(--sp-4);
  }
  .cmp-bh-banner__glyph {
    color: var(--amber);
    display: flex;
    align-items: center;
    justify-content: center;
    filter: drop-shadow(0 0 3px var(--amber-22));
  }
  .cmp-bh-banner__text {
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
  }
  .cmp-bh-banner__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--amber);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7), 0 0 6px var(--amber-40);
  }
  .cmp-bh-banner__body {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk);
    line-height: 1.5;
  }
  .cmp-bh-banner__caption {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 11px;
    color: var(--silk-65);
    margin-top: var(--sp-1);
  }
  .cmp-bh-banner__actions {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
`;

registerStyle("cmp-bh-banner", CSS);

export function BlackHoleBanner(props: BlackHoleBannerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-bh-banner vmx-tile";
  root.dataset.tile = "alert";
  root.setAttribute("role", "alert");

  const glyph = document.createElement("div");
  glyph.className = "cmp-bh-banner__glyph";
  glyph.innerHTML = BLACKHOLE_SVG;

  const text = document.createElement("div");
  text.className = "cmp-bh-banner__text";
  const heading = document.createElement("div");
  heading.className = "cmp-bh-banner__heading";
  // UI-SPEC §Step 2 "BlackHole banner heading" — VERBATIM
  heading.textContent = "BLACKHOLE NOT FOUND";
  const body = document.createElement("div");
  body.className = "cmp-bh-banner__body";
  // UI-SPEC §Step 2 "BlackHole banner body" — VERBATIM
  body.textContent = "vibemix needs blackhole to hear your master output. it's free, takes 30 seconds.";
  text.append(heading, body);

  if (props.postClickState) {
    const caption = document.createElement("div");
    caption.className = "cmp-bh-banner__caption";
    // UI-SPEC §Step 2 "BlackHole post-click caption" — VERBATIM
    caption.textContent = "opened in browser — install then click Recheck below";
    text.append(caption);
  }

  const actions = document.createElement("div");
  actions.className = "cmp-bh-banner__actions";
  actions.append(
    Button({
      variant: "primary",
      state: props.postClickState ? "disabled" : "armed",
      // UI-SPEC §Step 2 "BlackHole install button" — VERBATIM
      label: "Open install page ↗",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onOpenInstall,
    }),
    Button({
      variant: "secondary",
      state: "idle",
      // UI-SPEC §Step 2 "BlackHole recheck button" — VERBATIM
      label: "↻ Recheck",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onRecheck,
    })
  );

  root.append(glyph, text, actions);
  return root;
}
