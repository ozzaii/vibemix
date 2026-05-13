# Pitfalls Research — vibemix v2.0 Research-Driven Ship

**Domain:** Adding research-driven features (latency stack, citation linter, djay Pro overlay, pyrekordbox XML, 10-SKU MIDI library, mascot 4-layer additive state machine, post-session debrief, library intelligence, generalized event detector v1, cross-mode citation enforcement, Ship/Sign/Release matrix, Day-Zero Ops) into vibemix's existing 3-process architecture (Tauri Rust shell + Python sidecar + remote FastAPI proxy on api.altidus.world).
**Researched:** 2026-05-14
**Confidence:** HIGH — anchored to 11 verified v2-bucket research artifacts (~28,000 words) and to `cohost_v4.py` as the canonical baseline. Each pitfall has a concrete prevention strategy backed by a citation in the source artifacts.

> **Scope note:** Known/already-mitigated pitfalls are NOT re-researched here (PyInstaller --onefile AV trigger, AIza leak gate, IPC schema drift, TCC bundle ID lock, mascot opaque-chrome, Tauri start_dragging permission, sidecar PyInstaller path, Mixxx OSC un-shipped, ProDJ Link wrong-market, canvas-rendered Rekordbox/Serato AX, Mixamo blendshape death, mem0 vector-DB for profile, Gemini caching 1024-token floor, `SpeechHandle.cancel()` API name, pyrekordbox SQLCipher key extraction, Gemini Embedding 2 80s audio cap, MP3/WAV only). These appear in PROJECT.md decisions or were resolved by the v2-bucket research swarm. This document surfaces NEW pitfalls specific to v2.0 feature additions.

> v1 pitfalls (P1-P22 from previous research, 2026-05-11) remain valid but were milestone-1 anchored. The v2 milestone re-frames toward feature integration — this file replaces the v1 catalog.

---

## Critical Pitfalls

### Pitfall 1: Cancel-and-Refire Blows the 50€/mo Per-User Proxy Budget

**Severity:** Critical (budget-blowing — could break the funnel economics that gate vibemix-Free)

**What goes wrong:**
The latency stack ships `SpeechHandle.interrupt(force=True)` cancel-and-refire to keep reactions tied to the *latest* high-priority event. Each cancel is a Gemini call already in flight that gets thrown away — wasted tokens. At Hard Tek 170+ BPM with bursty event flow (`KICK_SWAP` → `SUB_LAYER_ARRIVAL` → `DISTORTION_CLIMB` in the same 16-bar phrase), the cancel rate can spike to 5-10/min sustained. At 1000 DAU with that cancel rate, the per-user Gemini cost multiplies 3-5× and breaks the ~50€/mo proxy budget. A-followup-1 §"Open follow-ups for Kaan" #3 calls this out as a metric needing a guard rail.

**Why it happens:**
The clean design says "cancel when a higher-priority event arrives" — easy to implement, hard to bound. Without a per-session cap, every wasted reply still bills full Gemini cost (TTFT tokens count even if interrupted). A-latency.md's "cap to 1 cancel per 8s" is in the recommendation but easy to forget when porting from POC.

**Symptom:**
- Gemini-side billing spikes vs reaction count baseline
- `events.jsonl` shows >3 `interrupted=True` outcomes per 60s sustained
- Bravoh proxy 429 rate climbs from <1% to >5% under viral load
- Users hit "free-tier daily cap" much faster than 100/day rate-limit math suggests

**Prevention:**
- Hard cap `CANCEL_COOLDOWN_S = 8.0` (per A-followup-1 §"Recommended pattern for v2 predictive backpressure") — refuse to cancel more than 1/8s regardless of event priority
- Soft cap 30 cancels per session — beyond this, log loud telemetry and stop cancel-firing for the session
- Per-session telemetry assertion in `coach_loop`: if `interrupted=True` count >3/min sustained over 5 ticks, emit `cancel_rate_excessive` to `events.jsonl` and force-disable cancel for remaining session
- Test: synthetic burst-event harness fires 20 events in 30s; assert ≤3 `interrupted=True` outcomes

**Phase to address:**
Phase that implements the latency stack (predictive firing + cancel-and-refire). Cancel-cap belongs in the same Wave as the cancel-fire implementation, not as a follow-up.

---

### Pitfall 2: Citation Linter Strips Entire Live Response → Empty Voice + Ack-Bank-Only Fallback Bug

**Severity:** Critical (user-visible silence on real events — fails the "real DJ friend in your ear" bar)

**What goes wrong:**
Live-mode citation linter enforces response-level stripping (E-followup-1 §"Stripping unit"): if a live response contains zero valid citations, drop the whole reply and fall back to the pre-canned ack bank. If Gemini ignores the citation grammar instruction on a given turn (preview-model behavior is non-deterministic), the linter eats the whole response. The fallback path then plays only an ack ("yeah") with no actual DJ commentary — the user hears the AI noticing but never saying anything substantive. Repeated 3-4 times in a row, this reads as "AI is broken" or "AI has nothing to say."

**Why it happens:**
The linter has two failure modes: (a) Gemini emitted text but used no citations (prompt-following drift), (b) Gemini emitted citations but they don't match the Evidence registry (citation hallucination). Both result in response-level strip. The ack bank fallback is correct for ONE turn — not for sustained turns. E-followup-1 §"Failure modes covered" only covers single-response failure semantics.

**Symptom:**
- `events.jsonl` shows `mode=live` + `accepted=""` for ≥3 consecutive turns
- User reports: "AI grunts but doesn't say anything"
- Stripped-response rate >10% on live mode (E-followup-1 §"Telemetry as product surface")

**Prevention:**
- Telemetry guard: if `stripped_rate_15s > 0.4` (40% of recent responses stripped), the next response BYPASSES the linter and is allowed through with a `[unverified]` console-only log marker. Anti-slop bar relaxed temporarily to keep the conversation alive.
- The linter logs `linter_silence_streak=N` to `events.jsonl`. Phase 16 (Kaan's ear-test) MUST replay a session with `linter_silence_streak > 2` and assert it doesn't happen on real DJ sets.
- Prompt-side mitigation: append `"If you cannot cite, say 'I'm listening' — never reply with empty text"` to live mode system instruction. Forces Gemini to fail toward a graceful unsourced-but-honest line rather than a stripped void.
- Test: replay `events.jsonl` from a 30-min Kaan session through the linter; assert `stripped_rate < 0.15` overall.

**Phase to address:**
Citation linter phase (live mode shipping). Must land WITH the telemetry guard and the bypass-on-streak escape hatch — not as a v2.x follow-up.

---

### Pitfall 3: djay Pro Mac Overlay AX Call Made From Python Sidecar Instead of Rust Parent

**Severity:** Critical (would make the headline viral demo feature unusable on installed binaries)

**What goes wrong:**
The djay Pro highlight overlay needs to read window bounds via `AXUIElement` (or `kCGWindowBounds`). Tauri issue #8329 confirms sidecar processes do NOT reliably inherit Accessibility (AX) permission from the bundled parent app on macOS — even though the parent has been granted TCC. The user grants vibemix AX permission in System Settings, the parent works, the Python sidecar tries to call `Quartz.CGWindowListCopyWindowInfo` and gets stale/empty data. The overlay draws at (0,0) or stops drawing entirely. This kills Beat A of the viral demo ("AI points at the knob") — the single most differentiating frame.

**Why it happens:**
The instinct is "I already have pyobjc in the Python sidecar, call AX from there." The Tauri tooling makes IPC look more expensive than it is. Without explicit policy, the engineer who picks this up later will probably default to sidecar.

**Symptom:**
- Overlay draws at wrong screen position OR doesn't draw at all on installed binary (works fine in `tauri dev` because dev signing inherits more permissively)
- First-run user reports: "I granted permission but the highlight is off-screen / invisible"
- `events.jsonl` shows `highlight_skipped: reason=ax_no_position` in sustained streaks

**Prevention:**
- Implement the AX/Quartz call in `tauri/src-tauri/src/djay_ax.rs` (Rust parent process) — confirmed by synthesis-viral-demo §"Day 1: AX bridge in Rust parent"
- Expose as a Tauri command `get_djay_window_rect()` over IPC; sidecar Python NEVER calls AX directly for djay window bounds
- Pre-flight Day-0 spike (synthesis-viral-demo §"Critical path"): 1-hour test confirming `kCGWindowBounds` readable from Rust parent on a code-signed bundle without re-prompting TCC
- Lint rule (codebase grep gate, like Phase 11's no-pydantic gate): `! grep -rn "Quartz.CGWindowListCopyWindowInfo\|AXUIElement" src/vibemix/runtime/highlight/` in the highlight overlay package — fails CI if AX called from Python
- Test: install signed binary on fresh non-dev macOS, grant AX, launch djay, fire highlight — assert ring appears at correct window-relative position

**Phase to address:**
djay Pro overlay phase. AX-from-parent must be the FIRST wave of that phase; everything else depends on it.

---

### Pitfall 4: Tauri `visible_on_all_workspaces` Doesn't Cover Fullscreen Spaces on macOS — Overlay Vanishes When DJ Goes Fullscreen

**Severity:** Critical (kills the demo on the most common pro-DJ workflow — fullscreen djay)

**What goes wrong:**
The overlay window uses `visible_on_all_workspaces(true)` per `mascot_window.rs` builder. Tauri issue #11488 confirms this DOES NOT cover macOS fullscreen Spaces — when djay Pro enters fullscreen, it lives on its own Space and the vibemix highlight overlay stays behind on the previous Space. The user sees the AI talking, the mascot reacting, but no rings on the djay UI. The viral demo storyboard (synthesis-viral-demo §"Setup") explicitly notes: "djay Pro 5 in 2-deck mode, full-window, **NOT fullscreen** (fullscreen Space breaks the overlay per C-bucket Tauri #11488 — verified)." But pro DJs use fullscreen by default during live sets.

**Why it happens:**
The mascot already works "everywhere" via `visible_on_all_workspaces`, so the engineer assumes the highlight overlay will too. The fullscreen-Space behavior on macOS is a separate code path that Tauri 2 hasn't reached yet.

**Symptom:**
- Demo recording is fine (windowed mode), production use fails (fullscreen mode)
- User in r/Beatmatch: "I love the idea but the rings only work when djay isn't fullscreen — that's never"
- `events.jsonl` shows `highlight_fired=true` but user never sees them

**Prevention:**
- Detect djay fullscreen state at runtime (Quartz: `kCGWindowLayer != 0` AND window bounds match screen bounds with menubar adjustment). When detected, show a non-blocking toast: "Highlights work best in windowed djay — full-screen Spaces hide overlays (macOS limitation)."
- Track Tauri issue #11488 via dependency-watcher; auto-create issue when it merges
- Alternative path: `set_activation_policy(Accessory)` workaround documented in C-ui-overlay.md — Dock icon disappears though, which is its own UX cost. Don't ship by default.
- Document in README + onboarding card: "Best in windowed mode. Fullscreen support tracking macOS limitation."
- Test: take a screen recording showing the windowed-mode behavior; explicitly note in the demo film script the windowed mode

**Phase to address:**
djay Pro overlay phase. Detection + toast goes alongside the overlay implementation, not as a polish follow-up.

---

### Pitfall 5: Apple Developer ID Issuer ID Not Provided / Wrong .p8 Key → Notarytool Fails at Day-Zero

**Severity:** Critical (blocks v2.0 ship until resolved — single-engineer dependency)

**What goes wrong:**
Apple Developer ID code signing requires the Issuer ID (UUID from App Store Connect → Users + Access → Integrations → API), the Key ID, AND the corresponding `.p8` private key. `notarytool` (Xcode 13+) takes all three. If Issuer ID is missing or wrong, `notarytool submit` fails with `400` and the build pipeline cannot ship a notarized DMG. SYNTHESIS §"Blocks v1.0 ship" #1 calls this out. Kaan must provide it; agent cannot retrieve.

**Why it happens:**
The Apple developer portal hides the Issuer ID in a single place that's easy to miss (page header on the API page, NOT a separate field). Engineers often confuse Issuer ID with Team ID (10-char alphanumeric) or with the .p8 filename's KEY_ID portion. App-specific password from appleid.apple.com is an alternative path that works for `xcrun altool` but is DEPRECATED for notarytool.

**Symptom:**
- Release pipeline (GitHub Actions release.yml) fails on `notarytool submit` step with `Error: HTTP status code: 400 Bad Request`
- Manual DMG sign on Kaan's rig succeeds but notarization step hangs
- First user installing DMG sees "vibemix.app is damaged and cannot be opened" Gatekeeper prompt

**Prevention:**
- BEFORE Phase that touches signing: Kaan provides `APPLE_ISSUER_ID` + `APPLE_KEY_ID` + `APPLE_PRIVATE_KEY` (p8 contents) to GitHub Actions secrets
- Pre-flight test: run `notarytool history --issuer $ID --key-id $KID --key $P8` from CI — must return a valid response (even empty list is OK). Fails CI if credentials wrong.
- Dual-path fallback: if notarytool fails, log loud error + skip notarization, mark DMG as "test-only" so the release.yml doesn't publish it as the production manifest
- Day-zero rehearsal on fresh non-dev macOS (Pitfall 17 below) catches stapler-missing case before users hit it

**Phase to address:**
Apple Developer ID sign + notarize phase (absorbs v0.1.0 outstanding). Kaan-blocked dependency must be resolved Day 1 of that phase.

---

### Pitfall 6: SignPath Foundation OSS Application 1-Week SLA → Windows MSI Unsigned at Launch

**Severity:** Critical (Windows SmartScreen warns "malicious software" on every first install; reputation rebuilds over weeks)

**What goes wrong:**
SignPath Foundation provides free code-signing for OSS projects, but the application + approval cycle is ~1 week (B carry-over from Phase 1). If the application isn't filed Day 1 of v2.0 (or wasn't filed during v0.1.0), the Windows MSI ships unsigned at launch. Even with SignPath signing, SmartScreen reputation building takes additional time (Windows uses install-count + flag-count over weeks). First user clicks "Download" → Windows warns "Microsoft Defender SmartScreen prevented an unrecognized app from starting" → high abandon rate on download.

**Why it happens:**
SignPath is free but the engineer treats it as "I'll do this last." The application form needs: GitHub repo URL, open-source license proof, identity verification of Kaan. STATE.md "Open To-dos" lists "File SignPath Foundation OSS application on day 1 of Phase 1 (lead time ~3 weeks)" — if Phase 1 was completed without filing, the SLA bites at v2.0 ship.

**Symptom:**
- GitHub release Windows MSI signed by ad-hoc key OR unsigned
- First Windows install: SmartScreen blue screen "Microsoft Defender SmartScreen prevented..." → user must click "More info" → "Run anyway"
- Abandon rate on Windows download >40% (vs ~10% on macOS signed DMG)
- HN thread: "Tried to install on Windows, got a virus warning, noped out"

**Prevention:**
- Verify SignPath application status via `gh issue list --search "signpath"` or direct application portal — confirm it's filed and approved before Phase that builds Windows MSI
- If SignPath not approved by Day 7 of v2.0: apply SECONDARY signing via Kaan-purchased EV cert (~$200/yr, instant SmartScreen reputation) — budget gate
- Day-Zero install rehearsal on fresh Windows VM (Phase 20 / Day-Zero Ops) catches SmartScreen behavior before launch
- README "Windows install" section preemptively explains SmartScreen warning + "click More info → Run anyway" with screenshots
- Track Windows download → install → first-launch funnel in launch-day telemetry (anonymous OS+version, no PII)

**Phase to address:**
Ship/Sign/Release matrix phase. SignPath check should be the FIRST gate in that phase — block phase entry if application not filed.

---

### Pitfall 7: Updater Manifest Signing Variable Name Mismatch (`TAURI_UPDATER_KEY_PASSWORD` vs `TAURI_UPDATER_PRIVATE_KEY_PASSWORD`)

**Severity:** Critical (silently breaks auto-update for ALL shipped users; only catches at first updater pull)

**What goes wrong:**
The Tauri updater signs the manifest with a private key. The GitHub Actions secret name + the local variable name + the Tauri config field name must all match. Tauri docs use `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` in some places and `TAURI_UPDATER_KEY_PASSWORD` in others; release.yml may have one and `tauri.conf.json5` may reference the other. The build appears to succeed (just uses an empty password) but signs the manifest with a wrong/default key. When users hit the updater endpoint, signature verification fails silently → users never get auto-updates → must manually re-download every release.

**Why it happens:**
Tauri's environment-variable naming has drifted between v1 and v2; documentation lags. The CI passes (signing didn't fail catastrophically), so the bug only surfaces when the FIRST shipped user tries to auto-update — usually weeks after launch.

