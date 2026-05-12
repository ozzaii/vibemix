/* Phase 11 Wave 0 — ajv runtime guard for inbound ipc.* frames.
 *
 * Mirrors the Python side (vibemix.ui_bus.validator.parse_message). Drift
 * between the two sides is caught at build time by scripts/check_ipc_schema.py
 * (oneOf-vs-wrapper-count parity) and `npm run check:ipc` (codegen + tsc).
 * This module is the runtime trust boundary T-11-W0-04: webview accepts NO
 * sidecar frame that fails ajv validation.
 *
 * Schema is imported as JSON via tsconfig `resolveJsonModule: true`. ajv is
 * compiled once at module load — calling `validate(raw)` is cheap.
 */

import Ajv, { type ValidateFunction } from "ajv";
import addFormats from "ajv-formats";

import schema from "./messages.schema.json" with { type: "json" };
import type { VibemixIPCMessages as IpcMessage } from "./messages.js";

// `strict: false` because our schema uses `$comment` (Draft-07 supported but
// not part of ajv's strict-keywords whitelist) and the discriminated union
// is by oneOf-with-const rather than ajv's discriminator extension.
const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const validate: ValidateFunction = ajv.compile(schema);

/**
 * Parse an inbound IPC frame.
 *
 * @throws Error with `ajv.errorsText(...)` body when validation fails. The
 *   Wave 4 WizardLoop will catch + log + drop the frame (DoS mitigation).
 */
export function parseIpcMessage(raw: unknown): IpcMessage {
  if (!validate(raw)) {
    throw new Error(`IPC schema violation: ${ajv.errorsText(validate.errors)}`);
  }
  return raw as IpcMessage;
}

/**
 * Type guard variant — narrows without throwing. Useful in fan-out switches
 * that want to log-and-skip rather than raise.
 */
export function isIpcMessage(raw: unknown): raw is IpcMessage {
  return validate(raw) as boolean;
}

export type { IpcMessage };
