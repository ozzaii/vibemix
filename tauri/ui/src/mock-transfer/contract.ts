// SPDX-License-Identifier: Apache-2.0
/*
 * Stable anchors for moving visual ideas from static mockups into the live app.
 * These are not a second UI API. They name the production mounts that must stay
 * wired to real WS/IPC data while a mock's structure or styling is transferred.
 */

export interface MockTransferWire {
  wire: string;
  purpose: string;
}

export interface DynamicMockTransferWire extends MockTransferWire {
  producerFile: string;
}

export interface MockTransferSurface {
  surface: "session" | "library" | "pill" | "debrief" | "overlay" | "mascot";
  productionFile: string;
  mockSources: readonly string[];
  requiredWires: readonly MockTransferWire[];
  dynamicWires?: readonly DynamicMockTransferWire[];
  inbound: readonly string[];
  outbound: readonly string[];
}

export interface MockTransferRuntimeSurface {
  surface: "session-runtime" | "settings" | "shell-debrief";
  productionFile: string;
  mockSources: readonly string[];
  requiredWires: readonly MockTransferWire[];
  inbound: readonly string[];
  outbound: readonly string[];
}

export const MOCK_TRANSFER_CONTRACT: readonly MockTransferSurface[] = [
  {
    surface: "session",
    productionFile: "index.html",
    mockSources: [
      "mocks/vibemix-rebuild-session.html",
      "mocks/vibemix-app-ui.html",
      "mocks/vibemix-direction-final.html",
    ],
    requiredWires: [
      { wire: "session.shell", purpose: "main live shell after wizard teardown" },
      { wire: "session.titlebar", purpose: "window drag/title surface" },
      { wire: "session.content", purpose: "wizard-to-runtime content region" },
      { wire: "session.primary", purpose: "SessionLayout mount and deck copy" },
      { wire: "session.status", purpose: "status.tick health footer" },
      { wire: "session.crash-banner", purpose: "sidecar crash recovery" },
      { wire: "wizard.step-strip", purpose: "first-run calibration step strip" },
      { wire: "wizard.cta", purpose: "first-run calibration command row" },
    ],
    inbound: [
      "ipc.session.snapshot",
      "ipc.status.tick",
      "ipc.settings.state",
      "ipc.session.cohost-reaction",
    ],
    outbound: [
      "ipc.settings.set",
      "ipc.session.mute",
      "ipc.session.set_mode",
      "open_library_window",
      "open_debrief_window",
      "open_learn_window",
    ],
  },
  {
    surface: "library",
    productionFile: "library.html",
    mockSources: ["mocks/vibemix-library-ui.html", "mocks/vibemix-viber-chat.html"],
    requiredWires: [
      { wire: "library.shell", purpose: "Viber / vibe-engine window shell" },
      { wire: "library.titlebar", purpose: "library window drag/title surface" },
      { wire: "library.console", purpose: "left-side Viber command console" },
      { wire: "library.mode-tabs", purpose: "search/similar/curate/build/chat/ingest tabs" },
      { wire: "library.search-field", purpose: "search and similar query field" },
      { wire: "library.similar-dropzone", purpose: "seed-track dropzone" },
      { wire: "library.ingest-field", purpose: "folder ingest controls" },
      { wire: "library.cue-field", purpose: "auto-cue export folder controls" },
      { wire: "library.curate-field", purpose: "Viber curate theme input" },
      { wire: "library.build-field", purpose: "Viber build-set brief and curve controls" },
      { wire: "library.chat-field", purpose: "Viber chat prompt" },
      { wire: "library.run", purpose: "active mode command button" },
      { wire: "library.stats", purpose: "corpus/model/backend stats" },
      { wire: "library.model-setup", purpose: "local model readiness and install" },
      { wire: "library.agent-setup", purpose: "Codex/Viber setup hint" },
      {
        wire: "library.operator-brief",
        purpose: "folded Crate/Viber first-screen operator brief",
      },
      { wire: "library.results-panel", purpose: "main result/rationale panel" },
      { wire: "library.command-field", purpose: "command echo and active-mode label" },
      { wire: "library.rationale", purpose: "curate/build set notes" },
      { wire: "library.export", purpose: "Rekordbox export result line" },
      { wire: "library.results", purpose: "search/set/build rows" },
      { wire: "library.chat-thread", purpose: "conversation transcript" },
      { wire: "library.chat-starters", purpose: "Viber starter prompt actions" },
      { wire: "library.ingest-progress", purpose: "folder ingest progress log" },
      { wire: "library.grounding-panel", purpose: "right-side grounding/receipts panel" },
      { wire: "library.scope-wrap", purpose: "scope visualization frame" },
      { wire: "library.chat-tools", purpose: "tool trace / grounding receipts" },
      { wire: "library.chat-artifact", purpose: "playlist/export/source artifact" },
      { wire: "library.scope", purpose: "grounding scope plot" },
      { wire: "library.chat-side", purpose: "chat sidecar receipts area" },
    ],
    dynamicWires: [
      {
        wire: "library.clarification",
        purpose: "Viber clarification prompt and numbered choices",
        producerFile: "src/library/index.ts",
      },
      {
        wire: "library.chat-clarification",
        purpose: "Viber chat clarification card and choices",
        producerFile: "src/library/index.ts",
      },
      {
        wire: "library.chat-move-grade",
        purpose: "Viber chat move-grade and XP receipt rows",
        producerFile: "src/library/index.ts",
      },
    ],
    inbound: [
      "library_search",
      "library_similar",
      "library_curate",
      "library_build_set",
      "library_chat",
      "library_stats",
      "library_models",
      "library://embed-progress",
      "library://embed-done",
      "library://model-progress",
      "library://viber-tool",
      "live-deck-context",
      "ipc-session-snapshot",
    ],
    outbound: [
      "ipc.library.import",
      "library_embed_folder",
      "library_models",
      "library_search",
      "library_similar",
      "library_curate",
      "library_build_set",
      "library_chat",
      "library_cue_folder",
    ],
  },
  {
    surface: "pill",
    productionFile: "pill.html",
    mockSources: ["mocks/vibemix-pill-hover.html", "mocks/vibemix-pill-notch.html"],
    requiredWires: [
      { wire: "pill.shell", purpose: "transparent overlay root and state attrs" },
      { wire: "pill.drag", purpose: "native window drag strip" },
      { wire: "pill.row", purpose: "collapsed state row" },
      { wire: "pill.intelligence", purpose: "data-derived live intelligence lens" },
      { wire: "pill.state-label", purpose: "cohost state caption" },
      { wire: "pill.grade", purpose: "earned move grade and XP readout" },
      { wire: "pill.level", purpose: "grounded pill XP level bead from grade progress" },
      { wire: "pill.wave", purpose: "voice RMS waveform mount" },
      { wire: "pill.burst", purpose: "earned overdrive visual burst mount" },
      { wire: "pill.overdrive", purpose: "liquid-glass overdrive halo for lit-aff moves" },
      { wire: "pill.streak", purpose: "grounded combo heat rail from grade progress" },
      { wire: "pill.notch", purpose: "grounded next suggestion hint" },
      { wire: "pill.expand", purpose: "reaction and receipt drawer" },
      { wire: "pill.reaction", purpose: "verbatim cohost reaction text" },
      { wire: "pill.decks", purpose: "deck context chips" },
      { wire: "pill.peek", purpose: "collapsed hover next-suggestion card" },
    ],
    dynamicWires: [
      {
        wire: "pill.next",
        purpose: "reserved next-suggestion mount; reaction mode stays reaction-first",
        producerFile: "src/pill/index.ts",
      },
      {
        wire: "pill.receipt",
        purpose: "reaction receipt hairline inserted above citations",
        producerFile: "src/pill/index.ts",
      },
      {
        wire: "pill.citations",
        purpose: "expanded reaction citation strip",
        producerFile: "src/pill/index.ts",
      },
      {
        wire: "pill.next-card",
        purpose: "rendered next-track suggestion card",
        producerFile: "src/pill/next-suggestion.ts",
      },
      {
        wire: "pill.next-grade",
        purpose: "rendered move grade inside next-track card",
        producerFile: "src/pill/next-suggestion.ts",
      },
      {
        wire: "pill.next-combo",
        purpose: "rendered earned combo and session XP inside next-track card",
        producerFile: "src/pill/next-suggestion.ts",
      },
      {
        wire: "pill.next-backups",
        purpose: "backup transition choices inside next-track card",
        producerFile: "src/pill/next-suggestion.ts",
      },
      {
        wire: "pill.next-feedback",
        purpose: "feedback controls for next-track suggestion",
        producerFile: "src/pill/next-suggestion.ts",
      },
    ],
    inbound: [
      "snapshot",
      "cohost-reaction",
      "ipc.session.cohost-reaction",
      "next_suggestion",
      "deck_state",
    ],
    outbound: [
      "set_pill_height",
      "open_debrief_window",
      "forward_ipc_to_sidecar",
      "next_suggestion.choose",
      "next_suggestion.feedback",
    ],
  },
  {
    surface: "debrief",
    productionFile: "debrief.html",
    mockSources: ["mocks/vibemix-cinematic-storyboard.html"],
    requiredWires: [
      { wire: "debrief.shell", purpose: "debrief window root" },
      { wire: "debrief.titlebar", purpose: "debrief window drag/title surface" },
      { wire: "debrief.layout", purpose: "debrief split layout" },
      { wire: "debrief.sidebar", purpose: "chapter navigation sidebar" },
      { wire: "debrief.chapters", purpose: "chapter list" },
      { wire: "debrief.main", purpose: "main debrief analysis column" },
      { wire: "debrief.tldr", purpose: "TLDR section" },
      { wire: "debrief.tldr-player", purpose: "voiced TLDR player" },
      { wire: "debrief.timeline", purpose: "timeline section" },
      { wire: "debrief.waveform", purpose: "timeline waveform" },
      { wire: "debrief.drills", purpose: "practice drills section" },
      { wire: "debrief.drills-list", purpose: "practice drills" },
      { wire: "debrief.ear-test", purpose: "ear-test sign-off section" },
      { wire: "debrief.ear-test-toggle", purpose: "ear-test sign-off" },
      { wire: "debrief.bravoh", purpose: "Bravoh waitlist opt-in section" },
      { wire: "debrief.bravoh-toggle", purpose: "Bravoh opt-in" },
      { wire: "debrief.error-banner", purpose: "sidecar errors" },
      { wire: "debrief.tooltip", purpose: "citation tooltip" },
    ],
    inbound: [
      "ipc.debrief.session-loaded",
      "ipc.debrief.chapter-list",
      "ipc.debrief.drills",
      "ipc.debrief.tldr-audio",
      "ipc.debrief.citation-tooltip",
      "ipc.debrief.error",
      "session-loaded",
      "chapter-list",
      "drills",
      "tldr-audio",
      "citation-tooltip",
      "sidecar-debrief-crashed",
      "vmx-debrief-deeplink",
    ],
    outbound: [
      "ipc.debrief.citation-tooltip-request",
      "ipc.debrief.ear-test-submit",
      "write_ear_test_log",
      "read_bravoh_waitlist_opt_in",
      "write_bravoh_waitlist_opt_in",
    ],
  },
  {
    surface: "overlay",
    productionFile: "overlay.html",
    mockSources: [],
    requiredWires: [
      { wire: "overlay.shell", purpose: "transparent click-through overlay root" },
      { wire: "overlay.ring", purpose: "screen-citation highlight ring" },
      { wire: "overlay.corner.tl", purpose: "top-left aperture corner" },
      { wire: "overlay.corner.tr", purpose: "top-right aperture corner" },
      { wire: "overlay.corner.bl", purpose: "bottom-left aperture corner" },
      { wire: "overlay.corner.br", purpose: "bottom-right aperture corner" },
      { wire: "overlay.scan-x", purpose: "horizontal scan line" },
      { wire: "overlay.scan-y", purpose: "vertical scan line" },
    ],
    inbound: ["ipc.session.overlay-highlight", "overlay.html?color", "overlay.html?duration_ms"],
    outbound: ["show_overlay_highlight", "Rust overlay close timer"],
  },
  {
    surface: "mascot",
    productionFile: "mascot.html",
    mockSources: [],
    requiredWires: [
      { wire: "mascot.shell", purpose: "transparent always-on-top overlay root" },
      { wire: "mascot.host", purpose: "bare WebGL positioning host" },
      { wire: "mascot.canvas", purpose: "Three.js renderer canvas" },
      { wire: "mascot.hidden-sweep", purpose: "hidden legacy chrome compatibility node" },
      { wire: "mascot.hidden-label", purpose: "hidden legacy top-label compatibility node" },
      { wire: "mascot.hidden-state", purpose: "hidden legacy state-caption compatibility node" },
    ],
    inbound: ["flat mascot frame", "ipc.mascot.mood_change", "deck_state"],
    outbound: ["window geometry persistence"],
  },
] as const;

