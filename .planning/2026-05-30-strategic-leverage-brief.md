# vibemix — Strategic Leverage Brief (2026-05-30)

> The 32-agent strategic investigation (6 lanes, adversarially scored), rescued to
> disk from its ephemeral workflow output. Companion to the constellation star-chart,
> the dead-path audit, and the Judge roadmap. Ship lens: every finding below is graded
> for what it does for a SHIPPED vibemix, not for novelty.

All load-bearing claims verified against source: `INVOKE_AUDIO_SECONDS=60.0` with the Kaan 18→30→60 history (constants.py:20), the audio-window branch at dj_cohost.py:2047, citation linter defaults `off` (__main__.py:1254-1263), the discarded skill-credit return (coach.py:391 bare call, mutate+save lands at :169), and the banned friend-words (negative_dict.py:60-63). Writing the brief.

---

# vibemix Leverage Brief — for Kaan

417 commits of deck-context work on the branch. Here's what 6 lanes + adversarial scoring actually found. Signal only.

## 1. How our AI is actually doing — the "real DJ friend, no slop" verdict

**The grounding architecture is genuinely strong — this is well above "voice assistant doing music commentary."** The brain hears real audio (not a transcript), every event carries measured DSP facts into the prompt, and EvidenceRegistry + per-turn `clear_source` + strict-subset registration make fabricated transitions/keys/recalls **uncitable by construction**. `live_claim_guard` is a real, unconditional, deck-evidence-grounded gate against "AI calls a single-deck move a great transition." The 6 persona cells (skill×mode) are differentiated for real, not cosmetic. The honesty discipline (honest-null everywhere, no fabrication) is the actual moat.

**Three real risks, in order:**

1. **Latency is the single biggest threat to the "alive, not late" bar.** The path bypasses Gemini Live, runs a custom cascade, attaches a **60s audio Part per non-ack turn** (`INVOKE_AUDIO_SECONDS=60.0`, constants.py:20 — confirmed), and the prompt itself admits reactions land 5-10s after the moment. The codebase honestly copes by making everything past-tense. That's the correct mitigation, but the constant is load-bearing and ear-tuned by you.

2. **Two of the most sophisticated grounding subsystems are dark in the live path.** The citation linter defaults **off** (confirmed __main__.py:1254-1263 — Gemini 3.x rarely emits the grammar, so a wired linter strips every turn); harmonic KEY_CLASH/TRANSITION_OPPORTUNITY is **off pending your ear-pass**. So "citation grounding is the release gate" (Invariant #2) is **partially theater at runtime** — it shapes the prompt and post-hoc telemetry but does not strip. The doc says uncited reactions "strip to the ack-bank fallback" — the ack-bank was **retired** 2026-05-19. That's a real doc-vs-code lie worth fixing.

3. **Repetition control is a 10-line no-repeat memory + a prompt instruction.** No semantic dedup. Once the citation linter is off, this is the most likely runtime slop vector.

**What's actually holding the line live:** slop filter + `live_claim_guard` + recall-subset strip (default-on whenever `_registry` exists) + single-modality audio + the "trust the audio / ears are the referee / past-tense" prompt spine. That's real and load-bearing — not the linter.

## 2. Highest-leverage wiring (the multipliers)

Honest note: the audit **downgraded most "multiplier" claims** — several touch one surface dressed as cross-pipeline. The genuinely multi-surface seams are *already wired* (taste_model → 3 surfaces; CUE-DETR auto-cue → live phrase anchor; CLAP → Learn exemplars; memory → live brain; debrief → profile writeback). **Don't churn those.** The real dead seams all cluster on **one asset: the v11 skill-tree.**

| Wire | Lights up | Reality check |
|---|---|---|
| **Skill-credit event** (the live-mastery spine) | live UI toast + pill + debrief | `_credit_live_skill_demo` mutates+saves `learn-progress.json` (confirmed coach.py:169) but the caller **discards the returned credit list** (confirmed bare call coach.py:391). v11 "Mastered unlocks" is **dark** — nothing renders it. **But:** reuse the existing `ipc.learn.progress_state` channel (already subscribed, already emitted by LessonRuntime) — do NOT invent a new `skill_credit` message. And the felt outcome is **M-effort frontend** (a skill-render consumer), not the claimed S. Gated behind your §EARNED-LIVE-MASTERED-VERIFY hardware ear-pass. |
| **Session recap card** — aggregate `move_grade` XP in debrief | live grade → debrief | The premise that "XP is already in events.jsonl" is **false** — grep returns zero `log_event` carrying grade/xp; it lives only in in-memory `SuggestionService` + ws broadcast. You must **add a per-transition `log_event` producer first**, then aggregate. Real producer→consumer wire, M-effort, not the free read it was pitched as. |

**The pattern:** the mature pipelines are done. The newest one (v11 skill-tree) is a **finishing job** — its producer fires and persists, but the consumers (UI/pill/debrief) never read it. That's where the cheap connective wins are.

## 3. New features worth building (grounded, anti-creep, star-magnet)

The real gap is **not missing engines** — it's that finished engines are **stranded behind the Viber chat agent or the live loop with no standalone, screenshottable surface.**

- **`library cue` — standalone auto-hot-cue command.** Reuses CUE-DETR ONNX (`cue_detr.py`) + the smart_cues A-H role policy + cue_export. Directly replaces **KimiCue ($29) and Mixed In Key ($58-99)** for free, local, torch-free. Genuine GitHub-star screenshot. **Two real blockers the card hid:** (1) the CUE-DETR model **isn't hosted** — sequence that first or the "free, point-and-go" headline is a lie; (2) the chain only connects through a *full library ingest* today, so you need a real `audio→cue→XML` bridge, not an argparse line. Build it — fits every lock — but budget the bridge + host the model.

- **Shareable cited recap PNG** (debrief Canvas→PNG). Reuses chapters' `citation_event_id` + the `stripper.py` cited-only gate (every recap sentence must resolve a citation — same anti-slop guard, don't loosen it). Client-side, no new data path. **Sequenced behind** the session-recap aggregate above (the richer "one highlight line" version doesn't exist yet). "Single highest star lever" is an *unproven marketing bet* — discount that, but it's a real first-run-delight surface.

- **Library prep "doctor" readiness report** (after cue + recap). Reuses the `doctor.py` CHECKS pattern + honest-null energy + Camelot. Honest caveat: it's a **post-ingest scorecard, not a first-run hook** — a cold user with no `collection.xml` still sees "0 tracks." Ship the thin 3-dimension version (key/cue/embedding); **drop or gate energy** (it's keyed by content-sig, not track_id — "energy per track" is either meaningless or a hidden full-decode sweep).

