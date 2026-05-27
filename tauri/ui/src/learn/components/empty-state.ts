// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — EmptyState component (UI-SPEC §Component Inventory).
//
// Shown when `mido.get_input_names()` returns no candidate controllers
// (no `ipc.learn.controller_detected` envelope has arrived). Centered
// single column over the void:
//
//   - 64×64 plug glyph (silk-22 currentColor)
//   - 28px Saira heading: "no controller detected"
//   - 16px body: "plug one in to begin."
//   - NO CTA button (P91 has no fall-through path; P97 adds the
//     mode-picker bypass).
//
// All copy lowercase, period-terminated. The void DOMINATES — empty
// state is the ABSENCE of the artifact, not a content surface.
// Copywriting verbatim from UI-SPEC §Copywriting Contract.

const PLUG_GLYPH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <!-- USB plug body -->
  <rect x="20" y="14" width="24" height="22" rx="3" ry="3"/>
  <!-- Plug prongs -->
  <line x1="26" y1="10" x2="26" y2="14"/>
  <line x1="38" y1="10" x2="38" y2="14"/>
  <!-- Cable -->
  <path d="M32 36 L32 46 Q32 52 28 52 L20 52"/>
  <!-- Cable jack -->
  <rect x="12" y="48" width="10" height="8" rx="1.5" ry="1.5"/>
</svg>`;

/**
 * Render the empty-state surface into the given root element. Replaces
 * any prior content. Called by `learn-window.ts` when no controller is
 * detected (first paint + on disconnect).
 */
export function mountEmptyState(el: HTMLElement): void {
  el.innerHTML = `
    <div class="learn-empty-state">
      <div class="learn-empty-state-glyph">${PLUG_GLYPH_SVG}</div>
      <h2 class="learn-empty-state-heading">no controller detected</h2>
      <p class="learn-empty-state-body">plug one in to begin.</p>
    </div>
  `;
}
