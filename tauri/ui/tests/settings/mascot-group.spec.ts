/* Phase 13-03 — Settings drawer MASCOT group spec (Plan 13-03 Task 2).
 *
 * Filed under tests/settings/ per vitest.config.ts glob (the plan's nominal
 * path was src/settings/components/mascot-group.test.ts — that pattern is
 * outside the default test glob so vitest would skip it; using *.spec.ts
 * keeps the suite picking it up automatically).
 *
 * Asserts:
 *   1. Group renders with title "MASCOT" + 1 toggle + 3 mood pills
 *   2. Active pill mirrors SessionState.settings.mood
 *   3. Active toggle segment mirrors SessionState.settings.click_through
 *   4. Clicking a mood pill emits ipc.settings.set { field: 'mood', ... }
 *   5. Toggling click-through invokes set_mascot_click_through Tauri command
 *      AND emits ipc.settings.set { field: 'click_through', ... }
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// vi.mock is hoisted to the top of the file by vitest's transformer, which
// means any `const` defined outside the factory is unreachable. Use
// `vi.hoisted` so the mock fn is also hoisted alongside the vi.mock call —
// this gives the spec a stable reference to inspect call args.
const { invokeMock } = vi.hoisted(() => {
  return {
    invokeMock: vi.fn(
      async (_cmd: string, _args?: Record<string, unknown>) => {},
    ),
  };
});

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

import {
  MascotGroup,
  renderMascotGroup,
} from "../../src/settings/components/mascot-group.js";
import {
  _resetSessionStateForTests,
  getSessionState,
} from "../../src/session/state.js";

// Cast through unknown to set the writable session-state slice from the
// test side. The session state is mutated by the bridge in prod; tests
// reach in via the underlying singleton.
function setMood(mood: "hype-man" | "teacher" | "coach"): void {
  const cur = getSessionState();
  (cur as { settings: { mood: typeof mood } }).settings.mood = mood;
}

function setClickThrough(value: boolean): void {
  const cur = getSessionState();
  (cur as { settings: { click_through: boolean } }).settings.click_through =
    value;
}

beforeEach(() => {
  _resetSessionStateForTests();
  invokeMock.mockClear();
  document.body.replaceChildren();
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("MascotGroup rendering", () => {
  it("renders the group with MASCOT title + 1 toggle + 3 mood pills", () => {
    const group = renderMascotGroup();
    document.body.append(group);
    // Group header text comes from the shared SettingsGroup wrapper.
    expect(
      group.querySelector(".vmx-settings-group__header")?.textContent,
    ).toContain("MASCOT");
    // One rocker (click-through), one mood-pills container with 3 pills.
    expect(group.querySelectorAll(".vmx-rocker").length).toBe(1);
    const pills = group.querySelectorAll(".vmx-mascot-pill");
    expect(pills.length).toBe(3);
    const labels = Array.from(pills).map((p) => p.textContent);
    expect(labels).toEqual(["HYPE-MAN", "TEACHER", "COACH"]);
  });

  it("MascotGroup public alias matches renderMascotGroup output shape", () => {
    const a = MascotGroup();
    document.body.append(a);
    expect(a.getAttribute("data-component")).toBe("mascot-group");
  });

  it("reflects SessionState.settings.mood — teacher active pill, others inactive", () => {
    setMood("teacher");
    const group = renderMascotGroup();
    document.body.append(group);
    const pills = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-mascot-pill"),
    );
    const active = pills.find((p) => p.dataset.id === "teacher");
    const others = pills.filter((p) => p.dataset.id !== "teacher");
    expect(active?.dataset.active).toBe("true");
    for (const p of others) {
      expect(p.dataset.active).toBe("false");
    }
  });

  it("reflects SessionState.settings.click_through=true on the ON rocker segment", () => {
    setClickThrough(true);
    const group = renderMascotGroup();
    document.body.append(group);
    const segs = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-rocker__seg"),
    );
    const onSeg = segs.find((s) => s.dataset.id === "on");
    const offSeg = segs.find((s) => s.dataset.id === "off");
    expect(onSeg?.dataset.active).toBe("true");
    expect(offSeg?.dataset.active).toBe("false");
  });

  it("default state: click_through=false → OFF segment active, mood=hype-man → HYPE-MAN pill active", () => {
    const group = renderMascotGroup();
    document.body.append(group);
    const offSeg = group.querySelector<HTMLElement>(
      '.vmx-rocker__seg[data-id="off"]',
    );
    expect(offSeg?.dataset.active).toBe("true");
    const hypePill = group.querySelector<HTMLElement>(
      '.vmx-mascot-pill[data-id="hype-man"]',
    );
    expect(hypePill?.dataset.active).toBe("true");
  });
});

describe("MascotGroup IPC wiring", () => {
  it("clicking the 'coach' pill emits ipc.settings.set { field: 'mood', value: 'coach' }", async () => {
    const group = renderMascotGroup();
    document.body.append(group);
    const coachPill = group.querySelector<HTMLButtonElement>(
      '.vmx-mascot-pill[data-id="coach"]',
    );
    expect(coachPill).toBeTruthy();
    coachPill!.click();
    // emitIpc → invoke('forward_ipc_to_sidecar', { message: { type, ts, payload } })
    // We can't await the void promise inline; flush the microtask queue.
    await new Promise<void>((r) => setTimeout(r, 0));
    const calls = invokeMock.mock.calls.filter(
      (c) => c[0] === "forward_ipc_to_sidecar",
    );
    expect(calls.length).toBeGreaterThanOrEqual(1);
    const msg = (calls[calls.length - 1]?.[1] as { message: unknown }).message as {
      type: string;
      payload: { field: string; value: unknown };
    };
    expect(msg.type).toBe("ipc.settings.set");
    expect(msg.payload).toEqual({ field: "mood", value: "coach" });
  });

  it("clicking the already-active pill does NOT fire emitIpc (idempotency)", async () => {
    const group = renderMascotGroup();
    document.body.append(group);
    const hypePill = group.querySelector<HTMLButtonElement>(
      '.vmx-mascot-pill[data-id="hype-man"]',
    );
    hypePill!.click();
    await new Promise<void>((r) => setTimeout(r, 0));
    expect(invokeMock).not.toHaveBeenCalled();
  });

  it("toggling click-through ON invokes set_mascot_click_through(true) AND emits ipc.settings.set { field: 'click_through', value: true }", async () => {
    const group = renderMascotGroup();
    document.body.append(group);
    const onSeg = group.querySelector<HTMLButtonElement>(
      '.vmx-rocker__seg[data-id="on"]',
    );
    expect(onSeg).toBeTruthy();
    onSeg!.click();
    await new Promise<void>((r) => setTimeout(r, 0));

    // Two invokes: one is the Tauri set_mascot_click_through command, the
    // other is emitIpc → forward_ipc_to_sidecar.
    const tauriCall = invokeMock.mock.calls.find(
      (c) => c[0] === "set_mascot_click_through",
    );
    expect(tauriCall).toBeTruthy();
    expect(tauriCall![1]).toEqual({ enabled: true });

    const ipcCall = invokeMock.mock.calls.find(
      (c) => c[0] === "forward_ipc_to_sidecar",
    );
    expect(ipcCall).toBeTruthy();
    const msg = (ipcCall![1] as { message: unknown }).message as {
      type: string;
      payload: { field: string; value: unknown };
    };
    expect(msg.type).toBe("ipc.settings.set");
    expect(msg.payload).toEqual({ field: "click_through", value: true });
  });

  it("toggling click-through OFF invokes set_mascot_click_through(false) AND emits ipc.settings.set { field: 'click_through', value: false }", async () => {
    setClickThrough(true);
    const group = renderMascotGroup();
    document.body.append(group);
    const offSeg = group.querySelector<HTMLButtonElement>(
      '.vmx-rocker__seg[data-id="off"]',
    );
    offSeg!.click();
    await new Promise<void>((r) => setTimeout(r, 0));
    const tauriCall = invokeMock.mock.calls.find(
      (c) => c[0] === "set_mascot_click_through",
    );
    expect(tauriCall![1]).toEqual({ enabled: false });
  });
});

describe("MascotGroup style guard (no hex literals)", () => {
  it("emitted CSS contains zero hex outside rgba()/var() — frontend-enforcement", () => {
    renderMascotGroup(); // ensures registerStyle ran
    const styleEl = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-mascot-group"]',
    );
    expect(styleEl).toBeTruthy();
    const css = styleEl!.textContent ?? "";
    const hexMatches = css.match(/#[0-9a-fA-F]{3,8}/g) ?? [];
    expect(hexMatches).toEqual([]);
  });
});
