# E-followup-1 — Citation Linter (Cross-Mode Design)

> Follow-up to Bucket E ([E-debrief-pedagogy.md §AI-specific grounding strategy](./E-debrief-pedagogy.md)). Anchors to `cohost_v4.py` (the canonical baseline) — specifically the evidence sources `EventDetector`, `AICoach.evidence_line`, `VoiceRecorder.log_event`, and `MusicState`.
>
> **Thesis recap:** vibemix's anti-slop product principle ([project_anti_slop_grounded_gemini_thesis]) says the model is allowed to talk only when it can point at a real event. The mandatory citation linter is the deterministic post-processor that *enforces* the principle — Gemini emits sentences tagged with citation tokens, a regex pass strips anything unsourced before it reaches the user. This document specifies the grammar, the regex enforcement, the per-mode prompt templates, the latency budget, the telemetry shape, and the phasing.

---

## TL;DR (5 bullets)

1. **One grammar, four sources, two timestamp dialects.** `[source:key@ts]` with sources `ev / aud / midi / track / screen / mix / tend` and timestamps as session-relative `mm:ss` or absolute `bar:N`. EBNF locks the shape so a single regex pass covers all four product modes.
2. **Stripping unit is sentence-level for debrief, response-level for live.** Live mode reactions are 1-2 sentences total — partial stripping leaves you with a half-thought. If the live response has zero valid citations, drop the whole reply and fall back to a pre-canned ack (Bucket A pattern).
3. **The linter is an O(1) lookup against an in-memory evidence registry, NOT a file scan.** Every event emitted by `EventDetector` registers a `(source, key, t_session, t_wall)` tuple in a `CitationLinter` instance. The validator hashes the cited token and checks presence + timestamp tolerance (±1.0s for live, ±2.0s for debrief).
4. **Live-mode linter cost is <3ms per response.** Negligible relative to the 800-2000ms voice-to-voice budget ([A-latency.md]). Debrief mode pays ~30-80ms on a 4-chapter response — also negligible relative to a 15s Gemini call.
5. **Phasing: linter ships v1.1 (live mode only, strict), expands to all modes in v2.0.** v1.0 ships with prompt-only grounding to clear the schedule pressure. The linter lands in the first dot release once the v4 prompt has shown the production-loss rate of unsourced sentences (telemetry-driven decision).

---

## 1. Citation Grammar

### Token shape

```
[<source>:<key>@<timestamp>]
```

Compact, single bracket, machine-parseable, human-readable. The token is allowed inline anywhere in a sentence — `"Your filter sweep at [midi:filter_cc23@04:22] was too long."` reads naturally. Multi-citation uses semicolons inside one bracket: `[ev:DROP@04:22; aud:peak_rms=0.91; midi:filter_open@04:21]` — single open/close pair, semicolon-separated claims.

### Source tags (exhaustive)

| Tag | Meaning | Source of truth | Key shape |
|---|---|---|---|
| `ev` | Typed event from `events.jsonl` | `VoiceRecorder.log_event` rows | One of `TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL` (`Event.type` in `cohost_v4.py:1167`). Optionally followed by `=value` for value-bearing events. |
| `aud` | Audio feature (snapshot) | `AudioBuffer.snapshot_features` + `MusicState.bands/rms/bpm` | `peak_rms / sub_share / hi_share / mid_share / low_share / bpm / spectral_flux / silence_dur` with optional `=value` |
| `midi` | Controller move | `ControllerState` recent_moves | `<deck>_<control>:<value>` e.g. `deckA_filter:23` or named: `xfader_to_B`, `lows_killed_deckA`, `deck_play→on` |
| `track` | Track-level metadata | `TrackInfo` + Rekordbox priors (v2) | `"<title>"` plus optional sub-fields `bpm=128`, `key=8A`, `energy=7` |
| `screen` | Visual signal from screen capture | `ScreenBuffer` + djay-Pro state extraction | `deckA_loaded / deckB_loaded / cue_visible / loop_active` |
| `mix` | Derived multi-source claim | Computed from ≥2 sources at linter time | `transition_smoothness=0.7`, `harmonic_distance=0.2`, `phrase_aligned=true` — must internally cite its inputs |
| `tend` | Long-term DJ tendency | `profile.json.tendencies[]` ([E-debrief-pedagogy.md §profile architecture]) | `tendency_idx=3` referencing a profile tendency line |

