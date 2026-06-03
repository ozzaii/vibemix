// SPDX-License-Identifier: Apache-2.0
//
// The Cmd+K command palette: the desktop-native "understand and act in one
// keystroke" surface. Vanilla-TS, no cmdk dependency. A small case-insensitive
// subsequence matcher ranks actions; arrow keys move the selection, Enter runs
// it, Esc (or a backdrop click) closes. Actions are provided lazily so the
// caller can mix static commands with dynamic ones.
//
// Visibility is the palette's own `is-open` class (see shell.css); the binding
// (Cmd+K) lives in DesktopShell, mirroring Bravoh's "binding in the hook,
// component stays pure render" split.

export interface PaletteAction {
  readonly id: string;
  readonly label: string;
  /** Broad bucket shown as a quiet list divider. Navigation rows stay above
   *  direct controls so Cmd+K reads as "where do you want to go?" first. */
  readonly section?: "navigate" | "control";
  /** A short descriptive subtitle, inline after the label (e.g. "the live
   *  co-host"). NOT the shortcut — that is `accel`, in its own right-aligned
   *  slot, so a description and a keybind never share one overloaded field. */
  readonly hint?: string;
  /** The keyboard accelerator, shown right-aligned so the palette doubles as the
   *  shortcut cheat-sheet (a bare digit for surfaces, matching the sidebar; a
   *  chord like "Ctrl+]" for commands). Omitted when the action has no shortcut. */
  readonly accel?: string;
  readonly glyph?: string;
  readonly aliases?: readonly string[];
  readonly status?: string;
  readonly statusKind?: "current" | "ready" | "warn" | "quiet";
  run(): void;
}

export interface PaletteSummaryCell {
  readonly label: string;
  readonly value: string;
  readonly tone?: "ok" | "warn" | "muted";
}

export interface CommandPalette {
  readonly el: HTMLElement;
  open(): void;
  close(): void;
  toggle(): void;
  isOpen(): boolean;
}

/** Case-insensitive subsequence score (every query char appears in order).
 *  Lower scores are better; -1 means no match. */
function matchScore(query: string, text: string): number {
  if (!query) return 0;
  const haystack = text.toLowerCase();
  const needle = query.toLowerCase();
  if (haystack === needle) return 0;
  if (haystack.startsWith(needle)) return 1;
  if (haystack.includes(needle)) return 2;
  let i = 0;
  for (const char of needle) {
    i = haystack.indexOf(char, i);
    if (i === -1) return -1;
    i += 1;
  }
  return 6;
}

export interface CommandPaletteOptions {
  /** Elements to mark inert + aria-hidden while the dialog is open, so the
   *  background is unreachable by Tab AND a screen-reader's browse cursor.
   *  Cleared before focus restoration on close. */
  readonly inertWhileOpen?: readonly HTMLElement[];
  /** Small honest status strip for the current shell state. */
  readonly summaryProvider?: () => readonly PaletteSummaryCell[];
}

const LISTBOX_ID = "shell-palette-listbox";
const optionId = (index: number): string => `shell-palette-opt-${index}`;

const sectionLabel = (section: PaletteAction["section"]): string =>
  section === "control" ? "Controls" : "Surfaces";

function scoreAction(query: string, action: PaletteAction): number {
  const fields = [
    action.label,
    ...(action.aliases ?? []),
    action.hint ?? "",
    action.status ?? "",
    action.accel ?? "",
    action.section ?? "",
  ];
  let best = -1;
  fields.forEach((field, index) => {
    const score = matchScore(query, field);
    if (score < 0) return;
    const weighted = score * 10 + index;
    if (best < 0 || weighted < best) best = weighted;
  });
  return best;
}

