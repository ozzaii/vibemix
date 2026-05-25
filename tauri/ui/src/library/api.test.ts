// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — api.ts dev-fallback vitest spec.
 *
 * Runs under node with no `@tauri-apps/api/core` resolvable invoke (vitest
 * env), so every client call MUST fall through to the real 2026-05-25
 * subset-run sample data — the same numbers baked into the mock. No network.
 */

import { describe, expect, it } from "vitest";

import {
  DEV_FALLBACK,
  libraryEmbedFolder,
  librarySearch,
  librarySimilar,
  libraryStats,
} from "./api.js";

// Under vitest there is no Tauri runtime: `invoke()` either is unresolvable or
// throws when called. Either way every client function must fall through to the
// real 2026-05-25 subset-run sample — that's the contract these tests pin.
describe("dev fallback (no Tauri bridge)", () => {
  it("librarySearch returns the techno subset (6 rows, top = Raffertie)", async () => {
    const r = await librarySearch("hard aggressive techno");
    expect(r.results).toHaveLength(6);
    expect(r.corpus_size).toBe(142);
    expect(r.centered).toBe(true);
    expect(r.results[0]?.title).toBe("Raffertie — The Substance");
    expect(r.results[0]?.score).toBeCloseTo(0.764, 3);
  });

  it("librarySimilar returns the ygmf_Remix neighbour list (centered ~0.3)", async () => {
    const r = await librarySimilar("ygmf_Remix.wav");
    expect(r.results).toHaveLength(6);
    expect(r.results[0]?.title).toBe("Girl Like Me");
    expect(r.results[0]?.score).toBeCloseTo(0.369, 3);
    expect(r.results[0]?.meta).toBe("centered · cos");
  });

  it("libraryStats returns 142 / sqlite-vec / €0.19 / 0 failed", async () => {
    const s = await libraryStats();
    expect(s).toEqual({
      indexed: 142,
      backend: "sqlite-vec",
      spent_eur: 0.19,
      failed: 0,
    });
  });

  it("libraryEmbedFolder returns false (no bridge → caller drives replay)", async () => {
    expect(await libraryEmbedFolder("~/Music", "cue-anchored")).toBe(false);
  });

  it("exposes the captured embed log (8 entries, mixed ok/skip)", () => {
    expect(DEV_FALLBACK.embedLog).toHaveLength(8);
    expect(DEV_FALLBACK.embedLog.some(([st]) => st === "skip")).toBe(true);
    expect(DEV_FALLBACK.embedLog.every(([st]) => st !== "err")).toBe(true);
  });
});