### Timestamp formats

Three valid dialects, picked per source:

1. **Session-relative `@mm:ss` or `@mm:ss.sss`** — the default. Anchored to `VoiceRecorder.start_time`. Used everywhere except wall-clock-bound facts.
2. **Bar-position `@bar:<N>`** — for phrasing claims. Resolved via `MusicState.bpm` + session-relative start. Used in debrief Pro-level critique ("you mixed in 8 bars early at [aud:phrase_boundary@bar:32]").
3. **Omitted** — only valid for `track:` (atemporal track facts) and `tend:` (atemporal tendency facts). Token still has the `@` separator dropped: `[track:"Boys Noize – Mvinline" bpm=128 key=8A]`.

Multi-citation timestamps must agree to within the tolerance band (±1.0s live, ±2.0s debrief). Disagreement → linter flags inconsistent claim, strips.

### EBNF

```ebnf
citation_block  = "[" claim { ";" SP claim } "]" ;
claim           = source ":" key [ "@" timestamp ] [ SP "=" SP value ] ;
source          = "ev" | "aud" | "midi" | "track" | "screen" | "mix" | "tend" ;
key             = event_key | feature_key | midi_key | track_key
                | screen_key | derived_key | tendency_key ;

event_key       = "TRACK_CHANGE" | "PHASE" | "LAYER_ARRIVAL"
                | "MIX_MOVE" | "HEARTBEAT" | "KAAN_SPOKE" | "MANUAL" ;
feature_key     = "peak_rms" | "sub_share" | "low_share" | "mid_share"
                | "hi_share" | "bpm" | "spectral_flux" | "silence_dur"
                | "phrase_boundary" ;
midi_key        = deck "_" control ":" digit { digit }
                | "xfader_to_" ("A" | "B" | "center")
                | "lows_killed_" deck | "mids_killed_" deck | "hi_killed_" deck
                | "deck_play→" ("on" | "off") ;
track_key       = QUOTED_STR ;                     /* "<title>" */
screen_key      = "deckA_loaded" | "deckB_loaded" | "cue_visible"
                | "loop_active" | "beatgrid_visible" ;
derived_key     = "transition_smoothness" | "harmonic_distance"
                | "phrase_aligned" | "energy_delta" ;
tendency_key    = "tendency_idx" "=" digit { digit } ;

deck            = "deckA" | "deckB" | "deckC" | "deckD" ;
control         = "filter" | "lo_eq" | "mid_eq" | "hi_eq"
                | "vol" | "play" | "cue" | "fx_on" ;

timestamp       = mmss | bar_pos ;
mmss            = digit { digit } ":" digit digit [ "." digit { digit } ] ;
bar_pos         = "bar:" digit { digit } ;

value           = NUMBER | QUOTED_STR | "true" | "false" ;
SP              = " " ;
```

This grammar is intentionally restrictive — every key must be enumerable. Any token the linter cannot parse against this grammar is treated as invalid and triggers stripping.

---

## 2. Regex Enforcement Rules

### Stripping unit

**Sentence-level for long-form, response-level for live.** The decision rests on what a stripped fragment leaves behind:

- **Debrief (4 chapters, 600-1000 words)** — stripping a single unsourced sentence inside "What to drill" leaves the rest of the chapter intact and still useful. Sentence is the right grain.
- **Live mode (1-2 sentences, ~30-80 words total)** — stripping one sentence from a 2-sentence response leaves a fragment ("Yeah."). The result is *worse* than playing the original. Response-level enforcement is correct: if the whole response lacks ≥1 valid citation, drop the response entirely and fire a pre-canned ack instead ([A-latency.md ack bank]).
- **Library suggestion (3-5 track recs)** — per-recommendation grain. Each "I recommend X because Y" block stands or falls on its own citations.
- **Genre-aware feedback** — sentence-level when nested inside a debrief; response-level when fired live.

### The regex

`re` stdlib is sufficient — no need for the third-party `regex` package; we don't need variable-length lookbehinds, recursive patterns, or Unicode-class-walking. Sticking with stdlib keeps `requirements.txt` slim ([project_one_click_install_hard_req]).

