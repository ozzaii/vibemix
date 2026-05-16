/* Phase 15 Plan 04 Task 1 — recording-row.ts vitest jsdom coverage.
 *
 * Covers UI-SPEC §Row anatomy + §Row expanded state + §prefers-reduced-motion
 * + §Component Contracts (RecordingRowHandle). The 14 tests below are
 * the verbatim acceptance set declared in 15-04-PLAN.md §Task 1 §behavior.
 *
 * Mocking strategy:
 *   - `@tauri-apps/api/core` → `convertFileSrc(path) => "asset://localhost" + path`
 *   - `../../ipc/client` → `sendIpcRequest` is a per-test-controlled Promise so
 *     loading + render + error transcript states can be asserted deterministically.
 *
 * Vitest env: jsdom (routed via vitest.config.ts environmentMatchGlobs).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
}));

// Hoisted handles so each test can drive the in-flight promise.
type EventsPayload = { session_dir: string; events: Array<Record<string, unknown>> };
let pendingResolve: ((payload: { type: string; ts: string; payload: EventsPayload }) => void) | null = null;
let pendingReject: ((err: Error) => void) | null = null;
let lastRequest: { type: string; payload: Record<string, unknown> } | null = null;

// Plan 15-03 Task 2 mocks for the new shell-out wrappers; spy fns let the
// reveal/open-external tests assert the exact `session_dir` passed through.
const revealInOSMock = vi.fn(async (_session_dir: string) => undefined);
const openInputWavMock = vi.fn(async (_session_dir: string) => undefined);

vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn(
    (requestType: string, requestPayload: Record<string, unknown>) => {
      lastRequest = { type: requestType, payload: requestPayload };
      return new Promise((resolve, reject) => {
        pendingResolve = resolve as typeof pendingResolve;
        pendingReject = reject;
      });
    },
  ),
  revealInOS: (sd: string) => revealInOSMock(sd),
  openInputWav: (sd: string) => openInputWavMock(sd),
}));

import { renderRecordingRow } from "./recording-row.js";

const baseSummary = {
  session_dir: "20260513-210410",
  started_at_iso: "2026-05-13T21:04:10+02:00",
  duration_s: 5040, // 1h 24m
  event_count: 38,
  bytes_total: 12345678,
  crashed: false,
};

let matchMediaReduced = false;

beforeEach(() => {
  pendingResolve = null;
  pendingReject = null;
  lastRequest = null;
  matchMediaReduced = false;
  revealInOSMock.mockClear();
  openInputWavMock.mockClear();
  // jsdom does not implement matchMedia by default; stub a controllable one.
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: matchMediaReduced && query.includes("prefers-reduced-motion"),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    }),
  });
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

async function flushMicrotasks(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

describe("recording-row — Test 1: root contract", () => {
  it("returns a 44px min-height root with aria-expanded='false' initially", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);

    expect(root.classList.contains("vmx-rec-row")).toBe(true);
    expect(root.getAttribute("aria-expanded")).toBe("false");
    // The 44px min-height is declared in the registered <style> block.
    const styleBlock = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-rec-row"]',
    );
    expect(styleBlock?.textContent ?? "").toContain("min-height: 44px");
  });
});

describe("recording-row — Test 2: center cell duration format", () => {
  it("renders '1h 24m · 38 events' for 5040s + 38 events", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const meta = root.querySelector<HTMLElement>(".vmx-rec-row__meta");
    expect(meta?.textContent ?? "").toContain("1h 24m");
    expect(meta?.textContent ?? "").toContain("38 events");
  });

  it("renders '48m · 22 events' for < 1h sessions", () => {
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, duration_s: 2880, event_count: 22 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const meta = root.querySelector<HTMLElement>(".vmx-rec-row__meta");
    expect(meta?.textContent ?? "").toContain("48m");
    expect(meta?.textContent ?? "").toContain("22 events");
    expect(meta?.textContent ?? "").not.toContain("h");
  });

  it("renders '1h 30m' for exactly 5400s", () => {
    const { root } = renderRecordingRow({
      summary: { ...baseSummary, duration_s: 5400, event_count: 50 },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const meta = root.querySelector<HTMLElement>(".vmx-rec-row__meta");
    expect(meta?.textContent ?? "").toContain("1h 30m");
  });
});

describe("recording-row — Test 3: left cell timestamp format", () => {
  it("renders '2026-05-13 21:04' from started_at_iso in JetBrains Mono", () => {
    const { root } = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(root);
    const ts = root.querySelector<HTMLElement>(".vmx-rec-row__ts");
    expect(ts?.textContent).toBe("2026-05-13 21:04");
    // The CSS rule (in the registered style block) maps the class to --type-mono.
    const styleBlock = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-rec-row"]',
    );
    expect(styleBlock?.textContent ?? "").toMatch(/\.vmx-rec-row__ts[^}]*font-family:\s*var\(--type-mono\)/);
  });
});

describe("recording-row — Test 4: setExpanded(true) mounts audio with asset:// URL", () => {
  it("creates an <audio> with the convertFileSrc-mapped src and aria-expanded='true'", () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
      absoluteWavPathResolver: (sd) => `/recordings/${sd}/voice.wav`,
    });
    document.body.append(handle.root);

    handle.setExpanded(true);

    const audio = handle.root.querySelector<HTMLAudioElement>("audio");
    expect(audio).not.toBeNull();
    expect(audio?.getAttribute("src")).toBe(
      "asset://localhost/recordings/20260513-210410/voice.wav",
    );
    expect(handle.root.getAttribute("aria-expanded")).toBe("true");
    expect(handle.root.dataset.open).toBe("true");
  });
});

describe("recording-row — Test 5: setExpanded(false) tears down audio + transcript", () => {
  it("removes audio src + calls load() AND detaches the transcript node", async () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setExpanded(true);
    const audioBefore = handle.root.querySelector<HTMLAudioElement>("audio");
    expect(audioBefore).not.toBeNull();
    // jsdom does not implement HTMLMediaElement.load — patch it before collapse.
    const loadSpy = vi.fn();
    if (audioBefore) (audioBefore as unknown as { load: () => void }).load = loadSpy;

    // Resolve the in-flight events request so the transcript node is mounted —
    // then collapse should detach it.
    pendingResolve?.({
      type: "ipc.recordings.events_result",
      ts: new Date().toISOString(),
      payload: { session_dir: baseSummary.session_dir, events: [] },
    });
    await flushMicrotasks();

    handle.setExpanded(false);

    // The <audio> element may have been removed entirely OR kept with null src;
    // either way the row is "torn down" — assert decoder release semantics.
    const audioAfter = handle.root.querySelector<HTMLAudioElement>("audio");
    if (audioAfter !== null) {
      expect(audioAfter.getAttribute("src")).toBeNull();
    }
    expect(loadSpy).toHaveBeenCalled();

    const transcriptAfter = handle.root.querySelector(".vmx-rec-row__transcript");
    expect(transcriptAfter).toBeNull();
    expect(handle.root.getAttribute("aria-expanded")).toBe("false");
    expect(handle.root.dataset.open).toBe("false");
  });
});

describe("recording-row — Test 6: delete button fires onDelete (only)", () => {
  it("clicking delete calls onDelete and does NOT call onToggle", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete,
    });
    document.body.append(handle.root);

    const deleteBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="delete"]',
    );
    expect(deleteBtn).not.toBeNull();
    deleteBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onToggle).not.toHaveBeenCalled();
  });
});

describe("recording-row — Test 7: row body click fires onToggle", () => {
  it("clicking the row meta cell calls onToggle exactly once", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete,
    });
    document.body.append(handle.root);

    const meta = handle.root.querySelector<HTMLElement>(".vmx-rec-row__meta");
    meta!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onDelete).not.toHaveBeenCalled();
  });
});

describe("recording-row — Test 8: crashed session LED prefix", () => {
  it("renders a led-warn dot + data-crashed='true' when summary.crashed", () => {
    const handle = renderRecordingRow({
      summary: { ...baseSummary, crashed: true },
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    expect(handle.root.dataset.crashed).toBe("true");
    const led = handle.root.querySelector<HTMLElement>(".vmx-rec-row__crashed-led");
    expect(led).not.toBeNull();
  });

  it("omits the LED dot for healthy sessions", () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    expect(handle.root.dataset.crashed).toBe("false");
    const led = handle.root.querySelector<HTMLElement>(".vmx-rec-row__crashed-led");
    expect(led).toBeNull();
  });
});

describe("recording-row — Test 9: keyboard support", () => {
  it("Enter on the focused row root calls onToggle", () => {
    const onToggle = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.root.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("Enter on the focused delete button calls onDelete (only)", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete,
    });
    document.body.append(handle.root);

    const deleteBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="delete"]',
    );
    deleteBtn!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onToggle).not.toHaveBeenCalled();
  });
});

describe("recording-row — Test 10: prefers-reduced-motion override", () => {
  it("uses display-toggle CSS rule when reduce is matched", () => {
    matchMediaReduced = true;
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);
    handle.setExpanded(true);

    // The CSS includes the @media override; verify the rule text is present.
    const styleBlock = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-rec-row"]',
    );
    expect(styleBlock?.textContent ?? "").toMatch(
      /@media\s*\(prefers-reduced-motion:\s*reduce\)/,
    );
    expect(styleBlock?.textContent ?? "").toMatch(/transition:\s*none/);
  });
});

describe("recording-row — Test 11: transcript loading state", () => {
  it("renders 'Loading events…' immediately after setExpanded(true)", () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setExpanded(true);
    const transcript = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-row__transcript",
    );
    expect(transcript).not.toBeNull();
    expect(transcript!.children.length).toBe(1);
    const loadingChild = transcript!.firstElementChild as HTMLElement;
    expect(loadingChild.className).toContain("vmx-rec-evt--dim");
    expect(loadingChild.textContent).toBe("Loading events…");
    // IPC request was fired with the correct payload.
    expect(lastRequest?.type).toBe("ipc.recordings.events");
    expect(lastRequest?.payload).toEqual({ session_dir: baseSummary.session_dir });
  });
});

describe("recording-row — Test 12: transcript render with 4 events", () => {
  it("renders bold/dim children + [+M:SS] prefixes per event-kind map", async () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setExpanded(true);

    pendingResolve?.({
      type: "ipc.recordings.events_result",
      ts: new Date().toISOString(),
      payload: {
        session_dir: baseSummary.session_dir,
        events: [
          { t: 0.0, kind: "session_start" },
          { t: 5.2, kind: "ai_text", text: "Nice transition." },
          { t: 12.4, kind: "controller_move", control: "filter_a", value: 0.42 },
          { t: 125.0, kind: "trigger", reason: "phase_change" },
        ],
      },
    });
    await flushMicrotasks();

    const transcript = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-row__transcript",
    );
    expect(transcript).not.toBeNull();
    const children = Array.from(transcript!.children) as HTMLElement[];
    expect(children.length).toBe(4);

    // session_start → --dim, label "session start"
    expect(children[0]!.className).toContain("vmx-rec-evt--dim");
    expect(children[0]!.textContent).toContain("session start");
    expect(children[0]!.textContent).toContain("[+0:00]");

    // ai_text → --bold, label "Nice transition."
    expect(children[1]!.className).toContain("vmx-rec-evt--bold");
    expect(children[1]!.textContent).toContain("Nice transition.");
    expect(children[1]!.textContent).toContain("[+0:05]");

    // controller_move → --dim, label "filter_a 0.42"
    expect(children[2]!.className).toContain("vmx-rec-evt--dim");
    expect(children[2]!.textContent).toContain("filter_a");
    expect(children[2]!.textContent).toContain("0.42");
    expect(children[2]!.textContent).toContain("[+0:12]");

    // trigger → --bold, label "trigger: phase_change"
    expect(children[3]!.className).toContain("vmx-rec-evt--bold");
    expect(children[3]!.textContent).toContain("trigger: phase_change");
    expect(children[3]!.textContent).toContain("[+2:05]");

    // Amber-22 border-left rule is in the registered style block.
    const styleBlock = document.querySelector<HTMLStyleElement>(
      'style[data-scope="vmx-rec-row"]',
    );
    expect(styleBlock?.textContent ?? "").toContain(
      "border-left: 1px solid var(--amber-22)",
    );

    // The relative-timestamp span uses --type-mono per UI-SPEC.
    expect(styleBlock?.textContent ?? "").toMatch(
      /\.vmx-rec-evt__ts[^}]*font-family:\s*var\(--type-mono\)/,
    );
  });
});

describe("recording-row — Test 13: transcript error state", () => {
  it("renders 'Events unavailable.' on sendIpcRequest rejection", async () => {
    const consoleErr = vi.spyOn(console, "error").mockImplementation(() => {});
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setExpanded(true);
    pendingReject?.(new Error("ipc timeout: no events_result within 10000ms"));
    await flushMicrotasks();

    const transcript = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-row__transcript",
    );
    expect(transcript).not.toBeNull();
    expect(transcript!.children.length).toBe(1);
    const errorChild = transcript!.firstElementChild as HTMLElement;
    expect(errorChild.className).toContain("vmx-rec-evt--dim");
    expect(errorChild.textContent).toBe("Events unavailable.");

    // No uncaught console.error spew.
    expect(consoleErr).not.toHaveBeenCalled();
    consoleErr.mockRestore();
  });
});

describe("recording-row — Test 14: HTML escape via textContent", () => {
  it("renders <script> as literal text without injecting a <script> element", async () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    handle.setExpanded(true);

    pendingResolve?.({
      type: "ipc.recordings.events_result",
      ts: new Date().toISOString(),
      payload: {
        session_dir: baseSummary.session_dir,
        events: [
          { t: 0.0, kind: "ai_text", text: "<script>alert(1)</script>" },
        ],
      },
    });
    await flushMicrotasks();

    const transcript = handle.root.querySelector<HTMLElement>(
      ".vmx-rec-row__transcript",
    );
    expect(transcript).not.toBeNull();
    expect(transcript!.querySelectorAll("script").length).toBe(0);
    expect(transcript!.textContent).toContain("<script>alert(1)</script>");
  });
});

// ---------------------------------------------------------------------------
// Plan 15-03 Task 2 — reveal + open-external action buttons.
// Cluster grew from 64px (replay + delete) to 128px (replay + reveal +
// open-external + delete). Tests below pin the wiring + a11y contract.
// ---------------------------------------------------------------------------

describe("recording-row — Test 15: row renders 5 action buttons in correct order", () => {
  it("emits replay → reveal → open-external → debrief → delete inside the action cluster", () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    const buttons = Array.from(
      handle.root.querySelectorAll<HTMLButtonElement>(
        ".vmx-rec-row__actions .vmx-rec-row__btn",
      ),
    );
    // Plan 29-06 added the Open Debrief button: 4 → 5.
    expect(buttons.length).toBe(5);
    expect(buttons.map((b) => b.dataset.kind)).toEqual([
      "replay",
      "reveal",
      "open-external",
      "debrief",
      "delete",
    ]);
  });
});

describe("recording-row — Test 16: reveal button click invokes revealInOS", () => {
  it("passes the row's session_dir to the wrapper, stops bubbling, no onToggle/onDelete", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete,
    });
    document.body.append(handle.root);

    const revealBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="reveal"]',
    );
    expect(revealBtn).not.toBeNull();
    revealBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(revealInOSMock).toHaveBeenCalledTimes(1);
    expect(revealInOSMock).toHaveBeenCalledWith(baseSummary.session_dir);
    expect(onToggle).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
  });
});

describe("recording-row — Test 17: open-external button click invokes openInputWav", () => {
  it("passes the row's session_dir to the wrapper, stops bubbling, no onToggle/onDelete", () => {
    const onToggle = vi.fn();
    const onDelete = vi.fn();
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle,
      onDelete,
    });
    document.body.append(handle.root);

    const openExtBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="open-external"]',
    );
    expect(openExtBtn).not.toBeNull();
    openExtBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(openInputWavMock).toHaveBeenCalledTimes(1);
    expect(openInputWavMock).toHaveBeenCalledWith(baseSummary.session_dir);
    expect(onToggle).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
  });
});

describe("recording-row — Test 18: aria-labels for reveal + open-external", () => {
  it("matches the documented a11y format including formatted timestamp", () => {
    const handle = renderRecordingRow({
      summary: baseSummary,
      onToggle: vi.fn(),
      onDelete: vi.fn(),
    });
    document.body.append(handle.root);

    const revealBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="reveal"]',
    );
    const openExtBtn = handle.root.querySelector<HTMLButtonElement>(
      '.vmx-rec-row__btn[data-kind="open-external"]',
    );
    expect(revealBtn?.getAttribute("aria-label")).toBe(
      "reveal session 2026-05-13 21:04 in Finder",
    );
    expect(openExtBtn?.getAttribute("aria-label")).toBe(
      "open input.wav for session 2026-05-13 21:04 in default app",
    );
  });
});
