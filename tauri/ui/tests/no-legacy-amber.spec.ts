/**
 * App-wide closure of the v5 -> tozpembe accent migration. The old primary
 * accent (#ff8a3d amber, the v5 "deck-light") is dead: the whole app is rose
 * (--brand #FFA5DF). The migration alias (--amber -> var(--brand)) retones every
 * TOKEN reference for free, but raw `rgba(255, 138, 61, ...)` / `#ff8a3d`
 * literals bypass the token and render AMBER on a rose app.
 *
 * The surface-specific guards (wizard, debrief) caught their corners; this one
 * bans the legacy amber in EVERY source file (.ts + .css) so no surface can
 * drift back. If you genuinely need to NAME the old color in a comment, write
 * "the retired v5 amber" — never the literal, so this gate stays honest.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "src");

// The v5 amber, in the forms it shows up as raw literals (rgba triple + hex).
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

describe("app cohesion — no legacy v5 amber anywhere", () => {
  it("declares NO raw amber literal in any source file (.ts or .css)", () => {
    const offenders: string[] = [];
    for (const file of walk(SRC)) {
      const text = readFileSync(file, "utf-8");
      text.split("\n").forEach((line, i) => {
        if (LEGACY_AMBER.some((re) => re.test(line))) {
          offenders.push(`${file.replace(SRC, "src")}:${i + 1}: ${line.trim().slice(0, 80)}`);
        }
      });
    }
    expect(
      offenders,
      `Raw v5 amber found — retone to rose (rgba(255, 165, 223, …) / var(--brand*)):\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
