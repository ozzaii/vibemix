// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — Click-only citation tooltip.

export interface CitationTooltipPayload {
  event_id: string;
  evidence_text: string;
  timestamp: number;
  found: boolean;
}

export function showCitationTooltip(
  container: HTMLElement,
  payload: CitationTooltipPayload,
  anchor?: { x: number; y: number },
): void {
  container.textContent = "";
  container.hidden = false;
  container.dataset.eventId = payload.event_id;

  if (!payload.found) {
    const empty = document.createElement("p");
    empty.className = "vmx-debrief-tooltip-empty";
    empty.textContent = "No evidence found for this citation.";
    container.append(empty);
  } else {
    const evidence = document.createElement("p");
    evidence.className = "vmx-debrief-tooltip-evidence";
    evidence.textContent = payload.evidence_text;

    const ts = document.createElement("p");
    ts.className = "vmx-debrief-tooltip-ts";
    const m = Math.floor(payload.timestamp / 60);
    const s = Math.floor(payload.timestamp % 60)
      .toString()
      .padStart(2, "0");
    ts.textContent = `${m}:${s}`;

    container.append(evidence, ts);
  }

  if (anchor) {
    container.style.left = `${anchor.x}px`;
    container.style.top = `${anchor.y}px`;
  }

  // Auto-dismiss handlers — outside click + Escape.
  const dismiss = (e: Event) => {
    if (e.type === "keydown" && (e as KeyboardEvent).key !== "Escape") return;
    if (e.type === "click" && container.contains(e.target as Node)) return;
    container.hidden = true;
    document.removeEventListener("click", dismiss, true);
    document.removeEventListener("keydown", dismiss);
  };
  // setTimeout so the click that opened the tooltip doesn't immediately
  // close it.
  setTimeout(() => {
    document.addEventListener("click", dismiss, true);
    document.addEventListener("keydown", dismiss);
  }, 0);
}

export function hideCitationTooltip(container: HTMLElement): void {
  container.hidden = true;
  container.textContent = "";
}
