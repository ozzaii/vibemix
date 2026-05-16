## RESEARCH COMPLETE

**Phase:** 40 - Anti-Slop Audio Port
**Confidence:** HIGH (port from byte-identical POC; existing infra is mature)

### Key Findings
- v4 mic-Part architecture differs subtly from CONTEXT.md description: mic is a **second `AudioBuffer(seconds=12.0, sr=16000)` instance** (not the existing `MicBuffer` class), populated by **resampling the existing 48kHz mic stream → 16kHz int16** and **zero-filling samples while AI is speaking** to prevent self-triggered KAAN_SPOKE loops. The snapshot Part is **8s wide**, not 12s (the 12s is just the ring window).
- v4_tr lookahead is NOT a "3rd Part with 3s of audio" as CONTEXT.md describes. It is a **drop-in REPLACEMENT for Part 1** — when lookahead fires, the 18s window slides forward so its END is 3s past `now` (`end_file_sec = pos + lookahead_sec * rate`). Mic remains Part 2. There is no Part 3 in v4_tr's contract; the screen Part is currently `None` everywhere.
- All three external dependencies are installed and working on this Mac: `ffmpeg 8.0.1`, `nowplaying-cli` (returning "Circles"), `mdfind` (`/usr/bin/mdfind`).
- ffmpeg invocation in `cohost_v4_tr.py:746-757` uses `-f wav` (not `s16le`/`pcm_s16le` as CONTEXT.md claims). `-ss` is correctly **before `-i`** (input seek for speed). Output is mono 16kHz WAV — already compatible with `types.Part.from_bytes(mime_type="audio/wav")`.
- v4 cooldown reality is opposite of CONTEXT.md "values match v4 chat-tested baseline literally": **the values in CONTEXT.md (10/10/14/45/5) are the TARGET; the values shipped in `src/vibemix/audio/constants.py:54-90` are still the OLD values (18/16/20/70/6) verbatim from v4:134-142**. Phase 40 must REDUCE these, not preserve them.
- Pre-stage KAAN-ACTION mechanics: `release.yml` already references `TAURI_UPDATER_PRIVATE_KEY` (Phase 18 Plan 18-05); current `tauri.conf.json5` pubkey is the **2026-05-13 dev key** (Phase 18 comment confirms). PGP placeholder is `SECURITY.md` line 29 + 39 (`KAAN-PGP-PLACEHOLDER.asc` / `PLACEHOLDER-FINGERPRINT-NOT-REAL`). BlackHole probe `installed=False` is the trigger flag — needs structured-event instrumentation (no telemetry sink wired today).

