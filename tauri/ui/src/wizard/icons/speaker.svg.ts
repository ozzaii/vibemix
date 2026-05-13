/* Speaker cone glyph + 4 concentric "sound waves" ring set used by the
 * audio-test-button. When the button is in `playing` state the 4 rings
 * animate via CSS keyframes (see audio-test-button.ts). UI-SPEC §7. */
export const SPEAKER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6l9-7v26l-9-7H9V18z"/></svg>`;

/* Standalone BlackHole-style sound waveform pulse for the install banner —
 * concentric arcs of decreasing opacity to suggest "missing audio path".
 * UI-SPEC §8 BlackHole banner. */
export const BLACKHOLE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="2.5" fill="currentColor"/><path opacity="0.6" d="M8 8a5.6 5.6 0 0 1 8 0"/><path opacity="0.6" d="M8 16a5.6 5.6 0 0 0 8 0"/><path opacity="0.3" d="M5 5a9.9 9.9 0 0 1 14 0"/><path opacity="0.3" d="M5 19a9.9 9.9 0 0 0 14 0"/></svg>`;

/* Plug glyph for the controller-probe empty state ("no controller
 * detected — plug one in or skip"). Rendered in --silk-40. UI-SPEC §10. */
export const PLUG_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 40" width="64" height="40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="20" y="10" width="24" height="20" rx="3"/><line x1="26" y1="6" x2="26" y2="10"/><line x1="38" y1="6" x2="38" y2="10"/><line x1="44" y1="20" x2="56" y2="20"/></svg>`;
