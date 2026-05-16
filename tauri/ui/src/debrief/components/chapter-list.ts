// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — chapter list (left sidebar).

export interface ChapterPayload {
  id: string;
  start: number;
  end: number;
  label: string;
  kind: string;
  citation_event_id: string;
}

export interface ChapterSelectedEvent extends CustomEvent {
  detail: {
    id: string;
    start: number;
    citation_event_id: string;
  };
}

export function mountChapterList(
  container: HTMLElement,
  chapters: ChapterPayload[],
): void {
  container.textContent = "";
  for (const c of chapters) {
    const li = document.createElement("li");
    li.className = "vmx-debrief-chapter";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-debrief-chapter-btn";
    btn.dataset.chapterId = c.id;
    btn.dataset.kind = c.kind;
    btn.textContent = c.label;
    btn.title = `${formatTime(c.start)}–${formatTime(c.end)}`;
    btn.addEventListener("click", () => {
      container.dispatchEvent(
        new CustomEvent("chapter-selected", {
          detail: {
            id: c.id,
            start: c.start,
            citation_event_id: c.citation_event_id,
          },
          bubbles: true,
        }),
      );
    });
    li.append(btn);
    container.append(li);
  }
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${sec}`;
}
