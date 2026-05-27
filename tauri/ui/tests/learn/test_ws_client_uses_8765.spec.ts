// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-07 — Learn webview connects to ws:8765 only (one-socket
//                    invariant #4 — CLAUDE.md §Architecture). Any
//                    `new WebSocket(...)` in `tauri/ui/src/learn/**/*.ts`
//                    MUST use port 8765 — never 8766 (debrief), never a
//                    new port. Sibling Python gate:
//                    `tests/learn/test_no_new_ws_port.py` (zero
//                    `websockets.serve` under `src/vibemix/learn/`).
//
// Phase 91 Plan 02 — GREEN day-one because the Learn TS sources do not yet
// contain any `new WebSocket(...)` (Plan 05 wires the ws-client). The
// moment any TS file under `tauri/ui/src/learn/` instantiates a WebSocket,
// every URL is scanned; the first off-8765 reference fails the gate red.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LEARN_SRC = path.join(REPO_ROOT, "tauri/ui/src/learn");

// Match `new WebSocket(<url>)` — capture the URL argument literal/expr.
// We want both `new WebSocket("ws://127.0.0.1:8765")` and
// `new WebSocket(WS_URL)` (i.e. a constant ref). For the constant case,
// the URL is in the variable definition elsewhere — we walk every line
// in the source and check that each `new WebSocket(...)` argument resolves
// to a string containing ":8765".
const WS_NEW_RE = /\bnew\s+WebSocket\s*\(\s*([^)]+)\s*\)/g;

function walkTsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkTsFiles(full));
    else if (
      entry.isFile() &&
      entry.name.endsWith(".ts") &&
      !entry.name.endsWith(".d.ts")
    )
      out.push(full);
  }
  return out;
}

describe("test_ws_client_uses_8765.spec.ts (RENDER-07 — Invariant #4)", () => {
  it("every `new WebSocket(...)` in tauri/ui/src/learn/ targets :8765", () => {
    const offenders: string[] = [];
    for (const file of walkTsFiles(LEARN_SRC)) {
      const source = fs.readFileSync(file, "utf8");
      let match: RegExpExecArray | null;
      while ((match = WS_NEW_RE.exec(source)) !== null) {
        const arg = (match[1] ?? "").trim();
        // If the argument is a string literal, inspect it directly.
        const stringLiteral = arg.match(/^["'`]([^"'`]+)["'`]$/);
        if (stringLiteral) {
          const url = stringLiteral[1] ?? "";
          if (!url.includes(":8765")) {
            offenders.push(`${file}: new WebSocket("${url}") — wrong port`);
          }
          continue;
        }
        // Identifier reference — scan the same file for its definition.
        const ident = arg.match(/^[A-Za-z_][A-Za-z0-9_]*$/);
        if (ident) {
          const defRe = new RegExp(
            `(?:const|let|var)\\s+${ident[0]}\\s*[:=][^;\\n]*?["'\`]([^"'\`]+)["'\`]`,
          );
          const defMatch = source.match(defRe);
          const url = defMatch?.[1] ?? "";
          if (!url || !url.includes(":8765")) {
            offenders.push(
              `${file}: new WebSocket(${ident[0]}) — ${ident[0]} not found or off-8765`,
            );
          }
          continue;
        }
        // Unknown shape — report so the next executor can investigate.
        offenders.push(`${file}: new WebSocket(<expr>) — non-literal arg "${arg}"`);
      }
    }
    expect(
      offenders,
      `Invariant #4 violation — Learn webview must share ws:8765:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });
});
