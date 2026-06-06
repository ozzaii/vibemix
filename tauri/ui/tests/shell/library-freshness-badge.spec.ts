/**
 * @vitest-environment jsdom
 *
 * The shell freshness badge is a glanceable product-truth readout: it consumes
 * the existing library stats contract and never invents a good state when stats
 * cannot be read.
 */

import { describe, expect, it, vi } from "vitest";

import {
  libraryFreshnessBadgeModel,
  mountLibraryFreshnessBadge,
} from "../../src/shell/LibraryFreshnessBadge.js";
import type {
  LibraryImportProgress,
  LibraryStats,
} from "../../src/library/api.js";

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

  it("surfaces a discovered music folder as a first-run setup affordance", async () => {
    const footer = document.createElement("footer");
    const handle = mountLibraryFreshnessBadge(footer, {
      autoload: false,
      pollMs: null,
      getStats: async () =>
        stats({
          indexed: 0,
          library_freshness: {
            status: "not_indexed",
            stale: false,
            reason: "library_cache_missing",
            age_days: 0,
            cache_path: "/tmp/library.pkl",
          },
          library_setup_candidates: [
            {
              kind: "music_folder",
              path: "/Users/ozai/Downloads/Music",
              reason: "187 audio files",
            },
          ],
        }),
    });

    await handle.refresh();

    expect(handle.element.dataset.state).toBe("setup");
    expect(handle.element.textContent).toBe("index music");
    expect(handle.element.title).toContain("found music folder");
    expect(handle.element.title).toContain("/Users/ozai/Downloads/Music");
  });

  it("does not surface catalog-only dead import candidates as setup", async () => {
    const footer = document.createElement("footer");
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
          library_setup_candidates: [
            {
              kind: "rekordbox_xml",
              path: "/Users/ozai/Library/Pioneer/rekordbox.xml",
            },
          ],
        }),
    });

    await handle.refresh();

    expect(handle.element.dataset.state).toBe("empty");
    expect(handle.element.textContent).toBe("library not indexed");
    handle.teardown();
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
    expect(handle.element.hidden).toBe(true);
    expect(handle.element.textContent).toBe("");
    expect(handle.element.title).toContain("library stats offline");
  });

  it("paints an ambient indexing state from live import progress, then reverts", async () => {
    let captured: ((p: LibraryImportProgress) => void) | null = null;
    const getStats = vi.fn(async () =>
      stats({
        indexed: 0,
        library_freshness: {
          status: "not_indexed",
          stale: false,
          reason: "library_cache_missing",
          age_days: 0,
          cache_path: "/tmp/library.pkl",
        },
      }),
    );
    const footer = document.createElement("footer");
    const handle = mountLibraryFreshnessBadge(footer, {
      autoload: false,
      pollMs: null,
      getStats,
      subscribeProgress: async (cb) => {
        captured = cb;
        return () => {};
      },
    });
    await Promise.resolve();
    expect(captured).not.toBeNull();

    captured!({
      total: 10,
      done: 3,
      current_track_name: "track.mp3",
      cache_hits: 0,
      cancelled: false,
    });
    expect(handle.element.dataset.state).toBe("indexing");
    expect(handle.element.textContent).toBe("indexing 3/10");
    expect(handle.element.title).toContain("go run a set");

    const callsBefore = getStats.mock.calls.length;
    captured!({
      total: 10,
      done: 10,
      current_track_name: "",
      cache_hits: 0,
      cancelled: false,
    });
    await Promise.resolve();
    expect(getStats.mock.calls.length).toBe(callsBefore + 1);
    handle.teardown();
  });
});
