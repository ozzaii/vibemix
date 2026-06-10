/**
 * @vitest-environment jsdom
 *
 * F10 frontend-half: the launch step surfaces the local embed as privacy
 * reassurance while it runs, and exposes a native folder-pick callback.
 */

import { describe, expect, it, vi } from "vitest";

import {
  renderStepLibraryFeed,
  type LibraryFeedCallbacks,
  type LibraryFeedState,
} from "../step-library-feed.js";

function callbacks(over: Partial<LibraryFeedCallbacks> = {}): LibraryFeedCallbacks {
  return {
    skill: "beginner",
    profileConsent: false,
    telemetryConsent: false,
    onSelectSkill: vi.fn(),
    onToggleProfile: vi.fn(),
    onToggleTelemetry: vi.fn(),
    onRefreshCandidates: vi.fn(),
    onIndexCandidate: vi.fn(),
    onPickFolder: vi.fn(),
    onOpenVibemix: vi.fn(),
    ...over,
  };
}

function privacyCard(root: HTMLElement): HTMLElement {
  const card = root.querySelector<HTMLElement>('[data-role="privacy"]');
  if (!card) throw new Error("privacy card missing");
  return card;
}

describe("library-feed embed progress (F10 frontend-half)", () => {
  it("frames the running embed as local-only privacy progress in the Privacy card", () => {
    const state: LibraryFeedState = {
      status: "indexing",
      candidates: [],
      indexed: 0,
      selectedPath: "/Users/ozai/Music",
      progress: {
        total: 10,
        done: 4,
        current_track_name: "track.mp3",
        cache_hits: 0,
        cancelled: false,
      },
    };
    const root = renderStepLibraryFeed(state, callbacks());
    const text = privacyCard(root).textContent ?? "";
    expect(text).toContain("never leaves this machine");
    expect(text).toContain("4/10");
    const fill = privacyCard(root).querySelector<HTMLElement>(
      ".wizard-feed-progress__fill",
    );
    expect(fill?.style.getPropertyValue("--feed-progress")).toBe("40%");
  });

  it("keeps the Privacy card free of embed copy before an import starts", () => {
    const state: LibraryFeedState = { status: "ready", candidates: [], indexed: 0 };
    const text = privacyCard(renderStepLibraryFeed(state, callbacks())).textContent ?? "";
    expect(text).not.toContain("never leaves this machine");
  });

  it("offers a native folder pick wired to onPickFolder", () => {
    const onPickFolder = vi.fn();
    const state: LibraryFeedState = { status: "empty", candidates: [], indexed: 0 };
    const root = renderStepLibraryFeed(state, callbacks({ onPickFolder }));
    const pick = Array.from(root.querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").includes("Choose a folder"),
    );
    expect(pick).toBeDefined();
    pick!.click();
    expect(onPickFolder).toHaveBeenCalledTimes(1);
  });

  it("shows failed counts on a done import instead of pure success copy", () => {
    const state: LibraryFeedState = {
      status: "done",
      candidates: [],
      indexed: 0,
      selectedPath: "/Users/ozai/Music",
      progress: {
        total: 10,
        done: 10,
        current_track_name: "",
        cache_hits: 0,
        cancelled: false,
        failed: 3,
        failure_reason: "broken.mp3: unprobeable",
      },
    };
    const text = renderStepLibraryFeed(state, callbacks()).textContent ?? "";
    expect(text).toContain("7 of 10");
    expect(text).toContain("3 failed");
  });

  it("renders the wipeout error copy the router sets on a total failure", () => {
    const state: LibraryFeedState = {
      status: "error",
      candidates: [],
      indexed: 0,
      error: "indexing failed: first.mp3: unprobeable",
    };
    const text = renderStepLibraryFeed(state, callbacks()).textContent ?? "";
    expect(text).toContain("indexing failed: first.mp3: unprobeable");
  });
});
