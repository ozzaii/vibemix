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

// One noun per concept across the whole surface: the segments are
// "moments", the voiced artifact is the "recap", the surface itself is
// the "debrief". The same screen once said chapters/regions/TRACKS and
// TL;DR/voiced summary/recap at the same time.
const REASON_COPY: Record<DebriefErrorReason, string> = {
  events_missing:
    "I didn't catch anything in that session to debrief. Try a longer set.",
  session_too_short:
    "That set is too short for a fair debrief. Give me at least five minutes of music.",
  invalid_session_dir:
    "That recording can't be opened. It isn't a session I saved, so I can't replay it.",
  sidecar_crashed: "Debrief crashed unexpectedly. Try reopening.",
  tldr_generation_failed:
    "Couldn't put your recap together. Try reopening.",
  drills_generation_failed:
    "Couldn't build drills I can stand behind this time. Try reopening.",
  llm_unavailable:
    "Sven's brain is unreachable, so drills and the recap are skipped this time. Your moments and the replay below are still from your set.",
  port_in_use:
    "Another debrief window is already open. Close it and reopen this one.",
  unknown_kind:
    "The debrief hit something it didn't understand. Try reopening.",
};

export function showErrorBanner(
  container: HTMLElement,
  reason: string,
  message = "",
): void {
  const key = (reason as DebriefErrorReason) in REASON_COPY
    ? (reason as DebriefErrorReason)
    : null;
  // Unmapped reasons can carry raw sidecar prose; that belongs in the
  // console for QA, not on the surface.
  if (!key && message) {
    console.warn(`[debrief] unmapped error reason "${reason}": ${message}`);
  }
  const copy = key
    ? REASON_COPY[key]
    : "Something went wrong putting this debrief together. Try reopening.";

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

/** The panels each boot with a skeleton line claiming live work
 *  ("Generating drills…"). A terminal error must resolve those too: a
 *  banner saying drills are skipped over a panel still claiming
 *  generation is two instruments disagreeing. Scoped per reason — a
 *  TL;DR-only failure leaves panels whose work is still real alone. */
export const SKELETON_TERMINAL_COPY = {
  morning: "Nothing to listen back to this time.",
  tldr: "No recap this time.",
  drills: "No drills this time.",
} as const;

export type SkeletonHostKey = keyof typeof SKELETON_TERMINAL_COPY;

export interface SkeletonHosts {
  morning: HTMLElement | null;
  tldr: HTMLElement | null;
  drills: HTMLElement | null;
}

export function resolveSkeletonsToTerminal(
  hosts: SkeletonHosts,
  reason: string,
): void {
  const scope: SkeletonHostKey[] =
    reason === "tldr_generation_failed"
      ? ["tldr"]
      : reason === "drills_generation_failed"
        ? ["drills"]
        : ["morning", "tldr", "drills"];
  for (const key of scope) {
    const host = hosts[key];
    // No skeleton means a success frame already resolved this panel —
    // never overwrite real content with terminal copy.
    if (!host || !host.querySelector(".vmx-debrief-skeleton")) continue;
    host.textContent = "";
    const line = document.createElement("p");
    line.className = "vmx-debrief-skeleton";
    line.dataset.state = "settled";
    line.textContent = SKELETON_TERMINAL_COPY[key];
    host.append(line);
  }
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
