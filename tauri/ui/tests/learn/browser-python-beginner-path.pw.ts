// SPDX-License-Identifier: Apache-2.0

import { expect, test, type Page } from "@playwright/test";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { createServer } from "node:net";

interface HarnessProcess {
  port: number;
  progressPath: string;
  stop: () => Promise<void>;
}

test.describe("Learn browser plus Python sidecar path", () => {
  let harness: HarnessProcess | null = null;

  test.afterEach(async () => {
    await harness?.stop();
    harness = null;
  });

  test("recommended L1.01 completes through the Tauri-style forwarder", async ({
    page,
  }) => {
    harness = await startPythonHarness();
    await installTauriForwarder(page, harness.port);

    await completeRecommendedL101(page, harness);
  });

  test("recommended L1.01 completes through direct browser ws fallback", async ({
    page,
  }) => {
    harness = await startPythonHarness();
    await installDirectWsRewrite(page, harness.port);

    await completeRecommendedL101(page, harness);
  });

  test("wrong on-screen move receives grounded adaptive coaching", async ({
    page,
  }) => {
    harness = await startPythonHarness();
    await installDirectWsRewrite(page, harness.port);
    await installTutorSpeakRecorder(page);

    await page.goto("/learn.html");
    await page.waitForFunction(
      () =>
        (window as Window & { __learnHarnessLearnSocketOpen?: boolean })
          .__learnHarnessLearnSocketOpen === true,
    );
    await page.locator("svg.learn-controller-schematic").waitFor();

    await page.locator("#learn-open-map").click();
    await page.locator('[data-lesson-id="L1.03"]').click();

    await expect(page.locator(".tutor-dock .now")).toHaveText(
      "turn the top EQ knob on deck A all the way one direction, then the other.",
    );
    await expect(page.locator('[data-control-id="eq_hi:A"]')).toHaveAttribute(
      "data-cue-color",
      "amber",
    );

    await page.locator('[data-control-id="eq_mid:A"]').click({ force: true });
    await expectSentFrame(page, "ipc.learn.ack", 1);
    await expect(page.locator(".tutor-dock .hint-line")).toHaveText(
      "that was deck A mid EQ. use deck A high EQ.",
    );
    await expect(page.locator(".tutor-dock .cite")).toHaveText(
      "◂ SCREEN DECK A MID EQ",
    );
    await expect(page.locator(".tutor-dock .cite")).toHaveAttribute(
      "data-active",
      "true",
    );
    await page.waitForFunction(() => {
      const payloads =
        (window as Window & { __learnHarnessTutorSpeakPayloads?: unknown[] })
          .__learnHarnessTutorSpeakPayloads ?? [];
      return payloads.some((payload) => {
        if (payload === null || typeof payload !== "object") return false;
        const row = payload as {
          data_state?: unknown;
          citations?: unknown;
          teaching_loop?: { turn_kind?: unknown };
        };
        return (
          row.data_state === "hint" &&
          Array.isArray(row.citations) &&
          row.citations.includes("[screen:eq_mid:A]") &&
          row.citations.includes("[screen:eq_hi:A]") &&
          row.teaching_loop?.turn_kind === "adapt"
        );
      });
    });

    await page.locator('[data-control-id="eq_hi:A"]').click({ force: true });
    await expectSentFrame(page, "ipc.learn.ack", 2);
    await expect(page.locator("#learn-booth-panel")).toHaveAttribute(
      "data-visible",
      "true",
    );

    const progress = JSON.parse(readFileSync(harness.progressPath, "utf8")) as {
      lessons?: Record<string, { completed?: boolean }>;
    };
    expect(progress.lessons?.["L1.03"]?.completed).toBe(true);
  });
});

async function completeRecommendedL101(
  page: Page,
  harness: HarnessProcess,
): Promise<void> {
  await page.goto("/learn.html");
  await page.waitForFunction(
    () =>
      (window as Window & { __learnHarnessLearnSocketOpen?: boolean })
        .__learnHarnessLearnSocketOpen === true,
  );
  await page.locator("svg.learn-controller-schematic").waitFor();

  await page.locator("#learn-start-recommended").click();

  const now = page.locator(".tutor-dock .now");
  const continueButton = page.locator("#learn-screen-action");
  await expect(now).toHaveText("Hello vibemix, what are you?");
  await expect(continueButton).toBeVisible();
  await expect(continueButton).toHaveText("continue");

  await continueButton.click();
  await expectSentFrame(page, "ipc.learn.ack", 1);
  await expect(now).toHaveText("I'm the best DJ app in the world.");

  await continueButton.click();
  await expectSentFrame(page, "ipc.learn.ack", 2);
  await expect(now).toHaveText("If you are the best, then who the fuck am I?");

  await continueButton.click();
  await expectSentFrame(page, "ipc.learn.ack", 3);
  await expect(now).toHaveText(
    "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go.",
  );

  await continueButton.click();
  await expectSentFrame(page, "ipc.learn.ack", 4);
  await expect(page.locator("#learn-booth-panel")).toHaveAttribute("data-visible", "true");
  await expect(page.locator("#learn-start-recommended")).toHaveText(
    /start meet your controller/i,
  );

  const progress = JSON.parse(readFileSync(harness.progressPath, "utf8")) as {
    lessons?: Record<string, { completed?: boolean }>;
  };
  expect(progress.lessons?.["L1.01"]?.completed).toBe(true);
}

