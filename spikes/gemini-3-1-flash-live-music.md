# Gemini 3.1 Flash Live — music co-host spike verdict

> This is a scaffolded verdict template — Phase 41 LAT-09 ships the framework;
> the real-DJ-clip session that fills the blanks is a Kaan-action discharge
> per [KAAN-ACTION-PROXY §LAT-09](../.planning/KAAN-ACTION-PROXY.md#lat-09).
> Until that session runs, status stays at `engineering-scaffolded`.

**Status:** engineering-scaffolded
**Run date:** _____
**Operator:** Kaan (real-DJ-ear required)
**Scaffold landed:** Phase 41 Plan 41-06 (2026-05-16)
**Locked decision:** default cascade unchanged for v3.0 regardless of spike outcome (CONTEXT.md). Spike output sets the v3.x toggle decision only.

State machine:
`engineering-scaffolded` → `kaan-action-discharge` (operator running the spike) → `verdict-written` (verdict box checked, all sections filled).

---

## Setup

- **Model under test:** `gemini-3.1-flash-live-preview` (spike-only; MUST NOT leak to `src/vibemix/`)
- **Baseline for comparison:** current v4 cascade (Gemini 3 Flash multimodal → Gemini 3.1 Flash TTS)
- **Audio source:** Real DJ session via BlackHole 48kHz (djay Pro / Rekordbox / Mixxx)
- **Representative clip target:** 5 min techno ~124 BPM with 2 transitions + 1 phrase shift
- **VAD config:** `realtimeInputConfig.automaticActivityDetection: low` (music-tolerant)
- **Proactive Audio:** enabled
- **Audio modality only:** spike intentionally drops MIDI / screen / nowplaying to isolate Live latency + grounding signal
- **Recording sink:** `spikes/recordings/spike_<UTC-timestamp>.wav` + `spike_<UTC-timestamp>.metrics.json`

OPERATOR NOTE: confirm exact kwarg names for VAD + Proactive Audio against the installed `livekit-plugins-google` v1.5.8 at run time. The script flags this inline.

---

## Measurements

Numbers come from `spike_<UTC-timestamp>.metrics.json`.

- TTFT (first audio chunk after event): ___ ms (target: <500 ms; cascade baseline: ~1400 ms)
- Total turn time (event → end-of-utterance): ___ ms (target: <2500 ms; cascade baseline: ~3800 ms)
- p50 TTFT across N turns: ___ ms
- p95 TTFT across N turns: ___ ms
- Cost per minute observed: ___ €/min (target: comparable to cascade at ~0.003 €/min)
- Reactions per minute (Proactive Audio on): ___ rpm (sanity check — too many → bursty, fails "real DJ friend" feel)
- Session uptime before cap / error: ___ s (Live API 15-min cap is load-bearing — see Session Cap Workaround Status)

---

## Anti-Hallucination Behavior

Verbatim transcript samples — paste 5–10 representative reactions from `spike_<UTC-timestamp>.wav`:

```
[mm:ss] <reaction text>
[mm:ss] <reaction text>
...
```

Grounding judgment (Kaan's ear):

- Did Live model identify the right deck / track moment? (yes / partial / hallucinated)
- Did Proactive Audio mode invent beats, drops, or transitions that didn't happen? (yes / no / sometimes)
- Did Live model maintain "real DJ friend" feel vs cascade? (better / equal / worse)
- Did Live model preserve cascade-tier grounding signals (mic context, lookahead Parts)? (n/a — spike drops these; note whether the missing context hurt the feel)
- "Harikaydı" Phase 40 baseline regression check: would Kaan ship this voice over the v4 cascade? (yes / no / not without v3.x design changes)

---

## Session Cap Workaround Status

The Live API hits a 15-min session cap (Pitfall 4 / research). If the spike duration exceeds 15 min:

- Did session reset transparently? (yes / no / crashed)
- Was state continuity preserved across resets? (yes / no / n/a — single short spike)
- Estimated v3.x design cost to handle the cap: (trivial / moderate / blocking)

Skip this section if the spike ran ≤ 15 min — note "n/a — short spike, cap not stressed".

---

## Verdict

Exactly one box checked.

- [ ] **defer-to-v3.x toggle** — Live + Proactive Audio shows promise; ship an opt-in toggle in a future v3.x release after addressing [open issues listed in Rationale]. Cascade stays default.
- [ ] **sealed-no** — Live + Proactive Audio is not music-grounding-suitable for vibemix's "real DJ friend" bar. Revisit only if Google ships a music-aware variant or a grounding-instruction surface that fixes the failure modes documented in Rationale.

---

## Rationale

2–3 sentences. Ear notes — what made you check the box you checked. Reference the specific transcript moments in Anti-Hallucination Behavior that drove the call.

_______________________________________________________________

_______________________________________________________________

_______________________________________________________________

---

## Sign-off

- [ ] Verdict box checked above (exactly one)
- [ ] All 6 H2 sections filled (no `___` blanks except in Session Cap if n/a)
- [ ] Status field flipped from `engineering-scaffolded` → `verdict-written`
- [ ] Spike recording filed under `spikes/recordings/` (git-LFS if > 50 MB; otherwise direct commit)
- [ ] Operator: Kaan / ____________  Date: ____________
