// SPDX-License-Identifier: Apache-2.0
// Plan 42-03 Task 2 · ear-test sign-off toggle (debrief window).
//
// Wired into the Phase 29 debrief window per D-GATE-07. Renders an
// opt-in toggle: when ON, a form expands with the 4 slop-flag
// checkboxes + free-form textarea + Sign off button. Submit posts the
// structured payload to the Python writer
// (`src/vibemix/debrief/ear_test_capture.py::write_ear_test_log`) via
// Tauri IPC, with a DebriefWsClient fallback for dev mode.
//
// Copy is Turkish-mix per CLAUDE.md tone · single-DJ regime (signed_by
// pinned to "kaan" in the schema).

import { showErrorBanner } from "./error-banner.js";

// ---------------------------------------------------------------------------
// Types · mirror eval/ear-test-logs/schema.json
// ---------------------------------------------------------------------------

export type EarTestGenre =
  | "hard_tek"
  | "techno"
  | "house"
  | "hip_hop"
  | "dnb"
  | "dubstep"
  | "other";

export interface SlopFlags {
  felt_slop: boolean;
  felt_scripted: boolean;
  felt_late: boolean;
  felt_generic: boolean;
}

export interface EarTestSubmission {
  session_id: string;
  started_at: string;
  duration_s: number;
  genre: EarTestGenre;
  slop_flags: SlopFlags;
  free_form: string;
  signed_by: "kaan";
  signed_at: string;
}

export interface EarTestMountPayload {
  session_id: string;
  started_at?: string;
  duration_s: number;
  genre: EarTestGenre | string;
}

// Tauri IPC shim · keeps the file importable in dev/test without the
// Tauri runtime.
interface TauriWindow {
  __TAURI__?: {
    invoke: (cmd: string, args: Record<string, unknown>) => Promise<unknown>;
  };
}

// Optional WS fallback · passed by the bootstrap when dev-mode capture
// goes via the existing 8766 channel.
export interface EarTestWsSink {
  send: (msg: { kind: "ear-test-submit"; payload: EarTestSubmission }) => void;
}

const SLOP_FLAG_LABELS: Array<[keyof SlopFlags, string]> = [
  ["felt_slop", "AI slop'ladı mı? / Felt slop?"],
  ["felt_scripted", "Felt scripted?"],
  ["felt_late", "Felt late?"],
  ["felt_generic", "Felt generic?"],
];

const GENRE_OPTIONS: EarTestGenre[] = [
  "hard_tek",
  "techno",
  "house",
  "hip_hop",
  "dnb",
  "dubstep",
  "other",
];

const TOGGLE_LABEL =
  "Bu session'ı release-gate için işaretle / Rate this session for release-gate";

const FORM_HEADER =
  "Ear-test sign-off: 30min minimum, ≥2 genres in 14d window";

// ---------------------------------------------------------------------------
// Mount
// ---------------------------------------------------------------------------

