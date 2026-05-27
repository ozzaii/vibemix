# Reaction-Context Enrichment Audit — vibemix cascade path

Branch `live-tuning-or-brain`. Read-only design+research. Judging criteria: **anti-slop**
(grounded, citation-resolvable reactions) + **"alive, not late"** (TTFT must feel real-time).

---

## 1. CURRENT STATE (mapped, file:line)

### Audio window + Part assembly
- `INVOKE_AUDIO_SECONDS = 60.0` — `src/vibemix/audio/constants.py:20`. Full-payload window.
- `DIET_AUDIO_SECONDS = 6.0` — `src/vibemix/agent/dj_cohost.py:103`. Ack-eligible events shrink to 6s.
- Per-call window choice: `audio_seconds = DIET_AUDIO_SECONDS if diet else INVOKE_AUDIO_SECONDS`
  — `dj_cohost.py:1154`. `diet = ev_type in ACK_ELIGIBLE_EVENTS` (`:1153`).
- Audio is snapshotted off the ring: `audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)`
  — `dj_cohost.py:1180`.
- **HARD CONSTRAINT**: the ring is sized `AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0, ...)`
  = **65 s** — `__main__.py:586`. The buffer *physically cannot hold 3 minutes today*. The
  separate gain-boosted `audio_buf` is 140s (`__main__.py:22`, `buffers.py:9`), but the **clean**
  buffer fed to Gemini is 65s.
- Parts attached per call (`contents` list, `dj_cohost.py:1291`–1332):
  1. **text prompt** (string) — `text_prompt + parts_clause + history_clause` (`:1292`)
  2. **master audio** Part — always (`:1293`, `audio/wav`)
  3. **mic audio** Part — conditional, 8s, only when KAAN spoke within `MIC_AUDIO_PART_RECENCY_S`=4s
     and ring RMS > floor (`:1226`–1256, `:1295`)
  4. **lookahead** Part — conditional, next-track source-file snapshot (`:1267`–1320)
  5. **screen** Part — hardwired `screen_jpeg = None` (`:1204`); disabled, caused hallucination.
  → **Max 1 image-equiv + up to 3 audio Parts**; in the common case it's **1 text + 1 audio (60s)**.

### Thinking budget + model
- Live path config: `thinking_config=types.ThinkingConfig(thinking_level="minimal")`,
  `temperature=1.0`, `max_output_tokens=1024` — `dj_cohost.py:604`–608 (and the per-turn cached
  branch re-states the same literal `:1363`).
- **Thinking is already pinned to MINIMAL, globally, with no per-event split.** It is *enforced*
  by `thinking_gate.validate_live_config` (`llm/thinking_gate.py:40`, `_ALLOWED_THINKING={"MINIMAL"}`)
  which **raises** if anything higher is set on the live path — Phase 41 LAT-08: "anything higher
  adds 7s+ TTFT regression." Service tier STANDARD enforced; FLEX banned (`:43`).
- **Model resolves to `gemini-3.5-flash`** — `llm/_router_config.py:27`
  (`"live_coach": ("gemini-3.5-flash", ServiceTier.STANDARD)`). TTS is already `gemini-3.1-flash-tts-preview`
  (`:28`). Models are config-only here; CI grep-gates literals elsewhere.

### Reaction history
- `self._ai_text_history = collections.deque(maxlen=10)` — `dj_cohost.py:554`.
  **Last 10 reactions, verbatim**, each tagged `[M:SS]` (`:824`).
- Re-sent every call as `history_clause` (`:1207`–1216): full join of all 10, with instruction
  "do NOT repeat/rephrase, find a FRESH angle, don't re-quote a set-time you already mentioned."

### Evidence-grounded prompt (`state/coach.py`)
- `AICoach.build_prompt(ev, registry_snapshot=, diet=, [recall_moments=])` (`coach.py:578`,
  `dj_cohost.py:1172`). `evidence_line` (`coach.py:256`) packs: track + confidence, `deck=`,
  `set_time=M:SS` (`:299`), resolved deck keys/BPM (camelot, `:311`), `phase_age`/`track_age`
  (`:330`), `recent_moves[8s]` (`:335`), **`set_arc[Ns]=<long_arc>`** (`:346`), `phase_history`
  chain (`:355`), `recent_tracks` chain (`:360`), and the EvidenceRegistry citation-corpus footer
  (`:362`). Diet path drops the history fields (`_evidence_line_compact`, `:427`).

