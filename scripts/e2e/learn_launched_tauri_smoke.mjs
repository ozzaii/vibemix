#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
//
// Launched Learn smoke for macOS where tauri-driver cannot inspect WKWebView.
// It starts the real Python Learn harness on :8765, launches `cargo tauri dev`
// with the production Rust WS bridge, opens the real Learn webview through an
// opt-in Rust e2e hook, and waits for L1.01 completion to persist.

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { get as httpGet } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SCRIPT_DIR, "..", "..");
const TAURI_DIR = join(REPO_ROOT, "tauri");
const UI_DIR = join(TAURI_DIR, "ui");
const SIDE_PORT = 8765;
const DEV_PORT = 1420;
const TIMEOUT_MS = Number(process.env.VIBEMIX_LEARN_E2E_TIMEOUT_MS ?? 120_000);
const DEFAULT_OUT_PATH =
  process.env.VIBEMIX_LEARN_TAURI_SMOKE_OUT ??
  "/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json";

const axePath = join(UI_DIR, "node_modules", "axe-core", "axe.min.js");
const OUT_PATH = parseOutPath(process.argv, DEFAULT_OUT_PATH);

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log("Usage: node scripts/e2e/learn_launched_tauri_smoke.mjs [--out PATH]");
  console.log("Runs a launched Tauri Learn smoke against a test sidecar on 127.0.0.1:8765.");
  console.log(
    `Writes a durable JSON proof artifact to ${DEFAULT_OUT_PATH} unless --out PATH is provided.`,
  );
  process.exit(0);
}

const tempDir = mkdtempSync(join(tmpdir(), "vibemix-learn-tauri-"));
const progressPath = join(tempDir, "learn-progress.json");
const resultPath = join(tempDir, "learn-e2e-result.json");
const children = [];

main().catch((err) => {
  console.error(`[learn-tauri-smoke] FAIL: ${err instanceof Error ? err.message : String(err)}`);
  process.exitCode = 1;
}).finally(async () => {
  await stopChildren();
  rmSync(tempDir, { recursive: true, force: true });
});

async function main() {
  await assertPortFree(SIDE_PORT);
  if (!existsSync(axePath)) {
    throw new Error(`axe-core is not installed at ${axePath}`);
  }
  if (!(await httpReady(DEV_PORT))) {
    await assertPortFree(DEV_PORT);
    spawnTracked(
      "Vite dev server",
      "npm",
      ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(DEV_PORT)],
      { cwd: UI_DIR },
    );
    await waitForHttp(DEV_PORT, 30_000);
  }

  const harness = spawnTracked(
    "Python Learn harness",
    "uv",
    [
      "run",
      "python",
      "tests/learn/learn_ws_sidecar_harness.py",
      "--port",
      String(SIDE_PORT),
      "--progress-path",
      progressPath,
      "--unlock-dwell",
    ],
    { cwd: REPO_ROOT },
  );
  await waitForOutput(harness, `READY ${SIDE_PORT}`, 20_000, "Python Learn harness");

  const tauri = spawnTracked(
    "Tauri dev app",
    "cargo",
    [
      "tauri",
      "dev",
      "--no-watch",
      "--no-dev-server-wait",
      "--config",
      JSON.stringify({ build: { beforeDevCommand: "" } }),
    ],
    {
      cwd: TAURI_DIR,
      env: {
        ...process.env,
        VIBEMIX_E2E_EXTERNAL_SIDECAR: "1",
        VIBEMIX_E2E_AUTORUN_LEARN: "1",
        VIBEMIX_E2E_RESULT_PATH: resultPath,
        VIBEMIX_E2E_AXE_PATH: axePath,
        VIBEMIX_DEV_SIDECAR: "1",
        PYTHONDONTWRITEBYTECODE: "1",
      },
    },
  );

  const quality = await waitForQualityResult(resultPath, TIMEOUT_MS);
  const progress = await waitForProgressCompletion(progressPath, TIMEOUT_MS);
  if (OUT_PATH !== null) {
    writeSummary(OUT_PATH, { quality, progress });
  }
  console.log(
    "[learn-tauri-smoke] PASS: launched Tauri Learn completed L1.01 and quality checks through :8765",
  );
  void tauri;
  void harness;
}

function spawnTracked(label, command, args, options) {
  const child = spawn(command, args, {
    ...options,
    env: options.env ?? process.env,
    stdio: ["ignore", "pipe", "pipe"],
    detached: process.platform !== "win32",
  });
  child.__label = label;
  child.__detached = process.platform !== "win32";
  child.__stdout = "";
  child.__stderr = "";
  child.stdout.on("data", (chunk) => {
    child.__stdout += chunk.toString("utf8");
  });
  child.stderr.on("data", (chunk) => {
    child.__stderr += chunk.toString("utf8");
  });
  children.push(child);
  return child;
}

