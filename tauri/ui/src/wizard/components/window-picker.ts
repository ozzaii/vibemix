/* window-picker.ts — Step 2 DJ-app window picker (UI-SPEC §9).
 *
 * Two modes:
 *   - "hint": auto-detected DJ app — 80×80 thumbnail (placeholder rect
 *     in Phase 11) + app name + window title + [ Select ] primary.
 *     Below: [ Pick a different window ↗ ] link.
 *   - "enum": 3-col × N-row grid (160×120 each) + privacy warning at top.
 *
 * Plus a "non-DJ confirm" overlay modal (UI-SPEC §9). */

import { registerStyle } from "./_style-registry.js";
import { Button } from "./button.js";

export interface WindowOption {
  id: string;
  name: string;
  thumbnail?: string;
}

export type WindowPickerMode = "hint" | "enum";

export interface WindowPickerProps {
  mode: WindowPickerMode;
  detectedHint?: { appName: string; windowTitle: string; thumbnail?: string };
  allWindows?: WindowOption[];
  onSelect: (id: string) => void;
  onPickDifferent: () => void;
}

const CSS = `
  .cmp-window-picker__hint {
    display: grid;
    grid-template-columns: 80px 1fr auto;
    align-items: center;
    gap: var(--sp-md);
    padding: var(--sp-md);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-1);
    border-radius: 6px;
  }
  .cmp-window-picker__thumb {
    width: 80px;
    height: 80px;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 4px;
    background-size: cover;
    background-position: center;
  }
  .cmp-window-picker__meta {
    display: flex;
    flex-direction: column;
    gap: var(--sp-xs);
    min-width: 0;
  }
  .cmp-window-picker__app {
    font-family: "DM Mono", monospace;
    font-weight: 500;
    font-size: 14px;
    color: var(--ink);
  }
  .cmp-window-picker__title {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cmp-window-picker__pickdiff {
    margin-top: var(--sp-md);
    text-align: center;
  }
  .cmp-window-picker__pickdiff-btn {
    background: none;
    border: none;
    color: var(--ink-dim);
    font-family: "DM Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.06em;
    cursor: pointer;
    padding: var(--sp-sm);
  }
  .cmp-window-picker__pickdiff-btn:hover {
    color: var(--phosphor);
  }
  .cmp-window-picker__privacy {
    display: flex;
    align-items: center;
    gap: var(--sp-md);
    padding: var(--sp-sm) var(--sp-md);
    background: var(--phosphor-soft);
    border-radius: 4px;
    margin-bottom: var(--sp-md);
  }
  .cmp-window-picker__privacy-heading {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--phosphor);
  }
  .cmp-window-picker__privacy-body {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink);
    line-height: 1.5;
  }
  .cmp-window-picker__grid {
    display: grid;
    grid-template-columns: repeat(3, 160px);
    gap: var(--sp-md);
    max-height: 280px;
    overflow-y: auto;
  }
  .cmp-window-picker__grid::-webkit-scrollbar { width: 6px; }
  .cmp-window-picker__grid::-webkit-scrollbar-track { background: var(--panel-deep); }
  .cmp-window-picker__grid::-webkit-scrollbar-thumb { background: var(--bezel-2); border-radius: 3px; }
  .cmp-window-picker__cell {
    width: 160px;
    height: 120px;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 4px;
    padding: var(--sp-sm);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: var(--sp-xs);
    transition: border-color var(--motion-snap) ease-out;
  }
  .cmp-window-picker__cell:hover {
    border-color: var(--phosphor-dim);
  }
  .cmp-window-picker__cell-thumb {
    flex: 1;
    background: var(--groove);
    border-radius: 2px;
  }
  .cmp-window-picker__cell-name {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  /* Non-DJ confirm modal */
  .cmp-window-picker__modal {
    position: fixed;
    inset: 0;
    z-index: 9000;
    background: rgba(7, 8, 10, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cmp-window-picker__modal[hidden] { display: none; }
  .cmp-window-picker__modal-box {
    width: 420px;
    padding: var(--sp-lg);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-2);
    border-radius: 8px;
    box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.8);
  }
  .cmp-window-picker__modal-heading {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--rec);
    margin-bottom: var(--sp-sm);
  }
  .cmp-window-picker__modal-body {
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink);
    line-height: 1.5;
    margin-bottom: var(--sp-md);
  }
  .cmp-window-picker__modal-actions {
    display: flex;
    gap: var(--sp-md);
    justify-content: flex-end;
  }
`;

registerStyle("cmp-window-picker", CSS);

