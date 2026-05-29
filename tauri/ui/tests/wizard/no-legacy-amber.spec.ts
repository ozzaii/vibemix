/**
 * The wizard is the first screen a new user sees, so its cohesion sets the
 * whole first impression. tozpembe replaced the v5 primary accent (#ff8a3d
 * amber, the old deck-light) with rose (--brand #FFA5DF). The migration alias
 * (--amber -> var(--brand)) retones every TOKEN reference for free, but raw
 * `rgba(255, 138, 61, ...)` literals bypass the token and render AMBER on a
 * rose app. wizard.tokens.test.ts only catches legacy token NAMES, not raw
 * rgba, so those literals slipped through. This gate bans them so the first
 * impression can't drift back to amber.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const WIZARD = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "src", "wizard");

// The v5 amber, in the forms it shows up as raw literals.
const LEGACY_AMBER = [/255,\s*138,\s*61/i, /#ff8a3d/i];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (extname(p) === ".ts" && !/\.(spec|test)\.ts$/.test(name)) out.push(p);
  }
  return out;
}

describe("wizard cohesion — no legacy v5 amber", () => {
  it("declares NO raw #ff8a3d amber literal anywhere in the wizard surface", () => {
    const offenders: string[] = [];
    for (const file of walk(WIZARD)) {
      const text = readFileSync(file, "utf-8");
      text.split("\n").forEach((line, i) => {
        if (LEGACY_AMBER.some((re) => re.test(line))) {
          offenders.push(`${file.replace(WIZARD, "src/wizard")}:${i + 1}: ${line.trim().slice(0, 80)}`);
        }
      });
    }
    expect(
      offenders,
      `Raw v5 amber found — retone to rose (rgba(255, 165, 223, …) / var(--brand*)):\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
