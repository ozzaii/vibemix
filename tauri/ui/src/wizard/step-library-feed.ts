/* step-library-feed.ts - collapsed final activation surface.
 *
 * The launch step replaces the old controller -> skill -> privacy ->
 * smoke-test tail. It keeps the load-bearing controls in one place:
 * skill level, optional controller note, local privacy toggles, and the
 * one-click music feed into the existing ipc.library.import path.
 */

import {
  type LibraryImportProgress,
  type LibrarySetupCandidate,
} from "../library/api.js";
import { Button } from "./components/button.js";
import { PrimaryPanel } from "./components/primary-panel.js";
import { registerStyle } from "./components/_style-registry.js";
import {
  renderSkillLevelCard,
  type SkillLevel,
} from "./components/skill-level.js";
import { withStepLeadGlyph } from "./step1-permissions.js";

export type LibraryFeedStatus =
  | "loading"
  | "ready"
  | "indexing"
  | "done"
  | "empty"
  | "error";

export interface LibraryFeedState {
  status: LibraryFeedStatus;
  candidates: LibrarySetupCandidate[];
  indexed: number;
  selectedPath?: string;
  progress?: LibraryImportProgress;
  error?: string;
}

export interface VoiceModelState {
  status: "idle" | "downloading" | "ready" | "error";
  downloaded: number;
  size: number;
  detail?: string;
}

export function voiceModelReadoutText(vm: VoiceModelState): string {
  const mb = (n: number): string => `${Math.round(n / (1024 * 1024))} MB`;
  if (vm.status === "downloading") {
    return vm.size > 0
      ? `downloading voice — ${mb(vm.downloaded)} of ${mb(vm.size)}`
      : "downloading voice";
  }
  if (vm.status === "ready") return "voice installed";
  if (vm.status === "error") {
    return "voice download failed — vibemix opens with voice muted";
  }
  return "preparing voice";
}

export interface LibraryFeedCallbacks {
  skill: SkillLevel;
  profileConsent: boolean;
  telemetryConsent: boolean;
  voiceModel?: VoiceModelState;
  onSelectSkill: (next: SkillLevel) => void;
  onToggleProfile: (next: boolean) => void;
  onToggleTelemetry: (next: boolean) => void;
  onRefreshCandidates: () => void;
  onIndexCandidate: (candidate: LibrarySetupCandidate) => void;
  onPickFolder?: () => void;
  onOpenVibemix: () => void;
  onBack?: () => void;
}

