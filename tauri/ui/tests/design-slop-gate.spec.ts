/* v8.0 P75 (DESIGN-01..04) — the design level-up loop, made permanent.
 *
 * The CDJ-Whisper aesthetic passed paired UI audits across v3.0 (VIS-01) and
 * v7.0 (UI-review 23/24). This gate LOCKS the most load-bearing brand promise
 * — "never sounding like AI slop" (PROJECT.md core value) — so a future edit
 * can't silently regress it. Per the frontend-enforcement skill, generic
 * platform fonts are the #1 AI-slop tell. This is the "review→fix→re-review"
 * loop turned into a standing check that runs every CI: the loop never stops.
 *
 * Scope: every shipped stylesheet + component source under tauri/ui/src.
 * (Throwaway design mocks under mocks/ are intentionally NOT gated.)
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "src");

// The canonical brand fonts (tokens.css @font-face + the --type-* tokens).
const ALLOWED_FONTS = ["Saira", "JetBrains Mono"];
// Generic / platform fonts that signal AI slop if used as a brand face.
// (system-ui / ui-monospace / sans-serif / monospace are allowed ONLY as the
// trailing fallback in a stack that starts with a brand font — see the
// font-family stack check below.)
const BANNED_FONTS = [
  "Inter",
  "Roboto",
  "Arial",
  "Helvetica",
  "Courier",
  "Times New Roman",
  "Times",
  "Verdana",
  "Tahoma",
  "Segoe",
  "Open Sans",
  "Lato",
];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      out.push(...walk(p));
    } else if (
      [".ts", ".css"].includes(extname(p)) &&
      // Gate SHIPPED source only — co-located *.spec.ts / *.test.ts files
      // legitimately mention fonts inside regex assertions/comments.
      !/\.(spec|test)\.ts$/.test(name)
    ) {
      out.push(p);
    }
  }
  return out;
}

const FILES = walk(SRC);
// All `font-family: ...;` declarations across the source, with their file.
const FONT_DECLS: { file: string; decl: string }[] = [];
for (const f of FILES) {
  const text = readFileSync(f, "utf-8");
  for (const m of text.matchAll(/font-family:\s*([^;}\n]+)/gi)) {
    FONT_DECLS.push({ file: f.replace(SRC, "src"), decl: m[1].trim() });
  }
}

describe("design-slop gate — no AI-slop fonts", () => {
  it("finds font-family declarations to check (sanity)", () => {
    expect(FONT_DECLS.length).toBeGreaterThan(0);
  });

  it("declares NO banned/generic brand font anywhere in src", () => {
    const offenders = FONT_DECLS.filter(({ decl }) =>
      BANNED_FONTS.some((b) => new RegExp(`\\b${b}\\b`, "i").test(decl)),
    );
    expect(
      offenders,
      `AI-slop fonts found — use Saira / JetBrains Mono via var(--type-*):\n${offenders
        .map((o) => `  ${o.file}: font-family: ${o.decl}`)
        .join("\n")}`,
    ).toEqual([]);
  });

  it("every font-family stack starts with a brand font or a --type-* token", () => {
    const offenders = FONT_DECLS.filter(({ decl }) => {
      const first = decl.replace(/['"]/g, "").split(",")[0].trim();
      const isToken = first.startsWith("var(--type-");
      const isBrand = ALLOWED_FONTS.some((a) => first.toLowerCase() === a.toLowerCase());
      // `inherit` / `unset` / empty are neutral (don't impose a face).
      const isNeutral = ["inherit", "unset", "initial", ""].includes(first.toLowerCase());
      return !(isToken || isBrand || isNeutral);
    });
    expect(
      offenders,
      `font stacks must LEAD with Saira / JetBrains Mono or a --type-* token (system-ui only as trailing fallback):\n${offenders
        .map((o) => `  ${o.file}: font-family: ${o.decl}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});

describe("design-slop gate — @font-face brand lock", () => {
  it("declares ONLY Saira + JetBrains Mono as @font-face families", () => {
    const tokens = readFileSync(join(SRC, "tokens.css"), "utf-8");
    const faces = [...tokens.matchAll(/@font-face\s*\{[^}]*?font-family:\s*['"]([^'"]+)['"]/gis)].map(
      (m) => m[1],
    );
    expect(faces.length).toBeGreaterThan(0);
    for (const fam of faces) {
      expect(ALLOWED_FONTS).toContain(fam);
    }
  });
});
