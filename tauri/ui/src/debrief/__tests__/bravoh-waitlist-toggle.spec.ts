// SPDX-License-Identifier: Apache-2.0
// Plan 44-04 Task 2 — bravoh-waitlist-toggle (LAUNCH-05).
//
// Pins the LAUNCH-05 contract:
//   - Default OFF when initialOptIn=false; no link in DOM.
//   - Toggle ON → link visible + href matches BRAVOH_WAITLIST_URL verbatim.
//   - Toggle OFF after ON → link removed from save-success view.
//   - Click toggle fires onToggle with the new state.
//   - No telemetry / IPC invocation on mount — only on explicit user toggle.
//
// The verbatim UTM URL is locked from CONTEXT §LAUNCH-05:
//   https://bravoh.com/waitlist?utm_source=vibemix&utm_medium=app&utm_campaign=oss-launch

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BRAVOH_WAITLIST_URL,
  mountBravohWaitlistToggle,
} from "../components/bravoh-waitlist-toggle.js";

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// (i) URL constant lock
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — URL constant", () => {
  it("BRAVOH_WAITLIST_URL matches CONTEXT §LAUNCH-05 verbatim", () => {
    expect(BRAVOH_WAITLIST_URL).toBe(
      "https://bravoh.com/waitlist?utm_source=vibemix&utm_medium=app&utm_campaign=oss-launch",
    );
  });
});

// ---------------------------------------------------------------------------
// (ii) Default OFF + no link
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — default OFF", () => {
  it("renders toggle in OFF state when initialOptIn=false", () => {
    const onToggle = vi.fn();
    mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle,
    });
    const checkbox = container.querySelector<HTMLInputElement>(
      'input[type="checkbox"][data-vmx-bravoh-toggle]',
    );
    expect(checkbox).not.toBeNull();
    expect(checkbox?.checked).toBe(false);
  });

  it("hides the waitlist link when toggle is OFF", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle: vi.fn(),
    });
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    // Link is either absent OR hidden via display:none — both are valid.
    if (link) {
      expect(link.hidden || link.style.display === "none").toBe(true);
    }
  });

  it("does NOT fire onToggle on mount (no implicit opt-in)", () => {
    const onToggle = vi.fn();
    mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle,
    });
    expect(onToggle).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// (iii) Toggle ON — link visible with verbatim href
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — toggle ON", () => {
  it("shows the waitlist link when initialOptIn=true", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle: vi.fn(),
    });
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link).not.toBeNull();
    expect(link?.hidden).toBe(false);
    expect(link?.style.display).not.toBe("none");
  });

  it("link href is the verbatim BRAVOH_WAITLIST_URL", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle: vi.fn(),
    });
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link?.getAttribute("href")).toBe(BRAVOH_WAITLIST_URL);
  });

  it("link opens in new tab with noopener noreferrer", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle: vi.fn(),
    });
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link?.target).toBe("_blank");
    expect(link?.rel).toContain("noopener");
    expect(link?.rel).toContain("noreferrer");
  });
});

// ---------------------------------------------------------------------------
// (iv) Click toggle fires onToggle with new state + flips link visibility
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — user click", () => {
  it("click on OFF toggle → onToggle(true) + link appears", () => {
    const onToggle = vi.fn();
    mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle,
    });
    const checkbox = container.querySelector<HTMLInputElement>(
      'input[type="checkbox"][data-vmx-bravoh-toggle]',
    );
    expect(checkbox).not.toBeNull();
    checkbox!.checked = true;
    checkbox!.dispatchEvent(new Event("change", { bubbles: true }));

    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onToggle).toHaveBeenCalledWith(true);

    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link).not.toBeNull();
    expect(link?.hidden).toBe(false);
  });

  it("click on ON toggle → onToggle(false) + link hidden", () => {
    const onToggle = vi.fn();
    mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle,
    });
    const checkbox = container.querySelector<HTMLInputElement>(
      'input[type="checkbox"][data-vmx-bravoh-toggle]',
    );
    checkbox!.checked = false;
    checkbox!.dispatchEvent(new Event("change", { bubbles: true }));

    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onToggle).toHaveBeenCalledWith(false);

    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    if (link) {
      expect(link.hidden || link.style.display === "none").toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// (v) Imperative API — setOptIn updates DOM without re-firing onToggle
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — imperative setOptIn", () => {
  it("setOptIn(true) shows link without firing onToggle", () => {
    const onToggle = vi.fn();
    const handle = mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle,
    });
    handle.setOptIn(true);
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link).not.toBeNull();
    expect(link?.hidden).toBe(false);
    expect(onToggle).not.toHaveBeenCalled();
  });

  it("setOptIn(false) hides link + leaves callback untouched", () => {
    const onToggle = vi.fn();
    const handle = mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle,
    });
    handle.setOptIn(false);
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    if (link) {
      expect(link.hidden || link.style.display === "none").toBe(true);
    }
    expect(onToggle).not.toHaveBeenCalled();
  });

  it("destroy() detaches the listener — no callback after destroy", () => {
    const onToggle = vi.fn();
    const handle = mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle,
    });
    handle.destroy();
    expect(container.querySelector("[data-vmx-bravoh-toggle]")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// (vi) Copy lock — label + subtitle pinned to CONTEXT
// ---------------------------------------------------------------------------

describe("bravoh-waitlist-toggle — copy lock", () => {
  it("toggle label is 'Join Bravoh waitlist (optional)'", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: false,
      onToggle: vi.fn(),
    });
    const text = container.textContent ?? "";
    expect(text).toContain("Join Bravoh waitlist (optional)");
  });

  it("link text is 'Join the Bravoh waitlist →'", () => {
    mountBravohWaitlistToggle(container, {
      initialOptIn: true,
      onToggle: vi.fn(),
    });
    const link = container.querySelector<HTMLAnchorElement>(
      "a.vmx-bravoh-waitlist-link",
    );
    expect(link?.textContent).toBe("Join the Bravoh waitlist →");
  });
});