### File Created
`.planning/phases/40-anti-slop-audio-port/40-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Mic-as-Part port surface | HIGH | v4 source verbatim; only adapt to package layout |
| Lookahead port surface | HIGH | v4_tr source verbatim; ffmpeg deps present + verified |
| Cooldown re-tune | HIGH | Constants live in one dict; tests likely pin old values, need updating |
| KAAN-ACTION pre-stage scaffolding | MEDIUM | Tauri key rotation runbook documented; release.yml CI legs verified; PGP publish flow is standard `gpg --send-keys` |
| Replay harness extension | HIGH | Harness CLI is argparse; adding `--print-cooldowns` is non-invasive |

### Open Questions
- Should Phase 40 ship the lookahead with `LOOKAHEAD_ENABLED=True` default-on, or keep v4_tr's `False` default and ship a UI/config toggle? (RECOMMENDATION: default-on; v4_tr was a dev-flag spike, the lookahead semantically replaces the past-only Part 1 when a local file is present.)
- The CONTEXT.md description says "Part 3 = lookahead labeled `NOT YET HEARD BY AUDIENCE`" — but v4 actually swaps Part 1's audio content (not adds a third). Recommend planner picks **v4 verbatim semantics** (swap, not append) for byte-identical anti-slop behavior; the prompt text just gets the "may include audience-not-heard frames" framing.
- ffmpeg output: should the port write `s16le` raw PCM (smaller, deterministic) or keep v4's `wav` (with header — Gemini accepts both via `audio/wav` mime)? Recommend **keep v4 `-f wav`** — it matches the existing `snapshot_wav` helper format and one less conversion step.

### Ready for Planning
Research complete. Planner can now create PLAN.md files.

---

# Phase 40: Anti-Slop Audio Port - Research

**Researched:** 2026-05-16
**Domain:** Real-time audio pipeline + multimodal Gemini request assembly + macOS subprocess integrations
**Confidence:** HIGH

## Summary

Phase 40 is a **verbatim port** from `cohost_v4.py` + `cohost_v4_tr.py` POC files into the shipped `src/vibemix/` package. Three engineering changes plus three pre-stage KAAN-ACTION discharges. The architectural primitives already exist — pre-allocated ring buffers, multimodal Gemini Part assembly, EventDetector cooldown machinery, ffmpeg + nowplaying-cli + mdfind subprocess patterns. The shipped code is also already a clean port FROM v4 for everything ELSE; this phase closes the two deliberate omissions (mic-as-Part, lookahead) that the shipped v2.1 cut without.

The biggest risk is **mis-reading the v4 architecture**: CONTEXT.md describes a 3-Part contract (mix + mic + lookahead) but v4 actually does a 2-Part swap contract (mix-OR-lookahead + mic). Both are valid product choices — but only the v4-verbatim semantics carry the "harikaydı" baseline ear-test seal. Locked decision in CONTEXT.md §3-Part vs 2-Part says "always Part 1 = BlackHole 7s (existing). Mic appended only when KAAN_SPOKE-recent. Lookahead appended only when file path resolved." That's a strict superset of v4 (adds a third slot rather than swapping). I read this as a deliberate enhancement; planner should pick one and document the deviation.

**Primary recommendation:** Port the three audio paths in this order — (1) cooldown constants update + replay-harness `--print-cooldowns` mode (smallest blast radius, regression-safe), (2) MicAudioRing wiring + 2-Part contract in `dj_cohost.py:332-342`, (3) LookaheadProvider port + 3-Part assembly. Pre-stage items run in parallel with audio work (no shared files). Defer the 3-Part-vs-swap semantic call to the discuss-phase / plan-phase decision — both are 2-day diffs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Mic audio capture | Backend (Python sidecar) | — | Existing `_audio_macos.py` `open_mic_capture` — extend its callback |
| Mic ring buffer (16kHz) | Backend (Python sidecar) | — | New `MicAudioRing` (or reuse `AudioBuffer(12.0, 16000)`); CPU side |
| Lookahead extraction (ffmpeg subprocess) | Backend (Python sidecar) | — | Off-process ffmpeg call, async-offloaded; never on audio thread |
| Multimodal Part assembly | Backend (Python sidecar) | — | `DJCoHostAgent.llm_node` — already the chokepoint |
| Event cooldown tuning | Backend (Python sidecar) | — | Pure constants table in `audio/constants.py` |
| Replay harness regression | CI / dev tooling | — | `scripts/eval/replay_harness.py` — standalone script |
| BlackHole probe (CoreAudio) | Tauri Rust + Python | Tauri Rust UI | Probe runs sidecar-side via `_audio_macos.py` query_devices; CTA fires in Tauri shell wizard |
| Tauri ed25519 updater key | CI / release pipeline | Tauri Rust runtime | Pubkey lives in `tauri.conf.json5`; signing happens in `release.yml` |
| PGP key publishing | Out-of-process Kaan action | Repo `SECURITY.md` | Key generation + `keys.openpgp.org` publish is manual; commit is engineering |

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | 2.0.1 | Gemini multimodal Part assembly | Already shipped — `types.Part.from_bytes` is the standard `audio/wav` ingress path [VERIFIED: src/vibemix/agent/dj_cohost.py:55,339] |
| `numpy` | 2.4.4 | Ring buffer math + resample int16 | Already shipped [VERIFIED: src/vibemix/audio/buffers.py] |
| `scipy` | 1.17.1 | `resample_poly` for 48kHz→16kHz mic | Already shipped — same path as v4:2290 [VERIFIED: cohost_v4.py:2290] |
| `sounddevice` | 0.5.5 | Mic InputStream (existing) | Already shipped [VERIFIED: src/vibemix/platform/_audio_macos.py:357] |

### Supporting (subprocess CLIs — already on Mac)
| Binary | Version | Purpose | When to Use |
|--------|---------|---------|-------------|
| `ffmpeg` | 8.0.1 | Decode 18s window from track file @ position+3s lookahead | Lookahead Part assembly; `-ss` before `-i` for fast input seek [VERIFIED: which ffmpeg → /opt/homebrew/bin/ffmpeg] |
| `nowplaying-cli` | (Homebrew) | Get current playing title + elapsedTime + playbackRate | Lookahead position resolution [VERIFIED: which nowplaying-cli → /opt/homebrew/bin/nowplaying-cli; returned "Circles" on test poll] |
| `mdfind` | (macOS stdlib) | Spotlight search for track file path by title | Lookahead file resolution; `/usr/bin/mdfind` always present on macOS [VERIFIED: which mdfind → /usr/bin/mdfind] |
| `gpg` | (will be installed by Kaan) | ed25519 GPG key generation for security@bravoh.com | One-off Kaan-side; not a runtime dep [CITED: standard `gpg --quick-gen-key` ed25519 flow] |
| Tauri CLI | latest | `tauri signer generate` for ed25519 updater key | Already-installed dev dep [CITED: tauri/src-tauri/tauri.conf.json5:137 comment shows prior 2026-05-13 generation] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `AudioBuffer(12.0, 16000)` as mic ring | New `MicAudioRing` class | v4 uses the existing `AudioBuffer` class verbatim — extra class adds API surface without behavior change. **Recommend reuse `AudioBuffer`** — CONTEXT.md `MicAudioRing` name is OK if it's just `class MicAudioRing(AudioBuffer): pass` (rename for clarity), but a new identical class is anti-DRY [VERIFIED: cohost_v4.py:2257 — `mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)`]. |
| ffmpeg `-f wav` output | `-f s16le` raw PCM | s16le is 44 bytes smaller and one parse step faster, but `audio/wav` is the de-facto Gemini ingress format already used everywhere else in `dj_cohost.py`. **Recommend `-f wav`** [VERIFIED: cohost_v4_tr.py:754]. |
| 3-Part contract (CONTEXT.md) | 2-Part swap contract (v4 actual) | Swap = byte-identical to ear-tested v4; append = strictly more info but unvalidated. **Defer to plan-phase decision; document both** [VERIFIED: cohost_v4.py:1790 `music_wav = lookahead_wav if lookahead_wav else audio_wav`]. |

**Installation:** All deps already present. Zero new package installs.

**Version verification:**
```bash
ffmpeg -version | head -1          # → ffmpeg version 8.0.1
nowplaying-cli get title           # → Circles (or current track)
which mdfind                       # → /usr/bin/mdfind
python3 --version                  # → Python 3.14.5
```
All four [VERIFIED: Bash output 2026-05-16].

## Project Constraints (from CLAUDE.md)

- **Gemini-only AI** — no other LLM providers. Mic + lookahead Parts route to `genai.Client`, not OpenAI / Anthropic [VERIFIED: project CLAUDE.md "Gemini only (Pro = deep work, Flash = search/grounding)"].
- **POC files are BYTE-IDENTICAL reference** — do NOT modify `cohost_v4.py` / `cohost_v4_tr.py`; lift FROM them [VERIFIED: project CLAUDE.md "POC = Reference, Devour It"; Phase 37 immutability gate].
- **v4 = canonical baseline** (supersedes v3) [VERIFIED: project CLAUDE.md `Memory: project_v4_canonical_baseline`].
- **"Trust the audio" anti-hallucination rule** — preserve verbatim in 2-Part / 3-Part prompt template [VERIFIED: project CLAUDE.md and CONTEXT.md §Anti-Hallucination Hardening].
- **GSD Workflow Enforcement** — Phase 40 work MUST go through `/gsd-execute-phase` (not direct edits) [VERIFIED: project CLAUDE.md].
- **No scope creep — clean utility only** — no stem separation, no CLAP, no enterprise features [VERIFIED: CLAUDE.md + memory `feedback_no_scope_creep_clean_utility`].
- **One-click install is HARD requirement** — BlackHole probe must surface the right CTA on fresh Mac without manual config [VERIFIED: CLAUDE.md memory `project_one_click_install_hard_req`].
- **Privacy rule narrow — full Mac access otherwise** — log paths off-limits, everything else fine. Phase 40 touches no logs/sessions [VERIFIED: project CLAUDE.md].

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIO-01 | Mic as 2nd Gemini multimodal Part — `mic_audio_buf` (12s ring) attached when KAAN_SPOKE fires | v4:1791-1813 architecture mapped; mic ring = `AudioBuffer(12.0, 16000)` resampled from 48kHz native; AI-silence zero-fill prevents self-loop; integration point = `dj_cohost.py:332-342` |
| AUDIO-02 | 3s file-based source-track lookahead pipeline (ffmpeg + mdfind + nowplaying-cli) | v4_tr:624-770 `LookaheadProvider` verbatim port; ffmpeg/nowplaying-cli/mdfind all VERIFIED present on this Mac; v4_tr semantics = REPLACE Part 1 (not append) — plan must reconcile with CONTEXT.md's 3-Part contract |
| AUDIO-03 | Event cooldowns re-tuned to v4 chat-tested values (10/10/14/45/5) | `src/vibemix/audio/constants.py:54-90` holds the current dict (18/16/20/70/6); single-file change; replay harness extension validates measured gaps |
| AUDIO-04 | Prompt template documents the 3-Part contract (mix / mic / lookahead) | v4:1791-1805 contains the literal `TWO AUDIO PARTS ATTACHED` text — adapt to 3-Part contract from CONTEXT; preserve "your ears are the judge" anti-slop framing |
| AUDIO-05 | PGP key for security@bravoh.com published; SECURITY.md updated | Current state: placeholder at SECURITY.md:29,39 (`KAAN-PGP-PLACEHOLDER.asc` / `PLACEHOLDER-FINGERPRINT-NOT-REAL`). Engineering scope: commit real public key armor + fingerprint + drop placeholder file |
| AUDIO-06 | Tauri ed25519 updater key rotated to production | Current state: `tauri.conf.json5:153` has the 2026-05-13 dev key (Phase 18 comment confirms). Engineering scope: pubkey rotation + `release.yml` CI verification (uses GH secret `TAURI_UPDATER_PRIVATE_KEY`) |
| AUDIO-07 | BlackHole probe fresh-Mac smoke pass | Current state: `blackhole_probe.py` returns `{installed: bool, device_name: str|None}` — no telemetry events. Engineering scope: add structured-event emission `audio.probe.{detected,missing,cta_fired}` to wizard IPC bus |

## Architecture Patterns

### System Architecture Diagram

```
                                  ┌─────────────────────────────┐
                                  │  sounddevice mic InputStream│  (48kHz mono float32, existing)
                                  │  → _mic_callback_factory()  │
                                  └────────────┬────────────────┘
                                               │
                                               ▼
                       ┌───────────────────────┴────────────────────────┐
                       │  Two side-effects per callback:                │
                       │   (a) mic.push(mono_f) → Levels.update_mic     │  (existing)
                       │   (b) resample_poly 48→16k, zero-if-AI-talks,  │  ← NEW (AUDIO-01)
                       │       int16 clip, mic_audio_buf.push(pcm16)    │
                       └───────────────────────┬────────────────────────┘
                                               │
              ┌────────────────────────────────┼─────────────────────────────────┐
              │                                │                                 │
              ▼                                ▼                                 ▼
    ┌──────────────────┐         ┌──────────────────────┐         ┌─────────────────────┐
    │ clean_audio_buf  │         │ mic_audio_buf        │         │ LookaheadProvider   │
    │ AudioBuffer 23s  │         │ AudioBuffer 12s @16k │         │ nowplaying-cli      │  ← NEW (AUDIO-02)
    │ @16k (existing)  │         │ (NEW)                │         │ + mdfind + ffmpeg   │
    └────────┬─────────┘         └──────────┬───────────┘         └──────────┬──────────┘
             │                              │                                │
             │ snapshot_wav(audio_seconds)  │ snapshot_wav(8.0)              │ snapshot_wav() → bytes|None
             ▼                              ▼                                ▼
    ┌──────────────────────────────────────────────────────────────────────────────────┐
    │  DJCoHostAgent.llm_node — contents = [text_prompt, music_part,                   │  ← MODIFIED
    │                                       mic_part?, lookahead_part? OR swap?]      │     (AUDIO-04)
    │  Routes to genai_client.aio.models.generate_content_stream(...)                   │
    └────────────────────────────────────────┬─────────────────────────────────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │  EventDetector (existing)    │
                              │  reads MIN_EVENT_GAP_PER_TYPE│  ← REDUCED (AUDIO-03)
                              │  from audio/constants.py     │     PHASE 18→10, etc.
                              └──────────────────────────────┘

                              ┌──────────────────────────────┐
                              │  scripts/eval/replay_harness │  ← EXTENDED (AUDIO-03 validation)
                              │  --print-cooldowns mode      │     measures inter-event gaps
                              └──────────────────────────────┘