```python
import re

# Single-citation block — matches one [src:key@ts] or one [src:key@ts; src:key@ts; ...]
CITATION_RX = re.compile(
    r"""
    \[                                  # opening bracket
    (?P<claims>                         # one or more claims, semicolon-separated
        (?:ev|aud|midi|track|screen|mix|tend)    # source
        :
        [^@\];]+                        # key (no @ ] ; allowed)
        (?:@[^;\]]+)?                   # optional @timestamp
        (?:                              # repeat for semicolon-separated extras
            \s*;\s*
            (?:ev|aud|midi|track|screen|mix|tend)
            :
            [^@\];]+
            (?:@[^;\]]+)?
        )*
    )
    \]                                  # closing bracket
    """,
    re.VERBOSE,
)

# Sentence splitter — naive but robust enough for Gemini's prose.
# Splits on . ! ? followed by whitespace+capital or EOL.
SENTENCE_RX = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'\[])")
```

### Stripping algorithm

```python
from dataclasses import dataclass, field
from typing import Iterable
import re, time, math

@dataclass(frozen=True)
class Evidence:
    source: str          # ev / aud / midi / track / screen / mix / tend
    key: str             # e.g. "TRACK_CHANGE" or "peak_rms" or "deckA_filter:23"
    t_session: float     # seconds since session start
    extras: dict = field(default_factory=dict)

@dataclass
class ValidatedText:
    accepted: str                            # output after stripping
    stripped_sentences: list[tuple[str, str]]  # (sentence, reason)
    valid_citations: int
    invalid_citations: int

@dataclass
class Citation:
    source: str
    key: str
    t_session: float | None  # None for atemporal sources

class CitationLinter:
    """O(1) lookup linter. Caller registers evidence as it happens
    (in EventDetector.detect() and MusicState.state_refresh_loop), then
    feeds Gemini output through validate()."""

    def __init__(self, tolerance_s: float = 1.0):
        # Index by (source, key) -> list of t_session values
        self._index: dict[tuple[str, str], list[float]] = {}
        self.tolerance_s = tolerance_s
        # Telemetry
        self.total_sentences = 0
        self.stripped_count = 0
        self.invalid_citation_count = 0

    def register_event(self, ev: Evidence) -> None:
        key = (ev.source, ev.key)
        self._index.setdefault(key, []).append(ev.t_session)

    def _parse_timestamp(self, ts: str | None) -> float | None:
        if ts is None:
            return None
        ts = ts.strip()
        if ts.startswith("bar:"):
            # Resolution requires bpm context — caller passes via mix-citation
            # path. For raw bar: claims we return -1 and the validator treats
            # them as "atemporal but must match an aud:phrase_boundary tag".
            return -1.0
        if ":" in ts:
            mm, ss = ts.split(":", 1)
            return int(mm) * 60 + float(ss)
        try:
            return float(ts)
        except ValueError:
            return None

    def _parse_block(self, block_text: str) -> list[Citation]:
        # block_text is the inner "claims" group from CITATION_RX, e.g.
        # "ev:DROP@04:22; aud:peak_rms=0.91"
        out = []
        for piece in block_text.split(";"):
            piece = piece.strip()
            if ":" not in piece:
                continue
            source, rest = piece.split(":", 1)
            if "@" in rest:
                key, ts = rest.split("@", 1)
                t = self._parse_timestamp(ts)
            else:
                key, t = rest, None
            # Strip trailing "=value" if present
            if "=" in key:
                key = key.split("=", 1)[0]
            out.append(Citation(source.strip(), key.strip(), t))
        return out

    def _is_valid(self, c: Citation) -> bool:
        # Atemporal sources: presence in index is enough.
        if c.source in ("track", "tend") and c.t_session is None:
            return (c.source, c.key) in self._index
        # Atemporal source given with a timestamp is fine — we just check key presence.
        idx_key = (c.source, c.key)
        if idx_key not in self._index:
            return False
        if c.t_session is None:
            return True
        # Timestamp check — within tolerance band of any registered event of this key.
        return any(
            abs(t - c.t_session) <= self.tolerance_s
            for t in self._index[idx_key]
        )

    def _sentence_is_sourced(self, sentence: str) -> tuple[bool, int, int]:
        """Returns (has_any_valid_citation, n_valid, n_invalid)."""
        n_valid = n_invalid = 0
        for m in CITATION_RX.finditer(sentence):
            cites = self._parse_block(m.group("claims"))
            for c in cites:
                if self._is_valid(c):
                    n_valid += 1
                else:
                    n_invalid += 1
        return (n_valid > 0, n_valid, n_invalid)

    def validate(self, text: str, *,
                 mode: str = "debrief",
                 allow_grounding_paragraph: bool = True) -> ValidatedText:
        """mode in {'live', 'debrief', 'library', 'genre'}.
        - live: response-level — empty if no valid citation found anywhere.
        - debrief / genre: sentence-level stripping.
        - library: per-recommendation block (split on double-newline)."""

        sentences = SENTENCE_RX.split(text.strip()) if text.strip() else []
        self.total_sentences += len(sentences)

        if mode == "live":
            any_valid, nv, ni = self._sentence_is_sourced(text)
            self.invalid_citation_count += ni
            if not any_valid:
                self.stripped_count += len(sentences)
                return ValidatedText("", [(text, "no_valid_citation")], nv, ni)
            return ValidatedText(text, [], nv, ni)

        accepted: list[str] = []
        stripped: list[tuple[str, str]] = []
        total_valid = total_invalid = 0

        # Heuristic: the FIRST sentence of a debrief chapter may be a
        # grounding paragraph ("This was your second session this week.")
        # and is allowed to skip citation. Controlled per-mode.
        is_first = True

        for s in sentences:
            s_stripped = s.strip()
            if not s_stripped:
                continue
            has_valid, nv, ni = self._sentence_is_sourced(s_stripped)
            total_valid += nv
            total_invalid += ni

            if has_valid and ni == 0:
                accepted.append(s_stripped)
            elif has_valid and ni > 0:
                # Mixed — accept (sentence has at least one real anchor) but log.
                accepted.append(s_stripped)
                stripped.append((s_stripped, f"mixed_{ni}_invalid"))
            elif allow_grounding_paragraph and is_first and mode == "debrief":
                accepted.append(s_stripped)
            else:
                stripped.append((s_stripped, "unsourced" if ni == 0 else "all_invalid"))
                self.stripped_count += 1

            is_first = False

        self.invalid_citation_count += total_invalid

        if not accepted:
            # Emergency: linter ate everything. Caller decides fallback.
            return ValidatedText("", stripped, total_valid, total_invalid)

        return ValidatedText(" ".join(accepted), stripped, total_valid, total_invalid)

    def strip_unsourced(self, text: str, mode: str = "debrief") -> str:
        return self.validate(text, mode=mode).accepted

    def slop_ratio(self) -> float:
        if self.total_sentences == 0:
            return 0.0
        return self.stripped_count / self.total_sentences
```