**Symptom:**
- v2.0.1 release ships, no users auto-update
- Manual check: `curl -s https://api.altidus.world/updater/latest.json` returns manifest, but `signature` field is empty or wrong
- Tauri updater log on client: `Failed to verify signature`
- All users stuck on v2.0.0

**Prevention:**
- Codify env var name in `tauri/src-tauri/tauri.conf.json5` updater config; add a Day-Zero test that signs a manifest and verifies the signature using `@tauri-apps/cli signer verify` (or equivalent) BEFORE the release.yml uploads
- Audit ALL three locations: `release.yml`, local `.env` (if any), `tauri.conf.json5`. Grep all repos for `TAURI_UPDATER` — assert exactly one canonical name across all
- First-release smoke test: build v2.0, install on fresh VM, build v2.0.1 with one trivial change, watch updater fire on VM
- Track Tauri docs evolution; pin to `tauri-cli` version that matches the docs at lock time

**Phase to address:**
Ship/Sign/Release matrix phase. Updater verification test goes alongside DMG sign / MSI sign tests, all in one phase.

---

### Pitfall 8: Pre-Canned Ack Rotation Collision → Same "yeah" Twice in 30s = AI Slop Tell

**Severity:** Critical (single-issue trust-breaker — the entire "real DJ friend" thesis cracks)

**What goes wrong:**
The ack bank ships ~40 OPUS samples organized by event class. A simple `random.choice()` picks one. Without rotation memory, the same sample plays twice within 30 seconds with probability ~`1/N` per fire — at 40 samples and 5 fires/min, the collision rate is ~5-8%. The viewer who notices "wait, it just said 'yeah' twice in a row" cracks the illusion. A-latency.md §"Risk mitigation" calls this out: "Never reuse same sample within 30s."

**Why it happens:**
The naive implementation is `random.choice(ack_bank)`. The clean rotation implementation needs a `deque(maxlen=10)` recent-history filter + per-event-class buckets + intensity binning. Easy to skip the deque in a hurry.

**Symptom:**
- User testing: "It just said 'yeah' twice in 20 seconds, lol — that's AI"
- Demo clip viewers comment: "Why does the AI say the same thing over and over?"
- Telemetry: ack-bank-collision rate > 2% over a session

**Prevention:**
- Implement rotation deque per event-class bucket (drop_hit / track_change / mix_move / generic_filler / silence_break)
- Rule: `ack_recent: deque(maxlen=10)` — eligible = `[s for s in bank if s not in ack_recent]`; if exhausted, clear deque
- Per-event-class filtering: never play a `mix_move` ack on a `track_change` event
- Test: synthetic burst of 60 ack-fires across 60s; assert zero collisions within sliding 30s window
- Phase 16 ear-test gate: Kaan listens to 30 min of acks-in-context; if he flags ANY collision feel, the rotation logic ships with smaller bucket-per-class sizing

**Phase to address:**
Latency stack phase (ack bank ship). Rotation logic is part of the ack bank, not a follow-up.

---

### Pitfall 9: Mascot Anticipation Layer Fires on Misfire → False-Positive Lean-In Then Nothing

**Severity:** Critical (breaks the anti-slop visual contract — mascot becomes the AI slop tell)

**What goes wrong:**
The mascot 4-layer additive state machine fires `prep_lean_in_hyped` the instant `EventDetector.detect()` returns an event — BEFORE the Gemini round-trip resolves. If Gemini fails to generate (timeout, citation linter strips entire response, generation cancelled by higher-priority event), the user sees the mascot lean forward enthusiastically then snap back to idle with no audio. This reads as "AI is broken" or "AI got excited about nothing." Beat B of the viral demo ("anticipation lean-in BEFORE voice") becomes the worst tell instead of the best one.

**Why it happens:**
D-mascot-emotion.md §"Anticipation recipe" treats the lean-in as if Gemini WILL respond. The failure case isn't designed for. The citation linter (E-followup-1) AND the cancel-and-refire logic (A-followup-1) BOTH introduce new ways the round-trip can produce no audio.

**Symptom:**
- Video reviews: "Why did the bat lean in if it had nothing to say?"
- User reports: "The mascot acts hype then stops, looks broken"
- `events.jsonl` shows `mascot_anticipation_fired=true` AND `accepted=""` for same event

