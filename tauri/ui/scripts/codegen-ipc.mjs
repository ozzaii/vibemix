/* Phase 11 Wave 0 — codegen wrapper.
 *
 * Generates two artifacts from messages.schema.json:
 *  1. src/ipc/messages.ts                 — TS types via json-schema-to-typescript
 *  2. src/ipc/validator.generated.mjs     — pre-compiled ajv standalone validator
 *
 * The standalone validator is REQUIRED because the production webview ships
 * under a Tauri CSP without `unsafe-eval`. ajv's runtime `.compile(schema)`
 * uses `new Function(...)` which CSP blocks. Pre-compiling to a static .mjs
 * at build time avoids the eval entirely.
 *
 * Both outputs are committed so CI can diff for schema drift.
 */
import Ajv from "ajv";
import addFormats from "ajv-formats";
import standaloneCode from "ajv/dist/standalone/index.js";
import { compileFromFile } from "json-schema-to-typescript";
import { readFile, writeFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SCHEMA = resolve(ROOT, "src/ipc/messages.schema.json");
const TS_OUT = resolve(ROOT, "src/ipc/messages.ts");
const VALIDATOR_OUT = resolve(ROOT, "src/ipc/validator.generated.mjs");

const BANNER = `/* AUTO-GENERATED from messages.schema.json — do not edit. Run 'npm run codegen:ipc'. */`;

const ts = await compileFromFile(SCHEMA, {
  bannerComment: BANNER,
  unreachableDefinitions: true,
  additionalProperties: false,
});
await writeFile(TS_OUT, ts);
process.stdout.write(`codegen:ipc — wrote ${TS_OUT}\n`);

const schema = JSON.parse(await readFile(SCHEMA, "utf8"));
const ajv = new Ajv({
  code: { source: true, esm: true },
  allErrors: true,
  strict: false,
});
addFormats(ajv);
const validateFn = ajv.compile(schema);
let moduleCode = standaloneCode(ajv, validateFn);

// ajv standalone emits inline require() calls for ajv-formats and ajv
// runtime helpers even when esm: true is set. The Tauri webview CSP blocks
// CommonJS require, so we rewrite each require("...") into a hoisted static
// import. Vite then bundles those modules into the final main.js.
const requireSpecs = new Map();
moduleCode = moduleCode.replace(/require\("([^"]+)"\)/g, (_match, spec) => {
  let ident = requireSpecs.get(spec);
  if (!ident) {
    ident = `__req_${requireSpecs.size}`;
    requireSpecs.set(spec, ident);
  }
  return ident;
});
const importLines = [...requireSpecs.entries()]
  .map(([spec, ident]) => `import ${ident} from ${JSON.stringify(spec)};`)
  .join("\n");
const stripped = moduleCode.replace(/^"use strict";\s*/, "");
const banner = `${BANNER}\n/* eslint-disable */\n${importLines}\n`;
await writeFile(VALIDATOR_OUT, banner + stripped);
process.stdout.write(`codegen:ipc — wrote ${VALIDATOR_OUT}\n`);
