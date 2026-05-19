/* timecode.ts — center column track + timecode hero (v5 §01 SESSION SURFACE).
 *
 * v5 layout (per `mocks/vibemix-direction-final.html` .track-display):
 *   row 1: [now playing · BPM · KEY meta] | [recessed glass clock]
 *   row 2: huge Saira track title + Saira-light artist subtitle
 *   row 3: BPM / KEY / DECK meta cells
 *
 * Pure-function: idempotent re-renders via setTimecode(el, state) — only
 * textContent pokes, no DOM rebuild. The 250ms rAF cadence is owned by
 * SessionLayout. */

import { registerStyle } from "./_style-registry.js";

export interface TimecodeProps {
  clock: string;
  bpm: number | null;
  key: string | null;
  deck: string | null;
  track: { title: string; artist?: string | null } | null;
  genre: string | null;
}

const CSS = `
  .vmx-timecode {
    position: relative;
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    padding: var(--sp-5) var(--sp-5) var(--sp-4);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.65),
      0 24px 60px rgba(0, 0, 0, 0.65),
      0 0 0 1px rgba(255, 255, 255, 0.018);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
  }
  /* Faint diagonal glass-fingerprint streak — barely-there character */
  .vmx-timecode::after {
    content: '';
    position: absolute;
    top: 14%;
    right: -10%;
    width: 55%;
    height: 200px;
    background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.012), transparent);
    transform: rotate(-12deg);
    pointer-events: none;
    z-index: 0;
  }
  .vmx-timecode > * { position: relative; z-index: 1; }

  /* Top strip — live tag + session label */
  .vmx-timecode__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-4);
    padding-bottom: var(--sp-3);
    border-bottom: 1px solid var(--glass-edge);
  }
  .vmx-timecode__live {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    line-height: 1;
  }
  .vmx-timecode__live::before {
    /* 2026-05-19 /impeccable critique fix: demoted --glow-strong to
     * --glow-soft. DESIGN.md §4 reserves --glow-strong for the primary
     * action button at hover/press. The LIVE pip is an always-on idle
     * indicator, not a brand action. */
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: var(--glow-soft);
    animation: vmx-timecode-live-blink 1.4s ease-in-out infinite;
  }
  @keyframes vmx-timecode-live-blink {
    0%, 70% { opacity: 1; }
    85%     { opacity: 0.3; }
    100%    { opacity: 1; }
  }
  .vmx-timecode__sess {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    color: var(--silk-40);
    letter-spacing: 0.08em;
  }

  /* Track + clock — main row */
  .vmx-timecode__hero {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: end;
    gap: var(--sp-5);
  }
  .vmx-timecode__title-block {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    min-width: 0;
    overflow: hidden;
  }
  .vmx-timecode__nowplay {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 90, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-65);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    line-height: 1;
  }
  .vmx-timecode__nowplay .dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--silk-40);
  }
  .vmx-timecode__title {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 80, "wght" 700;
    font-size: 32px;
    line-height: 0.94;
    letter-spacing: -0.022em;
    text-transform: uppercase;
    color: var(--silk);
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
    word-break: normal;
    overflow-wrap: anywhere;
    text-wrap: balance;
    /* Cap to two visual lines via line-clamp; longer titles get ellipsis. */
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
  }
  .vmx-timecode__title .sub {
    display: block;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 13px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--silk-65);
    margin-top: 4px;
    text-shadow: none;
    -webkit-line-clamp: 1;
  }
  /* Empty state — when no track is detected */
  .vmx-timecode__title[data-empty="true"] {
    color: var(--silk-22);
    font-variation-settings: "wdth" 82, "wght" 500;
    font-size: 24px;
    line-height: 1;
    text-shadow: none;
  }

  /* Recessed clock display window */
  .vmx-timecode__display {
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    padding: 12px 18px 14px;
    border-radius: var(--rad-sm);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.9),
      inset 0 0 0 1px rgba(0, 0, 0, 0.55),
      inset 0 0 18px rgba(255, 138, 61, 0.035),
      0 0 0 1px rgba(255, 255, 255, 0.022);
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
  }
  .vmx-timecode__display::after {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, transparent 30%, transparent 80%, rgba(255, 138, 61, 0.028) 100%);
  }
  .vmx-timecode__display-lbl {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 8px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    line-height: 1;
    margin-bottom: 5px;
    display: block;
  }
  .vmx-timecode__hero-clock {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    font-size: 38px;
    line-height: 0.95;
    color: var(--silk);
    text-shadow: 0 0 6px rgba(255, 138, 61, 0.20);
    letter-spacing: -0.035em;
    display: block;
    user-select: none;
  }

  /* Bottom meta — BPM / KEY / DECK cells */
  .vmx-timecode__meta {
    display: flex;
    gap: var(--sp-5);
    padding-top: var(--sp-3);
    border-top: 1px solid var(--glass-edge);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    color: var(--silk-40);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-timecode__meta-cell {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
  }
  .vmx-timecode__meta-cell b {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 13px;
    color: var(--silk);
    font-weight: 500;
    letter-spacing: 0;
  }
`;

registerStyle("vmx-timecode", CSS);