export const SESSION_RUNTIME_WIRES = [
  "session.runtime",
  "session.titlebar",
  "session.mode-picker",
  "session.stage",
  "session.primary",
  "session.vibe-engine",
  "session.now-line",
  "session.citation",
  "session.drop",
  "session.claim-policy",
  "session.idle-proof",
  "session.idle-proof.next",
  "session.meter",
  "session.status",
] as const;

export const SETTINGS_RUNTIME_WIRES = [
  "settings.backdrop",
  "settings.drawer",
  "settings.header",
  "settings.close",
  "settings.body",
  "settings.modal-slot",
  "settings.trust",
  "settings.trust.contract",
  "settings.trust.voice",
  "settings.trust.output",
  "settings.trust.recordings",
  "settings.trust.proof",
  "settings.persona.voice.deferred-note",
  "settings.output.deferred-note",
] as const;

export const SETTINGS_GROUP_WIRES = [
  "settings.group.persona",
  "settings.group.output",
  "settings.group.hotkey",
  "settings.group.recording",
  "settings.group.library",
  "settings.group.profile",
  "settings.group.diagnostics",
  "settings.group.calibration",
  "settings.group.learn",
  "settings.group.mascot",
  "settings.group.performance",
  "settings.group.help",
] as const;

export const SETTINGS_PERSONA_CONTROL_WIRES = [
  "settings.persona.voice",
  "settings.persona.mode",
  "settings.persona.lens",
  "settings.persona.genre",
  "settings.persona.skill",
] as const;

