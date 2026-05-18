/* copy.ts — Typed loader for installer/companion/onboarding_copy.json.
 *
 * Phase 49 Plan 03 — single source-of-truth for every wizard user-facing
 * string. The JSON file at installer/companion/onboarding_copy.json is the
 * canonical store; this module re-exports it as a typed `copy` const +
 * helper interpolator.
 *
 * Anti-pattern guard: step components MUST import strings from here. Inline
 * string literals in step files are lint-checked via the sibling anti-slop
 * script scripts/audit/check_no_slop_install.py (which sweeps these files).
 *
 * Vite is configured to import JSON via `?raw` or direct JSON import. The
 * onboarding_copy.json file lives outside the tauri/ui/ root, so we copy
 * a frozen mirror to tauri/ui/src/wizard/copy.json at build time via
 * scripts/build/sync_wizard_copy.sh (see hand-off note below). If the
 * mirror is stale (build script not run), the asserts here fail loud at
 * module-init.
 *
 * BUILD HAND-OFF: when installer/companion/onboarding_copy.json changes,
 * re-run `bash scripts/build/sync_wizard_copy.sh` to refresh the mirror.
 * CI gates this via tests/wizard/test_copy_mirror_in_sync.test.ts.
 */

// @ts-ignore — Vite resolves JSON imports natively. The mirror file is
// generated; if absent the build will fail at this import.
import copyJson from "./copy.json";

export interface WelcomeStep {
  hero_line_1: string;
  hero_line_2: string;
  hero_line_3: string;
  primary_cta: string;
}

export interface ForewarningStep {
  section_heading: string;
  mac_title: string;
  mac_body: string;
  win_title: string;
  win_body: string;
  continue_cta: string;
  back_cta: string;
}

export interface DriverFetchStep {
  heading: string;
  row_idle: string;
  row_fetching: string;
  row_verifying: string;
  row_installing: string;
  row_done: string;
  midi_probe: string;
  tcc_probe: string;
  bravoh_probe: string;
  stopwatch: string;
  fallback_heading: string;
  fallback_body: string;
  continue_cta: string;
}

export interface FormatCheckStep {
  heading: string;
  success: string;
  fail: string;
  fix_cta: string;
  mac_manual: string;
  win_manual: string;
  final_cta: string;
}

export interface UninstallDialog {
  title: string;
  body: string;
  default_cta: string;
  clean_opt_in: string;
  clean_body: string;
  clean_confirm_cta: string;
  cancel_cta: string;
}

export interface CopyShape {
  version: string;
  steps: {
    welcome: WelcomeStep;
    forewarning: ForewarningStep;
    driver_fetch: DriverFetchStep;
    format_check: FormatCheckStep;
  };
  uninstall: UninstallDialog;
}

export const copy: CopyShape = copyJson as CopyShape;

// Module-init assertions — loud fail if mirror is stale or missing fields.
function assertField(path: string, value: unknown): void {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(
      `wizard/copy.ts: missing/empty required field: ${path}. ` +
        `Re-run scripts/build/sync_wizard_copy.sh to refresh.`,
    );
  }
}

assertField("steps.welcome.hero_line_1", copy.steps?.welcome?.hero_line_1);
assertField("steps.welcome.primary_cta", copy.steps?.welcome?.primary_cta);
assertField("steps.forewarning.mac_title", copy.steps?.forewarning?.mac_title);
assertField("steps.forewarning.win_title", copy.steps?.forewarning?.win_title);
assertField("steps.driver_fetch.heading", copy.steps?.driver_fetch?.heading);
assertField("steps.format_check.success", copy.steps?.format_check?.success);
assertField("uninstall.title", copy.uninstall?.title);

/** Interpolate `{name}` placeholders with values. */
export function interpolate(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{([a-z_]+)\}/g, (_match, key) => {
    const v = vars[key];
    return v === undefined ? `{${key}}` : String(v);
  });
}