```

### Recommended Project Structure (deltas only)
```
src/vibemix/
├── audio/
│   ├── buffers.py         # MODIFY: no change OR add MicAudioRing alias of AudioBuffer
│   ├── constants.py       # MODIFY: MIN_EVENT_GAP_PER_TYPE re-tuned values + new mic/lookahead constants
│   ├── lookahead.py       # NEW: port of cohost_v4_tr.py:624-770 LookaheadProvider
│   └── __init__.py        # MODIFY: re-export LookaheadProvider
├── agent/
│   └── dj_cohost.py       # MODIFY (~25 lines): contents = [...] block at line 332-342 picks up mic + lookahead Parts
├── install/
│   └── blackhole_probe.py # MODIFY (+10 lines): emit structured probe.{detected,missing,cta_fired} events
├── __main__.py            # MODIFY: instantiate mic_audio_buf + LookaheadProvider, wire into _mic_callback_factory + DJCoHostAgent kwargs
docs/security/
└── pgp-public-key.txt     # NEW (AUDIO-05): ASCII-armored public key block
scripts/eval/
└── replay_harness.py      # MODIFY: add --print-cooldowns flag + measured-gap report
tauri/src-tauri/
└── tauri.conf.json5       # MODIFY (AUDIO-06): pubkey rotation
SECURITY.md                 # MODIFY (AUDIO-05): real fingerprint, drop placeholder line
```

### Pattern 1: Mic-resample-and-mute-during-AI callback extension
**What:** Extend existing `_mic_callback_factory(mic)` to also produce 16kHz int16 PCM for the Gemini Part ring. Zero-fill when AI is talking to prevent the AI's own voice (leaked through the speakers into the mic) from being heard as Kaan's voice.
**When to use:** Always — only path that prevents self-triggered KAAN_SPOKE loops.
**Example:**
```python
# Source: cohost_v4.py:2278-2296
def callback(indata, frames, time_info, status):
    if status:
        print(f"[mic status] {status}", file=sys.stderr)
    mono = indata[:, 0] if indata.ndim > 1 else indata
    mono_f = mono.astype(np.float32)
    mic.push(mono_f)                            # existing — Levels.update_mic side-effect
    # NEW — resample 48k → 16k and push to mic_audio_buf so Gemini can
    # hear Kaan's literal words (not just the KAAN_SPOKE signal).
    # CRITICAL: zero-fill while AI is talking — else AI's voice leaks back
    # through the speakers → mic → mic_audio_buf and Gemini hears the AI
    # as Kaan (self-triggered KAAN_SPOKE loop).
    try:
        mic16 = resample_poly(mono_f, INPUT_SR_TARGET, INPUT_SR_NATIVE)
        if mic.ai_is_active():                  # uses existing MicBuffer flag
            mic16 = np.zeros_like(mic16)
        pcm16 = np.clip(mic16 * 32767.0, -32768, 32767).astype(np.int16)
        mic_audio_buf.push(pcm16)
    except Exception:
        pass                                    # never crash the audio callback
```

### Pattern 2: Lookahead Part attachment in llm_node
**What:** Three-step pipeline in `DJCoHostAgent.llm_node` before assembling `contents = [...]`:
1. Take `audio_wav` snapshot (existing — Part 1 baseline).
2. Take `mic_wav = mic_audio_buf.snapshot_wav(8.0)` if `KAAN_SPOKE`-recent AND mic ring has signal.
3. Call `lookahead_wav, lookahead_meta = self._lookahead.snapshot_wav()` (returns `(None, meta)` on streaming sources).
4. Assemble Parts: Part 1 = `audio_wav` (always); append `mic_wav` and `lookahead_wav` Parts where present.

**When to use:** Every `llm_node` invocation. Mic gate runs first (KAAN_SPOKE-recent + has-signal); lookahead runs unconditionally and skips silently on `None`.

**Example:**
```python
# Source: cohost_v4.py:1727-1813 (combined with v4_tr LookaheadProvider call)
audio_wav = snapshot_wav(self._clean_audio_buf, audio_seconds)
mic_wav: bytes | None = None
if MIC_ENABLED and kaan_spoke_recent:
    mic_wav = snapshot_wav(self._mic_audio_buf, 8.0)
lookahead_wav, lookahead_meta = (None, {})
if self._lookahead is not None:
    try:
        lookahead_wav, lookahead_meta = self._lookahead.snapshot_wav()
    except Exception as e:
        print(f"[lookahead err] {e}", file=sys.stderr)

contents: list = [text_prompt + parts_desc, types.Part.from_bytes(data=audio_wav, mime_type="audio/wav")]
if mic_wav:
    contents.append(types.Part.from_bytes(data=mic_wav, mime_type="audio/wav"))
