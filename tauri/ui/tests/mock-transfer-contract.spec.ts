/**
 * @vitest-environment jsdom
 *
 * Pins the production anchors used when a static mockup is transferred into
 * the live Tauri surfaces. A mock can change the look, but these data-wire
 * mounts must stay present and unique so real WS/IPC wiring remains attached.
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
  invoke: vi.fn(async () => undefined),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

vi.mock("../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async () => undefined),
  sendIpcRequest: vi.fn(() => new Promise(() => undefined)),
  subscribeIpc: vi.fn(async () => () => {}),
}));

import {
  ACTIVE_MOCK_ITERATION_DIR,
  ACTIVE_MOCK_ITERATION_INDEX,
  ACTIVE_MOCK_ITERATION_TEMPLATE,
  MOCK_TRANSFER_CONTRACT,
  MOCK_TRANSFER_RUNTIME_CONTRACT,
  SETTINGS_GROUP_WIRES,
  SETTINGS_PERSONA_CONTROL_WIRES,
  wireSelector,
  type MockTransferSurface,
  type MockTransferRuntimeSurface,
} from "../src/mock-transfer/contract.js";
import { mountSessionLayout } from "../src/session/SessionLayout.js";
import { mountDebriefDock } from "../src/shell/DebriefDock.js";
import {
  _resetDrawerForTests,
  mountSettingsDrawer,
  unmountSettingsDrawer,
} from "../src/settings/SettingsDrawer.js";
import { renderSettingsGroup } from "../src/settings/components/group.js";

const TAURI_UI_ROOT = resolve(__dirname, "..");
const REPO_ROOT = resolve(TAURI_UI_ROOT, "..", "..");
const SESSION_RUNTIME_PRODUCER_FILES = [
  "src/session/render-loop.ts",
  "src/session/ws-bridge.ts",
  "src/session/quit-guard.ts",
  "src/session/session-shortcuts.ts",
  "src/session/tray-mood.ts",
] as const;
const SETTINGS_RUNTIME_PRODUCER_FILES = [
  "src/settings/SettingsDrawer.ts",
  "src/settings/components/help-group.ts",
  "src/settings/components/library-panel.ts",
  "src/settings/components/learn-group.ts",
  "src/settings/components/mascot-group.ts",
  "src/settings/components/performance-group.ts",
  "src/settings/components/profile-panel.ts",
  "src/settings/components/recording-row.ts",
  "src/settings/components/staleness-banner.ts",
] as const;
const SHELL_DEBRIEF_RUNTIME_PRODUCER_FILES = [
  "src/shell/DebriefDock.ts",
] as const;
const STATIC_SURFACE_PRODUCER_FILES: Partial<
  Record<MockTransferSurface["surface"], readonly string[]>
> = {
  library: ["src/library/api.ts", "src/library/index.ts"],
  pill: ["src/pill/index.ts"],
  debrief: [
    "src/debrief/ws-client.ts",
    "src/debrief/debrief-window.ts",
    "src/debrief/components/ear-test-toggle.ts",
  ],
  overlay: ["src/overlay/overlay-highlight.ts", "src/overlay/overlay-runtime.ts"],
  mascot: ["src/mascot/index.ts", "src/mascot/event-dispatcher.ts"],
};

const IPC_LITERAL_PATTERN = /["'](ipc\.[a-zA-Z0-9_.-]+)["']/g;
const TAURI_INVOKE_PATTERN =
  /\b(?:invoke|invokeFn|localInvoke|invokeTauri)(?:<[^>]+>)?\(\s*["']([^"']+)["']/g;
const TAURI_LISTEN_PATTERN =
  /\b(?:tauriListen|event\.listen|listen)(?:<[^>]+>)?\(\s*["']([^"']+)["']/g;
const TAURI_EMIT_PATTERN =
  /\b(?:event\.emit|emit)(?:<[^>]+>)?\(\s*["']([^"']+)["']/g;
const LIBRARY_EVENT_PATTERN =
  /["'](library:\/\/(?:embed-progress|embed-done|model-progress))["']/g;
const ACTION_PRODUCER_PATTERN =
  /import\s+\{[^}]*\b(?:invoke|invokeTauri|emit|listen|tauriListen|emitIpc|sendIpcRequest|subscribeIpc|sendSettings|sendMute|openInputWav|revealInOS)\b[^}]*\}\s+from\s+["'][^"']+["']|\b(?:invoke|invokeFn|localInvoke|invokeTauri|emitIpc|sendIpcRequest|subscribeIpc|sendSettings|sendMute|openInputWav|revealInOS|tauriListen)\s*\(|\bevent\.(?:listen|emit)\s*\(/g;

function parseHtml(file: string): Document {
  const src = readFileSync(resolve(TAURI_UI_ROOT, file), "utf-8");
  return new DOMParser().parseFromString(src, "text/html");
}

function readRepoFile(file: string): string {
  return readFileSync(resolve(REPO_ROOT, file), "utf-8");
}

function activeMockIterationFiles(): string[] {
  return readdirSync(resolve(REPO_ROOT, ACTIVE_MOCK_ITERATION_DIR))
    .filter((name) => /^m\d{2}-.+\.html$/.test(name))
    .sort();
}

function sourceTreeFiles(root: string): string[] {
  const absRoot = resolve(TAURI_UI_ROOT, root);
  const out: string[] = [];

  function walk(absDir: string, relDir: string): void {
    for (const entry of readdirSync(absDir, { withFileTypes: true })) {
      const abs = resolve(absDir, entry.name);
      const rel = `${relDir}/${entry.name}`;
      if (entry.isDirectory()) {
        walk(abs, rel);
        continue;
      }
      if (
        entry.isFile()
        && rel.endsWith(".ts")
        && !rel.endsWith(".test.ts")
        && !rel.endsWith(".spec.ts")
        && !rel.includes("/__tests__/")
      ) {
        out.push(rel);
      }
    }
  }

  walk(absRoot, root);
  return out.sort();
}

function stripTsComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

function actionProducerFiles(root: string): string[] {
  return sourceTreeFiles(root).filter((file) => {
    const src = stripTsComments(readFileSync(resolve(TAURI_UI_ROOT, file), "utf-8"));
    ACTION_PRODUCER_PATTERN.lastIndex = 0;
    return ACTION_PRODUCER_PATTERN.test(src);
  });
}

function sourceLiterals(
  files: readonly string[],
  pattern: RegExp,
): string[] {
  const values = new Set<string>();
  for (const file of files) {
    const src = readFileSync(resolve(TAURI_UI_ROOT, file), "utf-8");
    pattern.lastIndex = 0;
    for (const match of src.matchAll(pattern)) {
      if (match[1]) values.add(match[1]);
    }
  }
  return [...values].sort();
}

function staticContractChannels(surfaceName: MockTransferSurface["surface"]): Set<string> {
  const surface = MOCK_TRANSFER_CONTRACT.find((entry) => entry.surface === surfaceName);
  expect(surface, `${surfaceName} static surface should be contracted`).toBeTruthy();
  return new Set([...(surface?.inbound ?? []), ...(surface?.outbound ?? [])]);
}

function runtimeContractChannels(surfaceName: MockTransferRuntimeSurface["surface"]): Set<string> {
  const surface = MOCK_TRANSFER_RUNTIME_CONTRACT.find((entry) => entry.surface === surfaceName);
  expect(surface, `${surfaceName} runtime surface should be contracted`).toBeTruthy();
  return new Set([...(surface?.inbound ?? []), ...(surface?.outbound ?? [])]);
}

function rustRegisteredCommands(): Set<string> {
  const main = readRepoFile("tauri/src-tauri/src/main.rs");
  const handler = main.match(/generate_handler!\s*\[([\s\S]*?)\]\)/)?.[1] ?? "";
  const commands = new Set<string>();
  for (const match of handler.matchAll(/\b(?:[a-z_]+::)+([a-z_][a-z0-9_]*)\b/g)) {
    if (match[1]) commands.add(match[1]);
  }
  return commands;
}

function contractedTauriCommands(): string[] {
  return [
    ...MOCK_TRANSFER_CONTRACT,
    ...MOCK_TRANSFER_RUNTIME_CONTRACT,
  ]
    .flatMap((surface) => [...surface.outbound])
    .filter((value) => /^[a-z][a-z0-9_]*$/.test(value))
    .filter((value, index, values) => values.indexOf(value) === index)
    .sort();
}

function dataWireValues(doc: Document): string[] {
  return Array.from(doc.querySelectorAll<HTMLElement>("[data-wire]"))
    .map((el) => el.dataset.wire ?? "")
    .filter(Boolean);
}

function mountedDataWireValues(): string[] {
  return Array.from(document.querySelectorAll<HTMLElement>("[data-wire]"))
    .map((el) => el.dataset.wire ?? "")
    .filter(Boolean)
    .sort();
}

function expectedRuntimeWireValues(surface: MockTransferRuntimeSurface): string[] {
  const values = new Set(surface.requiredWires.map((entry) => entry.wire));
  if (surface.surface === "settings") {
    for (const wire of SETTINGS_GROUP_WIRES) {
      values.add(wire);
      values.add(`${wire}.header`);
      values.add(`${wire}.body`);
    }
    for (const wire of SETTINGS_PERSONA_CONTROL_WIRES) {
      values.add(wire);
    }
  }
  return [...values].sort();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function mountRuntimeSurface(surface: MockTransferRuntimeSurface): void {
  document.body.replaceChildren();
  if (surface.surface === "session-runtime") {
    const host = document.createElement("div");
    document.body.append(host);
    mountSessionLayout(host);
    return;
  }
  if (surface.surface === "shell-debrief") {
    mountDebriefDock(document.body);
    return;
  }
  mountSettingsDrawer(document.body);
}

afterEach(() => {
  _resetDrawerForTests();
  document.body.replaceChildren();
});

describe("mock transfer contract", () => {
  it("keeps each contracted static wire mounted exactly once", () => {
    for (const surface of MOCK_TRANSFER_CONTRACT) {
      const doc = parseHtml(surface.productionFile);
      for (const entry of surface.requiredWires) {
        const matches = doc.querySelectorAll(wireSelector(entry.wire));
        expect(
          matches.length,
          `${surface.productionFile} must expose ${entry.wire} (${entry.purpose})`,
        ).toBe(1);
      }
    }
  });

  it("keeps data-wire anchors unique inside each static surface", () => {
    for (const surface of MOCK_TRANSFER_CONTRACT) {
      const wires = dataWireValues(parseHtml(surface.productionFile));
      const duplicates = wires.filter((wire, index) => wires.indexOf(wire) !== index);
      expect(duplicates, `${surface.productionFile} duplicate data-wire anchors`).toEqual([]);
    }
  });

  it("contracts every static data-wire anchor", () => {
    for (const surface of MOCK_TRANSFER_CONTRACT) {
      const contracted = new Set(surface.requiredWires.map((entry) => entry.wire));
      const wires = dataWireValues(parseHtml(surface.productionFile));
      const missing = wires.filter((wire) => !contracted.has(wire));
      expect(
        missing,
        `${surface.productionFile} has uncontracted data-wire anchors`,
      ).toEqual([]);
    }
  });

  it("keeps dynamic wires attached where the runtime creates their nodes", () => {
    for (const surface of MOCK_TRANSFER_CONTRACT) {
      for (const entry of surface.dynamicWires ?? []) {
        const src = readFileSync(resolve(TAURI_UI_ROOT, entry.producerFile), "utf-8");
        const wire = escapeRegExp(entry.wire);
        const pattern = new RegExp(
          `(?:dataset\\.wire\\s*=\\s*["']${wire}["']|setAttribute\\(["']data-wire["']\\s*,\\s*["']${wire}["']\\)|data-wire=["']${wire}["'])`,
        );
        expect(
          src,
          `${entry.producerFile} must create ${entry.wire} (${entry.purpose})`,
        ).toMatch(pattern);
      }
    }
  });

  it("keeps each contracted runtime wire mounted exactly once", () => {
    for (const surface of MOCK_TRANSFER_RUNTIME_CONTRACT) {
      mountRuntimeSurface(surface);

      for (const entry of surface.requiredWires) {
        expect(
          document.querySelectorAll(wireSelector(entry.wire)).length,
          `${surface.productionFile} must expose ${entry.wire} (${entry.purpose})`,
        ).toBe(1);
      }

      unmountSettingsDrawer();
    }
  });

  it("contracts every mounted runtime data-wire anchor", () => {
    for (const surface of MOCK_TRANSFER_RUNTIME_CONTRACT) {
      mountRuntimeSurface(surface);

      const expected = expectedRuntimeWireValues(surface);
      const mounted = mountedDataWireValues();
      expect(
        mounted,
        `${surface.productionFile} mounted uncontracted data-wire anchors`,
      ).toEqual(expected);

      unmountSettingsDrawer();
    }
  });

  it("keeps every live settings group transfer anchor mounted", () => {
    document.body.replaceChildren();
    mountSettingsDrawer(document.body);

    for (const wire of SETTINGS_GROUP_WIRES) {
      expect(
        document.querySelectorAll(wireSelector(wire)).length,
        `settings drawer group ${wire} must mount exactly once`,
      ).toBe(1);
    }
  });

  it("keeps every live persona-control transfer anchor mounted", () => {
    document.body.replaceChildren();
    mountSettingsDrawer(document.body);

    for (const wire of SETTINGS_PERSONA_CONTROL_WIRES) {
      expect(
        document.querySelectorAll(wireSelector(wire)).length,
        `settings persona control ${wire} must mount exactly once`,
      ).toBe(1);
    }
  });

  it("keeps runtime IPC channel lists in sync with production literals", () => {
    const cases: Array<{
      files: readonly string[];
      surface: MockTransferRuntimeSurface["surface"];
    }> = [
      { surface: "session-runtime", files: SESSION_RUNTIME_PRODUCER_FILES },
      { surface: "settings", files: SETTINGS_RUNTIME_PRODUCER_FILES },
      { surface: "shell-debrief", files: SHELL_DEBRIEF_RUNTIME_PRODUCER_FILES },
    ];

    for (const entry of cases) {
      const contracted = runtimeContractChannels(entry.surface);
      const used = [
        ...sourceLiterals(entry.files, IPC_LITERAL_PATTERN),
        ...sourceLiterals(entry.files, TAURI_LISTEN_PATTERN),
        ...sourceLiterals(entry.files, TAURI_EMIT_PATTERN),
      ].filter((value, index, values) => values.indexOf(value) === index);
      const missing = used.filter((channel) => !contracted.has(channel));
      expect(missing, `${entry.surface} missing IPC channels`).toEqual([]);
    }
  });

  it("scans every runtime file that can produce IPC, Tauri commands, or Tauri events", () => {
    const cases = [
      {
        root: "src/session",
        files: SESSION_RUNTIME_PRODUCER_FILES,
        label: "session-runtime",
      },
      { root: "src/settings", files: SETTINGS_RUNTIME_PRODUCER_FILES, label: "settings" },
    ] as const;

    for (const entry of cases) {
      const contracted = new Set<string>(entry.files);
      const producers = actionProducerFiles(entry.root);
      const missing = producers.filter((file) => !contracted.has(file));
      expect(
        missing,
        `${entry.label} producer files missing from mock-transfer channel scan`,
      ).toEqual([]);
    }
  });

  it("scans every static surface file that can produce IPC, Tauri commands, or Tauri events", () => {
    const cases = [
      {
        root: "src/library",
        files: STATIC_SURFACE_PRODUCER_FILES.library ?? [],
        label: "library",
      },
      { root: "src/pill", files: STATIC_SURFACE_PRODUCER_FILES.pill ?? [], label: "pill" },
      {
        root: "src/debrief",
        files: STATIC_SURFACE_PRODUCER_FILES.debrief ?? [],
        label: "debrief",
      },
      {
        root: "src/overlay",
        files: STATIC_SURFACE_PRODUCER_FILES.overlay ?? [],
        label: "overlay",
      },
      {
        root: "src/mascot",
        files: STATIC_SURFACE_PRODUCER_FILES.mascot ?? [],
        label: "mascot",
      },
    ] as const;

    for (const entry of cases) {
      const contracted = new Set<string>(entry.files);
      const producers = actionProducerFiles(entry.root);
      const missing = producers.filter((file) => !contracted.has(file));
      expect(
        missing,
        `${entry.label} producer files missing from mock-transfer channel scan`,
      ).toEqual([]);
    }
  });

  it("keeps static surface IPC/event lists in sync with production literals", () => {
    for (const [surface, files] of Object.entries(STATIC_SURFACE_PRODUCER_FILES)) {
      const contracted = staticContractChannels(surface as MockTransferSurface["surface"]);
      const used = [
        ...sourceLiterals(files, IPC_LITERAL_PATTERN),
        ...sourceLiterals(files, LIBRARY_EVENT_PATTERN),
        ...sourceLiterals(files, TAURI_LISTEN_PATTERN),
        ...sourceLiterals(files, TAURI_EMIT_PATTERN),
      ].filter((value, index, values) => values.indexOf(value) === index);
      const missing = used.filter((channel) => !contracted.has(channel));
      expect(missing, `${surface} missing IPC/event channels`).toEqual([]);
    }
  });

  it("keeps runtime Tauri command lists in sync with production invokes", () => {
    const cases: Array<{
      files: readonly string[];
      surface: MockTransferRuntimeSurface["surface"];
    }> = [
      { surface: "session-runtime", files: SESSION_RUNTIME_PRODUCER_FILES },
      { surface: "settings", files: SETTINGS_RUNTIME_PRODUCER_FILES },
      { surface: "shell-debrief", files: SHELL_DEBRIEF_RUNTIME_PRODUCER_FILES },
    ];

    for (const entry of cases) {
      const contracted = runtimeContractChannels(entry.surface);
      const used = sourceLiterals(entry.files, TAURI_INVOKE_PATTERN);
      const missing = used.filter((command) => !contracted.has(command));
      expect(missing, `${entry.surface} missing Tauri commands`).toEqual([]);
    }
  });

  it("keeps static surface Tauri command lists in sync with production invokes", () => {
    for (const [surface, files] of Object.entries(STATIC_SURFACE_PRODUCER_FILES)) {
      const contracted = staticContractChannels(surface as MockTransferSurface["surface"]);
      const used = sourceLiterals(files, TAURI_INVOKE_PATTERN);
      const missing = used.filter((command) => !contracted.has(command));
      expect(missing, `${surface} missing Tauri commands`).toEqual([]);
    }
  });

  it("keeps contracted Tauri commands registered in Rust", () => {
    const registered = rustRegisteredCommands();
    const missing = contractedTauriCommands().filter(
      (command) => !registered.has(command),
    );
    expect(missing, "contracted Tauri commands missing from generate_handler").toEqual([]);
  });

  it("points at tracked mock sources for visual transfer", () => {
    for (const surface of [
      ...MOCK_TRANSFER_CONTRACT,
      ...MOCK_TRANSFER_RUNTIME_CONTRACT,
    ]) {
      for (const mock of surface.mockSources) {
        expect(existsSync(resolve(REPO_ROOT, mock)), `${mock} should exist`).toBe(true);
      }
    }
  });

  it("keeps active Claude mock iterations indexed for transfer", () => {
    expect(
      existsSync(resolve(REPO_ROOT, ACTIVE_MOCK_ITERATION_INDEX)),
      `${ACTIVE_MOCK_ITERATION_INDEX} should exist`,
    ).toBe(true);
    expect(
      existsSync(resolve(REPO_ROOT, ACTIVE_MOCK_ITERATION_TEMPLATE)),
      `${ACTIVE_MOCK_ITERATION_TEMPLATE} should exist`,
    ).toBe(true);

    const files = activeMockIterationFiles();
    expect(files.length, "active mock iteration files").toBeGreaterThan(0);

    const index = readRepoFile(ACTIVE_MOCK_ITERATION_INDEX);
    for (const file of files) {
      expect(index, `${ACTIVE_MOCK_ITERATION_INDEX} should link ${file}`)
        .toContain(`href="${file}"`);
    }

    const template = readRepoFile(ACTIVE_MOCK_ITERATION_TEMPLATE);
    expect(template).toContain("SHELL CONTRACT");
    expect(template).toContain("REGIONS TO RENDER");
  });

  it("gives settings groups stable transfer anchors", () => {
    for (const wire of SETTINGS_GROUP_WIRES) {
      const header = wire.replace("settings.group.", "").replace(/-/g, " ").toUpperCase();
      const child = document.createElement("div");
      const group = renderSettingsGroup({ header, children: child });
      expect(group.dataset.wire).toBe(wire);
      expect(group.querySelector(wireSelector(`${wire}.header`))).toBeTruthy();
      expect(group.querySelector(wireSelector(`${wire}.body`))).toBeTruthy();
    }

    const custom = renderSettingsGroup({
      header: "EXPERIMENTAL",
      wireId: "settings.group.experimental",
      children: document.createElement("div"),
    });
    expect(custom.dataset.wire).toBe("settings.group.experimental");
  });
});
