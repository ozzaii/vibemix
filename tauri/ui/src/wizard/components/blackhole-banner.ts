/* blackhole-banner.ts — Step 2 macOS-only conditional banner (UI-SPEC §8).
 *
 * Full-width inside primary panel, top-positioned (above audio test).
 * --phosphor-halo border-glow + --phosphor-dim border + linear-gradient
 * --panel-lift→--panel background.
 *
 * Left: 24px BlackHole waveform glyph (inline SVG) in --phosphor.
 * Center: heading "BLACKHOLE NOT FOUND" + body "vibemix needs blackhole
 * to hear your master output. it's free, takes 30 seconds." (VERBATIM
 * from UI-SPEC §Step 2).
 * Right: stacked [ Open install page ↗ ] (primary armed) +
 * [ ↻ Recheck ] (secondary).
 *
 * postClickState true → primary disabled with caption "opened in browser
 * — install then click Recheck below" (DM Mono 11px --ink-dim). */

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
    gap: var(--sp-md);
    padding: var(--sp-md) var(--sp-lg);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--phosphor-dim);
    border-radius: 6px;
    box-shadow: var(--phosphor-halo);
    margin-bottom: var(--sp-md);
  }
  .cmp-bh-banner__glyph {
    color: var(--phosphor);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cmp-bh-banner__text {
    display: flex;
    flex-direction: column;
    gap: var(--sp-xs);
  }
  .cmp-bh-banner__heading {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
  }
  .cmp-bh-banner__body {
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink);
    line-height: 1.5;
  }
  .cmp-bh-banner__caption {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    margin-top: var(--sp-xs);
  }
  .cmp-bh-banner__actions {
    display: flex;
    flex-direction: column;
    gap: var(--sp-sm);
  }
`;

registerStyle("cmp-bh-banner", CSS);

export function BlackHoleBanner(props: BlackHoleBannerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-bh-banner";
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