**Prevention:**
- Anticipation timeout: if no audio arrives within 2.5s of anticipation-fire, gracefully crossfade prep → `settle_down` (D's `prep_settle` clip) — reads as "AI heard something but lost the thought," not as "AI broken"
- Cancel-aware: when `SpeechHandle.interrupt(force=True)` fires, IMMEDIATELY crossfade mascot to settle (not back to idle directly — that snap is visible)
- Citation-linter-aware: when the linter strips the entire response, fire `settle_down` clip + the ack-bank-fallback ack
- Renderer max-age guard: every additive layer has `expiresAt` — if `anticipation.expiresAt < now` for >2s, force-clear (D-mascot-emotion.md §"Risk: Mascot stuck on wrong layer")
- Test: synthetic event-burst with 50% Gemini-fail rate; assert mascot never wedges in lean-in pose for >3s

**Phase to address:**
Mascot 4-layer state machine refactor phase. Timeout + cancel-aware crossfade ship WITH the anticipation layer, not as v2.x polish.

---

## High Pitfalls

### Pitfall 10: Predictive Misfire Rate Wastes Gemini Tokens at Hard Tek BPM Rates

**Severity:** High (degrades cost economics; not user-visible but bleeds budget)

**What goes wrong:**
Predictive firing triggers `generate_reply()` ~2 bars BEFORE the drop on `buildup_score > 0.7`. If the build doesn't resolve to a drop (false buildup, filtered breakdown, fake-drop trick), the prediction is cancelled — wasted Gemini tokens. A-latency.md §"Risk + watchouts" says misfire cost = canceled Gemini call. At Hard Tek 170+ BPM with frequent fake-drop tricks (Speedy J, Surgeon), misfire rates can hit 30%+. 1 cancel per 12s cap helps but doesn't eliminate.

**Why it happens:**
`buildup_score` is a heuristic (hi_share_rising × snare_density × filter_sweep × phrase_boundary_proximity). It's tuned for "drop coming" but Hard Tek genre signature includes "fake drops" — the build resolves into a breakdown or stripped section. A4 in the latency assumptions log calls this out: "Buildup detector at 0.7 threshold catches >70% of real drops in Hard Tek without false-positiving on filtered breakdowns — RISK if wrong: predictive firing rate misjudged."

**Symptom:**
- Per-session telemetry: `predicted_drop_misfire_rate > 0.25`
- Bravoh proxy usage spikes per session, no corresponding reaction count increase
- 50€/mo per-user budget exhausted by day 18 instead of day 30

**Prevention:**
- Conservative threshold: ship v2.0 with `buildup_score > 0.85` (not 0.7) — fewer fires but higher precision (A-latency.md §"Open question for Kaan #1")
- Hard cap predictive fires to 1 per 12s
- Telemetry: per-session `predicted_drop_misfire_rate`; if >0.3 sustained, log loud + disable predictive for the session
- Phase 16 Kaan-ear-test gates predictive firing — Kaan listens to 30 min of real Hard Tek sessions; if he flags ANY false anticipation, threshold goes higher
- Per-genre tuning: predictive ENABLED for techno/house (clean buildups), DISABLED by default for hard-tek/acidcore until F1 ear-test passes (v2.0 → v2.0.1 staged rollout)

**Phase to address:**
Latency stack phase. Conservative threshold + telemetry guard ship together.

---

### Pitfall 11: Caching Falls Below 1024-Token Floor After Prompt Diet → Silent Cache Miss

**Severity:** High (silent regression — TTFT win disappears with no error)

**What goes wrong:**
Gemini context caching requires `gemini-3-flash-preview` cached content ≥1024 tokens. vibemix's system instruction is ~1250-1400 tokens — squeaks past. The latency stack's "prompt diet" recommendation (A-latency.md §1) says trim per-turn parts. If the engineer ALSO trims the cached system instruction (or the cached padding content), tokens drop below 1024 and the cache silently stops applying — no error, just `prompt_cached_tokens=0` in metrics. TTFT win disappears (1500ms regression) with no loud signal.

**Why it happens:**
The 1024-token floor is documented but easy to forget mid-tuning. A-followup-1 §"Critical implication for vibemix" calls it out: "If we trim the system instruction further as part of A's prompt-diet recommendation, we risk falling below 1024 and losing cache eligibility entirely. The two latency wins partially fight each other."

**Symptom:**
- TTFT regresses ~1500ms with no code change correlating
- `livekit/plugins/google/llm.py:475` shows `prompt_cached_tokens=0` after cache was supposedly created
- Bravoh proxy uncached-input bill goes up 10×

**Prevention:**
- Mandatory padding block in cached content (A-followup-1 §"Mitigation"): controller MIDI map JSON dump, event taxonomy enum, deck-naming convention, voice persona spec — deterministic + invariant across turns, pads to ~1400-1600 tokens
- Startup assertion: `client.models.count_tokens(model=..., contents=SYSTEM_INSTRUCTION + PADDING).total_tokens >= 1100` — fails fast if below floor (with margin)
- Metric assertion in `coach_loop`: after first 3 turns, if `prompt_cached_tokens == 0` for all of them, emit `cache_miss_critical` log line + alert
- Test: snapshot the cached payload size in CI; fail if dips below 1100 tokens

**Phase to address:**
Latency stack phase (caching implementation). Padding + token-count assertion ship together with the cache creation code.

---

### Pitfall 12: Evidence Registry Race Condition — Linter Validates While Event Being Written

**Severity:** High (intermittent linter false-strips on legitimate citations)

**What goes wrong:**
The citation linter's `CitationLinter._index` is read by the linter's `validate()` call (from `llm_node` accumulating Gemini output) and written by `EventDetector.detect()` (in the `state_refresh_loop` @10Hz). If Gemini cites `[ev:KICK_SWAP@t]` that just happened in the last 50ms and the linter tries to validate while `EventDetector` is mid-write to `_index`, the lookup misses → valid citation incorrectly stripped → user hears truncated response. Python's GIL gives atomic dict.set() but NOT atomic dict.setdefault() + list.append() pattern shown in E-followup-1.

**Why it happens:**
The linter design is "O(1) lookup" — assumes the index is stable at lookup time. The 100ms `state_refresh_loop` tick can write to `_index` simultaneously with a linter read in `llm_node` (different coroutine, different stack frame). asyncio.Lock not designed-in.

**Symptom:**
- Intermittent (~1-3%) live-mode citation strips on events that ARE in the log
- `events.jsonl` shows event registered, linter logs `invalid_citation` for same event 50ms later
- Phase 16 Kaan-ear-test: "the AI said something then trailed off"

**Prevention:**
- Wrap `CitationLinter._index` access in `asyncio.Lock` — `register_event()` and `_is_valid()` both acquire
- OR (simpler) use `collections.deque` per (source, key) with thread-safe `.append()` — read with snapshot copy via `list(deque)` at validation time
- Test: spawn 100 concurrent registers + validates against a populated index; assert zero false-strips

**Phase to address:**
Citation linter phase. Lock-or-deque design ships in the first cut, not as v2.x patch.

---

### Pitfall 13: Multi-Monitor Y-Flip Coordinate Trap (macOS Quartz vs NSScreen)

**Severity:** High (overlay draws on wrong screen for ~40% of multi-monitor users)

**What goes wrong:**
macOS Quartz coordinates have origin at top-left of the primary display; secondary displays can have negative Y. `NSScreen.Screens` flips Y so its origin is at bottom-left of the bottom-most display. Mixing the two systems silently puts the overlay one screen off. C-ui-overlay.md §"Coordinate gotchas" calls this out, citing the Swindler issue #62. The mascot already worked single-screen; the highlight overlay must work across monitors because pro DJs use dual-screen (laptop + external) setups.

**Why it happens:**
Most code samples online mix the two coordinate spaces. Pro DJs are exactly the audience that has a second screen for djay Pro. The bug doesn't surface on Kaan's single-monitor dev setup.

**Symptom:**
- Multi-monitor users report: "The highlight ring appears on my other screen, not on djay"
- Specific to: laptop primary display + external secondary with djay fullscreen
- Trackable: `events.jsonl` shows correct window-rect detection but overlay window positioned wrong

**Prevention:**
- Use Quartz coords (top-left origin, Y grows down) consistently throughout — DON'T touch `NSScreen.frame` unless flipping Y
- Document the contract in `djay_ax.rs`: "All coordinates Quartz/CGWindow space, NEVER NSScreen — see https://github.com/tmandry/Swindler/issues/62"
- Test rig: dual-monitor smoke test (CI matrix or Kaan rig with external display) — assert highlight draws on correct screen for both primary+secondary djay positions
- Tauri side: `WebviewWindowBuilder.position(x, y)` accepts physical pixels — convert from Quartz logical points via `window.scale_factor()`

**Phase to address:**
djay Pro overlay phase. Coordinate-system contract documented + dual-monitor test in same wave.

---

### Pitfall 14: Windows DPI Virtualization Triple-Coordinate-Trap (Per-Monitor + GetWindowRect Caller-DPI + Process Aware)

**Severity:** High (overlay misaligns on every Windows multi-monitor + mixed-DPI setup — common for laptops with 4K external)

**What goes wrong:**
Three independent coordinate-space traps on Windows: (1) `GetWindowRect` auto-scales to caller's DPI awareness — if vibemix is per-monitor DPI-aware and djay is system DPI-aware, the rect is silently rescaled. (2) Different monitors can have different DPI (laptop 150% + external 100%). (3) Tauri windows position in logical coords; the rect we get back is physical pixels. C-ui-overlay.md §"Coordinate gotchas — Windows DPI" calls this out. Result: overlay positioned off by 50-150% on Windows multi-monitor.

**Why it happens:**
DPI-awareness on Windows is famously underdocumented. Most cross-platform code copies the macOS coord handler and assumes "Windows is the same." Tauri 2 abstracts SOME of this but not all.

**Symptom:**
- Windows users with external monitor: "Highlight is way off the djay window"
- Affects ~30-40% of Windows users (any with 4K external + 1080p laptop, or 150% scaling)
- Specific to Windows 10/11 multi-monitor; single-monitor works

**Prevention:**
- Mark vibemix process `PROCESS_PER_MONITOR_DPI_AWARE_V2` at startup (Tauri 2 exposes this)
- Call `GetDpiForWindow(target_hwnd)` to learn djay's actual DPI; rescale rect from target DPI to overlay DPI
- For multi-monitor different DPIs: `MonitorFromWindow(target_hwnd, MONITOR_DEFAULTTONEAREST)` + `GetDpiForMonitor` to get per-monitor scale
- Phase 20 (Day-Zero Ops) MUST include Windows multi-monitor fresh-VM rehearsal with 150% + 100% scaling mix
- Test rig: GitHub Actions windows-latest with simulated multi-monitor (or manual on Kaan's Windows access)

**Phase to address:**
Windows port of djay Pro overlay phase (or general Windows DPI hardening phase). DPI awareness flag set at startup is a one-line fix; the rescale logic is the heavier part.

---

### Pitfall 15: Pyrekordbox XML Library Re-Export Staleness — User Adds Tracks But Library Doesn't Auto-Update

**Severity:** High (vibemix says "I don't have that track in your library" for newly-added tracks — sustained UX confusion)

**What goes wrong:**
Pyrekordbox XML import is one-shot — user exports collection.xml from Rekordbox, vibemix imports. Rekordbox doesn't auto-export, so any track added/modified after the import is invisible to vibemix. The user plays a new track, vibemix says "unknown track" or fails to ground the suggestion. B-followup-1 §"Refresh" says: "No file-watcher. Rekordbox holds the source DB open during a session; even if we watched the XML path, the user has to manually re-export. We expose the refresh as a deliberate UX action, not magic."

**Why it happens:**
The XML path is durable (vs broken SQLCipher); the cost is staleness. The user doesn't think to re-export weekly. Vibemix appears to "forget" their newer tracks.

**Symptom:**
- After 2-3 weeks, user says: "vibemix doesn't know my new tracks even though I added them"
- Reduced grounding quality on recent tracks → AI sounds vaguer
- User abandonment: "It used to work, now it doesn't"

**Prevention:**
- 30-day nudge: settings UI shows "Library last imported 33 days ago — re-export from Rekordbox if you've added tracks"
- Track-not-found counter: if `track_lookup_failed_count > 5` over 24h, automatically prompt "Looks like vibemix is missing some of your tracks — re-import?"
- Re-import wizard streamlined: drag-drop the new XML, vibemix detects TrackID overlap > 80% → incremental reindex (~1s for 1k new tracks), else full reindex
- Confidence-aware grounding: if track lookup confidence <0.5, AI prompt explicitly says "I think this is X" not "X is playing now"
- README documents the re-export workflow with screenshots

**Phase to address:**
Pyrekordbox XML import phase. Nudge logic + re-import wizard ship together (not as v2.x).

---

### Pitfall 16: Track Title Fuzzy Match Collisions — Same Title, Different Artist/BPM → Wrong Grounding

**Severity:** High (vibemix grounds suggestions in the WRONG track's BPM/key/cues — anti-slop violation)

**What goes wrong:**
Pyrekordbox track lookup uses fuzzy title match (B-followup-1 §"Confidence threshold"). Common pop/electronic track titles collide: "Insomnia" by Faithless vs the 20 other tracks called "Insomnia." Without artist/BPM disambiguation, the linter accepts a wrong-but-plausible match. AI grounds in the wrong track's key/BPM → "you've got 12 bars before the 8A clash" but the actual track is 4B, not 8A. Anti-slop violation traceable to grounding-data error, not LLM hallucination.

**Why it happens:**
The fuzzy lookup tries title first, then artist+title, then artist+title+BPM. The first tier is too permissive. If title alone matches and artist is "Various Artists" or empty (common in user libraries), confidence is overestimated.

**Symptom:**
- Phase 16 Kaan-ear-test: "The AI said something about key 8A but my track is 4B"
- Citation linter shows `track:` citation valid (it IS in the library) but the track is the wrong "Insomnia"
- Anti-slop telemetry shows `slop_ratio > 0.1` on track-grounded reactions

**Prevention:**
- Require artist OR BPM match for confidence ≥0.7 (B-followup-1 §"Confidence threshold" already specifies this — verify enforced)
- Add Camelot key as third disambiguation axis when both available
- Conservative default: ambiguous matches drop to "(probable)" tag — AI says "I think this is X" not "X is playing"
- Telemetry: log every `track_match_low_confidence` for review; if a session has >3 ambiguous matches, surface to user "vibemix is unsure about some tracks — check your Rekordbox export"
- Test: synthetic library with 5 "Insomnia" entries; assert lookup with only title returns no high-confidence match

**Phase to address:**
Pyrekordbox XML import phase + library intelligence phase. Disambiguation logic in lookup function shipped both places.

---

### Pitfall 17: First DMG Gatekeeper Warning on Fresh Mac — Notarization Succeeded But Stapler Missed

**Severity:** High (every first-launch user sees scary "may damage your computer" — high abandon rate)

**What goes wrong:**
notarytool can succeed (returned 200) but the staple step is separate. `xcrun stapler staple vibemix.dmg` MUST run on the DMG before upload. If stapling skipped or failed silently, the DMG is notarized but the ticket isn't embedded → user's Mac can't verify offline → Gatekeeper shows "vibemix.app cannot be opened because Apple cannot check it for malicious software." User abandons.

**Why it happens:**
Stapling is a separate command that's easy to omit from release.yml. The CI logs show "notarization successful" but the staple step might be missing entirely. Kaan's dev rig works because he already has the app trusted locally.

**Symptom:**
- Fresh-mac user: "Tried to install, got a Mac warning, gave up"
- Twitter/Reddit: "Is vibemix legit? My Mac says it could damage my computer"
- `spctl --assess --verbose vibemix.app` on fresh Mac: `source=No matching credential found`

**Prevention:**
- Release.yml MUST include `xcrun stapler staple vibemix.dmg` AFTER notarytool submission completes
- Verify with `xcrun stapler validate vibemix.dmg` as a release gate (exit code must be 0)
- Day-Zero rehearsal on fresh non-dev macOS: download DMG → drag-install → first-launch → assert NO Gatekeeper warning
- Include the staple-validate step in release.yml exit gate (fail release if staple-validate fails)

**Phase to address:**
Ship/Sign/Release matrix phase. Stapling is part of the macOS sign workflow, not a separate step.

---

### Pitfall 18: Citation to Non-Existent Event — Wrong Timestamp Within Tolerance Window → Strip

**Severity:** High (AI claims event at t=0:42 that was actually at t=0:45 — citation stripped, sentence lost)

**What goes wrong:**
The linter validates citation timestamps within ±1.0s (live) or ±2.0s (debrief) tolerance. Gemini occasionally generates timestamps that are 2-3s off from the actual event time (preview-model behavior; the audio Part it receives is a snapshot not absolutely time-anchored). E-followup-1 §"Failure modes covered" calls this out as "Citation to non-existent event → strip + log." If Gemini cites `[ev:KICK_SWAP@0:42]` but the actual KICK_SWAP fired at 0:45, the citation fails validation → sentence stripped → response degraded.

**Why it happens:**
Gemini doesn't have absolute timeline pinning. The audio Part is X seconds long; Gemini infers WHERE in the session it is from context but can drift. The tolerance window protects against ±1s drift but not the 2-3s case.

**Symptom:**
- Linter telemetry: `invalid_citation_count > 0.2 × total_citations`
- Reviewing stripped sentences: the events WERE present but timestamps were off by 2-3s
- User feels: AI says less than it should

**Prevention:**
- Increase live tolerance to ±2.0s (matching debrief default) — accept the slop window grows but the strip rate drops
- Prompt mitigation: include `current_session_time={t}` in the evidence packet so Gemini has the absolute anchor
- Telemetry per-session: if `invalid_timestamp_rate > 0.15`, suggest Gemini prompt audit
- Hardened lookup: if exact timestamp fails, search ±5s window for ANY event of the cited type; if found, accept with `(probable)` flag
- Test: replay sessions with deliberately off-timestamps in cited claims; verify recovery rate >90%

**Phase to address:**
Citation linter phase. Tolerance + prompt-mitigation ship together.

---

## Medium Pitfalls

### Pitfall 19: Three.js AnimationMixer Crossfade Discontinuity at Layer-Switch Under Load

**Severity:** Medium (visible jitter on the mascot during heavy events; not breaking but reads as polish-failure)

**What goes wrong:**
Three.js AnimationMixer's `crossFadeTo()` works smoothly under normal load, but the mascot 4-layer additive state machine introduces 3-4 concurrent actions + per-frame additive blending + procedural hip-bob bone update. Under sustained event burst (Hard Tek phase with KICK_SWAP + SUB_LAYER + DISTORTION_CLIMB all firing in 8s), the crossfade between layers can stutter — mascot pose snaps instead of blending. D-mascot-emotion.md §"Risk: Rendering perf budget" says expected cost is +1-2ms/frame on M2; reality can be worse with simultaneous layer activations.

**Why it happens:**
`AnimationUtils.makeClipAdditive()` is required for additive blending but is easy to skip. Mascot pose discontinuities also happen when an `AnimationAction.fadeIn/fadeOut` is interrupted mid-transition by another fade call. The "blendMode" parameter can be silently NormalAnimationBlendMode if additive setup was missed.

**Symptom:**
- Mascot pose snaps visibly when layer changes
- Frame time spikes >16ms during multi-event bursts
- Three.js console warning: "Animation cycle"

**Prevention:**
- Asset-loader pass: `AnimationUtils.makeClipAdditive(clip)` for every layer-2+ clip BEFORE play
- Single AnimationMixer instance with per-layer weight management (NOT multiple mixers)
- Performance budget assertion: per-frame `requestAnimationFrame` time >25ms triggers loud warning
- Test: synthetic 60-second mascot burst (50 events in 60s); assert no `Animation cycle` warnings, frame time p99 <22ms
- Fallback: if frame time consistently >22ms, drop additive layers to single-layer fallback (current behavior)

**Phase to address:**
Mascot 4-layer refactor phase. Performance budget + makeClipAdditive ship together.

---

### Pitfall 20: Beat-Coupled Idle Desync — BPM Detection Drift > 0.5 BPM Over 5 Min

**Severity:** Medium (mascot bobs off-beat after long sets — visible artifact, not breaking)

**What goes wrong:**
Beat-coupled hip-bob is phase-locked to BPM detected via audio autocorr. Over 5+ minutes, BPM detection drifts ±0.5 BPM relative to the actual tempo (especially with tempo-fader changes). The hip-bob phase accumulates error → after 5 min, mascot bob is visibly off the kick. D-mascot-emotion.md §"Beat-sync idle" assumes BPM stays accurate; doesn't address drift.

**Why it happens:**
Autocorr-based BPM is good to ~±0.5 BPM accuracy on most music. Phase-lock over time requires periodic re-sync. Without that, drift accumulates linearly with session time.

**Symptom:**
- User watching mascot mid-set: "It used to be on beat, now it's off"
- Heavy on long techno sets (10-30 min single track sections)
- Trackable: beat-phase vs actual-kick alignment by minute 5

**Prevention:**
- Re-sync beat phase on every downbeat detection (audio onset on band-limited kick) — phase resets to 0 on detected downbeat
- Use Mixxx OSC `/Channel{N}/bpm` when available (sub-1ms latency, perfect accuracy) — fallback to autocorr only when Mixxx absent
- BPM lock acquisition: confidence threshold ≥0.6 (D-mascot-emotion.md notes existing state machine accepts this) — below threshold, mascot bob falls back to amplitude-driven (procedural, no phase-lock needed)
- Test: 30-min synthetic session at 130 BPM; assert beat-phase drift <0.2 phase units (0.0 = on beat, 0.5 = off beat) by minute 30

**Phase to address:**
Mascot beat-coupled idle phase. Re-sync logic ships with the bob driver, not as v2.x.

---

### Pitfall 21: Emote Tag Vocab Gate — Gemini Text Channel Arriving BEFORE Audio (1-Day Spike Required)

**Severity:** Medium (anticipation tag firing degrades to no-op if text lags audio — feature underperforms)

**What goes wrong:**
The inline emote-tag vocab (D-mascot-emotion.md §"Emote tag vocabulary proposal") needs Gemini's text transcripts to arrive BEFORE TTS audio so the mascot can fire anticipation pose from the tag. If transcripts lag audio (which has been observed on lossy connections per livekit-plugins-google docs), the tag-driven anticipation never fires — degrades to "anticipation fires when talk_loop fires" which is what it was before. D-mascot-emotion.md §"Latency note — VERY important" flags this with "Confidence: MEDIUM — needs verification."

**Why it happens:**
Gemini Live API streams text + audio on different channels with no guaranteed ordering. The LiveKit plugin's exposure of the text channel isn't fully documented. The assumption "text-first" holds on stable connections; doesn't hold under network jitter.

**Symptom:**
- Anticipation pose fires AT or AFTER voice (not before) — defeats the perceived-latency mask
- D-mascot-emotion.md A3 in assumptions log: "If transcripts don't precede TTS audio, the mascot anticipation will fire from event-detector directly (T=0 prep clip), with the emote-tag refinement as a phase 2 enhancement."

**Prevention:**
- **1-day spike BEFORE Phase commits to design (D-mascot-emotion.md §"Open questions for Kaan" #1)**: test against actual livekit-plugins-google integration, measure transcript-vs-audio ordering on a typical session
- Fallback: ship anticipation layer driven by `EventDetector` directly (T=0 prep clip), NOT by emote tag — fires reliably before LLM completes
- Emote tag refinement as a v2.0.1+ enhancement once spike confirms feasibility
- Test rig: synthetic Gemini responses with deliberately-lagged transcripts; assert anticipation still fires from event-detector path

**Phase to address:**
Mascot 4-layer refactor phase. 1-day spike runs in pre-phase research; if it fails, the emote tag design is deferred.

---

### Pitfall 22: Mascot Opaque Chrome Regression — Phase 14 v5 Glass Could Inadvertently Reintroduce

**Severity:** Medium (visible UX regression — opaque chrome on mascot was just fixed this session)

**What goes wrong:**
This session (2026-05-13) fixed the mascot chrome being opaque on tokens.css glass-3 background. Phase 14 v5 migration touched all four surfaces (wizard, session, settings, mascot). If a future polish phase or a new v5 chrome variant is introduced (e.g., "glass-4"), the mascot wrapper could be re-styled with opaque background by default. Memory `project_v0_1_0_rc1_open_bugs.md` lists this as recently-fixed.

**Why it happens:**
Mascot wrapper is a transparent border around a Three.js canvas. The default for new chrome variants is opaque. Easy to forget the mascot needs the override.

**Symptom:**
- Mascot has a visible solid background blocking the view behind it
- Visual regression in mascot corner of session UI
- Phase 14 close note: "POLISH-03 (mascot v5 chrome) closed in 14-05" — verify still holds

**Prevention:**
- Test: vitest snapshot of mascot wrapper element computed style — assert `background` transparent OR matches `var(--surface-translucent)`
- Lint rule: ESLint or stylelint rule blocking explicit `background-color: rgb()` on mascot wrapper selector
- Code review checklist for any chrome-touching PR: "Did you check mascot wrapper transparency?"
- Per-session screenshot diff in CI (Playwright) — assert mascot region is visibly translucent against tokens.css background

**Phase to address:**
Any Phase 14-adjacent chrome polish; mascot test goes in the chrome-touching phase's verifier.

---

### Pitfall 23: 21 GLB Clips → Adding ~5 More for Anticipation/Speak Variants Explodes Wheel Size

**Severity:** Medium (installer size grows; one-click install promise erodes)

**What goes wrong:**
Current mascot has 21 GLB animation clips. D-mascot-emotion.md §"Specific new clips to commission" adds 8 new clips (prep_lean_in_neutral, prep_lean_in_hyped, prep_head_turn_left/right, prep_settle, talk_loop_energetic_v2, react_celebrate_alt, dance_alt3). Each GLB ~250-500KB (DRACO-compressed). Total addition ~3MB; wheel size grows accordingly. Memory `project_one_click_install_hard_req` is "HARD requirement" — every dep choice rated green/yellow/red on install impact.

**Why it happens:**
Three.js animation clips don't have an obvious "size budget" awareness. The wheel/installer size growth is gradual — never any single decision that triggers "this is too big."

**Symptom:**
- DMG size grows from ~120MB to ~140MB+
- Tauri wheel size grows beyond expected ~150-250 MB range (A6 phase 11 said "well under 350 MB hard cap")
- First-install download timeouts on slow connections

**Prevention:**
- Per-clip size budget: <300KB DRACO-compressed; reject if larger from asset pipeline
- Total animation budget: ≤15MB for ALL clips combined (21 current + 8 new = 29 clips; budget allows 500KB avg)
- Asset pipeline test: total size of `tauri/ui/public/mascot/*.glb` ≤ 15MB; fails CI if exceeded
- Compress aggressively (DRACO level 7+) for additional clips
- Phase 20 Day-Zero install rehearsal measures actual download time on slow connection (4G) — must complete <60s

**Phase to address:**
Mascot 4-layer refactor phase. Size budget gate ships with the new clip commission.

---

### Pitfall 24: 9 Untested SKUs Ship With Unverified Mapping (Each Needs 30-min Mido Sniff)

**Severity:** Medium (Kaan owns FLX4 only; 9 SKUs have JSON-derived mappings, may not match actual hardware)

**What goes wrong:**
Phase 9 already shipped 10 MIDI controller profiles (DDJ-FLX4 verified + 9 from JSON/Mixxx/manufacturer charts). B-followup-1 §"Per-SKU snapshot" caveats: FLX10 / SX3 / XDJ-RX3 / Numark Mixstream Pro+ are `[ASSUMED]` — engineer must sniff. STATE.md notes Phase 9 close: "9 controller JSONs ship 'verified by JSON only' with `notes` flag — Kaan owns FLX4 only; live verification deferred to Phase 16/20/community PRs."

**Why it happens:**
Pioneer keeps CC numbers consistent within the DDJ family but other SKUs and other vendors diverge. The JSON-only approach is a reasonable starting point but each controller needs its actual MIDI wire validated. Without sniff, the wrong CC number = the EQ knob seems dead.

**Symptom:**
- User reports: "I'm using a DDJ-SX3 and vibemix doesn't see my EQ moves"
- Specific to Pioneer SX3 / FLX10 / XDJ-RX3 / Hercules / Numark
- `events.jsonl` shows MIDI messages flowing but `MidiEvent.field=None` (mapping miss)

**Prevention:**
- Per-SKU sniff form: a 30-min walkthrough script (`scripts/sniff_controller.py`) the user runs to capture actual CC/note for each control. Output uploaded as a community PR.
- Phase 16 / Phase 20 explicitly include "test each non-FLX4 SKU when available" — track in deferred-items.md
- Community contribution path documented in CONTRIBUTING.md (memory project mentions controller-mapping contribution path as most likely external PR)
- Telemetry: track per-SKU `mapping_match_rate` over real sessions; if a SKU has <0.5 match rate sustained, flag as "needs sniff"
- Fallback: generic-MIDI mode (already shipped Phase 9) — degrades gracefully but loses semantic context

**Phase to address:**
10-SKU MIDI controller library extension phase. Sniff tooling ships alongside the controller library; community PR path documented.

---

### Pitfall 25: DDJ-FLX4 Sync Note `0x60` vs Mixxx Canonical `0x58` Disagreement

**Severity:** Medium (sync button on FLX4 not firing; specific to this controller mode)

**What goes wrong:**
`cohost_v4.py:599` has Sync at note `0x60`. The Mixxx FLX4 mapping has Sync at `0x58`. B-followup-1 §"3" surfaces this: "One of them is wrong, or they refer to different controller modes (FLX4 has Pioneer-native and MIDI modes with different note maps)." If shipping pulls the v4 value but the controller is in MIDI mode (or vice versa), Sync presses go undetected.

**Why it happens:**
Pioneer ships FLX4 with two MIDI modes: native (proprietary) and Mixxx-MIDI-compatible. The note assignments differ. Kaan's controller may be in one mode; the JSON profile may target the other.

**Symptom:**
- Sync button presses don't appear in `events.jsonl` as MIDI events
- Kaan reports: "I press sync, AI doesn't see it"
- Mido sniff vs profile JSON disagreement

**Prevention:**
- 5-minute mido sniff resolves (B-followup-1 §3): boot controller, run sniffer, press Sync, record actual note number
- Profile JSON includes BOTH mode entries: `0x60` and `0x58` as alternates; matcher tries both
- Document in controller profile JSON `notes` field with clear "verified against MIDI mode X" attestation
- Test: after sniff, byte-equivalent integration test pins the verified value

**Phase to address:**
10-SKU MIDI controller library phase. Sniff resolution ships as a Day-1 verification step.

---

### Pitfall 26: Gemini Embedding 2 AAC/M4A Tracks Require Transcoding Via pydub (Extra Dep)

**Severity:** Medium (macOS iTunes libraries are full of .m4a — without transcode, half the library fails embedding)

**What goes wrong:**
Gemini Embedding 2 accepts MP3 and WAV ONLY (F-library-intelligence.md §"Formats"). macOS music libraries are dominated by AAC/.m4a (iTunes default). Without pydub-based transcoding, ~60% of a typical Mac library can't be embedded. pydub requires ffmpeg under the hood (~20MB bundled). Memory `project_one_click_install_hard_req` says every dep choice rated green/yellow/red on install impact.

**Why it happens:**
Embedding API gotcha is documented but not until F-research. The naive implementation tries to embed a .m4a directly → API rejects → silent skip.

**Symptom:**
- Library indexing reports "5,000 tracks scanned, 2,100 embedded" — gap is .m4a tracks
- User confused why their library isn't fully indexed
- F-bucket §"AAC/M4A transcoding" calls this out

**Prevention:**
- pydub + ffmpeg in installer (F bucket says "~20MB to the installer. Acceptable.")
- Transcode at ingestion: if path is .m4a/.aac, transcode to 128kbps MP3 BEFORE embed call
- Cache the transcoded MP3 in `~/Library/Application Support/vibemix/library/cache/` so re-indexing doesn't re-transcode
- Progress UI: show "Transcoding AAC tracks..." as a separate progress phase so user knows what's happening
- macOS: also try `afconvert` (system-bundled) as a lighter fallback before pydub

**Phase to address:**
Library intelligence phase. Transcoding ships in the indexing pipeline; ffmpeg bundling ships in Phase 20 / installer phase.

---

### Pitfall 27: sqlite-vec Wheel Availability Changes Per Platform — Fallback to numpy.float32 BLOB Ranking

**Severity:** Medium (if sqlite-vec wheels break on a target OS, embedding queries fail silently)

**What goes wrong:**
sqlite-vec is the picked vector store (F-bucket §"Vector store recommendation"). Wheels ship for Mac arm64/x64 + Windows. If a future sqlite-vec release breaks a wheel for one of those platforms (semi-common in pre-1.0 projects — current v0.1.9), library queries fail on that platform. User experience: "search by vibe" works on Mac, doesn't work on Windows. F bucket says fallback exists: "Bravoh's pattern — store embedding as `numpy.float32.tobytes()` in a BLOB column, do top-k ranking in Python with `np.dot`. At 30k × 1536 this is ~6ms in pure numpy."

**Why it happens:**
sqlite-vec is at v0.1.9 (March 2026 release). 7.6k stars but pre-1.0. Wheel availability can shift across releases or Python versions.

**Symptom:**
- sqlite-vec import fails on a specific OS/Python combination
- Library search returns "no results" silently
- User reports: "search isn't working on my Windows machine"

**Prevention:**
- Abstract behind `LibraryStore` interface: `sqlite_vec_store.py` and `numpy_fallback_store.py` both implement it
- Auto-detect at startup: try to import sqlite-vec; if fail OR if `vec0` virtual table can't be created, fall back to numpy BLOB pattern
- Pin sqlite-vec version in `requirements.txt`; don't auto-upgrade
- Wheel availability check at CI: install on Mac arm64, Mac x64, Windows latest, all Python 3.12 — block release if any fail
- Test: integration test runs with both backends, asserts feature parity

**Phase to address:**
Library intelligence phase. Backend abstraction shipped Day 1, not as a v2.x patch.

---

### Pitfall 28: Embedding Indexing Cost for 30k-Track Library — User Consent Gate Missing

**Severity:** Medium (silent $432 cost for a hoarder library running on Bravoh's key)

**What goes wrong:**
F-bucket §"One-time index cost projection" shows 30k tracks = $432 one-time embed cost (paid Gemini tier). The expected free-tier flow has user provide their own Gemini API key for indexing (their free RPM/TPM handles it). But if vibemix proxy is configured to handle indexing and the user has 30k tracks without explicit consent gate, Bravoh eats $432 per such user. At 10 hoarder users, $4,320 — out of the 50€/mo budget.

**Why it happens:**
The free-tier policy proposal (F bucket) is "BYO key for indexing, vibemix proxy handles live queries." If the policy isn't enforced in code, the indexer falls back to whatever's available (could be proxy).

**Symptom:**
- Bravoh proxy bill spikes when a Pro-DJ user installs vibemix
- Single user's library indexing tops $200+ via proxy
- No user-side prompt: "Your library is large — please provide your own API key for indexing"

**Prevention:**
- Library size gate: if user library >500 tracks AND user hasn't provided BYO key, show consent screen: "Your 5,234-track library will cost $X to index. Provide your Gemini API key for free indexing, or use Bravoh proxy (subject to free-tier daily caps)."
- Hard cap: vibemix proxy refuses indexing for libraries >500 tracks (F bucket alternative proposal)
- Telemetry: log per-user `index_cost_estimated` vs `proxy_used` ratio
- README + onboarding documents the BYO key path with screenshots

**Phase to address:**
Library intelligence phase. Consent screen + cap logic ship with the indexing UI.

---

### Pitfall 29: File-Watcher Native API Edge Cases (FSEvents vs ReadDirectoryChangesW Edge Cases — Symlinks, NFS, Network Drives)

**Severity:** Medium (silent missed-changes on edge-case mounts; library appears stale)

**What goes wrong:**
The library file-watcher uses `watchdog` library which wraps FSEvents (macOS) / ReadDirectoryChangesW (Windows). Edge cases: symlinks (FSEvents doesn't follow by default), NFS mounts (FSEvents doesn't fire at all for NFS), Windows network drives (some SMB versions don't fire ReadDirectoryChangesW). DJ users often have their library on external SSDs that may mount via these mechanisms. Silent missed changes → library appears stale even though file watcher claims to be running.

**Why it happens:**
File-watcher reliability is platform-OS-mount specific. The `watchdog` docs document the gotchas but not the practical implication for DJ libraries on USB/external mounts.

**Symptom:**
- User: "I added tracks but vibemix doesn't see them"
- Watcher logs "running" but no events on external mount
- Affects ~20-30% of pro DJs (external library drive common)

**Prevention:**
- Detect mount type at startup: parse `mount` output / `WMI Win32_LogicalDisk` → if NFS/SMB/symlink involved, fall back to polling mode (scan directory every 60s)
- Manual refresh button always available in settings UI ("Re-scan library now")
- Document supported mount types in README; recommend local-disk library for best experience
- Telemetry: per-session count of `watcher_event_received` — if 0 over 1h sustained, suggest manual refresh

**Phase to address:**
Library intelligence phase. Mount detection + polling fallback ship with the watcher.

---

### Pitfall 30: Bravoh Proxy Free-Tier Rate Limit Inadequate Under Viral Load (1000+ DAU)

**Severity:** Medium (viral moment → free-tier RPM cap → service degradation for ALL users simultaneously)

**What goes wrong:**
Bravoh proxy bundles a Bravoh-side Gemini API key. Free tier has shared RPM/TPM limits. A Reddit post hits the front page → 10× normal traffic in 1 hour → all users hit the proxy → proxy hits Gemini's RPM cap → all vibemix users get 429 errors simultaneously. F bucket §"Risk + watchouts" calls this out: "Gemini rate limit on shared proxy."

**Why it happens:**
Free-tier proxy = single shared key. Viral spikes (10× baseline) can exceed the per-key RPM cap. Without queue + retry + degradation strategy, every user gets failures at the same time.

**Symptom:**
- Reddit post day-spike: all vibemix users report "AI not working"
- Bravoh proxy logs show sustained 429s from Gemini upstream
- Cascading failure: users retry → more 429s → worse degradation

**Prevention:**
- Tenacity retry with exponential backoff (already in Bravoh's pipeline per F bucket — port as-is)
- Surface "high traffic, retry in 30s" in vibemix UI when proxy returns 429 (not silent fail)
- Bravoh Pro key as backup pool: when free-tier exhausted, BRAVOH-PRO key takes over (no user-visible difference, higher cost ceiling)
- Per-user daily cap: 100 reactions/day default soft cap (F bucket); hitting it shows graceful "I'm conserving juice for the day" message
- Pre-launch capacity planning: estimate viral surge (10× baseline) → ensure key can sustain it OR have queue
- Load test before launch: synthetic 10× burst against proxy; assert graceful degradation, no cascade failure

**Phase to address:**
Bravoh-side proxy phase + Day-Zero ops phase. Capacity planning + load test owned by Day-Zero Ops.

---

### Pitfall 31: Day-Zero Rehearsal on Fresh Non-Dev macOS — Kaan's Rig Has Dev Cruft

**Severity:** Medium (Kaan's rig false-passes; real users hit issues Kaan didn't see)

**What goes wrong:**
Phase 16 / Day-Zero rehearsal must run on FRESH non-dev macOS (clean install, no dev tools, no Xcode). Kaan's rig has: BlackHole pre-installed, DDJ-FLX4 paired, TCC permissions granted from prior testing, signed apps trusted via `spctl --add`. Testing on Kaan's rig would false-pass scenarios that fail on user rigs (Gatekeeper warning, AX permission flow, BlackHole missing).

**Why it happens:**
The dev rig accumulates state over months. "Works on my machine" is the classic engineer trap. STATE.md Phase 11 close explicitly noted: "STRUCTURAL gate (NOT fresh-machine timing). Fresh-machine <90s wizard timing rehearsal is owned by Phase 16 ... Kaan's rig has BlackHole pre-installed + DDJ-FLX4 + TCC granted — not a fresh non-dev macOS, so timing the wizard here would either false-pass or false-fail."

**Symptom:**
- v2.0 ships, Day 1 install reports: "vibemix said BlackHole not detected — your install isn't working"
- TCC permission flow stuck because Kaan never re-saw the prompts
- Build verified on Kaan rig but fails on user rigs

**Prevention:**
- Day-Zero rehearsal MUST use: fresh macOS VM (UTM/Parallels with clean macOS Sonoma+ image), fresh Windows VM (clean Windows 11), zero pre-installed deps
- Checklist: BlackHole installer prompt → install → permission flow → audio works
- Recording the rehearsal run as a screencast — review for any UX friction
- CI matrix at GitHub Actions: macOS-latest + windows-latest (closest to fresh) — at minimum smoke tests the build, doesn't catch user-level UX

**Phase to address:**
Day-Zero Ops phase. Fresh-VM rehearsal is the central activity, not a side check.

---

### Pitfall 32: api.altidus.world Endpoint Not Deployed When First User Installs

**Severity:** Medium (silent failure for all users; updater + proxy both depend on it)

**What goes wrong:**
release.yml falls back to GH-Releases-only manifest if api.altidus.world is down (per STATE.md Phase 5 / 11 notes). But the Tauri updater wants BOTH endpoints to be configured. If `api.altidus.world` isn't deployed by launch day, the updater configuration is inconsistent and may silently fail. Bravoh proxy also lives there; without it, vibemix can't make Gemini calls without user's own key.

**Why it happens:**
STATE.md Open To-do: "deploy `proxy/` to api.altidus.world when ready" — was "pending Kaan's operational schedule (does NOT block phase close)" — could still be pending at v2.0 ship.

**Symptom:**
- v2.0 release, no users can use vibemix-Free tier
- Updater silently fails (signature mismatch from inconsistent config)
- Discord/community gets flooded with "AI not responding" reports

**Prevention:**
- Deploy api.altidus.world BEFORE Phase 20 (Day-Zero Ops) — pre-requisite, not a follow-up
- Health check: `curl https://api.altidus.world/healthz` MUST return 200 before release.yml runs
- Updater config sanity check: both endpoints listed in `tauri.conf.json5`; both validated in CI
- Bravoh proxy load test: 100 RPS sustained for 5 min, no errors, p99 latency <500ms

**Phase to address:**
Day-Zero Ops phase + Bravoh-side proxy deployment phase. Deployment is a phase-entry pre-requisite.

---

### Pitfall 33: First-Day Star Momentum Collapses if README Hero Asset Doesn't Pop

**Severity:** Medium (vibemix's GitHub-star goal of 500-1000 hinges on first-100-stars momentum)

**What goes wrong:**
Memory `project_github_star_goal` is "500+ min, 1000+ realistic." First 100 stars come from social media → repo visit → README scan. If the hero asset (the 30-second viral demo film) is missing or low-quality at launch, the conversion from visit to star drops 5-10×. README must be camera-ready Day 1; this is NOT a follow-up polish task.

**Why it happens:**
The viral demo film is a 7-engineering-day plan (synthesis-viral-demo.md). It's tempting to defer until "after launch" but the launch moment IS the viral moment — there's no second chance. PROJECT.md "Validated" requirements include: "Hero demo video / GIF — 30-45s cinematic edit."

**Symptom:**
- Twitter post launches with text only or low-quality clip → low engagement
- Star velocity day 1: 50 instead of 200 expected
- HN front page slot wasted

**Prevention:**
- Viral demo film MUST be committed to repo (or hosted, linked from README) by release tag
- README "Above the fold" hero contains: project name + tagline + GIF + Install button + brief value prop
- Pre-launch checklist: render demo film, render hero PNG, render social preview OG image, render demo GIF (smaller)
- Phase Sequence: viral demo phase MUST complete BEFORE Day-Zero Ops phase

**Phase to address:**
Viral demo film + post arsenal phase. Day-Zero Ops phase has the launch checklist that validates hero assets exist.

---

### Pitfall 34: Discord/Community Channel Not Set Up — First 100 Stars Can't Gather

**Severity:** Medium (community feels absent; churn on early curious users)

**What goes wrong:**
Memory `project_github_star_goal` frames vibemix-Bravoh funnel. Without a Discord/community channel at launch, the first 100 curious users have nowhere to gather, ask questions, or share their setups. They install, hit an issue, can't find anyone to ask, churn.

**Why it happens:**
Community setup is "soft" work — easy to defer. But the launch moment is when community formation has highest momentum (FOMO). Discord setup is ~1h, but verification/moderation/onboarding flow is another ~4h.

**Symptom:**
- Day 3 post-launch: GitHub Issues thread is the only support channel; flood of repeat questions
- No "vibemix users showing off" social proof
- Bravoh team gets diverted to direct support

**Prevention:**
- Discord server set up BEFORE launch day: roles, channels (#general, #setup-help, #showcase, #controller-mapping-contrib), code-of-conduct posted, moderation bot installed
- Link in README footer + first-run onboarding card
- First 50 stars get auto-invited via README CTA
- Bravoh team has rotating Discord on-call for first 2 weeks

**Phase to address:**
Day-Zero Ops phase. Discord setup is part of the launch checklist.

---

## Low Pitfalls

### Pitfall 35: GitHub Action Issue Triage Workflow Not Catching All Bug Reports

**Severity:** Low (manageable manually for first 100 stars; becomes critical only past 500)

**What goes wrong:**
GitHub Actions triage workflow auto-labels issues by content (e.g., "bug" / "feature" / "controller-request"). If the workflow isn't set up or has gaps, bug reports get lost in the queue. At <100 stars manageable manually; at 1000+ stars / 500+ issues it's untenable.

**Prevention:**
- GitHub Issues templates: bug template, feature template, controller-request template (PROJECT.md mentions: "Issue templates — bug / feature / new-controller-request")
- Auto-label via `actions/labeler` config matching keywords
- Weekly issue triage review cadence (Kaan + Francesco)

**Phase to address:**
Day-Zero Ops phase. Issue templates + auto-labeler setup is a launch checklist item.

---

### Pitfall 36: Voiced TL;DR Voice Match with Live-Mode Voice (Achird Drift Across Model Updates)

**Severity:** Low (cosmetic — live mode and debrief mode might sound slightly different)

**What goes wrong:**
The post-session debrief includes a 60-90s voiced TL;DR (E-bucket). Generated via Gemini TTS Achird voice. The live mode also uses Achird. If Google updates the TTS model between rendering the debrief and the next live session, the voices may drift slightly — debrief sounds "older" than live. A-latency.md §"Risk + watchouts" calls out similar: "Pre-canned samples must match the cascade voice (Achird): if the model voice drifts in a Gemini update, samples will sound disjoint."

**Prevention:**
- Pin TTS model version in installer (specific preview version, not "latest")
- Regenerate ack bank + debrief TL;DR generation pipeline on model bump (rare, but plan for it)
- Document model version in `events.jsonl` for traceability
- Low priority — both sound similar enough; user won't notice unless directly comparing

**Phase to address:**
Post-session debrief phase. Voice pin is part of TTS configuration.

---

### Pitfall 37: Long-Term DJ Profile JSON Corruption / Disk-Write Race

**Severity:** Low (single-file local state; corruption recoverable from session_summary.json)

**What goes wrong:**
Long-term DJ profile = ~2KB JSON file (`profile.json`) per user. Written at end of each session. If two vibemix processes ever run concurrently (shouldn't, but possible if user double-launches), file write race could corrupt. Memory `project_v2_open_candidates` confirmed no mem0/vector DB — single JSON file is the design.

**Prevention:**
- Atomic write: write to `profile.json.tmp` → rename to `profile.json` (POSIX rename is atomic)
- Single-instance lock at vibemix startup (file lock or socket-based)
- Backup: keep last 3 profile versions in `profile.json.bak.{1,2,3}` rotation
- Validation on read: if JSON parse fails, fall back to backup

**Phase to address:**
Post-session debrief phase. Atomic write pattern shipped with the profile-writer.

---

### Pitfall 38: Debrief Gemini Call Cost ($0.05-0.15) × Every Session × 1000 Users = $50-150/day at Scale

**Severity:** Low (predictable cost; manageable in budget)

**What goes wrong:**
Each post-session debrief is a single Gemini call (E-bucket). Long audio Part (full session ~30 min) + structured prompt + response. Cost $0.05-0.15 per debrief. At 1000 users × 1 session/day = $50-150/day in debrief alone. Within Bravoh budget at low DAU; concerning at scale.

**Prevention:**
- BYO-key path: debrief uses USER's Gemini key (not proxy) by default — keeps cost off Bravoh
- Free-tier proxy: allow N debriefs/month via proxy (e.g., 3/month) — beyond that, requires BYO key
- Debrief opt-in: user must explicitly request debrief at end of session (not auto-generated)
- Track cost per debrief; alert if any session exceeds $0.30

**Phase to address:**
Post-session debrief phase. Opt-in + BYO-key default ship with the debrief feature.

---

## Cross-Cutting Pitfalls

### Pitfall 39: 50€/mo Per-User Proxy Budget Assumption Holds at 100 Reactions/Day, NOT at 1000+ DAU Viral Spike

**Severity:** High (budget assumption is single-point-of-failure for the free-tier promise)

**What goes wrong:**
50€/mo proxy budget assumes ~100 reactions/day cap holds for the free tier. At 1000+ DAU and viral conversion, the math doesn't hold. F bucket §"Per-user cost projection" puts working DJ at $0.017/mo and pro DJ at $0.039/mo — comfortable per-user math. But the bottleneck isn't COST, it's Gemini RPM rate limits on Bravoh's shared key. Viral 10× spike → all users hit cap simultaneously → service degradation.

**Prevention:**
- Bravoh Pro key as overflow: when free-tier RPM exhausted, Pro key takes over (higher cost, but absorbs spike)
- Per-user soft cap visible in vibemix UI: "You've used 80/100 reactions today"
- Adaptive cap: if proxy RPM > 80% sustained for 10min, soft-cap users to 50/day until pressure releases
- Daily/weekly cost dashboard for Kaan (Slack alerts at thresholds)

**Phase to address:**
Bravoh-side proxy phase + Day-Zero Ops phase. Overflow + cap logic shipped together.

---

### Pitfall 40: Kaan as Sole Tester for Phase 16 Ear-Test — Sample Size of 1

**Severity:** Medium (memory: Kaan's DJ ear is the test; risk = his taste might not generalize)

**What goes wrong:**
Memory `project_phase_16_kaan_dj_testing` confirms: "Phase 16 = Kaan's DJ ear, not formal suite. Don't auto-build the 30-session replay harness / LLM scorer / F1 validator." Per Kaan's preference. The risk: Kaan's DJ ear captures HIS taste; vibemix's audience is broader (beginner curiosity to pro feedback). What flies for Kaan may flop for a 6-month-in beginner.

**Prevention:**
- Kaan + Francesco both test (2 ears, different perspectives) — Francesco is the cofounder targeting DJ network
- Beta tester pool of 5-10 DJs (Francesco's network) for pre-launch ear-tests
- Telemetry post-launch: `slop_ratio` per-session reported via opt-in analytics; if cohort skews different from Kaan baseline, surface
- Acknowledge in PROJECT.md "Limitations" section — "v1 tuning anchored to Hard Tek; expansion to other genres in v2.x"

**Phase to address:**
Phase 16 ear-test phase (Kaan's DJ-set testing). 2-3 additional testers as a stretch goal within the phase.

---

### Pitfall 41: Bravoh Launch Overlap — vibemix Slips, Marketing Wedge Weakens

**Severity:** High (entire vibemix value prop is "drop ~3-4 weeks before Bravoh public launch")

**What goes wrong:**
PROJECT.md "Constraints": "Drop before Bravoh's public launch (~3-4 weeks out, ~early June 2026). Marketing momentum requires vibemix in the wild ahead of Bravoh's wave." If v2.0 slips past Bravoh's public launch, vibemix becomes "the OSS sidecar Bravoh shipped" instead of "the OSS warm-up that built Bravoh's audience." Conversion funnel disrupted.

**Prevention:**
- Phase ordering by criticality: ship-infrastructure (signing/notarize/MSI) FIRST so the binary is shippable any moment from there
- Feature gates: viral demo / library intelligence / cross-mode citation are NICE TO HAVE — drop to v2.0.1 if timeline at risk
- Weekly slip check: Kaan reviews timeline against Bravoh public launch date; cuts scope before slip
- Bravoh team coordinates: if vibemix slips, Bravoh launch can slide 1-2 weeks (mutual buffer)

**Phase to address:**
Roadmap-level concern; visible in phase ordering and gate criteria.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip ack-bank rotation deque, use raw `random.choice` | -2 hours dev time | Demo trust-breaker — same ack twice in 30s reads as AI slop | Never in v2.0 — ship gates require rotation |
| Skip AX-from-parent rule, call AX from Python sidecar | -1 day refactor | Tauri #8329 — overlay breaks on installed binaries | Never. AX-from-parent is a hard rule. |
| Skip Apple Issuer ID early provision | -1 day Kaan coordination | Critical path blocker at sign phase | Never — must be Day 1 of sign phase |
| Skip stapler step after notarytool | -1 line of release.yml | Every first-launch user sees Gatekeeper warning | Never. |
| Skip context-cache 1024-token floor padding | -1 hour planning | Silent 1500ms TTFT regression | Never — padding is mandatory |
| Skip mascot anticipation timeout/cancel-aware crossfade | -1 day | Anticipation pose freezes on Gemini fail = "AI broken" tell | Never in v2.0 |
| Skip per-SKU mido sniff on 9 untested controllers | -5 hours per SKU | Wrong CC numbers, controller appears dead | Acceptable if SKU is deprioritized and gracefully falls back to generic-MIDI |
| Skip Day-Zero rehearsal on fresh VM | -1 day | "Works on Kaan's rig" trap; users hit issues | Never — Day-Zero Ops phase requires fresh-VM rehearsal |
| Skip Discord setup at launch | -4 hours | Community can't gather; bug reports flood Issues | Never in v2.0 launch — required for community formation |
| Skip ffmpeg bundling, fail on .m4a tracks | -20MB installer | ~60% of macOS libraries fail to index | Never in v2.0 |
| Skip BYO-key consent for >500 track libraries | -1 day UX | Bravoh eats $200+/hoarder-user — budget breach | Never — consent gate is mandatory |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Tauri AX from Python sidecar | Call `Quartz.CGWindowListCopyWindowInfo` from sidecar | Call from Rust parent process; sidecar receives rect over IPC (Tauri #8329) |
| Tauri `visible_on_all_workspaces` on macOS | Assume covers all Spaces including fullscreen | Only covers shared Spaces; document fullscreen as known limitation (Tauri #11488) |
| Tauri `setIgnoreCursorEvents` on Windows | Use per-region hit-testing | Go fully click-through to sidestep Tauri #11461 bug |
| Notarytool | Use Issuer ID where Key ID expected | Provide BOTH Issuer ID and Key ID; both required |
| `xcrun stapler` | Skip after notarization succeeds | Always staple AND validate; assert exit 0 in CI |
| Gemini context caching | Trim cached system instruction below 1024 tokens | Pad with deterministic invariant context to stay above 1100 tokens |
| `SpeechHandle.cancel()` API | Assume method exists | Use `interrupt(force=True)`; `cancel()` doesn't exist in livekit-agents 1.5.x |
| pyrekordbox SQLCipher | Read master.db with bundled key | Use XML export path; SQLCipher key extraction broken post-6.6.5 |
| Mixxx OSC integration | Assume OSC ships in stock Mixxx 2.5.6 | Verify build of PR #14388; ship as opt-in beta with custom build instructions |
| Gemini Embedding 2 audio | Send AAC/M4A | Transcode to MP3 via pydub; 80s max (NOT 180s per docs) |
| sqlite-vec on Windows | Trust wheel availability | Fallback to numpy BLOB ranking; abstract behind LibraryStore interface |
| Updater secret name | Use `TAURI_UPDATER_KEY_PASSWORD` | Match name exactly across release.yml + tauri.conf.json5 (`TAURI_UPDATER_PRIVATE_KEY_PASSWORD` is current canonical) |
| Mascot AnimationMixer additive blend | Use clip directly without preprocessing | `AnimationUtils.makeClipAdditive(clip)` required before play |
| Citation linter index | Read without lock | Wrap in `asyncio.Lock` or use thread-safe `deque` |
| File watcher on NFS/SMB | Trust FSEvents/ReadDirectoryChangesW | Detect mount type; fall back to polling on remote mounts |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Cancel-and-refire uncapped | Gemini bill spike, no reaction count growth | Cap 1 cancel per 8s + 30 cancels per session | Hard Tek 170+ BPM bursty events |
| Predictive firing misfire | Wasted Gemini tokens 30%+ | Conservative 0.85 threshold, per-genre toggle | Hard Tek fake-drop tricks |
| Mascot 4-layer overdraw | Frame time >25ms on heavy events | makeClipAdditive + single mixer + 22ms p99 budget assertion | Multi-event bursts (KICK + SUB + DISTORTION) |
| Beat-phase drift accumulates | Hip-bob off-beat after 5min | Re-sync on every downbeat detect; Mixxx OSC BPM preferred | Long techno sets without tempo change |
| Library indexing 30k tracks blocks UI | 33hr indexing on free tier | Background indexing + progress bar + can-be-paused | Hoarder libraries |
| File watcher on large library | Event flood on `~/Music/` recursive scan | Throttle to 1 event/track/10s | Library re-org operations |
| Free-tier RPM exhaustion | All users 429 simultaneously | Bravoh Pro key overflow + per-user soft cap | Viral 10× spike |
| Mascot animation pre-load on launch | 3-5s startup delay | Lazy-load clips by category; prep_* loaded first | First-launch UX |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Skip per-user JWT rate limit on cancel-and-refire | Single client burns Bravoh's entire daily quota | Tie cancel quota to install_uuid in proxy |
| Citation linter passes user-controllable strings | Injection attack on linter regex | Linter inputs are Gemini-only; never trust user input to drive Evidence registry |
| Bravoh proxy logs full audio payloads | Privacy violation per CLAUDE.md "PRIVACY HARD RULE" | Strip audio from proxy logs; only metadata logged |
| Updater manifest unsigned (wrong env var) | Supply-chain attack vector — malicious update goes through | Validate signature at release.yml exit gate |
| Long-term DJ profile JSON readable globally | User profile leak | `~/Library/Application Support/vibemix/profile.json` chmod 600 (POSIX) / NTFS-restricted on Windows |
| Library indexing sends track audio to Gemini | Unreleased promos leaked | Explicit user consent screen; document Gemini API non-retention policy |
| Citation linter Evidence registry persists across sessions | Track history leaks if registry corrupted | In-memory only; cleared on session end |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Mascot anticipation freezes on Gemini fail | Mascot looks broken; "AI got excited about nothing" | Crossfade to `settle_down` on timeout; never wedge in lean-in |
| Overlay ring on multi-monitor draws on wrong screen | "Highlights are on the wrong display" | Quartz coord-space consistent; per-monitor DPI scale |
| Library indexing silent on .m4a tracks | "vibemix indexed 5k of my 12k tracks — why?" | Surface "Transcoding 7,000 AAC tracks..." progress phase |
| Pyrekordbox XML staleness | "vibemix doesn't know my new tracks" | 30-day nudge + auto-detect via lookup-fail counter |
| Track title fuzzy match wrong | AI grounds in wrong track's BPM/key | Require artist OR BPM match for confidence ≥0.7 |
| Sync button doesn't register on FLX4 | "vibemix doesn't see my sync presses" | Sniff actual MIDI mode; ship both note candidates |
| Discord absent at launch | First curious users have nowhere to gather | Discord setup BEFORE launch; linked in README footer |
| Hero asset missing on Day 1 | "What does this even do?" → low star conversion | Demo film + GIF in repo at release tag |
| First-launch Gatekeeper warning | "Mac says this is malicious — I'm out" | Notarize + staple + README pre-explains warning |
| Windows SmartScreen warning | "Microsoft says this is unrecognized — abandon" | SignPath OSS + README screenshots of "More info → Run anyway" |
| Free-tier daily cap hit silently | "AI stopped working" | UI shows "80/100 reactions used today; upgrade or wait" |

---

## "Looks Done But Isn't" Checklist

- [ ] **Latency stack:** Often missing cancel-cooldown + per-session cap — verify `events.jsonl` shows ≤3 cancels/min in real-DJ session
- [ ] **Citation linter (live mode):** Often missing telemetry guard for `stripped_rate > 0.4` bypass — verify guard fires on synthetic stripped-heavy session
- [ ] **djay Pro overlay:** Often missing AX-from-parent grep gate + dual-monitor test — verify lint rule + multi-monitor smoke run
- [ ] **djay Pro overlay (fullscreen):** Often missing the "windowed-only" toast — verify Quartz fullscreen-detect fires
- [ ] **Pyrekordbox XML:** Often missing 30-day staleness nudge + confidence-aware grounding — verify both
- [ ] **MIDI library:** Often missing per-SKU sniff path + community contribution docs — verify CONTRIBUTING.md walkthrough exists
- [ ] **Mascot anticipation:** Often missing 2.5s timeout + cancel-aware crossfade — verify mascot doesn't wedge on synthetic Gemini-fail
- [ ] **Post-session debrief:** Often missing BYO-key path + opt-in for cost gating — verify defaults
- [ ] **Library intelligence:** Often missing BYO-key consent gate for >500 tracks — verify gate fires
- [ ] **Library intelligence:** Often missing sqlite-vec fallback to numpy BLOB — verify auto-detect on startup
- [ ] **Apple Developer ID sign:** Often missing stapler step + stapler-validate gate — verify CI fails on missing staple
- [ ] **Windows MSI:** Often missing SignPath approval verification before release — verify gate fires
- [ ] **Updater manifest:** Often missing signature verification before publish — verify CI signs+verifies cycle
- [ ] **Day-Zero Ops:** Often missing fresh-VM rehearsal record — verify screencast exists
- [ ] **Day-Zero Ops:** Often missing api.altidus.world health check pre-release — verify curl-test in CI
- [ ] **Day-Zero Ops:** Often missing Discord setup + linked from README — verify both
- [ ] **Day-Zero Ops:** Often missing demo film + hero GIF in repo — verify at release tag
- [ ] **Cross-mode citation linter:** Often missing per-mode tolerance window tuning — verify ±1s live, ±2s debrief
- [ ] **Generalized event detector v1:** Often missing per-genre cooldown tuning — verify `MIN_EVENT_GAP_PER_TYPE` matches G-followup-1

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cancel-and-refire blowing budget | LOW | Add per-session cap, ship hotfix v2.0.1, alert affected users |
| Citation linter silence-streak | MEDIUM | Disable linter for affected user, ship telemetry guard in v2.0.1 |
| djay Pro overlay AX broken on install | HIGH | Tauri-issue workaround OR sidecar workaround; ship v2.0.1 with permission re-grant flow |
| Pyrekordbox XML staleness complaint | LOW | UI nudge + re-import wizard; no code change |
| MIDI controller mapping wrong | LOW | Community PR or hotfix JSON ship via auto-update |
| Mascot anticipation freeze on fail | MEDIUM | Ship cancel-aware crossfade in v2.0.1 |
| Apple sign / notarize / staple miss | HIGH | Manually staple existing DMG; release v2.0.1 from staple-included CI |
| Windows SmartScreen warning | HIGH | SignPath approval (1 week SLA); meanwhile README + EV cert backup |
| Updater manifest signing wrong | CRITICAL | Manual sign + manual update push via release-asset URL; communicate via Discord |
| api.altidus.world not deployed | HIGH | Emergency deploy; meanwhile BYO-key fallback for live calls |
| Discord absent | LOW | Set up Discord, edit README, post link via Twitter |
| Hero asset missing | MEDIUM | Quick-edit demo film; re-post launch tweet with proper hero |
| BPM phase drift | LOW | Hotfix re-sync logic; ship v2.0.1 |
| Library indexing timeout | LOW | Background pause/resume in UI; ship in patch |
| Free-tier RPM exhausted | LOW | Activate Bravoh Pro key overflow; ship adaptive cap in patch |

---

## Pitfall-to-Phase Mapping

How v2.0 milestone phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1 Cancel-and-refire budget blowout | Latency stack phase | Burst-event test: ≤3 cancels/min sustained |
| P2 Citation linter silence streak | Citation linter phase | Replay Kaan session: `stripped_rate < 0.15` |
| P3 AX from Python sidecar | djay Pro overlay phase | Lint rule: no AX import in sidecar highlight package |
| P4 Fullscreen Space overlay loss | djay Pro overlay phase | Quartz fullscreen-detect fires toast |
| P5 Apple Issuer ID missing | Ship/Sign/Release phase | Pre-flight `notarytool history` test in CI |
| P6 SignPath unapproved at MSI build | Ship/Sign/Release phase | Phase entry gate: application filed AND approved |
| P7 Updater secret name mismatch | Ship/Sign/Release phase | Signer-verify on synthetic manifest in CI |
| P8 Ack rotation collision | Latency stack phase (ack bank) | 60-fire synthetic: zero collisions in 30s window |
| P9 Anticipation freeze on fail | Mascot 4-layer refactor | Synthetic Gemini-fail: mascot crossfades to settle, no wedge |
| P10 Predictive misfire rate | Latency stack phase | `predicted_drop_misfire_rate < 0.25` sustained |
| P11 Cache below 1024-token floor | Latency stack phase (caching) | Token-count assertion + metric check post-3-turns |
| P12 Linter registry race | Citation linter phase | 100-concurrent register+validate test, zero false-strips |
| P13 Multi-monitor Y-flip | djay Pro overlay phase | Dual-monitor smoke test |
| P14 Windows DPI virtualization | Windows port phase | Multi-monitor + multi-DPI fresh-VM test |
| P15 Pyrekordbox staleness | Pyrekordbox XML import phase | 30-day nudge + lookup-fail counter shipped |
| P16 Track title fuzzy collision | Pyrekordbox + Library intel phases | Synthetic 5-Insomnia library: no high-confidence wrong-match |
| P17 Stapler missing | Ship/Sign/Release phase | `xcrun stapler validate` in CI release gate |
| P18 Citation timestamp out of tolerance | Citation linter phase | Tolerance ±2.0s + prompt anchor in evidence packet |
| P19 Three.js crossfade discontinuity | Mascot 4-layer refactor | Frame-time p99 <22ms on 60-event burst |
| P20 Beat-phase drift | Mascot beat-coupled idle | 30-min synthetic: drift <0.2 phase units |
| P21 Emote tag text-vs-audio order | Mascot 4-layer refactor (spike) | 1-day spike BEFORE phase commits to emote tag design |
| P22 Mascot opaque chrome regression | Mascot polish phase | vitest computed-style snapshot |
| P23 GLB clip size explosion | Mascot 4-layer refactor | Total clip size ≤15MB CI gate |
| P24 9 untested SKU mappings | 10-SKU MIDI library extension | Community PR sniff path + telemetry |
| P25 DDJ-FLX4 Sync note disagreement | 10-SKU MIDI library extension | Mido sniff resolution Day 1 |
| P26 AAC/M4A transcoding | Library intelligence phase | ffmpeg bundled, transcode tested |
| P27 sqlite-vec wheel breakage | Library intelligence phase | LibraryStore abstraction + numpy fallback |
| P28 30k library cost gate missing | Library intelligence phase | Consent screen for >500 tracks |
| P29 File watcher mount edge cases | Library intelligence phase | Mount-type detection + polling fallback |
| P30 Bravoh proxy viral RPM exhaustion | Day-Zero Ops + proxy deploy | Pro key overflow + load test |
| P31 Day-Zero rehearsal on dev rig | Day-Zero Ops phase | Fresh-VM rehearsal screencast |
| P32 api.altidus.world undeployed | Day-Zero Ops phase | Healthz curl gate pre-release |
| P33 Hero asset missing at launch | Viral demo + post arsenal phase | Demo film + GIF + OG image in repo at tag |
| P34 Discord absent at launch | Day-Zero Ops phase | Discord URL in README footer |
| P35 GitHub Action triage gaps | Day-Zero Ops phase | Issue templates + auto-labeler config |
| P36 TTS voice drift across model updates | Post-session debrief phase | Pin TTS model version |
| P37 Profile JSON corruption race | Post-session debrief phase | Atomic write + backup rotation |
| P38 Debrief cost at scale | Post-session debrief phase | BYO-key default + opt-in |
| P39 Free-tier 50€/mo budget breach | Bravoh proxy + Day-Zero Ops | Adaptive cap + Pro overflow + dashboard |
| P40 Kaan-only Phase 16 ear-test | Phase 16 ear-test phase | Francesco + 5-tester beta pool |
| P41 Bravoh launch overlap slip | Roadmap-level | Weekly slip review; cut-list pre-published |

---

## Sources

### Primary v2-bucket research artifacts (HIGH confidence)

- `.planning/research/v2-buckets/SYNTHESIS.md` — integration layer + priority matrix + executive TL;DR
- `.planning/research/v2-buckets/A-latency.md` — predictive firing, ack bank, prompt diet, latency targets, A1-A6 assumptions
- `.planning/research/v2-buckets/A-followup-1-cancel-and-caching.md` — empirical verification of `interrupt(force=True)`, 1024-token floor, caching plumbing
- `.planning/research/v2-buckets/B-followup-1-v11-integration-spec.md` — 10-SKU MIDI library spec, pyrekordbox XML import, Mixxx OSC opt-in stance, DDJ-FLX4 Sync note disagreement
- `.planning/research/v2-buckets/C-ui-overlay.md` — djay Pro overlay, Tauri AX bug #8329, fullscreen #11488, Windows DPI traps, dual-monitor coord pitfalls
- `.planning/research/v2-buckets/D-mascot-emotion.md` — 4-layer additive state machine, emote tag vocab, anticipation layer timeout, GLB size budget
- `.planning/research/v2-buckets/E-debrief-pedagogy.md` — post-session debrief design, SBI/STAR-AR framing, voice match risks
- `.planning/research/v2-buckets/E-followup-1-citation-linter.md` — citation grammar, regex enforcement, registry race, telemetry surface
- `.planning/research/v2-buckets/F-library-intelligence.md` — Gemini Embedding 2 80s cap, sqlite-vec fallback, AAC transcoding, BYO-key economics, file-watcher edge cases
- `.planning/research/v2-buckets/G-genre-taxonomy.md` + `G-followup-1-hard-tek-dsp.md` — generalized event detector v1, per-genre tuning, KICK_SWAP DSP
- `.planning/research/v2-buckets/synthesis-viral-demo.md` — 30s storyboard, 3 signature beats, 7-day eng plan, critical path

### Internal references (HIGH confidence)

- `.planning/PROJECT.md` — v2.0 milestone scope, constraints, decisions
- `.planning/STATE.md` — Phase 11 Risks section, Decisions Locked, recent fix log
- `.planning/codebase/CONCERNS.md` — codebase tech debt + np.concatenate ring-buffer regression flagged
- `CLAUDE.md` — project constraints (1-click install, no scope creep, Gemini-only, anti-slop thesis)
- Memory files: `project_v0_1_0_rc1_open_bugs.md`, `project_one_click_install_hard_req.md`, `feedback_no_scope_creep_clean_utility.md`, `project_phase_16_kaan_dj_testing.md`, `project_github_star_goal.md`

### Tauri bug tracker (MEDIUM-HIGH confidence)

- [Tauri #8329 — sidecar AX permission inheritance](https://github.com/tauri-apps/tauri/issues/8329)
- [Tauri #11488 — visibleOnAllWorkspaces + fullscreen Spaces](https://github.com/tauri-apps/tauri/issues/11488)
- [Tauri #11461 — setIgnoreCursorEvents Windows quirks](https://github.com/tauri-apps/tauri/issues/11461)

### Anti-pattern / industry references (MEDIUM confidence)

- [Swindler #62 — NSScreen vs Quartz coord systems](https://github.com/tmandry/Swindler/issues/62)
- [Microsoft Learn — GetWindowRect DPI behavior](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect)
- [Three.js makeClipAdditive docs](https://threejs.org/docs/#api/en/animation/AnimationUtils)
- [Apple notarytool — Issuer ID + Key ID requirements](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

---

*Pitfalls research for: vibemix v2.0 Research-Driven Ship — feature additions to 3-process architecture*
*Researched: 2026-05-14*