### "Set vibe" — what already exists
- `MusicState.long_arc` = **~120s RMS at 10s hop** (`music_state.py:126`) — already a coarse
  rolling set-energy curve, already surfaced as `set_arc[]` in the prompt (`coach.py:346`).
- `energy_curve` = last ~12s @ 1s hop (`music_state.py:35`); `phase_history` / `track_history`
  last 6 (`:127`–128). **No running session *embedding* and no LLM set-summary.**
- The embedding layer (`library/`, `gemini-embedding-2` via `_router_config.py:40`, FLEX lane)
  is built for offline library vibe search — it is **not** wired to the live loop and emb-2 has a
  ~80–180s audio cap. It *could* produce a rolling vector cheaply (one FLEX embed call per N
  seconds), but a vector is not consumable as grounding text by the coach prompt — it'd need a
  nearest-label lookup to become words. Verdict: **`long_arc` is already the cheap set-vibe;
  don't add an embedding to the hot path.**

---

## 2. THE PROPOSAL SCORED (a–e)

Audio token math (verified: **~32 tokens/sec**, 2026 rate — ai.google.dev pricing; costgoat):
60s ≈ **1,920 tok**; 180s ≈ **5,760 tok** (+3,840 tok). At `gemini-3.5-flash` audio-input
(model input rate $1.50/1M today): 60s ≈ $0.0029, 180s ≈ $0.0086 per call **just for master audio**.

### (a) 3 MIN audio instead of 60s — **DROP (modify to ≤90s + text summary)**
- **Cost**: +3,840 input tok/call → ~3× the master-audio bill. Over a 90-min set with a reaction
  ~every 22s (≈245 reactions), that's ~+0.94M input tok ≈ **+$1.40/set on 3.5-flash** for audio alone
  — and the input also re-bills on every single call (no caching of the rolling window).
- **Latency**: TTFT scales with prefill token count. Tripling the dominant input Part directly
  inflates prefill → slower first token. This **directly attacks "alive, not late."**
- **Grounding value**: marginal. A reaction is about *what's happening now* + recent arc. The model
  does not need to re-hear 3 minutes of audio it already reacted to — that history is better carried
  as **compact text** (`set_arc`, `phase_history`, `recent_tracks`) which is already in the prompt
  at ~near-zero token cost. 3 min of raw audio = paying audio-token rates to re-encode the past.
- **Blocker**: the clean ring is 65s (`__main__.py:586`) — 3min is impossible without a buffer
  resize, which also triples that buffer's RAM.
- **Recommend**: keep 60s (optionally 75–90s ceiling). Enrich the *past* via text, not raw audio.

### (b) SET VIBE (running embedding/summary) — **KEEP, but as the existing cheap text, not a new embedding**
- The cheap version **already ships**: `long_arc` → `set_arc[]` in the prompt (`coach.py:346`).
- A live `gemini-embedding-2` vector adds a hot-path network call + can't be read as grounding words
  without a label-lookup; emb-2's audio cap and FLEX latency make it wrong for the 22s loop.
