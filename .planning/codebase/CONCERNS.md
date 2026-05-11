# Codebase Concerns

**Analysis Date:** 2026-05-11

> **Framing note:** This is a fast-iteration prototype (single initial commit, ~2 days of iteration based on file timestamps). Concerns are framed to help future work, not to imply the code is broken. Many patterns that would be unacceptable in a production service are fine for a local-only personal tool.

---

## Tech Debt

**Three parallel cohost variants with diverged logic:**
- Issue: `cohost.py` (Gemini 3 Flash + TTS, non-LiveKit), `cohost_v2.py` (Gemini 2.5 native audio via LiveKit, most evolved), and `cohost_lk.py` (intermediate LiveKit approach, same model as v2) are three independent files that share almost all primitives but have separately evolved. `MUSIC_GAIN_TO_GEMINI` is `2.5` in `cohost.py` and `cohost_lk.py` but `8.0` in `cohost_v2.py`. `AudioBuffer` is `130s` in `cohost_lk.py`, `140s` in `cohost_v2.py`. `SYSTEM_INSTRUCTION` differs significantly across all three — different genre tags (150-160 BPM vs 150-170 BPM), different behavioral constraints, different evidence packet formats.
- Files: `cohost.py:75`, `cohost_v2.py:84`, `cohost_lk.py:117`, `cohost.py:82`, `cohost_v2.py:120`, `cohost_lk.py:126`
- Impact: Tuning a parameter in one variant does not propagate to others. The active variant (`cohost_v2.py`) has a different gain, buffer size, and AI persona than the v1 reference.
- Fix approach: Pick `cohost_v2.py` as the canonical file. Delete or archive `cohost.py` and `cohost_lk.py`. Extract shared primitives (`AudioBuffer`, `Levels`, `MicBuffer`, `PlaybackQueue`, `VoiceRecorder`, `ControllerState`) into a `primitives.py` module if a fourth variant is ever needed.

**`np.concatenate` ring-buffer pattern on every audio callback:**
- Issue: `AudioBuffer.push()`, `MicBuffer.push()` in all three variants allocate a new numpy array on every call by doing `np.concatenate([self._buf, new_chunk])` followed by a trim slice. At 48kHz with 480-frame chunks this is ~100 allocs/sec, each copying the full ring.
- Files: `cohost_v2.py:257`, `cohost_v2.py:392`, `cohost_lk.py:368`, `cohost_lk.py:553`, `cohost.py:215`, `cohost.py:246`
- Impact: Unnecessary GC pressure during a latency-sensitive audio callback. Not crashing but generates allocator churn. CPython's GC pauses can cause audio dropouts.
- Fix approach: Pre-allocate the ring buffer as a fixed-size `np.ndarray` and use a write-pointer with modular indexing, or use `collections.deque` for the int16 ring and only convert to ndarray on `snapshot_*` calls.

**`trigger_state` dict shared between asyncio coroutines without an asyncio lock:**
- Issue: `trigger_state = {"in_flight": False}` is mutated by both the `coach_loop` coroutine and by the `on_gen` callback (registered via `@session.on("generation_created")`). In `cohost_v2.py`, `on_gen` creates a new asyncio Task on every generation event and sets `trigger_state["in_flight"] = False` in its `finally` block, while `coach_loop` reads and writes the same dict without any lock. Since both run in the same event loop, CPython's GIL means individual dict mutations are atomic, but the check-then-set pattern (`if trigger_state.get("in_flight")` ... `trigger_state["in_flight"] = True`) is not atomic across awaits.
- Files: `cohost_v2.py:1457-1531`, `cohost_v2.py:1674-1683`, `cohost_lk.py:1347-1597`
- Impact: In practice this is low-risk because all mutations are in single-threaded asyncio, but if `session.on()` fires from a thread (LibKit internals), a double-trigger is possible.
- Fix approach: Replace the `dict` with an `asyncio.Event` or `asyncio.Lock` and add an explicit note about which thread sets it.

