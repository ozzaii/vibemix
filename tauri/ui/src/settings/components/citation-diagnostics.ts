/* Phase 20 Plan 04 Task 2 — citation-diagnostics.ts.
 *
 * STUB component for Settings → Diagnostics. Plain TS DOM-API style to match
 * the prevailing pattern in this directory (recording-row.ts, retention-slider.ts,
 * mascot-group.ts). Phase 14's Settings drawer wiring is out of scope; this
 * file ships only the renderer + a typed update API ready to drop in.
 *
 * Inputs (typed via CitationDiagnosticsProps):
 *   - slopRatio:           cumulative stripped/total in [0, 1]
 *   - strippedRate15s:     15-second rolling stripped rate in [0, 1]
 *   - lastUnverifiedResponse: most recent stripped/blocked text, or null
 *   - bypassActive:        true when the linter's bypass guard is silencing output
 *
 * Render contract (per Plan 20-04 §Task 2 §behavior):
 *   Line 1: "Slop ratio: <pct>%  ·  Stripped rate (15s): <pct>%"
 *   Line 2: bypass badge — "Bypass: ACTIVE" (data-active="true") or "Bypass: idle"
 *   Optional Line 3: when lastUnverifiedResponse !== null AND bypassActive,
 *     a subtitle showing the first 60 chars + "..." + the full text in the
 *     `title` attribute (XSS-safe via element.textContent / .title assignment).
 *
 * The component returns a `CitationDiagnosticsHandle` exposing the root +
 * an `update(props)` setter so a future Settings-drawer subscriber can
 * push fresh props on every ipc.session.citation message without rebuilding
 * the DOM.
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface CitationDiagnosticsProps {
  slopRatio: number;
  strippedRate15s: number;
  lastUnverifiedResponse: string | null;
  bypassActive: boolean;
}

export interface CitationDiagnosticsHandle {
  root: HTMLElement;
  update(next: CitationDiagnosticsProps): void;
}

const TRUNCATE_AT = 60;

const CSS = `
  .vmx-citation-diag {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    padding: var(--sp-3);
    background: var(--glass-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    font-family: var(--type-body);
    color: var(--silk);
  }
  .vmx-citation-diag__line {
    font-size: 13px;
    color: var(--silk);
    font-variant-numeric: tabular-nums;
  }
  .vmx-citation-diag__badge {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    padding: 2px var(--sp-2);
    font-size: 11px;
    font-family: var(--type-mono);
    border-radius: var(--rad-sm);
    background: var(--glass-3);
    color: var(--silk-65);
    border: 1px solid var(--glass-edge);
    text-transform: none;
    letter-spacing: 0.02em;
  }
  .vmx-citation-diag__badge[data-active="true"] {
    background: var(--amber-22);
    color: var(--amber);
    border-color: var(--amber);
  }
  .vmx-citation-diag__last-unverified {
    font-size: 12px;
    color: var(--silk-65);
    font-style: italic;
    cursor: help;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

registerStyle("vmx-citation-diag", CSS);

function formatPct(value: number): string {
  // Defensive: clamp to [0, 1] in case telemetry overshoots before the
  // sidecar's jsonschema guard would normally catch it (the schema bound
  // is enforced on the wire; this is a safety net for the renderer).
  const clamped = Math.max(0, Math.min(1, value));
  return `${Math.round(clamped * 100)}%`;
}

function buildLine1(props: CitationDiagnosticsProps): string {
  return (
    `Slop ratio: ${formatPct(props.slopRatio)}  ·  `
    + `Stripped rate (15s): ${formatPct(props.strippedRate15s)}`
  );
}

function buildBadgeText(active: boolean): string {
  return active ? "Bypass: ACTIVE" : "Bypass: idle";
}

export function renderCitationDiagnostics(
  initial: CitationDiagnosticsProps,
): CitationDiagnosticsHandle {
  const root = document.createElement("div");
  root.className = "vmx-citation-diag";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");

  const line1 = document.createElement("div");
  line1.className = "vmx-citation-diag__line";
  root.append(line1);

  const badge = document.createElement("span");
  badge.className = "vmx-citation-diag__badge";
  root.append(badge);

  let lastUnverifiedEl: HTMLElement | null = null;

  function applyState(props: CitationDiagnosticsProps): void {
    line1.textContent = buildLine1(props);
    badge.textContent = buildBadgeText(props.bypassActive);
    badge.dataset.active = props.bypassActive ? "true" : "false";

    const showUnverified
      = props.bypassActive && props.lastUnverifiedResponse !== null;
    if (showUnverified) {
      const fullText = props.lastUnverifiedResponse as string;
      const truncated
        = fullText.length > TRUNCATE_AT
          ? `${fullText.slice(0, TRUNCATE_AT)}...`
          : fullText;
      if (lastUnverifiedEl === null) {
        lastUnverifiedEl = document.createElement("div");
        lastUnverifiedEl.className = "vmx-citation-diag__last-unverified";
        // Tag with a class the spec asserts on for absence in the idle case.
        lastUnverifiedEl.classList.add("citation-diag-last-unverified");
        root.append(lastUnverifiedEl);
      }
      // textContent + title — never innerHTML (T-20-04-06 mitigation).
      lastUnverifiedEl.textContent = truncated;
      lastUnverifiedEl.title = fullText;
    } else if (lastUnverifiedEl !== null) {
      lastUnverifiedEl.remove();
      lastUnverifiedEl = null;
    }
  }

  applyState(initial);

  return {
    root,
    update(next: CitationDiagnosticsProps): void {
      applyState(next);
    },
  };
}
