// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — DrillsPanel: 3 SBI/STAR-AR cards with citation chip.

export interface DrillPayload {
  situation: string;
  behavior: string;
  impact: string;
  action_recommended: string;
  citation: string;
}

export interface CitationClickEvent extends CustomEvent {
  detail: { citation: string };
}

export function mountDrillsPanel(
  container: HTMLElement,
  drills: DrillPayload[],
): void {
  container.textContent = "";
  for (let i = 0; i < drills.length; i += 1) {
    const d = drills[i];
    if (!d) continue;
    const article = document.createElement("article");
    article.className = "vmx-drill";
    article.dataset.drillIndex = String(i);

    const h3 = document.createElement("h3");
    h3.className = "vmx-drill-title";
    h3.textContent = `Drill ${i + 1}`;

    const dl = document.createElement("dl");
    dl.className = "vmx-drill-fields";
    for (const [label, value] of [
      ["Situation", d.situation],
      ["Behavior", d.behavior],
      ["Impact", d.impact],
      ["Action", d.action_recommended],
    ] as const) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;  // textContent → no XSS surface
      dl.append(dt, dd);
    }

    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "vmx-drill-citation";
    chip.textContent = d.citation;
    chip.dataset.citation = d.citation;
    chip.title = "Click to see evidence";
    chip.addEventListener("click", (e) => {
      e.stopPropagation();
      container.dispatchEvent(
        new CustomEvent("citation-click", {
          detail: { citation: d.citation },
          bubbles: true,
        }),
      );
    });

    article.append(h3, dl, chip);
    container.append(article);
  }
}