**No requirements.txt / pyproject.toml — dependency state is not reproducible:**
- Issue: The `.venv` contains `google-genai==2.0.1`, `livekit==1.1.7`, `livekit-agents==1.5.8`, `livekit-plugins-google==1.5.8` etc., but there is no `requirements.txt` or `pyproject.toml`. The only install documentation is implicit in the import statements.
- Files: (entire repo root — missing)
- Impact: On a fresh machine or after `.venv` corruption, the exact package versions needed are unknown. Preview model names (`gemini-2.5-flash-native-audio-preview-12-2025`, `gemini-3-flash-preview`) may stop working at any time and you need the SDK version locked to know what was used.
- Fix approach: `pip freeze > requirements.txt` in the venv, commit it. One command.

**`cohost.streaming.py.bak` committed to git:**
- Issue: A 856-line, 34KB backup file is tracked in git history. It represents the Gemini 3.1 Flash Live streaming approach that was superseded by the LiveKit variants.
- Files: `cohost.streaming.py.bak`
- Impact: Bloats the repo; confusing for anyone reading the file tree; `.bak` extension means Python won't run it but it adds noise.
- Fix approach: `git rm cohost.streaming.py.bak` and commit. The history already preserves it if needed.

---

## Known Bugs

**`_test_multimodal.py` hardcodes an absolute path to a specific session:**
- Symptoms: Running `_test_multimodal.py` on any machine other than the original, or after a `recordings/` cleanup, fails immediately with a `FileNotFoundError`.
- Files: `_test_multimodal.py:14`
- Trigger: `python3 _test_multimodal.py` on a fresh clone or after pruning old recordings.
- Workaround: Edit line 14 to point to an existing session directory before running.

**`generate_bat.py` is misnamed — generates a bat mascot PNG, not a `.bat` script:**
- Symptoms: The filename strongly implies a Windows batch-file generator. The actual function is calling Gemini's image generation API to produce the animated bat mascot asset.
- Files: `generate_bat.py:1-64`
- Trigger: Reading the filename without opening the file.
- Workaround: Rename to `generate_bat_image.py` or `generate_mascot.py`.

---

## Security Considerations

**`.env` file is gitignored but was present at initial commit time — verify it was never staged:**
- Risk: `.env` contains `GEMINI_API_KEY` (55 bytes — consistent with a single API key line). The `.gitignore` correctly lists `.env`, but the file exists on disk and there is only one commit. If the file was staged before `.gitignore` was written, it would be in git history.
- Files: `.env` (present on disk), `.gitignore:1`
- Current mitigation: `.gitignore` entry exists; `git ls-files` does not show `.env` in tracked files.
- Recommendation: Run `git log --all --full-history -- .env` to confirm it was never committed. If clean, no action needed. Rotate the API key if there is any doubt.

**Screen capture runs without user confirmation and captures the full primary display:**
- Risk: `mss.grab(monitor[1])` captures the entire primary display at 1fps, including any visible content (terminal output with credentials, browser tabs, other apps). Frames are sent to Gemini API servers as JPEG.
- Files: `cohost.py:607-627`, `cohost_v2.py:872-935`, `cohost_lk.py` (equivalent `screen_capture_loop`)
- Current mitigation: `cohost_v2.py` uses `find_djay_window_bounds()` via Quartz to crop to just the djay Pro window when available, reducing exposure.
- Recommendation: Log a startup notice when full-screen capture is active (i.e., when `find_djay_window_bounds()` returns `None`). Already mitigated in v2; `cohost.py` always captures full screen without djay crop.

**WebSocket mascot bus binds to `127.0.0.1` only — acceptable for local use:**
- Risk: `ws://127.0.0.1:8765` is localhost-only. No authentication on the connection. The `cohost_lk.py` variant accepts `{action: "trigger"}` messages from any local WebSocket client, which can force an AI generation.
- Files: `cohost_lk.py:1622-1647`, `cohost.py:1049-1062`
- Current mitigation: Loopback-only binding limits exposure to the local machine.
- Recommendation: Acceptable for a local dev tool. Document the trigger capability in a comment.

---

## Performance Bottlenecks

