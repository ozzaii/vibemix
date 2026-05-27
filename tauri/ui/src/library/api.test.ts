// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — api.ts dev-fallback vitest spec.
 *
 * Runs under node with no `@tauri-apps/api/core` resolvable invoke (vitest
 * env), so every client call MUST fall through to the real 2026-05-25
 * subset-run sample data — the same numbers baked into the mock. No network.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  DEV_FALLBACK,
  libraryBuildSet,
  libraryChat,
  libraryEmbedFolder,
  libraryModels,
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
      embedding_backend: "clap",
      embedding_dim: 512,
      clap_model_installed: true,
      clap_model_path: "~/.cache/vibemix/clap-onnx",
      clap_model_missing: [],
      agent_backend: "codex",
      agent_ready: true,
      agent_status: "ready",
      agent_hint: "",
      spent_eur: 0.19,
      failed: 0,
    });
  });

  it("libraryEmbedFolder returns false (no bridge → caller drives replay)", async () => {
    expect(await libraryEmbedFolder("~/Music", "cue_anchored")).toBe(false);
  });

  it("libraryModels returns the local model setup fallback", async () => {
    const r = await libraryModels();
    expect(r.required_ready).toBe(true);
    expect(r.all_ready).toBe(true);
    expect(r.models.map((m) => m.id)).toEqual(["clap", "cue-detr"]);
    expect(r.models[0]?.installed).toBe(true);
  });

  it("libraryModels install fallback keeps the install shape", async () => {
    const r = await libraryModels("clap");
    expect(r.install?.target).toBe("clap");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results[0]?.id).toBe("clap");
  });

  it("libraryModels required install fallback returns required assets", async () => {
    const r = await libraryModels("required");
    expect(r.install?.target).toBe("required");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results.map((item) => item.id)).toEqual(["clap"]);
  });

  it("libraryModels cue install fallback keeps the cue target shape", async () => {
    const r = await libraryModels("cue");
    expect(r.install?.target).toBe("cue");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results[0]?.id).toBe("cue-detr");
  });

  it("libraryModels all install fallback returns both local model targets", async () => {
    const r = await libraryModels("all");
    expect(r.install?.target).toBe("all");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results.map((item) => item.id)).toEqual(["clap", "cue-detr"]);
  });

  it("exposes the captured embed log (8 entries, mixed ok/skip)", () => {
    expect(DEV_FALLBACK.embedLog).toHaveLength(8);
    expect(DEV_FALLBACK.embedLog.some(([st]) => st === "skip")).toBe(true);
    expect(DEV_FALLBACK.embedLog.every(([st]) => st !== "err")).toBe(true);
  });

  it("libraryBuildSet returns the DEV_BUILD exported set (6 tracks, .xml export)", async () => {
    const r = await libraryBuildSet("warehouse opener", "peak_time");
    expect(r.tracks).toHaveLength(6);
    expect(r.count).toBe(6);
    expect(r.stop_reason).toBe("exported");
    expect(r.export_path).toMatch(/\.xml$/);
    // honest meta — no fabricated human title/artist on the flat-id rows.
    expect(r.tracks[0]?.meta).toMatch(/^track /);
  });

  it("libraryChat returns the DEV_CHAT conversational sample", async () => {
    const r = await libraryChat("what should I demo?");
    expect(r.reply.length).toBeGreaterThan(20);
    expect(r.tool_trace[0]?.name).toBe("search_vibe");
    expect(r.playlist).toBeNull();
    expect(r.stop_reason).toBe("model_done");
    expect(DEV_FALLBACK.chat.seen_track_ids).toContain("7f9f9052");
  });
});

describe("library entry markup", () => {
  it("does not first-paint the stale mock corpus denominator", () => {
    const html = readFileSync("library.html", "utf8");
    const indexedStat = html.match(
      /<div class="v" id="vmx-lib-stat-indexed">(?<body>.*?)<\/div>/s,
    );

    expect(indexedStat?.groups?.body).toBe("·");
    expect(html).not.toContain("/ 1547");
  });
});
