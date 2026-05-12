// Phase 11 Wave 0 — Vitest minimal config. Node environment for now (DOM
// tests arrive in Wave 3 when wizard components land). Default everything
// else; tsconfig handles strict mode + path resolution.
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.spec.ts"],
  },
});