export const SETTINGS_MOCK_SOURCES = [
  "mocks/vibemix-settings-drawer.html",
] as const;

export const SHELL_DEBRIEF_RUNTIME_WIRES = [
  "shell.debrief.dock",
] as const;

export const ACTIVE_MOCK_ITERATION_DIR = "mocks/iterations";
export const ACTIVE_MOCK_ITERATION_INDEX = `${ACTIVE_MOCK_ITERATION_DIR}/_index.html`;
export const ACTIVE_MOCK_ITERATION_TEMPLATE = `${ACTIVE_MOCK_ITERATION_DIR}/_template.html`;

const SESSION_RUNTIME_WIRE_PURPOSES: Record<
  (typeof SESSION_RUNTIME_WIRES)[number],
  string
> = {
  "session.runtime": "hydrated live shell replacing the setup wizard",
  "session.titlebar": "runtime titlebar and settings affordance",
  "session.mode-picker": "cohost/library/build/debrief/learn mode switch",
  "session.stage": "main post-wizard stage",
  "session.primary": "primary deck and cohost mount",
  "session.vibe-engine": "Library/Viber and vibe-engine open control",
  "session.now-line": "current deck / phrase readout",
  "session.citation": "grounded evidence chip",
  "session.drop": "runtime drop-countdown chip",
  "session.claim-policy": "live claim-proof policy chip",
  "session.idle-proof":
    "idle first-move proof rail for audio, Sven, controller, and screen evidence",
  "session.idle-proof.next": "idle first-move next action copy tied to proof readiness",
  "session.meter": "audio health meter",
  "session.status": "runtime status footer",
};

