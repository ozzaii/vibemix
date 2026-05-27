// SPDX-License-Identifier: Apache-2.0
// REQ-ID: N/A — Brand safety / Apache-clean. The CDJ-Whisper accent is
//               `var(--cdj-amber-2)`; Pioneer brand-orange is `#FF7F00` and
//               ±10° hue neighbours. This grep gate fails red on any
//               literal `#FF7F00` / `#ff7f00`, RGB equivalent, or
//               near-neighbour hex literal in any `tauri/ui/src/learn/`
//               `.svg.ts` file.
//
// Phase 91 Plan 02 — GREEN day-one because `tauri/ui/src/learn/` does not
// yet contain any `.svg.ts` files (Plans 05+06 land them). The moment any
// file appears under that path, every body is scanned; the first hit fails
// the gate red. Sibling: `tests/learn/test_no_pioneer_brand_marks.py` for
// the wordmark side.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LEARN_SRC = path.join(REPO_ROOT, "tauri/ui/src/learn");

// Pioneer brand-orange + ±10° hue neighbours. Each is hex literal (case-
// insensitive) plus the canonical RGB form. The neighbour set was lifted
// from PITFALLS §P4 — same range the Pioneer style-guide reserves.
const FORBIDDEN_RE = new RegExp(
  [
    "#ff7f00", "#ff8000", "#ff7e00", "#ff7d00", "#ff8100", "#ff8200",
    "#ff7c00", "#ff7b00", "#ff8300", "#ff8400", "#ff7a00", "#ff8500",
    "rgb\\s*\\(\\s*255\\s*,\\s*127\\s*,\\s*0\\s*\\)",
  ].join("|"),
  "i",
);

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

describe("test_no_pioneer_orange.spec.ts (Brand safety)", () => {
  it("no Pioneer brand-orange or ±10° hue neighbour in learn/*.svg.ts", () => {
    const offenders: string[] = [];
    for (const file of walkSvgFiles(LEARN_SRC)) {
      const lines = fs.readFileSync(file, "utf8").split("\n");
      lines.forEach((line, idx) => {
        if (FORBIDDEN_RE.test(line)) {
          offenders.push(`${file}:${idx + 1}: ${line.trim()}`);
        }
      });
    }
    expect(
      offenders,
      `Pitfall 4 — Pioneer brand-orange leak:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
