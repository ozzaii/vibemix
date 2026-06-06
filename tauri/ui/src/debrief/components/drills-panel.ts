// SPDX-License-Identifier: Apache-2.0
// Plan 29-05 Task 2 — DrillsPanel: 3 SBI/STAR-AR cards with citation chip.

export interface DrillPayload {
  situation: string;
  behavior: string;
  impact: string;
  action_recommended: string;
  citation: string;
  learn_referral?: LearnReferralPayload | null;
}

export interface LearnReferralPayload {
  lesson_id: string;
  course_id: string;
  course_label: string;
  skill_id: string;
  skill_label: string;
  title: string;
  reason: string;
  cta: string;
}

export interface CitationClickEvent extends CustomEvent {
  detail: { citation: string };
}

export interface LearnReferralClickEvent extends CustomEvent {
  detail: { referral: LearnReferralPayload };
}

export type MomentFeedbackVerdict = "agree" | "disagree" | "unclear";
export type MomentFeedbackSurface = "transition" | "live_pill" | "cue";

export interface MomentFeedbackClickEvent extends CustomEvent {
  detail: {
    momentId: string;
    citationId: string;
    verdict: MomentFeedbackVerdict;
    surface: MomentFeedbackSurface;
  };
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
    const momentId = `drill-${i}`;
    const surface = feedbackSurfaceForCitation(d.citation);

    // The situation IS the title (the real line); "Drill N" was template filler.
    const h3 = document.createElement("h3");
    h3.className = "vmx-drill-title";
    h3.textContent = d.situation;

    const dl = document.createElement("dl");
    dl.className = "vmx-drill-fields";
    for (const [label, value] of [
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

    const feedback = document.createElement("div");
    feedback.className = "vmx-drill-feedback";
    feedback.setAttribute("aria-label", "moment feedback");
    for (const [verdict, label] of [
      ["agree", "right"],
      ["disagree", "off"],
      ["unclear", "?"],
    ] as const) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "vmx-drill-feedback__btn";
      button.dataset.verdict = verdict;
      button.setAttribute("aria-pressed", "false");
      button.title = `Mark this debrief moment ${label}`;
      button.textContent = label;
      button.addEventListener("click", (e) => {
        e.stopPropagation();
        for (const peer of Array.from(
          feedback.querySelectorAll(".vmx-drill-feedback__btn"),
        )) {
          peer.setAttribute("aria-pressed", "false");
        }
        button.setAttribute("aria-pressed", "true");
        container.dispatchEvent(
          new CustomEvent("moment-feedback-click", {
            detail: {
              momentId,
              citationId: d.citation,
              verdict,
              surface,
            },
            bubbles: true,
          }),
        );
      });
      feedback.append(button);
    }

    article.append(h3, dl, chip, feedback);
    if (d.learn_referral) {
      const referral = d.learn_referral;
      const route = document.createElement("div");
      route.className = "vmx-drill-learn-route";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "vmx-drill-learn";
      button.dataset.lessonId = referral.lesson_id;
      button.textContent = referral.cta || `Practice ${referral.title}`;
      button.title = referral.reason;
      button.addEventListener("click", (e) => {
        e.stopPropagation();
        container.dispatchEvent(
          new CustomEvent("learn-referral-click", {
            detail: { referral },
            bubbles: true,
          }),
        );
      });

      const meta = document.createElement("span");
      meta.className = "vmx-drill-learn-meta";
      meta.textContent = `${referral.skill_label} · ${referral.lesson_id}`;

      const reason = document.createElement("span");
      reason.className = "vmx-drill-learn-reason";
      reason.textContent = referral.reason;

      route.append(button, meta, reason);
      article.append(route);
    }
    container.append(article);
  }
}

function feedbackSurfaceForCitation(citation: string): MomentFeedbackSurface {
  return citation.trim().startsWith("[track:") ? "cue" : "transition";
}