const SETTINGS_RUNTIME_WIRE_PURPOSES: Record<
  (typeof SETTINGS_RUNTIME_WIRES)[number],
  string
> = {
  "settings.backdrop": "dismissable overlay behind the slide-over",
  "settings.drawer": "live settings slide-over shell",
  "settings.header": "settings title and close row",
  "settings.close": "drawer close affordance",
  "settings.body": "settings group mount",
  "settings.modal-slot": "confirmation dialog portal",
  "settings.trust": "top trust/readiness rail for local voice, output, recordings, and proof",
  "settings.trust.contract": "summary of Sven persona, route, and proof state before controls",
  "settings.trust.voice": "local MOSS voice readiness summary",
  "settings.trust.output": "current co-host output route summary",
  "settings.trust.recordings": "local recording vault usage summary",
  "settings.trust.proof": "current grounded proof-gate summary",
  "settings.persona.voice.deferred-note": "voice changes apply on next start",
  "settings.output.deferred-note": "output changes apply on next start",
};

const SHELL_DEBRIEF_RUNTIME_WIRE_PURPOSES: Record<
  (typeof SHELL_DEBRIEF_RUNTIME_WIRES)[number],
  string
> = {
  "shell.debrief.dock": "folded shell Debrief route listing recent review sessions",
};