These are **thin surfaces on top of shipped engines**, not new engines. That's the whole anti-creep play.

## 4. Reinvented wheels — replace vs keep

**The hand-rolled inventory is unusually disciplined** — most of it is reinvented *on purpose* to honor torch-free/librosa-free/scipy-free, with comments citing exactly which heavy dep each numpy primitive replaces. The two model-shaped jobs already use the right OSS models.

**KEEP hand-rolled (do NOT churn):**
- CLAP ONNX (Xenova) + CUE-DETR ONNX (ETH-DISCO, ISMIR'24, MIT, web-confirmed best-in-class) — the right models, not wheels.
- Torch-free numpy DSP (Slaney mel, STFT, 63-tap windowed-sinc 48k→16k) — deliberate librosa/scipy replacements, unit-tested, zero reliability upside to swapping.
- `cosine_topk` over sqlite-vec storage — **swapping to native sqlite-vec KNN would reintroduce the macOS/Windows top-K divergence bug.** Intentional.
- PyAV/FFmpeg decode, Camelot lookup table (LLM must never compute keys), Levels EMA metering.

**The ONE defensible swap — and it's LATER, not now:**
- **Silero VAD (ONNX) for the mic/KAAN_SPOKE gate.** Today it's a bare RMS-EMA energy gate with **zero speech/non-speech discrimination** — bass bleed or headphone leak can fire a fake "Kaan spoke." Lock-clean (torch-free ONNX, onnxruntime already pinned). **But** the audit found the false-trigger is already **triple-gated** (mic mute + 7s cooldown during AI talk; zero-filled mic buffer; RMS-gated mic Part) — a phantom trigger yields a *humble ack*, not an invented conversation. So VAD is **polish, not an open hallucination class.** Touches one surface (~12 lines in coach.py). Revisit only if your real ear-pass surfaces open-mic false triggers. The "single highest-value swap" framing was an enthusiasm tell.

**Explicitly DON'T:** BeatNet/torch beat-tracker — its only consumer (mascot beat-entry anim) already self-gates on low BPM confidence; *no beat-quantized feature exists to consume better beats.* Already parked in planning. Adopting = torch lock-break for a non-existent consumer.

## 5. Experience + cost

**The machinery is mature — ahead of most pre-launch OSS.** Streaming pipe (chunk-by-chunk yield, bracket-balanced clip, slop-prefix head-gate), Invariant #5 idle≠fault timer, optimistic pill repaint, and the production-grade macOS signing chain (inside-out preflight, idempotent notarytool retry, staple, spctl, AIza-leak scan) — **do not churn any of these.**

**Cost — the one big lever, and it's yours to call:**
- The 60s audio Part is **re-uploaded and prefilled every non-diet turn** — `GeminiContextCache` caches only the text system prefix, NOT the audio (confirmed). At 32 tok/s that's ~1920 audio tokens/turn vs ~768 at 24s. Real prefill/TTFT + per-turn-cost delta on the brutal-latency path. The diet path (6s, confirmed dj_cohost.py:134) proves short windows ship today.
- **But this is a load-bearing ear-tuned constant** — you personally raised it to 60 for "fuller context," and the file header says don't re-tune without fresh live validation. The bench infra to A/B it exists. **The trial is cheap; the decision is yours, not autonomous.** A/B-trim toward ~24s for substantive events, with your ear in the loop.

**First-run gaps (known launch-gate items, not architecture):**
- The BlackHole driver-SHA + manifest entries are still **PLACEHOLDER** — gating actual one-click install. *Caveat:* the release-tag supply-chain gate **already fails** on placeholder, so don't flip the fetch-script to `exit-1` today (breaks every dev run for zero gain). The real digest is a human download-on-trusted-machine task. Bundle into the SignPath discharge.
- The "fetch CLAP model during onboarding to light up the pill" idea is **wrong about the mechanism** — the pill reads pre-computed vectors from `library-clap.db`; CLAP is an *ingest-time* dep, not suggestion-time. A fresh pill is silent because the **store is empty (no ingested library)**, not because the model is missing. Downloading the model leaves the pill exactly as silent. The real first-set blocker is a library-ingest onboarding step that doesn't exist.

**Dev-loop / eval-observability plan (token-cheap, high-leverage):**
The recorders and scorers exist and are well-built but **aren't wired to each other.** `bench/eval.py` (deterministic, RANK-only, reuses the live CitationLinter) only runs against a fixed offline corpus; `SessionTracer` writes categorized `trace.jsonl`; `StrippedRateTracker` tracks 15s slop-rate. Nothing **replays the live trace through the scorers**, and nothing aggregates cost or slop-rate across sessions — so **your ear (Phase-16) is the only signal the bar holds over time.** The leverage is **connecting recorders to scorers, not adding a SaaS** (Langfuse/Phoenix violate the no-managed-framework + privacy locks). Honest caveat: the live trace doesn't carry reaction text + registry snapshot today, so the real work is a **live-write instrumentation change first** (privacy-adjacent), then the thin replay-grader. M-to-L, sequenced — not the free reader it was pitched as.

## 6. Don't bother / already good (so we don't relitigate)

- **Single-modality audio Part** (screen_jpeg=None, no MIDI Part) — correct, load-bearing anti-hallucination decision (v4:1502). Don't re-add screen/MIDI as model Parts.
- **The trust-the-audio / past-tense prompt spine** — the honest, correct mitigation for high latency. Keep across all 6 cells.
- **The deliberate split** where the live path uses EvidenceRegistry citations and the pill uses decision_runtime — intentional, not a missing wire. Don't force-unify.
- **`move_grade` XP gamification in the Viber curate path is a separate system from the v11 skill-tree** — keep them separate; conflating = a bug.
- **Wire `TrackRelation.why` into the pill** — REJECTED. Premise is false: the pill's `why` already renders `key + bpm` (test pins `"similar vibe · 8A · 124"`), deck camelot/bpm already threaded live. It's a cosmetic phrasing swap (`· 8A · 124` vs `8A→9A, +5 BPM`), no grounding upgrade.
- **Repoint Tauri updater off altidus.world** — not an S tweak. `api.altidus.world` is the live proxy base every reaction phones (47 files, entitlements, crons). The bravoh.ai note governs *partner-facing marketing copy*, not infra. Park as a deliberate pre-tag ops decision.
- **Client-side SessionMeter spend-cap** — theater for an OSS binary (trivially bypassable); the **proxy per-client rate limit** owns runaway cost. A single set is cents. SessionMeter's role is telemetry feeding the proxy, not a client enforcer.
- **Hard length truncation / lower max_output_tokens** — REJECTED. `max_output_tokens` is a *shared* budget (thinking + output); `thinking_level=minimal` already eats part of it, so re-lowering risks clipping a legit short reaction mid-word. That's why your "don't cap output" comment exists.

## 7. The one move I'd make first

**Finish the v11 skill-tree's live→UI wiring — emit skill-credit over the existing `ipc.learn.progress_state` channel — right after your §EARNED-LIVE-MASTERED-VERIFY ear-pass.**

Why this over everything else:
- It's the **only real dead seam** in an otherwise-wired engine graph. The producer already fires, persists, and is **citation-gated** (inherits Invariants #2/#3 — it *cannot* fabricate an unlock). The credit return is just thrown away (coach.py:391). Right now v11 "Mastered" is **invisible to the user** — you built a mastery spine nobody can see.
- It's **on the active milestone** (v11.0 "Earned") — not scope creep, it's *finishing the thing you're already shipping*.
- It **reuses an existing channel** (already subscribed, already emitted) instead of inventing a new message type — minimal token spend, minimal surface.
- It's the **substrate for the next two NEXT items** (session recap card, shareable PNG) — they all consume the same skill/grade signal. Wire it once, three surfaces light up.

Honest scoping correction: the audit found the felt work is **M-effort frontend** (a skill-render consumer that doesn't exist yet), not the S it was first scored. And it's **gated behind your hardware ear-pass** — that's the actual first step, not an agent task. So: **you do the ear-pass; then an agent wires `progress_state` to a pill/debrief skill-render consumer.** That's the highest-ROI sequence — it converts already-built, already-grounded capability into something the user can actually see, on the milestone you're already on.