const CSS = `
  .wizard-grid:has(.wizard-step--library-feed) {
    grid-template-columns: minmax(0, min(980px, calc(100vw - 96px)));
  }
  .wizard-step--library-feed .cmp-primary-panel {
    padding: var(--sp-4) var(--sp-5);
  }
  .wizard-step--library-feed .cmp-primary-panel__body {
    padding-top: 0;
  }
  .wizard-step--library-feed .wizard-step__subtitle {
    max-width: 64ch;
  }
  .wizard-feed-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    gap: var(--sp-4);
    margin-bottom: var(--sp-3);
  }
  .wizard-feed-hero__kicker {
    margin-bottom: var(--sp-2);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--brand);
  }
  .wizard-feed-hero__title {
    margin: 0;
    font-family: var(--type-serif);
    font-size: 42px;
    font-weight: 400;
    line-height: 0.96;
    letter-spacing: 0;
    color: var(--silk);
    text-shadow: 0 0 16px var(--brand-12);
  }
  .wizard-feed-hero__ready {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 var(--sp-3);
    border: 1px solid var(--brand-22);
    border-radius: var(--rad-sm);
    background: var(--brand-04);
    color: var(--brand);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    box-shadow: inset 0 1px 0 rgba(255, 251, 244, 0.035);
  }
  .wizard-feed-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.12fr) minmax(280px, 0.88fr);
    gap: var(--sp-3);
    align-items: start;
  }
  .wizard-feed-support {
    display: grid;
    gap: var(--sp-2);
  }
  .wizard-feed-card {
    min-width: 0;
    padding: var(--sp-3);
    border: 0;
    border-radius: var(--rad-md);
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.022), transparent 48%, rgba(0, 0, 0, 0.18)),
      var(--void-8);
    box-shadow:
      var(--chrome-highlight),
      inset 0 -22px 42px rgba(0, 0, 0, 0.20),
      var(--shadow-raised);
  }
  .wizard-feed-card[data-role="library"] {
    min-height: 252px;
    background:
      radial-gradient(circle at 20% 8%, var(--brand-12), transparent 34%),
      linear-gradient(180deg, rgba(255, 251, 244, 0.026), transparent 54%, rgba(0, 0, 0, 0.22)),
      var(--void-10);
    box-shadow:
      var(--chrome-highlight),
      inset 0 0 24px var(--brand-04),
      inset 0 -26px 52px rgba(0, 0, 0, 0.24),
      var(--shadow-float);
  }
  .wizard-feed-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    margin-bottom: var(--sp-2);
  }
  .wizard-feed-card__title {
    margin: 0;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 90, "wght" 700;
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--silk);
  }
  .wizard-feed-card__meta,
  .wizard-feed-card__body,
  .wizard-feed-privacy__copy {
    font-family: var(--type-body);
    font-size: 13px;
    line-height: 1.45;
    color: var(--silk-65);
  }
  .wizard-feed-card__body {
    margin: 0 0 var(--sp-2);
  }
  .wizard-feed-candidate {
    display: grid;
    grid-template-columns: 58px minmax(0, 1fr) 132px;
    gap: var(--sp-3);
    align-items: center;
    padding: var(--sp-3);
    border: 0;
    border-radius: var(--rad-md);
    background:
      linear-gradient(180deg, rgba(255, 251, 244, 0.018), transparent 52%),
      var(--glass-3);
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.035),
      inset 0 -12px 24px rgba(0, 0, 0, 0.22);
  }
  .wizard-feed-candidate__badge {
    width: 54px;
    height: 54px;
    border-radius: var(--rad-md);
    display: grid;
    place-items: center;
    background:
      radial-gradient(circle at 36% 24%, var(--brand-22), transparent 36%),
      linear-gradient(145deg, var(--void-20), var(--void-8));
    box-shadow:
      inset 0 1px 0 rgba(255, 251, 244, 0.055),
      inset 0 -10px 20px rgba(0, 0, 0, 0.34);
    color: var(--silk);
    font-family: var(--type-mono);
    font-size: 10px;
    letter-spacing: 0.05em;
  }
  .wizard-feed-candidate__kind {
    margin-bottom: var(--sp-1);
    font-family: var(--type-display);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--amber);
  }
  .wizard-feed-candidate__path {
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.35;
    color: var(--silk);
    overflow-wrap: anywhere;
  }
  .wizard-feed-candidate__detail {
    margin-top: var(--sp-1);
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.35;
    color: var(--silk-65);
  }
  .wizard-feed-recheck {
    margin-top: var(--sp-2);
    align-self: start;
  }
  .wizard-feed-candidate .cmp-btn {
    width: 100%;
    min-width: 0;
  }
  .wizard-feed-progress {
    margin-top: var(--sp-3);
  }
  .wizard-feed-progress__bar {
    height: 4px;
    border-radius: 2px;
    background: var(--glass-edge);
    overflow: hidden;
  }
  .wizard-feed-progress__fill {
    display: block;
    height: 100%;
    width: var(--feed-progress, 0%);
    background: var(--amber);
    box-shadow: 0 0 8px var(--amber-40);
  }
  .wizard-feed-progress__label {
    margin-top: var(--sp-2);
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-65);
  }
  .wizard-feed-privacy {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--sp-2);
  }
  .wizard-feed-privacy .wizard-feed-card__title,
  .wizard-feed-privacy .wizard-feed-privacy__copy {
    grid-column: 1 / -1;
  }
  .wizard-feed-toggle {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    cursor: pointer;
    user-select: none;
  }
  .wizard-feed-toggle input {
    appearance: none;
    width: 18px;
    height: 18px;
    border: 1.5px solid var(--silk-65);
    border-radius: 3px;
    background: transparent;
    position: relative;
    flex: 0 0 auto;
  }
  .wizard-feed-toggle input:checked {
    border-color: var(--amber);
    background: var(--amber-22);
  }
  .wizard-feed-toggle input:checked::after {
    content: "";
    position: absolute;
    left: 4px;
    top: 0;
    width: 6px;
    height: 11px;
    border: solid var(--amber);
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  .wizard-feed-toggle span {
    font-family: var(--type-body);
    font-size: 13px;
    color: var(--silk);
    text-transform: uppercase;
  }
  .wizard-feed-controller {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
  }
  .wizard-feed-controller__dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: var(--amber);
    box-shadow: 0 0 8px var(--amber-40);
  }
  .wizard-step--library-feed .vmx-skill-level {
    padding: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
  }
  .wizard-step--library-feed .vmx-skill-level__radio-row {
    padding: 8px var(--sp-3);
  }
  .wizard-step.wizard-step--library-feed > .wizard-step__cta-row {
    margin-top: var(--sp-2);
  }
  @media (max-width: 900px) {
    .wizard-grid:has(.wizard-step--library-feed) {
      grid-template-columns: minmax(0, 1fr);
    }
    .wizard-feed-grid {
      grid-template-columns: 1fr;
    }
    .wizard-feed-layout {
      grid-template-columns: 1fr;
    }
    .wizard-feed-hero {
      grid-template-columns: 1fr;
      align-items: start;
    }
    .wizard-feed-candidate {
      grid-template-columns: 54px minmax(0, 1fr);
    }
    .wizard-feed-candidate .cmp-btn {
      grid-column: 1 / -1;
    }
  }
`;

