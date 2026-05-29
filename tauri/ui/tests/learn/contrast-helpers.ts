// SPDX-License-Identifier: Apache-2.0

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export interface Rgba {
  r: number;
  g: number;
  b: number;
  a: number;
}

const TOKENS_CSS = readFileSync(resolve(process.cwd(), "src/tokens.css"), "utf8");

export function readLearnCss(): string {
  return readFileSync(resolve(process.cwd(), "src/learn/styles/learn.css"), "utf8");
}

export function tokenColor(name: string, css: string = TOKENS_CSS): Rgba {
  const value = findTokenValue(name, css);
  if (value === null) {
    throw new Error(`Missing CSS token --${name}`);
  }
  return parseColor(value, css);
}

/** Regex-free `--name: value;` lookup (avoids dynamic RegExp / ReDoS). Returns
 *  the declared value with whitespace trimmed, honoring token-name boundaries
 *  so `--silk` does not match `--silk-65`. */
function findTokenValue(name: string, css: string): string | null {
  const needle = `--${name}`;
  for (let idx = css.indexOf(needle); idx !== -1; idx = css.indexOf(needle, idx + needle.length)) {
    const before = idx === 0 ? "" : css[idx - 1]!;
    if (before === "-" || before === "_" || /[a-zA-Z0-9]/.test(before)) continue;
    let i = idx + needle.length;
    while (i < css.length && (css[i] === " " || css[i] === "\t")) i += 1;
    if (css[i] !== ":") continue;
    const end = css.indexOf(";", i);
    return css.slice(i + 1, end === -1 ? css.length : end).trim();
  }
  return null;
}

export function contrastTokens(foregroundName: string, backgroundName = "void"): number {
  const voidBase = tokenColor("void");
  const background = composite(tokenColor(backgroundName), voidBase);
  const foreground = composite(tokenColor(foregroundName), background);
  return contrastRatio(foreground, background);
}

export function contrastRatio(foreground: Rgba, background: Rgba): number {
  const l1 = relativeLuminance(foreground);
  const l2 = relativeLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function parseColor(value: string, css: string = TOKENS_CSS): Rgba {
  // Follow var(--token) indirection the way the CSS cascade would, so legacy
  // alias tokens that point at canonical tokens (e.g. --silk: var(--ink-100))
  // resolve to their leaf color.
  const varRef = value.match(/^var\(\s*--([a-zA-Z0-9-]+)\s*(?:,[^)]*)?\)$/);
  if (varRef) {
    return tokenColor(varRef[1]!, css);
  }

  const hex = value.match(/^#([0-9a-f]{6})$/i);
  if (hex) {
    const n = Number.parseInt(hex[1]!, 16);
    return {
      r: (n >> 16) & 255,
      g: (n >> 8) & 255,
      b: n & 255,
      a: 1,
    };
  }

  const rgb = value.match(/^rgba?\(([^)]+)\)$/i);
  if (rgb) {
    const parts = rgb[1]!.split(",").map((part) => part.trim());
    if (parts.length === 3 || parts.length === 4) {
      return {
        r: Number.parseFloat(parts[0]!),
        g: Number.parseFloat(parts[1]!),
        b: Number.parseFloat(parts[2]!),
        a: parts[3] === undefined ? 1 : Number.parseFloat(parts[3]),
      };
    }
  }

  throw new Error(`Unsupported color syntax: ${value}`);
}

function composite(foreground: Rgba, background: Rgba): Rgba {
  const a = foreground.a + background.a * (1 - foreground.a);
  if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
  return {
    r: (foreground.r * foreground.a + background.r * background.a * (1 - foreground.a)) / a,
    g: (foreground.g * foreground.a + background.g * background.a * (1 - foreground.a)) / a,
    b: (foreground.b * foreground.a + background.b * background.a * (1 - foreground.a)) / a,
    a,
  };
}

function relativeLuminance(color: Rgba): number {
  const r = linear(color.r);
  const g = linear(color.g);
  const b = linear(color.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function linear(channel: number): number {
  const c = channel / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
