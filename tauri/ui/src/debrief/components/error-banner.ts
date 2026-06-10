// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — Error banner with reason→copy map.

export type DebriefErrorReason =
  | "events_missing"
  | "session_too_short"
  | "invalid_session_dir"
  | "sidecar_crashed"
  | "tldr_generation_failed"
  | "drills_generation_failed"
  | "llm_unavailable"
  | "port_in_use"
  | "unknown_kind";

const REASON_COPY: Record<DebriefErrorReason, string> = {
  events_missing:
    "This session has no event data. Try a longer recording.",
  session_too_short:
    "Session is too short for a meaningful debrief (need ≥ 5 minutes).",
  invalid_session_dir:
    "That recording can't be opened. Its location doesn't match the expected layout.",
  sidecar_crashed: "Debrief crashed unexpectedly. Try reopening.",
  tldr_generation_failed:
    "Couldn't generate the voiced summary. Try refreshing.",
  drills_generation_failed:
    "Couldn't generate drills with valid citations. Try refreshing.",
  llm_unavailable:
    "Sven's brain is unreachable, so drills and the voiced recap are skipped this time. Chapters and the replay below are still from your set.",
  port_in_use:
    "Another debrief window is already open. Close it and reopen this one.",
  unknown_kind:
    "The review hit something it didn't understand. Try reopening.",
};

export function showErrorBanner(
  container: HTMLElement,
  reason: string,
  message = "",
): void {
  const key = (reason as DebriefErrorReason) in REASON_COPY
    ? (reason as DebriefErrorReason)
    : null;
  const copy = key ? REASON_COPY[key] : message || "An unknown error occurred.";

  container.textContent = "";
  container.hidden = false;
  container.dataset.reason = reason;

  const text = document.createElement("p");
  text.className = "vmx-debrief-error-text";
  text.textContent = copy;

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "vmx-debrief-error-dismiss";
  dismiss.textContent = "Dismiss";
  dismiss.addEventListener("click", () => {
    container.hidden = true;
    container.textContent = "";
  });

  container.append(text, dismiss);
}

export function reasonToCopy(reason: string): string {
  return (REASON_COPY as Record<string, string>)[reason] ?? "";
}

/** Honest waiting line while the sidecar boots/generates — NOT an error.
 *  No dismiss control; the window clears it on the first successful
 *  connection (see debrief-window.ts `open` listener). */
export function showWorkingBanner(container: HTMLElement): void {
  container.textContent = "";
  container.hidden = false;
  container.dataset.reason = "still_working";

  const text = document.createElement("p");
  text.className = "vmx-debrief-error-text";
  text.textContent =
    "Sven is still putting your debrief together. The first pass can take a minute.";

  container.append(text);
}