async function waitForOutput(child, needle, timeoutMs, label) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if ((child.__stdout ?? "").includes(needle) || (child.__stderr ?? "").includes(needle)) {
      return;
    }
    if (child.exitCode !== null) {
      throw new Error(`${label} exited before ready.\n${tail(child)}`);
    }
    await sleep(80);
  }
  throw new Error(`${label} did not print ${JSON.stringify(needle)}.\n${tail(child)}`);
}

async function waitForProgressCompletion(path, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (existsSync(path)) {
      const raw = readFileSync(path, "utf8");
      try {
        const progress = JSON.parse(raw);
        if (progress?.lessons?.["L1.01"]?.completed === true) {
          return progress;
        }
      } catch {
        // Atomic replace means a partial read should be rare; retry.
      }
    }
    for (const child of children) {
      if (child.exitCode !== null) {
        throw new Error(`${child.__label} exited before Learn completed.\n${tail(child)}`);
      }
    }
    await sleep(250);
  }
  throw new Error(`timed out waiting for L1.01 completion in ${path}`);
}

async function waitForQualityResult(path, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (existsSync(path)) {
      const raw = readFileSync(path, "utf8");
      const result = JSON.parse(raw);
      if (result?.ok === true) {
        if (!Array.isArray(result.checks) || result.checks.length < 6) {
          throw new Error(`quality result is too weak: ${raw}`);
        }
        return result;
      }
      throw new Error(`launched Learn quality checks failed: ${raw}`);
    }
    for (const child of children) {
      if (child.exitCode !== null) {
        throw new Error(`${child.__label} exited before Learn quality proof.\n${tail(child)}`);
      }
    }
    await sleep(250);
  }
  throw new Error(`timed out waiting for launched Learn quality result in ${path}`);
}

function parseOutPath(argv, defaultPath) {
  const outIndex = argv.indexOf("--out");
  if (outIndex < 0) return resolve(defaultPath);
  const value = argv[outIndex + 1];
  if (!value || value.startsWith("--")) {
    throw new Error("--out requires a path");
  }
  return resolve(value);
}

function writeSummary(path, { quality, progress }) {
  mkdirSync(dirname(path), { recursive: true });
  const summary = {
    schema_version: 1,
    proof: "launched_tauri_learn_smoke",
    passed: true,
    completed_lesson_id: "L1.01",
    l101_completed: progress?.lessons?.["L1.01"]?.completed === true,
    quality_ok: quality?.ok === true,
    quality_check_count: Array.isArray(quality?.checks) ? quality.checks.length : 0,
    quality_checks: quality?.checks ?? [],
    failures: quality?.failures ?? [],
    progress,
    generated_at: new Date().toISOString(),
  };
  writeFileSync(path, JSON.stringify(summary, null, 2) + "\n", "utf8");
}

async function assertPortFree(port) {
  await new Promise((resolveFree, rejectBusy) => {
    const server = createServer();
    server.once("error", (err) => {
      rejectBusy(new Error(`127.0.0.1:${port} is already in use; stop vibemix first. ${err}`));
    });
    server.listen(port, "127.0.0.1", () => {
      server.close(resolveFree);
    });
  });
}

async function waitForHttp(port, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await httpReady(port)) return;
    await sleep(100);
  }
  throw new Error(`Vite dev server did not answer on 127.0.0.1:${port}`);
}

async function httpReady(port) {
  return await new Promise((resolveReady) => {
    const req = httpGet(`http://127.0.0.1:${port}/learn.html`, (res) => {
      res.resume();
      resolveReady(Boolean(res.statusCode && res.statusCode >= 200 && res.statusCode < 500));
    });
    req.setTimeout(500, () => {
      req.destroy();
      resolveReady(false);
    });
    req.on("error", () => resolveReady(false));
  });
}

async function stopChildren() {
  for (const child of children) {
    killChild(child, "SIGTERM");
  }
  await sleep(1200);
  for (const child of children) {
    killChild(child, "SIGKILL");
  }
}

function killChild(child, signal) {
  try {
    if (child.__detached && typeof child.pid === "number") {
      process.kill(-child.pid, signal);
      return;
    }
  } catch {
    // Fall through to direct kill.
  }
  try {
    if (child.exitCode === null) child.kill(signal);
  } catch {
    // Already gone.
  }
}

function tail(child) {
  const stdout = (child.__stdout ?? "").split(/\r?\n/).slice(-60).join("\n");
  const stderr = (child.__stderr ?? "").split(/\r?\n/).slice(-60).join("\n");
  return `stdout:\n${stdout}\nstderr:\n${stderr}`;
}

function sleep(ms) {
  return new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}