### Edge cases — answers

- **Citation-only sentence** ("Per `[ev:TRACK_CHANGE@03:45]`."): KEEP. It's grounded by construction even if conversationally thin. Stripping it would feel pedantic.
- **Citation in subordinate clause vs main clause**: Don't distinguish. A sentence is sourced if it contains ≥1 valid citation anywhere. Going stricter (main-clause-only) makes the linter aggressive without measurable anti-slop gain.
- **Citation with malformed shape** ("event was at 3:45"): Doesn't match `CITATION_RX`. Sentence has zero citations → strip. This is the *correct* failure mode — Gemini learns through the prompt+telemetry loop to use the grammar.
- **Empty output after stripping**:
  - Live mode → fall back to pre-canned ack from [A-latency.md].
  - Debrief mode → emit a single recovery line ("Couldn't ground enough of that chapter. Re-running.") and re-prompt Gemini with the stripped sentences and instruction "these were unsourced — cite or remove." One retry; if still empty, ship the chapter omitted with a `[chapter_skipped]` marker.
  - Library mode → return zero suggestions rather than ungrounded ones.

### Validation against the registry

The linter does NOT scan `events.jsonl` from disk per call. That would be both slow and racy (the file is being appended to). Instead:

- Every event detected by `EventDetector` calls `linter.register_event(Evidence(...))` synchronously alongside `recorder.log_event(...)`.
- Every audio feature snapshot pushed into `MusicState.state_refresh_loop` registers an `Evidence(source="aud", key="peak_rms", t_session=t, extras={"value": 0.91})`. Same for `bands`, `bpm`, `spectral_flux`.
- Every MIDI move logged into `ControllerState.recent_moves` registers an `Evidence(source="midi", key=label, t_session=t)`.
- Every `TrackInfo` poll registers `Evidence(source="track", key=f'"{title}"', t_session=t)`.

