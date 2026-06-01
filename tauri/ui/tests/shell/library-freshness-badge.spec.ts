/**
 * @vitest-environment jsdom
 *
 * The shell freshness badge is a glanceable product-truth readout: it consumes
 * the existing library stats contract and never invents a good state when stats
 * cannot be read.
 */

import { describe, expect, it } from "vitest";

import {
  libraryFreshnessBadgeModel,
  mountLibraryFreshnessBadge,
} from "../../src/shell/LibraryFreshnessBadge.js";
import type { LibraryStats } from "../../src/library/api.js";

function stats(overrides: Partial<LibraryStats> = {}): LibraryStats {
  return {
    indexed: 12,
    backend: "sqlite-vec",
    spent_eur: 0,
    failed: 0,
    ...overrides,
  };
}

describe("library freshness badge", () => {
  it("maps fresh and stale stats into terse footer states", () => {
    expect(
      libraryFreshnessBadgeModel(
        stats({
          library_freshness: {
            status: "fresh",
            stale: false,
            reason: "cache_current",
            age_days: 0,
            cache_path: "/tmp/library.pkl",
          },
        }),
      ),
    ).toMatchObject({ state: "ok", label: "library fresh" });

    expect(
      libraryFreshnessBadgeModel(
        stats({
          library_freshness_status: "stale",
          library_stale: true,
          library_staleness_reason: "source_newer_than_cache",
          library_age_days: 4,
        }),
      ),
    ).toMatchObject({ state: "warn", label: "library stale" });
  });

  it("renders not-indexed and unreadable states without calling them fresh", async () => {
    const footer = document.createElement("button");
    const handle = mountLibraryFreshnessBadge(footer, {
      autoload: false,
      pollMs: null,
      getStats: async () =>
        stats({
          library_freshness: {
            status: "not_indexed",
            stale: false,
            reason: "library_cache_missing",
            age_days: 0,
            cache_path: "/tmp/library.pkl",
          },
        }),
    });

    await handle.refresh();

    expect(footer.querySelector(".footer-separator")).toBeTruthy();
    expect(handle.element.dataset.state).toBe("empty");
    expect(handle.element.textContent).toBe("library not indexed");
    handle.teardown();
    expect(footer.querySelector(".library-freshness-badge")).toBeNull();
  });

  it("keeps backend failures honest as unknown", async () => {
    const footer = document.createElement("button");
    const handle = mountLibraryFreshnessBadge(footer, {
      autoload: false,
      pollMs: null,
      getStats: async () => {
        throw new Error("library stats offline");
      },
    });

    await handle.refresh();

    expect(handle.element.dataset.state).toBe("unknown");
    expect(handle.element.textContent).toBe("library unknown");
    expect(handle.element.title).toContain("library stats offline");
  });
});
