/* Wave-2 copy contract — ONE enforced sweep instead of twenty point edits.
 *
 * The 2026-06-10 copy audit (UI-AUDIT-WAVE2-FULL.json, surface
 * sven-voice-copy-consistency) found the same classes of violation
 * repeating across surfaces: em dashes in shipped copy (explicit contract
 * ban), the internal binary name VIBEMIX-CORE shouting at the user, port
 * numbers and process vocabulary in error prose, vendor jargon
 * (LiveKit/Gemini/Codex) leaking into user-facing strings, the retired
 * "Adam" voice name, and engineering notes (cache paths) shipping as
 * tooltips. Point-fixing each site leaves the next edit free to regress;
 * this spec scans every shipped string literal so the class stays dead.
 *
 * Scope: string literals in tauri/ui/src/**\/*.ts (comments stripped) and
 * the static HTML entry pages. Test files are excluded — they legitimately
 * mention banned words inside assertions. Mocks under mocks/ are not gated.
 *
 * The scanner is intentionally small: a char-level pass that strips
 * line/block comments and collects single-quote, double-quote, and
 * template-literal contents. Regex literals are not modeled; if one ever
 * confuses the scanner the failure is loud (a weird "literal" in the
 * report), not silent.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const UI_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(UI_ROOT, "src");

/** Files excluded from the sweep, each with a reason. Keep this list SHRINKING. */
const EXCLUDED = new Set<string>([
  // Another session's uncommitted WIP owns this file (Viber chat). Its
  // AGENT_FAILURE_COPY cards carry known Codex-jargon violations — queued
  // in the UI-QUALITY-PASS ledger; remove this entry when that lands.
  "src/library/index.ts",
  // Dev-mode mock DATA, not authored copy: real track titles legitimately
  // carry em dashes ("Raffertie — The Substance") and the mock Viber prose
  // mimics model output, which this spec does not govern.
  "src/library/api.ts",
]);

interface Ban {
  id: string;
  why: string;
  /** Return true when the literal violates the ban. */
  hits: (literal: string) => boolean;
}

const BANS: Ban[] = [
  {
    id: "em-dash",
    why: "no em dashes in shipped copy (house contract); use periods, commas, or the ' · ' separator",
    // A literal that IS the em dash is the instrument 'no value' placeholder
    // (recording-browser usage line) — that glyph is allowed; prose is not.
    // Same for a placeholder readout standing alone between tags in markup
    // templates (">—<", ">— BPM<"): the dash is a no-value glyph, not prose.
    hits: (s) => {
      const noPlaceholders = s.replace(/>\s*—(?:\s+[A-Z]{2,6})?\s*</g, "><");
      return noPlaceholders.includes("—") && noPlaceholders.trim() !== "—";
    },
  },
  {
    id: "internal-binary",
    why: "vibemix-core is the sidecar build name, not a product noun",
    hits: (s) => /vibemix-core/i.test(s),
  },
  {
    id: "port-prose",
    why: "port numbers are dev vocabulary; tell the user the recovery action instead",
    hits: (s) => /\bport\s+\d{4,5}\b/i.test(s),
  },
  {
    id: "vendor-jargon",
    why: "LiveKit/Gemini/Codex are internals; speak in product nouns (voice link, brain, Viber). Lowercase wire keys ('livekit') are not prose and pass.",
    hits: (s) => /\b(?:LiveKit|Gemini|Codex)\b/.test(s),
  },
  {
    id: "voice-adam",
    why: "'Adam' is the retired cloud-TTS voice name; the product voice is Sven (local Chatterbox)",
    hits: (s) => /\bAdam\b/.test(s),
  },
  {
    id: "path-prose",
    why: "internal cache paths are engineering notes, not user copy (bare path VALUES on data rows pass; sentences embedding them do not)",
    hits: (s) => /(~\/\.cache|\/Users\/)/.test(s) && /\s/.test(s.trim()),
  },
  {
    id: "ascii-ellipsis",
    why: "trailing-off copy uses the single … glyph; three ASCII dots regress per-surface (one debrief screen rendered both forms at once)",
    hits: (s) => s.includes("..."),
  },
];

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name === "__tests__") continue;
      out.push(...walk(p));
    } else if (
      extname(p) === ".ts" &&
      !/\.(spec|test)\.ts$/.test(name) &&
      !/\.generated\./.test(name)
    ) {
      out.push(p);
    }
  }
  return out;
}

