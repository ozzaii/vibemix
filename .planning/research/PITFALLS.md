# Pitfalls Research

**Domain:** Real-time AI music co-host (open-source desktop app for live DJ sets)
**Researched:** 2026-05-11
**Confidence:** HIGH (most pitfalls are validated either from the existing POC's own bug surface — see `.planning/codebase/CONCERNS.md` — from named library issues, or from documented production failure modes; the prompt-design / "AI slop" pitfalls are MEDIUM because they are taste-bound rather than mechanically testable)

> **Scoping note.** This file catalogs failure modes specific to vibemix. It is an action map for the roadmap, not a fearmongering list. Every pitfall ends with a Phase tag so the roadmap-builder can wire prevention into the right phase. Severity is classified as **Critical** (blocks ship; quality bar fails or the product literally won't run for users), **High** (degrades the "real DJ friend" feel — shippable but disappointing), **Medium** (annoying / supportable in v1.1).

---

## Critical Pitfalls

### Pitfall 1: AI Slop — reactions that feel scripted, generic, or like a voice assistant

**Severity:** Critical
**What goes wrong:**
The AI says "Wow, that drop was sick!" / "Great mix bro!" / "Nice EQ adjustment there!" — bland, ESL-tutor-cheerful, syntactically perfect, semantically empty. It says the same thing every drop. It uses "Let me know if you need anything else." It says "delve", "leverage", "navigate". The voice carries the slight overeager assistant-bot cadence. Within 60 seconds the user knows they are talking to ChatGPT in a costume. The Bravoh-first-OSS positioning ("we build cool AI for musicians") collapses on first contact.

This is the existential failure mode. Every other pitfall is recoverable. This one is the product.

**Why it happens:**
Three compounding causes:
1. **Trigger word leakage.** The detection layer tells the model what happened (`[react to DROP!]`, `[Kaan just spoke. Reply.]`, `[LEVEL→peak]`) — the model dutifully confirms the framing instead of actually listening. The existing codebase has exactly this issue: `cohost.py` / `cohost_lk.py` pass trigger labels into the prompt, and `cohost_v2.py`'s ARCHITECTURE.md anti-patterns section already flags it.
2. **Genericness of base-model voice.** Out-of-the-box Gemini Flash is trained to be a polite, helpful assistant. Without aggressive persona pressure and *concrete* style anchors (specific phrases, specific don'ts, specific vocabulary), it regresses to assistant-voice.
3. **Repetition over a session.** No persona memory of what was already said → the model repeats favorite phrases ("that was sick!", "love that buildup") because each turn is stateless and the prompt template is the same.

**How to avoid:**
- **Surrounding-data prompting (PROJECT.md "Active" requirement).** Feed Gemini: timestamp, last 30s of RMS curve, band shares, BPM, recent MIDI moves, recent phase transitions — and a *task* ("react to what you just heard, briefly"), never a claim ("the drop hit"). Let the model form the reaction from raw evidence. This is the documented v2 pattern (`AICoach.task_for_event`) and it must be the only pattern shipped.
- **Persona anchored to specific vocabulary, not adjectives.** Don't write "friendly, hype DJ friend". Write: "You talk like someone who has been at the warehouse since 2 AM and is half-drunk on the music. You say 'oof', 'yeah yeah yeah', 'okay okay', 'this part this part', 'don't ruin it'. You do NOT say 'amazing', 'awesome', 'great mix', 'nice transition'. You never address the DJ by their function ('DJ'). You never explain what just happened — they were there, they did it."
- **Negative dictionary in prompt.** Hard ban: "amazing", "awesome", "incredible", "let me know", "feel free", "navigate", "delve", "leverage", "in conclusion", "great job", "well done", "absolutely", em dashes in TTS output. Re-check after every model rev (Gemini 3 → 3.x may drift).
- **Per-session anti-repetition.** Maintain a last-N-utterances ring in the prompt context: "You already said this in the last 5 minutes: [...]. Don't repeat phrasing." The existing `TurnHistory` primitive in `cohost.py` does this — port it to v2.
- **React only when there is something to react to.** Slop is partly a *frequency* problem. If the model fires every 30s regardless of musical content, it WILL pad with filler. Per-event-type cooldowns + a "is anything actually happening?" gate (RMS variance below threshold → don't fire, even if cooldown elapsed) makes silence the default.
- **Persona has *opinions*.** A real DJ friend reacts negatively too: "ehh, the low cut was rough", "you came in early", "that's not the one". A hype-man that only ever praises is detectable as fake within 3 reactions. The Coach mode obviously does this; the Hype-man mode also needs occasional "ohhh you almost lost it" honesty.
- **Hand-graded reaction reel before any release.** Record 30 minutes of varied DJing. Have Kaan (and 2-3 DJ friends) blind-rate each reaction 1-5 on "would a real friend say this?". Average ≥ 4.0 with zero 1-2 ratings is the ship gate. Iterate the system prompt until the gate passes. This is the hallucination/grounding verification phase already mandated in Constraints.

**Warning signs:**
- The same phrase appears twice in a 10-minute session.
- The AI says "great" / "awesome" / "amazing" in a reaction (regex grep the events.jsonl).
- The reaction is grammatically perfect across the entire utterance (real friends say "yeah this — yeah").
- The reaction explains what just happened ("That was a nice high-pass filter sweep into the drop") instead of *responding* to it ("oh come on").
- Blind testers say "ChatGPT voice" or "AI assistant" unprompted.
- A reaction would be appropriate to any 4-bar segment of any track in any genre (no specificity).

**Phase to address:** Prompting & Persona phase (mid-build), but **the hand-graded reaction reel is a pre-release gate phase** — no merge to main, no installer build, no marketing push until the gate passes.

**Sources:** [The end of boring bots: How to add personality to AI agents](https://www.gohighlevel.com/post/the-end-of-boring-bots-how-to-add-personality-to-your-ai-agents), [Crossing the uncanny valley of conversational voice (HN)](https://news.ycombinator.com/item?id=43227881), [Audio Uncanny Valley in AI Music Production](https://medium.com/ai-music/when-machines-learn-to-feel-the-audio-uncanny-valley-in-ai-music-production-269a8c3a7e52), [What is AI slop and why it matters](https://artlist.io/blog/what-is-ai-slop-and-why-it-matters-for-video-creators/), POC code at `cohost_v2.py:AICoach`.

---

### Pitfall 2: Hallucination of musical events not present in the audio

**Severity:** Critical
**What goes wrong:**
Model says "loved that vocal sample" when there is no vocal. Says "into the breakdown" while the track is still in the build. Says "fast tempo tonight" when BPM is 124. The user immediately recognizes the model is making things up — and once trust is broken on one reaction, every subsequent reaction is suspect. This is the second existential failure mode and is the explicit hard-gate in PROJECT.md Constraints: "No release until verification phase confirms reactions are tied to real events."

**Why it happens:**
Multimodal hallucinations stem from "imbalanced modality utilization" — textual tokens dominate, the model resorts to language priors (what a hype-man "would say") over actual perceptual evidence. With Gemini Live Native Audio the grounding was empirically worse for live music (per PROJECT.md: "Kaan tested it, doesn't generalize well"), which is why the Flash+TTS cascade is the chosen path. Even with Flash, the model will confabulate when (a) the audio packet is too short to disambiguate, (b) evidence is summarized in natural language ("energy rising") rather than raw numbers, (c) the prompt mentions a hypothesis ("drop incoming") which the model anchors on.

**How to avoid:**
- **Send the audio bytes, not a description of the audio.** `AudioBuffer.snapshot_bytes()` already does this — keep it. Multi-modal grounding requires the model see/hear the primary signal, not a paraphrase.
- **Send evidence as raw numbers, not interpretations.** `rms=0.18, sub=0.42, mid=0.28, high=0.30, onset_density=4.2/s, bpm=126` is grounding. "energy is rising, drop incoming" is poisoning the well.
- **Prompt the model to anchor before reacting.** From Gemini best-practices: "describe before inferring" produces measurable grounding gains. Force the model to internally name what it hears (`audio_describe` as a quick chain-of-thought step, not output) before producing the spoken reaction.
- **Permission to say nothing.** Add an explicit short-circuit token: model may output `<silence/>` if there is nothing worth saying. Add it to the prompt: "If the audio shows nothing distinctive, output `<silence/>` and stop." Don't penalize the empty turn.
- **Verification suite.** Replay 30 known recorded sessions through the pipeline offline. For each AI reaction: extract the audio window the model heard, have a human (or a second-pass LLM grader) score (a) grounded-in-evidence and (b) not-confabulating. Target: ≥ 95% grounded on a held-out test set. This is the documented "Hallucination verification before open-source release" gate in PROJECT.md.
- **No track-name guessing.** `TrackInfo` from nowplaying-cli is the only authoritative source. If `audible_track` confidence < 0.6, the model must use `(unsure)` and not invent a name. Existing v2 logic; preserve it.
- **No screen-OCR claims.** Do not let the model read the BPM/tempo readout off the screen JPEG and then claim "you're at 128" — pixel-derived numbers are a hallucination magnet. Use the actual BPM from `AudioBuffer.estimate_bpm()`.

**Warning signs:**
- Grader-LLM disagreement rate > 5% on the verification suite.
- Model references a specific lyric / artist name that isn't in TrackInfo or the audio.
- Model claims a transition that didn't happen on the controller-MIDI track.
- Model references "the breakdown" when phase_history shows no `breakdown` event in the last 30s.

**Phase to address:** Architecture phase (lock evidence-packet format), Prompting phase (lock verification grading harness), Pre-release verification phase (run the 30-session suite, must pass before installer build).

**Sources:** [Hallucination of Multimodal LLMs: A Survey](https://arxiv.org/pdf/2404.18930), [Grounding the Ungrounded: Spectral-Graph Framework](https://arxiv.org/html/2508.19366v1), [How I Eliminated Hallucinations using Grounding with Gemini 2.5 Flash](https://medium.com/@ansurkar.tejasvi12/how-i-eliminated-hallucinations-using-grounding-with-google-search-using-gemini-2-5-flash-0e3d8aaf8881), [Gemini Prompting Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies), PROJECT.md Constraints.

---

### Pitfall 3: API key leakage from the shipped binary

**Severity:** Critical
**What goes wrong:**
Bravoh's Gemini API key ships embedded in the installer because the product is "free, no key required". Anyone runs `strings vibemix.exe | grep -E "AIza"` or unpacks the PyInstaller bundle with `pyinstxtractor`, extracts the key, and either (a) drains the Bravoh API budget, (b) abuses Gemini under Bravoh's quota with content that gets the project flagged, or (c) posts the key on Hacker News with the title "Bravoh ships their API key in plain text". This has happened to OpenAI keys embedded in shipped apps — there is a documented HN thread about it.

This is also called out in PROJECT.md Constraints as "API-key-protection problem of the year — solve via Bravoh-side proxy". The constraint is correct; the pitfall is shipping anyway because the proxy felt like extra work.

**Why it happens:**
- "It's obfuscated" / "it's compiled" / "we'll watch the dashboard" — none of these survive contact with one motivated user.
- PyInstaller `--onefile` mode extracts to a temp dir at runtime: the unencrypted Python source + bundled `.env` is reconstructable from disk by anyone who runs the binary once.
- Environment-variable injection ("key is in env at install time") leaks via process-listing tools or process memory dumps.
- Hardcoded fallback "in case env is missing" defeats the proxy.

**How to avoid:**
- **The product NEVER possesses the raw Gemini API key.** Period. This is the architecture, not a target.
- **Bravoh-side proxy** at `api.bravoh.io/vibemix/v1/...` that forwards to Gemini, attaches the real key server-side, and applies abuse controls. The client gets a short-lived JWT (or just no token at all and per-IP/per-installation limits) — never the upstream key.
- **Per-installation anonymous client ID.** Generated on first launch, stored locally, sent as a header. Server-side rate-limit per client-ID + per source IP. Both layers, not just one (IPs are shared by NAT, client-IDs can be regenerated).
- **Quota cap per client-ID per day.** PROJECT.md mentions "rate-limit, quota cap per anonymous client" — implement it as a hard 400 if exceeded, not a silent slowdown.
- **Kill switch.** Server can reject specific client-IDs (revocation). Server can refuse all traffic (regional / emergency).
- **Verify by attack.** Before launch: download own installer, run `strings`, run `pyinstxtractor`, decompile the .pyc, search the bundle directory for `AIza...` (Gemini key pattern), search for `bravoh-internal` / `BRAVOH_GEMINI_KEY` env names. Anything found = block ship.
- **Server-side logging.** Every request to the proxy logs: timestamp, client-ID, IP, model, prompt size, response size. Daily cost dashboard. Alert if any single client-ID exceeds 3σ.
- **No fallback.** If the proxy is unreachable, the app says "vibemix needs internet" and stops. Do not add `if proxy_fail: use_local_key()`.

**Warning signs:**
- Anyone says "wait, isn't your key in the binary?" in a code review → answer better be a confident "no, here's the architecture diagram".
- `strings` on a final build shows any string starting with `AIza` (Google API key pattern) or matching `^[A-Za-z0-9_-]{39}$`.
- A Gemini bill spike of >3x baseline within the first week of launch.
- Any "rate limited" error reported by a user that doesn't correlate to *their* usage but to a noisy neighbor (suggests per-project quota, not per-client).

**Phase to address:** Architecture phase (lock the proxy contract before any client work), Distribution phase (build the proxy as a hard dependency of the installer), Pre-release security gate (run the binary-search attack).

**Sources:** [OpenAI API keys leaking through app binaries (HN)](https://news.ycombinator.com/item?id=35557256), [API Keys, Tokens, and Secrets: How They Leak](https://medium.com/@svotwalynet/api-keys-tokens-and-secrets-how-they-leak-and-how-developers-can-avoid-it-3c28374c48e0), [Stop Leaking API Keys: BFF Pattern](https://blog.gitguardian.com/stop-leaking-api-keys-the-backend-for-frontend-bff-pattern-explained/), [How Google AI Studio proxies Gemini API requests](https://glaforge.dev/posts/2026/02/09/decoded-how-google-ai-studio-securely-proxies-gemini-api-requests/), PROJECT.md Constraints.

---

### Pitfall 4: Hardcoded audio device names break on every machine that isn't Kaan's

**Severity:** Critical
**What goes wrong:**
The current POC has `INPUT_DEVICE = "BlackHole 2ch"`, `OUTPUT_DEVICE = "External Headphones"`, `MIC_DEVICE = "MacBook Pro Microphone"` as module-level constants (`cohost.py:139-149` per CONCERNS.md). `find_device()` raises `RuntimeError` on mismatch. A user on a Mac Mini, on a different laptop, with a USB interface, with Loopback Audio instead of BlackHole, with their headphones renamed — all crash on startup with a non-actionable error. Day-one open-source disaster: "doesn't even run".

**Why it happens:**
The dev-machine convention got baked into the constants. The "polished installer" plan in PROJECT.md mentions a calibration wizard but it doesn't yet exist.

**How to avoid:**
- **No hardcoded device names anywhere in the shipping codebase.** Constants moved into a `config.json` written by the calibration wizard on first run.
- **Calibration wizard.** First-run flow:
  1. Enumerate input devices via `sd.query_devices()`.
  2. Detect a loopback device by name match against a list (`BlackHole`, `Loopback Audio`, `VB-Audio Virtual Cable`, `Soundflower`, `WASAPI loopback for ...`). If none found, prompt the user to install BlackHole (macOS) or use WASAPI loopback auto-pick (Windows).
  3. Show the detected output devices, let the user pick "headphones (in-ear)" or "speakers".
  4. Play a 2-second test tone through the picked output, then a 2-second test through the loopback to confirm round-trip.
  5. Save device names + sample rate + channel count to `~/.vibemix/config.json`.
- **Re-validate at every launch.** If a saved device name is no longer in `sd.query_devices()` (headphones unplugged, USB interface gone), show a "device not found — recalibrate or pick a fallback" modal. Don't crash.
- **Sample-rate negotiation.** Don't assume 48kHz. Query each device's `default_samplerate`. If input is 44.1k and output is 48k, resample. Log the chosen rate.
- **macOS-specific:** check that BlackHole's sample rate is actually 48k (BlackHole has a documented Sonoma bug where the rate halves silently — Issue #524). Fail loud if mismatch.
- **Windows-specific:** WASAPI loopback exposes the loopback device with the same name + " (Loopback)" suffix. Pick the loopback variant of the default render device automatically.
- **Helpful error reporting.** On any audio failure: dump `sd.query_devices()` output to a log file the user can attach to a bug report.

**Warning signs:**
- Beta test on any machine other than Kaan's crashes within 5 seconds.
- The first 5 GitHub issues are all "device not found".
- `find_device()` raises bare `RuntimeError` anywhere in the code.

**Phase to address:** Cross-platform audio I/O phase (must do during MVP build, not after).

**Sources:** [BlackHole sample rate keeps changing Issue #524](https://github.com/ExistentialAudio/BlackHole/issues/524), [High Sample Rate Issue Started With macOS Sonoma](https://github.com/ExistentialAudio/BlackHole/discussions/742), [SoundCard library WASAPI pitfalls](https://pypi.org/project/SoundCard/), CONCERNS.md "Fragile Areas".

---

### Pitfall 5: Blocking work inside the sounddevice audio callback (dropouts, glitches)

**Severity:** Critical
**What goes wrong:**
The audio callback runs on PortAudio's real-time thread with a hard deadline (~10ms at 48kHz / 480 frames). Any code path inside it that takes a malloc lock, runs FFT, calls a logger that touches disk, calls `np.concatenate` on a 4.5MB ring (current POC bug per CONCERNS.md), or holds a Python lock waiting on the asyncio side — produces an underrun. The user hears clicks, pops, garbled snippets. The AI's voice glitches. The mascot stutters. The product "feels broken" even though logically nothing is wrong.

**Why it happens:**
- Convenience: shoving work into the callback because it's where the audio lives.
- Allocation in numpy ops that look pure (`np.concatenate`, `arr[a:b]` on a non-contiguous slice → copy).
- `print()` inside the callback (looks innocent; takes the GIL + stdout lock).
- Holding a `threading.Lock` that asyncio code also holds (priority inversion).
- Logging the audio chunk to disk on every callback.

**How to avoid:**
- **The audio callback does ONE thing: push the raw bytes onto a lock-free queue and return.** No FFT, no numpy concat, no print, no log, no float-conversion that allocates.
- **Pre-allocate the ring buffer** as a fixed `np.ndarray` with a write-pointer (CONCERNS.md "Tech Debt" entry — fix during the consolidation phase). Do not `np.concatenate` on every callback.
- **Move all feature extraction to `state_refresh_loop`** running on an asyncio task at 10Hz, not in the callback. `cohost_v2.py` does this correctly — preserve the pattern, kill any regressions.
- **Use larger blocksize for output stream than for input stream.** PortAudio docs and SoundCard library note: WASAPI may underrun if `nframes == blocksize` — use ≥ 2× headroom on the playback side.
- **No `print()` in the callback ever.** Use the `cffi_backend.from_buffer` pattern + lock-free SPSC queue if you need to communicate timing back.
- **Profile with `cProfile` on a 5-minute session.** If anything in the callback path shows > 1ms cumulative, fix it.
- **PortAudio status flag check.** The callback receives a `status` argument — log (from outside the callback) any `input_overflow` / `output_underflow` events. These are the gold signal.

**Warning signs:**
- Audible clicks/pops on user feedback.
- PortAudio status flags `input_overflow` or `output_underflow` appearing in logs.
- CPU pegged at one core's worth (callback is doing too much).
- The AI voice has glitches/dropouts that are not in `voice.wav` (= the playback queue, not the upstream model).
- GC pauses visible as audio gaps every few seconds.

**Phase to address:** Architecture consolidation phase (pre-allocated ring), Audio I/O phase (callback discipline).

**Sources:** [python-sounddevice real-time audio docs](https://deepwiki.com/spatialaudio/python-sounddevice/4.3-real-time-audio-processing), [Possible underrun buffers Issue #139](https://github.com/spatialaudio/python-sounddevice/issues/139), [Latency 30msec Issue #524](https://github.com/spatialaudio/python-sounddevice/issues/524), CONCERNS.md "Performance Bottlenecks".

---

### Pitfall 6: Day-one installer broken on Windows or macOS

**Severity:** Critical
**What goes wrong:**
Mac users: "macOS cannot verify the developer of vibemix.app. Are you sure you want to open it?" — Gatekeeper modal because the app isn't notarized, or it's signed but Hardened Runtime entitlements are wrong (microphone, screen-record, audio-input). User clicks Move to Trash, the project is "broken on Mac".
Windows users: SmartScreen "Windows protected your PC" modal because the installer isn't signed with an EV cert, or Windows Defender quarantines the PyInstaller `--onefile` executable as a generic trojan (the PyInstaller bootloader is a known false-positive trigger). User asks for a refund (which, well, the product is free, so they just leave a 1-star review on the GitHub issue tracker).

For a marketing-coordinated launch this is the worst possible day-one signal — paid IG ads driving traffic to an installer that doesn't run.

**Why it happens:**
- Apple notarization requires Hardened Runtime + entitlements + timestamp + a `notarytool submit` round-trip + stapling. Skipping any step yields "not notarized" Gatekeeper modal.
- Microphone, screen capture, and audio-input each need specific `Info.plist` strings *and* matching entitlements.
- Windows: an unsigned `.exe` triggers SmartScreen until it has "established reputation" (download count + time). For a launch-day app this means every first user gets the modal.
- PyInstaller `--onefile` extracts a temp dir on every launch, which AV heuristics flag.
- Embedded nested binaries (Python's `.dylib`s, `_internal/*.so`) need to be signed individually with the `--deep` flag (or per-file).

**How to avoid:**
- **macOS:**
  - Build with `--codesign-identity` (Developer ID Application) and `--hardened-runtime`.
  - Entitlements file includes: `com.apple.security.device.audio-input`, `com.apple.security.device.microphone`, `com.apple.security.cs.allow-jit` (only if needed), `com.apple.security.cs.disable-library-validation` (because PyInstaller loads `.so`s that aren't signed by Apple).
  - `Info.plist` includes `NSMicrophoneUsageDescription`, `NSAudioCaptureUsageDescription`, `NSCameraUsageDescription` (if needed), and screen-capture description string.
  - Notarize via `xcrun notarytool submit --wait`, then `xcrun stapler staple`.
  - Test on a *clean* Mac (or a fresh user account) — the dev machine's keychain hides notarization issues.
- **Windows:**
  - EV code-signing certificate (NOT a standard OV cert — only EV gets instant SmartScreen reputation). Budget: ~$300/year. PROJECT.md doesn't yet allocate this.
  - PyInstaller `--onedir` (NOT `--onefile`) reduces false positives because nothing is extracted at runtime.
  - Sign every `.exe` and `.dll` in the dist dir, not just the launcher.
  - Submit the signed installer to Microsoft Defender for proactive scanning before launch (Microsoft has a false-positive submission form).
  - Build the installer with Inno Setup or NSIS, sign the installer itself separately.
- **Cross-platform test matrix.** Before launch, install on:
  - Fresh Apple Silicon macOS (Sequoia or current).
  - Intel Mac if any still in the wild (Bravoh-side decision; can defer).
  - Windows 10 stock (no Smart App Control).
  - Windows 11 with Smart App Control on (the strict mode that PROJECT.md will hit hardest).
- **Have a fallback.** If signing fails for a sub-platform, ship `homebrew install vibemix` (mac) + Scoop bucket (win) as the backup — power users can always go around Gatekeeper/SmartScreen.

**Warning signs:**
- Test installer on a clean machine and see the Gatekeeper or SmartScreen modal → block ship until fixed.
- Microsoft Defender's "submitted for analysis" returns "Malware" verdict.
- Any pyinstaller bundled file is unsigned in `codesign --verify --deep --strict` output.

**Phase to address:** Distribution & Branding phase (last phase before launch, but design the build matrix early).

**Sources:** [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [macOS distribution — code signing, notarization](https://gist.github.com/rsms/929c9c2fec231f0cf843a1a746a416f5), [How to Fix Antivirus False Positives with PyInstaller](https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/), [PyInstaller Smart App Control Issue #6747](https://github.com/pyinstaller/pyinstaller/issues/6747), [How to stop your Python programs being seen as malware](https://medium.com/@markhank/how-to-stop-your-python-programs-being-seen-as-malware-bfd7eb407a7).

---

### Pitfall 7: Genre-calibrated heuristics that only work for one genre

**Severity:** Critical
**What goes wrong:**
The phase detector (silent/low/groove/build/drop/peak/breakdown) was tuned on Kaan's Friday-night acid/techno sessions at 150-160 BPM. A house DJ playing 124 BPM never trips the `drop` threshold because the kick energy doesn't peak the same way. A drum-and-bass DJ at 175 BPM is constantly in `peak` because the onset density is permanently above threshold. A disco DJ at 118 BPM with mid-heavy mixes is permanently in `groove` even at the breakdown. The AI either fires constantly (annoying) or fires never (broken). PROJECT.md flags this as an "Active" requirement.

**Why it happens:**
- Hard-coded BPM bands (`SYSTEM_INSTRUCTION` differs across the three POC variants — "150-160" vs "150-170", per CONCERNS.md).
- Hard-coded RMS thresholds for "drop" — but acid drops are sub-bass dominant, house drops are kick+mid, drum-and-bass drops are kick+sub, disco drops are mid-heavy.
- Onset-density thresholds calibrated to 150 BPM produce nonsense at 124 or 175.
- The PROJECT.md decision is right: "genre picker at session start" + genre-aware thresholds. The pitfall is shipping with the picker but leaving the thresholds at the acid-tuned defaults for all genres.

**How to avoid:**
- **Per-genre threshold table.** Drop the constants into a `genre_profiles.json`:
  ```
  {
    "techno":  {"bpm_range": [125, 150], "drop_rms": 0.32, "build_dur_s": 8, "drop_sub_share": 0.40, ...},
    "house":   {"bpm_range": [118, 132], "drop_rms": 0.28, "build_dur_s": 16, "drop_sub_share": 0.35, ...},
    "dnb":     {"bpm_range": [165, 185], "drop_rms": 0.36, "build_dur_s": 4, "drop_sub_share": 0.42, ...},
    "disco":   {"bpm_range": [110, 125], "drop_rms": 0.22, "build_dur_s": 12, "drop_sub_share": 0.20, ...},
    "pop":     {"bpm_range": [95, 130],  "drop_rms": 0.24, "build_dur_s": 8,  "drop_sub_share": 0.25, ...}
  }
  ```
- **Normalize, don't threshold.** Instead of "is RMS > 0.32?", track "is RMS in the top 15% of the last 60 seconds?". A percentile-based phase detector is naturally genre-agnostic.
- **Genre-agnostic RMS calibration** (per PROJECT.md "Active"): on session start, run a 60-second listen phase that measures the dynamic range of the current set, then sets thresholds relative to that. Re-calibrate every 5 minutes (drift handling).
- **Per-genre validation.** For each genre profile, record 30 minutes of a representative set and verify the EventDetector produces sane phase transitions. Don't ship a profile that hasn't been bench-tested.
- **BPM detection robust to half/double errors.** `AudioBuffer.estimate_bpm()` can return 87 BPM when the track is 174 BPM (drum-and-bass is famously prone to this). Validate against a stability window — don't switch genres on a 4-second BPM spike.

**Warning signs:**
- House DJ tester reports "the AI never reacts to drops".
- D&B tester reports "the AI says drop every 8 bars".
- Phase histogram over a 1-hour set shows >70% `groove` or >70% `peak` (sign of mis-calibrated threshold).
- The same recording analyzed under techno vs house profile yields wildly different event timelines.

**Phase to address:** Sensing & Event Detection phase (mid-build, before the AI inference layer is touched). Per-genre validation in pre-release verification.

**Sources:** [Techno BPM: The Ultimate Guide For DJs (2026) | ZIPDJ](https://www.zipdj.com/blog/techno-bpm), [House Music BPM Guide](https://www.zipdj.com/blog/house-music-bpm), [EDM BPM Chart Complete Genre Ranges](https://trackradar.ai/tools/edm-bpm-chart), [BPM Chart by Genre | Orphiq](https://orphiq.com/resources/bpm-tempo-guide), PROJECT.md "Active" + CONCERNS.md "Tech Debt".

---

### Pitfall 8: Cross-platform audio loopback library churn (BlackHole vs Loopback vs VB-Cable)

**Severity:** Critical
**What goes wrong:**
The user has no virtual cable installed and the app demands one in a modal that says "Please install BlackHole from existential.audio" — half the users bounce. Worse: the user has BlackHole installed but their multi-output device is mis-configured (per macOS docs the built-in output must be the *top* device in the Multi-Output, or you get silence at high sample rates). Or on Windows the user is on Voicemeeter and the app doesn't know how to negotiate. Or BlackHole's Sonoma bug halves the sample rate silently (documented Issue #524) and the AI hears half-pitched, half-speed audio and thinks every track is at 60 BPM.

**Why it happens:**
- "BlackHole" the project name has a Sonoma-era bug surface that's still active in 2025-2026 per the GitHub issue tracker.
- macOS Multi-Output Devices have unintuitive ordering rules.
- Windows users have a fragmented landscape: VB-Cable, Voicemeeter Banana, OBS Virtual Cable, the *built-in* WASAPI loopback exposed by PortAudio's WASAPI host API.
- Sample-rate mismatches in chained virtual cables (BlackHole 16ch → BlackHole 2ch → Multi-Output) silently quantize down.

**How to avoid:**
- **Prefer the OS-native loopback path on Windows.** PyAudioWPatch + PortAudio's WASAPI host API exposes a "loopback" alias for every output device — zero install for the user. Use this as the default; VB-Cable is a fallback.
- **macOS: ship a one-click BlackHole install assistant.** PROJECT.md mentions a calibration wizard — that wizard detects no virtual cable, offers a button "Install BlackHole 2ch (open-source, by ExistentialAudio)" that runs the BlackHole installer (downloaded to a known path, signed). User stays inside the app.
- **Don't require a Multi-Output Device.** A virtual cable is enough — vibemix listens on BlackHole, the user's DJ software already routes to BlackHole, and the user's DJ software ALSO outputs to their real audio interface for the speakers/headphones. No Multi-Output juggling.
- **Sample-rate sanity check.** At startup, generate a 10-second 1kHz test tone, route it through the loopback, FFT the captured signal. If the peak is not at 1kHz ± 5%, the loopback is mis-rated. Show a clear error and a recalibration option.
- **Document the supported configurations in the README** with a screenshot grid (BlackHole + djay, BlackHole + Serato, VB-Cable + rekordbox, WASAPI loopback + rekordbox, etc.). Don't try to support every weird user setup in v1.

**Warning signs:**
- Sample-rate sanity check fails (peak not at 1kHz).
- AI thinks BPM is half of actual (BlackHole Sonoma bug signature).
- Windows tester on a fresh machine reports "no audio in the captured stream" (likely picked the render device, not the loopback variant).

**Phase to address:** Cross-platform audio I/O phase. Loopback compatibility test on a Sonoma + Sequoia + Win10 + Win11 matrix before each release.

**Sources:** [BlackHole sample rate keeps changing Issue #524](https://github.com/ExistentialAudio/BlackHole/issues/524), [BlackHole macOS Sonoma high sample rate](https://github.com/ExistentialAudio/BlackHole/discussions/742), [Virtual audio routing on macOS isn't lossless](https://blog.claranguyen.me/post/2025/03/09/lossless-loopback-audio-macos/), [WASAPI Loopback Recording (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording), [PyAudioWPatch loopback example](https://github.com/s0d3s/PyAudioWPatch/blob/master/examples/pawp_record_wasapi_loopback.py).

---

### Pitfall 9: LiveKit session disconnects and dies silently mid-set

**Severity:** Critical
**What goes wrong:**
The LiveKit `RealtimeModel` WebSocket disconnects 23 minutes into a set. The session is opened once at startup with no reconnect logic (CONCERNS.md "Architectural Constraints"). After disconnect, the audio capture keeps running, the mascot keeps animating, the user keeps DJing — but the AI never speaks again. The user notices 5 minutes later, restarts the app, and 5 minutes of momentum is gone. Worse — if the disconnect happens during the *demo recording* for the launch video, that's the cinematic moment ruined.

**Why it happens:**
- LiveKit Agents Python SDK has open GitHub issues (#4609, #4135, #4676, #1679) about WebSocket disconnects, retries not properly handled, "Unclosed client session" leaks.
- Gemini Realtime returns 1008 / 1011 policy violations and the LiveKit side doesn't always recover.
- POC code path: "if the session errors or drops, the program must be restarted" — explicitly called out.

**How to avoid:**
- **Per PROJECT.md decision: NOT using Gemini Live Native Audio as default.** The Flash + TTS cascade path has fewer of these failure modes because each turn is a fresh HTTP call (`cohost.py` pattern). Lock this in.
- **Even with Flash, add retry-with-backoff** on transient errors: 503, 429, network timeouts. Max 3 retries within 6 seconds, then give up gracefully and just don't speak this turn.
- **Health-check heartbeat.** Background task pings a known-good Gemini endpoint every 60s. If 3 consecutive failures, surface a "vibemix is having trouble — check your internet" status pill in the UI.
- **Watchdog on the in-flight flag.** CONCERNS.md notes the existing 12s stale-guard for `trigger_state["in_flight"]`. Keep this. Make it visible in the UI ("last AI reaction was 4 minutes ago" status).
- **Mid-session error event recording.** Every error logged to `events.jsonl` with timestamp + error class + stack. Aggregated over many sessions this becomes the bug-prioritization data.

**Warning signs:**
- `events.jsonl` contains `session_error` or `turn_error` entries.
- The 30-minute test recording has > 5-minute silent gaps.
- LiveKit logs show `Unclosed aiohttp ClientSession` or `code 1011` / `code 1008`.

**Phase to address:** Architecture phase (lock the Flash+TTS path, not Live Native), Inference layer phase (retry + watchdog), Pre-release stability phase (60-minute soak test).

**Sources:** [LiveKit agents Issue #4609](https://github.com/livekit/agents/issues/4609), [Gemini API WebSocket Overload #1679](https://github.com/livekit/agents/issues/1679), [Gemini Live Realtime 1008 policy violation #4414](https://github.com/livekit/agents/issues/4414), [code 1011 Issue #2274](https://github.com/livekit/agents/issues/2274), CONCERNS.md "Architectural Constraints" + ARCHITECTURE.md.

---

## High Severity Pitfalls

### Pitfall 10: TTS chunk boundaries that produce robotic pauses or cutoffs

**Severity:** High
**What goes wrong:**
Gemini TTS streams PCM in chunks. If the PlaybackQueue starves between chunks (network jitter, slow inference), the user hears "hey — — yeah that was —" with audible gaps. If the prompt produces text that's split mid-word for TTS, the prosody breaks. If the TTS sample-rate doesn't match the output device, the voice sounds chipmunk'd or molasses-y. If the gain isn't normalized, the voice clips during peak phases of the set and is inaudible during low energy.

**Why it happens:**
- TTS sentence-boundary buffering not done — partial tokens sent to TTS produce unnatural prosody.
- PCM output rate 24kHz, sounddevice output stream opened at 48kHz → speed-up artifact.
- No gain auto-leveling — the AI voice is calibrated to a quiet living room but during a 100dB drop nobody hears it.

**How to avoid:**
- **Buffer text up to sentence boundary before sending to TTS.** Don't stream half-sentences.
- **Match sample rates explicitly.** Gemini TTS returns 24kHz mono int16 — open the playback stream at 24kHz, not 48kHz. If the OS device only supports 48kHz, upsample once on chunk arrival.
- **Pre-buffer 200-400ms** of TTS audio before starting playback. Smaller chunks = lower latency but more glitches per real-time TTS playback guidance (~400ms reduces audio glitches).
- **Loudness normalization.** Apply a target LUFS (-16 to -14) to TTS chunks before queueing. Sidechain duck the music output by -6dB while AI is speaking (the existing `MicBuffer._current_gain()` pattern but inverted — duck music, not mic).
- **Detect and handle empty TTS chunks.** Gemini occasionally returns empty `inline_data` (per `cohost.py:827-838` SDK issue noted in CONCERNS.md). Don't enqueue zero-length frames.

**Warning signs:**
- AI voice has audible gaps in `voice.wav`.
- AI voice pitch is wrong (sample-rate mismatch).
- AI voice is inaudible during peak phases.
- TTS output ends mid-word.

**Phase to address:** Playback layer phase (mid-build).

**Sources:** [Real-Time TTS interview Q&A | credmark](https://credmark.ai/practice/top-real-time-text-to-speech-interview-questions-and-answers), [How to Cut TTS Latency for Real-Time Voice Apps](https://www.dupdub.com/blog/tts-latency-optimization), [Prosodic Boundary-Aware Streaming Generation for LLM-Based TTS](https://arxiv.org/html/2603.06444), [Deepgram Audio Output Streaming](https://developers.deepgram.com/docs/streaming-the-audio-output).

---

### Pitfall 11: MIDI controller hot-plug & enumeration races

**Severity:** High
**What goes wrong:**
User starts vibemix, then plugs the DDJ-FLX4 — controller doesn't appear (mido enumerated ports at startup and didn't re-scan). User has the DDJ already plugged but the Pioneer driver hasn't finished USB enumeration (DDJ-FLX4 has documented USB-enumeration timing issues with Windows 10/11) — mido returns an empty port list. User has two MIDI devices (controller + a launchpad they forgot about) — vibemix picks the wrong one. macOS, PortMidi/RtMidi hang for 1-2 seconds during init (documented mido behavior) — looks like the app froze.

**Why it happens:**
- mido / python-rtmidi don't expose USB hot-plug events on either macOS or Windows — you have to poll.
- Pioneer DDJ-FLX4 has specific USB-C power requirements (9V) and enumeration quirks that produce intermittent "not detected" on Windows 11.
- Some controllers (Numark NS7) demand exclusive USB access — if another app has it open, mido fails.

**How to avoid:**
- **Re-enumerate periodically.** Every 2 seconds, run `mido.get_input_names()` and diff against the previous set. New device → match against the controller library → auto-bind. Removed device → unbind, show "controller disconnected" status.
- **Detect by USB VID:PID where possible** (mido reports name strings, but on Windows you can correlate via pywin32). Pioneer DDJ controllers expose recognizable name strings like `DDJ-FLX4 MIDI 1`.
- **Sequenced startup.** Don't open the controller in `main()`. Open it after the calibration wizard completes, so a user without a controller can still get to the UI.
- **Async enumeration.** mido's port open on macOS hangs 1-2s; do it on a background thread with a "detecting controller..." spinner.
- **Graceful "no controller" mode.** The product must run end-to-end with zero MIDI devices. The reactions get less specific (no EQ-move context) but don't crash.
- **Document the Pioneer USB quirk** in the troubleshooting README: "If your DDJ-FLX4 isn't detected on Windows, try unplug/replug after Windows boots, use a USB-C with 9V power."

**Warning signs:**
- Tester plugs controller after launch and it's not detected.
- `mido.get_input_names()` returns an empty list when a known controller is connected.
- Startup time > 3 seconds with a "frozen UI".

**Phase to address:** MIDI Controller Library phase.

**Sources:** [python-rtmidi 1.5.8 docs](https://spotlightkid.github.io/python-rtmidi/rtmidi.html), [Mido backends documentation](https://mido.readthedocs.io/en/latest/backends/), [DDJ-FLX4 USB recognition issue](https://forums.pioneerdj.com/hc/en-us/community/posts/12890193751961-DDJ-FLX4-not-being-recognised-by-my-windows-pc), [Pioneer DJ troubleshooting PDF](https://www.pioneerdj.com/-/media/pioneerdj/downloads/other/troubleshooting/troubleshooting_002_e_v011.pdf).

---

### Pitfall 12: Mic feedback loop — AI's own voice triggers the AI

**Severity:** High
**What goes wrong:**
Speakers mode: AI says "yeah this part this part". The mic picks up the AI's own speech, transcribes it, and the system fires a "Kaan_spoke" trigger. The AI responds to itself, which the mic picks up again. Endless feedback. The user is at a party trying to DJ and the AI is gibbering on top of itself.

The existing POC has `MicBuffer._current_gain()` doing partial mitigation by muting the mic during AI talk + a 350ms hold window, but headphones mode (in-ear) is the safe mode — speakers mode is where this becomes ugly.

**Why it happens:**
- AI voice leakage into mic is unavoidable when the user picks "speakers" as output destination.
- Mic gating with a fixed hold window doesn't survive reverb tails on a loud system.
- Echo cancellation (AEC) isn't free — the real-time DSP is non-trivial.

**How to avoid:**
- **Hard-disable mic in speakers mode.** If user picks "speakers" as output destination, the mic capture path is bypassed entirely. The `KAAN_SPOKE` trigger source no longer exists. The set proceeds with audio + MIDI + screen only.
- **Headphones mode allows mic.** Because headphones don't bleed back, mic detection is safe. The existing gating logic + 350ms hold is sufficient.
- **OR: WebRTC AEC.** LiveKit's audio pipeline includes WebRTC AEC. If the LiveKit pipeline is preserved (PROJECT.md says it is), enable AEC explicitly and confirm via the AEC docs.
- **Document in UI.** "Mic input is disabled when output is speakers — it would create feedback. Use headphones if you want the AI to hear you."

**Warning signs:**
- Session log shows back-to-back `KAAN_SPOKE` triggers within 2s of `AI_SPOKE` events.
- Tester reports "the AI keeps talking to itself".
- Reaction text contains references to the AI's own previous utterance.

**Phase to address:** Audio I/O phase + UX phase (the output picker decision drives this).

**Sources:** PROJECT.md "Active" output destination picker, ARCHITECTURE.md `MicBuffer._current_gain()` pattern.

---

### Pitfall 13: Screen-capture privacy & sensitive-content exposure

**Severity:** High
**What goes wrong:**
User has Slack messages, a 1Password autofill, a Stripe dashboard, or their email open. Screen capture goes to Gemini's API servers as JPEG. Gemini logs it. Even if no breach happens, the user (correctly) freaks out when they discover what got sent. Public trust in vibemix collapses.

CONCERNS.md flags this: "Screen capture runs without user confirmation and captures the full primary display." `cohost_v2.py` already crops to the djay window when found, but the fallback is full-screen.

**Why it happens:**
- `mss.grab(monitor[1])` grabs the entire primary display.
- The DJ-window-crop (Quartz `find_djay_window_bounds`) only works for djay Pro and only on macOS.
- If the user is on rekordbox / Serato / Traktor / VirtualDJ, the crop doesn't apply.
- On Windows, equivalent window-bounds detection needs to be implemented per-app.

**How to avoid:**
- **Mandatory window picker on first run.** The user picks "this is my DJ software window". App captures only that window's bounds — never the full screen.
- **If the picked window is minimized or off-screen,** stop capture and show "DJ window not visible — pausing screen input". Don't fall back to full-screen.
- **Per-window capture on macOS via ScreenCaptureKit (>= macOS 12.3)** — modern API, supports per-window capture with explicit user consent prompts.
- **Per-window capture on Windows via Windows.Graphics.Capture** — modern API requires user-visible consent banner.
- **Show a "Screen capture is ON" status indicator** at all times in the UI.
- **Privacy README section.** Explicitly list: "We send the picked DJ window image (not your full screen, not your other apps) to Google's Gemini API. Images are NOT stored by us. Google's data-retention policy applies." Link to Google's terms.
- **Optional: full opt-out.** Power user can disable screen capture entirely. The AI gets one less signal but still works (audio + MIDI).

**Warning signs:**
- A test session captures the full screen including any non-DJ-app window.
- The README doesn't mention screen capture.
- Privacy-conscious tester (Francis Tural is a good candidate) says "wait, what does it capture?"

**Phase to address:** Cross-platform screen capture phase, with hard requirement for window picker.

**Sources:** CONCERNS.md "Security Considerations", [ScreenCaptureKit (Apple)](https://developer.apple.com/documentation/screencapturekit), Windows.Graphics.Capture API.

---

### Pitfall 14: License confusion / Bravoh dual-use constraint

**Severity:** High
**What goes wrong:**
Repo ships under MIT, but Bravoh wants to use the same code internally in a closed-source product. MIT allows this trivially — but if it ships under GPL or AGPL, Bravoh's internal use of the code "infects" their commercial product. Worse: contributor licensing isn't clear — a contributor sends a PR, the PR gets merged, the contributor later objects to Bravoh's commercial use because they didn't sign a CLA. Legal blast radius right before Bravoh's public launch.

**Why it happens:**
- License choice deferred to last minute (PROJECT.md says "TBD (likely MIT or Apache 2.0)").
- No CONTRIBUTING.md → no CLA → contributor IP rights are ambiguous.
- Marketing assumes "open source = anyone can use it however" without considering the upstream Bravoh business need.

**How to avoid:**
- **License = Apache 2.0.** Permissive (allows Bravoh internal use), explicit patent grant (covers Gemini integration risks), well-understood, GitHub badge support. MIT is also fine but Apache 2.0's patent clause is friendlier.
- **CLA from contributors.** Either:
  - Use the [Developer Certificate of Origin (DCO)](https://developercertificate.org/) — every commit signed-off with `Signed-off-by:`. Lightweight, no admin overhead.
  - OR a full CLA (e.g., Apache Individual CLA) administered via [cla-assistant.io](https://cla-assistant.io/). Heavier, but unambiguous IP assignment to Bravoh.
- **CONTRIBUTING.md** specifies: license, sign-off requirement, code style, how to file bugs, how to propose features, where the maintainer lives.
- **Trademark notice.** "vibemix" and "Bravoh" are trademarks of Bravoh; the code is Apache 2.0 but the marks are not. Add a `TRADEMARKS.md` clarifying.
- **NOTICE file** per Apache 2.0 requirements — list third-party dependencies and their licenses (Gemini SDK, LiveKit, sounddevice, mido, BlackHole if bundled, etc.).

**Warning signs:**
- Day-of-launch debate about whether someone can fork it.
- A contributor PR is merged before CLA/DCO is in place.
- The README says "open source" but no LICENSE file exists.

**Phase to address:** Distribution & Branding phase (before launch, but not the last day).

**Sources:** [Apache 2.0 license terms](https://www.apache.org/licenses/LICENSE-2.0), [Developer Certificate of Origin](https://developercertificate.org/), [Promote Your Open Source Project guide](https://business.daily.dev/resources/promote-open-source-project-step-by-step-launch-guide/).

---

### Pitfall 15: Issue tsunami on launch day with no triage

**Severity:** High
**What goes wrong:**
Launch day: paid IG ads + friend network + DJ outreach. The repo gets 400 stars in 24 hours and 70 GitHub issues — half are duplicate "doesn't work on my Mac" reports, a quarter are feature requests for Linux / Traktor / iOS, the rest are real bugs buried in the noise. Kaan is busy with Bravoh's public launch the same week. Issues sit untriaged. The repo's first impression to anyone reading the issue tracker is "abandonware in 7 days". Stars stop growing. Bravoh's wedge fails.

**Why it happens:**
- Open-source projects routinely underestimate the issue volume from a successful launch.
- No issue templates → users provide insufficient info → maintainer has to ask follow-ups.
- No triage labels → no way to filter "critical bug" from "Linux feature request".
- Single maintainer + Bravoh public launch concurrency.

**How to avoid:**
- **Issue templates** for: bug report (with mandatory OS + audio device + controller + repro steps), feature request (with "have you checked the roadmap?" gate), question (redirected to Discussions).
- **Auto-close for incomplete reports** (GitHub Action that closes bug reports missing the template fields after 7 days).
- **Pre-populated FAQ** in `docs/troubleshooting.md` covering the known top-10 issues from internal testing (BlackHole install, device not found, Gatekeeper modal, controller not detected, mic feedback, etc.).
- **Discussions tab enabled** for "how do I" questions — issues are bugs only.
- **Triage labels:** `needs-info`, `confirmed-bug`, `feature-request`, `wontfix`, `good-first-issue`, `critical`, `linux` (auto-closed in v1).
- **A second responder pre-arranged.** Musa or Yasin available to triage for the first 72h post-launch — assign them in advance.
- **Disable issues briefly if drowning.** "We're getting overwhelmed — please use Discussions for now" is a better signal than 200 unread issues.
- **First-impressions audit.** Before launch, look at the repo as if you've never seen it: README hero, install button, first 5 issues, license, contributing — does it look "alive and maintained"?

**Warning signs:**
- Issues backlog > 30 within first week.
- Most-thumbs-up issue is a duplicate of another open issue.
- Hacker News comment says "looks like a dead project from 2 days in" because issues are unresponded.

**Phase to address:** Pre-launch readiness phase.

**Sources:** [What Does an Open Source Triage Team Do?](https://opensauced.pizza/docs/community-resources/what-does-an-open-source-triage-team-do/), [Triage Issues | Pragmatic Programmers](https://medium.com/pragmatic-programmers/triage-issues-af72eea5df12), [Why Your Open Source Startup Is Going To Fail](https://about.scarf.sh/post/why-your-open-source-startup-is-going-to-fail-and-what-you-can-do-about-it).

---

### Pitfall 16: Copyright over copyrighted music streams

**Severity:** High
**What goes wrong:**
A user records a vibemix session for their YouTube channel — the recording has copyrighted music underneath the AI's voice. YouTube Content ID flags the upload, mutes audio, or takedown. Worse: the user posts a clip to TikTok and DJ Snake's lawyer sees vibemix's name in the description. Less acute but still bad: a user broadcasts a live set with vibemix to Twitch, gets the channel struck, blames vibemix.

vibemix doesn't *play* the music — it listens to and reacts to the user's own playback — but Marketing materials might inadvertently demo with commercial tracks, and the README's recommended workflow might encourage uploads.

**Why it happens:**
- Marketing instinct: "here's our demo set, listen to the AI react to [Track Name]!" — the demo video uses copyrighted music.
- README example workflow: "record your set with the AI commentary and share on social".
- Users assume "the AI is talking over it, so it's transformed" → it's not, that's not how copyright works.

**How to avoid:**
- **Marketing & demo content uses royalty-free or self-produced music.** Bravoh has artist relationships; use them. Or commission a short licensed loop for the launch video.
- **README doesn't encourage public publishing.** "Record your set for personal review" is fine. "Share your set on TikTok" is dangerous to suggest.
- **No upload feature in v1.** Recording is local-only. Don't ship a "post to Twitter" button. Recording-to-YouTube hook is already Out of Scope per PROJECT.md.
- **Disclaimer in the README:** "vibemix records your own session for personal review. Public sharing of recordings containing copyrighted music may require licenses — that's between you and the rights holders."
- **AI doesn't recite lyrics.** Add to system prompt: "Never sing lyrics, never quote song lyrics verbatim — describe vibe, not words." Avoids creating a derivative work in the recording.

**Warning signs:**
- Marketing draft features a commercial track in the demo audio.
- README example says "share your set".
- User reports YouTube takedown referencing vibemix in description.

**Phase to address:** Distribution & Branding phase (marketing materials), Prompting phase (no-lyrics rule).

**Sources:** [How to Avoid Copyright Trouble When Livestreaming Your Sets](https://brewerlong.com/information/intellectual-property/livestreaming-copyright-guide/), [The DJ's Guide to Music Licensing and Copyright](https://dj.studio/blog/dj-licence), [Copyright Implications for Live Event Streaming Platforms](https://www.scoredetect.com/blog/posts/copyright-implications-for-live-event-streaming-platforms-a-primer).

---

## Medium Severity Pitfalls

### Pitfall 17: Recording disk-space blowout

**Severity:** Medium
**What goes wrong:**
Every session writes `input.wav` + `voice.wav` + `events.jsonl` to `~/.vibemix/recordings/`. Per CONCERNS.md, 96 sessions in 2 days produced 566MB — at this rate a heavy user fills 10GB in a month. Eventually disk-full, the app crashes mid-session, or the user's machine alerts on low storage.

**Why it happens:**
- No retention policy in the POC.
- WAV is uncompressed; 30 minutes of 16kHz mono is ~58MB.

**How to avoid:**
- **Default 7-day retention.** On startup, delete sessions older than 7 days. User-configurable in settings.
- **Compress with FLAC.** Lossless, ~50% of WAV. Or Opus at 64kbps if Kaan accepts lossy.
- **Keep `events.jsonl` longer than audio.** The text events are the valuable artefact; WAVs are the bulk.
- **Settings UI:** "vibemix uses X GB of recordings. [Delete recordings older than: 1 / 7 / 30 days / Never]".

**Phase to address:** Recording layer phase.

**Sources:** CONCERNS.md "Performance Bottlenecks".

---

### Pitfall 18: Preview model name expiry (Gemini 3 Flash / Gemini 3.1 TTS rotation)

**Severity:** Medium
**What goes wrong:**
Gemini model identifiers like `gemini-3-flash-preview` are time-limited preview endpoints. Google rotates them. One morning vibemix users open the app and the AI never speaks because the model name 404s.

CONCERNS.md flags this — and the existing POC uses preview model names with December-2025 date suffixes.

**Why it happens:**
- Preview model names are deliberately short-lived.
- The model name is hardcoded.
- No fallback chain.

**How to avoid:**
- **Server-side model selection via the proxy.** The proxy resolves "Gemini Flash latest" to whatever the current production model is. Client never knows the model name. Server rotates without a client release.
- **Use GA model names where possible.** As Gemini 3 Flash exits preview, switch the proxy to the GA name.
- **Health-check at startup.** If the proxy reports "no model available", show a clear "vibemix is currently being updated, please try again" message — not a crash.

**Phase to address:** Architecture phase (proxy contract design).

**Sources:** [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Gemini generateContent API](https://ai.google.dev/gemini-api/docs/gemini-3), CONCERNS.md "Fragile Areas".

---

### Pitfall 19: Missing test coverage on prompt-building & event-detection logic

**Severity:** Medium
**What goes wrong:**
A refactor changes the `AICoach.build_prompt()` evidence-line format. Suddenly the prompts are missing the audio_evidence packet but nothing crashes — the AI just hallucinates more. No test catches it because there are no tests (CONCERNS.md "Test Coverage Gaps"). The regression ships. Slop returns.

**Why it happens:**
- POC has zero unit tests.
- Pure Python logic (feature extraction, prompt assembly, event detection) is testable without audio hardware but isn't tested.

**How to avoid:**
- **Snapshot tests on prompt-building.** For each event type, capture the prompt string as a snapshot. Refactors that change wording must be deliberate.
- **Unit tests on `AudioBuffer.snapshot_features()`** with known synthetic inputs (sine waves at known frequencies, silence, white noise, known onset patterns). Verify outputs match expected within tolerance.
- **Event-detector replay tests.** Feed `events.jsonl` from real sessions back through `EventDetector` and verify the same events fire.
- **CI on PRs.** GitHub Actions runs `pytest` on every PR; failing tests block merge.

**Phase to address:** Consolidation phase (after POC merge, before feature additions).

**Sources:** CONCERNS.md "Test Coverage Gaps".

---

### Pitfall 20: Calibration wizard that's too aggressive (asks 12 questions on first run)

**Severity:** Medium
**What goes wrong:**
First-run wizard takes 4 minutes. Users bounce before reaching the actual product. PROJECT.md "Active" lists "Calibration wizard on first run (one-click setup)" — the "one-click" framing is correct; the failure mode is shipping a 12-step Settings dialog instead.

**Why it happens:**
- Every config option feels essential to the engineer.
- Defaults aren't picked confidently → user has to pick.

**How to avoid:**
- **3 questions max.**
  1. Pick your DJ software window (visual picker, default = whatever the largest visible non-vibemix window is).
  2. Pick output destination (in-ear headphones vs. speakers — 2 buttons).
  3. Pick genre (visual chips, default = "electronic / open format").
- **Auto-detect everything else.** Loopback device, mic, controller, all done in the background.
- **Settings page** for the deep configuration. Wizard is the fast path.
- **"Skip" button on every step** with sensible defaults.

**Phase to address:** UX phase.

---

### Pitfall 21: Mascot easter egg leaks into the polished installer

**Severity:** Medium
**What goes wrong:**
`mascot.html` (canvas sprite reacting to RMS) is fun, but it's a hobby-prototype aesthetic. If it ships as the default UI, the product looks unprofessional. PROJECT.md is correct that mascot is Out of Scope as a shipped UI — but if the dev-shortcut is left in (e.g., the WebSocket bus auto-opens browser to `mascot.html`), it leaks.

**How to avoid:**
- **Mascot WebSocket bus disabled in release builds.** Feature-flag it behind `VBEMIX_DEV=1` env var.
- **Polished main UI** is the only thing the shipped installer launches.

**Phase to address:** Distribution phase.

---

### Pitfall 22: Onset density inflation under heavy compression

**Severity:** Medium
**What goes wrong:**
DJs often run a master compressor or limiter on their output (built-in to rekordbox, Traktor, etc.). The compressed master has more uniform RMS — onset density rises because every kick reaches the same peak, the "build → drop" RMS delta shrinks, and the phase detector misfires "groove" as "peak".

**Why it happens:**
- The POC's heuristics assume an uncompressed-ish master.
- Real DJ output is almost always compressed.

**How to avoid:**
- **Calibrate against the *running average* of the user's master**, not against absolute thresholds. Percentile-based thresholds (as in Pitfall 7) handle this naturally.
- **Detect compression** via crest-factor (peak / RMS ratio). Very low crest factor → compressed master, lower the delta thresholds.

**Phase to address:** Sensing & Event Detection phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded device names | Works on dev machine immediately | Breaks for every user → Pitfall 4 | Never in shipping code; only in unit tests / dev scripts |
| `print()` debug statements in audio callback | Fast to add | Allocation pressure, GIL contention → glitches | Never; use a lock-free ring + separate logger thread |
| `np.concatenate` per-callback ring | One-line implementation | GC pressure → dropouts → Pitfall 5 | Acceptable only in offline batch tools |
| Three parallel cohost variants | Lets you A/B before deciding | Param drift, untestable, scary refactors → CONCERNS.md | Never past consolidation phase |
| `.env` file with API key on disk | "It just works locally" | Leak risk; not what users get | Only on Kaan's dev machine, never in distributed binary |
| Hardcoded BPM/RMS thresholds for one genre | Tuning feels precise | Breaks every other genre → Pitfall 7 | Only as the techno-profile default; behind a genre key |
| No requirements.txt | Easy to add deps fast | Reproducibility lost; SDK rotation breaks build → Pitfall 18 | Never; pin in pyproject from day-one of vibemix |
| `--onefile` PyInstaller | Single .exe is clean | Higher AV false-positive rate → Pitfall 6 | Only if mitigated by EV signing and onedir tested first |
| Full-screen capture fallback | Crops aren't perfect on all apps | Privacy → Pitfall 13 | Never; pause capture instead |
| LiveKit Live Native Audio as default | Pretty real-time architecture | Worse grounding per PROJECT.md own testing → ship Flash+TTS | Out of scope per PROJECT.md decision |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Gemini Flash multimodal | Sending paraphrased "audio summary" as text | Send the raw audio bytes inline + raw numeric evidence |
| Gemini TTS streaming | Sending half-sentences as they're generated | Buffer to sentence boundary, then stream |
| LiveKit Agents Python SDK | Assume the session lasts forever | Add retry, watchdog, and graceful "no AI this turn" fallback — or use the simpler Flash+TTS path |
| BlackHole | Assume 48kHz always | Sample-rate sanity tone test on every startup |
| WASAPI loopback (Windows) | Recording from the render device, not the loopback alias | Use PortAudio's `loopback` flag or PyAudioWPatch |
| python-rtmidi / mido | Enumerate once at startup | Re-enumerate every 2s for hot-plug |
| nowplaying-cli (macOS) | Treat output as ground truth always | Cross-reference with audible-deck detection; emit `(unsure)` below threshold |
| Quartz `find_djay_window_bounds` | Assume the user has djay Pro | User picks their window; cross-platform window picker |
| PyInstaller bundle | `--onefile` because it's neat | `--onedir` + sign every nested binary → fewer AV false positives |
| GitHub Issues | No templates, no triage | Templates + labels + Discussions + DCO from day one |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| FFT in trigger callback | Asyncio loop stutter, missed events | Run feature extraction at 10Hz on a separate task | Becomes audible on any user with active CPU contention |
| `np.concatenate` ring buffer | Audio dropouts every few seconds | Pre-allocated ring with write-pointer | Already happening at 16kHz × 140s = 4.5MB per push (CONCERNS.md) |
| Per-frame screen capture | Asyncio loop blocked on disk/JPEG encode | mss at 1fps, never per-frame; encode in a thread executor | Already 1fps in POC — keep it there |
| Full-string TurnHistory in every prompt | Token cost balloons over a 2hr session | Cap to last N turns (already done in cohost.py); summarize older history | Visible token costs > $0.10 per session |
| Unbounded `events.jsonl` | Disk fills slowly | Rotate per-session; keep recent N sessions | Pitfall 17 at ~10GB |
| WebSocket mascot broadcast at 30fps | Asyncio task time on every tick | Conditional broadcast (only if connected client exists) | Negligible at single-user; matters if it's left running |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API key embedded in distributed binary | Total quota drain, public embarrassment, key revocation cycle | Proxy + per-installation client-ID + rate-limit (Pitfall 3) |
| Full-screen capture without consent | Privacy breach (Slack, banking, etc. visible to Gemini) | Window picker only; pause when window not visible (Pitfall 13) |
| WebSocket mascot bus accepts `{action: "trigger"}` from any local client | Local-process can force AI generation | Loopback-only + auth token; or remove the trigger endpoint in release builds |
| Logs include user audio + screen captures | If logs uploaded for support, sensitive data goes too | Redact before sending; ask user explicit consent for log upload |
| Mic always recording | User in a private room is captured | Mic disabled in speakers mode; explicit "mic on" indicator in UI |
| `.env` committed to git accidentally | Key in git history forever | CONCERNS.md notes `.gitignore` is in place; verify no historical leak; rotate key for vibemix anyway |
| Auto-update mechanism unsigned | Supply-chain attack vector | If shipping auto-update, sign the update payload; verify signature client-side |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| AI talks too often | Annoying, gets muted, never used again | Per-event cooldowns + "is anything happening?" gate + user-adjustable density slider (rare / normal / chatty) |
| AI never talks | Feels broken | Heartbeat reaction every 60-90s if no other trigger has fired AND audio is non-silent |
| Reaction text on screen flashes too fast to read | Frustrating | Visible transcript pane that persists last N reactions |
| User can't tell if vibemix is "hearing" them | Lost trust ("is it on?") | Live audio meter visible at all times; mascot or pulse animation tied to RMS |
| Permissions dialog cascade on first launch | Confusion: mic → screen-capture → audio-input → notifications | Calibration wizard requests permissions one at a time with explanation; don't trigger them at random startup moments |
| Settings hidden behind 3 menus | "How do I switch to Coach mode?" | One-tap toggle for mode and voice in the main UI |
| AI in coach mode is harsh | User feels bad about their mixing | Coach mode has a warmth dial; framing is "what I'd try next" not "what you did wrong" |
| No way to mute the AI mid-set | DJ can't recover from a bad reaction | Big visible mute button; AI stops, mascot indicates muted state |

## "Looks Done But Isn't" Checklist

- [ ] **Calibration wizard:** Often missing the sample-rate sanity test (Pitfall 8) — verify a 1kHz tone round-trip gives back 1kHz
- [ ] **Installer:** Often missing nested-binary signing (Pitfall 6) — run `codesign --verify --deep --strict` on a clean mac
- [ ] **Installer (Windows):** Often missing the onedir mode + EV cert + Defender pre-submit — install on a fresh Win11 with Smart App Control on
- [ ] **API proxy:** Often missing per-IP + per-client rate limit at *both* layers (Pitfall 3) — verify by running 100 requests from one IP, then 100 from one client-ID across IPs
- [ ] **Genre profiles:** Often missing validation for non-default genres (Pitfall 7) — replay a known house set under "house" profile and confirm sane event timeline
- [ ] **Hallucination grounding:** Often missing the 30-session offline verification run (Pitfall 2) — block ship until the suite passes ≥95%
- [ ] **AI slop check:** Often missing the blind-rated reaction reel (Pitfall 1) — block ship until ≥4.0 average with no 1-2 ratings
- [ ] **Cross-platform parity:** Often only tested on dev machine — install on a fresh Mac and fresh Windows and run end-to-end
- [ ] **MIDI fallback:** Often only tested with the one controller — test generic-MIDI mode with an unmapped device
- [ ] **No-controller mode:** Often crashes when no MIDI present — run without a controller plugged in
- [ ] **Mic off in speakers mode:** Often the mic path is forgotten — verify mic is hard-disabled when output = speakers
- [ ] **License + CONTRIBUTING + NOTICE:** Often just LICENSE exists — verify all three present, plus DCO setup
- [ ] **Issue templates:** Often only README — verify .github/ISSUE_TEMPLATE/ has bug + feature + question templates
- [ ] **README hero:** Often a text-only readme — verify the install GIF and the 30s demo video are present at launch
- [ ] **AbuseProtection:** Often the proxy can be hit by any unauthenticated request — verify a 401 / 429 with no client-ID header

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| AI slop in shipped reactions (P1) | HIGH | Hotfix system prompt; release patch; apologize on socials; the brand damage persists for the launch window |
| Hallucination in shipped reactions (P2) | HIGH | Tighten evidence-packet format; re-run verification suite; release; same brand damage |
| API key leaked (P3) | CRITICAL | Rotate the key immediately at Google Cloud; deploy proxy if not already; release patched build forcing all clients to update; communicate to users (one line in the README); audit billing for damage |
| Device-name crash on user machine (P4) | MEDIUM | Ship a hotfix with the calibration wizard; meanwhile, give users a manual fallback (env var to override device names) |
| Audio dropouts (P5) | MEDIUM | Roll back to last-known-good build; profile; fix; re-release |
| Installer broken on launch day (P6) | HIGH | Pull the IG ads, post a known-issues note, hotfix the installer, restart the ad campaign 24-48h later |
| Genre detector misfiring for non-techno (P7) | LOW | Profile fix in JSON; users update; not a code release necessarily |
| BlackHole sample-rate halving silently (P8) | LOW | Detect via tone test; surface to user with a fix-link |
| LiveKit session disconnects mid-set (P9) | LOW | Reconnect logic + Flash fallback; if user hits it, manual app restart still works |
| TTS chunk glitches (P10) | LOW | Buffer size tuning; releases as needed |
| Controller not detected (P11) | LOW | Document workaround in troubleshooting; hotfix hot-plug detection |
| Mic feedback loop (P12) | LOW | Hard-disable mic in speakers mode (P12 prevention is the same as the recovery) |
| Screen-capture privacy concern (P13) | MEDIUM | Switch to window picker, document, communicate transparently; some users will still bounce |
| License confusion (P14) | MEDIUM | Add CLA / DCO; relicense if needed (Apache 2.0 is compatible with MIT, so it's a one-way ratchet) |
| Issue tsunami (P15) | MEDIUM | Enable Discussions, add templates, pause public ads for 48h, triage, resume |
| Copyright takedown (P16) | LOW | Update README disclaimer; user-side problem mostly |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: AI slop | Prompting & Persona phase (mid-build) + Pre-release verification | Hand-graded reaction reel ≥ 4.0 avg, no 1-2 ratings |
| P2: Hallucination | Architecture + Prompting + Pre-release verification | 30-session offline replay ≥ 95% grounded |
| P3: API key leak | Architecture (proxy contract) + Distribution + Pre-release security gate | `strings` / `pyinstxtractor` against final binary, server logs show 0 raw-key requests |
| P4: Device-name hardcoding | Cross-platform Audio I/O phase | Install on 3 non-dev machines and run to AI's first reaction |
| P5: Blocking audio callback | Architecture consolidation phase + Audio I/O phase | `cProfile` of audio callback; PortAudio status flags zero over a 30-min session |
| P6: Installer broken | Distribution & Branding phase | Install on fresh macOS + Windows; Gatekeeper / SmartScreen modals do not appear |
| P7: Genre mis-calibration | Sensing & Event Detection phase | Per-genre replay validation against recorded sets |
| P8: Loopback library churn | Cross-platform Audio I/O phase | Sample-rate sanity test passes on Sonoma + Sequoia + Win10 + Win11 |
| P9: LiveKit / network disconnects | Architecture phase (lock Flash+TTS) + Inference layer (retry+watchdog) | 60-minute soak test with zero `session_error` events |
| P10: TTS chunk glitches | Playback layer phase | `voice.wav` has no gaps > 100ms within an utterance |
| P11: MIDI hot-plug | MIDI Controller Library phase | Plug/unplug 5× during a session; controller re-binds each time |
| P12: Mic feedback | Audio I/O + UX phase | Speakers mode has zero `KAAN_SPOKE` events from AI playback |
| P13: Screen privacy | Cross-platform Screen Capture phase | Window picker is mandatory; full-screen fallback removed |
| P14: License confusion | Distribution phase | LICENSE + CONTRIBUTING + NOTICE + TRADEMARKS present; CLA/DCO live |
| P15: Issue tsunami | Pre-launch readiness phase | Templates, labels, Discussions, second responder confirmed |
| P16: Copyright | Distribution (marketing) + Prompting (no-lyrics rule) | Marketing audit; AI never recites lyrics in 1hr test |
| P17: Disk blowout | Recording layer phase | Retention policy in settings; default 7d |
| P18: Preview model expiry | Architecture phase (proxy contract) | Model name is server-side resolution, not client constant |
| P19: Missing tests | Consolidation phase | CI green on PRs; snapshot tests on prompt-building |
| P20: Heavy wizard | UX phase | First-run flow ≤ 3 questions, ≤ 60s total |
| P21: Mascot leak | Distribution phase | Release build has no `mascot.html` served from a default-on port |
| P22: Compression inflation | Sensing & Event Detection phase | Percentile-based thresholds; crest-factor compression detection |

## Sources

- POC code analysis: `/Users/ozai/projects/dj-set-ai/.planning/codebase/CONCERNS.md`
- POC architecture: `/Users/ozai/projects/dj-set-ai/.planning/codebase/ARCHITECTURE.md`
- Project intent: `/Users/ozai/projects/dj-set-ai/.planning/PROJECT.md`
- [Hallucination of Multimodal Large Language Models: A Survey (arXiv)](https://arxiv.org/pdf/2404.18930)
- [Grounding the Ungrounded: Spectral-Graph Framework (arXiv 2508.19366)](https://arxiv.org/html/2508.19366v1)
- [Mitigating Multimodal LLM Hallucinations via Relevance Propagation (arXiv 2605.01766)](https://arxiv.org/html/2605.01766)
- [How I Eliminated Hallucinations using Grounding with Gemini 2.5 Flash (Medium)](https://medium.com/@ansurkar.tejasvi12/how-i-eliminated-hallucinations-using-grounding-with-google-search-using-gemini-2-5-flash-0e3d8aaf8881)
- [Gemini Prompt Design Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- [Agentic Vision in Gemini 3 Flash (Google blog)](https://blog.google/innovation-and-ai/technology/developers-tools/agentic-vision-gemini-3-flash/)
- [python-sounddevice Real-time Audio Processing (DeepWiki)](https://deepwiki.com/spatialaudio/python-sounddevice/4.3-real-time-audio-processing)
- [python-sounddevice underrun Issue #139](https://github.com/spatialaudio/python-sounddevice/issues/139)
- [python-sounddevice latency Issue #524](https://github.com/spatialaudio/python-sounddevice/issues/524)
- [WASAPI shared mode sample-rate Issue #52](https://github.com/spatialaudio/python-sounddevice/issues/52)
- [PyAudioWPatch (WASAPI loopback)](https://github.com/s0d3s/PyAudioWPatch)
- [SoundCard library (cross-platform audio)](https://pypi.org/project/SoundCard/)
- [BlackHole sample-rate Issue #524](https://github.com/ExistentialAudio/BlackHole/issues/524)
- [BlackHole macOS Sonoma high-rate Discussion #742](https://github.com/ExistentialAudio/BlackHole/discussions/742)
- [Virtual audio routing on macOS isn't lossless](https://blog.claranguyen.me/post/2025/03/09/lossless-loopback-audio-macos/)
- [WASAPI Loopback Recording (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)
- [python-rtmidi 1.5.8](https://spotlightkid.github.io/python-rtmidi/rtmidi.html)
- [Mido backends](https://mido.readthedocs.io/en/latest/backends/)
- [DDJ-FLX4 USB recognition issue](https://forums.pioneerdj.com/hc/en-us/community/posts/12890193751961-DDJ-FLX4-not-being-recognised-by-my-windows-pc)
- [Pioneer DJ troubleshooting PDF](https://www.pioneerdj.com/-/media/pioneerdj/downloads/other/troubleshooting/troubleshooting_002_e_v011.pdf)
- [PyInstaller SmartScreen Issue #6747](https://github.com/pyinstaller/pyinstaller/issues/6747)
- [PyInstaller AV false-positive Issue #6754](https://github.com/pyinstaller/pyinstaller/issues/6754)
- [How to Fix AV False Positives with PyInstaller (pythonguis.com)](https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/)
- [How to stop Python programs being seen as malware (Medium)](https://medium.com/@markhank/how-to-stop-your-python-programs-being-seen-as-malware-bfd7eb407a7)
- [macOS distribution — code signing + notarization (rsms gist)](https://gist.github.com/rsms/929c9c2fec231f0cf843a1a746a416f5)
- [Notarizing macOS software (Apple Developer)](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Notarization: the hardened runtime (Eclectic Light)](https://eclecticlight.co/2021/01/07/notarization-the-hardened-runtime/)
- [godot notarization hardened-runtime issue #83469](https://github.com/godotengine/godot/issues/83469)
- [OpenAI API keys leaking through app binaries (HN)](https://news.ycombinator.com/item?id=35557256)
- [Stop Leaking API Keys: BFF Pattern (GitGuardian)](https://blog.gitguardian.com/stop-leaking-api-keys-the-backend-for-frontend-bff-pattern-explained/)
- [How Google AI Studio proxies Gemini requests](https://glaforge.dev/posts/2026/02/09/decoded-how-google-ai-studio-securely-proxies-gemini-api-requests/)
- [API Key Leak prevention (PayloadsAllTheThings)](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/API%20Key%20Leaks/README.md)
- [LiveKit agents reconnect Issue #4609](https://github.com/livekit/agents/issues/4609)
- [LiveKit Gemini WebSocket overload #1679](https://github.com/livekit/agents/issues/1679)
- [LiveKit Gemini Realtime 1008 #4414](https://github.com/livekit/agents/issues/4414)
- [LiveKit code 1011 #2274](https://github.com/livekit/agents/issues/2274)
- [Audio Output Streaming (Deepgram)](https://developers.deepgram.com/docs/streaming-the-audio-output)
- [TTS latency optimization (DupDub)](https://www.dupdub.com/blog/tts-latency-optimization)
- [Prosodic Boundary-Aware Streaming TTS (arXiv 2603.06444)](https://arxiv.org/html/2603.06444)
- [Techno BPM Guide 2026 (ZIPDJ)](https://www.zipdj.com/blog/techno-bpm)
- [House Music BPM Guide (ZIPDJ)](https://www.zipdj.com/blog/house-music-bpm)
- [EDM BPM Chart by Genre (TrackRadar)](https://trackradar.ai/tools/edm-bpm-chart)
- [BPM Chart by Genre (Orphiq)](https://orphiq.com/resources/bpm-tempo-guide)
- [AI Music Copyright Risks (Silverman Sound)](https://www.silvermansound.com/ai-music-copyright-legal-risks-content-creators)
- [How to Avoid Copyright Trouble When Livestreaming (BrewerLong)](https://brewerlong.com/information/intellectual-property/livestreaming-copyright-guide/)
- [The DJ's Guide to Music Licensing (DJ.Studio)](https://dj.studio/blog/dj-licence)
- [What Does an Open Source Triage Team Do? (OpenSauced)](https://opensauced.pizza/docs/community-resources/what-does-an-open-source-triage-team-do/)
- [Why Your Open Source Startup Is Going To Fail (Scarf)](https://about.scarf.sh/post/why-your-open-source-startup-is-going-to-fail-and-what-you-can-do-about-it)
- [Promote Your Open Source Project (daily.dev)](https://business.daily.dev/resources/promote-open-source-project-step-by-step-launch-guide/)
- [The end of boring bots: AI personality (GoHighLevel)](https://www.gohighlevel.com/post/the-end-of-boring-bots-how-to-add-personality-to-your-ai-agents)
- [Crossing the uncanny valley of conversational voice (HN)](https://news.ycombinator.com/item?id=43227881)
- [Audio Uncanny Valley in AI Music Production (Medium)](https://medium.com/ai-music/when-machines-learn-to-feel-the-audio-uncanny-valley-in-ai-music-production-269a8c3a7e52)
- [What is AI slop and why it matters (Artlist)](https://artlist.io/blog/what-is-ai-slop-and-why-it-matters-for-video-creators/)
- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Developer Certificate of Origin](https://developercertificate.org/)
- [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0)

---
*Pitfalls research for: vibemix — open-source AI DJ co-host*
*Researched: 2026-05-11*