async function expectSentFrame(
  page: Page,
  type: string,
  count: number,
): Promise<void> {
  await page.waitForFunction(
    ({ expectedType, expectedCount }) => {
      const frames =
        (window as Window & { __learnHarnessSentFrames?: string[] })
          .__learnHarnessSentFrames ?? [];
      return (
        frames.filter((frame) => {
          try {
            return JSON.parse(frame)?.type === expectedType;
          } catch {
            return false;
          }
        }).length >= expectedCount
      );
    },
    { expectedType: type, expectedCount: count },
  );
}

async function installDirectWsRewrite(page: Page, port: number): Promise<void> {
  await page.addInitScript(
    ({ wsPort }) => {
      type HarnessWindow = Window & {
        __learnHarnessLearnSocketOpen?: boolean;
        __learnHarnessSentFrames?: string[];
      };

      const harnessWindow = window as HarnessWindow;
      harnessWindow.__learnHarnessSentFrames = [];
      const NativeWebSocket = window.WebSocket;
      const rewriteUrl = (url: string | URL): string => {
        const raw = String(url);
        return raw.replace("127.0.0.1:8765", `127.0.0.1:${wsPort}`);
      };
      const HarnessWebSocket = function (
        this: WebSocket,
        url: string | URL,
        protocols?: string | string[],
      ): WebSocket {
        const rewritten = rewriteUrl(url);
        const socket =
          protocols === undefined
            ? new NativeWebSocket(rewritten)
            : new NativeWebSocket(rewritten, protocols);
        socket.addEventListener("open", () => {
          harnessWindow.__learnHarnessLearnSocketOpen = true;
        });
        const nativeSend = socket.send.bind(socket);
        socket.send = (data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
          if (typeof data === "string") {
            harnessWindow.__learnHarnessSentFrames?.push(data);
          }
          return nativeSend(data);
        };
        return socket;
      } as unknown as typeof WebSocket;
      Object.setPrototypeOf(HarnessWebSocket, NativeWebSocket);
      HarnessWebSocket.prototype = NativeWebSocket.prototype;
      window.WebSocket = HarnessWebSocket;
    },
    { wsPort: port },
  );
}

async function installTutorSpeakRecorder(page: Page): Promise<void> {
  await page.addInitScript(() => {
    type HarnessWindow = Window & {
      __learnHarnessTutorSpeakPayloads?: unknown[];
    };

    const harnessWindow = window as HarnessWindow;
    harnessWindow.__learnHarnessTutorSpeakPayloads = [];
    window.addEventListener("ipc.learn.tutor_speak", (event: Event) => {
      harnessWindow.__learnHarnessTutorSpeakPayloads?.push(
        (event as CustomEvent<unknown>).detail,
      );
    });
  });
}

