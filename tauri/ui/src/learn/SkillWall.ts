// SPDX-License-Identifier: Apache-2.0
//
// The Earned Wall (v11.0 "Earned") — the visible face of the mastery spine.
//
// Renders the six REQ-locked DJ skills at a glance: each half-lit Competent from
// lessons, Mastered ONLY from a cited live demo. The backend computes the stage
// (SkillTree.compute, single-source) and ships it on `ipc.learn.progress_state`
// as `skill_wall`; this paints it. `mastered`/`first_mastered_at` is set only by
// a citation-gated live demo (Invariant #2/#3), so the wall LITERALLY proves
// nothing was given — a real trophy case, not a pitch. No co-host voice enters
// here: it is a read-only render of deterministically-derived flags (slop-risk
// zero). Honest fallback throughout — never prettify a skill we don't know.

import "./styles/skill-wall.css";

/** One derived skill row off `ipc.learn.progress_state.progress.skill_wall`.
 *  Mirrors the generated shape in src/ipc/messages.ts (schema is the source). */
export interface SkillWallRow {
  skill_id: string;
  stage: "locked" | "competent" | "mastered";
  learn_fill: number;
  competent: boolean;
  live_proof_count: number;
  mastered: boolean;
  first_mastered_at: string | null;
  /** SURF-01: the plain "what's left to advance" line, single-sourced in Python
   *  (SkillTree). Empty string for Mastered (the proof line carries it). */
  what_remains: string;
}

/** Display names for the six REQ-locked skills. An unknown id falls back to its
 *  raw id (honest — we never invent a label). */
const SKILL_WALL_LABELS: Record<string, string> = {
  deck_control: "Deck Control",
  beatmatching: "Beatmatching",
  eq_mixing: "EQ Mixing",
  harmonic_mixing: "Harmonic Mixing",
  transitions: "Transitions",
  phrasing_performance: "Phrasing & Performance",
};

const STAGE_LABELS: Record<SkillWallRow["stage"], string> = {
  locked: "Locked",
  competent: "Competent",
  mastered: "Mastered",
};

/** SURF-04 dual-channel cue: a distinct SHAPE per stage so the wall reads with
 *  ZERO color perception (deuteranopia/protanopia/tritanopia). Decorative
 *  (aria-hidden) — the `STAGE_LABELS` word is the screen-reader semantic. */
const STAGE_GLYPHS: Record<SkillWallRow["stage"], string> = {
  locked: "○", // hollow — nothing earned yet
  competent: "◑", // half-lit — lessons done
  mastered: "★", // the trophy — earned in a live set
};

function labelFor(skillId: string): string {
  return SKILL_WALL_LABELS[skillId] ?? skillId;
}

/** The cited-proof line for a Mastered skill — shows ONLY what a live demo
 *  earned (count + the day it first flipped). Date is sliced from the ISO, not
 *  locale-formatted, so it is deterministic and slop-free. */
function proofLine(row: SkillWallRow): string {
  const n = row.live_proof_count;
  const demos = `${n} cited demo${n === 1 ? "" : "s"}`;
  const when = row.first_mastered_at ? ` · ${row.first_mastered_at.slice(0, 10)}` : "";
  return `${demos}${when}`;
}

