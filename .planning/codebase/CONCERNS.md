# Codebase Concerns

**Analysis Date:** 2026-06-08

> Scope: full repo (`src/vibemix/` Python + `tauri/` desktop shell). Ground truth:
> project `CLAUDE.md` (Constraints + Cardinal invariants + gotchas), the
> `2026-06-08` handoff (`.planning/handoffs/2026-06-08-HANDOFF-NEXT-SESSION.md`),
> and the three `2026-06-08` strategy packets. The signed DMG
> (`dist/vibemix-0.0.1.dmg`) shipped from commit `8bc721ce`. This document
> surfaces real risk for launch — it is not a reassurance doc.

---

## ⭐ The Core Product Risk — voice "AI slop" (the launch gate)

This is the #1 risk and it is a **measured quality gap, not a code bug**. The
product fails its own bar ("real DJ friend in your ear, no AI slop") if reactions
feel scripted, late, hallucinated, or generic. Kaan will block release on this.

**What it is:**
- Bench-measured "friend" scores are LOW — the co-host reads as a **narrator, not a
  friend**. The blind 2-judge panel over real labeled lines
  (`.planning/packets/2026-06-02/CODEX_READY-SVEN-PROMPT-BENCH-MEASURED.md`) put
  the best coach-identity prompt at `friend_not_narrator` ≈ 1.93 vs 1.14 baseline
  (+0.79), but the handoff records live by-ear friend as low as **~0.09–1.2** —
  "137-of-137 lines should-not-have-spoken = narrator" (memory
  `project_autonomous_night_machine_2026_06_04`). The prompt axis has **plateaued**
  (round-2 bench converged 1.97–2.08, all noise) — more prompt tuning yields
  nothing; the next lever is perception + speak-gate, not prose.

**Where the anti-slop machinery lives (and its fragility):**
- `src/vibemix/state/evidence_registry.py` (28KB) — citation grounding store backing
  Cardinal Invariant #2.
- `src/vibemix/coach/citation_linter.py` (8.7KB) — strips any reaction whose
  citation does not resolve in the registry down to the ack-bank fallback. This IS
  the anti-slop release gate, but it is **double-edged**: it can over-strip a good
  reaction to a bland ack, and during last QA it was **disabled**
  (`VIBEMIX_ANTI_SLOP=off`, handoff line 43) to let Sven speak at all. The default
  is ON (`dj_cohost.py:321` `default=not _sven_probe_mode_enabled()`), so the
  ship config and the QA config diverge — a real "tested-with-the-gate-off" risk.
- `src/vibemix/prompts/matrix.py` (`_ANTI_SLOP_FOOTER`, applied to every cell),
  `src/vibemix/prompts/negative_dict.py` (the runtime slop phrase filter, seeded by
  the `stop-slop` skill).

