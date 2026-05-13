/* Phase 14 Wave 0 — RED proof for the legacy-token detector.
 *
 * Proves that the v5 migration gate's detection logic is sound:
 *   - A clean v5 fixture passes (no legacy tokens)
 *   - A legacy fixture with --phosphor fails (detector flags it)
 *
 * The detector lives here as a tiny TypeScript helper exported for reuse
 * by the four per-surface specs (wizard/session/settings/mascot). The
 * pattern mirrors scripts/check_v5_migration.sh's LEGACY_TOKEN_PATTERN so
 * the bash gate and the vitest gate agree byte-for-byte on what counts
 * as a legacy reference.
 *
 * This spec is always-green in Wave 0 — it's a RED proof for the
 * DETECTOR, not for the migration itself. Per-surface specs (which
 * currently `describe.skip(...)`) carry the actual migration RED.
 */

import { describe, expect, it } from "vitest";

/**
 * Match any of the Phase 11 → Phase 14 shim alias tokens. Keep in sync
 * with LEGACY_TOKEN_PATTERN inside scripts/check_v5_migration.sh —
 * any divergence is a Pitfall (RESEARCH §Pitfall 6).
 *
 * --cue is excluded (Phase 11 invariant: declared-but-never-consumed —
 * not part of the v5 migration; out-of-scope here).
 */
const LEGACY_TOKEN_PATTERN =
  /--(phosphor(-warm|-dim|-soft|-glow|-halo)?|brushed-(hi|lo)|bezel-[123]|panel(-lift|-deep|-hover-top|-pressed-bottom)?|groove|ink(-dim|-deep|-engraved)?|charcoal|col-mascot)\b/;

/**
 * Return true iff `s` contains any legacy CSS-token reference covered by
 * the Wave 0 migration gate. Designed for fixture-string assertions in
 * per-surface specs — pass the rendered component's outerHTML +
 * stylesheet text concatenation.
 */
export function containsLegacyToken(s: string): boolean {
  return LEGACY_TOKEN_PATTERN.test(s);
}

describe("legacy token detector", () => {
  it("returns false for a clean v5 fixture", () => {
    const fixture = "color: var(--silk); background: var(--glass-2); border: 1px solid var(--glass-edge);";
    expect(containsLegacyToken(fixture)).toBe(false);
  });

  it("returns true when --phosphor is present (Wave 0 RED proof)", () => {
    const fixture = "color: var(--phosphor);";
    expect(containsLegacyToken(fixture)).toBe(true);
  });

  it("flags every shim alias from tokens.css:175-231", () => {
    const aliases = [
      "--phosphor",
      "--phosphor-warm",
      "--phosphor-dim",
      "--phosphor-soft",
      "--phosphor-glow",
      "--phosphor-halo",
      "--brushed-hi",
      "--brushed-lo",
      "--bezel-1",
      "--bezel-2",
      "--bezel-3",
      "--panel",
      "--panel-lift",
      "--panel-deep",
      "--panel-hover-top",
      "--panel-pressed-bottom",
      "--groove",
      "--ink",
      "--ink-dim",
      "--ink-deep",
      "--ink-engraved",
      "--charcoal",
      "--col-mascot",
    ];
    for (const alias of aliases) {
      expect(containsLegacyToken(`background: var(${alias});`)).toBe(true);
    }
  });

  it("does NOT flag v5 primitives (no false positives)", () => {
    const v5Tokens = [
      "--void", "--void-1", "--void-2", "--void-3", "--void-4",
      "--glass-1", "--glass-2", "--glass-3",
      "--glass-edge", "--glass-edge-up", "--glass-top",
      "--silk", "--silk-65", "--silk-40", "--silk-22", "--silk-12",
      "--amber", "--amber-deep", "--amber-pale", "--amber-22", "--amber-40", "--amber-65",
      "--glow-faint", "--glow-soft", "--glow-strong",
      "--type-display", "--type-body", "--type-mono",
      "--rad-sm", "--rad-md", "--rad-lg",
      "--sp-1", "--sp-2", "--sp-3", "--sp-4", "--sp-5", "--sp-6", "--sp-7", "--sp-8",
      "--motion-border-sweep",
    ];
    for (const tok of v5Tokens) {
      expect(containsLegacyToken(`color: var(${tok});`)).toBe(false);
    }
  });

  it("does NOT flag --cue (Phase 11 invariant — declared-but-never-consumed)", () => {
    expect(containsLegacyToken("color: var(--cue);")).toBe(false);
  });
});
