// SPDX-License-Identifier: Apache-2.0
// REQ-ID: RENDER-07 — Learn window label is `"learn"` (lowercase, no
//                    spaces) — mirrors the precedent set by
//                    `tauri/src-tauri/src/debrief_window.rs::DEBRIEF_WINDOW_LABEL`.
//                    The Rust-side cargo test
//                    (`cargo test learn_window_label_const_is_lowercase`)
//                    pins the const inside Rust; this TS gate is a static
//                    grep over the Rust source so any front-end developer
//                    accidentally renaming the label (e.g. to "Learn") is
//                    caught at the vitest layer too — the label is
//                    referenced from TS in the IPC envelope window-topic
//                    routing.
//
// Phase 91 Plan 02 — RED-state. The `learn_window.rs` file lands in
// Plan 04; until then this test SKIPS.

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LEARN_WINDOW_RS = path.join(
  REPO_ROOT,
  "tauri/src-tauri/src/learn_window.rs",
);

describe("test_learn_window_label.spec.ts (RENDER-07)", () => {
  const present = fs.existsSync(LEARN_WINDOW_RS);
  const testFn = present ? it : it.skip;

  testFn("learn_window.rs declares LEARN_WINDOW_LABEL = \"learn\"", () => {
    const source = fs.readFileSync(LEARN_WINDOW_RS, "utf8");
    // Match the const with flexible whitespace; the type annotation must
    // be `&str` (or `&'static str`) to mirror debrief precedent.
    const re = /pub\s+const\s+LEARN_WINDOW_LABEL\s*:\s*&'?(?:static\s+)?str\s*=\s*"([^"]+)"/;
    const m = source.match(re);
    expect(m, "LEARN_WINDOW_LABEL const not found in learn_window.rs").not.toBeNull();
    const label = m?.[1] ?? "";
    expect(label).toBe("learn");
    // Belt-and-braces: lowercase + no spaces.
    expect(label).toBe(label.toLowerCase());
    expect(label).not.toContain(" ");
  });
});