**Tracking instrument (use it, don't eyeball):**
- `src/vibemix/bench/` (`run.py`, `eval.py`, `matrix.py`, `assemble.py`, `cell.py`,
  `review.py`, `respan.py`, `fixtures.py`) — the Phase-81 regression harness (real
  Gemini + blind judge panel, friend/grounded/overall per line). Per the locked
  philosophy (`project_vibemix_sven_prompt_philosophy`) slop is a
  prompting+data+bench problem; fix by measuring, never by per-failure NOT-X bans.
- **Risk:** the bench is a *dev/eval* harness (`bench/` is explicitly "NOT a runtime
  feature" per CLAUDE.md). Green unit tests prove nothing here — only a bench score
  + a live `drive-vibemix` proof + Kaan's ear gate the quality.

**Fix approach (decided, not yet shipped):** local hi-fi EARS → rich musical TEXT →
Gemini = brain. Gemini forces audio to 16kHz-mono so it is a mediocre listener; the
ceiling is on the input side. See `.planning/packets/2026-06-08/LOCAL-HIFI-EARS-ARCHITECTURE.md`.

---

## Tech Debt

**God-module: `__main__.py` is 8,914 lines.**
- Files: `src/vibemix/__main__.py`
- Impact: The async orchestrator (ported from the retired `cohost_v4.py`) holds
  routing, mode resolution, capture wiring, genre dispatch, taste loading, and
  service binding all in one module. Nearly every cross-cutting bug in this doc
  threads through it (`:1525` downgrade, `:2576` cache, `:2504` suggestion binding,
  `:1028` audio collapse, `:2459` anti-slop flag). High blast radius; hard to test
  in isolation; concurrent-session merge conflicts concentrate here.
- Fix approach: extract the mode/routing block, the service-binding block, and the
  audio-callback block into `runtime/` submodules with explicit DI (the codebase
  already prefers DI-over-globals per CLAUDE.md — apply it here).

**Other large modules (complexity hotspots):**
- `src/vibemix/state/deck_context.py` (5,094 lines), `src/vibemix/library/codex_curate.py`
  (4,939), `src/vibemix/agent/dj_cohost.py` (4,675), `src/vibemix/learn/runtime.py`
  (4,476), `src/vibemix/eval/session_report.py` (2,946).
- `tauri/ui/src/library/index.ts` (3,464), `tauri/ui/src/library/api.ts` (3,101),
  `tauri/ui/src/learn/learn-window.ts` (2,760), `tauri/ui/src/pill/index.ts` (2,271).
- Impact: each is a single-owner file that two concurrent Claude/Codex sessions
  cannot edit without collision (see Process Risk below).

**Stale planning machinery.**
- `.planning/` is 136MB; `.planning/eval-runs/` alone is 73MB and is **NOT
  gitignored** (`git check-ignore` returns nothing) — ~250+ eval-run dirs show as
  untracked `??` in `git status`, polluting every status and risking an accidental
  bulk `git add`.
- GSD was retired as a mandate (CLAUDE.md "Workflow") but the `.planning/`,
  `/gsd-*` commands, and codebase maps remain present and partly stale. The
  authoritative live work-queue moves often (currently the `2026-06-08` handoff).
  Risk: a future session treats a superseded packet (e.g. `WIRE-THE-GOLD`,
  `MASTER-ARRANGEMENT`) as authoritative TODOs. Fix: gitignore `eval-runs/`; keep
  the handoff-of-the-day as the single source of truth.

**`orphans.csv` is a weak/stale signal.**
- File: `.planning/codebase/orphans.csv` (96 rows, dated 2026-06-04).
- It lists "zero-caller in codegraph", which catches **intra-module-only** symbols
  (e.g. `intel/decision_runtime.py::validate_and_degrade` IS called at `:125`;
  `transition_scorer.py::phrase_alignment_score` at `:347`; `learn/copy_truth.py::transcript_copy`
  at `:39`) and re-exports — not true dead code. Several entries it flags have since
  been wired (voice producers, pill feedback — see below). Treat it as a hint to
  investigate, not a kill-list.

---

## WIRED-BUT-DARK — built + tested, not surfaced end-to-end

This is the second-largest risk class: a large amount of product is engineered and
unit-green but does not reach the human. Confirmed-dark surfaces (high confidence):

**Brain-switch UI (proxy ↔ direct + BYO key) — backend complete, UI DARK.**
- Backend: handler `runtime/session_loop.py` (`set_brain`), persist
  `runtime/config_store.py` (writes `.env` chmod 600), boot-load `__main__.py`.
  Schema/redaction plumbed: `tauri/ui/src/ipc/messages.ts:384`,
  `tauri/ui/src/ipc/client.ts:47` (redacts `gemini_api_key` in logs).
- **Zero UI emitter:** grep of `tauri/ui/src/settings/` and `tauri/ui/src/shell/`
  for `set_brain` returns nothing — no control sends `ipc.settings.set_brain`. A
  non-dev cannot switch brains or enter a key. This blocks the entire tiering model.
- Files: missing sender in `tauri/ui/src/settings/SettingsDrawer.ts`.

**Gemini context caching disabled.**
- `src/vibemix/__main__.py:2576` constructs the agent with `cache=None` → the full
  system prompt re-uploads on every reaction (~0.5–1.5s wasted TTFT per call,
  per handoff). Latency tax on the booth-critical path.

**Opener-ack PCM cache built but gated off.**
- `src/vibemix/agent/chatterbox_tts.py:191` — pre-rendered opener-ack PCM exists but
  is disabled; defeats the "instant grounded 1-word ack" latency lever.

**Anticipation / drop-prediction not closed to the prompt.**
- `src/vibemix/state/drop_predict.py` (`predicted_drop_in_sec`,
  `should_arm_drop_call`) is referenced by many modules (`refresh.py`,
  `event_detector.py`, `speak_gate.py`, `prompt_builder.py`, `drop_display.py`,
  `ws_bus.py`) but the lookahead→live-prompt anticipation path (fire-at-T scheduler,
  two-clock model) is the **C9-gap** — the substrate exists, the booth-DJ
  anticipation behavior is not wired (handoff line 35).

**Latency band-aids that swallow real moments.**
- `EVENT_GLOBAL_MIN_GAP=22s` + a 7s post-voice cooldown (handoff line 39) suppress
  genuine events to mask the ~6.7s event→voice latency. They trade slop for
  *missed reactions* — relax once latency drops.

**Recently un-darkened (verify, do not re-flag as orphan):**
- Pill explicit-feedback loop is now **wired** (commit `f87c0240`): UI emits over ws
  (`tauri/ui/src/pill/index.ts:2054 onPeekPrimaryAction`) → Python receivers
  `runtime/ws_bus.py:1128 choose_alternative` / `:1146 record_feedback`. The
  consent-gated taste update (`update_taste_scores`) still defaults OFF.
- Sven audio-coaching voice producers recovered + wired:
  `runtime/energy_read_voice.py` + `runtime/move_grade_voice.py` are now consumed in
  `runtime/coach.py:658-673` (no longer dangling against `speak_gate.py:24-25`).
- `SuggestionService` is now bound at runtime (`__main__.py:2504`), not the old
  permanent `None` — the pill display path lights up when `library.pkl` exists.
- **Residual dark:** the learn move-grade is still computed-then-not-fully-surfaced
  (`learn/runtime.py`); `move_grade` rides the IPC/library path
  (`tauri/ui/src/library/api.ts:437`) but the live in-set grade → TS consumer is thin.

---

## Security Considerations

**API-key-in-binary — SOLVED, verified.**
- Risk: a raw Gemini key shipped in the distributed binary (Kaan: "the
  API-key-protection problem of the year").
- Verified mitigation: the packaged proxy path carries **no real key**.
  `src/vibemix/agent/proxy_client.py:33` builds the genai client with
  `api_key="vibemix-proxy"` (dummy; proxy ignores `x-goog-api-key`) and a per-client
  JWT in the `Authorization` header; the JWT is cached in the OS keychain
  (`src/vibemix/agent/jwt_cache.py`), never embedded. Grep for `AIza[...]` literals
  across `src/`, `tauri/`, `scripts/`, specs, and `pyproject.toml` returns
  **nothing**. Direct mode requires the user's own `GEMINI_API_KEY`.
- Residual: rate-limiting / per-client cost caps live on the Bravoh side
  (`api.altidus.world`, not in this repo) — out of scope here but is the real
  abuse-control surface.

**🔑 Keystone TRUST bug — silent direct→proxy downgrade.**
- Files: `src/vibemix/__main__.py:1525-1534` (confirmed: `if not api_key: ... mode =
  "proxy"`).
- Risk: a Pro who selects direct mode with a bad/empty key is **silently** flipped
  to proxy, relaying 48s of master audio AND ~8s of booth-mic voice
  (`agent/dj_cohost.py:3029-3055`, gated on recent speech) through Bravoh's server —
  while believing they are private. This breaks any "your own key = private"
  promise.
- Current mitigation: none. `persist_brain_settings` does zero key validation.
- Recommendation: validate the key at save-time (one cheap test call), refuse the
  switch on bad/empty key, and fail loud mid-session — never silent-downgrade
  (`.planning/packets/2026-06-08/ROUTING-PROXY-VS-DIRECT-DECISION.md` risk #2).

**Disclosure honesty drift.**
- `src/vibemix/runtime/sec_check.py:51-77` — endpoint drift
  (`api.bravoh.altidus.world` → `api.altidus.world`) and it does not plainly state
  that in proxy mode 48s master + sometimes 8s booth mic are uploaded, nor the
  ~7-day local `audio.wav` retention (`agent/dj_cohost.py:2983-2997`). For a paid
  product handling live mic audio this is a real privacy-disclosure gap.

**`.env` handling — acceptable.**
- `.env` (447 bytes) present at repo root; `.env`, `.env.*`, and `proxy/.env` are
  all gitignored (`.gitignore:51-52,171`). Contents not read (privacy rule). Boot
  loads via `python-dotenv`. The `set_brain` persist writes `.env` chmod 600.

**Telegram bridge auth — fail-closed, but minimal.**
- `src/vibemix/library/telegram_bridge.py` — v1 auth is a numeric chat-id allow-list
  (`parse_allowed_chats`, `_ENV_ALLOWED=VIBEMIX_TELEGRAM_ALLOWED_CHATS`), explicitly
  **fail-closed**: an empty/missing list authorizes nobody (`:82,:99`). Outbound
  messages are path-scrubbed; each request runs the local Codex Viber under a
  wall-clock timeout. Risk is acceptable for an optional opt-in surface, but the
  allow-list IS the entire auth — there is no token-per-user or rate-limit; a leaked
  bot token + a known allowed chat-id = full Viber access. Keep it opt-in/off by
  default for v1.

**`generic39` false-positive in the sign pipeline — process security risk.**
- `scripts/dist/verify_binary.py:83,98,311` (`_include_generic39`). The secret
  scanner flags 39-char `[A-Za-z0-9_-]` runs; bundled `transformers` identifiers
  produce 505 benign hits → `verify_binary` exits 5 AFTER the DMG is already
  notarized+stapled (the `8bc721ce` DMG is valid). Risk: the security gate
  cries-wolf, training operators to ignore exit-5 — which would mask a *real* leak
  next time. Fix: add a `_include_generic39` allowlist for vendored trees (NOT
  auto-edited — it is a security gate, Kaan's call).

---

## Performance Bottlenecks

**Event→voice latency ~6.7s (the booth-critical path).**
- Anatomy (`.planning/packets/2026-06-08/COHOST-LATENCY-PERCEPTION-STRATEGY.md`):
  LLM ~3s ≈ TTS ~3s, serial, no caching — no single villain. The 8s audio window is
  a continuous ring, not an accumulation wait.
- Contributing files: `agent/dj_cohost.py:285-333` (48s audio Part, shrinkable to
  6-8s for free), `__main__.py:2576` (`cache=None`, re-uploads system prompt),
  `chatterbox_tts.py:191` (opener-ack cache gated off).
- Improvement path: decouple WHEN-to-speak from WHAT-to-say (instant grounded
  1-word ack via the non-LLM `say()` lane → perceived 6.7s → ~0.5s); enable context
  cache; shrink the audio window.

**Proxy SSE streaming UNVERIFIED — dominant launch risk for the proxy default.**
- If `api.altidus.world`'s reverse proxy buffers the SSE response (`proxy_buffering
  on` / missing `X-Accel-Buffering: no`), proxy TTFT collapses from first-token to
  full-completion (multi-second) — catastrophic for booth latency. Unverifiable from
  client code; gates the keyless-proxy-default decision
  (`ROUTING-PROXY-VS-DIRECT-DECISION.md` risk #1).

**PlaybackQueue O(n) front-delete on the audio thread.**
- `src/vibemix/agent/buffers.py` (`PlaybackQueue.pull`) does a front-delete each pull
  on the OS audio thread; `OUTPUT_BLOCKSIZE=256`. Flagged as a hardening target only
  if voice stutter persists on a single device (memory
  `project_inapp_ux_lane_verified_2026_06_07`, demonic-voice bundle). Fix: ring
  buffer + bump blocksize to 1024.

---

## Fragile Areas

**Frozen-sidecar false-negative (the recurring trap).**
- The bundled Python sidecar in `cargo tauri dev` and in the DMG is FROZEN — it lags
  edited `src/vibemix/`. Verifying backend wiring against the bundled binary yields
  false negatives (and false "fixed" claims). Safe modification: run `main()` on
  current source (`uv run python -m vibemix`), never the bundled binary; grep the
  build TOC (`build/vibemix-core.macos/*.toc`) to see what actually shipped
  (`find dist/` misses pure-Python modules in the PYZ). The `.dmg` is rebuilt
  separately from the loose `dist/vibemix-core` sidecar — a sidecar rebuild does NOT
  refresh the DMG. (CLAUDE.md Commands.)

**BlackHole self-hearing / phantom-music trap.**
- If system output or a Multi-Output device also feeds BlackHole, the co-host hears
  its own voice as phantom music and reacts to it — directly violating Invariant #3
  ("trust the audio"). Mitigation is **config, not code**: in Audio MIDI Setup route
  only the DJ app into BlackHole. The deck passthrough ships silent
  (`audio/constants.py PASSTHROUGH_GAIN=0.0`) precisely to avoid mirroring
  BlackHole → speakers. Fragile because it depends on correct user audio routing.

**Multi-Output aggregate-clock drift → voice stutter.**
- `src/vibemix/platform/_audio_macos.py:738` self-warns on aggregate-device clock
  drift. A Multi-Output device with members at mismatched rates / no Drift
  Correction causes the stutter that has been mis-blamed on code. Safe fix:
  single physical output device, or all members 48k + Drift Correction on. The
  device-stability heuristic lives in `src/vibemix/audio/device_select.py`
  (`is_unstable_output_device`, `is_explicit_multi_output_device`).

**Demonic/slow voice — config, not code (do NOT edit `dj_cohost.py:2373`).**
- Memory `project_inapp_ux_lane_verified_2026_06_07` (demonic-voice bundle): the
  finder-claimed `target_sr=48000` bug at `dj_cohost.py:2373` was REFUTED by
  hand-read (it is already `OUTPUT_SR`=24000). Real causes ranked: doubled
  probe-direct path racing one PlaybackQueue (mitigated by
  `VIBEMIX_SVEN_PROBE_DIRECT_VOICE=0`), `VIBEMIX_SVEN_PROBE_PLAYBACK_SPEED`<1.0
  (deliberate slow), and Multi-Output clock drift. Fragile because the symptom looks
  like a code bug and invites a no-op edit.

**Go-live warmup flail (capture opens AFTER a ~90s TTS warm).**
- Memory `project_inapp_ux_lane_verified_2026_06_07` (go-live root-cause): activation
  warms the local TTS for up to ~90s BEFORE opening audio capture
  (`__main__.py:2160-2167`), then logs `session_lifecycle "started"` before the
  capture stream binds (`:2549-2554`). For ~90s the app shows started+IDLE+music=0;
  capture failure is stderr-only (no `ipc.error`). not-started / warming /
  capture-failed look identical → operators relaunch into the same warmup and loop
  for hours. Immediate unblock (zero code):
  `VIBEMIX_CHATTERBOX_START_WARMUP_TIMEOUT_S=0`. Proper fix: open capture before
  warmup, gate "started" on the first audio callback, emit `ipc.error` on
  capture-fail, add an ARMED status.

**Single-socket assumption (Invariant #4) + idle-grounding (Invariant #5).**
- The mascot/wizard bus binds `127.0.0.1:8765` only (debrief `8766`). A leftover QA
  engine on `:8765` silently steals the port — `pkill -f "python -m vibemix"` before
  every relaunch (one instance only). `SessionLayout`'s grounding-failure timer must
  run ONLY while the co-host is ACTIVE; counting idle `grounded=false` falsely flips
  the deck to "AI service unreachable" with a blank hero (the recurring empty-screen
  bug, test-guarded `tauri/ui/tests/session/grounding-failure.spec.ts`).

**macOS-vs-Windows backend split.**
- `src/vibemix/platform/` is the firewall keeping `__main__` OS-agnostic
  (`_audio_macos.py`, WASAPI loopback for Windows, `_hid_macos.py`). Windows is a v1
  target but the live QA loop runs on macOS only — the Windows audio/HID paths carry
  the least real-rig coverage and are the most likely to surprise at launch
  (`docs/windows-setup.md`).

---

## Process Risk

**Shared `git commit` across concurrent Claude/Codex sessions.**
- Kaan runs 2+ sessions in parallel; `git commit` absorbs EVERY staged file across
  all sessions. `git reset --soft HEAD~1` keeps racing. Verify
  `git diff --cached --name-only` matches intent BEFORE committing; for shared files
  (`CLAUDE.md`) stage hunk-level via a filtered patch + `git apply --cached
  --recount` (interactive `git add -p` is unavailable here). The god-modules above
  (`__main__.py`, `dj_cohost.py`) are the worst collision targets. (CLAUDE.md
  Conventions.)

**23 active worktrees, 40 git branches.**
- `.claude/worktrees/` holds 23 dirs; 40 branches exist. Audited 2026-06-07 (memory
  `project_autonomous_night_machine_2026_06_04` worktree-retention audit) — hygiene
  mostly good, but genuine work has been lost-then-recovered before (voice
  producers, telemetry-consent IPC, vibe-search cache fix). Risk: a fix lands on a
  worktree branch and never reaches ship (the dangling-producer pattern). Verify
  ship state on `ux-redesign-impeccable`, not a worktree.

**Ship built from an unpushed commit.**
- The DMG was built from `8bc721ce`, a surgical 7-file `src/vibemix` snapshot that is
  **NOT pushed** (handoff line 11). The shipped artifact's source-of-truth lives only
  in local git — a `git gc` / disk loss risks orphaning the exact ship source. Push
  or tag it.

---

## Test Coverage Gaps

**Quality is not unit-testable here.**
- The product's #1 risk (friend-score slop) has NO unit gate — green tests "prove
  NOTHING" (handoff line 8). The only real gates are the bench score
  (`src/vibemix/bench/`), the `vibemix-grounding-review` skill, and Kaan's ear. A
  PR can be fully green and still ship narrator slop.

**The QA config diverges from the ship config.**
- Live QA ran with `VIBEMIX_ANTI_SLOP=off` and a non-default model/probe env
  (handoff line 43). The citation-linter strip (Invariant #2, the release gate) was
  therefore NOT exercised in the proving session. "Tested" reactions were tested
  with the gate off.

**Windows backend under-tested on real rigs (see Fragile Areas).**

**Frozen-sidecar masks integration regressions** — see Fragile Areas; backend wiring
verified against the bundled binary can pass while current source is broken.

---

## Dependencies at Risk

**Unbacked CUE-DETR "parity verified" claim.**
- The V2 perception moonshot depends on a torch→ONNX export of CUE-DETR; the in-tree
  "parity verified" claim is **UNBACKED** — no first-party ONNX exists, the export +
  parity is real work (handoff line 32, memory drop-in scout). Do not treat
  structure-detection as shippable until the export lands. Gated, must not block v1.

**`pyrekordbox==0.4.4` installed `--no-deps`.**
- Rekordbox `collection.xml` import only; the SQLCipher path is explicitly unused
  (`pyproject.toml` install-recipe comment). A pin + `--no-deps` install is fragile
  across environments — a fresh install on a different rekordbox export schema could
  silently mis-parse.

**Local-AI extras silently fall back when missing.**
- Plain `uv run python -m vibemix` prunes `onnxruntime`/`tokenizers`/`sentencepiece`
  → CLAP / CUE / local-TTS features silently no-op with **no error** (CLAUDE.md
  Commands). A packaged path that lost an extra ships a dark feature, not a crash —
  hard to detect. The MOSS-TTS path reports `unavailable (MOSS local only; voice
  muted, no cloud fallback)` rather than failing loud.

---

## Missing Critical Features (launch-relevant)

- **No UI to switch brain / enter a key** (Brain-switch dark, above) — the entire
  proxy↔direct tiering is unreachable by a non-dev.
- **No mid-set cost-cap → upsell** (`agent/proxy_client.py:71-151`) — a proxy
  cost-cap stall currently becomes silent mid-set silence (the worst booth failure)
  with no path to "add your own key for uncapped".
- **Anticipation/lookahead** — the booth-DJ "call the drop before it lands" behavior
  is designed (`drop_predict.py` substrate) but not wired to the prompt (C9-gap).

---

## Marker Census (TODO / FIXME / HACK / XXX)

Codebase hygiene is **good** — markers are sparse. Real markers (excluding
`MIXXX`/word-boundary false matches):

**Python (1 real):**
- `src/vibemix/runtime/session_loop.py:20` — "EventDetector recent events (TODO —
  Phase 12-04 glue)". Stale phase reference.

**TypeScript (clustered, all benign-but-tracked):**
- **Tauri capability allowlist (3):** `tauri/ui/src/settings/SettingsDrawer.ts:1276`
  + `tauri/ui/src/settings/components/help-group.ts:15,43` — GitHub repo URL not yet
  in the Tauri capability allowlist; `openGithubRepo()` is wired but blocked. One
  note at `help-group.ts:236` flags an *earlier* TODO as already-stale ("this just
  works").
- **Phase 17 cohost-reconnect (3):** `tauri/ui/src/session/render-loop.ts:40,196,360`
  — no dedicated `ipc.cohost.reconnect` route; session passes an empty `session_dir`.
- **Recording restore (1):** `tauri/ui/src/settings/components/recording-browser.ts:349`
  — `ipc.recordings.restore` IPC not yet built ("impeccable Wave 5.B").

No `FIXME`/`HACK`/`XXX` markers in product code. The absence of markers does NOT mean
absence of debt — the real debt (this doc) lives in *dark wiring* and *measured
quality*, not in commented stubs.

---

*Concerns audit: 2026-06-08*
