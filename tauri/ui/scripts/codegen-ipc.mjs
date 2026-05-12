/* Phase 11 Wave 0 — codegen wrapper.
 *
 * The json2ts CLI doesn't expose --bannerComment so we drive the programmatic
 * API directly. The generated `messages.ts` is committed alongside the schema
 * per RESEARCH alternatives-considered (codegen output is committed so
 * downstream Tauri builds don't depend on Node being available; CI regenerates
 * and diffs to catch drift).
 */
import { compileFromFile } from "json-schema-to-typescript";
import { writeFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SCHEMA = resolve(ROOT, "src/ipc/messages.schema.json");
const OUT = resolve(ROOT, "src/ipc/messages.ts");

const BANNER = `/* AUTO-GENERATED from messages.schema.json — do not edit. Run 'npm run codegen:ipc'. */`;

const ts = await compileFromFile(SCHEMA, {
  bannerComment: BANNER,
  unreachableDefinitions: true,
  additionalProperties: false,
});
await writeFile(OUT, ts);
process.stdout.write(`codegen:ipc — wrote ${OUT}\n`);
