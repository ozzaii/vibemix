/* Phase 11 Wave 0 — ajv runtime guard for inbound ipc.* frames.
 *
 * Mirrors the Python side (vibemix.ui_bus.validator.parse_message). Drift
 * between the two sides is caught at build time by scripts/check_ipc_schema.py
 * (oneOf-vs-wrapper-count parity) and `npm run check:ipc` (codegen + tsc).
 * This module is the runtime trust boundary T-11-W0-04: webview accepts NO
 * sidecar frame that fails ajv validation.
 *
 * Uses ajv standalone (pre-compiled validator emitted by codegen-ipc.mjs) so
 * the CSP can stay free of `unsafe-eval` — ajv's runtime `.compile(schema)`
 * relies on `new Function(...)` which Tauri's CSP blocks.
 */

// @ts-expect-error — generated file ships without .d.ts; validator is a
// function(value) => boolean with `.errors` populated on failure.
import validateGenerated from "./validator.generated.mjs";
import type { VibemixIPCMessages as IpcMessage } from "./messages.js";

type AjvValidator = ((data: unknown) => boolean) & {
  errors?: Array<{
    instancePath: string;
    keyword: string;
    message?: string;
    params?: Record<string, unknown>;
  }> | null;
};

const validate = validateGenerated as AjvValidator;

function errorsText(): string {
  if (!validate.errors || validate.errors.length === 0) return "no errors";
  return validate.errors
    .map((e) => `${e.instancePath || "(root)"} ${e.message ?? e.keyword}`)
    .join("; ");
}

/**
 * Parse an inbound IPC frame.
 *
 * @throws Error with a summary of ajv errors when validation fails. The
 *   Wave 4 WizardLoop will catch + log + drop the frame (DoS mitigation).
 */
export function parseIpcMessage(raw: unknown): IpcMessage {
  if (!validate(raw)) {
    throw new Error(`IPC schema violation: ${errorsText()}`);
  }
  return raw as IpcMessage;
}

/**
 * Type guard variant — narrows without throwing. Useful in fan-out switches
 * that want to log-and-skip rather than raise.
 */
export function isIpcMessage(raw: unknown): raw is IpcMessage {
  return validate(raw);
}

export type { IpcMessage };