Result: the index is in-memory, O(1) lookup, refreshed live, and survives session-restart because every entry has been mirrored to `events.jsonl` (so debrief can rebuild it from disk in one pass at session-end).

---

## 3. Per-Mode Prompt Templates

The prompt enforces citation discipline at write-time; the linter enforces it at read-time. The two together make Gemini converge on grammar quickly (~3-5 turns in a fresh session; see `cohost_v4.py:154` system instruction style).

### a. Live mode (1-2 sentences, <800ms target)

**Added to existing `SYSTEM_INSTRUCTION` in `cohost_v4.py`** (after the "trust the audio" rule):

```
GROUNDING DISCIPLINE — HARD RULE:
Every claim you make must cite at least one evidence token in this shape:
  [ev:TRACK_CHANGE@04:22]
  [aud:peak_rms@04:22]
  [midi:deckA_filter:23@04:22]
  [track:"Boys Noize - Mvinline"]
Source tags allowed: ev / aud / midi / track / screen / mix / tend.
Timestamps are mm:ss session-relative.
Your whole response must contain at least one valid token, OR the post-
processor drops it and the user hears silence. Cite or stay quiet.
You can put the token inline naturally:
  "Nice — that filter at [midi:deckA_filter:23@04:22] really opened it up."
NOT meta-commentary:
  "Based on the data, the filter at 4:22..."
```

**User payload format** (built per-event by `AICoach`, current shape in `cohost_v4.py:1336 evidence_line`):

```
EVENT: MIX_MOVE
EVIDENCE:
  hearing[rms=0.087 sub=0.41 low=0.28 mid=0.18 high=0.13 bpm=128]
  track="Boys Noize - Mvinline"
  deck=A
  set_time=12:43
  phase_age=8.2s
  recent_moves[8s]: 1.2s ago deckA_filter:104, 3.4s ago xfader_to_B
TASK: One sentence. React to the move. Cite at least one ev/aud/midi/track.
```

**Example pass:**
> "Clean — you opened the filter at `[midi:deckA_filter:104@12:42]` right when the bridge hit, that's the move."

Sentence-level: 1 valid citation → response passes. Output delivered to TTS.

**Example fail:**
> "Great energy management there, really feeling it."

Sentence-level: 0 citations. Response-level (live mode): empty after stripping → fall back to pre-canned ack ("nice") from ack-bank. Telemetry: `{mode: live, fallback: true, reason: no_citation}`.

### b. Post-session debrief (long-form)

**System instruction** (extends [E-debrief-pedagogy.md template]):

```
You are vibemix's post-session DJ coach.
[... pedagogy block from E-debrief-pedagogy.md ...]

GROUNDING DISCIPLINE — HARD RULE:
Every sentence in "What worked", "What to drill", and "3 drills" must cite
at least one evidence token. Token grammar:
  [<source>:<key>@<mm:ss>]
  Sources: ev / aud / midi / track / screen / mix / tend.
Multi-claim sentences may chain inside one bracket with semicolons:
  [ev:PHASE@23:14; aud:peak_rms=0.91; midi:lows_killed_deckA@23:13]

The opening "What I heard" paragraph is grounding context — it may use
prose without per-sentence citations, but must include at least 3 tokens
total across its 4-6 sentences.

The post-processor will strip any unsourced sentence in the critique
chapters. If you can't cite, don't claim. Better to write 5 sentences
that all land than 12 sentences where half get stripped.
```

**User payload** = the full `session_summary.json` ([E-debrief-pedagogy.md]) — `events.jsonl` rows, MIDI moves, AI reactions log, energy proxy, profile priors. Plus the 80-min `input.wav` attached as audio Part.

**Example pass (one chapter):**
> **What to drill**
> - At `[ev:PHASE@23:14]` you mixed in 8 bars early — the outgoing track's bridge `[aud:peak_rms=0.74@23:13]` was still resolving when the new kick `[ev:TRACK_CHANGE@23:14]` punched through, so the build never released. The fix is the 32-bar wait: park at the cue, listen for the bridge to resolve, then bring the new track in on the downbeat `[mix:phrase_aligned=true]`.
> - Filter sweep at `[midi:deckA_filter:23@04:22]` ran 12.4 bars `[aud:hi_share=0.18→0.42@04:22]` — pros sit at 4-6. Cut it shorter; the longer it goes, the more the crowd reads it as "DJ doesn't know what to do next."