registerStyle("wizard-step--library-feed", CSS);

function kindLabel(candidate: LibrarySetupCandidate): string {
  const kind = candidate.kind.replace(/[_-]+/g, " ");
  if (kind === "engine database") return "Engine DJ";
  if (kind === "rekordbox xml") return "Rekordbox";
  if (kind === "traktor nml") return "Traktor";
  if (kind === "virtualdj database") return "VirtualDJ";
  if (kind === "serato database") return "Serato";
  if (kind === "music folder") return "Music folder";
  return kind;
}

function progressPercent(progress: LibraryImportProgress | undefined): number {
  if (!progress || progress.total <= 0) return 0;
  return Math.max(0, Math.min(100, (progress.done / progress.total) * 100));
}

function progressCopy(state: LibraryFeedState): string {
  const progress = state.progress;
  if (state.status === "loading") return "looking for Rekordbox, Engine, Serato, and music folders";
  if (state.status === "ready") return "source found";
  if (state.status === "done") {
    if (progress?.cancelled) return "import cancelled";
    if (progress && progress.total > 0) {
      const failed = progress.failed ?? 0;
      if (failed > 0) {
        return `indexed ${Math.max(0, progress.total - failed)} of ${progress.total} · ${failed} failed`;
      }
      return `indexed ${progress.done} of ${progress.total}`;
    }
    return "music feed started";
  }
  if (state.status === "error") return state.error ?? "library feed failed";
  if (state.status === "indexing") {
    if (!progress) return "starting import";
    const item = progress.current_track_name || state.selectedPath || "library";
    return `${progress.done}/${progress.total} ${item}`;
  }
  if (state.indexed > 0) return `${state.indexed} tracks already indexed`;
  return "no library source found yet";
}

