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

import { DJ_VOCAB } from "../src/shell/dj-vocab.js";

const SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "src");

// The canonical brand fonts (tokens.css @font-face + the --type-* tokens).
// Phase-1b landed: Geist (body/UI, --type-display/--type-body) + Geist Mono
// (numerics/labels, --type-mono) retired Saira + JetBrains Mono; Instrument
// Serif stays the cohost hero / lead-track-name face. All three are OFL.
const ALLOWED_FONTS = ["Geist", "Geist Mono", "Instrument Serif"];
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

// Word-boundary match without a dynamic `new RegExp(...)`. The font names are
// hardcoded constants (not user input), but a templated RegExp trips static
// ReDoS scanners and a hardcoded boundary check is clearer regardless. Boundary
// = the chars flanking the match are non-alphanumeric, so "Inter" never matches
// inside a longer word.
const WORD_CHAR = /[a-z0-9]/;
function mentionsFont(decl: string, font: string): boolean {
  const haystack = decl.toLowerCase();
  const needle = font.toLowerCase();
  for (let i = haystack.indexOf(needle); i !== -1; i = haystack.indexOf(needle, i + 1)) {
    const before = i === 0 ? "" : haystack[i - 1] ?? "";
    const after = haystack[i + needle.length] ?? "";
    if (!WORD_CHAR.test(before) && !WORD_CHAR.test(after)) return true;
  }
  return false;
}

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
    const decl = m[1];
    if (decl === undefined) continue;
    FONT_DECLS.push({ file: f.replace(SRC, "src"), decl: decl.trim() });
  }
}

describe("design-slop gate — no AI-slop fonts", () => {
  it("finds font-family declarations to check (sanity)", () => {
    expect(FONT_DECLS.length).toBeGreaterThan(0);
  });

  it("declares NO banned/generic brand font anywhere in src", () => {
    const offenders = FONT_DECLS.filter(({ decl }) =>
      BANNED_FONTS.some((b) => mentionsFont(decl, b)),
    );
    expect(
      offenders,
      `AI-slop fonts found — use Geist / Geist Mono via var(--type-*):\n${offenders
        .map((o) => `  ${o.file}: font-family: ${o.decl}`)
        .join("\n")}`,
    ).toEqual([]);
  });

  it("every font-family stack starts with a brand font or a --type-* token", () => {
    const offenders = FONT_DECLS.filter(({ decl }) => {
      const first = (decl.replace(/['"]/g, "").split(",")[0] ?? "").trim();
      const isToken = first.startsWith("var(--type-");
      const isBrand = ALLOWED_FONTS.some((a) => first.toLowerCase() === a.toLowerCase());
      // `inherit` / `unset` / empty are neutral (don't impose a face).
      const isNeutral = ["inherit", "unset", "initial", ""].includes(first.toLowerCase());
      return !(isToken || isBrand || isNeutral);
    });
    expect(
      offenders,
      `font stacks must LEAD with Geist / Geist Mono or a --type-* token (system-ui only as trailing fallback):\n${offenders
        .map((o) => `  ${o.file}: font-family: ${o.decl}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});

describe("design-slop gate — @font-face brand lock", () => {
  it("declares ONLY Geist + Geist Mono + Instrument Serif as @font-face families", () => {
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

// Engine vocabulary that must never reach user-visible copy. The list is TIGHT
// (separators / multi-word) so a phrase cannot match a legitimate code comment
// or identifier; each was a real leak removed in the UX-redesign pass. One DJ
// phrase per concept lives in shell/dj-vocab.ts; printing the raw engine word
// here is the same class of slop as a generic brand font, so it fails the build.
const JARGON_PHRASES = [
  "grounded · ",
  "strategy · ",
  "CLAP 512D",
  "mean centered",
  "Sven pipe",
  "sidecar socket",
  "Sven contract",
  "Proof gate",
  "proof pending",
  "Sven waits for evidence",
  "I will show the tool trace",
  "tool trace ready",
  "receipts land here",
  "proof waiting",
  "ask Viber for receipts",
  "Live mix receipt armed",
  "after grounded set",
  "show receipts",
  "· cue-anchored",
  "must land before the receipt",
  "bind the lesson move",
  "cited review",
  "open cited",
];

describe("design-slop gate — no engine jargon in user copy", () => {
  it("prints no raw engine vocabulary anywhere in src", () => {
    const offenders: string[] = [];
    for (const f of FILES) {
      const text = readFileSync(f, "utf-8");
      for (const phrase of JARGON_PHRASES) {
        if (text.includes(phrase)) offenders.push(`${f.replace(SRC, "src")}: "${phrase}"`);
      }
    }
    expect(
      offenders,
      `engine jargon leaked into source — translate it (shell/dj-vocab.ts):\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("keeps every DJ_VOCAB value itself jargon-free (no laundering through the helper)", () => {
    const JARGON_WORD = /\b(grounded|proof|receipt|cited|sidecar|cosine|recital|CLAP|512D)\b/i;
    const dirty = Object.entries(DJ_VOCAB).filter(([, value]) => JARGON_WORD.test(value));
    expect(
      dirty,
      `DJ_VOCAB values must stay DJ-plain:\n${dirty.map(([k, v]) => `  ${k}: "${v}"`).join("\n")}`,
    ).toEqual([]);
  });
});