/** Extract string-literal contents from TS source, comments stripped. */
export function extractStringLiterals(source: string): string[] {
  const out: string[] = [];
  let i = 0;
  const n = source.length;
  while (i < n) {
    const c = source[i]!;
    const next = source[i + 1];
    // line comment
    if (c === "/" && next === "/") {
      while (i < n && source[i] !== "\n") i++;
      continue;
    }
    // block comment
    if (c === "/" && next === "*") {
      i += 2;
      while (i < n && !(source[i] === "*" && source[i + 1] === "/")) i++;
      i += 2;
      continue;
    }
    if (c === '"' || c === "'") {
      const quote = c;
      i++;
      let lit = "";
      while (i < n && source[i] !== quote) {
        if (source[i] === "\\") {
          lit += source[i]! + (source[i + 1] ?? "");
          i += 2;
          continue;
        }
        if (source[i] === "\n") break; // unterminated — scanner got confused; bail on this literal
        lit += source[i]!;
        i++;
      }
      i++;
      out.push(lit);
      continue;
    }
    if (c === "`") {
      i++;
      let lit = "";
      while (i < n && source[i] !== "`") {
        if (source[i] === "\\") {
          lit += source[i]! + (source[i + 1] ?? "");
          i += 2;
          continue;
        }
        // skip ${...} interpolations (track nested braces)
        if (source[i] === "$" && source[i + 1] === "{") {
          i += 2;
          let depth = 1;
          while (i < n && depth > 0) {
            if (source[i] === "{") depth++;
            else if (source[i] === "}") depth--;
            i++;
          }
          continue;
        }
        lit += source[i]!;
        i++;
      }
      i++;
      out.push(lit);
      continue;
    }
    i++;
  }
  return out;
}

/** Strip comment syntax EMBEDDED IN a literal before judging it: CSS/GLSL
 *  block comments and HTML/SVG comments inside template literals are author
 *  notes, not shipped copy. Whitespace-preceded `//` line comments (GLSL)
 *  are stripped too; `https://` survives because `:` precedes its slashes. */
function stripEmbeddedComments(lit: string): string {
  return lit
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/(^|\s)\/\/[^\n]*/g, "$1");
}

interface Violation {
  file: string;
  ban: string;
  literal: string;
}

function scan(): Violation[] {
  const violations: Violation[] = [];
  for (const file of walk(SRC)) {
    const rel = relative(UI_ROOT, file).split("\\").join("/");
    if (EXCLUDED.has(rel)) continue;
    const literals = extractStringLiterals(readFileSync(file, "utf8"));
    for (const raw of literals) {
      const lit = stripEmbeddedComments(raw);
      for (const ban of BANS) {
        if (ban.hits(lit)) {
          violations.push({ file: rel, ban: ban.id, literal: lit.trim().slice(0, 120) });
        }
      }
    }
  }
  // Static HTML entry pages: user-visible markup text. Strip HTML comments,
  // then run the same bans over the whole remaining text (markup carries no
  // legitimate em dash / binary-name / port-prose content).
  for (const name of readdirSync(UI_ROOT)) {
    if (extname(name) !== ".html") continue;
    // HTML + inline-<style> CSS comments are author notes, not copy.
    const text = stripEmbeddedComments(readFileSync(join(UI_ROOT, name), "utf8"));
    for (const ban of BANS) {
      for (const line of text.split("\n")) {
        if (ban.hits(line)) {
          violations.push({ file: name, ban: ban.id, literal: line.trim().slice(0, 120) });
        }
      }
    }
  }
  return violations;
}

describe("copy contract — shipped strings stay in the product voice", () => {
  it("no banned vocabulary in shipped string literals or entry HTML", () => {
    const violations = scan();
    const report = violations
      .map((v) => `[${v.ban}] ${v.file}: ${JSON.stringify(v.literal)}`)
      .join("\n");
    expect(violations, `\n${report}\n`).toEqual([]);
  });

  it("scanner extracts literals and strips comments (self-test)", () => {
    const src = [
      `// comment — with em dash`,
      `/* block — comment */`,
      `const a = "real string";`,
      "const b = `tpl ${x} text`;",
      `const c = 'single';`,
    ].join("\n");
    expect(extractStringLiterals(src)).toEqual([
      "real string",
      "tpl  text",
      "single",
    ]);
  });
});
