/**
 * picker.ts — dropdown-row component contract.
 *
 * Pins the 2026-05-25 dead-dropdown fix: selecting an option must update
 * the row's displayed label + the selected-marks OPTIMISTICALLY, the
 * instant the choice is made — the picker analog of rocker.setRockerActive.
 *
 * Before the fix, picker onChange fired but the row label stayed frozen
 * until the sidecar round-tripped ipc.settings.state. In dev (no live
 * session) that echo never arrives, so every dropdown read as dead even
 * though the handler ran. This test guarantees the visible response.
 *
 * jsdom env (routed by vitest.config.ts `src/session/components/*.test.ts`
 * glob), pure DOM assertions against the rendered HTMLElement.
 */
import { describe, test, expect, vi } from "vitest";
import { disposePicker, renderPicker, type PickerOption } from "./picker.js";

const OPTS: PickerOption[] = [
  { id: "house", label: "house" },
  { id: "techno", label: "techno" },
  { id: "dnb", label: "dnb" },
];

function mount(onChange = vi.fn()): {
  root: HTMLElement;
  row: HTMLButtonElement;
  opts: HTMLButtonElement[];
  label: HTMLElement;
  onChange: ReturnType<typeof vi.fn>;
} {
  const root = renderPicker({
    label: "GENRE",
    value: "house",
    options: OPTS,
    onChange,
  });
  document.body.append(root);
  return {
    root,
    row: root.querySelector(".vmx-picker__row") as HTMLButtonElement,
    opts: Array.from(
      root.querySelectorAll<HTMLButtonElement>(".vmx-picker__opt"),
    ),
    label: root.querySelector(".vmx-picker__label") as HTMLElement,
    onChange,
  };
}

describe("picker — optimistic select (dead-dropdown fix)", () => {
  test("row opens on trigger click", () => {
    const { root, row } = mount();
    expect(root.dataset.open).toBe("false");
    row.click();
    expect(root.dataset.open).toBe("true");
  });

  test("selecting an option updates the row label immediately", () => {
    const { row, opts, label } = mount();
    expect(label.textContent).toBe("house");
    row.click();
    opts[1]!.click(); // techno
    expect(label.textContent).toBe("techno");
  });

  test("selecting an option flips data-selected to the chosen option", () => {
    const { row, opts } = mount();
    row.click();
    opts[2]!.click(); // dnb
    expect(opts[2]!.dataset.selected).toBe("true");
    expect(opts[2]!.getAttribute("aria-selected")).toBe("true");
    expect(opts[0]!.dataset.selected).toBe("false");
    expect(opts[1]!.dataset.selected).toBe("false");
  });

  test("onChange fires with the option id and the list closes", () => {
    const { root, row, opts, onChange } = mount();
    row.click();
    opts[1]!.click();
    expect(onChange).toHaveBeenCalledWith("techno");
    expect(root.dataset.open).toBe("false");
  });

  test("initial selected option reflects the value prop", () => {
    const { opts } = mount();
    expect(opts[0]!.dataset.selected).toBe("true"); // house
    expect(opts[1]!.dataset.selected).toBe("false");
  });

  test("dispose closes the popover and removes global listeners", () => {
    const documentRemove = vi.spyOn(document, "removeEventListener");
    const windowRemove = vi.spyOn(window, "removeEventListener");
    const { root, row } = mount();

    row.click();
    expect(root.dataset.open).toBe("true");
    disposePicker(root);

    expect(root.dataset.open).toBe("false");
    expect(documentRemove).toHaveBeenCalledWith("click", expect.any(Function));
    expect(windowRemove).toHaveBeenCalledWith("scroll", expect.any(Function), true);
    expect(windowRemove).toHaveBeenCalledWith("resize", expect.any(Function));

    documentRemove.mockRestore();
    windowRemove.mockRestore();
  });
});