Both sentences land — every claim has a token, all valid against the registry. Output preserved.

**How the linter applies per-chapter:** the response is split on `## ` headers first; each chapter is fed to `linter.validate(chapter_text, mode="debrief", allow_grounding_paragraph=True)` separately. Per-chapter `slop_ratio` is computed independently and surfaced in the debrief UI (transparency move). A chapter that hits >50% strip rate is replaced by a single "Couldn't ground this chapter — re-running" line and a single retry is fired with the stripped sentences shown back to Gemini.

### c. Library suggestion ("what should I play next?")

**System instruction:**

```
You are vibemix's library scout. The user asked for next-track suggestions.

GROUNDING DISCIPLINE — HARD RULE:
For every suggestion, you must cite:
  1. [track:"<title>" bpm=N key=XX]   — the library track itself
  2. At least ONE rationale token tied to the current playback:
     [aud:bpm=128@now] | [track:"<current>" key=8A]
     | [mix:harmonic_distance=0.2] | [tend:tendency_idx=2]

Suggestions without both anchors will be dropped. The user only sees
suggestions you can defend.

Format each suggestion as one paragraph, blank line between suggestions:

  1. "Track Title" — Artist  [track:"Track Title" bpm=130 key=9A]
     Why: it's a +1 Camelot move from your current 8A [track:"current"
     key=8A; mix:harmonic_distance=0.2] and lifts the BPM 2 cleanly
     [aud:bpm=128@now].
```

**User payload** = current track + last 5 tracks + library candidates (top-K from Gemini Embedding 2 nearest-neighbour). Each candidate already has Rekordbox priors attached.

**Example pass:**
> 1. "Mvinline" — Boys Noize  `[track:"Mvinline" bpm=130 key=9A]`
>    Why: harmonic +1 from your current 8A `[track:"Spit It Out" key=8A; mix:harmonic_distance=0.2]`, BPM lift is gentle from where you sit `[aud:bpm=128@now]`, and your set arc is flattening `[aud:peak_rms=0.62@now]` — this track's hook lifts.

Per-suggestion lint pass; all anchors land.

**Example fail:**
> 1. "Mvinline" — Boys Noize. This is a banger that everyone loves and will hype the crowd.

Per-suggestion: no `[track:]` token, no rationale token. Stripped from output. User sees the other 4 suggestions.

### d. Genre-aware feedback

**System instruction:**

```
You are vibemix's genre-aware coach. The user is playing {genre}.
Genre-specific events fire from the genre detector ({detector_name}).

GROUNDING DISCIPLINE — TIGHTER THAN GENERIC MODE:
Every genre-specific claim must cite the detector that fired:
  [ev:KICK_VARIATION@04:22]
  [ev:HARDSTYLE_REVERSE_BASS@04:22]
  [ev:TECHHOUSE_PERC_LOOP@04:22]
Generic audio observations still need a regular [aud:] or [midi:] anchor.

If you cannot cite the genre detector, you cannot make the genre claim.
("That kick variation was sick" without [ev:KICK_VARIATION@...] = stripped.)
```

The system instruction here is *narrower* on purpose. Generic mode might forgive "your energy curve flatlined" with just `[aud:peak_rms=...]` because the audio anchor exists. Genre mode requires the detector citation too — "the techno kick variation at 4:22" must point to `[ev:KICK_VARIATION@04:22]`, because the *genre interpretation* is the load-bearing claim.

---

## 4. Live-Mode Latency Budget

**Per-response linter cost: <3ms on a 1-2 sentence completion.**

Profiling estimate (Python 3.14 on M-series Mac, `re` stdlib, in-memory dict registry):

| Operation | Time |
|---|---|
| `SENTENCE_RX.split(text)` on ~80 chars | ~30µs |
| `CITATION_RX.finditer(sentence)` × 2 sentences | ~100µs |
| `_parse_block` per match (avg 1.3 claims) | ~40µs |
| `_is_valid` dict lookup + tolerance scan (≤10 entries/key) | ~25µs |
| Total worst-case for live response | **~2.5ms** |

Relative to Bucket A's 800-2000ms voice-to-voice budget — negligible. The linter runs synchronously on the LLM-stream-complete event, before the response is handed to TTS. No need to offload, no need to stream-incrementally lint.

