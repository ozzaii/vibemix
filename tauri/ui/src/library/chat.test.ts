// SPDX-License-Identifier: Apache-2.0
/**
 * @vitest-environment jsdom
 */
/* Vibe Engine - chat UI spec.
 *
 * Exercises the real mountLibrary -> runChat path so the conversational Viber
 * surface keeps grounded tools, artifacts, and multi-turn history wired.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  LibraryChatResult,
  LibraryLiveContext,
  LibraryModelInstallTarget,
  LibraryModelsResult,
  LibraryStats,
} from "./api.js";

const chatMock =
  vi.fn<
    (
      message: string,
      history: unknown[],
      liveContext?: LibraryLiveContext | null,
    ) => Promise<LibraryChatResult>
  >();
let liveContextCallback: ((context: LibraryLiveContext) => void) | null = null;
let liveMoveCallback: ((moves: string[]) => void) | null = null;
let viberToolCallback:
  | ((event: { tool: string; ok: boolean; summary: string }) => void)
  | null = null;
const DECK_LANES_CONTEXT =
  "deck_lanes_context[deck1=A identity=known route=dominant | deck2=B identity=unresolved route=muted lane_aliases=deck1:A,deck2:B rule=per_lane_identity_route_control_not_outcome]";
const DECK_REFERENCE_CONTEXT =
  "deck_reference_context[deck1=A identity=known route=dominant deck2=B identity=unresolved route=muted audio=P1_global_mix per_deck_audio=not_attached isolated_decks=false rule=deck1_deck2_reference_not_outcome]";
const DECK_SOURCE_CONTEXT =
  "deck_source_context[identity_state=MusicState.deck_state primary=nowplaying_controller_attribution_to_library_cache resolved=A unresolved=B sources=rekordbox_xml live_db=not_read event_xml=diagnostic_only second_deck=independent_source_required rule=unresolved_deck_is_not_transition_evidence]";
const DECK_AUDIO_CONTEXT =
  "deck_audio_context[audio=audible source=global_mix isolated_decks=false routing=A_dominant B_muted support=single_deck_A rule=audio_heard_must_be_mapped_through_deck_context]";
const DECK_PAIR_LANES_CONTEXT =
  "deck_lanes_context[deck1=A identity=known route=dominant | deck2=B identity=known route=present lane_aliases=deck1:A,deck2:B rule=per_lane_identity_route_control_not_outcome]";
const DECK_PAIR_REFERENCE_CONTEXT =
  "deck_reference_context[deck1=A identity=known route=dominant deck2=B identity=known route=present audio=P1_global_mix per_deck_audio=not_attached isolated_decks=false rule=deck1_deck2_reference_not_outcome]";
const DECK_PAIR_SOURCE_CONTEXT =
  "deck_source_context[identity_state=MusicState.deck_state primary=rekordbox_xml resolved=A+B unresolved=none sources=deck1:rekordbox_xml+deck2:rekordbox_xml live_db=not_read event_xml=diagnostic_only second_deck=independent_source_required rule=unresolved_deck_is_not_transition_evidence]";
const DECK_PAIR_AUDIO_CONTEXT =
  "deck_audio_context[audio=audible source=global_mix isolated_decks=false routing=A_dominant B_present support=two_deck_context_no_outcome rule=audio_heard_must_be_mapped_through_deck_context]";
const DECK_AUDIO_SEPARATION_CONTEXT =
  "deck_audio_separation_context[requested_device=BlackHole_2ch capture_device=BlackHole_2ch input_channels=2 opened_channels=2 sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture deckA_audio=not_captured deckB_audio=not_captured per_deck_audio=not_attached isolated_decks=false upgrade_path=multi_channel_deck_pair_capture rule=separation_capability_not_outcome]";
const DECK_PAIR_AUDIO_SEPARATION_CONTEXT =
  "deck_audio_separation_context[requested_device=BlackHole_16ch capture_device=BlackHole_16ch input_channels=16 opened_channels=4 sample_rate=48000 device_capacity=multichannel_available mode=deck_pair_capture_configured master_channels=0,1,2,3 current_capture=P1_global_mix_plus_deck_pairs gemini_audio=mono_downmix_of_master_capture deckA_audio=captured deckB_audio=captured per_deck_audio=captured_not_attached isolated_decks=runtime_capture_available deck_pairs=A:0,1+B:2,3 upgrade_path=attach_deck_pair_audio_parts_when_needed deck_audio_activity=A_active+B_active rule=separation_capability_not_outcome]";
const DECK_AUDIO_FEATURES_CONTEXT =
  "deck_audio_features_context[source=deck_pair_capture window=latest_callback per_deck_audio=captured_features A_activity=active A_rms=0.020 A_peak=0.100 A_zcr=0.030 B_activity=active B_rms=0.030 B_peak=0.110 B_zcr=0.035 rule=deck_audio_features_not_outcome_verdict]";
const DECK_AUDIO_DELTA_CONTEXT =
  "deck_audio_delta_context[source=deck_pair_capture window=latest_callback per_deck_delta=captured_feature_delta A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong rule=deck_audio_delta_not_causal_proof]";
const DECK_AUDIO_WINDOW_CONTEXT =
  "deck_audio_window_context[source=deck_pair_capture timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 per_deck_audio=captured_window_features A_pre=active_rms_0.020_peak_0.100_flux_0.004 A_current=active_rms_0.040_peak_0.120_flux_0.009 A_delta=rms_rose_100pct_strong B_pre=active_rms_0.030_peak_0.110_flux_0.006 B_current=active_rms_0.020_peak_0.090_flux_0.004 B_delta=rms_fell_33pct_clear rule=deck_audio_window_not_causal_or_quality_verdict]";
const DECK_PAIR_AUDIO_PART_CONTEXT =
  "audio_part_context[surface=gemini_parts P1=live_global_mix P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 part_order=P1,P2,P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deckA_part=P2 P2=deckA_configured_capture P2_model_heard=true P2_audience_heard=false P2_span=-3.0..0.0 P2_deck_audio=deckA_configured_capture P2_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P3 P3=deckB_configured_capture P3_model_heard=true P3_audience_heard=false P3_span=-3.0..0.0 P3_deck_audio=deckB_configured_capture P3_rule=deck_pair_capture_reference_not_quality_verdict rule=part_labels_not_outcome_verdict]";
const DECK_PAIR_AUDIO_WINDOW_CONTEXT =
  "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future together_audio=P1_global_mix decks_together=true deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context deck_audio_separation=deck_audio_separation_context deck_part_span=-3.0..0.0 deckA_activity=active deckB_activity=active lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 rule=time_alignment_not_outcome_verdict move_anchor=none future_heard=false future=not_attached]";
const searchMock = vi.fn(async (_query: string) => ({
  results: [],
  centered: true,
  corpus_size: 12,
}));
const statsMock = vi.fn(async () => STATS_READY);
const modelsMock = vi.fn(
  async (_install?: LibraryModelInstallTarget) => MODELS_READY,
);
const emitIpcMock =
  vi.fn<(type: string, payload: Record<string, unknown>) => Promise<void>>();

const STATS_READY: LibraryStats = {
  indexed: 12,
  backend: "sqlite-vec",
  embedding_backend: "clap",
  embedding_dim: 512,
  clap_model_installed: true,
  clap_model_path: "~/.cache/vibemix/clap-onnx",
  clap_model_missing: [],
  agent_backend: "codex",
  agent_ready: true,
  agent_status: "ready",
  agent_hint: "",
  library_setup_candidates: [],
  spent_eur: 0,
  failed: 0,
};

const MODELS_READY: LibraryModelsResult = {
  models: [
    {
      id: "clap",
      label: "CLAP ONNX",
      role: "library embeddings/search/similarity",
      required: true,
      env: "VIBEMIX_CLAP_ONNX_DIR",
      installed: true,
      path: "~/.cache/vibemix/clap-onnx",
      missing: [],
      mismatched: [],
    },
    {
      id: "cue-detr",
      label: "CUE-DETR ONNX",
      role: "cue anchors",
      required: false,
      env: "VIBEMIX_CUE_ONNX_PATH",
      installed: true,
      path: "~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx",
      missing: [],
      mismatched: [],
    },
  ],
  required_ready: true,
  all_ready: true,
};

function statsWithSetupCandidate(): LibraryStats {
  return {
    ...STATS_READY,
    indexed: 0,
    library_freshness_status: "not_indexed",
    library_stale: false,
    library_staleness_reason: "library_cache_missing",
    library_age_days: 0,
    library_setup_candidates: [
      {
        kind: "music_folder",
        path: "/Users/ozai/Music/PSYMIND",
        confidence: "high",
        reason: "bounded scan saw 42 supported audio files",
        audio_files_seen: 42,
        import_action: {
          type: "ipc.library.import",
          payload: {
            path: "/Users/ozai/Music/PSYMIND",
            schema_version: "1",
          },
        },
      },
    ],
  };
}

function statsWithEngineSetupCandidate(): LibraryStats {
  const path = "/Users/ozai/Music/Engine Library/Database2/m.db";
  return {
    ...STATS_READY,
    indexed: 0,
    library_freshness_status: "not_indexed",
    library_stale: false,
    library_staleness_reason: "library_cache_missing",
    library_age_days: 0,
    library_setup_candidates: [
      {
        kind: "engine_database",
        path,
        confidence: "high",
        reason: "standard Engine DJ Database2/m.db path exists",
        import_action: {
          type: "ipc.library.import",
          payload: { path, schema_version: "1" },
        },
      },
    ],
  };
}

const CHAT_WITH_PLAYLIST: LibraryChatResult = {
  reply: "Pull SMOKED OUT after the current track and keep the low end clean.",
  tool_trace: [
    { name: "search_vibe", arg: "dark peak techno", ok: true },
    { name: "create_playlist", arg: "Dark Fuse", ok: true },
  ],
  playlist: {
    name: "Dark Fuse",
    track_ids: ["t001", "t002"],
    m3u_path: "/Users/ozai/.cache/vibemix/playlists/dark-fuse.m3u",
    json_path: "/Users/ozai/.cache/vibemix/playlists/dark-fuse.json",
    dropped_ids: [],
  },
  export_path: null,
  seen_track_ids: ["t001", "t002"],
  move_grades: [],
  iterations: 3,
  stop_reason: "created",
};

function readyLiveContext(): LibraryLiveContext {
  return {
    live_context_schema_version: 2,
    live_context_capabilities: [
      "deck_state",
      "deck_source_status",
      "audio_part_context",
      "deck_audio_separation_context",
      "deck_audio_features_context",
      "deck_audio_delta_context",
      "deck_audio_window_context",
      "audio_window_map",
      "audio_delta",
      "live_evidence",
    ],
    deck: "A",
    audible: true,
    music: 0.42,
    deck_state: {
      A: {
        title: "Strobe",
        track_id: "t000",
        camelot: "8A",
        bpm: 128,
        confidence: 0.82,
        source: "rekordbox_xml",
      },
    },
    deck_mixer: {
      connected: true,
      xfader: 64,
      A: { vol: 110, eq_low: 2, eq_mid: 64, eq_hi: 64, filter: 64 },
      B: { vol: 72, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 92 },
    },
    deck_source_status: {
      controller: "present",
      nowplaying: "blocked_non_deck_owner",
      nowplaying_owner: "com.apple.webkit.gpu",
      resolution: "blocked_non_deck_nowplaying",
    },
    deck_lanes_context: DECK_LANES_CONTEXT,
    deck_reference_context: DECK_REFERENCE_CONTEXT,
    deck_source_context: DECK_SOURCE_CONTEXT,
    deck_audio_context: DECK_AUDIO_CONTEXT,
    deck_audio_separation_context: DECK_AUDIO_SEPARATION_CONTEXT,
    audio_part_context:
      "audio_part_context[surface=live_context P1=live_global_mix P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 per_deck_audio=not_attached duplicate_audio=same_master_not_deck_split rule=part_labels_not_outcome_verdict]",
    audio_delta: ["sub energy fell 50% (strong)"],
    audio_window_context:
      "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future deckA_audio=not_attached deckB_audio=not_attached per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]",
    audio_window_map: {
      p1: "master_global_mix",
      p1_heard: true,
      timeline: "past_action_future",
      together_audio: "P1_global_mix",
      decks_together: true,
      deckA_audio: "not_attached",
      deckB_audio: "not_attached",
      per_deck_audio: "structured_text_only",
      duplicate_audio: "same_master_not_deck_split",
      deck_separation: "deck_lanes_context",
      lane_aliases: "deck1:A,deck2:B",
      pre_s: [-6, -1],
      current_s: [-1, 0],
      action_s: [-1, 0],
      move_anchors: [
        {
          label: "A_low: cut->killed",
          token: "a_low_cut_to_killed",
          age_s: 0.7,
          relation: "inside_p1",
        },
      ],
      future: { heard: false, span: "not_attached" },
      rule: "time_alignment_not_outcome_verdict",
    },
    live_evidence: {
      mix: [
        "deck_audio_support=single_deck_A",
        "transition_block=single_resolved_deck",
        "deck_lanes=A_known_route_dominant+B_unknown_route_present",
        "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
        "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
      ],
      refs: [
        "mix:transition_block=single_resolved_deck",
        "mix:deck_lanes=A_known_route_dominant+B_unknown_route_present",
        "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
        "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
      ],
    },
  };
}

function readyDeckPairLiveContext(): LibraryLiveContext {
  const context = readyIdentifiedDeckPairLiveContext();
  return {
    ...context,
    deck_audio_separation_context: DECK_PAIR_AUDIO_SEPARATION_CONTEXT,
    deck_audio_features_context: DECK_AUDIO_FEATURES_CONTEXT,
    deck_audio_delta_context: DECK_AUDIO_DELTA_CONTEXT,
    deck_audio_window_context: DECK_AUDIO_WINDOW_CONTEXT,
    audio_part_context: DECK_PAIR_AUDIO_PART_CONTEXT,
    audio_window_context: DECK_PAIR_AUDIO_WINDOW_CONTEXT,
    audio_window_map: {
      ...(context.audio_window_map ?? {
        p1: "master_global_mix",
        p1_heard: true,
        timeline: "past_action_future",
        together_audio: "P1_global_mix",
        decks_together: true,
        deck_separation: "deck_lanes_context",
        lane_aliases: "deck1:A,deck2:B",
        pre_s: [-6, -1],
        current_s: [-1, 0],
        action_s: [-1, 0],
        move_anchors: [],
        future: { heard: false, span: "not_attached" },
        rule: "time_alignment_not_outcome_verdict",
      }),
      deckA_audio: "P2",
      deckB_audio: "P3",
      per_deck_audio: "deck_pair_parts",
      duplicate_audio: "separate_deck_pair_parts",
      deck_audio_separation: "deck_audio_separation_context",
      deck_part_span_s: [-3, 0],
      deck_part_activity: { A: "active", B: "active" },
    },
    live_evidence: {
      mix: [
        ...(context.live_evidence?.mix ?? []),
        "deck_audio_capture=A_active+B_active",
        "deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
        "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
        "deck_audio_window=A_active_pre_0.020_current_0.040+B_active_pre_0.030_current_0.020",
      ],
      refs: [
        ...(context.live_evidence?.refs ?? []),
        "mix:deck_audio_capture=A_active+B_active",
        "mix:deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
        "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
        "mix:deck_audio_window=A_active_pre_0.020_current_0.040+B_active_pre_0.030_current_0.020",
      ],
    },
  };
}

function readyIdentifiedDeckPairLiveContext(): LibraryLiveContext {
  const context = readyLiveContext();
  return {
    ...context,
    deck_state: {
      ...(context.deck_state ?? {}),
      B: {
        title: "Transit",
        track_id: "t001",
        camelot: "9A",
        bpm: 128,
        confidence: 0.78,
        source: "rekordbox_xml",
      },
    },
    deck_lanes_context: DECK_PAIR_LANES_CONTEXT,
    deck_reference_context: DECK_PAIR_REFERENCE_CONTEXT,
    deck_source_context: DECK_PAIR_SOURCE_CONTEXT,
    deck_audio_context: DECK_PAIR_AUDIO_CONTEXT,
    live_evidence: {
      mix: [
        "transition_watch=two_resolved_decks",
        "deck_lanes=A_known_route_dominant+B_known_route_present",
        "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
        "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_known_src_rekordbox_xml",
      ],
      refs: [
        "mix:transition_watch=two_resolved_decks",
        "mix:deck_lanes=A_known_route_dominant+B_known_route_present",
        "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
        "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_known_src_rekordbox_xml",
      ],
    },
  };
}

function doMockApi(): void {
  liveContextCallback = null;
  liveMoveCallback = null;
  viberToolCallback = null;
  vi.doMock("../ipc/client.js", () => ({
    emitIpc: emitIpcMock,
  }));
  vi.doMock("./api.js", async (importOriginal) => {
    const actual = await importOriginal<typeof import("./api.js")>();
    return {
      ...actual,
      libraryChat: (
        message: string,
        history: unknown[],
        liveContext?: LibraryLiveContext | null,
      ) =>
        liveContext === undefined
          ? chatMock(message, history)
          : chatMock(message, history, liveContext),
      libraryBuildSet: vi.fn(async () => ({
        name: "x",
        rationale: "",
        stop_reason: "exported",
        tracks: [],
        count: 0,
        export_path: null,
      })),
      libraryCurate: vi.fn(async () => ({
        name: "x",
        rationale: "",
        stop_reason: "created",
        tracks: [],
        count: 0,
      })),
      librarySearch: (query: string) => searchMock(query),
      librarySimilar: vi.fn(async () => ({
        results: [],
        centered: true,
        corpus_size: 0,
      })),
      libraryStats: () => statsMock(),
      libraryModels: (install?: LibraryModelInstallTarget) =>
        modelsMock(install),
      libraryEmbedFolder: vi.fn(async () => false),
      onEmbedProgress: vi.fn(async () => () => {}),
      onEmbedDone: vi.fn(async () => () => {}),
      onModelProgress: vi.fn(async () => () => {}),
      onLiveDeckContext: vi.fn(
        async (cb: (context: LibraryLiveContext) => void) => {
          liveContextCallback = cb;
          return () => {};
        },
      ),
      onLiveMoveContext: vi.fn(async (cb: (moves: string[]) => void) => {
        liveMoveCallback = cb;
        return () => {};
      }),
      onViberTool: vi.fn(
        async (
          cb: (event: { tool: string; ok: boolean; summary: string }) => void,
        ) => {
          viberToolCallback = cb;
          return () => {};
        },
      ),
      DEV_FALLBACK: { embedLog: [] },
    };
  });
}

function mountSkeleton(): void {
  document.body.dataset.mode = "chat";
  document.body.innerHTML = `
    <div class="vmx-lib-modeswitch">
      <button data-mode="search" aria-selected="false">Search</button>
      <button data-mode="similar" aria-selected="false">Similar</button>
      <button data-mode="curate" aria-selected="false">Curate</button>
      <button data-mode="build" aria-selected="false">Build</button>
      <button data-mode="cue" aria-selected="false">Cue</button>
      <button data-mode="chat" aria-selected="true">Viber</button>
      <button data-mode="ingest" aria-selected="false">Ingest</button>
    </div>
    <span id="vmx-lib-qlabel"></span>
    <input id="vmx-lib-q" />
    <input id="vmx-lib-folder" value="~/Music" />
    <input id="vmx-lib-cue-folder" value="~/Music" />
    <input id="vmx-lib-theme" />
    <textarea id="vmx-lib-brief"></textarea>
    <textarea id="vmx-lib-chat"></textarea>
    <div class="vmx-lib-curve">
      <button class="vmx-lib-curveseg" data-curve="opener" aria-pressed="false">Opener</button>
      <button class="vmx-lib-curveseg" data-curve="peak_time" aria-pressed="true">Peak time</button>
      <button class="vmx-lib-curveseg" data-curve="after_hours" aria-pressed="false">After hours</button>
      <button class="vmx-lib-curveseg" data-curve="festival" aria-pressed="false">Festival</button>
    </div>
    <button data-cue-export="rekordbox" aria-pressed="true">Rekordbox XML</button>
    <button data-cue-export="m3u8" aria-pressed="false">M3U8</button>
    <button data-cue-export="both" aria-pressed="false">Both</button>
    <span id="vmx-lib-seed-name"></span>
    <button id="vmx-lib-runbtn"></button>
    <span id="vmx-lib-center-label"></span>
    <span id="vmx-lib-echo"></span>
    <div id="vmx-lib-stat-indexed"></div>
    <div id="vmx-lib-stat-backend"></div>
    <div id="vmx-lib-stat-spent"></div>
    <div id="vmx-lib-stat-failed"></div>
    <div id="vmx-lib-model-state"></div>
    <button id="vmx-lib-install-models"></button>
    <div id="vmx-lib-agent-setup" hidden><div id="vmx-lib-agent-state"></div></div>
    <p id="vmx-lib-rationale-body"></p>
    <div id="vmx-lib-rationale-meta"></div>
    <div id="vmx-lib-export" style="display: none"><div id="vmx-lib-export-path"></div></div>
    <div id="vmx-lib-results"></div>
    <div id="vmx-lib-chat-thread">
      <div class="vmx-lib-chat-turn" data-role="viber">
        <div class="who">viber</div>
        <div class="body">I can build a set, solve a transition, or find deep cuts. I will show receipts before you trust it.</div>
      </div>
      <div id="vmx-lib-chat-starters" data-wire="library.chat-starters">
        <button type="button" data-chat="build a 45-minute psytrance set from my indexed tracks, clean energy arc, no fake genres">
          <span>Build a set</span>
          <b>Build 45 min psytrance</b>
        </button>
        <button type="button" data-chat="what mixes cleanly out of the currently playing track? use only grounded live and library evidence">
          <span>What mixes next</span>
          <b>Find grounded transition</b>
        </button>
        <button type="button" data-chat="find deep cuts in my crate that fit this set but avoid the obvious repeats">
          <span>Rediscover</span>
          <b>Find deep cuts, no repeats</b>
        </button>
      </div>
    </div>
    <span id="vmx-lib-rcount"></span>
    <div id="vmx-lib-prog-n"></div>
    <div id="vmx-lib-prog-cost"></div>
    <i id="vmx-lib-progress-fill"></i>
    <div id="vmx-lib-loglist"></div>
    <span id="vmx-lib-side-label"></span>
    <span id="vmx-lib-scope-state"></span>
    <div id="vmx-lib-chat-tools"></div>
    <div id="vmx-lib-chat-artifact"></div>
    <svg id="vmx-lib-scope"></svg>`;
}

async function mountChat(): Promise<void> {
  vi.resetModules();
  doMockApi();
  const { mountLibrary } = await import("./index.js");
  mountSkeleton();
  mountLibrary();
  for (let i = 0; i < 6; i++) await Promise.resolve();
}

async function sendChat(message: string): Promise<void> {
  const input = document.getElementById("vmx-lib-chat") as HTMLTextAreaElement;
  input.value = message;
  (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

describe("chat - real runChat path", () => {
  beforeEach(() => {
    chatMock.mockReset();
    chatMock.mockResolvedValue(CHAT_WITH_PLAYLIST);
    searchMock.mockClear();
    statsMock.mockReset();
    statsMock.mockResolvedValue(STATS_READY);
    modelsMock.mockReset();
    modelsMock.mockResolvedValue(MODELS_READY);
    emitIpcMock.mockReset();
    emitIpcMock.mockResolvedValue(undefined);
    vi.resetModules();
    document.body.innerHTML = "";
  });

  it("opens Viber chat with real starter missions instead of a blank console", async () => {
    await mountChat();

    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("I can build a set");
    expect(threadText).toContain("Build a set");
    expect(threadText).toContain("What mixes next");
    expect(threadText).toContain("Rediscover");
    expect(
      document.querySelector('[data-wire="library.chat-starters"]'),
    ).toBeTruthy();
  });

  it("runs a starter mission through the same Viber path and hides the starter rail", async () => {
    await mountChat();

    document
      .querySelector<HTMLButtonElement>('[data-chat^="what mixes cleanly"]')
      ?.click();
    for (let i = 0; i < 8; i++) await Promise.resolve();

    expect(chatMock).toHaveBeenCalledWith(
      "what mixes cleanly out of the currently playing track? use only grounded live and library evidence",
      [],
    );
    expect(
      document.getElementById("vmx-lib-chat-starters")?.hasAttribute("hidden"),
    ).toBe(true);
    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("what mixes cleanly out of the currently playing track");
    expect(threadText).toContain("Pull SMOKED OUT");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("shows live read status before the user asks Viber", async () => {
    await mountChat();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("waiting");

    const proofRow = document.querySelector<HTMLElement>(
      '.vmx-lib-chat-tool[data-proof="true"]',
    );
    expect(proofRow?.dataset.proofState).toBe("waiting");
  });

  it("surfaces a user-approved library setup action when Viber finds a source", async () => {
    statsMock.mockResolvedValueOnce(statsWithSetupCandidate());

    await mountChat();

    const artifact = document.getElementById("vmx-lib-chat-artifact");
    const setupCard = artifact?.querySelector<HTMLElement>(
      '[data-wire="library.setup-candidate"]',
    );
    expect(setupCard).not.toBeNull();
    expect(setupCard?.textContent).toContain("library setup");
    expect(setupCard?.textContent).toContain("Viber found a likely music folder.");
    expect(setupCard?.textContent).toContain("/Users/ozai/Music/PSYMIND");
    expect(setupCard?.textContent).toContain("waiting for approval");
    expect(setupCard?.textContent).toContain("Index folder");
    expect(emitIpcMock).not.toHaveBeenCalled();
  });

  it("labels Engine DJ setup candidates as importable databases", async () => {
    statsMock.mockResolvedValueOnce(statsWithEngineSetupCandidate());

    await mountChat();

    const setupCard = document.querySelector<HTMLElement>(
      '[data-wire="library.setup-candidate"]',
    );
    expect(setupCard).not.toBeNull();
    expect(setupCard?.textContent).toContain(
      "Viber found a likely Engine DJ database.",
    );
    expect(setupCard?.textContent).toContain(
      "/Users/ozai/Music/Engine Library/Database2/m.db",
    );
    expect(setupCard?.textContent).toContain("Import source");
  });

  it("sends the safe library import action only after the user clicks it", async () => {
    statsMock.mockResolvedValueOnce(statsWithSetupCandidate());

    await mountChat();

    const button = document.querySelector<HTMLButtonElement>(
      '[data-wire="library.setup-candidate"] .vmx-lib-chat-action',
    );
    expect(button).not.toBeNull();
    button?.click();
    for (let i = 0; i < 4; i++) await Promise.resolve();

    expect(emitIpcMock).toHaveBeenCalledTimes(1);
    expect(emitIpcMock).toHaveBeenCalledWith("ipc.library.import", {
      path: "/Users/ozai/Music/PSYMIND",
      schema_version: "1",
    });
    expect(button?.disabled).toBe(true);
    expect(
      document.getElementById("vmx-lib-chat-artifact")?.textContent,
    ).toContain("indexing started");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "indexing library",
    );
  });

  it("keeps the live read partial until deck-pair audio is active", async () => {
    await mountChat();

    liveContextCallback?.(readyIdentifiedDeckPairLiveContext());
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("partial");
    expect(toolText).toContain("deck audio");
    expect(toolText).not.toContain("armed");
  });

  it("arms the live read only after deck-pair audio activity arrives", async () => {
    await mountChat();

    liveContextCallback?.(readyDeckPairLiveContext());
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("armed");
    expect(toolText).toContain("deck1 A=known:dominant");
    expect(toolText).toContain("deck2 B=known:present");
  });

  it("keeps the live read partial when deck audio is active but Deck B is unresolved", async () => {
    await mountChat();

    const context = readyDeckPairLiveContext();
    liveContextCallback?.({
      ...context,
      deck_state: context.deck_state?.A ? { A: context.deck_state.A } : {},
    });
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("partial");
    expect(toolText).toContain("deck identities");
    expect(toolText).not.toContain("armed");
  });

  it("keeps the live read partial when only one captured deck lane is active", async () => {
    await mountChat();

    const oneLane = readyDeckPairLiveContext();
    liveContextCallback?.({
      ...oneLane,
      live_evidence: {
        mix: (oneLane.live_evidence?.mix ?? []).map((token) =>
          token
            .replace(
              "deck_audio_capture=A_active+B_active",
              "deck_audio_capture=A_active+B_silent",
            )
            .replace(
              "deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
              "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
            )
            .replace(
              "deck_audio_window=A_active_pre_0.020_current_0.040+B_active_pre_0.030_current_0.020",
              "deck_audio_window=A_active_pre_0.020_current_0.040+B_silent_pre_0.030_current_0.000",
            ),
        ),
        refs: (oneLane.live_evidence?.refs ?? []).map((token) =>
          token
            .replace(
              "mix:deck_audio_capture=A_active+B_active",
              "mix:deck_audio_capture=A_active+B_silent",
            )
            .replace(
              "mix:deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
              "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
            )
            .replace(
              "mix:deck_audio_window=A_active_pre_0.020_current_0.040+B_active_pre_0.030_current_0.020",
              "mix:deck_audio_window=A_active_pre_0.020_current_0.040+B_silent_pre_0.030_current_0.000",
            ),
        ),
      },
    });
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("partial");
    expect(toolText).toContain("both decks active");
    expect(toolText).not.toContain("armed");
  });

  it("passes Deck A/B audio-window part labels into Viber chat", async () => {
    await mountChat();

    liveContextCallback?.(readyDeckPairLiveContext());
    await sendChat("what changed by deck?");

    expect(chatMock).toHaveBeenLastCalledWith(
      "what changed by deck?",
      [],
      expect.objectContaining({
        audio_part_context: expect.stringContaining(
          "per_deck_audio=deck_pair_parts",
        ),
        audio_window_context: expect.stringContaining("deckA_audio=P2"),
        deck_audio_window_context: expect.stringContaining(
          "timeline=pre_action_current",
        ),
        audio_window_map: expect.objectContaining({
          deckA_audio: "P2",
          deckB_audio: "P3",
          per_deck_audio: "deck_pair_parts",
          duplicate_audio: "separate_deck_pair_parts",
          deck_audio_separation: "deck_audio_separation_context",
          deck_part_span_s: [-3, 0],
          deck_part_activity: { A: "active", B: "active" },
        }),
      }),
    );
  });

  it("clears stale Deck A/B audio part context when a later frame omits it", async () => {
    await mountChat();

    liveContextCallback?.(readyDeckPairLiveContext());
    liveContextCallback?.({ deck: "A", audible: true });
    await sendChat("is the deck split still attached?");

    expect(chatMock).toHaveBeenLastCalledWith(
      "is the deck split still attached?",
      [],
      expect.not.objectContaining({
        audio_part_context: expect.any(String),
        audio_window_context: expect.any(String),
        audio_window_map: expect.any(Object),
        deck_audio_separation_context: expect.any(String),
        deck_audio_features_context: expect.any(String),
        deck_audio_delta_context: expect.any(String),
        deck_audio_window_context: expect.any(String),
      }),
    );
  });

  it("keeps live read partial when deck-pair receipts are missing", async () => {
    await mountChat();

    const context = readyDeckPairLiveContext();
    liveContextCallback?.({
      ...context,
      live_evidence: {
        mix: (context.live_evidence?.mix ?? []).filter(
          (token) =>
            !token.includes("deck_audio_features=") &&
            !token.includes("deck_audio_delta=") &&
            !token.includes("deck_audio_window="),
        ),
        refs: (context.live_evidence?.refs ?? []).filter(
          (token) =>
            !token.includes("deck_audio_features=") &&
            !token.includes("deck_audio_delta=") &&
            !token.includes("deck_audio_window="),
        ),
      },
    });
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("proof gate");
    expect(toolText).toContain("partial");
    expect(toolText).toContain("feature receipt");
    expect(toolText).not.toContain("armed");
  });

  it("renders a grounded tool trace and playlist artifact from one Viber turn", async () => {
    await mountChat();
    await sendChat("find two dark peak techno tracks");

    expect(chatMock).toHaveBeenCalledWith(
      "find two dark peak techno tracks",
      [],
    );

    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("find two dark peak techno tracks");
    expect(threadText).toContain("Pull SMOKED OUT");
    expect(
      (document.getElementById("vmx-lib-chat") as HTMLTextAreaElement).value,
    ).toBe("");

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("search_vibe");
    expect(toolText).toContain("dark peak techno");
    expect(toolText).toContain("create_playlist");

    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("playlist");
    expect(artifactText).toContain("Dark Fuse");
    expect(artifactText).toContain("2 tracks");
    expect(artifactText).toContain("dark-fuse.m3u");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "3 iter · created",
    );
  });

  it("renders the live read verifier beside a Viber chat reply", async () => {
    chatMock.mockResolvedValueOnce({
      ...CHAT_WITH_PLAYLIST,
      reply:
        "I caught the live move. The useful note is the sound change right there.",
      tool_trace: [],
      playlist: null,
      seen_track_ids: [],
      iterations: 1,
      stop_reason: "model_done",
      live_verification: {
        ok: true,
        violations: [],
        reply:
          "I caught the live move. The useful note is the sound change right there.",
        corrected: false,
        corrected_reply: null,
        claim_policy: "blocked",
        transport_status: "fresh_schema_v2",
        move_grades_allowed: false,
        move_grades_seen: 0,
        guard_applied: true,
        guard_violations: ["unsupported_live_outcome_claim"],
      },
    } satisfies LibraryChatResult);

    await mountChat();
    await sendChat("was that a transition?");

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("live read");
    expect(toolText).toContain("fresh");
    expect(toolText).toContain("live move checked");
    expect(toolText).toContain("grounded");
    expect(toolText).not.toContain("live_reply_verify");
    expect(toolText).not.toContain("guard");
    expect(toolText).not.toContain("unsupported_live_outcome_claim");

    const proofRow = document.querySelector<HTMLElement>(
      '.vmx-lib-chat-tool[data-proof="true"]',
    );
    expect(proofRow?.dataset.ok).toBe("true");

    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("live read");
    expect(artifactText).toContain("live move checked");
    expect(artifactText).not.toContain("guard");
    expect(artifactText).not.toContain("unsupported_live_outcome_claim");
  });

  it("renders supported live verdicts as grounded scoring", async () => {
    chatMock.mockResolvedValueOnce({
      ...CHAT_WITH_PLAYLIST,
      reply: "Great transition, clean handoff.",
      tool_trace: [],
      playlist: null,
      seen_track_ids: [],
      move_grades: [
        {
          candidate_id: "tr_001",
          track_id: "t000",
          title: "Tt000",
          slug: "lit_aff",
          label: "LIT AFF",
          xp: 100,
          reason: "both decks are locked",
          overdrive: true,
        },
      ],
      iterations: 1,
      stop_reason: "model_done",
      live_verification: {
        ok: true,
        violations: [],
        reply: "Great transition, clean handoff.",
        corrected: false,
        corrected_reply: null,
        claim_policy: "supported_verdict",
        transport_status: "fresh_schema_v2",
        move_grades_allowed: true,
        move_grades_seen: 1,
        guard_applied: false,
        guard_violations: [],
      },
    } satisfies LibraryChatResult);

    await mountChat();
    await sendChat("was that transition good?");

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("live read");
    expect(toolText).toContain("fresh");
    expect(toolText).toContain("scoring grounded");
    expect(toolText).not.toContain("supported_verdict");

    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("live read");
    expect(artifactText).toContain("scoring grounded");
    expect(artifactText).toContain("move scoring grounded by live read");
    expect(artifactText).not.toContain("claim_policy");
    expect(artifactText).not.toContain("supported_verdict");
  });

  it("hides internal live read failure labels from the chat chrome", async () => {
    chatMock.mockResolvedValueOnce({
      ...CHAT_WITH_PLAYLIST,
      reply:
        "Start live monitoring first, then I'll read the live move from the decks.",
      tool_trace: [
        {
          name: "live_context_required",
          arg: "waiting for live deck feed",
          ok: false,
        },
      ],
      playlist: null,
      seen_track_ids: [],
      iterations: 0,
      stop_reason: "live_context_required",
      live_verification: {
        ok: false,
        violations: ["missing_live_context"],
        reply:
          "Start live monitoring first, then I'll read the live move from the decks.",
        corrected: false,
        corrected_reply: null,
        claim_policy: "requires_more_evidence",
        transport_status: "missing_live_context",
        move_grades_allowed: false,
        move_grades_seen: 0,
        guard_applied: false,
        guard_violations: [],
      },
    } satisfies LibraryChatResult);

    await mountChat();
    await sendChat("was that transition good?");

    const toolText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(toolText).toContain("live read");
    expect(toolText).toContain("waiting");
    expect(toolText).toContain("listening");
    expect(toolText).not.toContain("live_context_required");
    expect(toolText).not.toContain("proof gate not armed");
    expect(toolText).not.toContain("requires_more_evidence");

    expect(document.querySelectorAll(".vmx-lib-chat-tool")).toHaveLength(1);
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "live read waiting",
    );

    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("live read");
    expect(artifactText).toContain("listening");
    expect(artifactText).not.toContain("live_context_required");
    expect(artifactText).not.toContain("requires_more_evidence");
  });

  it("keeps the library setup action visible when proof gate is still waiting", async () => {
    statsMock.mockResolvedValueOnce(statsWithSetupCandidate());
    chatMock.mockResolvedValueOnce({
      ...CHAT_WITH_PLAYLIST,
      reply:
        "I need a stronger live read before I can grade that, and I found a likely library source.",
      tool_trace: [
        {
          name: "live_context_required",
          arg: "waiting for live deck feed",
          ok: false,
        },
      ],
      playlist: null,
      seen_track_ids: [],
      iterations: 0,
      stop_reason: "live_context_required",
      live_verification: {
        ok: false,
        violations: ["missing_library", "missing_live_context"],
        reply: "Index the library first, then I can bind deck identity.",
        corrected: false,
        corrected_reply: null,
        claim_policy: "requires_more_evidence",
        transport_status: "missing_live_context",
        move_grades_allowed: false,
        move_grades_seen: 0,
        guard_applied: false,
        guard_violations: [],
      },
    } satisfies LibraryChatResult);

    await mountChat();
    await sendChat("why can't you read the decks?");

    const artifact = document.getElementById("vmx-lib-chat-artifact");
    const cards = artifact?.querySelectorAll<HTMLElement>(".vmx-lib-chat-card");
    expect(cards).toHaveLength(2);
    const firstCard = cards?.item(0);
    expect(firstCard).not.toBeNull();
    expect(firstCard?.textContent).toContain("live read");
    expect(firstCard?.textContent).toContain("listening");

    const setupCard = artifact?.querySelector<HTMLElement>(
      '[data-wire="library.setup-candidate"]',
    );
    expect(setupCard).not.toBeNull();
    expect(setupCard?.textContent).toContain("Viber found a likely music folder.");
    expect(setupCard?.textContent).toContain("/Users/ozai/Music/PSYMIND");
    expect(setupCard?.textContent).toContain("waiting for approval");
    expect(emitIpcMock).not.toHaveBeenCalled();
  });

  it("shows the live Viber tool tape while the chat turn is still running", async () => {
    let resolveChat!: (value: LibraryChatResult) => void;
    chatMock.mockImplementationOnce(
      () =>
        new Promise<LibraryChatResult>((resolve) => {
          resolveChat = resolve;
        }),
    );

    await mountChat();
    await sendChat("find a dark rolling bridge");
    viberToolCallback?.({
      tool: "search_vibe",
      ok: true,
      summary: "dark rolling bridge; 8 tracks",
    });
    for (let i = 0; i < 4; i++) await Promise.resolve();

    const liveText =
      document.getElementById("vmx-lib-chat-tools")?.textContent ?? "";
    expect(liveText).toContain("search_vibe");
    expect(liveText).toContain("dark rolling bridge");
    expect(liveText).toContain("8 tracks");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "working",
    );

    resolveChat(CHAT_WITH_PLAYLIST);
    for (let i = 0; i < 8; i++) await Promise.resolve();
  });

  it("renders a built set as a numbered, ordered track breakdown", async () => {
    // A build/curate turn returns a playlist of track_ids (titles, when known,
    // ride in move_grades). Removing the Build/Curate tabs must NOT lose the
    // ordered "01. track" set view — the conversation has to reproduce it.
    chatMock.mockResolvedValue({
      ...CHAT_WITH_PLAYLIST,
      playlist: {
        name: "Warehouse 90",
        track_ids: ["t001", "t002", "t003"],
        m3u_path: "/Users/ozai/.cache/vibemix/playlists/warehouse-90.m3u",
        json_path: "/Users/ozai/.cache/vibemix/playlists/warehouse-90.json",
        dropped_ids: ["tX"],
      },
      move_grades: [
        {
          candidate_id: "c1",
          track_id: "t001",
          title: "SMOKED OUT",
          slug: "clean",
          label: "Clean",
          xp: 10,
          reason: "low end clean",
          overdrive: false,
        },
        {
          candidate_id: "c2",
          track_id: "t002",
          title: "DEEPER STILL",
          slug: "sexy",
          label: "Sexy",
          xp: 20,
          reason: "tension holds",
          overdrive: false,
        },
      ],
    } satisfies LibraryChatResult);

    await mountChat();
    await sendChat("build me a 90 minute warehouse set");

    const breakdown = document.querySelector(
      '[data-wire="library.chat-set-breakdown"]',
    );
    expect(breakdown).not.toBeNull();
    const breakdownText = breakdown?.textContent ?? "";
    // numbered + ordered: all three slots, zero-padded ranks
    expect(breakdownText).toContain("01");
    expect(breakdownText).toContain("02");
    expect(breakdownText).toContain("03");
    // titles enrich the rows from move_grades when known…
    expect(breakdownText).toContain("SMOKED OUT");
    expect(breakdownText).toContain("DEEPER STILL");
    // …and the bare id is the honest fallback when no title exists (t003 has
    // no move_grade) — proving the breakdown renders EVERY track, not just graded ones.
    expect(breakdownText).toContain("t003");
    // dropped tracks are surfaced, not silently swallowed
    const artifactText =
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "";
    expect(artifactText).toContain("1 dropped");
  });

  it("passes the latest live deck context into a Viber chat turn", async () => {
    await mountChat();
    const liveContext: LibraryLiveContext = {
      live_context_schema_version: 2,
      live_context_capabilities: [
        "deck_state",
        "deck_source_status",
        "audio_part_context",
        "deck_audio_separation_context",
        "deck_audio_features_context",
        "deck_audio_delta_context",
        "deck_audio_window_context",
        "audio_window_map",
        "audio_delta",
        "live_evidence",
      ],
      deck: "A",
      audible: true,
      phase: "groove",
      bpm: 128,
      music: 0.4,
      deck_state: {
        A: {
          title: "Strobe",
          camelot: "8A",
          bpm: 128,
          confidence: 0.8,
          source: "rekordbox_xml",
        },
      },
      deck_mixer: {
        connected: true,
        xfader: 64,
        A: { vol: 110, eq_low: 2, eq_mid: 64, eq_hi: 64, filter: 64 },
        B: { vol: 0, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 64 },
      },
      deck_source_status: {
        controller: "present",
        nowplaying: "blocked_non_deck_owner",
        nowplaying_owner: "com.apple.webkit.gpu",
        resolution: "blocked_non_deck_nowplaying",
      },
      deck_lanes_context: DECK_LANES_CONTEXT,
      deck_reference_context: DECK_REFERENCE_CONTEXT,
      deck_source_context: DECK_SOURCE_CONTEXT,
      deck_audio_context: DECK_AUDIO_CONTEXT,
      deck_audio_separation_context: DECK_AUDIO_SEPARATION_CONTEXT,
      audio_part_context:
        "audio_part_context[surface=live_context P1=live_global_mix P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 per_deck_audio=not_attached duplicate_audio=same_master_not_deck_split rule=part_labels_not_outcome_verdict]",
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future deckA_audio=not_attached deckB_audio=not_attached per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]",
      audio_delta: ["sub energy fell 50% (strong)"],
      live_evidence: {
        mix: [
          "deck_audio_support=single_deck_A",
          "transition_block=single_resolved_deck",
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "second_deck_identity=unknown_or_suppressed",
          "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "deck_route=A_dominant+B_muted",
        ],
        refs: [
          "mix:deck_audio_support=single_deck_A",
          "mix:transition_block=single_resolved_deck",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "mix:deck_route=A_dominant+B_muted",
        ],
      },
    };
    liveContextCallback?.(liveContext);
    liveMoveCallback?.(["A_low: cut->killed"]);

    await sendChat("was that a transition?");

    expect(chatMock).toHaveBeenCalledWith("was that a transition?", [], {
      ...liveContext,
      recent_moves: ["A_low: cut->killed"],
    });
  });

  it("merges live evidence across deck frames before a Viber chat turn", async () => {
    await mountChat();
    liveContextCallback?.({
      deck: "A",
      audible: true,
      music: 0.2,
      deck_state: {
        A: {
          title: "Strobe",
          track_id: "track-1",
          camelot: "8A",
          confidence: 0.8,
          source: "rekordbox_xml",
        },
      },
      audio_delta: ["sub energy fell 50% (strong)"],
      deck_lanes_context: DECK_LANES_CONTEXT,
      deck_reference_context: DECK_REFERENCE_CONTEXT,
      deck_source_context: DECK_SOURCE_CONTEXT,
      deck_audio_context: DECK_AUDIO_CONTEXT,
      live_evidence: {
        mix: [
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
        ],
        refs: [
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
        ],
      },
    });
    liveContextCallback?.({
      deck: "A",
      music: 0.01,
      deck_mixer: {
        connected: true,
        xfader: 0,
        A: { vol: 112, eq_low: 2, eq_mid: 64, eq_hi: 64, filter: 64 },
        B: { vol: 0, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 64 },
      },
      deck_lanes_context: DECK_LANES_CONTEXT,
      deck_reference_context: DECK_REFERENCE_CONTEXT,
      deck_source_context: DECK_SOURCE_CONTEXT,
      deck_audio_context: DECK_AUDIO_CONTEXT,
      live_evidence: {
        mix: ["transition_block=single_resolved_deck"],
        refs: ["mix:transition_block=single_resolved_deck"],
        midi: [{ key: "A_low_cut_to_killed", t: 42 }],
      },
    });
    liveMoveCallback?.(["A_low: cut->killed"]);

    await sendChat("what really happened?");

    expect(chatMock).toHaveBeenCalledWith("what really happened?", [], {
      deck: "A",
      audible: true,
      music: 0.2,
      deck_state: {
        A: {
          title: "Strobe",
          track_id: "track-1",
          camelot: "8A",
          confidence: 0.8,
          source: "rekordbox_xml",
        },
      },
      deck_mixer: {
        connected: true,
        xfader: 0,
        A: { vol: 112, eq_low: 2, eq_mid: 64, eq_hi: 64, filter: 64 },
        B: { vol: 0, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 64 },
      },
      deck_lanes_context: DECK_LANES_CONTEXT,
      deck_reference_context: DECK_REFERENCE_CONTEXT,
      deck_source_context: DECK_SOURCE_CONTEXT,
      deck_audio_context: DECK_AUDIO_CONTEXT,
      audio_delta: ["sub energy fell 50% (strong)"],
      live_evidence: {
        mix: [
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "transition_block=single_resolved_deck",
          "second_deck_identity=unknown_or_suppressed",
          "deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "deck_audio_support=single_deck_A",
          "deck_route=A_dominant+B_muted",
        ],
        refs: [
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "mix:transition_block=single_resolved_deck",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "mix:deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "midi:A_low_cut_to_killed@42.0",
          "mix:deck_audio_support=single_deck_A",
          "mix:deck_route=A_dominant+B_muted",
        ],
        midi: [{ key: "A_low_cut_to_killed", t: 42 }],
      },
      recent_moves: ["A_low: cut->killed"],
    });
  });

  it("passes live audio window context from deck frames without making it stale", async () => {
    await mountChat();
    liveContextCallback?.({
      deck: "A",
      audible: true,
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future deckA_audio=not_attached deckB_audio=not_attached per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]",
      recent_moves: ["A_low: cut->killed"],
    });

    await sendChat("what happened?");

    expect(chatMock).toHaveBeenLastCalledWith("what happened?", [], {
      deck: "A",
      audible: true,
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future deckA_audio=not_attached deckB_audio=not_attached per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]",
      recent_moves: ["A_low: cut->killed"],
    });

    chatMock.mockClear();
    liveContextCallback?.({ deck: "A", audible: true });

    await sendChat("and now?");

    expect(chatMock).toHaveBeenLastCalledWith("and now?", expect.any(Array), {
      deck: "A",
      audible: true,
      recent_moves: ["A_low: cut->killed"],
    });
  });

  it("drops raw live deck context that the normalizer rejects", async () => {
    await mountChat();
    liveContextCallback?.({
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future deckA_audio=P2 deckB_audio=P3 per_deck_audio=attached duplicate_audio=separate_deck_pair_parts rule=time_alignment_not_outcome_verdict]",
    } as unknown as LibraryLiveContext);

    await sendChat("should Viber trust this?");

    expect(chatMock.mock.calls.at(-1)).toEqual(["should Viber trust this?", []]);
  });

  it("clears stale deck identity when an explicit empty deck frame arrives", async () => {
    await mountChat();
    liveContextCallback?.({
      deck: "A",
      audible: true,
      deck_state: {
        A: {
          title: "Strobe",
          track_id: "track-1",
          camelot: "8A",
          confidence: 0.8,
          source: "rekordbox_xml",
        },
      },
      deck_mixer: {
        connected: true,
        xfader: 0,
        A: { vol: 112, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 64 },
        B: { vol: 0, eq_low: 64, eq_mid: 64, eq_hi: 64, filter: 64 },
      },
      deck_lanes_context: DECK_LANES_CONTEXT,
      deck_reference_context: DECK_REFERENCE_CONTEXT,
      deck_source_context: DECK_SOURCE_CONTEXT,
      deck_audio_context: DECK_AUDIO_CONTEXT,
    });
    liveContextCallback?.({
      deck: "none",
      audible: false,
      deck_state: {},
      deck_mixer: { connected: false },
    });

    await sendChat("what is loaded now?");

    expect(chatMock).toHaveBeenCalledWith("what is loaded now?", [], {
      deck: "none",
      audible: false,
      deck_state: {},
      deck_mixer: { connected: false },
      recent_moves: [],
    });
  });

  it("keeps recent moves across empty delta snapshots before a Viber chat turn", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-29T00:00:00Z"));
    await mountChat();
    const liveContext: LibraryLiveContext = {
      deck: "A",
      audible: true,
      deck_state: {
        A: { title: "Strobe", camelot: "8A", bpm: 128, confidence: 0.8 },
      },
    };
    liveContextCallback?.(liveContext);
    liveMoveCallback?.(["A_low: cut->killed"]);
    liveMoveCallback?.([]);

    await sendChat("what happened now?");

    expect(chatMock).toHaveBeenCalledWith("what happened now?", [], {
      ...liveContext,
      live_evidence: {
        mix: [
          "transition_block=single_resolved_deck",
          "second_deck_identity=unknown_or_suppressed",
          "deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "deck_source=deck1_A_known_src_unknown+deck2_B_unknown_src_none",
        ],
        refs: [
          "mix:transition_block=single_resolved_deck",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "mix:deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "mix:deck_source=deck1_A_known_src_unknown+deck2_B_unknown_src_none",
        ],
      },
      recent_moves: ["A_low: cut->killed"],
    });
  });

  it("expires recent moves after the bounded Viber context window", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-29T00:00:00Z"));
    await mountChat();
    const liveContext: LibraryLiveContext = {
      deck: "A",
      audible: true,
      deck_state: {
        A: { title: "Strobe", camelot: "8A", bpm: 128, confidence: 0.8 },
      },
    };
    liveContextCallback?.(liveContext);
    liveMoveCallback?.(["A_low: cut->killed"]);
    vi.advanceTimersByTime(8_001);
    liveMoveCallback?.([]);

    await sendChat("what happened now?");

    expect(chatMock).toHaveBeenCalledWith("what happened now?", [], {
      ...liveContext,
      live_evidence: {
        mix: [
          "transition_block=single_resolved_deck",
          "second_deck_identity=unknown_or_suppressed",
          "deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "deck_source=deck1_A_known_src_unknown+deck2_B_unknown_src_none",
        ],
        refs: [
          "mix:transition_block=single_resolved_deck",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
          "mix:deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
          "mix:deck_source=deck1_A_known_src_unknown+deck2_B_unknown_src_none",
        ],
      },
      recent_moves: [],
    });
  });

  it("renders Viber move-grade receipts as a chat artifact", async () => {
    chatMock.mockResolvedValueOnce({
      reply: "That bridge is LIT AFF.",
      tool_trace: [
        { name: "transition_slate", arg: "Bridge A -> Insane Click", ok: true },
        { name: "compile_musical_context", arg: "tr_001", ok: true },
      ],
      playlist: null,
      export_path: null,
      seen_track_ids: ["t001"],
      move_grades: [
        {
          candidate_id: "tr_001",
          track_id: "t001",
          title: "Insane Click",
          slug: "lit_aff",
          label: "LIT AFF",
          xp: 100,
          reason: "everything clicks",
          overdrive: true,
          streak: 4,
          total_xp: 288,
          level: 2,
          level_xp: 38,
          next_level_xp: 250,
          level_up: true,
          levels_gained: 1,
        },
      ],
      iterations: 2,
      stop_reason: "model_done",
    });

    await mountChat();
    await sendChat("what bridge clicks?");

    const artifact = document.getElementById(
      "vmx-lib-chat-artifact",
    ) as HTMLElement;
    const grade = artifact.querySelector<HTMLElement>(
      '[data-wire="library.chat-move-grade"]',
    );
    expect(artifact.textContent).toContain("moves");
    expect(grade?.dataset.moveGrade).toBe("lit_aff");
    expect(grade?.dataset.overdrive).toBe("true");
    expect(grade?.dataset.levelUp).toBe("true");
    expect(grade?.dataset.intel).toBe("overdrive");
    expect(grade?.dataset.gradeLevel).toBe("2");
    expect(grade?.dataset.totalXp).toBe("288");
    expect(grade?.title).toBe("DJ KNOWS");
    expect(grade?.getAttribute("aria-label")).toBe("DJ KNOWS");
    expect(grade?.textContent).toContain("LIT AFF");
    expect(grade?.textContent).toContain("+100xp");
    expect(grade?.textContent).toContain("LV2");
    expect(grade?.textContent).toContain("x4");
    expect(grade?.textContent).toContain("LEVEL UP");
    expect(grade?.textContent).toContain("Insane Click");
  });

  it("marks ordinary Viber move grades as DJ-known earned/care receipts", async () => {
    chatMock.mockResolvedValueOnce({
      reply: "One move works, one needs care.",
      tool_trace: [{ name: "transition_slate", arg: "two options", ok: true }],
      playlist: null,
      export_path: null,
      seen_track_ids: ["t_clean", "t_risk"],
      move_grades: [
        {
          candidate_id: "tr_clean",
          track_id: "t_clean",
          title: "Clean Lift",
          slug: "clean",
          label: "CLEAN",
          xp: 28,
          reason: "phrase and cue locked",
          overdrive: false,
          streak: 2,
          total_xp: 56,
          level: 1,
          level_xp: 56,
          next_level_xp: 250,
          level_up: false,
          levels_gained: 0,
        },
        {
          candidate_id: "tr_risk",
          track_id: "t_risk",
          title: "Risk Move",
          slug: "negative",
          label: "NEG",
          xp: 0,
          reason: "key clash",
          overdrive: false,
          streak: 0,
          total_xp: 56,
          level: 1,
          level_xp: 56,
          next_level_xp: 250,
          level_up: false,
          levels_gained: 0,
        },
      ],
      iterations: 2,
      stop_reason: "model_done",
    });

    await mountChat();
    await sendChat("which moves?");

    const grades = Array.from(
      document.querySelectorAll<HTMLElement>(
        '[data-wire="library.chat-move-grade"]',
      ),
    );
    expect(grades).toHaveLength(2);
    expect(grades[0]?.dataset.intel).toBe("earned");
    expect(grades[0]?.title).toBe("DJ KNOWS · phrase and cue locked");
    expect(grades[0]?.getAttribute("aria-label")).toBe(
      "DJ KNOWS · phrase and cue locked",
    );
    expect(grades[1]?.dataset.intel).toBe("care");
    expect(grades[1]?.title).toBe("DJ KNOWS · key clash");
    expect(grades[1]?.getAttribute("aria-label")).toBe("DJ KNOWS · key clash");
  });

  it("renders Viber clarification choices as a chat artifact", async () => {
    chatMock.mockResolvedValueOnce({
      reply: "Which room are we aiming at?\n1. headphones\n2. club",
      tool_trace: [
        {
          name: "request_clarification",
          arg: "Which room are we aiming at?",
          ok: true,
        },
      ],
      playlist: null,
      export_path: null,
      seen_track_ids: [],
      move_grades: [],
      iterations: 1,
      stop_reason: "clarification_needed",
      question: "Which room are we aiming at?",
      choices: ["headphones", "club"],
    });

    await mountChat();
    await sendChat("make it uplifting");

    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("Which room are we aiming at?");
    expect(threadText).toContain("1. headphones");

    const artifact = document.getElementById(
      "vmx-lib-chat-artifact",
    ) as HTMLElement;
    const card = artifact.querySelector(
      '[data-wire="library.chat-clarification"]',
    );
    expect(card?.textContent).toContain("clarify");
    expect(card?.textContent).toContain("Which room are we aiming at?");
    expect(card?.textContent).toContain("2. club");
    expect(document.getElementById("vmx-lib-scope-state")?.textContent).toBe(
      "1 iter · clarification_needed",
    );
  });

  it("renders live indexed count without the stale mock denominator", async () => {
    await mountChat();

    const indexed =
      document.getElementById("vmx-lib-stat-indexed")?.textContent ?? "";
    expect(indexed).toBe("12");
    expect(indexed).not.toContain("1547");
  });

  it("keeps the idle Crate face product-readable, not backend-readable", async () => {
    await mountChat();

    const search =
      document.getElementById("vmx-lib-stat-backend")?.textContent ?? "";
    const setup =
      document.getElementById("vmx-lib-model-state")?.textContent ?? "";

    expect(search).toBe("local");
    expect(setup).toContain("search ready");
    expect(setup).toContain("cue export ready");
    expect(search).not.toContain("sqlite-vec");
    expect(setup).not.toContain("CLAP ready");
    expect(setup).not.toContain("MOSS ready");
    expect(setup).not.toContain("CUE ready");
  });

  it("renders honest setup errors when boot stats or model checks fail", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    statsMock.mockRejectedValueOnce(new Error("stats bridge down"));
    modelsMock.mockRejectedValueOnce(new Error("model bridge down"));

    await mountChat();

    expect(document.getElementById("vmx-lib-stat-indexed")?.textContent).toBe(
      "·",
    );
    expect(document.getElementById("vmx-lib-stat-backend")?.textContent).toBe(
      "unavailable",
    );
    expect(document.getElementById("vmx-lib-model-state")?.textContent).toBe(
      "model check failed · model bridge down",
    );
    expect(
      (document.getElementById("vmx-lib-install-models") as HTMLButtonElement)
        .hidden,
    ).toBe(true);
    expect(errorSpy).toHaveBeenCalledWith(
      "[vmx-lib] stats refresh failed:",
      expect.any(Error),
    );
    expect(errorSpy).toHaveBeenCalledWith(
      "[vmx-lib] model refresh failed:",
      expect.any(Error),
    );
  });

  it("passes only completed prior turns as history on the next message", async () => {
    chatMock
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "First answer" })
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "Second answer" });

    await mountChat();
    await sendChat("first");
    await sendChat("second");

    expect(chatMock).toHaveBeenNthCalledWith(1, "first", []);
    expect(chatMock).toHaveBeenNthCalledWith(2, "second", [
      { role: "you", text: "first" },
      { role: "viber", text: "First answer" },
    ]);
  });

  it("does not keep a thrown backend turn in API history", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    chatMock
      .mockRejectedValueOnce(new Error("sidecar down"))
      .mockResolvedValueOnce({ ...CHAT_WITH_PLAYLIST, reply: "Recovered" });

    await mountChat();
    await sendChat("first");
    await sendChat("second");

    expect(chatMock).toHaveBeenNthCalledWith(1, "first", []);
    expect(chatMock).toHaveBeenNthCalledWith(2, "second", []);
    expect(errorSpy).toHaveBeenCalled();
    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("engine error: sidecar down");
    expect(threadText).toContain("Recovered");
  });

  it("ignores a stale Viber reply after the user switches modes", async () => {
    let resolveChat!: (value: LibraryChatResult) => void;
    chatMock.mockImplementationOnce(
      () =>
        new Promise<LibraryChatResult>((resolve) => {
          resolveChat = resolve;
        }),
    );

    await mountChat();
    const input = document.getElementById(
      "vmx-lib-chat",
    ) as HTMLTextAreaElement;
    input.value = "slow turn";
    (document.getElementById("vmx-lib-runbtn") as HTMLButtonElement).click();
    for (let i = 0; i < 4; i++) await Promise.resolve();

    document
      .querySelector<HTMLButtonElement>(
        '.vmx-lib-modeswitch button[data-mode="search"]',
      )
      ?.click();
    for (let i = 0; i < 8; i++) await Promise.resolve();

    expect(document.body.dataset.mode).toBe("search");
    expect(searchMock).toHaveBeenCalled();

    resolveChat(CHAT_WITH_PLAYLIST);
    for (let i = 0; i < 8; i++) await Promise.resolve();

    const threadText =
      document.getElementById("vmx-lib-chat-thread")?.textContent ?? "";
    expect(threadText).toContain("slow turn");
    expect(threadText).not.toContain("Pull SMOKED OUT");
    expect(
      document.getElementById("vmx-lib-chat-artifact")?.textContent ?? "",
    ).not.toContain("Dark Fuse");
    expect(document.getElementById("vmx-lib-rcount")?.textContent).toBe(
      "0 of 12",
    );
  });
});