**566MB of recording sessions accumulating with no cleanup:**
- Problem: Every run of any variant creates a new timestamped directory in `recordings/` with `voice.wav`, `input.wav`, and `events.jsonl`. 96 sessions have accumulated in under 2 days totalling 566MB. At this rate a week of heavy use reaches 2-3GB.
- Files: `cohost.py:538-543`, `cohost_v2.py:699-705`, `cohost_lk.py:940-946`; `recordings/` directory (96 subdirectories)
- Cause: No retention policy, no cleanup on startup, `recordings/` is gitignored but not auto-pruned.
- Improvement path: On `VoiceRecorder.__init__`, scan `recordings/` and delete sessions older than N days (e.g., 7). Or add a one-liner cleanup script. The `events.jsonl` files are the valuable artifact; the WAV files are large and often redundant.

**7.5MB of PNG sprite assets tracked in git:**
- Problem: `sprite-1.png` (2.3MB), `sprite-2.png` (2.5MB), `sprite-3.png` (2.3MB) are committed directly to git. `git clone` pulls all three.
- Files: `sprite-1.png`, `sprite-2.png`, `sprite-3.png`
- Cause: Committed in the initial commit with no LFS configuration.
- Improvement path: Either add git-lfs tracking for `*.png`, or store them externally and reference a URL in `mascot.html`. For a local-only tool this is low priority but worsens clone time if the repo is shared.

**`AudioBuffer` allocates a new numpy array on every push at ~100Hz:**
- Problem: See the tech debt entry above. The allocation rate is bounded (ring size is capped) but each `np.concatenate` at 16kHz int16 with 140s ring = 2.24M samples × 2 bytes = ~4.5MB copied per push tick.
- Files: `cohost_v2.py:255-259`, `cohost_lk.py:366-370`
- Cause: Simple implementation; fine for a prototype.
- Improvement path: Preallocate ring with write-pointer as described above.

---

## Fragile Areas

**`find_device()` raises `RuntimeError` if audio device name doesn't match:**
- Files: `cohost.py:139-149` (equivalent in all three variants)
- Why fragile: Device names are hardcoded module-level constants (`INPUT_DEVICE = "BlackHole 2ch"`, `OUTPUT_DEVICE = "External Headphones"`, `MIC_DEVICE = "MacBook Pro Microphone"`). If the system audio setup changes (headphone jack pulled, device renamed, different Mac), the script crashes immediately at startup with a `RuntimeError` before any helpful context.
- Safe modification: Wrap `find_device` calls in startup with a catch that lists available devices on failure — already partially done in the mic path (mic failure is non-fatal), but music input and output failures are fatal and unhelpful.
- Test coverage: None.

**Preview model names will break when Google rotates them:**
- Files: `cohost.py:58-59` (`gemini-3-flash-preview`, `gemini-3.1-flash-tts-preview`), `cohost_v2.py:71` and `cohost_lk.py:103` (`gemini-2.5-flash-native-audio-preview-12-2025`)
- Why fragile: All model identifiers are preview endpoints. Google has historically deprecated preview model names with short notice. `gemini-2.5-flash-native-audio-preview-12-2025` includes a December-2025 date suffix suggesting it is time-limited.
- Safe modification: When a model stops working, update the `MODEL` constant at the top of the active variant. Keep the other variants' model constants in sync.
- Test coverage: `test_voice.py` and `_test_tts.py` would surface this immediately if run regularly.

**`cohost_v2.py` `on_gen` callback creates an asyncio Task from a synchronous `session.on()` handler:**
- Files: `cohost_v2.py:1674-1683`
- Why fragile: `asyncio.create_task()` called from inside a synchronous callback that may be invoked from a LiveKit library thread. If the library calls the event handler from outside the event loop, `create_task` will raise `RuntimeError: no current event loop`. The code works today because the LiveKit Python SDK fires events on the asyncio thread, but this is not guaranteed by the API contract.
- Safe modification: Capture the event loop at startup (`loop = asyncio.get_event_loop()`) and use `loop.call_soon_threadsafe(lambda: asyncio.ensure_future(runner()))`.
- Test coverage: None.

