/**
 * Debrief is the post-set review surface — the same tozpembe cohesion bar as
 * the rest of the app. tozpembe replaced the v5 primary accent (#ff8a3d amber)
 * with rose (--brand #FFA5DF). The migration alias (--amber -> var(--brand))
 * retones every TOKEN reference for free, but raw `rgba(255, 138, 61, ...)`
 * literals in debrief.css bypass the token and render AMBER on a rose app. This
 * gate bans them so the debrief surface stays on-palette. Mirrors
 * tests/wizard/no-legacy-amber.spec.ts, but also walks .css (the leak lived in
 * the stylesheet, not the .ts).
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const DEBRIEF = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "src", "debrief");

// The v5 amber, in the forms it shows up as raw literals.
const LEGACY_AMBER = [/255,\s*138,\s*61/i, /#ff8a3d/i];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if ([".ts", ".css"].includes(extname(p)) && !/\.(spec|test)\.ts$/.test(name)) out.push(p);
  }
  return out;
}

describe("debrief cohesion — no legacy v5 amber", () => {
  it("declares NO raw #ff8a3d amber literal anywhere in the debrief surface", () => {
    const offenders: string[] = [];
    for (const file of walk(DEBRIEF)) {
      const text = readFileSync(file, "utf-8");
      text.split("\n").forEach((line, i) => {
        if (LEGACY_AMBER.some((re) => re.test(line))) {
          offenders.push(`${file.replace(DEBRIEF, "src/debrief")}:${i + 1}: ${line.trim().slice(0, 80)}`);
        }
      });
    }
    expect(
      offenders,
      `Raw v5 amber found — retone to rose (rgba(255, 165, 223, …) / var(--brand*)):\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