function renderLibraryCard(
  state: LibraryFeedState,
  cb: LibraryFeedCallbacks,
): HTMLElement {
  const card = document.createElement("section");
  card.className = "wizard-feed-card";
  card.dataset.role = "library";
  card.dataset.status = state.status;

  const head = document.createElement("div");
  head.className = "wizard-feed-card__head";
  const title = document.createElement("h2");
  title.className = "wizard-feed-card__title";
  title.textContent = "feed your music";
  const meta = document.createElement("span");
  meta.className = "wizard-feed-card__meta";
  meta.textContent = progressCopy(state);
  head.append(title, meta);
  card.append(head);

  const body = document.createElement("p");
  body.className = "wizard-feed-card__body";
  body.textContent =
    "Viber builds from your local library. Index the source it found, then every set build starts from music you actually own.";
  card.append(body);

  const candidate = state.candidates[0];
  if (candidate) {
    const row = document.createElement("div");
    row.className = "wizard-feed-candidate";
    const badge = document.createElement("div");
    badge.className = "wizard-feed-candidate__badge";
    badge.setAttribute("aria-hidden", "true");
    badge.textContent = candidate.path.endsWith(".m3u") ? "M3U" : "m.db";

    const copy = document.createElement("div");
    const kind = document.createElement("div");
    kind.className = "wizard-feed-candidate__kind";
    kind.textContent = kindLabel(candidate);
    const path = document.createElement("div");
    path.className = "wizard-feed-candidate__path";
    path.textContent = candidate.path;
    const detail = document.createElement("div");
    detail.className = "wizard-feed-candidate__detail";
    const seen = candidate.audio_files_seen;
    if (typeof seen === "number" && seen > 0) {
      const conf = candidate.confidence ? ` · ${candidate.confidence} confidence` : "";
      detail.textContent = `${seen} ${seen === 1 ? "track" : "tracks"} found${conf}`;
    } else {
      detail.textContent = candidate.reason ?? "";
    }
    copy.append(kind, path, detail);

    row.append(badge, copy);
    row.append(
      Button({
        variant: "primary",
        state: state.status === "indexing" ? "loading" : "armed",
        label: "Index this",
        onClick: () => cb.onIndexCandidate(candidate),
      }),
    );
    card.append(row);

    const recheck = Button({
      variant: "secondary",
      state: state.status === "indexing" ? "disabled" : "idle",
      label: "Recheck",
      onClick: cb.onRefreshCandidates,
    });
    recheck.classList.add("wizard-feed-recheck");
    card.append(recheck);
  } else {
    card.append(
      Button({
        variant: "secondary",
        state: state.status === "loading" ? "disabled" : "idle",
        label: "Recheck",
        onClick: cb.onRefreshCandidates,
      }),
    );
  }

  // Native folder pick at launch: selectable, not only auto-detected.
  if (cb.onPickFolder) {
    card.append(
      Button({
        variant: "secondary",
        state: state.status === "indexing" ? "disabled" : "idle",
        label: "Choose a folder",
        onClick: cb.onPickFolder,
      }),
    );
  }

  if (state.status === "indexing" || state.status === "done") {
    const progress = document.createElement("div");
    progress.className = "wizard-feed-progress";
    const bar = document.createElement("div");
    bar.className = "wizard-feed-progress__bar";
    const fill = document.createElement("i");
    fill.className = "wizard-feed-progress__fill";
    fill.style.setProperty("--feed-progress", `${progressPercent(state.progress)}%`);
    bar.append(fill);
    const label = document.createElement("div");
    label.className = "wizard-feed-progress__label";
    label.textContent = progressCopy(state);
    progress.append(bar, label);
    card.append(progress);
  }

  return card;
}

function renderControllerCard(): HTMLElement {
  const card = document.createElement("section");
  card.className = "wizard-feed-card";
  card.dataset.role = "controller";
  const title = document.createElement("h2");
  title.className = "wizard-feed-card__title";
  title.textContent = "controller";
  const row = document.createElement("div");
  row.className = "wizard-feed-controller";
  const dot = document.createElement("span");
  dot.className = "wizard-feed-controller__dot";
  dot.setAttribute("aria-hidden", "true");
  const copy = document.createElement("p");
  copy.className = "wizard-feed-card__body";
  copy.textContent = "Plug it in whenever you want. Detection runs when you ask for it later.";
  row.append(dot, copy);
  card.append(title, row);
  return card;
}

function renderVoiceModelCard(vm: VoiceModelState): HTMLElement {
  const card = document.createElement("section");
  card.className = "wizard-feed-card";
  card.dataset.role = "voice-model";
  const title = document.createElement("h2");
  title.className = "wizard-feed-card__title";
  title.textContent = "voice";
  const copy = document.createElement("p");
  copy.className = "wizard-feed-card__body";
  copy.id = "voice-model-readout";
  copy.dataset.status = vm.status;
  copy.textContent = voiceModelReadoutText(vm);
  card.append(title, copy);
  return card;
}