**Streaming-incremental linting is unnecessary** in live mode because the response is short — by the time the first sentence has finished streaming from Gemini, the LLM is already 80%+ done. Waiting for the full response adds ~50ms (LLM remainder) vs the ~3ms lint cost. Saving the ~50ms is not worth the implementation complexity of mid-stream linting.

**Recommendation:** lint synchronously between LLM-complete and TTS-start in live mode. No optimization needed.

For **debrief mode**, the linter pays ~30-80ms on a 4-chapter 800-word response — also irrelevant against a 15-30s Gemini debrief call.

---

## 5. Telemetry + Trust Signals

The linter emits one event per stripped sentence and one summary event per validated response:

```python
# Per-stripped-sentence (high volume)
{
  "t": 423.1,
  "kind": "linter_strip",
  "mode": "live",
  "reason": "no_valid_citation",  # or "all_invalid" / "mixed_invalid"
  "sentence_preview": "Great energy man...",  # first 40 chars
  "invalid_citations": 0,
}

# Per-validated-response (one per Gemini call)
{
  "t": 423.5,
  "kind": "linter_validate",
  "mode": "live",
  "event_type": "MIX_MOVE",          # which event triggered the LLM
  "sentences_total": 2,
  "sentences_stripped": 0,
  "valid_citations": 3,
  "invalid_citations": 0,
  "fallback_fired": false,
}
```

**Three derived signals:**

1. **Per-session slop ratio** (`stripped / total`) — exposed in the debrief UI ("vibemix kept 47 of 52 reactions you'd heard; 5 were dropped for not citing real events"). This is a *transparency feature* — it turns the anti-slop discipline into a visible product signal. Users learn the AI is filtering itself.

2. **Per-mode slop tracking** (rolling 7-day average): live vs debrief vs library vs genre. Expected ranges from prompt design:
   - Live: 5-15% strip rate is healthy (Gemini occasionally veers into generic praise)
   - Debrief: 10-25% strip rate is healthy (long-form invites more drift)
   - Library: <5% strip rate (highly structured output)
   - Genre: 15-30% strip rate (tighter rule, more strips expected)
   A spike beyond +2σ of the rolling 7-day average triggers an alert in `~/Library/Application Support/vibemix/health.json`. Alert = "Gemini-side regression suspected; check model version."

3. **Per-event-type slop tracking**: which event types lead to the most stripped responses? If `HEARTBEAT` events strip 60% of the time but `MIX_MOVE` events strip 5%, the prompt for HEARTBEAT needs sharpening — the AI has nothing concrete to grab.

---

## 6. Failure Mode Inventory

1. **Linter strips EVERYTHING** (Gemini ignored citation instructions, or model regressed): live mode falls back to pre-canned ack; debrief retries once with stripped sentences shown back to Gemini ("these were unsourced — cite or remove"); if second pass also empty, surface a single recovery line and a `[chapter_skipped]` marker. Alert fires when this happens >3× in 10 minutes (model is broken, escalate).
2. **Linter passes invalid citations** (regex misses malformed): write 200 golden-corpus tests (real Gemini outputs from past `events.jsonl` invoke dirs) with expected accept/reject labels. Run in CI. Each new event type added to `EventDetector` adds 5 corpus cases.
3. **Linter is too strict, over-strips**: tolerance band tuneable per-mode (live ±1.0s, debrief ±2.0s) is the first lever. Second lever: `allow_grounding_paragraph` flag preserves first sentence of long-form chapters. Third lever: telemetry-driven — if slop ratio exceeds 30% in live mode for 24h, auto-relax `tolerance_s` by 0.5 and flag for Kaan's ear-test gate.
4. **Gemini cites a real event but timestamps it wrong**: the ±tolerance band catches small drift; large drift (e.g. citing `[ev:DROP@04:22]` when the actual DROP was at 04:31) gets caught — `_is_valid` returns False, sentence stripped, telemetry logs `reason=mixed_invalid` with the cited-vs-actual delta. Useful diagnostic for prompt sharpening.

---

## 7. Implementation Phasing