export function renderTimecode(props: TimecodeProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-timecode";

  // 2026-05-19 /impeccable critique fix: timecode previously mounted its
  // own .border-anim sweep here, putting TWO concurrent perimeter sweeps
  // on the session deck (the outer one comes from SessionLayout). DESIGN.md
  // §5 restricts the sweep to the session deck only — the timecode lives
  // INSIDE that deck, so the deck's sweep is its sweep.

  // Top strip
  const top = document.createElement("div");
  top.className = "vmx-timecode__top";
  const live = document.createElement("span");
  live.className = "vmx-timecode__live";
  live.dataset.role = "live-tag";
  live.textContent = buildLiveLabel(props);
  top.append(live);
  const sess = document.createElement("span");
  sess.className = "vmx-timecode__sess";
  sess.dataset.role = "sess";
  sess.textContent = "VBMX · LIVE";
  top.append(sess);
  root.append(top);

  // Hero — title-block + display-window
  const hero = document.createElement("div");
  hero.className = "vmx-timecode__hero";

  const titleBlock = document.createElement("div");
  titleBlock.className = "vmx-timecode__title-block";
  const nowplay = document.createElement("span");
  nowplay.className = "vmx-timecode__nowplay";
  nowplay.dataset.role = "nowplay";
  nowplay.textContent = "NOW PLAYING";
  titleBlock.append(nowplay);
  const title = document.createElement("span");
  title.className = "vmx-timecode__title";
  title.dataset.role = "track-title";
  setTitleContent(title, props.track);
  titleBlock.append(title);
  hero.append(titleBlock);

  const display = document.createElement("div");
  display.className = "vmx-timecode__display";
  const displayLbl = document.createElement("span");
  displayLbl.className = "vmx-timecode__display-lbl";
  displayLbl.textContent = "ELAPSED";
  display.append(displayLbl);
  const clock = document.createElement("span");
  clock.className = "vmx-timecode__hero-clock";
  clock.dataset.role = "clock";
  clock.textContent = props.clock;
  display.append(clock);
  hero.append(display);
  root.append(hero);

  // Meta cells
  const meta = document.createElement("div");
  meta.className = "vmx-timecode__meta";
  meta.append(buildCell("BPM", formatBpm(props.bpm)));
  meta.append(buildCell("KEY", props.key ?? "—"));
  meta.append(buildCell("DECK", props.deck ?? "—"));
  root.append(meta);

  return root;
}

function buildCell(label: string, value: string): HTMLElement {
  const cell = document.createElement("span");
  cell.className = "vmx-timecode__meta-cell";
  cell.dataset.role = label.toLowerCase();
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("b");
  v.textContent = value;
  cell.append(l, v);
  return cell;
}

/** Split a track title like "Strobe (Deadmau5 Remix)" into
 *  { main: "Strobe", tag: "Deadmau5 Remix" }. If there's no trailing
 *  parenthetical the whole string becomes `main` and `tag` is null. */
function splitTitle(raw: string): { main: string; tag: string | null } {
  const m = raw.match(/^\s*(.+?)\s*\(([^()]+)\)\s*$/);
  if (m && m[1] && m[2]) return { main: m[1], tag: m[2] };
  return { main: raw, tag: null };
}

function setTitleContent(
  el: HTMLElement,
  track: TimecodeProps["track"],
): void {
  if (!track || !track.title) {
    el.dataset.empty = "true";
    el.textContent = "silence";
    return;
  }
  el.dataset.empty = "false";
  el.textContent = "";
  const split = splitTitle(track.title);
  el.append(document.createTextNode(split.main));
  // Subtitle priority: parenthetical remix tag wins over artist (it's
  // more specific). If the title has no tag, fall back to the artist.
  const subText = split.tag ?? track.artist ?? null;
  if (subText) {
    const sub = document.createElement("span");
    sub.className = "sub";
    sub.textContent = subText;
    el.append(sub);
  }
}

function buildLiveLabel(props: TimecodeProps): string {
  const parts: string[] = ["LIVE"];
  if (props.deck) parts.push(`DECK ${props.deck}`);
  if (props.genre) parts.push(props.genre);
  return parts.join(" · ");
}

function formatBpm(bpm: number | null): string {
  if (bpm == null) return "—";
  return Math.round(bpm).toString();
}

/** Idempotent hot-update. */
export function setTimecode(el: HTMLElement, props: TimecodeProps): void {
  const clock = el.querySelector<HTMLElement>('[data-role="clock"]');
  if (clock && clock.textContent !== props.clock) clock.textContent = props.clock;

  const title = el.querySelector<HTMLElement>('[data-role="track-title"]');
  if (title) {
    const nextKey = props.track
      ? `${props.track.title}::${props.track.artist ?? ""}`
      : "";
    if (title.dataset.trackKey !== nextKey) {
      title.dataset.trackKey = nextKey;
      setTitleContent(title, props.track);
    }
  }

  const live = el.querySelector<HTMLElement>('[data-role="live-tag"]');
  if (live) {
    const v = buildLiveLabel(props);
    if (live.textContent !== v) live.textContent = v;
  }

  const bpm = el.querySelector<HTMLElement>('[data-role="bpm"] b');
  if (bpm) {
    const v = formatBpm(props.bpm);
    if (bpm.textContent !== v) bpm.textContent = v;
  }
  const key = el.querySelector<HTMLElement>('[data-role="key"] b');
  if (key) {
    const v = props.key ?? "—";
    if (key.textContent !== v) key.textContent = v;
  }
  const deck = el.querySelector<HTMLElement>('[data-role="deck"] b');
  if (deck) {
    const v = props.deck ?? "—";
    if (deck.textContent !== v) deck.textContent = v;
  }
}
