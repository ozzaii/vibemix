// SPDX-License-Identifier: Apache-2.0
/* Vibe Engine — api.ts dev-fallback vitest spec.
 *
 * Runs under node with no `@tauri-apps/api/core` resolvable invoke (vitest
 * env), so every client call MUST fall through to the real 2026-05-25
 * subset-run sample data — the same numbers baked into the mock. No network.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

import {
  DEV_FALLBACK,
  libraryBuildSet,
  libraryChat,
  libraryCueFolder,
  libraryEmbedFolder,
  libraryModels,
  librarySearch,
  librarySimilar,
  libraryStats,
  normalizeBuildSetResult,
  normalizeChatResult,
  normalizeCurateResult,
  normalizeCueResult,
  normalizeEmbedProgress,
  normalizeLiveContextPayload,
  normalizeLiveMovePayload,
  normalizeModelsResult,
  normalizeSearchResult,
  normalizeStats,
} from "./api.js";

afterEach(() => {
  vi.doUnmock("@tauri-apps/api/event");
  vi.restoreAllMocks();
});

// Under vitest there is no Tauri runtime: `invoke()` either is unresolvable or
// throws when called. Either way every client function must fall through to the
// real 2026-05-25 subset-run sample — that's the contract these tests pin.
describe("dev fallback (no Tauri bridge)", () => {
  it("librarySearch returns the techno subset (6 rows, top = Raffertie)", async () => {
    const r = await librarySearch("hard aggressive techno");
    expect(r.results).toHaveLength(6);
    expect(r.corpus_size).toBe(142);
    expect(r.centered).toBe(true);
    expect(r.results[0]?.title).toBe("Raffertie — The Substance");
    expect(r.results[0]?.score).toBeCloseTo(0.764, 3);
  });

  it("librarySimilar returns the ygmf_Remix neighbour list (centered ~0.3)", async () => {
    const r = await librarySimilar("ygmf_Remix.wav");
    expect(r.results).toHaveLength(6);
    expect(r.results[0]?.title).toBe("Girl Like Me");
    expect(r.results[0]?.score).toBeCloseTo(0.369, 3);
    expect(r.results[0]?.meta).toBe("centered · cos");
  });

  it("libraryStats returns 142 / sqlite-vec / €0.19 / 0 failed", async () => {
    const s = await libraryStats();
    expect(s).toEqual({
      indexed: 142,
      backend: "sqlite-vec",
      embedding_backend: "clap",
      embedding_dim: 512,
      clap_model_installed: true,
      clap_model_path: "~/.cache/vibemix/clap-onnx",
      clap_model_missing: [],
      library_freshness: {
        status: "fresh",
        stale: false,
        reason: "dev_fixture",
        age_days: 0,
        cache_path: "~/.cache/vibemix/library.pkl",
        source_path: "~/Music/rekordbox/collection.xml",
        source_age_days: 0,
        cache_mtime: null,
        source_mtime: null,
      },
      library_freshness_status: "fresh",
      library_stale: false,
      library_staleness_reason: "dev_fixture",
      library_age_days: 0,
      agent_backend: "codex",
      agent_ready: true,
      agent_status: "ready",
      agent_hint: "",
      library_setup_candidates: [],
      spent_eur: 0.19,
      failed: 0,
    });
  });

  it("libraryEmbedFolder returns false (no bridge → caller drives replay)", async () => {
    expect(await libraryEmbedFolder("~/Music", "cue_anchored")).toBe(false);
  });

  it("libraryModels returns the local model setup fallback", async () => {
    const r = await libraryModels();
    expect(r.required_ready).toBe(true);
    expect(r.all_ready).toBe(true);
    expect(r.models.map((m) => m.id)).toEqual(["clap", "moss-tts", "cue-detr"]);
    expect(r.models[0]?.installed).toBe(true);
    expect(r.models[1]?.required).toBe(true);
  });

  it("libraryModels install fallback keeps the install shape", async () => {
    const r = await libraryModels("clap");
    expect(r.install?.target).toBe("clap");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results[0]?.id).toBe("clap");
  });

  it("libraryModels required install fallback returns required assets", async () => {
    const r = await libraryModels("required");
    expect(r.install?.target).toBe("required");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results.map((item) => item.id)).toEqual([
      "clap",
      "moss-tts",
    ]);
  });

  it("libraryModels moss install fallback keeps the voice target shape", async () => {
    const r = await libraryModels("moss");
    expect(r.install?.target).toBe("moss");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results[0]?.id).toBe("moss-tts");
  });

  it("libraryModels cue install fallback keeps the cue target shape", async () => {
    const r = await libraryModels("cue");
    expect(r.install?.target).toBe("cue");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results[0]?.id).toBe("cue-detr");
  });

  it("libraryModels all install fallback returns both local model targets", async () => {
    const r = await libraryModels("all");
    expect(r.install?.target).toBe("all");
    expect(r.install?.ok).toBe(true);
    expect(r.install?.results.map((item) => item.id)).toEqual([
      "clap",
      "moss-tts",
      "cue-detr",
    ]);
  });

  it("exposes the captured embed log (8 entries, mixed ok/skip)", () => {
    expect(DEV_FALLBACK.embedLog).toHaveLength(8);
    expect(DEV_FALLBACK.embedLog.some(([st]) => st === "skip")).toBe(true);
    expect(DEV_FALLBACK.embedLog.every(([st]) => st !== "err")).toBe(true);
  });

  it("libraryBuildSet returns the DEV_BUILD exported set (6 tracks, .xml export)", async () => {
    const r = await libraryBuildSet("warehouse opener", "peak_time");
    expect(r.tracks).toHaveLength(6);
    expect(r.count).toBe(6);
    expect(r.stop_reason).toBe("exported");
    expect(r.export_path).toMatch(/\.xml$/);
    // honest meta — no fabricated human title/artist on the flat-id rows.
    expect(r.tracks[0]?.meta).toMatch(/^track /);
  });

  it("libraryCueFolder returns the DEV_CUE export receipt", async () => {
    const r = await libraryCueFolder("~/Music", "rekordbox");
    expect(r.ok).toBe(true);
    expect(r.mode).toBe("export");
    expect(r.tracks_cued).toBe(8);
    expect(r.cues_total).toBe(42);
    expect(r.outputs.rekordbox).toMatch(/vibemix-cues\.xml$/);
  });

  it("libraryChat returns the DEV_CHAT conversational sample", async () => {
    const r = await libraryChat("what should I demo?");
    expect(r.reply.length).toBeGreaterThan(20);
    expect(r.tool_trace[0]?.name).toBe("search_vibe");
    expect(r.playlist).toBeNull();
    expect(r.stop_reason).toBe("model_done");
    expect(r.move_grades[0]?.label).toBe("LIT AFF");
    expect(r.move_grades[0]?.xp).toBe(100);
    expect(r.move_grades[0]?.level_up).toBe(true);
    expect(r.move_grades[0]?.level).toBe(2);
    expect(DEV_FALLBACK.chat.seen_track_ids).toContain("7f9f9052");
  });
});

describe("library entry markup", () => {
  it("does not first-paint the stale mock corpus denominator", () => {
    const html = readFileSync("library.html", "utf8");
    const indexedStat = html.match(
      /<div class="v" id="vmx-lib-stat-indexed">(?<body>.*?)<\/div>/s,
    );

    expect(indexedStat?.groups?.body).toBe("·");
    expect(html).not.toContain("/ 1547");
  });
});

describe("runtime response normalizers", () => {
  it("accepts the search DTO and rejects malformed rows", () => {
    expect(
      normalizeSearchResult({
        centered: true,
        corpus_size: 1,
        results: [
          { track_id: "t1", title: "Track", score: 0.8, meta: "folder:t1" },
        ],
      }),
    ).toEqual({
      centered: true,
      corpus_size: 1,
      results: [
        { track_id: "t1", title: "Track", score: 0.8, meta: "folder:t1" },
      ],
    });

    expect(() =>
      normalizeSearchResult({
        centered: true,
        corpus_size: 1,
        results: [{ track_id: "t1", title: "Track", score: "hot", meta: "x" }],
      }),
    ).toThrow(/library_search\.results\[0\]\.score/);
  });

  it("rejects malformed Viber chat tool traces before UI render", () => {
    expect(() =>
      normalizeChatResult({
        reply: "ok",
        tool_trace: [{ name: "search_vibe", arg: "dark", ok: "yes" }],
        playlist: null,
        export_path: null,
        seen_track_ids: [],
        iterations: 1,
        stop_reason: "model_done",
      }),
    ).toThrow(/library_chat\.tool_trace\[0\]\.ok/);
  });

  it("keeps Viber chat clarification prompts before UI render", () => {
    const chat = normalizeChatResult({
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
      iterations: 1,
      stop_reason: "clarification_needed",
      question: "Which room are we aiming at?",
      choices: ["headphones", "club"],
    });
    expect(chat.question).toBe("Which room are we aiming at?");
    expect(chat.choices).toEqual(["headphones", "club"]);
    expect(chat.move_grades).toEqual([]);
  });

  it("keeps Viber live reply verification receipts before UI render", () => {
    const chat = normalizeChatResult({
      reply:
        "I caught the live move. The useful note is the sound change right there.",
      tool_trace: [],
      playlist: null,
      export_path: null,
      seen_track_ids: [],
      move_grades: [],
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
    });

    expect(chat.live_verification?.ok).toBe(true);
    expect(chat.live_verification?.claim_policy).toBe("blocked");
    expect(chat.live_verification?.guard_applied).toBe(true);
    expect(chat.live_verification?.guard_violations).toEqual([
      "unsupported_live_outcome_claim",
    ]);
  });

  it("accepts the cue export receipt and rejects malformed output paths", () => {
    expect(
      normalizeCueResult({
        ok: true,
        mode: "export",
        tracks_cued: 2,
        cues_total: 12,
        skipped: 1,
        outputs: { rekordbox: "/tmp/cues.xml", m3u8: "/tmp/cues.m3u8" },
      }),
    ).toEqual({
      ok: true,
      mode: "export",
      tracks_cued: 2,
      cues_total: 12,
      skipped: 1,
      outputs: { rekordbox: "/tmp/cues.xml", m3u8: "/tmp/cues.m3u8" },
    });

    expect(() =>
      normalizeCueResult({
        ok: true,
        mode: "export",
        tracks_cued: 2,
        cues_total: 12,
        skipped: 1,
        outputs: { rekordbox: 12 },
      }),
    ).toThrow(/library_cue_folder\.outputs\.rekordbox/);
  });

  it("keeps supported live verdict verification receipts before UI render", () => {
    const chat = normalizeChatResult({
      reply: "Great transition, clean handoff.",
      tool_trace: [],
      playlist: null,
      export_path: null,
      seen_track_ids: [],
      move_grades: [],
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
    });

    expect(chat.live_verification?.claim_policy).toBe("supported_verdict");
    expect(chat.live_verification?.move_grades_allowed).toBe(true);
    expect(chat.live_verification?.move_grades_seen).toBe(1);
  });

  it("normalizes live deck context and drops non-deck frame noise", () => {
    const context = normalizeLiveContextPayload({
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
        "audio_window_map",
        "bad capability",
      ],
      deck: "A",
      audible: true,
      phase: "groove",
      bpm: 128,
      music: 0.9,
      mic: 0.4,
      deck_state: {
        A: {
          title: "Strobe",
          track_id: "t000",
          camelot: "8A",
          bpm: 128,
          confidence: 0.82,
          source: "rekordbox_xml",
          filepath: "/private/strobe.mp3",
        },
        B: { source: "/private/injected" },
        Z: { title: "Injected", confidence: 1, source: "rekordbox_xml" },
      },
      deck_mixer: {
        connected: true,
        xfader: 64.9,
        deck_confidence: 0.82,
        A: {
          vol: 110,
          eq_low: 2,
          eq_mid: 64,
          eq_hi: 127,
          filter: 64,
          play: true,
        },
        B: {
          vol: 72,
          eq_low: 64,
          eq_mid: 64,
          eq_hi: 64,
          filter: 92,
          play: false,
        },
        Z: { vol: 127 },
      },
      deck_source_status: {
        controller: "present",
        controller_connection: "connected",
        library: "present",
        library_tracks: "24",
        library_source: "rekordbox_xml",
        library_match: "ambiguous label",
        nowplaying: "blocked_non_deck_owner",
        nowplaying_owner: "com.apple.WebKit.GPU",
        nowplaying_title: "seen",
        audible_deck: "A",
        resolution: "blocked non deck nowplaying",
        second_deck_source: "suppressed requires independent source",
        screen_vision: "disabled",
        leak: "/Users/ozai/private",
      },
      deck_lanes_context:
        "deck_lanes_context[deck1=A identity=known route=dominant | deck2=B identity=unresolved route=muted lane_aliases=deck1:A,deck2:B rule=per_lane_identity_route_control_not_outcome]",
      deck_reference_context:
        "deck_reference_context[deck1=A identity=known route=dominant deck2=B identity=unresolved route=muted audio=P1_global_mix per_deck_audio=not_attached isolated_decks=false rule=deck1_deck2_reference_not_outcome]",
      deck_source_context:
        "deck_source_context[identity_state=MusicState.deck_state primary=nowplaying_controller_attribution_to_library_cache resolved=A unresolved=B sources=rekordbox_xml live_db=not_read event_xml=diagnostic_only second_deck=independent_source_required rule=unresolved_deck_is_not_transition_evidence]",
      deck_audio_context:
        "deck_audio_context[audio=audible source=global_mix isolated_decks=false routing=A_dominant B_muted support=single_deck_A rule=audio_heard_must_be_mapped_through_deck_context]",
      deck_audio_separation_context:
        "deck_audio_separation_context[requested_device=BlackHole_2ch capture_device=BlackHole_2ch input_channels=2 opened_channels=2 sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture deckA_audio=not_captured deckB_audio=not_captured per_deck_audio=not_attached isolated_decks=false upgrade_path=multi_channel_deck_pair_capture rule=separation_capability_not_outcome]",
      deck_audio_delta_context:
        "deck_audio_delta_context[source=deck_pair_capture window=latest_callback per_deck_delta=captured_feature_delta A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong rule=deck_audio_delta_not_causal_proof]",
      deck_audio_window_context:
        "deck_audio_window_context[source=deck_pair_capture timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 per_deck_audio=captured_window_features A_pre=active_rms_0.020_peak_0.100_flux_0.004 A_current=active_rms_0.040_peak_0.120_flux_0.009 A_delta=rms_rose_100pct_strong B_pre=active_rms_0.030_peak_0.110_flux_0.006 B_current=active_rms_0.020_peak_0.090_flux_0.004 B_delta=rms_fell_33pct_clear rule=deck_audio_window_not_causal_or_quality_verdict]",
      audio_part_context:
        "audio_part_context[surface=live_context P1=live_global_mix P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 per_deck_audio=not_attached duplicate_audio=same_master_not_deck_split rule=part_labels_not_outcome_verdict]",
      audio_delta: [
        "sub energy fell 50% (strong)",
        "",
        "low energy fell 50% (strong)",
      ],
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
            token: "A_low_cut_to_killed",
            age_s: 0.7,
            relation: "inside_P1",
          },
        ],
        future: { heard: false, span: "not_attached" },
        rule: "time_alignment_not_outcome_verdict",
      },
      live_evidence: {
        mix: [
          "deck_audio_support=single_deck_A",
          "transition_block=single_resolved_deck",
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
        ],
        midi: [
          { key: "A_low_cut_to_killed", t: 42.04 },
          { key: "", t: 99 },
          { key: "bad_t", t: Number.NaN },
        ],
        refs: [
          "midi:A_low_cut_to_killed@42.0",
          "mix:transition_block=single_resolved_deck",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
        ],
      },
      recent_moves: ["A_low: cut->killed", "", "B_play->ON"],
    });

    expect(context).toEqual({
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
      music: 0.9,
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
        deck_confidence: 0.82,
        A: {
          vol: 110,
          eq_low: 2,
          eq_mid: 64,
          eq_hi: 127,
          filter: 64,
          play: true,
        },
        B: {
          vol: 72,
          eq_low: 64,
          eq_mid: 64,
          eq_hi: 64,
          filter: 92,
          play: false,
        },
      },
      deck_source_status: {
        controller: "present",
        controller_connection: "connected",
        library: "present",
        library_tracks: "24",
        library_source: "rekordbox_xml",
        library_match: "ambiguous_label",
        nowplaying: "blocked_non_deck_owner",
        nowplaying_owner: "com.apple.webkit.gpu",
        nowplaying_title: "seen",
        audible_deck: "a",
        resolution: "blocked_non_deck_nowplaying",
        second_deck_source: "suppressed_requires_independent_source",
        screen_vision: "disabled",
      },
      deck_lanes_context:
        "deck_lanes_context[deck1=A identity=known route=dominant | deck2=B identity=unresolved route=muted lane_aliases=deck1:A,deck2:B rule=per_lane_identity_route_control_not_outcome]",
      deck_reference_context:
        "deck_reference_context[deck1=A identity=known route=dominant deck2=B identity=unresolved route=muted audio=P1_global_mix per_deck_audio=not_attached isolated_decks=false rule=deck1_deck2_reference_not_outcome]",
      deck_source_context:
        "deck_source_context[identity_state=MusicState.deck_state primary=nowplaying_controller_attribution_to_library_cache resolved=A unresolved=B sources=rekordbox_xml live_db=not_read event_xml=diagnostic_only second_deck=independent_source_required rule=unresolved_deck_is_not_transition_evidence]",
      deck_audio_context:
        "deck_audio_context[audio=audible source=global_mix isolated_decks=false routing=A_dominant B_muted support=single_deck_A rule=audio_heard_must_be_mapped_through_deck_context]",
      deck_audio_separation_context:
        "deck_audio_separation_context[requested_device=BlackHole_2ch capture_device=BlackHole_2ch input_channels=2 opened_channels=2 sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture deckA_audio=not_captured deckB_audio=not_captured per_deck_audio=not_attached isolated_decks=false upgrade_path=multi_channel_deck_pair_capture rule=separation_capability_not_outcome]",
      deck_audio_delta_context:
        "deck_audio_delta_context[source=deck_pair_capture window=latest_callback per_deck_delta=captured_feature_delta A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong rule=deck_audio_delta_not_causal_proof]",
      deck_audio_window_context:
        "deck_audio_window_context[source=deck_pair_capture timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 per_deck_audio=captured_window_features A_pre=active_rms_0.020_peak_0.100_flux_0.004 A_current=active_rms_0.040_peak_0.120_flux_0.009 A_delta=rms_rose_100pct_strong B_pre=active_rms_0.030_peak_0.110_flux_0.006 B_current=active_rms_0.020_peak_0.090_flux_0.004 B_delta=rms_fell_33pct_clear rule=deck_audio_window_not_causal_or_quality_verdict]",
      audio_part_context:
        "audio_part_context[surface=live_context P1=live_global_mix P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 per_deck_audio=not_attached duplicate_audio=same_master_not_deck_split rule=part_labels_not_outcome_verdict]",
      audio_delta: [
        "sub energy fell 50% (strong)",
        "low energy fell 50% (strong)",
      ],
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
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "deck_audio_support=two_deck_route",
          "second_deck_identity=unknown_or_suppressed",
          "deck_lanes=A_known_route_dominant+B_unknown_route_present",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
          "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "deck_route=A_dominant+B_present",
        ],
        midi: [{ key: "A_low_cut_to_killed", t: 42 }],
        refs: [
          "midi:A_low_cut_to_killed@42.0",
          "mix:transition_block=single_resolved_deck",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "mix:deck_audio_support=single_deck_A",
          "mix:deck_audio_support=two_deck_route",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_present",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
          "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "mix:deck_route=A_dominant+B_present",
        ],
      },
      recent_moves: ["A_low: cut->killed", "B_play->ON"],
    });
  });

  it("preserves explicit empty live deck payloads so stale identities can clear", () => {
    expect(
      normalizeLiveContextPayload({ deck: "none", deck_state: {} }),
    ).toEqual({
      deck: "none",
      deck_state: {},
    });
    expect(normalizeLiveContextPayload({ deck_mixer: {} })).toEqual({
      deck_mixer: {},
    });
  });

  it("drops malformed live audio window context", () => {
    expect(
      normalizeLiveContextPayload({
        audio_window_context: "deckA_audio=totally_a_stem",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        audio_window_context:
          "audio_window_context[P1=master_global_mix deckA_audio=attached deckB_audio=stem isolated_decks=true]",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        audio_window_context:
          "audio_window_context[P1=master_global_mix deckA_audio=not_attached deckB_audio=not_attached]",
      }),
    ).toBeNull();
  });

  it("drops malformed live deck context maps", () => {
    expect(
      normalizeLiveContextPayload({
        deck_reference_context:
          "deck_reference_context[deck1=A deck2=B audio=P1_global_mix isolated_decks=true]",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        deck_lanes_context:
          "deck_lanes_context[deck1=A deck2=B rule=per_lane_identity_route_control_not_outcome]",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        deck_audio_context:
          "deck_audio_context[source=deckA isolated_decks=true rule=audio_heard_must_be_mapped_through_deck_context]",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        deck_audio_separation_context:
          "deck_audio_separation_context[current_capture=P1_global_mix deckA_audio=attached deckB_audio=stem per_deck_audio=attached rule=separation_capability_not_outcome]",
      }),
    ).toBeNull();
    expect(
      normalizeLiveContextPayload({
        deck_source_context:
          "deck_source_context[identity_state=MusicState.deck_state second_deck=inferred rule=unresolved_deck_is_transition_evidence]",
      }),
    ).toBeNull();
  });

  it("accepts configured deck-pair capture separation context", () => {
    const context = normalizeLiveContextPayload({
      deck_audio_separation_context:
        "deck_audio_separation_context[requested_device=BlackHole_16ch capture_device=BlackHole_16ch input_channels=16 opened_channels=4 sample_rate=48000 device_capacity=multichannel_available mode=deck_pair_capture_configured master_channels=0,1,2,3 current_capture=P1_global_mix_plus_deck_pairs gemini_audio=mono_downmix_of_master_capture deckA_audio=captured deckB_audio=captured per_deck_audio=captured_not_attached isolated_decks=runtime_capture_available deck_pairs=A:0,1+B:2,3 upgrade_path=attach_deck_pair_audio_parts_when_needed rule=separation_capability_not_outcome]",
    });

    expect(context?.deck_audio_separation_context).toContain(
      "mode=deck_pair_capture_configured",
    );
    expect(context?.deck_audio_separation_context).toContain(
      "deckA_audio=captured",
    );
  });

  it("accepts deck-pair audio feature descriptors", () => {
    const context = normalizeLiveContextPayload({
      deck_audio_features_context:
        "deck_audio_features_context[source=deck_pair_capture window=latest_callback per_deck_audio=captured_features A_activity=active A_rms=0.020 A_peak=0.100 A_zcr=0.030 B_activity=silent B_rms=0.000 B_peak=0.000 B_zcr=0.000 rule=deck_audio_features_not_outcome_verdict]",
    });

    expect(context?.deck_audio_features_context).toContain(
      "A_activity=active",
    );
    expect(context?.deck_audio_features_context).toContain("B_rms=0.000");
  });

  it("accepts deck-pair audio delta descriptors", () => {
    const context = normalizeLiveContextPayload({
      deck_audio_delta_context:
        "deck_audio_delta_context[source=deck_pair_capture window=latest_callback per_deck_delta=captured_feature_delta A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong rule=deck_audio_delta_not_causal_proof]",
    });

    expect(context?.deck_audio_delta_context).toContain(
      "A_delta=rms_rose_100pct_strong",
    );
    expect(context?.deck_audio_delta_context).toContain(
      "rule=deck_audio_delta_not_causal_proof",
    );
  });

  it("accepts deck-pair pre/current audio window descriptors", () => {
    const context = normalizeLiveContextPayload({
      deck_audio_window_context:
        "deck_audio_window_context[source=deck_pair_capture timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 per_deck_audio=captured_window_features A_pre=active_rms_0.020_peak_0.100_flux_0.004 A_current=active_rms_0.040_peak_0.120_flux_0.009 A_delta=rms_rose_100pct_strong B_pre=active_rms_0.030_peak_0.110_flux_0.006 B_current=active_rms_0.020_peak_0.090_flux_0.004 B_delta=rms_fell_33pct_clear rule=deck_audio_window_not_causal_or_quality_verdict]",
    });

    expect(context?.deck_audio_window_context).toContain(
      "timeline=pre_action_current",
    );
    expect(context?.deck_audio_window_context).toContain(
      "A_current=active_rms_0.040",
    );
    expect(context?.deck_audio_window_context).toContain(
      "rule=deck_audio_window_not_causal_or_quality_verdict",
    );
  });

  it("accepts Gemini deck-pair audio part labels", () => {
    const context = normalizeLiveContextPayload({
      audio_part_context:
        "audio_part_context[surface=gemini_parts P1=live_global_mix P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 part_order=P1,P2,P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deckA_part=P2 P2=deckA_configured_capture P2_model_heard=true P2_audience_heard=false P2_span=-3.0..0.0 P2_deck_audio=deckA_configured_capture P2_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P3 P3=deckB_configured_capture P3_model_heard=true P3_audience_heard=false P3_span=-3.0..0.0 P3_deck_audio=deckB_configured_capture P3_rule=deck_pair_capture_reference_not_quality_verdict rule=part_labels_not_outcome_verdict]",
    });

    expect(context?.audio_part_context).toContain(
      "per_deck_audio=deck_pair_parts",
    );
    expect(context?.audio_part_context).toContain("deckA_part=P2");
    expect(context?.audio_part_context).toContain("part_order=P1,P2,P3");
    expect(context?.audio_part_context).toContain(
      "P3_rule=deck_pair_capture_reference_not_quality_verdict",
    );
  });

  it("keeps full audio part order when mic and lookahead shift deck parts", () => {
    const fullPartContext = [
      "audio_part_context[surface=gemini_parts",
      "audio_token_rate=32_per_second",
      "P1=live_global_mix",
      "P1_model_heard=true",
      "P1_runtime_observed=true",
      "P1_audience_heard=true",
      "P1_span=-6.0..0.0",
      "P1_tokens_est=192",
      "P1_deck_audio=global_mix_not_stems",
      "deck1=A",
      "deck2=B",
      "together_audio=P1",
      "part_order=P1,P2,P3,P4,P5",
      "per_deck_audio=deck_pair_parts",
      "duplicate_audio=separate_deck_pair_parts",
      "deckA_part=P4",
      "P4=deckA_configured_capture",
      "P4_model_heard=true",
      "P4_audience_heard=false",
      "P4_span=-3.0..0.0",
      "P4_tokens_est=96",
      "P4_deck_audio=deckA_configured_capture",
      "P4_rule=deck_pair_capture_reference_not_quality_verdict",
      "deckB_part=P5",
      "P5=deckB_configured_capture",
      "P5_model_heard=true",
      "P5_audience_heard=false",
      "P5_span=-3.0..0.0",
      "P5_tokens_est=96",
      "P5_deck_audio=deckB_configured_capture",
      "P5_rule=deck_pair_capture_reference_not_quality_verdict",
      "P2=user_mic",
      "P2_model_heard=true",
      "P2_role=user_speech",
      "P2_deck_audio=none",
      "P2_rule=not_deck_audio",
      "P3=source_file_lookahead",
      "P3_model_heard=true",
      "P3_audience_heard=false",
      "P3_span=0.0..+3.0",
      "P3_tokens_est=96",
      "P3_deck_audio=none",
      "P3_rule=forecast_only_not_current_live_evidence",
      "rule=part_labels_not_outcome_verdict]",
    ].join(" ");

    expect(fullPartContext.length).toBeGreaterThan(900);

    const context = normalizeLiveContextPayload({
      audio_part_context: fullPartContext,
    });

    expect(context?.audio_part_context).toContain("part_order=P1,P2,P3,P4,P5");
    expect(context?.audio_part_context).toContain("deckA_part=P4");
    expect(context?.audio_part_context).toContain("deckB_part=P5");
    expect(context?.audio_part_context).toContain("P3=source_file_lookahead");
    expect(context?.audio_part_context).toContain(
      "rule=part_labels_not_outcome_verdict",
    );
  });

  it("rejects incomplete or conflicting deck-pair audio part labels", () => {
    const base = [
      "audio_part_context[surface=gemini_parts",
      "P1=live_global_mix",
      "P1_model_heard=true",
      "P1_runtime_observed=true",
      "P1_audience_heard=true",
      "P1_deck_audio=global_mix_not_stems",
      "deck1=A",
      "deck2=B",
      "together_audio=P1",
      "per_deck_audio=deck_pair_parts",
      "duplicate_audio=separate_deck_pair_parts",
      "rule=part_labels_not_outcome_verdict]",
    ];
    const tail = base[base.length - 1];
    const missingDeckB = [
      ...base.slice(0, -1),
      "part_order=P1,P2",
      "deckA_part=P2",
      "P2=deckA_configured_capture",
      "P2_model_heard=true",
      "P2_audience_heard=false",
      "P2_deck_audio=deckA_configured_capture",
      "P2_rule=deck_pair_capture_reference_not_quality_verdict",
      tail,
    ].join(" ");
    const conflictingDeckLabel = [
      ...base.slice(0, -1),
      "part_order=P1,P2",
      "deckA_part=P2",
      "deckB_part=P2",
      "P2=deckA_configured_capture",
      "P2=deckB_configured_capture",
      "P2_model_heard=true",
      "P2_audience_heard=false",
      "P2_deck_audio=deckA_configured_capture",
      "P2_rule=deck_pair_capture_reference_not_quality_verdict",
      tail,
    ].join(" ");
    const roleConflict = [
      ...base.slice(0, -1),
      "part_order=P1,P2,P3",
      "deckA_part=P2",
      "P2=deckA_configured_capture",
      "P2_model_heard=true",
      "P2_audience_heard=false",
      "P2_deck_audio=deckA_configured_capture",
      "P2_rule=deck_pair_capture_reference_not_quality_verdict",
      "deckB_part=P3",
      "P3=deckB_configured_capture",
      "P3_model_heard=true",
      "P3_audience_heard=false",
      "P3_deck_audio=deckB_configured_capture",
      "P3_rule=deck_pair_capture_reference_not_quality_verdict",
      "P2=user_mic",
      "P2_deck_audio=none",
      "P2_rule=not_deck_audio",
      tail,
    ].join(" ");

    expect(
      normalizeLiveContextPayload({ audio_part_context: missingDeckB })
        ?.audio_part_context,
    ).toBeUndefined();
    expect(
      normalizeLiveContextPayload({ audio_part_context: conflictingDeckLabel })
        ?.audio_part_context,
    ).toBeUndefined();
    expect(
      normalizeLiveContextPayload({ audio_part_context: roleConflict })
        ?.audio_part_context,
    ).toBeUndefined();
  });

  it("accepts Deck A/B audio-window part labels", () => {
    const context = normalizeLiveContextPayload({
      audio_part_context:
        "audio_part_context[surface=gemini_parts P1=live_global_mix P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 part_order=P1,P2,P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deckA_part=P2 P2=deckA_configured_capture P2_model_heard=true P2_audience_heard=false P2_deck_audio=deckA_configured_capture P2_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P3 P3=deckB_configured_capture P3_model_heard=true P3_audience_heard=false P3_deck_audio=deckB_configured_capture P3_rule=deck_pair_capture_reference_not_quality_verdict rule=part_labels_not_outcome_verdict]",
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future together_audio=P1_global_mix decks_together=true deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context deck_audio_separation=deck_audio_separation_context deck_part_span=-3.0..0.0 deckA_activity=active deckB_activity=silent lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 rule=time_alignment_not_outcome_verdict move_anchor=none future_heard=false future=not_attached]",
      audio_window_map: {
        p1: "master_global_mix",
        p1_heard: true,
        timeline: "past_action_future",
        together_audio: "P1_global_mix",
        decks_together: true,
        deckA_audio: "P2",
        deckB_audio: "P3",
        per_deck_audio: "deck_pair_parts",
        duplicate_audio: "separate_deck_pair_parts",
        deck_separation: "deck_lanes_context",
        deck_audio_separation: "deck_audio_separation_context",
        deck_part_span_s: [-3, 0],
        deck_part_activity: { A: "active", B: "silent", C: "ignored" },
        lane_aliases: "deck1:A,deck2:B",
        pre_s: [-6, -1],
        current_s: [-1, 0],
        action_s: [-1, 0],
        move_anchors: [],
        future: { heard: false, span: "not_attached" },
        rule: "time_alignment_not_outcome_verdict",
      },
    });

    expect(context?.audio_part_context).toContain("deckA_part=P2");
    expect(context?.audio_window_context).toContain("deckA_audio=P2");
    expect(context?.audio_window_context).toContain(
      "per_deck_audio=deck_pair_parts",
    );
    expect(context?.audio_window_map?.deckA_audio).toBe("P2");
    expect(context?.audio_window_map?.deckB_audio).toBe("P3");
    expect(context?.audio_window_map?.per_deck_audio).toBe("deck_pair_parts");
    expect(context?.audio_window_map?.duplicate_audio).toBe(
      "separate_deck_pair_parts",
    );
    expect(context?.audio_window_map?.deck_audio_separation).toBe(
      "deck_audio_separation_context",
    );
    expect(context?.audio_window_map?.deck_part_span_s).toEqual([-3, 0]);
    expect(context?.audio_window_map?.deck_part_activity).toEqual({
      A: "active",
      B: "silent",
    });
  });

  it("rejects deck-pair audio windows without matching audio part labels", () => {
    const mismatchedWindow =
      "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future together_audio=P1_global_mix decks_together=true deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context deck_audio_separation=deck_audio_separation_context lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 rule=time_alignment_not_outcome_verdict move_anchor=none future_heard=false future=not_attached]";
    const context = normalizeLiveContextPayload({
      audio_window_context: mismatchedWindow,
      audio_window_map: {
        p1: "master_global_mix",
        p1_heard: true,
        timeline: "past_action_future",
        together_audio: "P1_global_mix",
        decks_together: true,
        deckA_audio: "P2",
        deckB_audio: "P3",
        per_deck_audio: "deck_pair_parts",
        duplicate_audio: "separate_deck_pair_parts",
        deck_separation: "deck_lanes_context",
        deck_audio_separation: "deck_audio_separation_context",
        lane_aliases: "deck1:A,deck2:B",
        pre_s: [-6, -1],
        current_s: [-1, 0],
        action_s: [-1, 0],
        move_anchors: [],
        future: { heard: false, span: "not_attached" },
        rule: "time_alignment_not_outcome_verdict",
      },
    });

    expect(context?.audio_window_context).toBeUndefined();
    expect(context?.audio_window_map).toBeUndefined();
  });

  it("rejects audio windows that disagree with audio part labels", () => {
    const context = normalizeLiveContextPayload({
      audio_part_context:
        "audio_part_context[surface=gemini_parts P1=live_global_mix P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 part_order=P1,P2,P3,P4,P5 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deckA_part=P4 P4=deckA_configured_capture P4_model_heard=true P4_audience_heard=false P4_deck_audio=deckA_configured_capture P4_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P5 P5=deckB_configured_capture P5_model_heard=true P5_audience_heard=false P5_deck_audio=deckB_configured_capture P5_rule=deck_pair_capture_reference_not_quality_verdict rule=part_labels_not_outcome_verdict]",
      audio_window_context:
        "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future together_audio=P1_global_mix decks_together=true deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context deck_audio_separation=deck_audio_separation_context lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 rule=time_alignment_not_outcome_verdict move_anchor=none future_heard=false future=not_attached]",
      audio_window_map: {
        p1: "master_global_mix",
        p1_heard: true,
        timeline: "past_action_future",
        together_audio: "P1_global_mix",
        decks_together: true,
        deckA_audio: "P2",
        deckB_audio: "P3",
        per_deck_audio: "deck_pair_parts",
        duplicate_audio: "separate_deck_pair_parts",
        deck_separation: "deck_lanes_context",
        deck_audio_separation: "deck_audio_separation_context",
        lane_aliases: "deck1:A,deck2:B",
        pre_s: [-6, -1],
        current_s: [-1, 0],
        action_s: [-1, 0],
        move_anchors: [],
        future: { heard: false, span: "not_attached" },
        rule: "time_alignment_not_outcome_verdict",
      },
    });

    expect(context?.audio_part_context).toContain("deckA_part=P4");
    expect(context?.audio_window_context).toBeUndefined();
    expect(context?.audio_window_map).toBeUndefined();
  });

  it("rejects colliding Deck A/B audio-window part labels", () => {
    const collidingWindow =
      "audio_window_context[P1=master_global_mix P1_heard=true timeline=past_action_future together_audio=P1_global_mix decks_together=true deckA_audio=P2 deckB_audio=P2 per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context deck_audio_separation=deck_audio_separation_context lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 rule=time_alignment_not_outcome_verdict move_anchor=none future_heard=false future=not_attached]";
    const baseMap = {
      p1: "master_global_mix",
      p1_heard: true,
      timeline: "past_action_future",
      together_audio: "P1_global_mix",
      decks_together: true,
      deckA_audio: "P2",
      deckB_audio: "P2",
      per_deck_audio: "deck_pair_parts",
      duplicate_audio: "separate_deck_pair_parts",
      deck_separation: "deck_lanes_context",
      deck_audio_separation: "deck_audio_separation_context",
      lane_aliases: "deck1:A,deck2:B",
      pre_s: [-6, -1],
      current_s: [-1, 0],
      action_s: [-1, 0],
      move_anchors: [],
      future: { heard: false, span: "not_attached" },
      rule: "time_alignment_not_outcome_verdict",
    };

    const context = normalizeLiveContextPayload({
      audio_window_context: collidingWindow,
      audio_window_map: baseMap,
    });

    expect(context?.audio_window_context).toBeUndefined();
    expect(context?.audio_window_map).toBeUndefined();
  });

  it("normalizes recent move labels from session snapshots", () => {
    const moves = normalizeLiveMovePayload({
      type: "ipc.session.snapshot",
      payload: {
        midi_events: [
          {
            control: "A_low: cut->killed",
            value: null,
            ts: "2026-05-29T00:00:00Z",
          },
          {
            control: "xfader->center",
            value: null,
            ts: "2026-05-29T00:00:01Z",
          },
          { control: "", value: null, ts: "2026-05-29T00:00:02Z" },
        ],
      },
    });

    expect(moves).toEqual(["A_low: cut->killed", "xfader->center"]);
  });

  it("prioritizes live evidence safety tokens under the normalizer cap", () => {
    const context = normalizeLiveContextPayload({
      live_evidence: {
        mix: [
          ...Array.from({ length: 8 }, (_item, index) => `noise_${index}=kept`),
          "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "transition_block=single_resolved_deck",
        ],
        refs: [
          ...Array.from(
            { length: 8 },
            (_item, index) => `mix:noise_${index}=kept`,
          ),
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
          "mix:transition_block=single_resolved_deck",
        ],
      },
    });

    expect(context?.live_evidence?.mix).toHaveLength(10);
    expect(context?.live_evidence?.mix).toContain(
      "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
    );
    expect(context?.live_evidence?.mix).toContain(
      "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
    );
    expect(context?.live_evidence?.mix).toContain(
      "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
    );
    expect(context?.live_evidence?.mix).toContain(
      "transition_block=single_resolved_deck",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:transition_block=single_resolved_deck",
    );
  });

  it("derives deck reference and source evidence from controller frames", () => {
    const context = normalizeLiveContextPayload({
      deck: "mix",
      audible: false,
      music: 0,
      deck_state: {},
      deck_mixer: {
        connected: true,
        xfader: 64,
        A: { vol: 127, eq_low: 79, eq_mid: 71, eq_hi: 77, filter: 64 },
        B: { vol: 127, eq_low: 70, eq_mid: 77, eq_hi: 76, filter: 64 },
      },
      live_evidence: {
        mix: ["deck_audio_support=two_deck_route"],
        refs: ["mix:deck_audio_support=two_deck_route"],
      },
    });

    expect(context?.live_evidence?.mix).toContain(
      "transition_block=no_resolved_decks",
    );
    expect(context?.live_evidence?.mix).toContain(
      "deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_dominant",
    );
    expect(context?.live_evidence?.mix).toContain(
      "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_dominant",
    );
    expect(context?.live_evidence?.refs).toContain(
      "mix:deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none",
    );
  });

  it("normalizes empty session snapshots as an empty move delta", () => {
    expect(
      normalizeLiveMovePayload({
        type: "ipc.session.snapshot",
        payload: { midi_events: [] },
      }),
    ).toEqual([]);
  });

  it("normalizes Viber move-grade receipts before UI render", () => {
    const chat = normalizeChatResult({
      reply: "That bridge is LIT AFF.",
      tool_trace: [],
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
      iterations: 1,
      stop_reason: "model_done",
    });
    expect(chat.move_grades[0]?.slug).toBe("lit_aff");
    expect(chat.move_grades[0]?.overdrive).toBe(true);
    expect(chat.move_grades[0]?.streak).toBe(4);
    expect(chat.move_grades[0]?.total_xp).toBe(288);
    expect(chat.move_grades[0]?.level).toBe(2);
    expect(chat.move_grades[0]?.level_xp).toBe(38);
    expect(chat.move_grades[0]?.next_level_xp).toBe(250);
    expect(chat.move_grades[0]?.level_up).toBe(true);
    expect(chat.move_grades[0]?.levels_gained).toBe(1);

    expect(() =>
      normalizeChatResult({
        reply: "bad",
        tool_trace: [],
        playlist: null,
        export_path: null,
        seen_track_ids: [],
        move_grades: [
          {
            candidate_id: "tr_bad",
            track_id: "t001",
            title: "Insane Click",
            slug: "too_hot",
            label: "TOO HOT",
            xp: 100,
            reason: "not a contract grade",
            overdrive: true,
          },
        ],
        iterations: 1,
        stop_reason: "model_done",
      }),
    ).toThrow(/library_chat\.move_grades\[0\]\.slug/);
  });

  it("normalizes build-set export paths and rejects bad export shape", () => {
    expect(
      normalizeBuildSetResult({
        name: "Warehouse",
        rationale: "grounded",
        stop_reason: "exported",
        tracks: [],
        count: 0,
        export_path: "/tmp/warehouse.xml",
      }).export_path,
    ).toBe("/tmp/warehouse.xml");

    expect(() =>
      normalizeBuildSetResult({
        name: "Warehouse",
        rationale: "grounded",
        stop_reason: "exported",
        tracks: [],
        count: 0,
        export_path: 42,
      }),
    ).toThrow(/library_build_set\.export_path/);
  });

  it("keeps Viber clarification prompts on curate and build-set results", () => {
    const curate = normalizeCurateResult({
      name: "Warehouse",
      rationale: "Which direction should I take this?",
      stop_reason: "clarification_needed",
      question: "Which direction should I take this?",
      choices: ["Hypnotic", "Peak-time"],
      tracks: [],
      count: 0,
    });
    expect(curate.question).toBe("Which direction should I take this?");
    expect(curate.choices).toEqual(["Hypnotic", "Peak-time"]);

    const build = normalizeBuildSetResult({
      name: "Warehouse",
      rationale: "Which direction should I take this?",
      stop_reason: "clarification_needed",
      question: "Which direction should I take this?",
      choices: ["Hypnotic", "Peak-time"],
      tracks: [],
      count: 0,
      export_path: null,
    });
    expect(build.question).toBe("Which direction should I take this?");
    expect(build.choices).toEqual(["Hypnotic", "Peak-time"]);
  });

  it("normalizes stats and models, including install result files", () => {
    expect(
      normalizeStats({
        indexed: 12,
        backend: "sqlite-vec",
        library_freshness: {
          status: "stale",
          stale: true,
          reason: "source_newer_than_cache",
          age_days: 2,
          cache_path: "/cache/library.pkl",
          source_path: "/Music/collection.xml",
          source_age_days: 0,
          cache_mtime: 1,
          source_mtime: 2,
        },
        library_freshness_status: "stale",
        library_stale: true,
        library_staleness_reason: "source_newer_than_cache",
        library_age_days: 2,
        library_setup_candidates: [
          {
            kind: "music_folder",
            path: "/Music/PSYMIND",
            confidence: "high",
            reason: "bounded scan saw 42 supported audio files",
            audio_files_seen: 42,
            import_action: {
              type: "ipc.library.import",
              payload: { path: "/Music/PSYMIND", schema_version: "1" },
            },
          },
          {
            kind: "music_folder",
            path: "/Music/unsafe",
            import_action: {
              type: "ipc.settings.set",
              payload: { path: "/Music/unsafe", schema_version: "1" },
            },
          },
        ],
        spent_eur: 0.25,
        failed: 0,
        clap_model_missing: [],
      }),
    ).toMatchObject({
      indexed: 12,
      library_freshness_status: "stale",
      library_stale: true,
      library_staleness_reason: "source_newer_than_cache",
      library_age_days: 2,
      library_setup_candidates: [
        {
          kind: "music_folder",
          path: "/Music/PSYMIND",
          confidence: "high",
          reason: "bounded scan saw 42 supported audio files",
          audio_files_seen: 42,
          import_action: {
            type: "ipc.library.import",
            payload: { path: "/Music/PSYMIND", schema_version: "1" },
          },
        },
        {
          kind: "music_folder",
          path: "/Music/unsafe",
        },
      ],
      library_freshness: {
        status: "stale",
        stale: true,
        source_path: "/Music/collection.xml",
      },
    });

    const models = normalizeModelsResult({
      required_ready: true,
      all_ready: true,
      models: [
        {
          id: "clap",
          label: "CLAP",
          role: "embeddings",
          required: true,
          env: "VIBEMIX_CLAP_ONNX_DIR",
          installed: true,
          path: "/models/clap",
          missing: [],
          mismatched: [],
        },
      ],
      install: {
        target: "required",
        ok: true,
        results: [
          {
            id: "clap",
            installed: true,
            path: "/models/clap",
            files: [
              {
                rel_path: "onnx/audio_model.onnx",
                path: "/models/clap/onnx/audio_model.onnx",
                status: "skipped",
                size: 1,
                sha256: "sha",
                url: "https://example.test/audio_model.onnx",
              },
            ],
            errors: [],
          },
        ],
      },
    });
    expect(models.install?.results[0]?.files[0]?.rel_path).toBe(
      "onnx/audio_model.onnx",
    );

    expect(() =>
      normalizeModelsResult({
        required_ready: true,
        all_ready: true,
        models: {},
      }),
    ).toThrow(/library_models\.models/);
  });

  it("rejects malformed event progress instead of passing it to renderers", () => {
    expect(
      normalizeEmbedProgress({
        n: 1,
        total: 2,
        status: "ok",
        filename: "track.wav",
        cost_eur: 0.01,
      }).filename,
    ).toBe("track.wav");

    expect(() =>
      normalizeEmbedProgress({
        n: 1,
        total: 2,
        status: "done",
        filename: "track.wav",
        cost_eur: 0.01,
      }),
    ).toThrow(/unknown status/);
  });

  it("drops malformed live Tauri events without wedging valid progress", async () => {
    vi.resetModules();
    const handlers = new Map<string, (event: { payload: unknown }) => void>();
    const unlisten = vi.fn();
    const listen = vi.fn(async (eventName: string, handler: unknown) => {
      handlers.set(eventName, handler as (event: { payload: unknown }) => void);
      return unlisten;
    });
    vi.doMock("@tauri-apps/api/event", () => ({ listen }));
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const api = await import("./api.js");

    const progress = vi.fn();
    const done = vi.fn();
    const model = vi.fn();
    expect(await api.onEmbedProgress(progress)).toBe(unlisten);
    expect(await api.onEmbedDone(done)).toBe(unlisten);
    expect(await api.onModelProgress(model)).toBe(unlisten);

    handlers.get("library://embed-progress")?.({
      payload: {
        n: 1,
        total: 2,
        status: "ok",
        filename: "track.wav",
        cost_eur: 0.01,
      },
    });
    handlers.get("library://embed-progress")?.({
      payload: {
        n: 2,
        total: 2,
        status: "done",
        filename: "bad.wav",
        cost_eur: 0.01,
      },
    });
    handlers.get("library://embed-done")?.({
      payload: {
        embedded: 2,
        skipped: 0,
        failed: 0,
        total: 2,
        cost_eur: 0.02,
      },
    });
    handlers.get("library://embed-done")?.({
      payload: {
        embedded: "two",
        skipped: 0,
        failed: 0,
        total: 2,
        cost_eur: 0.02,
      },
    });
    handlers.get("library://model-progress")?.({
      payload: {
        target: "required",
        id: "clap",
        n: 1,
        total: 3,
        status: "downloaded",
        rel_path: "onnx/audio_model.onnx",
        downloaded: 12,
        size: 12,
      },
    });
    handlers.get("library://model-progress")?.({
      payload: {
        target: "later",
        id: "clap",
        n: 2,
        total: 3,
        status: "downloaded",
        rel_path: "onnx/audio_model.onnx",
        downloaded: 12,
        size: 12,
      },
    });

    expect(listen).toHaveBeenCalledTimes(3);
    expect(progress).toHaveBeenCalledTimes(1);
    expect(progress).toHaveBeenCalledWith({
      n: 1,
      total: 2,
      status: "ok",
      filename: "track.wav",
      cost_eur: 0.01,
    });
    expect(done).toHaveBeenCalledTimes(1);
    expect(done.mock.calls[0]?.[0].embedded).toBe(2);
    expect(model).toHaveBeenCalledTimes(1);
    expect(model.mock.calls[0]?.[0].target).toBe("required");
    expect(warn).toHaveBeenCalledTimes(3);
  });

  it("live move listener forwards empty snapshots for caller-side recency aging", async () => {
    vi.resetModules();
    const handlers = new Map<string, (event: { payload: unknown }) => void>();
    const unlisten = vi.fn();
    const listen = vi.fn(async (eventName: string, handler: unknown) => {
      handlers.set(eventName, handler as (event: { payload: unknown }) => void);
      return unlisten;
    });
    vi.doMock("@tauri-apps/api/event", () => ({ listen }));
    const api = await import("./api.js");

    const moves = vi.fn();
    expect(await api.onLiveMoveContext(moves)).toBe(unlisten);
    handlers.get("ipc-session-snapshot")?.({
      payload: {
        type: "ipc.session.snapshot",
        payload: { midi_events: [{ control: "A_low: cut->killed" }] },
      },
    });
    handlers.get("ipc-session-snapshot")?.({
      payload: {
        type: "ipc.session.snapshot",
        payload: { midi_events: [] },
      },
    });

    expect(moves).toHaveBeenNthCalledWith(1, ["A_low: cut->killed"]);
    expect(moves).toHaveBeenNthCalledWith(2, []);
  });
});