function wireEntries<const TWire extends string>(
  wires: readonly TWire[],
  purposes: Record<TWire, string>,
): readonly MockTransferWire[] {
  return wires.map((wire) => ({ wire, purpose: purposes[wire] }));
}

export const MOCK_TRANSFER_RUNTIME_CONTRACT: readonly MockTransferRuntimeSurface[] = [
  {
    surface: "session-runtime",
    productionFile: "src/session/SessionLayout.ts",
    mockSources: [
      "mocks/vibemix-rebuild-session.html",
      "mocks/vibemix-app-ui.html",
      "mocks/vibemix-direction-final.html",
    ],
    requiredWires: wireEntries(
      SESSION_RUNTIME_WIRES,
      SESSION_RUNTIME_WIRE_PURPOSES,
    ),
    inbound: [
      "ipc.session.snapshot",
      "ipc.status.tick",
      "ipc.settings.state",
      "ipc.error",
      "ipc.session.citation",
      "ipc.session.mute",
      "ipc.recordings.usage",
      "ipc.session.cohost-reaction",
      "tray-quit-requested",
      "tray-set-mood",
    ],
    outbound: [
      "ipc.settings.get",
      "ipc.settings.set",
      "ipc.session.set_mode",
      "ipc.session.mute",
      "ipc.status.recheck",
      "restart_sidecar",
      "open_library_window",
      "open_debrief_window",
      "open_learn_window",
      "confirmed-quit",
      "quit-cancelled",
    ],
  },
  {
    surface: "settings",
    productionFile: "src/settings/SettingsDrawer.ts",
    mockSources: SETTINGS_MOCK_SOURCES,
    requiredWires: wireEntries(
      SETTINGS_RUNTIME_WIRES,
      SETTINGS_RUNTIME_WIRE_PURPOSES,
    ),
    inbound: [
      "ipc.settings.state",
      "ipc.recordings.usage",
      "ipc.recordings.list_result",
      "ipc.recordings.delete_ack",
      "ipc.recordings.events_result",
      "ipc.library.staleness_nudge",
      "ipc.library.import_progress",
      "ipc.profile.view_result",
      "ipc.profile.regenerate_result",
      "ipc.profile.delete_ack",
      "ipc.profile.consent_state",
    ],
    outbound: [
      "ipc.settings.set",
      "ipc.recordings.list",
      "ipc.recordings.delete",
      "ipc.recordings.events",
      "ipc.library.import",
      "ipc.library.import_cancel",
      "ipc.library.staleness_action",
      "ipc.profile.view",
      "ipc.profile.regenerate",
      "ipc.profile.delete",
      "ipc.profile.set_consent",
      "ipc.wizard.start",
      "ipc.learn.progress_state",
      "rebind_hotkey",
      "read_mascot_window_state",
      "set_mascot_visible",
      "set_mascot_click_through",
      "open_debrief_window",
      "reveal_in_os",
      "open_input_wav",
      "plugin:shell|open",
    ],
  },
  {
    surface: "shell-debrief",
    productionFile: "src/shell/DebriefDock.ts",
    mockSources: ["mocks/vibemix-cinematic-storyboard.html"],
    requiredWires: wireEntries(
      SHELL_DEBRIEF_RUNTIME_WIRES,
      SHELL_DEBRIEF_RUNTIME_WIRE_PURPOSES,
    ),
    inbound: ["ipc.recordings.list_result"],
    outbound: ["ipc.recordings.list", "open_debrief_window"],
  },
] as const;

export function wireSelector(wire: string): string {
  return `[data-wire="${wire}"]`;
}

export function staticWires(surface: MockTransferSurface): readonly MockTransferWire[] {
  return surface.requiredWires;
}