function renderPrivacyCard(
  state: LibraryFeedState,
  cb: LibraryFeedCallbacks,
): HTMLElement {
  const card = document.createElement("section");
  card.className = "wizard-feed-card wizard-feed-privacy";
  card.dataset.role = "privacy";
  const title = document.createElement("h2");
  title.className = "wizard-feed-card__title";
  title.textContent = "local choices";
  const copy = document.createElement("p");
  copy.className = "wizard-feed-privacy__copy";
  copy.textContent = "Profile learning and diagnostics stay off unless you turn them on.";

  const profile = document.createElement("label");
  profile.className = "wizard-feed-toggle";
  const profileInput = document.createElement("input");
  profileInput.type = "checkbox";
  profileInput.checked = cb.profileConsent;
  profileInput.addEventListener("change", () => cb.onToggleProfile(profileInput.checked));
  const profileText = document.createElement("span");
  profileText.textContent = "build local profile";
  profile.append(profileInput, profileText);

  const telemetry = document.createElement("label");
  telemetry.className = "wizard-feed-toggle";
  const telemetryInput = document.createElement("input");
  telemetryInput.type = "checkbox";
  telemetryInput.checked = cb.telemetryConsent;
  telemetryInput.addEventListener("change", () =>
    cb.onToggleTelemetry(telemetryInput.checked),
  );
  const telemetryText = document.createElement("span");
  telemetryText.textContent = "share diagnostics";
  telemetry.append(telemetryInput, telemetryText);

  card.append(title, copy, profile, telemetry);
  if (state.status === "indexing" || state.status === "done") {
    const note = document.createElement("p");
    note.className = "wizard-feed-privacy__copy";
    note.dataset.role = "embed-privacy";
    note.textContent =
      "Embedding locally on your device — your library never leaves this machine.";

    const progress = document.createElement("div");
    progress.className = "wizard-feed-progress";
    progress.style.gridColumn = "1 / -1";
    const bar = document.createElement("div");
    bar.className = "wizard-feed-progress__bar";
    const fill = document.createElement("i");
    fill.className = "wizard-feed-progress__fill";
    fill.style.setProperty("--feed-progress", `${progressPercent(state.progress)}%`);
    bar.append(fill);
    const label = document.createElement("div");
    label.className = "wizard-feed-progress__label";
    label.textContent = progressCopy(state);
    progress.append(bar, label);

    card.append(note, progress);
  }
  return card;
}

export function renderStepLibraryFeed(
  state: LibraryFeedState,
  cb: LibraryFeedCallbacks,
): HTMLElement {
  const body = document.createElement("div");
  body.className = "wizard-step--library-feed";

  const hero = document.createElement("div");
  hero.className = "wizard-feed-hero";
  const heroCopy = document.createElement("div");
  const kicker = document.createElement("div");
  kicker.className = "wizard-feed-hero__kicker";
  kicker.textContent = "LAUNCH";
  withStepLeadGlyph(kicker, 3);
  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading wizard-feed-hero__title";
  heading.textContent = "Feed your library";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  subtitle.textContent =
    "Pick your level, feed Viber your music, and open the deck.";
  heroCopy.append(kicker, heading, subtitle);
  const ready = document.createElement("div");
  ready.className = "wizard-feed-hero__ready";
  ready.textContent =
    state.status === "ready" || state.status === "done"
      ? "source found"
      : progressCopy(state);
  hero.append(heroCopy, ready);

  const grid = document.createElement("div");
  grid.className = "wizard-feed-layout";

  const skillCard = document.createElement("section");
  skillCard.className = "wizard-feed-card";
  skillCard.dataset.role = "skill";
  const skillTitle = document.createElement("h2");
  skillTitle.className = "wizard-feed-card__title";
  skillTitle.textContent = "skill";
  skillCard.append(skillTitle);
  skillCard.append(
    renderSkillLevelCard({
      selected: cb.skill,
      onSelect: cb.onSelectSkill,
    }),
  );

  const support = document.createElement("div");
  support.className = "wizard-feed-support";
  support.append(
    skillCard,
    renderControllerCard(),
    renderVoiceModelCard(
      cb.voiceModel ?? { status: "idle", downloaded: 0, size: 0 },
    ),
    renderPrivacyCard(state, cb),
  );

  grid.append(renderLibraryCard(state, cb), support);

  body.append(hero, grid);

  const panel = PrimaryPanel({ children: body });
  panel.classList.add("wizard-step__panel-rise");

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";
  if (cb.onBack) {
    ctaRow.append(
      Button({
        variant: "secondary",
        state: "armed",
        label: "Back",
        onClick: cb.onBack,
      }),
    );
  }
  ctaRow.append(
    Button({
      variant: "primary",
      state: "armed",
      label: "Open vibemix",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: cb.onOpenVibemix,
    }),
  );

  const root = document.createElement("section");
  root.className = "wizard-step wizard-step--library-feed";
  root.append(panel, ctaRow);
  return root;
}
