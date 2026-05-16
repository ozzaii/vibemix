// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — Error banner with reason→copy map.

export type DebriefErrorReason =
  | "events_missing"
  | "session_too_short"
  | "invalid_session_dir"
  | "sidecar_crashed"
  | "tldr_generation_failed"
  | "drills_generation_failed"
  | "port_in_use"
  | "unknown_kind";

const REASON_COPY: Record<DebriefErrorReason, string> = {
  events_missing:
    "This session has no event data — try a longer recording.",
  session_too_short:
    "Session is too short for a meaningful debrief (need ≥ 5 minutes).",
  invalid_session_dir:
    "That recording can't be opened — its location doesn't match the expected layout.",
  sidecar_crashed: "Debrief crashed unexpectedly. Try reopening.",
  tldr_generation_failed:
    "Couldn't generate the voiced summary. Try refreshing.",
  drills_generation_failed:
    "Couldn't generate drills with valid citations. Try refreshing.",
  port_in_use:
    "Port 8766 is already taken by another process. Close the other debrief window and reopen.",
  unknown_kind:
    "Received an unknown message kind from the backend. Try reopening.",
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