export function WindowPicker(props: WindowPickerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-window-picker";

  if (props.mode === "hint" && props.detectedHint) {
    const hint = document.createElement("div");
    hint.className = "cmp-window-picker__hint";

    const thumb = document.createElement("div");
    thumb.className = "cmp-window-picker__thumb";
    if (props.detectedHint.thumbnail) {
      thumb.style.backgroundImage = `url(${JSON.stringify(props.detectedHint.thumbnail)})`;
    }

    const meta = document.createElement("div");
    meta.className = "cmp-window-picker__meta";
    const app = document.createElement("span");
    app.className = "cmp-window-picker__app";
    app.textContent = props.detectedHint.appName;
    const title = document.createElement("span");
    title.className = "cmp-window-picker__title";
    title.textContent = props.detectedHint.windowTitle;
    meta.append(app, title);

    const selectBtn = Button({
      variant: "primary",
      state: "armed",
      label: "Select",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: () => props.onSelect(props.detectedHint!.appName),
    });

    hint.append(thumb, meta, selectBtn);
    root.append(hint);

    const pickdiff = document.createElement("div");
    pickdiff.className = "cmp-window-picker__pickdiff";
    const pickBtn = document.createElement("button");
    pickBtn.type = "button";
    pickBtn.className = "cmp-window-picker__pickdiff-btn";
    // UI-SPEC §Step 2 "Window picker pick-different link" — VERBATIM
    pickBtn.textContent = "[ Pick a different window ↗ ]";
    pickBtn.addEventListener("click", () => props.onPickDifferent());
    pickdiff.append(pickBtn);
    root.append(pickdiff);
    return root;
  }

  // Enumeration mode
  const privacy = document.createElement("div");
  privacy.className = "cmp-window-picker__privacy";
  const ph = document.createElement("span");
  ph.className = "cmp-window-picker__privacy-heading";
  // UI-SPEC §Step 2 "Window picker privacy warning heading" — VERBATIM
  ph.textContent = "PRIVACY";
  const pb = document.createElement("span");
  pb.className = "cmp-window-picker__privacy-body";
  // UI-SPEC §Step 2 "Window picker privacy warning body" — VERBATIM
  pb.textContent = "vibemix only captures the window you pick — never your full screen";
  privacy.append(ph, pb);
  root.append(privacy);

  const grid = document.createElement("div");
  grid.className = "cmp-window-picker__grid";
  (props.allWindows ?? []).forEach((w) => {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "cmp-window-picker__cell";
    cell.dataset.id = w.id;
    const thumb = document.createElement("div");
    thumb.className = "cmp-window-picker__cell-thumb";
    if (w.thumbnail) thumb.style.backgroundImage = `url(${JSON.stringify(w.thumbnail)})`;
    const name = document.createElement("span");
    name.className = "cmp-window-picker__cell-name";
    name.textContent = w.name;
    cell.append(thumb, name);
    cell.addEventListener("click", () => props.onSelect(w.id));
    grid.append(cell);
  });
  root.append(grid);

  return root;
}

export interface NonDjConfirmProps {
  appName: string;
  onPickAnother: () => void;
  onContinueAnyway: () => void;
}

/* Modal overlay component for non-DJ-app confirm (UI-SPEC §9 Non-DJ confirm). */
export function NonDjConfirm(props: NonDjConfirmProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-window-picker__modal";
  const box = document.createElement("div");
  box.className = "cmp-window-picker__modal-box";
  const heading = document.createElement("div");
  heading.className = "cmp-window-picker__modal-heading";
  // UI-SPEC §Step 2 "Non-DJ confirm heading" — VERBATIM
  heading.textContent = "NOT A DJ APP";
  const body = document.createElement("div");
  body.className = "cmp-window-picker__modal-body";
  // UI-SPEC §Step 2 "Non-DJ confirm body" — VERBATIM template
  body.textContent =
    "vibemix works best with djay, rekordbox, serato, traktor, virtualdj — " +
    `continue with ${props.appName} anyway?`;
  const actions = document.createElement("div");
  actions.className = "cmp-window-picker__modal-actions";
  actions.append(
    Button({
      variant: "secondary",
      state: "idle",
      // UI-SPEC §Step 2 "Non-DJ confirm pick-another" — VERBATIM
      label: "↻ Pick another",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onPickAnother,
    }),
    Button({
      variant: "primary",
      state: "armed",
      // UI-SPEC §Step 2 "Non-DJ confirm continue" — VERBATIM
      label: "Continue anyway",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onContinueAnyway,
    })
  );
  box.append(heading, body, actions);
  root.append(box);
  return root;
}