if lookahead_wav:
    contents.append(types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav"))
```

### Pattern 3: ffmpeg input-seek for fast lookahead extraction
**What:** Put `-ss <seek_seconds>` **before `-i <path>`**. This makes ffmpeg seek by container index (file-position math, no decode) rather than decode-then-discard.
**When to use:** Every lookahead snapshot. ~270ms wall-clock per 18s extract on local SSD.
**Example:**
```python
# Source: cohost_v4_tr.py:747-755
proc = subprocess.run(
    [self._ffmpeg, "-loglevel", "error",
     "-ss", f"{seek:.3f}",       # ← BEFORE -i: fast input seek
     "-i", path,
     "-t", f"{duration:.3f}",
     "-ac", "1",                 # mono
     "-ar", "16000",             # 16kHz (matches Part 1 sample rate)
     "-f", "wav",                # WAV container (audio/wav mime)
     "-y", "pipe:1"],
    capture_output=True, timeout=4.0,
)
```

### Pattern 4: Subprocess graceful-degrade on missing local file
**What:** `LookaheadProvider.snapshot_wav()` returns `(None, meta)` on every failure path (no nowplaying, no file match, ffmpeg error, timeout). Caller branches on `if lookahead_wav:` — never on exceptions.
**When to use:** Streaming-only sessions (Spotify Connect / SoundCloud); the title isn't on disk; `mdfind` returns empty.
**Example:**
```python
# Source: cohost_v4_tr.py:721-770
def snapshot_wav(self) -> tuple[bytes | None, dict]:
    meta = {"ok": False, "reason": "init", ...}
    title, pos, rate = self._current_position()
    if not title or pos is None:
        meta["reason"] = "no nowplaying"
        return (None, meta)
    path = self._resolve_file(title)
    if not path or not os.path.exists(path):
        meta["reason"] = "no file"
        return (None, meta)
    # ... ffmpeg call ...
    # All exception paths populate meta["reason"] + return (None, meta)
```

### Anti-Patterns to Avoid
- **Synchronous ffmpeg call on audio thread:** Don't. `subprocess.run(timeout=4.0)` is fine in `llm_node` (async coroutine context) but MUST never run inside the sounddevice callback.
- **`-ss` after `-i` (output seek):** Decodes the entire file up to the seek point. 100× slower than input-seek for late-track positions. v4_tr correctly uses input-seek; preserve.
- **Mic resampling without AI-talk zero-fill:** The AI's voice plays out the speakers, the mic picks it up, you push that to `mic_audio_buf`, Gemini hears "Kaan" saying what the AI just said. Self-triggered KAAN_SPOKE loop. The `if mic.ai_is_active(): mic16 = np.zeros_like(mic16)` line is **load-bearing IP**.
- **Re-allocating mic ring per push:** Use the existing `AudioBuffer` zero-alloc-on-push primitive (the np.concatenate bug was fixed at Phase 2). New `MicAudioRing` class must follow same pre-allocated pattern.
- **Lookahead Part labeled as "future" in prompt:** v4 deliberately does NOT tell Gemini the lookahead is future audio. The note at v4:1788 explicitly says "AI is NEVER told about the offset — to AI, this Part is just 'djay master, playing now'." This hides the LLM+TTS latency without the AI making up "I predict you'll drop here" comments. CONTEXT.md's "NOT YET HEARD BY AUDIENCE" label DEVIATES from this — recommend planner re-decides (silent offset vs explicit label).
- **Hard-coded cooldown numbers in EventDetector:** Already lifted to constants dict in Phase 3 — keep the single-source-of-truth dict, don't scatter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mic 48k→16k resample | Custom polyphase filter | `scipy.signal.resample_poly` | Already used in `cohost_v4.py:2290`; one allocation per call; correct for 48000/16000 ratio (gcd=16000, up=1, down=3) |
| Now-playing metadata | `pyobjc-MediaPlayer` wrap | `nowplaying-cli get-raw` subprocess | Already installed via Homebrew; battle-tested; same path as `track_macos.py` |
| Spotlight track-file search | `pyobjc-CoreSpotlight` wrap | `mdfind -name "<title>"` subprocess | macOS stdlib; zero install footprint; v4_tr verified flow |
| Audio decode + resample to 16kHz mono PCM | librosa/audioread/ffmpeg-python | Direct `ffmpeg` subprocess with `-ar 16000 -ac 1 -f wav` | Single binary, no pip dep, deterministic output bytes |
| GPG ed25519 key generation | Custom `cryptography.hazmat.primitives.asymmetric.ed25519` | `gpg --quick-gen-key 'Bravoh Security <security@bravoh.com>' ed25519 default 0` | Standard tooling; produces keyring entry directly publishable via `gpg --send-keys --keyserver hpkps://keys.openpgp.org` |
| Tauri ed25519 updater key | Custom minisign integration | `npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key` | Already in tauri.conf.json5 generation comment; matches the existing pubkey format |
| Subprocess timeout handling | Polling loop on Popen | `subprocess.run(..., timeout=4.0)` with TimeoutExpired catch | v4_tr verbatim; raises clean exception caught by graceful-degrade |

**Key insight:** Every external dep already has a battle-tested subprocess wrapper in the POC. The only NEW code is the bookkeeping that calls them.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — phase ports code only; no DB schema changes; no Mem0/Chroma/SQLite migration | None |
| Live service config | `tauri.conf.json5:153` pubkey is dev key (2026-05-13) — needs production-key rotation in commit | Code edit + GH secret `TAURI_UPDATER_PRIVATE_KEY` re-set via `gh secret set` |
| OS-registered state | None — no Task Scheduler / launchd / systemd unit involved | None |
| Secrets/env vars | `GEMINI_API_KEY` (existing, no change); `TAURI_UPDATER_PRIVATE_KEY` GH secret (rotate to match new pubkey); `KAAN-PGP-PLACEHOLDER.asc` placeholder file in repo root needs deletion | (a) `gh secret set TAURI_UPDATER_PRIVATE_KEY` after `tauri signer generate`; (b) `git rm KAAN-PGP-PLACEHOLDER.asc` |
| Build artifacts | None — no compiled binaries depend on the renamed/changed surfaces; egg-info N/A (no pyproject rename) | None |

**Nothing found in category:** Stored data, OS-registered state, Build artifacts — confirmed by code inspection.

## Common Pitfalls

### Pitfall 1: Self-triggered KAAN_SPOKE loop
**What goes wrong:** AI starts speaking → AI voice plays out speakers → mic picks it up → mic ring fills with AI audio → Gemini sees mic Part with speech-shaped energy → next `llm_node` call treats it as Kaan speaking → infinite loop.
**Why it happens:** Without zero-fill while AI is talking, the mic ring is indistinguishable from Kaan's actual voice. KAAN_SPOKE detection at level-RMS layer wouldn't catch it because the feedback-suppression is timed to PlaybackQueue, not to mic-ring contents.
**How to avoid:** `if mic.ai_is_active(): mic16 = np.zeros_like(mic16)` before push to mic_audio_buf. Use the existing `MicBuffer.ai_is_active()` method (added by Phase 2 — exists at `src/vibemix/audio/buffers.py:495`).
**Warning signs:** Multiple consecutive KAAN_SPOKE events within 3-5 second window; AI saying "I heard you say X" where X is what the AI just said.

### Pitfall 2: nowplaying-cli stale data on app switch
**What goes wrong:** Kaan switches from djay Pro to Spotify briefly, the `nowplaying-cli get-raw` cache stays on the previous app's title for ~5-10 seconds, lookahead uses wrong file → silently wrong audio.
**Why it happens:** macOS MediaRemote framework caches the most-recent NowPlaying responder until a new one publishes.
**How to avoid:** v4_tr's title→path cache is per-title (good). Add a sanity gate: if `state.audible_track` (from `MusicState`) disagrees with `nowplaying-cli` title, skip lookahead this cycle. Or: trust v4's existing handling (the `prev_title == title` extrapolation guard at v4_tr:717-719 catches sustained mismatches by NOT extrapolating).
**Warning signs:** Lookahead audio doesn't match what the user is hearing; AI references content from the wrong track.

### Pitfall 3: Cooldown reduction breaking existing tests
**What goes wrong:** Reducing `PHASE` from 18s → 10s changes inter-event spacing. Existing tests in `tests/state/test_event_detector.py` that pin specific gap values fail.
**Why it happens:** Cooldown values are imported from `MIN_EVENT_GAP_PER_TYPE` constant — tests likely assert against this dict directly.
**How to avoid:** Search `tests/` for `MIN_EVENT_GAP_PER_TYPE`, `cooldown`, and the specific number literals (18.0, 16.0, 20.0, 70.0, 6.0); update each pin to new value. Don't add a compat shim — the change is the point.
**Warning signs:** Test failures in `tests/state/test_event_detector.py`, `tests/audio/test_constants.py`, `tests/state/test_phase17_constants.py`.

### Pitfall 4: ffmpeg "moov atom not found" on partial-download .m4a
**What goes wrong:** Tracks streamed from Apple Music / iTunes Match may have placeholder .m4a files with the moov atom at the end (not the front). `-ss` before `-i` fails because ffmpeg can't seek without the moov atom.
**Why it happens:** Standard mp4 streaming layout puts moov at end; offline-optimized files have it at front (faststart).
**How to avoid:** Catch ffmpeg's non-zero returncode + non-empty stderr → log `meta["reason"] = "moov not found"` → return `(None, meta)` → fall back to non-lookahead path. v4_tr already does this generically (catches all ffmpeg errors); confirm the metadata path is logged so we can spot the pattern.
**Warning signs:** stderr from ffmpeg containing `moov atom not found` or `Invalid data found when processing input` for specific tracks.

### Pitfall 5: BlackHole probe race on fresh boot
**What goes wrong:** Sidecar starts before CoreAudio has finished enumerating devices on a fresh boot. `sd.query_devices()` returns the partial list without BlackHole even though it IS installed.
**Why it happens:** macOS CoreAudio device enumeration is async on boot; PortAudio caches the first response.
**How to avoid:** When `probe_blackhole()` returns `installed=False`, retry once after a 1.5-second sleep BEFORE emitting `audio.probe.missing` and firing the install CTA. This is the same race that bit Phase 33-04; verify the retry is in.
**Warning signs:** Wizard CTA fires on a Mac that has BlackHole installed; second probe call (post-CTA dismissal) returns `installed=True`.

### Pitfall 6: tauri.conf.json5 pubkey check-comment trip
**What goes wrong:** `release.yml` CI gates on a placeholder-sentinel substring in the pubkey value (per Phase 18 Plan 18-05). Replacing the pubkey with the production key without also updating the gate-check value or removing the placeholder reference fails CI.
**Why it happens:** The Phase 18 comment at `tauri.conf.json5:141-142` says "Plan 18-05's release.yml gates on the literal placeholder sentinel string in the pubkey VALUE — this comment no longer trips it." Need to verify the gate doesn't FIRE-ON-NON-PLACEHOLDER (i.e. doesn't fail when prod key is present).
**How to avoid:** Read `.github/workflows/release.yml` 18-05 wave for the exact gate check; ensure production key passes; remove the placeholder mention from the comment block to keep grep-clean.
**Warning signs:** `release.yml` job "verify_tauri_pubkey" or similar failing on first key-rotation run.

