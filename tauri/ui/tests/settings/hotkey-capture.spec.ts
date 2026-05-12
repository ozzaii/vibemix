/* Phase 12 Wave 4 — hotkey capture state machine (Plan 12-05 §7).
 *
 * Asserts:
 *   - Idle render shows current combo + Rebind button + chip-as-`--phosphor`.
 *   - Clicking Rebind enters capture mode (data-capture=true, chip → PRESS KEYS…).
 *   - keyEventToCombo lifts KeyboardEvent into wire-form combo string.
 *   - keyEventToCombo returns null on modifier-only press.
 *   - isReservedCombo flags cmd+q, cmd+space, etc. (matches Rust side).
 *   - During capture: valid combo (e.g. alt+shift+k) fires onCapture
 *     with that combo and exits capture mode.
 *   - During capture: reserved combo surfaces inline --rec error, stays
 *     in capture mode, does NOT call onCapture.
 *   - Escape during capture cancels (does not fire onCapture).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  isReservedCombo,
  keyEventToCombo,
  renderHotkeyCapture,
} from "../../src/settings/components/hotkey-capture.js";

afterEach(() => {
  document.body.replaceChildren();
});

function mount(props: {
  value: string;
  onCapture: (combo: string) => void;
}) {
  const handle = renderHotkeyCapture(props);
  document.body.append(handle.root);
  return handle;
}

describe("keyEventToCombo", () => {
  it("captures cmd+shift+m", () => {
    const ev = new KeyboardEvent("keydown", {
      key: "m",
      metaKey: true,
      shiftKey: true,
    });
    expect(keyEventToCombo(ev)).toBe("cmd+shift+m");
  });

  it("captures ctrl+alt+k", () => {
    const ev = new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: true,
      altKey: true,
    });
    expect(keyEventToCombo(ev)).toBe("ctrl+alt+k");
  });

  it("maps space key to 'space'", () => {
    const ev = new KeyboardEvent("keydown", {
      key: " ",
      metaKey: true,
    });
    expect(keyEventToCombo(ev)).toBe("cmd+space");
  });

  it("returns null on modifier-only press", () => {
    const ev = new KeyboardEvent("keydown", { key: "Shift", shiftKey: true });
    expect(keyEventToCombo(ev)).toBeNull();
  });

  it("returns null with no modifiers (bare letter)", () => {
    const ev = new KeyboardEvent("keydown", { key: "m" });
    expect(keyEventToCombo(ev)).toBeNull();
  });
});

describe("isReservedCombo", () => {
  it("flags every macOS reserved combo", () => {
    expect(isReservedCombo("cmd+q")).toBe(true);
    expect(isReservedCombo("cmd+w")).toBe(true);
    expect(isReservedCombo("cmd+tab")).toBe(true);
    expect(isReservedCombo("cmd+space")).toBe(true);
    expect(isReservedCombo("cmd+shift+tab")).toBe(true);
  });

  it("flags every Windows reserved combo", () => {
    expect(isReservedCombo("alt+f4")).toBe(true);
    expect(isReservedCombo("ctrl+alt+del")).toBe(true);
    expect(isReservedCombo("ctrl+alt+delete")).toBe(true);
    expect(isReservedCombo("win+l")).toBe(true);
    expect(isReservedCombo("meta+l")).toBe(true);
  });

  it("does NOT flag valid combos", () => {
    expect(isReservedCombo("cmd+shift+m")).toBe(false);
    expect(isReservedCombo("ctrl+shift+m")).toBe(false);
    expect(isReservedCombo("alt+shift+k")).toBe(false);
  });
});

describe("renderHotkeyCapture — idle render", () => {
  it("renders chip + rebind button", () => {
    const h = mount({ value: "cmd+shift+m", onCapture: vi.fn() });
    expect(h.root.querySelector(".vmx-hotkey-capture__chip")).toBeTruthy();
    expect(h.root.querySelector(".vmx-hotkey-capture__rebind")).toBeTruthy();
    expect(h.root.dataset.capture).toBe("false");
  });

  it("chip text reflects the current combo (OS-pretty form on jsdom default)", () => {
    const h = mount({ value: "ctrl+shift+m", onCapture: vi.fn() });
    const chip = h.root.querySelector<HTMLElement>(".vmx-hotkey-capture__chip");
    // Linux/Windows jsdom: Ctrl+Shift+M  /  macOS jsdom platform: ⌃⇧M-ish
    expect(chip?.textContent ?? "").toMatch(/M$/i);
  });
});

describe("renderHotkeyCapture — capture state machine", () => {
  it("clicking Rebind enters capture mode", () => {
    const h = mount({ value: "cmd+shift+m", onCapture: vi.fn() });
    h.root
      .querySelector<HTMLElement>(".vmx-hotkey-capture__rebind")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(h.root.dataset.capture).toBe("true");
    const chip = h.root.querySelector<HTMLElement>(".vmx-hotkey-capture__chip");
    expect(chip?.textContent).toBe("PRESS KEYS…");
  });

  it("valid combo fires onCapture with wire-form string and exits capture", () => {
    const onCapture = vi.fn();
    const h = mount({ value: "cmd+shift+m", onCapture });
    h.beginCapture();
    document.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "k",
        altKey: true,
        shiftKey: true,
      }),
    );
    expect(onCapture).toHaveBeenCalledWith("alt+shift+k");
    expect(h.root.dataset.capture).toBe("false");
  });

  it("reserved combo surfaces inline error and stays in capture mode", () => {
    const onCapture = vi.fn();
    const h = mount({ value: "cmd+shift+m", onCapture });
    h.beginCapture();
    document.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "q",
        metaKey: true,
      }),
    );
    expect(onCapture).not.toHaveBeenCalled();
    expect(h.root.dataset.capture).toBe("true");
    expect(h.root.dataset.error).toBe("true");
    const err = h.root.querySelector<HTMLElement>(".vmx-hotkey-capture__error");
    expect(err?.textContent ?? "").toMatch(/reserved/i);
  });

  it("Escape during capture cancels (does not fire onCapture)", () => {
    const onCapture = vi.fn();
    const h = mount({ value: "cmd+shift+m", onCapture });
    h.beginCapture();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(onCapture).not.toHaveBeenCalled();
    expect(h.root.dataset.capture).toBe("false");
  });

  it("modifier-only press during capture does NOT fire", () => {
    const onCapture = vi.fn();
    const h = mount({ value: "cmd+shift+m", onCapture });
    h.beginCapture();
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Shift", shiftKey: true }),
    );
    expect(onCapture).not.toHaveBeenCalled();
    expect(h.root.dataset.capture).toBe("true");
  });

  it("setError surfaces a Rust-side rejection", () => {
    const h = mount({ value: "cmd+shift+m", onCapture: vi.fn() });
    h.setError("unparseable combo");
    expect(h.root.dataset.error).toBe("true");
    const err = h.root.querySelector<HTMLElement>(".vmx-hotkey-capture__error");
    expect(err?.textContent).toBe("unparseable combo");
  });

  it("setValue updates the chip without firing onCapture", () => {
    const onCapture = vi.fn();
    const h = mount({ value: "cmd+shift+m", onCapture });
    h.setValue("alt+shift+k");
    expect(onCapture).not.toHaveBeenCalled();
    // Chip text now reflects new value (in some platform-pretty form).
    const chip = h.root.querySelector<HTMLElement>(".vmx-hotkey-capture__chip");
    expect(chip?.textContent ?? "").toMatch(/K$/i);
  });
});