- **v1.0 (June 2026 launch)** — No linter. Prompt-only grounding. Rationale: v4's existing system instruction already enforces "trust the audio, don't invent kicks/drops"; Phase 16 (Kaan's DJ-ear gate) hasn't been satisfied yet, and shipping a linter without telemetry from production means tuning it blind. v1.0 ships the citation grammar in the *prompt* so Gemini gets used to emitting tokens — even though the linter isn't yet enforcing them — to seed corpus data for v1.1.
- **v1.1 (~2-4 weeks post-launch)** — Linter in live mode, strict response-level enforcement, pre-canned ack fallback. Telemetry on. Slop-ratio surfaced in a hidden debug panel (`?debug=1` URL param on the desktop overlay) but not yet in user-facing UI. Kaan validates against 5+ real DJ sessions before the linter is on-by-default.
- **v2.0 (alongside debrief, library, genre features)** — Linter cross-mode: sentence-level for debrief and genre, per-suggestion for library, response-level for live. Slop ratio exposed in debrief UI as a transparency signal. Per-mode tolerance tuning. Auto-alerts on Gemini-side regression.

Rationale per phase: the v1.0 → v1.1 split is driven by the [project_phase_16_kaan_dj_testing] gate. Shipping linter strictness at v1.0 risks degrading the launch reactions; landing it in v1.1 lets us tune from real telemetry. The v1.1 → v2.0 split tracks the debrief feature itself, which is a v2 product.

---

## Open questions for Kaan (5 max)

1. **Live-mode strictness — response-level vs sentence-level?** I picked response-level on the grounds that a partial 1-of-2-sentence response feels broken. But sentence-level with a "must have at least one valid sentence" rule would let the half-bad responses through partially. Lean response-level; flag your call.
2. **Tolerance band: ±1.0s live, ±2.0s debrief — correct?** Bucket A latency budget says reactions land 5-10s late today. If we set live tolerance to ±1.0s but reactions consistently arrive 2-3s after the cited event, valid citations get rejected. Should the band track the rolling voice-to-voice latency instead of being a constant?
3. **Telemetry exposure — show slop ratio to user?** I'm proposing yes (in debrief UI) as a transparency feature. Some product folks would argue it's noise. Counter-argument: making the anti-slop discipline *visible* is itself a trust-building move that differentiates vibemix from "generic AI commentary." Worth a decision before v2 UI lock.
4. **Grounding paragraph allowance** — sentence 1 of a debrief chapter can skip citation if it's setting context. Acceptable hole or risk-of-abuse (Gemini learns to dump unsourced claims into "context" sentences)? Mitigation: cap at 1 unsourced sentence per chapter; if telemetry shows abuse, drop the allowance entirely.
5. **Cross-session corpus for prompt-tuning** — every `linter_strip` event has the offending sentence. After 100 sessions, that's a corpus of ~3-5k stripped sentences. Worth investing in an end-of-week "what Gemini got wrong" review tool, with the stripped sentences clustered by mode + event type? Could feed back into prompt iteration. Lean yes; flag whether this is a v2.0 or v2.x build.

---

## Sources

- [E-debrief-pedagogy.md (Bucket E)](./E-debrief-pedagogy.md) — pattern origin, debrief prompt, profile architecture
- [A-latency.md (Bucket A)](./A-latency.md) — live-mode latency budget, ack bank fallback
- `cohost_v4.py:1167-1330` — `Event`, `EventDetector`, event-type taxonomy
- `cohost_v4.py:1336-1380` — `AICoach.evidence_line` — current evidence packet shape
- `cohost_v4.py:839-843` — `VoiceRecorder.log_event` — `events.jsonl` row shape
- [Chain-of-Verification reduces hallucination (ACL 2024)](https://aclanthology.org/2024.findings-acl.212.pdf) — citation-discipline pattern in long-form generation
- [Mitigating Hallucination in LLMs survey (arXiv 2510.24476)](https://arxiv.org/html/2510.24476v1) — post-processing strip vs re-prompt tradeoff
- [Citation-grounded code comprehension (arXiv 2512.12117)](https://arxiv.org/html/2512.12117v1) — prior art on machine-parseable inline citation tokens
- [Python `re` vs `regex` library notes](https://pypi.org/project/regex/) — confirms stdlib `re` is sufficient for the grammar (no recursive patterns, no variable-length lookbehinds required)
- [Gemini API output structure docs](https://ai.google.dev/gemini-api/docs/text-generation) — streaming chunk shape, sentence boundary semantics
- [project_anti_slop_grounded_gemini_thesis] (memory) — central product principle
- [project_phase_16_kaan_dj_testing] (memory) — DJ-ear gate
- [project_one_click_install_hard_req] (memory) — dep budget motivating `re`-stdlib over third-party `regex`
