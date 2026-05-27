// SPDX-License-Identifier: Apache-2.0
// REQ-ID: N/A — currentColor discipline. Every `fill="..."` / `stroke="..."`
//               value in any learn SVG body MUST be one of the allow-list:
//               `currentColor`, `none`, `var(--silk-22)`, `var(--silk)`, or
//               `var(--learn-highlight)`. Hex literals (`#xxx` / `#xxxxxx`)
//               and `rgb(...)` literals are forbidden — they bypass the
//               token palette and break theme switching.
//
// Phase 91 Plan 02 — GREEN day-one because `tauri/ui/src/learn/` does not
// yet contain any `.svg.ts` files. The moment any file appears, every
// fill/stroke attribute value is scanned; the first hex literal outside
// the allow-list fails the gate red. Sibling:
// `test_no_pioneer_orange.spec.ts` covers the brand-specific orange band.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LEARN_SRC = path.join(REPO_ROOT, "tauri/ui/src/learn");

const ALLOWED = new Set<string>([
  "currentcolor",
  "none",
  "var(--silk-22)",
  "var(--silk)",
  "var(--learn-highlight)",
]);

// Match `fill="…"` and `stroke="…"` attribute values. The regex captures
// only the QUOTED value so the allow-list comparison is exact.
const ATTR_RE = /\b(fill|stroke)\s*=\s*"([^"]*)"/gi;

function walkSvgFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkSvgFiles(full));
    else if (entry.isFile() && entry.name.endsWith(".svg.ts")) out.push(full);
  }
  return out;
}

describe("test_svg_currentcolor_only.spec.ts (currentColor discipline)", () => {
  it("every fill/stroke attribute value in learn/*.svg.ts is allow-listed", () => {
    const offenders: string[] = [];
    for (const file of walkSvgFiles(LEARN_SRC)) {
      const source = fs.readFileSync(file, "utf8");
      let match: RegExpExecArray | null;
      while ((match = ATTR_RE.exec(source)) !== null) {
        const attr = match[1] ?? "";
        const value = (match[2] ?? "").trim().toLowerCase();
        if (!ALLOWED.has(value)) {
          offenders.push(`${file}: ${attr}="${match[2]}"`);
        }
      }
    }
    expect(
      offenders,
      `currentColor discipline violated — hex literals outside the allow-list:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
