// SPDX-License-Identifier: Apache-2.0
//
// pngjs ships no bundled types and is only present transitively (pulled in by
// the Playwright/pixelmatch toolchain), so the organism visual-receipt test
// (browser-organism-probe.pw.ts) decodes screenshots through it. tsconfig
// type-checks tests/**, so without this ambient declaration the project build
// (`tsc --noEmit`) reddens on the bare `import { PNG } from "pngjs"`. We only
// use PNG.sync.read at runtime; an `any` surface is enough here.
declare module "pngjs";