## Code Examples

Verified patterns from POC source — port near-verbatim:

### Mic resampling + zero-on-AI in audio callback (AUDIO-01)
```python
# Source: cohost_v4.py:2278-2296 (mic_callback inner closure inside main)
# Adapted for src/vibemix/__main__.py:_mic_callback_factory pattern.

def _mic_callback_factory(mic: MicBuffer, mic_audio_buf: AudioBuffer):
    """Phase 40 — extends v2.1 _mic_callback_factory with a 2nd ring push
    for the Gemini mic Part. Zero-fills 16kHz output while AI is talking
    to prevent self-triggered KAAN_SPOKE loops (v4:2286-2288 comment).
    """
    def callback(indata, frames, time_info, status):
        if status:
            print(f"[mic status] {status}", file=sys.stderr)
        mono = indata[:, 0] if indata.ndim > 1 else indata
        mono_f = mono.astype(np.float32)
        mic.push(mono_f)  # existing — Levels.update_mic side-effect
        try:
            mic16 = resample_poly(mono_f, INPUT_SR_TARGET, INPUT_SR_NATIVE)
            if mic.ai_is_active():
                mic16 = np.zeros_like(mic16)
            pcm16 = np.clip(mic16 * 32767.0, -32768, 32767).astype(np.int16)
            mic_audio_buf.push(pcm16)
        except Exception:
            pass  # never crash the audio callback
    return callback
```

### LookaheadProvider port (AUDIO-02 — verbatim from cohost_v4_tr.py:624-770)
```python
# Source: cohost_v4_tr.py:624-770
# New file: src/vibemix/audio/lookahead.py
# Only adaptation: typing, logging via project logger pattern, absolute paths.

import json
import os
import shutil
import subprocess
import threading
import time

from vibemix.audio.constants import INPUT_SR_TARGET  # 16000

LOOKAHEAD_SECONDS = 3.0       # window END this far ahead — LLM+TTS latency offset
LOOKAHEAD_WINDOW_SECONDS = 18.0  # total window length (15s past context + 3s future)
LOOKAHEAD_SAMPLE_RATE = INPUT_SR_TARGET


class LookaheadProvider:
    """Peeks N seconds ahead into the audio file currently playing in djay Pro."""
    _AUDIO_EXTS = (".mp3", ".m4a", ".aiff", ".aif", ".wav", ".flac", ".ogg", ".aac")

    def __init__(self, lookahead_sec=LOOKAHEAD_SECONDS,
                 window_sec=LOOKAHEAD_WINDOW_SECONDS,
                 sample_rate=LOOKAHEAD_SAMPLE_RATE):
        self.lookahead_sec = lookahead_sec
        self.window_sec = window_sec
        self.sample_rate = sample_rate
        self._cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"
        self._ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self._title_to_path: dict[str, str | None] = {}
        self._last_raw: dict | None = None
        self._last_raw_wall: float = 0.0
        self._lock = threading.Lock()

    # ... _poll_raw / _resolve_file / _current_position / snapshot_wav verbatim ...
```