- **Modify**: enrich the existing text set-vibe — e.g. a 1-line rolling summary string
  (genre, BPM band, energy trend up/flat/down from `long_arc` slope, # tracks so far). Pure
  string assembly from `MusicState`, ~20 tokens, zero added latency. This is the right "set vibe."

### (c) DELTA-SINCE-LAST-REACTION audio — **KEEP as a complement, not a replacement**
- Sending only new audio since the last reaction is **cheaper** when reactions cluster:
  gap is gated to ≥22s (`EVENT_GLOBAL_MIN_GAP`, `constants.py:59`) but bursts can fire at the
  per-type floor (TRACK_CHANGE 5s). A delta window = `min(60s, now - last_reaction_ts)` caps
  audio at exactly the unheard portion → on a 5–10s burst you send 5–10s not 60s (5–10× cheaper).
- **Risk**: too-small a window loses the "what was building" context. Design with a **floor**:
  `delta = clamp(now - last_reaction_ts, 12s, 60s)`. Keeps grounding, trims waste on bursts.
- **Design**: store `self._last_reaction_ts`; `audio_seconds = clamp(now - last, 12.0, INVOKE_AUDIO_SECONDS)`
  on the *non-diet* path (diet stays 6s). The recent arc the model "missed" is still carried in
  `set_arc`/`recent_moves` text. **Net: cheaper + same grounding. Recommend adopt.**

### (d) ALL prior reactions — **DROP. Keep bounded `maxlen=10` + add a rolling summary**
- Unbounded history over 90 min = unbounded prompt tokens + linear TTFT creep — anti-"alive".
- Current `maxlen=10` verbatim is correct for "don't repeat what you just said."
- For "callback to earlier in the set" without unbounded cost: keep **last 10 verbatim** + add a
  **single rolling-summary line** ("earlier you hyped the acid breakdown ~12 min ago; called the
  key clash at 0:34"). Compress on eviction (when the deque drops an item, fold its gist into the
  summary). One short string, bounded. **Recommend: bounded verbatim + 1 summary line.**

### (e) THINKING low/minimal — **ALREADY minimal globally; modify to a per-event split (cautiously)**
- Today: hard MINIMAL everywhere, gate-enforced (`thinking_gate.py:40`). Minimal is the documented
  default for real-time voice (960ms TTFT on Flash Live; blog.google). **Minimal does NOT inherently
  break grounding** — grounding comes from the evidence packet + audio Part + citation gate
  (invariant #2), not from chain-of-thought. So minimal is safe for the anti-slop gate *as long as
  citations still resolve*.
- **But** a big structural moment (full MIX_MOVE / TRACK_CHANGE into a new genre) is where one extra
  reasoning step could pick the *right* callback. The 7s-regression figure was measured at LOW/MED/HIGH;
  **`low`** specifically is the unmeasured middle.
- **Recommend**: keep MINIMAL for HEARTBEAT / ack-eligible / MIC. *Pilot* `low` for TRACK_CHANGE and
  big MIX_MOVE **only** behind a latency A/B — and **first relax the `thinking_gate` allow-list**
  (it currently *raises* on anything but MINIMAL, `:40`, so a per-event `low` would crash the live
  path). Do not ship `low` until a TTFT measurement on 3.1-flash confirms it stays under ~1.2s.

---

## 3. GEMINI 3.1 FLASH — VERDICT + PRICE (sources)

**Exists (2026), audio + thinking + streaming all supported.** Pricing snapshot (ai.google.dev,
May 2026):

| Model | Text in / 1M | Output / 1M | Audio in | Thinking | Streaming |
|---|---|---|---|---|---|
| **gemini-3.5-flash** (current `live_coach`) | **$1.50** | **$9.00** | yes (multimodal) | minimal..high | yes |
| **gemini-3.1-flash** | **$0.75** | **$4.50** | yes (multimodal) | minimal..high | yes |
| gemini-3.1-flash-lite | $0.25 | $1.50 | $0.50 | yes | yes |
| gemini-3-flash | $0.50 | $3.00 | $1.00 | yes | yes |

- **3.1-flash is exactly 1/2 the price** of 3.5-flash on both input and output (Kaan guessed ~1/3 —
  it's ~50% cheaper, even better than he feared on input, slightly less than 1/3).
- A separate **`gemini-3.1-flash-live`** exists (real-time audio-to-audio, 960ms TTFT) — that's the
  **Live API**, which vibemix explicitly **rejected** (cascade-only). Not the same as `gemini-3.1-flash`
  used on the cascade path. Don't conflate.

**VERDICT — SWITCH `live_coach` to `gemini-3.1-flash`.** Half the cost, same modality/thinking/streaming
support, same cascade call shape. **Gate it behind a live ear-test** (3.5→3.1 is a quality step *down*
on paper; vibemix's bar is grounded-not-smart, and minimal-thinking grounding rides the evidence packet,
so 3.1-flash should hold — but verify on a real set before locking). **Change is a one-line edit at
`_router_config.py:27`** — never hardcode elsewhere.

Sources: ai.google.dev/gemini-api/docs/pricing · blog.google/.../gemini-3-flash · costgoat.com/pricing/gemini-api ·
ai.google.dev/.../gemini-3.1-flash-live-preview · marktechpost (3.1 Flash Live launch).

---

## 4. "STREAMING ON BOTH" — what it can actually mean here

- **Output is already streamed**: `generate_content_stream` (`dj_cohost.py:1472`) + streaming TTS.
  That half exists.
- **Input is NOT streamable on the cascade path.** The cascade sends a *complete request* (text +
  audio Parts) per detected event; `generate_content_stream` streams the **response**, not the
  request. There is no "stream the master audio in continuously" on `generate_content` — that
  continuous-input model **is the Live API** (`gemini-3.1-flash-live`), which vibemix rejected.
- So **"streaming on both" is not available** on the current architecture without adopting the Live
  API. What *is* achievable and worth doing:
  - **(i)** Keep output streaming (done).
  - **(ii)** The only "input latency win" left on the cascade is **shrinking the input prefill** —
    i.e. the delta-window (c) + not bloating to 3min (a). Smaller input Part = faster first token.
    That is the real, reachable "alive" win — not input streaming.
- **Conclusion**: define "streaming on both" honestly as **streamed output + minimized input prefill**.
  True input streaming = Live API = out of scope (already a locked decision).

---

## 5. OPTIMAL REACTION-CONTEXT DESIGN (recommended packing)

**Per non-diet reaction, send:**
1. **Master audio**: a **delta-since-last** window, `clamp(now - last_reaction_ts, 12s, 60s)`
   (cheaper on bursts, full 60s when idle). Keep diet path at 6s.
2. **Text set-vibe line** (new, ~20 tok): genre + BPM band + energy trend (slope of `long_arc`) +
   tracks-so-far count. Built from `MusicState`, zero network, zero added latency.
3. **Evidence packet** (unchanged): track/deck/keys/`set_arc`/`recent_moves`/`phase_history` +
   citation footer — this is the grounding spine; keep it.
4. **Reaction history**: last 10 verbatim (unchanged) **+ 1 rolling-summary line** for callbacks.
5. **Mic / lookahead Parts**: unchanged (already conditional + cheap).
6. **Drop**: the 3-min raw-audio idea and the all-reactions idea. Do NOT add a live embedding call.

**Thinking levels (per event):**
- HEARTBEAT, ack-eligible (MIX_MOVE/LAYER_ARRIVAL/MIC) → **minimal** (current).
- TRACK_CHANGE, big MIX_MOVE → **pilot `low`** behind a TTFT A/B (requires relaxing the gate first).
- Everything else → minimal. Anti-slop is unaffected because grounding ≠ thinking depth here.

**Model:** `live_coach` → **`gemini-3.1-flash`** (½ cost), ear-test gated. TTS unchanged.

**Net effect:** lower per-reaction cost (½ from model + delta-window trim), unchanged or *better*
grounding (richer text set-vibe + callbacks), and **faster TTFT** (smaller input prefill on bursts) —
all three judging axes move the right way; the only quality risk (3.1 < 3.5 on paper) is gated by a
live ear-test.

---

## 6. PHASED CHANGE LIST (file:line)

1. **Model swap** — `llm/_router_config.py:27` — `"live_coach": ("gemini-3.1-flash", ServiceTier.STANDARD)`.
   Ear-test on a real set before lock. (~½ cost.)
2. **Text set-vibe line** — `state/coach.py` `evidence_line` (~`:346`, beside `set_arc`) — assemble
   genre + BPM band + `long_arc`-slope trend + track count from `MusicState`. No new state needed.
3. **Delta-since-last audio window** — `agent/dj_cohost.py:1154` — add `self._last_reaction_ts`
   (set post-stream near `_ai_text_history.append`, `:824`), compute
   `audio_seconds = clamp(now - last, 12.0, INVOKE_AUDIO_SECONDS)` on the non-diet branch only.
   No buffer resize (stays within 65s ring).
4. **Rolling reaction-summary line** — `agent/dj_cohost.py:554` (deque) + `:1207` (history_clause) —
   on deque eviction fold gist into a bounded summary string; append it to `history_clause`.
5. **Per-event thinking (pilot)** — FIRST relax `llm/thinking_gate.py:40`
   (`_ALLOWED_THINKING` → `{"MINIMAL","LOW"}`), THEN map event→level in `dj_cohost.py` config build
   (`:604`/`:1363`). Ship `low` for TRACK_CHANGE/big-MIX_MOVE only after a TTFT A/B confirms <~1.2s.
6. **DO NOT**: enlarge the clean ring past 65s (`__main__.py:586`) for a 3-min window; add a live
   embedding call; remove the `maxlen=10` bound.
