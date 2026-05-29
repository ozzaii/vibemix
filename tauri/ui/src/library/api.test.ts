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
  libraryEmbedFolder,
  libraryModels,
  librarySearch,
  librarySimilar,
  libraryStats,
  normalizeBuildSetResult,
  normalizeChatResult,
  normalizeCurateResult,
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
      agent_backend: "codex",
      agent_ready: true,
      agent_status: "ready",
      agent_hint: "",
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
    expect(r.models.map((m) => m.id)).toEqual(["clap", "cue-detr"]);
    expect(r.models[0]?.installed).toBe(true);
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
    expect(r.install?.results.map((item) => item.id)).toEqual(["clap"]);
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
      reply: "I'll hold the transition verdict until live deck proof is stronger.",
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
        reply: "I'll hold the transition verdict until live deck proof is stronger.",
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

  it("normalizes live deck context and drops non-deck frame noise", () => {
    const context = normalizeLiveContextPayload({
      live_context_schema_version: 2,
      live_context_capabilities: [
        "deck_state",
        "deck_source_status",
        "audio_part_context",
        "deck_audio_separation_context",
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
        nowplaying: "blocked_non_deck_owner",
        nowplaying_owner: "com.apple.WebKit.GPU",
        resolution: "blocked non deck nowplaying",
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
        nowplaying: "blocked_non_deck_owner",
        nowplaying_owner: "com.apple.webkit.gpu",
        resolution: "blocked_non_deck_nowplaying",
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
          "second_deck_identity=unknown_or_suppressed",
          "deck_lanes=A_known_route_dominant+B_unknown_route_present",
          "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
          "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
        ],
        midi: [{ key: "A_low_cut_to_killed", t: 42 }],
        refs: [
          "midi:A_low_cut_to_killed@42.0",
          "mix:transition_block=single_resolved_deck",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
          "mix:deck_audio_support=single_deck_A",
          "mix:second_deck_identity=unknown_or_suppressed",
          "mix:deck_lanes=A_known_route_dominant+B_unknown_route_present",
          "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_present",
          "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
        ],
      },
      recent_moves: ["A_low: cut->killed", "B_play->ON"],
    });
  });

  it("preserves explicit empty live deck payloads so stale identities can clear", () => {
    expect(normalizeLiveContextPayload({ deck: "none", deck_state: {} })).toEqual({
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

    expect(context?.live_evidence?.mix).toHaveLength(8);
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
        spent_eur: 0.25,
        failed: 0,
        clap_model_missing: [],
      }).indexed,
    ).toBe(12);

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