**`MicBuffer` unbounded float32 accumulation before `pull()` is called:**
- Files: `cohost_v2.py:370-407`, `cohost_lk.py:530-570`
- Why fragile: `MicBuffer.push()` grows `self._buf` via `np.concatenate` and only trims when it exceeds `MAX_FRAMES` (200ms at 48kHz). `pull()` drains it. If `pull()` is never called (e.g., mic used only for level detection in `cohost_v2.py`), the buffer accumulates unchecked. In `cohost_v2.py` the `MicBuffer` is pushed but `pull()` is not called in the main audio loop (mic data goes to Gemini via the MIDI/LiveKit session, not via explicit `pull`). The `MAX_FRAMES` cap (`48000 * 200 // 1000 = 9600`) does bound it, so this is not actually a memory leak — but it's confusing.
- Safe modification: Add a comment in `MicBuffer` clarifying whether `pull()` is the intended consumer or just `levels.update_mic()`.

---

## Scaling Limits

**Single-machine, single-user local tool — no scaling concerns apply.**
The architecture intentionally relies on BlackHole virtual audio, a locally connected DDJ-FLX4, and macOS system APIs (Quartz, `nowplaying-cli`). There is no server, no database, no multi-user concern.

---

## Dependencies at Risk

**`google-genai==2.0.1` pinned in venv but not in any lockfile:**
- Risk: The SDK's streaming and TTS interfaces changed significantly between 1.x and 2.x. Without a lockfile, a future `pip install google-genai` could pull 3.x and break the `inline_data` extraction pattern used in `cohost.py:827-838`.
- Impact: `cohost.py`'s TTS drain loop and `_test_tts.py` would silently return empty audio.
- Migration plan: Pin in `requirements.txt`. Monitor the SDK changelog when upgrading.

**`livekit-agents==1.5.8` — rapidly evolving SDK:**
- Risk: `livekit.plugins.google.realtime.RealtimeModel` and `generate_reply()` are used in `cohost_v2.py` and `cohost_lk.py`. The LiveKit agents SDK has had breaking API changes between minor versions (0.x → 1.x was a full rewrite). `1.5.x` may not be the current stable release.
- Impact: Breaks the entire `cohost_v2.py` and `cohost_lk.py` variants (which are the active ones).
- Migration plan: Pin `livekit-agents==1.5.8` and `livekit-plugins-google==1.5.8` in `requirements.txt`. Test after any upgrade.

---

## Missing Critical Features

**No requirements.txt — fresh install is undocumented:**
- Problem: There is no documented install procedure. The only hint is `source .venv/bin/activate` in the run scripts, but `.venv` is gitignored. A collaborator or future-self on a new machine has no documented install path.
- Blocks: Onboarding, disaster recovery.

**No README or setup documentation:**
- Problem: There is no `README.md`. The only prose documentation is in module docstrings at the top of each `.py` file. The audio routing requirement (BlackHole, Multi-Output Device, djay Pro setup) is described in `cohost.py:1-22` but nowhere else.
- Blocks: Anyone trying to run this who didn't set it up themselves.

---

## Test Coverage Gaps

**No automated tests for any core logic:**
- What's not tested: `AudioBuffer.snapshot_features()`, `AudioBuffer.estimate_bpm()`, `AudioBuffer.long_arc_curve()`, `ControllerState` CC/Note decoding, `EventDetector.detect()`, `AICoach.build_prompt()`, trigger logic, TurnHistory, PlaybackQueue drain behavior.
- Files: All of `cohost.py`, `cohost_v2.py`, `cohost_lk.py`
- Risk: Any refactor of the feature extraction or prompt-building code could silently produce garbage without detection.
- Priority: Medium — the smoke tests (`test_voice.py`, `_test_tts.py`) cover the external API surface. The internal logic is pure Python and testable without audio hardware. `AudioBuffer.snapshot_features()` in particular has a number of edge cases (silent audio, short clips, zero-size arrays) that are worth unit-testing.

**`_test_multimodal.py` and `_test_tts.py` have leading underscores — ambiguous status:**
- What's not tested: It's unclear whether these are intentionally excluded from test runners (the `_` prefix convention) or are just named that way. Neither pytest nor any other runner is configured, so the prefix has no mechanical effect.
- Files: `_test_multimodal.py`, `_test_tts.py`
- Risk: Someone setting up pytest would not auto-discover these.
- Priority: Low — rename to `test_multimodal.py` / `test_tts.py` if a runner is ever configured.

---

*Concerns audit: 2026-05-11*