function renderRow(row: SkillWallRow): HTMLLIElement {
  const li = document.createElement("li");
  li.className = "skill-wall__row";
  li.dataset.skill = row.skill_id;
  li.dataset.stage = row.stage;

  // SURF-04 dual-cue: the shape glyph leads (decorative — the stage word is the
  // semantic), so the row is distinguishable without any color perception.
  const glyph = document.createElement("span");
  glyph.className = "skill-wall__glyph";
  glyph.setAttribute("aria-hidden", "true");
  glyph.textContent = STAGE_GLYPHS[row.stage];

  const name = document.createElement("span");
  name.className = "skill-wall__name";
  name.textContent = labelFor(row.skill_id);

  const stage = document.createElement("span");
  stage.className = "skill-wall__stage";
  stage.textContent = STAGE_LABELS[row.stage];

  const fill = document.createElement("div");
  fill.className = "skill-wall__fill";
  const bar = document.createElement("i");
  // Clamp to [0,1] then percentage — the fill is the lesson-portion, always
  // visible even at Mastered (Competent is the floor under Mastered).
  const pct = Math.max(0, Math.min(1, row.learn_fill));
  bar.style.width = `${Math.round(pct * 100)}%`;
  fill.appendChild(bar);

  li.append(glyph, name, stage, fill);

  // SURF-01: the honest "what's left" line (empty for Mastered — the proof
  // line carries it there). Single-sourced in Python; we only paint it.
  if (row.what_remains) {
    const remains = document.createElement("span");
    remains.className = "skill-wall__remains";
    remains.textContent = row.what_remains;
    li.appendChild(remains);
  }

  // SURF-04 keyboard-nav: EVERY row is focusable so a keyboard-only user can
  // browse the whole tree and read each skill; the aria-label folds the stage +
  // the next-step (or the cited proof for Mastered) into one announced line.
  const announce = row.mastered ? proofLine(row) : row.what_remains;
  li.setAttribute("tabindex", "0");
  li.setAttribute(
    "aria-label",
    `${labelFor(row.skill_id)}, ${STAGE_LABELS[row.stage]}${announce ? `. ${announce}` : ""}`,
  );

  if (row.mastered) {
    // The trophy: tappable to its cited demo. Only Mastered earns the BUTTON
    // affordance (browsable ≠ activatable — the others are read-only).
    li.setAttribute("role", "button");
    li.setAttribute("aria-expanded", "false");
    const proof = document.createElement("span");
    proof.className = "skill-wall__proof";
    proof.textContent = proofLine(row);
    li.appendChild(proof);

    const toggle = (): void => {
      const open = li.getAttribute("aria-expanded") === "true";
      li.setAttribute("aria-expanded", open ? "false" : "true");
    };
    li.addEventListener("click", toggle);
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        toggle();
      }
    });
  }

  return li;
}

/** Pure render: a `<section.skill-wall>` of one row per input skill, in order. */
export function renderSkillWall(rows: SkillWallRow[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "skill-wall";
  section.dataset.wire = "learn.skill-wall";

  const head = document.createElement("header");
  head.className = "skill-wall__head";
  const title = document.createElement("h2");
  title.className = "skill-wall__title";
  title.textContent = "Earned";
  const sub = document.createElement("p");
  sub.className = "skill-wall__sub";
  sub.textContent = "Competent comes from the lessons. Mastered comes only from a cited live set.";
  head.append(title, sub);

  if (rows.length === 0) {
    // Honest-null: no snapshot yet (or fresh user). Say so, don't fake a wall.
    const empty = document.createElement("p");
    empty.className = "skill-wall__empty";
    empty.textContent = "Your skills light up as you learn — and earn their stars in a live set.";
    section.append(head, empty);
    return section;
  }

  const list = document.createElement("ol");
  list.className = "skill-wall__list";
  for (const row of rows) list.appendChild(renderRow(row));

  section.append(head, list);
  return section;
}

/** A subscription source: hand it a callback, get an unsubscribe. The default
 *  reads `skill_wall` off the `ipc.learn.progress_state` window event (the same
 *  CustomEvent the learn window listens to). Injected in tests. */
export type SkillWallSubscribe = (
  onRows: (rows: SkillWallRow[]) => void,
) => () => void;

function defaultSubscribe(onRows: (rows: SkillWallRow[]) => void): () => void {
  const handler = (ev: Event): void => {
    const detail = (ev as CustomEvent).detail as
      | { progress?: { skill_wall?: SkillWallRow[] } }
      | undefined;
    const wall = detail?.progress?.skill_wall;
    if (Array.isArray(wall)) onRows(wall);
  };
  window.addEventListener("ipc.learn.progress_state", handler);
  return () => window.removeEventListener("ipc.learn.progress_state", handler);
}

export interface MountedSkillWall {
  update(rows: SkillWallRow[]): void;
  teardown(): void;
}

export interface MountSkillWallOptions {
  initialRows?: SkillWallRow[];
  subscribe?: SkillWallSubscribe;
}

/** Mount the live Earned Wall into a host: paints the initial rows, then
 *  repaints on every pushed `progress_state` snapshot. Non-fatal by design — it
 *  owns one container element and tears down its own subscription. */
export function mountSkillWall(
  host: HTMLElement,
  opts: MountSkillWallOptions = {},
): MountedSkillWall {
  const container = document.createElement("div");
  container.className = "skill-wall-mount";
  host.appendChild(container);

  let rows = opts.initialRows ?? [];
  const paint = (): void => {
    container.replaceChildren(renderSkillWall(rows));
  };
  paint();

  const subscribe = opts.subscribe ?? defaultSubscribe;
  const unsubscribe = subscribe((next) => {
    rows = next;
    paint();
  });

  return {
    update(next: SkillWallRow[]): void {
      rows = next;
      paint();
    },
    teardown(): void {
      unsubscribe();
      container.remove();
    },
  };
}