### Updated cooldown table (AUDIO-03 — modify src/vibemix/audio/constants.py)
```python
# Source: cohost_v4.py:134-142 (the chat-tested values, NOT the literal v4 file)
# Replaces lines 54-90 of src/vibemix/audio/constants.py.

MIN_EVENT_GAP_PER_TYPE: dict[str, float] = {
    "TRACK_CHANGE": 5.0,     # was 6.0 — v4 chat-tested baseline 2026-05-11
    "PHASE": 10.0,           # was 18.0 — v4 chat-tested baseline 2026-05-11
    "LAYER_ARRIVAL": 10.0,   # was 16.0 — v4 chat-tested baseline 2026-05-11
    "MIX_MOVE": 14.0,        # was 20.0 — v4 chat-tested baseline 2026-05-11
    "HEARTBEAT": 45.0,       # was 70.0 — v4 chat-tested baseline 2026-05-11
    "MIC": 3.0,              # unchanged
    "MANUAL": 1.5,           # unchanged
    # Phase 17 SENSE-12 — kick-side cross-genre detectors (unchanged)
    "KICK_SWAP": 14.0,
    "SUB_LAYER_ARRIVAL": 16.0,
    "KICK_DENSITY_SHIFT": 18.0,
    "BREAKDOWN_KICK_KILL": 20.0,
    "REENTRY_KICK_LAND": 12.0,
    "PHRASE_BOUNDARY": 24.0,
    "DISTORTION_CLIMB": 6.0,
    "ACID_LINE_ENTRY": 8.0,
}

# HEARTBEAT_SEC also reduced — keep it in sync
HEARTBEAT_SEC = 45.0  # was 70.0 — v4 chat-tested baseline
```

### Replay harness `--print-cooldowns` mode (AUDIO-03 validation)
```python
# Modify scripts/eval/replay_harness.py argparse + main loop.

parser.add_argument(
    "--print-cooldowns",
    action="store_true",
    help="Emit measured inter-event gaps per type to stderr; compare to MIN_EVENT_GAP_PER_TYPE.",
)

# In the main session-replay loop, after each Event fire:
if args.print_cooldowns:
    measured_gaps[ev.type].append(now - last_per_type_at.get(ev.type, now))
    last_per_type_at[ev.type] = now

# After all sessions:
if args.print_cooldowns:
    for ev_type, gaps in measured_gaps.items():
        if not gaps:
            continue
        median = sorted(gaps)[len(gaps) // 2]
        expected = MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
        delta = median - expected
        print(f"  {ev_type:24s} median_gap={median:6.2f}s "
              f"expected_min={expected:5.2f}s  delta={delta:+5.2f}s",
              file=sys.stderr)
        if abs(delta) > 1.0:
            # CI gate per CONTEXT.md §Replay harness validation: measured ±1s
            print(f"    WARNING: {ev_type} measured gap outside ±1s of locked value", file=sys.stderr)
```

### Tauri ed25519 key rotation procedure (AUDIO-06)
```bash
# Source: tauri.conf.json5:137 generation runbook (re-applied for prod key).
#
# 1. Generate new keypair locally
npx @tauri-apps/cli signer generate \
    -w ~/.tauri/vibemix_updater_prod.key \
    --no-password   # Tauri CI signing tolerates passwordless; matches Phase 18 setup

# 2. Read public half and copy into tauri.conf.json5
cat ~/.tauri/vibemix_updater_prod.key.pub
# → paste into tauri/src-tauri/tauri.conf.json5 plugins.updater.pubkey

# 3. Base64-encode private half and store as GH secret
base64 -i ~/.tauri/vibemix_updater_prod.key | gh secret set TAURI_UPDATER_PRIVATE_KEY

# 4. Verify release.yml CI rehearsal accepts the new key
gh workflow run release.yml --ref main \
    -f rehearsal=true   # if the workflow has a dispatch input
```

### PGP key generation + publish (AUDIO-05)
```bash
# Source: standard GPG ed25519 flow + keys.openpgp.org documented upload path.
#
# 1. Generate ed25519 key (no passphrase for OSS security@ inbox key)
gpg --quick-gen-key 'Bravoh Security <security@bravoh.com>' ed25519 default 0

# 2. Get the fingerprint
gpg --list-keys security@bravoh.com
# FINGERPRINT line — copy this into SECURITY.md

# 3. Export public key armor
gpg --armor --export security@bravoh.com > docs/security/pgp-public-key.txt

# 4. Publish to keys.openpgp.org (HKPS submission requires email-verify)
gpg --send-keys --keyserver hkps://keys.openpgp.org <FINGERPRINT>
# → keys.openpgp.org sends verification email to security@bravoh.com
# → click verification link to make the key searchable by email

# 5. Update SECURITY.md
# - Replace KAAN-PGP-PLACEHOLDER.asc reference with docs/security/pgp-public-key.txt
# - Replace PLACEHOLDER-FINGERPRINT-NOT-REAL with real fingerprint
# - Add hkps://keys.openpgp.org lookup hint
git rm KAAN-PGP-PLACEHOLDER.asc
```