export function mountEarTestToggle(
  rootEl: HTMLElement | null,
  payload: EarTestMountPayload,
  options: { wsSink?: EarTestWsSink; errorBannerEl?: HTMLElement | null } = {},
): void {
  if (!rootEl) return;

  rootEl.textContent = "";
  rootEl.dataset.sessionId = payload.session_id;

  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  toggleBtn.className = "vmx-debrief-ear-test-toggle-btn";
  toggleBtn.setAttribute("aria-expanded", "false");
  toggleBtn.textContent = TOGGLE_LABEL;

  const formEl = document.createElement("section");
  formEl.className = "vmx-debrief-ear-test-form";
  formEl.hidden = true;
  formEl.setAttribute("aria-label", "Ear-test sign-off form");

  toggleBtn.addEventListener("click", () => {
    const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
    toggleBtn.setAttribute("aria-expanded", expanded ? "false" : "true");
    formEl.hidden = expanded;
  });

  // ----- Header -----
  const header = document.createElement("h2");
  header.className = "vmx-debrief-section-title";
  header.textContent = FORM_HEADER;
  formEl.append(header);

  // ----- Genre dropdown (pre-filled from payload, editable) -----
  const genreLabel = document.createElement("label");
  genreLabel.className = "vmx-debrief-ear-test-field";
  genreLabel.textContent = "Genre";
  const genreSelect = document.createElement("select");
  genreSelect.className = "vmx-debrief-ear-test-genre";
  for (const g of GENRE_OPTIONS) {
    const opt = document.createElement("option");
    opt.value = g;
    opt.textContent = g;
    genreSelect.append(opt);
  }
  const initialGenre = (GENRE_OPTIONS as string[]).includes(payload.genre)
    ? (payload.genre as EarTestGenre)
    : "other";
  genreSelect.value = initialGenre;
  genreLabel.append(genreSelect);
  formEl.append(genreLabel);

  // ----- Slop-flag checkboxes -----
  const flagsFieldset = document.createElement("fieldset");
  flagsFieldset.className = "vmx-debrief-ear-test-flags";
  const flagsLegend = document.createElement("legend");
  flagsLegend.textContent = "Slop flags (tick if observed)";
  flagsFieldset.append(flagsLegend);

  const checkboxes: Map<keyof SlopFlags, HTMLInputElement> = new Map();
  for (const [key, label] of SLOP_FLAG_LABELS) {
    const wrap = document.createElement("label");
    wrap.className = "vmx-debrief-ear-test-flag";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.dataset.flag = key;
    checkboxes.set(key, cb);
    const span = document.createElement("span");
    span.textContent = label;
    wrap.append(cb, span);
    flagsFieldset.append(wrap);
  }
  formEl.append(flagsFieldset);

  // ----- Free-form textarea -----
  const notesLabel = document.createElement("label");
  notesLabel.className = "vmx-debrief-ear-test-field";
  notesLabel.textContent = "Notes";
  const notes = document.createElement("textarea");
  notes.className = "vmx-debrief-ear-test-notes";
  notes.maxLength = 4000;
  notes.placeholder = "Optional notes: what worked, what didn't";
  notes.rows = 4;
  notesLabel.append(notes);
  formEl.append(notesLabel);

  // ----- Submit -----
  const submit = document.createElement("button");
  submit.type = "button";
  submit.className = "vmx-debrief-ear-test-submit";
  submit.textContent = "Sign off";
  formEl.append(submit);

  const confirmation = document.createElement("p");
  confirmation.className = "vmx-debrief-ear-test-confirmation";
  confirmation.hidden = true;
  formEl.append(confirmation);

  submit.addEventListener("click", () => {
    submit.disabled = true;
    const submission = buildSubmission(
      payload,
      genreSelect.value as EarTestGenre,
      checkboxes,
      notes.value,
    );
    handleSubmit(submission, options)
      .then(() => {
        confirmation.hidden = false;
        confirmation.textContent = `Signed off · ${submission.session_id}`;
        // Collapse the form to mirror the existing "saved" pattern of
        // chapter-list etc.
        formEl.hidden = true;
        toggleBtn.setAttribute("aria-expanded", "false");
        toggleBtn.disabled = true;
        toggleBtn.textContent = "Signed off for release-gate ✓";
      })
      .catch((err) => {
        submit.disabled = false;
        if (options.errorBannerEl) {
          showErrorBanner(
            options.errorBannerEl,
            "tldr_generation_failed",
            String(err?.message ?? err),
          );
        } else {
          confirmation.hidden = false;
          confirmation.textContent = `Submit failed: ${String(err)}`;
        }
      });
  });

  rootEl.append(toggleBtn, formEl);
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function buildSubmission(
  mount: EarTestMountPayload,
  genre: EarTestGenre,
  checkboxes: Map<keyof SlopFlags, HTMLInputElement>,
  notes: string,
): EarTestSubmission {
  const now = new Date();
  const startedAt =
    mount.started_at ??
    new Date(now.getTime() - mount.duration_s * 1000).toISOString();
  const slopFlags: SlopFlags = {
    felt_slop: checkboxes.get("felt_slop")?.checked ?? false,
    felt_scripted: checkboxes.get("felt_scripted")?.checked ?? false,
    felt_late: checkboxes.get("felt_late")?.checked ?? false,
    felt_generic: checkboxes.get("felt_generic")?.checked ?? false,
  };
  return {
    session_id: mount.session_id,
    started_at: startedAt,
    duration_s: mount.duration_s,
    genre,
    slop_flags: slopFlags,
    free_form: notes,
    signed_by: "kaan",
    signed_at: now.toISOString(),
  };
}

async function handleSubmit(
  submission: EarTestSubmission,
  options: { wsSink?: EarTestWsSink },
): Promise<void> {
  // Prefer Tauri IPC when the runtime is present (the real desktop app
  // path). Fall back to the WS sink for dev / test contexts.
  const tauri = (window as unknown as TauriWindow).__TAURI__;
  if (tauri?.invoke) {
    await tauri.invoke("write_ear_test_log", { payload: submission });
    return;
  }
  if (options.wsSink) {
    options.wsSink.send({ kind: "ear-test-submit", payload: submission });
    return;
  }
  throw new Error("no submission channel · Tauri IPC and WS sink both absent");
}
