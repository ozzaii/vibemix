/**
 * @vitest-environment jsdom
 *
 * Behavioural contract for the cohesive DesktopShell skeleton: the structural
 * lever that makes the scattered surfaces read as one app. Covers keep-alive
 * surface routing, the sidebar collapse (persisted), the Cmd+K palette, the
 * grounding panel, and the self-arranging idle/listening/live activation.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";
import { ShellStore } from "../../src/shell/shell-store.js";
import { SURFACES } from "../../src/shell/surfaces.js";

let shell: MountedShell | null = null;
let host: HTMLElement;

function press(key: string, mods: { ctrl?: boolean; meta?: boolean } = {}): void {
  window.dispatchEvent(
    new KeyboardEvent("keydown", { key, ctrlKey: mods.ctrl ?? false, metaKey: mods.meta ?? false, bubbles: true }),
  );
}

beforeEach(() => {
  globalThis.localStorage?.clear();
  host = document.createElement("div");
  document.body.append(host);
});

afterEach(() => {
  shell?.teardown();
  shell = null;
  host.remove();
});

describe("DesktopShell", () => {
  it("mounts the full composition with the deck as the home surface", () => {
    shell = mountDesktopShell(host);
    expect(host.querySelector(".shell-chrome")).toBeTruthy();
    expect(host.querySelector(".shell-sidebar")).toBeTruthy();
    expect(host.querySelector(".shell-main")).toBeTruthy();
    expect(host.querySelector(".shell-panel")).toBeTruthy();
    expect(host.querySelector(".shell-footer")).toBeTruthy();
    // All five surfaces mounted at once (keep-alive), only the deck active.
    expect(host.querySelectorAll(".surface").length).toBe(SURFACES.length);
    const active = host.querySelectorAll(".surface.is-active");
    expect(active.length).toBe(1);
    expect((active[0] as HTMLElement).dataset.surface).toBe("deck");
  });

  it("switches the active surface while keeping every surface mounted", () => {
    shell = mountDesktopShell(host);
    const crateNav = host.querySelector<HTMLElement>('.sb-nav-item[data-surface="crate"]')!;
    crateNav.click();
    expect(shell.store.getState().activeSurface).toBe("crate");
    // Keep-alive: all regions still in the DOM, exactly one active.
    expect(host.querySelectorAll(".surface").length).toBe(SURFACES.length);
    expect(host.querySelectorAll(".surface.is-active").length).toBe(1);
    expect(host.querySelector(".surface.is-active")?.getAttribute("data-surface")).toBe("crate");
  });

  it("renders a grounded co-host empty state for each non-deck surface", () => {
    shell = mountDesktopShell(host);
    for (const surface of SURFACES) {
      if (surface.id === "deck") continue;
      const region = host.querySelector<HTMLElement>(`.surface[data-surface="${surface.id}"]`)!;
      const title = region.querySelector(".se-title");
      const sub = region.querySelector(".se-sub");
      // The empty state shows the surface's own at-rest copy, not a bare stub.
      expect(title?.textContent).toBe(surface.empty?.title);
      expect(sub?.textContent).toBe(surface.empty?.sub);
      // The real surface still has its keep-alive mount anchor underneath.
      expect(region.querySelector(`.surface-mount[data-wire="${surface.wire}"]`)).toBeTruthy();
    }
  });

  it("makes the Debrief empty state a product preview, not a dead void", () => {
    shell = mountDesktopShell(host);
    const debrief = host.querySelector<HTMLElement>('.surface[data-surface="debrief"]')!;

    expect(debrief.querySelector(".se-title")?.textContent).toBe("Your set review lands here.");
    expect(debrief.textContent).toContain("timeline, skill receipts, and the next move");
    expect(debrief.textContent).toContain("Timeline");
    expect(debrief.textContent).toContain("drops, recoveries, energy shape");
    expect(debrief.textContent).toContain("Receipts");
    expect(debrief.textContent).toContain("why a praise or critique was grounded");
    expect(debrief.textContent).toContain("Next move");
    expect(debrief.textContent).toContain("practice drill or crate follow-up");
    expect(debrief.textContent).not.toContain("No set to review.");
  });

  it("carries the deck tail cursor as the live speaking sign-of-life", () => {
    shell = mountDesktopShell(host);
    const deck = host.querySelector<HTMLElement>('.surface[data-surface="deck"]')!;
    // Present in the markup (CSS gates its visibility to the live state) and the
    // energy field sits behind the stage.
    expect(deck.querySelector(".deck-live-line .tail-cursor")).toBeTruthy();
    expect(deck.querySelector(".deck-energy")).toBeTruthy();
  });

  it("collapses the sidebar on Ctrl+\\ and persists it", () => {
    shell = mountDesktopShell(host);
    expect(host.dataset.collapsed).toBe("false");
    press("\\", { ctrl: true });
    expect(shell.store.getState().collapsed).toBe(true);
    expect(host.dataset.collapsed).toBe("true");
    // Persisted: a fresh store reads the collapsed state back.
    expect(new ShellStore().getState().collapsed).toBe(true);
  });

  it("opens the Cmd+K palette, filters, and runs an action", () => {
    shell = mountDesktopShell(host);
    const palette = host.querySelector<HTMLElement>(".shell-palette")!;
    expect(palette.classList.contains("is-open")).toBe(false);
    press("k", { meta: true });
    expect(palette.classList.contains("is-open")).toBe(true);

    const input = palette.querySelector<HTMLInputElement>(".palette-input")!;
    input.value = "learn";
    input.dispatchEvent(new Event("input"));
    const rows = palette.querySelectorAll(".palette-item");
    expect(rows.length).toBeGreaterThan(0);
    expect(palette.textContent).toContain("Go to Learn");

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(shell.store.getState().activeSurface).toBe("learn");
    expect(palette.classList.contains("is-open")).toBe(false);
  });

  it("toggles the grounding panel on Ctrl+]", () => {
    shell = mountDesktopShell(host);
    expect(host.dataset.panel).toBe("closed");
    press("]", { ctrl: true });
    expect(host.dataset.panel).toBe("open");
    press("]", { ctrl: true });
    expect(host.dataset.panel).toBe("closed");
  });

  it("self-arranges around activation: live opens the panel, idle closes it", () => {
    shell = mountDesktopShell(host);
    expect(host.dataset.state).toBe("idle");
    expect(host.dataset.panel).toBe("closed");

    shell.store.setActivation("live");
    expect(host.dataset.state).toBe("live");
    expect(host.dataset.panel).toBe("open"); // panel auto-opened by going live

    shell.store.setActivation("idle");
    expect(host.dataset.state).toBe("idle");
    expect(host.dataset.panel).toBe("closed"); // and auto-closed back at idle
  });

  it("reflects connection state honestly (idle is disconnected, not faulted)", () => {
    shell = mountDesktopShell(host);
    expect(host.dataset.conn).toBe("disconnected");
    shell.store.setConnection("connected");
    expect(host.dataset.conn).toBe("connected");
  });

  it("keeps the footer read-only so it cannot fake a live session", () => {
    shell = mountDesktopShell(host);
    const footer = host.querySelector<HTMLElement>(".shell-footer")!;
    expect(footer.tagName).toBe("DIV");
    expect(footer.getAttribute("role")).toBe("group");
    footer.click();
    expect(shell.store.getState().activation).toBe("idle");
    expect(shell.store.getState().connection).toBe("disconnected");
  });

  it("jumps surfaces with Cmd+digit accelerators (Settings is Cmd+5, not a bare comma)", () => {
    shell = mountDesktopShell(host);
    press("3", { meta: true });
    expect(shell.store.getState().activeSurface).toBe("learn");
    press("1", { meta: true });
    expect(shell.store.getState().activeSurface).toBe("deck");
    press("5", { meta: true });
    expect(shell.store.getState().activeSurface).toBe("settings");
  });

  it("exposes the Cmd+K palette as an ARIA combobox and inerts the background while open", () => {
    shell = mountDesktopShell(host);
    const input = host.querySelector<HTMLInputElement>(".palette-input")!;
    const body = host.querySelector<HTMLElement>(".shell-body")!;
    expect(input.getAttribute("role")).toBe("combobox");
    expect(input.getAttribute("aria-expanded")).toBe("false");
    expect(input.getAttribute("aria-controls")).toBe(host.querySelector(".palette-list")?.id);

    press("k", { meta: true });
    expect(input.getAttribute("aria-expanded")).toBe("true");
    // The arrow-key selection is exposed to AT via aria-activedescendant -> a real row id.
    const active = input.getAttribute("aria-activedescendant");
    expect(active).toBeTruthy();
    expect(host.querySelector(`#${active}`)?.getAttribute("role")).toBe("option");
    // The background is hidden from the SR browse cursor while the modal is open.
    expect(body.getAttribute("aria-hidden")).toBe("true");

    // Esc closes (handled on the input), clearing both the expanded + inert state.
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(input.getAttribute("aria-expanded")).toBe("false");
    expect(body.getAttribute("aria-hidden")).toBeNull();
  });

  it("renders the grounding panel as honest empty slots when live", () => {
    shell = mountDesktopShell(host);
    shell.store.setActivation("live");
    const sections = host.querySelectorAll(".shell-panel .panel-section");
    expect(sections.length).toBe(2);
    const labels = Array.from(host.querySelectorAll(".shell-panel .panel-label")).map(
      (el) => el.textContent,
    );
    expect(labels).toContain("Evidence");
    expect(labels).not.toContain("Cited");
    expect(host.querySelector(".shell-panel .panel-armed")).toBeNull();
    // Back to idle returns to the honest prose state (no leftover receipt slots).
    shell.store.setActivation("idle");
    expect(host.querySelectorAll(".shell-panel .panel-section").length).toBe(0);
  });
});
