# vibemix — The Universal Gobble (DJ-ecosystem interop) — 2026-05-30

> Workflow `wn03qxubv` (16 agents, 1.57M tokens). Gobbled 8 DJ ecosystems'
> data + audio output + live protocols, mapped vibemix's own deep-calc→simple-
> answer collapse, and grounded the universal interop seam. **Adversarial
> verification verdict: VERIFIED — honest, zero fabrications.** Companion §8 of
> the KNOWBOOK. The two trivial nits the verifier caught are folded below.

## The general principle (Kaan's thesis, grounded)

Every DJ ecosystem (rekordbox/Serato/Traktor/Engine/VirtualDJ/djay/Mixxx) **already
did the deep calculation** — beatgrid, key, cues, phrase — and it sits in a file or
on the network. The DJ never has to see it. **vibemix's whole job is the membrane
that swallows that deep calc and hands back ONE lived sentence:** *"that blend
locked"*, *"go to 9A next"*, *"one more cited demo to Master."* The universal
currency is **`TrackEntry`** (one narrow dataclass) and the universal seam is the
**`LibrarySource` Protocol** — every ecosystem collapses to the same shape, so
**writing a parser is the ONLY new work** and the whole downstream stack (CLAP
search, Viber curate, the pill, the Judge, the Earned Wall) lights up for free.
Honesty rule (Invariant #3): collapse REAL deep data into simple answers, never
fabricate the simplicity — when the data is absent, abstain in plain language.

## The interop seam — BUILT (verified exact, file:line)

| Piece | Location | Role |
|---|---|---|
| **`TrackEntry`** universal currency | `library/rekordbox.py:108-141` | bpm/key/camelot/cues/beatgrid + `CuePoint`(:73) + `TempoNode`(:91, battito beat-in-bar phase) |
| **`LibrarySource`** Protocol | `library/sources/base.py:34-69` | `@runtime_checkable`: `name`/`detect()`/`default_paths()`/`iter_tracks()→Iterable[TrackEntry]` |
| **`RekordboxSource`** (the reference) | `library/sources/rekordbox.py:47-127` | the one shipped parser; every new one mirrors it; XML-only, never opens SQLCipher |
| **`ingest_source()`** orchestrator | `library/ingest.py:709` | detect→iter→embed→store; **already takes `embedder` as a param** (only the CLI hard-instantiates `ClapEngine()` at `__main__.py:5349`) |
| **Capture seam** | `audio/deck_capture.py:81-144` + `deck_audio_routing_from_env()` :320-398 | `DeckAudioRouting{deck_channels: dict[label→channel-idx]}`; **rekordbox-XML-only** auto-hint at **:332** (the gap for every other ecosystem) |
| **Vision fallback** | `state/deck_vision.py:116` `DeckVisionReader` | universal cross-app on-screen read (Serato/djay/Traktor/Engine), eval-gated, zero per-app parsers |

## The ranked gobble (reach × parse-ease × Judge-feed)

| # | Ecosystem | Parser effort | Reach | Judge feed | First move |
|---|-----------|---------------|-------|------------|------------|
| 1 | **Serato DJ Pro** | M (binary TLV + GEOB ID3) | **largest** | master-only + History track-change tail | `SeratoSource`: parse `_Serato_/database V2` TLV + per-file GEOB (Markers2/Beatgrid/Autotags). Ref Holzhaus/serato-tags |
| 2 | **rekordbox Pro DJ Link** | L (UDP receiver) | club-standard (hw-gated) | **BEST realtime**: per-deck id+beat+on-air, NO audio split | passive virtual-CDJ receiver (UDP 50000/50001/50002, beat-link spec) → **deck-state seam**. ⚠ laptop-only rekordbox = 0 packets (Kaan's FLX4 rig → use per-deck AUDIO instead) |
| 3 | **VirtualDJ** | **S** (stdlib XML) | 150M+ base | master; PRO OSC = per-deck BPM+beatgrid | `VirtualDJSource`: parse `database.xml` (mirrors rekordbox path). PRO-only OSC `/vdj/subscribe/deck/N/...` |
| 4 | **Traktor Pro 3/4** | **S** (clean .nml) | big-three | audio-only (Inv #3 path) | `TraktorSource`: `collection.nml` `<ENTRY>`/`<CUE_V2>` — the cleanest parse of the big three |
| 5 | **Engine DJ (Denon)** | L (SQLite easy, StagelinQ heavy) | #2 standalone | StagelinQ per-deck track/BPM/beat/crossfader live | `EngineSource`: read-only ATTACH `m.db`/`p.db` (plain SQLite, no SQLCipher) + StagelinQ client (UDP 51337) |
| 6 | **Mixxx** | **S** (open SQLite+proto) | OSS, star-magnet | master; **External Mixer Mode = real per-deck stems** | `MixxxSource`: `mixxxdb.sqlite` + `beats.proto`/`keys.proto` BLOBs. GPL-legal, zero reverse-engineering |

> djay Pro (Algoriddim) = master-only + OneLibrary export + Ableton-Link tempo-only;
> software-mixer-centric, no per-deck buses.

## Capture matrix (the Judge-feed reality per rig)

- **Master loopback works TODAY for all 7** via BlackHole — the Judge's harmonic
  signal (metadata-grounded) + bass off the master spectrum.
- **Per-deck AUDIO** (the "tight blend" verdict): rekordbox (auto-hint shipped),
  Traktor/VDJ/Mixxx external-mixer mode (manual channel-map, no auto-reader yet).
- **Per-deck METADATA without audio** (the shortcut): Pro DJ Link (rekordbox CDJ),
  StagelinQ (Denon), VDJ-OSC (pro) — resolve deck identity + beat phase off the
  wire, upgrading `live_claim_policy` blocked→`supported_verdict` with no audio split.
- **`live_claim_policy()` at `deck_context.py:2037`** returns **6 strings**
  (blocked / watch_not_claim / candidate_not_verdict / supported_verdict /
  requires_more_evidence / move_effect_not_verdict) → **collapse to 3 user states
  (GREEN verdict ready / YELLOW watching / RED can't grade — fix X).**

## The "Universal Gobble" milestone (separate from the live-Judge work)

N parser-writing jobs against ONE Protocol + one capture seam, **open/closed
(zero `ingest.py`/`deck_capture.py` core edits)**. Build order (collision-safe —
each a NEW `library/sources/<eco>.py` island):
1. **Guard collisions** — concurrent sessions own `coach.py` credit, pill, library/, learn/. Gobble in NEW files only, surgical `git add`.
2. **Ingest first-run wizard** — bundle ffmpeg, auto-download Xenova CLAP on first-ingest failure, collection file-picker. Removes cold-start friction BEFORE sources pour in.
3. **`VirtualDJSource`** (S, biggest reach) — first parser, proves the seam.
4. **`TraktorSource` + `MixxxSource`** in parallel (both S, disjoint files).
5. **Multi-source blend/dedup + injectable embedder** (the seam-audit gaps) — touches `ingest.py`/`__main__.py` glue → SOLO + sequential.
6. **`SeratoSource`** (M, largest base) — rides the settled seam.
7. **`EngineSource`** ingest half (read-only ATTACH).
8. **Live-protocol capture lane** — Pro DJ Link receiver, then StagelinQ → feed the **deck-state seam**, NOT the Judge engine, NOT `coach.py`.
9. **Judge UX collapse** (frontend) — 6 policy strings → 3 states + score breakdown.

**Explicitly OUT:** the live-Judge engine (shipped) and any `coach.py` credit-path
change (concurrent-session-owned).

## Verifier nits (folded)
- `TrackEntry` is at `rekordbox.py:108-141` (the synth said 107 — off by one).
- The "injectable embedder hook" is **narrower than framed**: `ingest_source()`
  already takes `embedder`; only the CLI call site (`__main__.py:5349`) hard-
  instantiates `ClapEngine()`. The fix is a one-line CLI param, not a seam rebuild.

---
*Source: workflow `wf_484b9cfe-e94` / run `wn03qxubv`. Companion §8 of the KNOWBOOK.*