export function createCommandPalette(
  actionsProvider: () => PaletteAction[],
  options: CommandPaletteOptions = {},
): CommandPalette {
  const overlay = document.createElement("div");
  overlay.className = "shell-palette";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Command palette");

  const panel = document.createElement("div");
  panel.className = "palette-panel";

  const header = document.createElement("div");
  header.className = "palette-head";
  header.innerHTML =
    `<div class="palette-title">Command deck</div>` +
    `<div class="palette-subtitle">Jump surfaces, inspect state, or run a local control.</div>`;

  const summary = document.createElement("div");
  summary.className = "palette-summary";
  summary.setAttribute("aria-label", "Current shell state");
  header.append(summary);

  // Combobox-controls-listbox pattern: the input keeps DOM focus and points at
  // the visually-selected option via aria-activedescendant, so AT tracks the
  // arrow-key selection (the option rows are not individual tab stops).
  const input = document.createElement("input");
  input.className = "palette-input";
  input.type = "text";
  // Verb-led, not a four-noun feature list ("proof" was engine jargon, too).
  input.placeholder = "Jump to a surface or run a control…";
  input.setAttribute("aria-label", "Command palette query");
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-controls", LISTBOX_ID);
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-expanded", "false");

  const list = document.createElement("div");
  list.className = "palette-list";
  list.id = LISTBOX_ID;
  list.setAttribute("role", "listbox");

  const footer = document.createElement("div");
  footer.className = "palette-footer";
  footer.innerHTML =
    `<span><kbd>Enter</kbd> run</span>` +
    `<span><kbd>Esc</kbd> close</span>` +
    `<span><kbd>↑</kbd><kbd>↓</kbd> move</span>`;

  panel.append(header, input, list, footer);
  overlay.append(panel);

  let filtered: PaletteAction[] = [];
  let selected = 0;
  // The control that had focus when the palette opened, so close() can return
  // focus there (the input we were on becomes hidden on close).
  let trigger: HTMLElement | null = null;

  const renderSummary = (): void => {
    const cells = options.summaryProvider?.() ?? [];
    summary.replaceChildren();
    for (const cell of cells) {
      const item = document.createElement("span");
      item.className = "palette-summary-cell";
      item.dataset.tone = cell.tone ?? "muted";
      item.innerHTML =
        `<span class="ps-label">${cell.label}</span>` +
        `<span class="ps-value">${cell.value}</span>`;
      summary.append(item);
    }
  };

  const renderList = (): void => {
    const query = input.value.trim();
    filtered = actionsProvider()
      .map((action, index) => ({ action, index, score: scoreAction(query, action) }))
      .filter((entry) => entry.score >= 0)
      .sort((a, b) => (query ? a.score - b.score || a.index - b.index : a.index - b.index))
      .map((entry) => entry.action);
    if (selected >= filtered.length) selected = Math.max(0, filtered.length - 1);
    list.replaceChildren();
    if (filtered.length === 0) {
      const empty = document.createElement("div");
      empty.className = "palette-empty";
      empty.textContent = "Nothing matches.";
      list.append(empty);
      updateActiveDescendant();
      return;
    }
    let currentSection: PaletteAction["section"] | undefined;
    filtered.forEach((action, index) => {
      if (action.section !== currentSection) {
        currentSection = action.section;
        const heading = document.createElement("div");
        heading.className = "palette-section";
        heading.setAttribute("role", "presentation");
        heading.textContent = sectionLabel(currentSection);
        list.append(heading);
      }
      const row = document.createElement("button");
      row.type = "button";
      row.className = "palette-item";
      row.id = optionId(index);
      row.setAttribute("role", "option");
      // Listbox options are driven by Arrow/Enter on the input, not Tab — keep
      // them out of the tab order so the input stays the dialog's only tab stop.
      row.tabIndex = -1;
      row.setAttribute("aria-selected", index === selected ? "true" : "false");
      // Three slots: the mark, the label + its inline description, and the
      // right-aligned accelerator. The description and accelerator each render
      // ONLY when present, so a command with no shortcut shows no empty chip and
      // a surface with no subtitle shows no dangling slot.
      row.innerHTML =
        `<span class="pi-glyph" aria-hidden="true">${action.glyph ?? "›"}</span>` +
        `<span class="pi-main">` +
        `<span class="pi-title"><span class="pi-label">${action.label}</span>` +
        (action.hint ? `<span class="pi-desc">${action.hint}</span>` : "") +
        `</span>` +
        (action.status
          ? `<span class="pi-state" data-kind="${action.statusKind ?? "quiet"}">${action.status}</span>`
          : "") +
        `</span>` +
        (action.accel ? `<span class="pi-accel">${action.accel}</span>` : "");
      row.addEventListener("mousemove", () => {
        if (selected !== index) {
          selected = index;
          syncSelection();
        }
      });
      row.addEventListener("click", () => run(index));
      list.append(row);
    });
    updateActiveDescendant();
  };

  // Point the combobox at the selected option (or clear it when the list is
  // empty), so AT announces the arrow-key selection without moving DOM focus.
  const updateActiveDescendant = (): void => {
    if (filtered.length > 0) input.setAttribute("aria-activedescendant", optionId(selected));
    else input.removeAttribute("aria-activedescendant");
  };

  const syncSelection = (): void => {
    const rows = list.querySelectorAll<HTMLElement>(".palette-item");
    rows.forEach((row, index) => {
      row.setAttribute("aria-selected", index === selected ? "true" : "false");
      if (index === selected) row.scrollIntoView({ block: "nearest" });
    });
    updateActiveDescendant();
  };

  const run = (index: number): void => {
    const action = filtered[index];
    if (!action) return;
    close();
    action.run();
  };

  const open = (): void => {
    // Capture the launching context BEFORE we move focus into the dialog.
    trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    // Make the background unreachable to Tab AND the SR browse cursor.
    for (const el of options.inertWhileOpen ?? []) {
      el.inert = true;
      el.setAttribute("aria-hidden", "true");
    }
    overlay.classList.add("is-open");
    input.setAttribute("aria-expanded", "true");
    input.value = "";
    selected = 0;
    renderSummary();
    renderList();
    input.focus();
  };

  const close = (): void => {
    overlay.classList.remove("is-open");
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    // Un-inert the background BEFORE restoring focus — the trigger lives inside
    // an inert region and can't receive focus until that's cleared.
    for (const el of options.inertWhileOpen ?? []) {
      el.inert = false;
      el.removeAttribute("aria-hidden");
    }
    if (trigger?.isConnected) trigger.focus();
    trigger = null;
  };

  const toggle = (): void => {
    if (overlay.classList.contains("is-open")) close();
    else open();
  };

  const isOpen = (): boolean => overlay.classList.contains("is-open");

  input.addEventListener("input", () => {
    selected = 0;
    renderList();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      selected = Math.min(selected + 1, Math.max(0, filtered.length - 1));
      syncSelection();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      selected = Math.max(selected - 1, 0);
      syncSelection();
    } else if (event.key === "Enter") {
      event.preventDefault();
      run(selected);
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation(); // the shell's Esc-closes-panel must not also fire
      close();
    } else if (event.key === "Tab") {
      // Focus trap: the overlay is aria-modal=true, so Tab must not escape into
      // the focus-hidden background. The input is the only tab stop, so holding
      // focus here honors the modal contract.
      event.preventDefault();
    }
  });

  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) close();
  });

  return { el: overlay, open, close, toggle, isOpen };
}