### BlackHole probe structured-event extension (AUDIO-07)
```python
# Modify src/vibemix/install/blackhole_probe.py
# Add emit_event parameter + emit-on-state-transition.

def probe_blackhole(emit_event: Callable[[str, dict], None] | None = None) -> BlackHoleProbeResult:
    devices = _query_devices()
    matches = [d for d in devices if "BlackHole" in d.get("name", "")]
    result = {
        "installed": bool(matches),
        "device_name": matches[0]["name"] if matches else None,
    }
    if emit_event is not None:
        emit_event(
            "audio.probe.detected" if result["installed"] else "audio.probe.missing",
            {"device_name": result["device_name"]},
        )
    return result


# CTA-fired event emitted from the wizard layer when user clicks "Install BlackHole":
# emit_event("audio.probe.cta_fired", {"cta": "blackhole_install_link_opened"})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| KAAN_SPOKE as signal-only (event without payload) | KAAN_SPOKE + literal mic audio Part attached | Phase 40 (v3.0) | Gemini can answer in-context to what Kaan SAID, not just react to the fact he spoke |
| Past-only audio Part to LLM | Past + 3s-future via local-file lookahead | Phase 40 (v3.0) | LLM/TTS latency masked — reactions land timed to the moment they describe |
| Cooldowns at v3-era values (18/16/20/70/6) | v4 chat-tested values (10/10/14/45/5) | Phase 40 (v3.0) | More reactive co-host without slop; matches "harikaydı" baseline |
| `KAAN-PGP-PLACEHOLDER.asc` + fake fingerprint | Real ed25519 GPG key published to keys.openpgp.org | Phase 40 (v3.0) | SECURITY.md becomes actually usable for vuln reports |
| `tauri.conf.json5` dev key (2026-05-13) | Production ed25519 updater key | Phase 40 (v3.0) | Auto-update path signs/verifies against the key Kaan controls long-term |
| `blackhole_probe` returns dict, wizard polls | Probe emits `audio.probe.{detected,missing,cta_fired}` IPC events | Phase 40 (v3.0) | Telemetry-grade install-funnel diagnostics; CTA-fire visibility |

**Deprecated/outdated:**
- The 3-Part contract literal description in CONTEXT.md §Audio Plumbing — v4 actually does 2-Part swap. Resolve at plan-phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CONTEXT.md "3-Part contract" is the desired semantic (vs v4's swap) | Architecture Patterns + Pitfalls | If user actually wants v4-verbatim swap, the prompt template + Part assembly logic diverge. Recommend planner picks one explicitly; defer to discuss-phase if ambiguous. | [ASSUMED]
| A2 | `gpg --quick-gen-key ed25519 default 0` with no passphrase is acceptable for security@bravoh.com inbox key | Code Examples — PGP | If Kaan wants a passphrase-protected key + gpg-agent caching, the runbook is +2 lines. Cosmetic; no blocker. | [ASSUMED]
| A3 | `release.yml` Plan 18-05 placeholder-sentinel CI gate accepts non-placeholder pubkey | Pitfall 6 | If the gate is "fail unless value matches X placeholder", rotating to prod key fails CI. Need to read release.yml verify_tauri_pubkey step. | [ASSUMED]
| A4 | The "harikaydı" cooldown values (10/10/14/45/5) are what Kaan validated in the 2026-05-11 chat-tested session — not a different combination | AUDIO-03 | If the chat-test used different numbers, replay harness validation reports "outside ±1s" and Phase 40 fails the gate. Source: project memory `project_v4_canonical_baseline` cites "tuned event cooldowns from real DJ session 2026-05-11" but doesn't dump the exact numbers. CONTEXT.md asserts these specific values. | [ASSUMED] |
| A5 | Existing test suite contains pins on the old cooldown values (18/16/20/70/6) that must be updated | Pitfall 3 | If tests don't pin these values, the cooldown update is even smaller. Need to grep tests/state/, tests/audio/. | [ASSUMED] |
| A6 | The "AI NEVER told about lookahead offset" anti-slop principle (v4:1788) should override CONTEXT.md's "NOT YET HEARD BY AUDIENCE" labeling | Anti-Patterns + Pitfalls | If the explicit label is what users want, the prompt template gains the label and we lose the v4 ear-test seal. Recommend planner re-decides; not a blocker either way. | [ASSUMED] |

## Open Questions

1. **3-Part contract (CONTEXT.md) vs 2-Part swap (v4 actual)?**
   - What we know: v4:1790 does `music_wav = lookahead_wav if lookahead_wav else audio_wav` — swap semantics.
   - What's unclear: CONTEXT.md says always-Part-1 + optional-mic + optional-lookahead — strict additive.
   - Recommendation: Plan-phase or discuss-phase confirms with Kaan. Both are 2-day diffs; default to v4-verbatim if no preference signal.

2. **Lookahead prompt labeling: silent offset (v4) or explicit "future audio" (CONTEXT)?**
   - What we know: v4:1788 explicitly hides the offset to prevent AI from making prediction-shaped commentary.
   - What's unclear: CONTEXT.md prefers transparency. Possibly a deliberate behavior change.
   - Recommendation: Default to v4 silent-offset; treat the label as an opt-in for the explicit-mode prompt template if A/B testing is desired.

3. **Should `LookaheadProvider` be singleton or per-session?**
   - What we know: CONTEXT.md §Claude's Discretion explicitly punts this.
   - What's unclear: `DJCoHostAgent` is per-session; `LookaheadProvider` has a per-instance `_title_to_path` cache that grows over a long set.
   - Recommendation: Per-session (instantiated in `__main__.py` alongside the agent, passed in as constructor kwarg). Matches existing `clean_audio_buf` / `recorder` lifecycle.

4. **Where does `audio.probe.*` IPC event sink land?**
   - What we know: No telemetry sink wired today (`blackhole_probe.py` is pure return-dict).
   - What's unclear: Does Phase 40 stand up the sink, or just emit-or-log?
   - Recommendation: Local log (sidecar stdout) + structured `events.jsonl` write via existing `VoiceRecorder.log_event` pattern. Real telemetry pipe-through is post-v3.0 (no upstream dashboard yet).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ffmpeg | LookaheadProvider | ✓ | 8.0.1 | None — feature degrades to "no lookahead" silently |
| nowplaying-cli | LookaheadProvider position resolve | ✓ | (Homebrew) | None — feature degrades to "no lookahead" silently |
| mdfind | LookaheadProvider file resolve | ✓ | macOS stdlib | None — feature degrades to "no lookahead" silently |
| BlackHole 2ch | Existing AUDIO_INPUT path | ✓ (assumed — v2.1 ships requires it) | 2ch | INSTALL-BLACKHOLE-PROBE CTA |
| Tauri CLI | AUDIO-06 key gen | ✓ (assumed — Phase 18 already shipped Tauri) | latest | None — manual `tauri signer generate` is the only path |
| gpg | AUDIO-05 PGP gen | ✓ (assumed — standard macOS dev tool) | (system) | None — Kaan-side action |
| sounddevice / portaudio | mic stream | ✓ | 0.5.5 | N/A — already shipped |
| numpy / scipy | resample_poly | ✓ | 2.4.4 / 1.17.1 | N/A — already shipped |
| google-genai | Gemini Part assembly | ✓ | 2.0.1 | N/A — already shipped |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — every required dep is present.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project standard) |
| Config file | pytest.ini / pyproject.toml (project root — discovered via `tests/` dir presence) |
| Quick run command | `python -m pytest tests/audio/ tests/state/ tests/agent/ -x -q` |
| Full suite command | `python -m pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIO-01 | mic_audio_buf populated with resampled 16kHz int16; zero-filled on AI talk | unit | `pytest tests/audio/test_mic_ring.py -x` | ❌ Wave 0 |
| AUDIO-01 | `contents` list contains a 2nd `Part(audio/wav)` when KAAN_SPOKE-recent | integration | `pytest tests/integration/test_3part_request.py -x` | ❌ Wave 0 |
| AUDIO-02 | `LookaheadProvider.snapshot_wav()` returns valid 18s WAV bytes from a fixture audio file | unit | `pytest tests/audio/test_lookahead.py -x` | ❌ Wave 0 |
| AUDIO-02 | LookaheadProvider returns `(None, meta)` on missing file / ffmpeg error / no nowplaying | unit | `pytest tests/audio/test_lookahead.py::test_graceful_degrade -x` | ❌ Wave 0 |
| AUDIO-02 | `contents` list contains a 3rd `Part(audio/wav)` when lookahead WAV present | integration | `pytest tests/integration/test_3part_request.py::test_3_part_with_lookahead -x` | ❌ Wave 0 |
| AUDIO-03 | `MIN_EVENT_GAP_PER_TYPE` dict values match v4 chat-tested baseline | unit | `pytest tests/audio/test_constants.py -x` | ✅ (update existing) |
| AUDIO-03 | `replay_harness.py --print-cooldowns` reports measured gaps within ±1s of locked values | integration | `python -m scripts.eval.replay_harness --corpus tests/eval/fixtures --judges noop --output /tmp/eval --print-cooldowns` | ✅ (update existing) |
| AUDIO-04 | Prompt template enumerates Parts present in the request (1 / 2 / 3 part scenarios) | unit | `pytest tests/prompts/test_coach_3part.py -x` | ❌ Wave 0 |
| AUDIO-05 | `SECURITY.md` references real fingerprint, NOT `PLACEHOLDER-FINGERPRINT-NOT-REAL`; `docs/security/pgp-public-key.txt` parses as a valid OpenPGP block | unit | `pytest tests/security/test_pgp_published.py -x` | ❌ Wave 0 |
| AUDIO-06 | `tauri.conf.json5` pubkey is non-placeholder and not the dev key | unit | `pytest tests/tauri/test_updater_key_rotated.py -x` | ❌ Wave 0 |
| AUDIO-07 | `probe_blackhole(emit_event=cb)` calls `cb("audio.probe.missing", ...)` when no BlackHole device; `cb("audio.probe.detected", ...)` when present | unit | `pytest tests/install/test_blackhole_probe_events.py -x` | ❌ Wave 0 |
| AUDIO-07 | Wizard end-to-end smoke fires `audio.probe.cta_fired` on user click | integration | manual-only (fresh-Mac Kaan walk) | manual |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/audio/ tests/state/ tests/agent/ tests/integration/test_3part_request.py -x -q` (~30-45s)
- **Per wave merge:** `python -m pytest -x -q` (full suite)
- **Phase gate:** Full suite green + replay harness `--print-cooldowns` shows all 5 gaps within ±1s of locked values, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/audio/test_mic_ring.py` — covers AUDIO-01 ring push + AI-talk zero-fill + snapshot_wav format
- [ ] `tests/audio/test_lookahead.py` — covers AUDIO-02 success path (fixture mp3) + 4 failure paths (no nowplaying, no file, ffmpeg error, timeout)
- [ ] `tests/integration/test_3part_request.py` — mocks `genai_client.aio.models.generate_content_stream`, asserts Part count per scenario
- [ ] `tests/prompts/test_coach_3part.py` — asserts prompt body documents the correct Part count
- [ ] `tests/security/test_pgp_published.py` — asserts SECURITY.md no longer contains `PLACEHOLDER` strings; PGP block parses
- [ ] `tests/tauri/test_updater_key_rotated.py` — asserts pubkey != dev key, base64-decodes as ed25519 (32-byte after minisign header)
- [ ] `tests/install/test_blackhole_probe_events.py` — asserts emit_event callback fired with correct event names on both branches
- [ ] No framework install needed — pytest is the existing standard

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — Phase 40 touches no authn surface |
| V3 Session Management | no | — Phase 40 is pure runtime port |
| V4 Access Control | no | — no new APIs / endpoints |
| V5 Input Validation | yes (light) | Validate `nowplaying-cli` JSON output before use; bound ffmpeg subprocess timeout (4s); never shell-expand untrusted track titles |
| V6 Cryptography | yes (key gen) | Use `gpg --quick-gen-key ed25519` and `tauri signer generate` — both standard tooling, never hand-roll ed25519 |
| V7 Error Handling | yes | All subprocess failures must return `(None, meta_with_reason)` — never raise to caller; never leak file paths to logs that ship |
| V8 Data Protection | yes | TAURI_UPDATER_PRIVATE_KEY in GH secret (existing pattern); no secrets in `tauri.conf.json5` (pubkey only); no secrets in `docs/security/pgp-public-key.txt` (public key only) |
| V10 Malicious Code | yes | Subprocess args use list-form (not shell=True) — already correct in v4_tr port |