async function installTauriForwarder(page: Page, port: number): Promise<void> {
  await page.addInitScript(
    ({ wsPort }) => {
      type TauriInternals = {
        invoke: (cmd: string, args?: unknown) => Promise<unknown>;
        transformCallback: (callback?: (value: unknown) => unknown, once?: boolean) => number;
        unregisterCallback: (id: number) => void;
        runCallback: (id: number, value: unknown) => unknown;
        callbacks: Map<number, (value: unknown) => unknown>;
        metadata: {
          currentWindow: { label: string };
          currentWebview: { windowLabel: string; label: string };
        };
      };
      type HarnessWindow = Window & {
        __TAURI_INTERNALS__?: TauriInternals;
        __learnHarnessLearnSocketOpen?: boolean;
        __learnHarnessSentFrames?: string[];
      };

      const harnessWindow = window as HarnessWindow;
      harnessWindow.__learnHarnessSentFrames = [];
      const NativeWebSocket = window.WebSocket;
      let learnSocket: WebSocket | null = null;
      let resolveLearnSocketOpen: (() => void) | null = null;
      const learnSocketOpen = new Promise<void>((resolveOpen) => {
        resolveLearnSocketOpen = resolveOpen;
      });
      const rewriteUrl = (url: string | URL): string => {
        const raw = String(url);
        return raw.replace("127.0.0.1:8765", `127.0.0.1:${wsPort}`);
      };
      const HarnessWebSocket = function (
        this: WebSocket,
        url: string | URL,
        protocols?: string | string[],
      ): WebSocket {
        const rewritten = rewriteUrl(url);
        const socket =
          protocols === undefined
            ? new NativeWebSocket(rewritten)
            : new NativeWebSocket(rewritten, protocols);
        socket.addEventListener("open", () => {
          harnessWindow.__learnHarnessLearnSocketOpen = true;
          resolveLearnSocketOpen?.();
        });
        const nativeSend = socket.send.bind(socket);
        socket.send = (data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
          if (typeof data === "string") {
            harnessWindow.__learnHarnessSentFrames?.push(data);
          }
          return nativeSend(data);
        };
        learnSocket = socket;
        return socket;
      } as unknown as typeof WebSocket;
      Object.setPrototypeOf(HarnessWebSocket, NativeWebSocket);
      HarnessWebSocket.prototype = NativeWebSocket.prototype;
      window.WebSocket = HarnessWebSocket;

      const callbacks = new Map<number, (value: unknown) => unknown>();
      let nextCallbackId = 1;
      harnessWindow.__TAURI_INTERNALS__ = {
        invoke: async (cmd: string, args?: unknown): Promise<unknown> => {
          if (cmd !== "forward_ipc_to_sidecar") {
            throw new Error(`unexpected Tauri command in Learn harness: ${cmd}`);
          }
          const message = (args as { message?: unknown } | undefined)?.message;
          if (message === null || typeof message !== "object") {
            throw new Error("forward_ipc_to_sidecar missing message object");
          }
          await learnSocketOpen;
          if (learnSocket === null) {
            throw new Error("Learn harness socket missing");
          }
          learnSocket.send(JSON.stringify(message));
          return null;
        },
        transformCallback: (
          callback?: (value: unknown) => unknown,
          once = false,
        ): number => {
          const id = nextCallbackId;
          nextCallbackId += 1;
          callbacks.set(id, (value: unknown) => {
            if (once) callbacks.delete(id);
            return callback?.(value);
          });
          return id;
        },
        unregisterCallback: (id: number): void => {
          callbacks.delete(id);
        },
        runCallback: (id: number, value: unknown): unknown => {
          return callbacks.get(id)?.(value);
        },
        callbacks,
        metadata: {
          currentWindow: { label: "learn" },
          currentWebview: { windowLabel: "learn", label: "learn" },
        },
      };
    },
    { wsPort: port },
  );
}

async function startPythonHarness(): Promise<HarnessProcess> {
  const port = await freePort();
  const repoRoot = resolve(process.cwd(), "../..");
  const tempDir = mkdtempSync(join(tmpdir(), "vibemix-learn-browser-"));
  const progressPath = join(tempDir, "learn-progress.json");
  const child = spawn(
    "uv",
    [
      "run",
      "python",
      "tests/learn/learn_ws_sidecar_harness.py",
      "--port",
      String(port),
      "--progress-path",
      progressPath,
      "--unlock-dwell",
    ],
    {
      cwd: repoRoot,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    },
  );

  await waitForHarnessReady(child, port);
  return {
    port,
    progressPath,
    stop: async () => {
      await stopProcess(child);
      rmSync(tempDir, { recursive: true, force: true });
    },
  };
}

async function waitForHarnessReady(
  child: ChildProcessWithoutNullStreams,
  port: number,
): Promise<void> {
  let stdout = "";
  let stderr = "";
  await new Promise<void>((resolveReady, rejectReady) => {
    const timeout = setTimeout(() => {
      rejectReady(
        new Error(
          `Learn harness did not start on ${port}.\nstdout:\n${stdout}\nstderr:\n${stderr}`,
        ),
      );
    }, 15_000);
    const cleanup = (): void => {
      clearTimeout(timeout);
      child.stdout.off("data", onStdout);
      child.stderr.off("data", onStderr);
      child.off("exit", onExit);
    };
    const onStdout = (chunk: Buffer): void => {
      stdout += chunk.toString("utf8");
      if (stdout.includes(`READY ${port}`)) {
        cleanup();
        resolveReady();
      }
    };
    const onStderr = (chunk: Buffer): void => {
      stderr += chunk.toString("utf8");
    };
    const onExit = (code: number | null): void => {
      cleanup();
      rejectReady(
        new Error(
          `Learn harness exited before ready with code ${code}.\nstdout:\n${stdout}\nstderr:\n${stderr}`,
        ),
      );
    };
    child.stdout.on("data", onStdout);
    child.stderr.on("data", onStderr);
    child.once("exit", onExit);
  });
}

async function stopProcess(child: ChildProcessWithoutNullStreams): Promise<void> {
  if (child.exitCode !== null) return;
  await new Promise<void>((resolveStopped) => {
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      resolveStopped();
    }, 5_000);
    child.once("exit", () => {
      clearTimeout(timeout);
      resolveStopped();
    });
    child.kill("SIGTERM");
  });
}

async function freePort(): Promise<number> {
  return await new Promise<number>((resolvePort, rejectPort) => {
    const server = createServer();
    server.once("error", rejectPort);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        server.close();
        rejectPort(new Error("could not allocate local port"));
        return;
      }
      const port = address.port;
      server.close(() => resolvePort(port));
    });
  });
}