### Known Threat Patterns for `subprocess + mdfind + ffmpeg`

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via track title | Tampering | List-form `subprocess.run([cmd, "-name", title])` — no shell expansion. v4_tr is already correct [VERIFIED: cohost_v4_tr.py:670] |
| ffmpeg consuming a maliciously crafted file (CVE chain) | Tampering | Bound 4s timeout + capture stderr; trust ffmpeg's own input validation; never load remote URLs (we only read files mdfind already found by Spotlight index) |
| nowplaying-cli responding with controllable JSON (other-app spoof) | Spoofing | Read only the 3 fields we use (title / elapsedTime / playbackRate); validate `elapsed` is a non-negative float; never `eval()` or `exec()` |
| GH secret leak via `release.yml` echo | Information Disclosure | Existing Phase 18 hygiene — `set +x` around secret use; `secrets.TAURI_UPDATER_PRIVATE_KEY` never logged. No new exposure in Phase 40 |
| Tauri pubkey replaced via tampered PR | Tampering | Branch protection on `main` + Kaan-only PR approval (existing repo policy); minisign verifies installer signature anyway |
| BlackHole probe race exploited to bypass install gate | Bypass | One-shot retry on `installed=False` after 1.5s sleep (Pitfall 5) prevents false-negative; nothing exploitable beyond that |

## Sources

### Primary (HIGH confidence)
- `cohost_v4.py:1727-1820, 2253-2310` — multimodal Part assembly + mic_audio_buf wiring (project file, byte-identical reference per CLAUDE.md)
- `cohost_v4_tr.py:100-152, 624-770, 1690-1770` — LookaheadProvider implementation + invocation site
- `cohost_v4.py:134-142` — v4 cooldown table baseline (note: file shipped with 18/16/20/70/6; chat-tested 10/10/14/45/5 lives in CONTEXT.md + memory `project_v4_canonical_baseline`)
- `src/vibemix/audio/buffers.py` — `AudioBuffer` zero-alloc pattern (reuse for mic ring)
- `src/vibemix/audio/constants.py:54-90` — current `MIN_EVENT_GAP_PER_TYPE` table (target of AUDIO-03)
- `src/vibemix/agent/dj_cohost.py:270-350` — `contents = [...]` assembly point (target of AUDIO-01, AUDIO-02, AUDIO-04)
- `src/vibemix/__main__.py:328-538` — audio stream factories + mic stream wiring
- `src/vibemix/install/blackhole_probe.py` — BlackHole probe (target of AUDIO-07)
- `tauri/src-tauri/tauri.conf.json5:120-160` — updater plugin config (target of AUDIO-06)
- `.github/workflows/release.yml`, `.github/workflows/README.md` — `TAURI_UPDATER_PRIVATE_KEY` CI integration
- `SECURITY.md:1-50` — current PGP placeholder state (target of AUDIO-05)
- `scripts/eval/replay_harness.py:350-401` — argparse extension point for `--print-cooldowns`

### Secondary (MEDIUM confidence)
- Project memory `project_v4_canonical_baseline` — confirms cohost_v4 is canonical + carries the tuned cooldown numbers + "trust the audio" rule
- Project memory `feedback_mic_audio_as_multimodal_part` — confirms mic-as-literal-Part validated in v4 chat tests
- Project memory `project_v4_tr_lookahead` — confirms 3s-ahead file-based pipeline validated in v4_tr chat tests
- `.planning/research/v3-buckets/B-gemini-capabilities.md:153,180,230` — research bucket validating both audio paths for v3 port

### Tertiary (LOW confidence)
- `keys.openpgp.org` upload flow assumed standard `gpg --send-keys --keyserver hpkps://keys.openpgp.org` — only minor risk of UI flow change [CITED: standard OpenPGP submission protocol; not checked live]
- `npx @tauri-apps/cli signer generate -w <path>` flag set assumed unchanged since 2026-05-13 generation [CITED: `tauri.conf.json5:137` runbook comment]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps verified installed, all packages already in `.venv/`
- Architecture: HIGH for v4-verbatim semantics; MEDIUM for CONTEXT.md 3-Part addition (deviates from v4)
- Pitfalls: HIGH — self-loop, nowplaying staleness, cooldown-test-pin, moov-atom are all observed issues in the v4 POC era
- KAAN-ACTION pre-stage scaffolding: MEDIUM — release.yml gate semantics not directly read in this research pass; recommend planner verify

**Research date:** 2026-05-16
**Valid until:** 2026-06-13 (30 days — stable platform deps; ffmpeg / nowplaying-cli / mdfind / Gemini SDK all on slow-moving major versions)
