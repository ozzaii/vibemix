# KAAN-ACTION-PROXY

Items deferred from autonomous execution that require Kaan's ear, eyes, or proxy-side credentials. Filed per the `gsd-autonomous fully` mode rule ("defer blockers, continue work — never pause").

---

## Phase 29 (Post-Session Debrief MVP UI)

### A5-VOICE-LISTEN — Achird voice quality at 60–90s

**Filed:** 2026-05-15 (Plan 29-00 Wave 0 probe)
**What:** Validate that the Achird Gemini TTS voice stays coherent / natural / not-monotone over a 60–90 second narrated TLDR. The live runtime only stresses Achird for 8–14 word snippets; the debrief stresses it 10× longer.
**How:** After Plan 29-01 ships, run a real debrief on a real recorded session, listen to `<session>/debrief/tldr.mp3`, and judge: PASS (ship Achird) or FAIL (flip `DEBRIEF_TTS_VOICE = "Kore"` in `src/vibemix/debrief/tldr.py`).
**Fallback in place:** Constant is single-source — swap is one-line.
**Blocking on Phase 29 ship?** No (e2e tests assert the MP3 plays, not voice quality).

### A7-PROXY-RESPONSESCHEMA-VERIFY — Proxy passes `responseSchema` through

**Filed:** 2026-05-15 (Plan 29-00 Wave 0 probe)
**What:** Confirm `api.altidus.world/vibemix/gemini` forwards the `responseSchema` field on `generate_content` calls so structured-output drill generation in Plan 29-01 runs in `mode=proxy` cleanly.
**How:** Provision a dev JWT (`VIBEMIX_PROXY_JWT`) → POST a tiny Pydantic-schema generate_content request through the proxy → inspect the response shape against the schema. PASS = use `mode=proxy` for drills; FAIL = drills use Pydantic post-hoc JSON validation as the fallback.
**Fallback in place:** `drills.py` JSON-parses + Pydantic-validates regardless of which mode produced the response — no code change needed if A7 fails.
**Blocking on Phase 29 ship?** No.

---

How to clear an item: post the result (verdict + date) inline above and remove the entry, or move to `.planning/audits/RESOLVED.md` if the project wants a historical log.

---

## Phase 41 (Gemini SKU Upgrade + Latency Stack v2)

## §LAT-09 — Gemini 3.1 Flash Live spike investigation

**Status:** scaffolded; discharge pending
**Scaffold landed:** Phase 41 Plan 41-06 (2026-05-16)
**Verdict file:** `spikes/gemini-3-1-flash-live-music.md`

### Why
CONTEXT.md locks: "default cascade unchanged for v3.0 regardless of spike
outcome." The spike validates whether Gemini 3.1 Flash Live + Proactive Audio
is music-grounding-suitable enough to become a v3.x opt-in toggle. The
research framework + verdict template are scaffolded; only a real DJ clip
+ Kaan's ear produces the verdict.

### How to discharge

1. Ensure `GEMINI_API_KEY` is set in environment.
2. Connect a real DJ source (djay Pro / Rekordbox / Mixxx) feeding BlackHole
   at 48kHz — same pre-flight as a normal vibemix session.
3. Cue up a 5-min representative DJ clip: techno around 124 BPM, includes
   2 transitions + 1 phrase shift (matches research clip recommendation).
4. Run:
   ```
   python -m spikes.scripts.run_live_spike --duration-s 300
   ```
   Output: `spikes/recordings/spike_<UTC-timestamp>.wav` + `.metrics.json`
5. Listen to the recording offline. Note hallucinations, grounding failures,
   feel of latency vs cascade baseline. Compare against the v4 cascade
   "harikaydı" feel (Phase 40 baseline).
6. Fill in `spikes/gemini-3-1-flash-live-music.md`:
   - Measurements section: paste numbers from `.metrics.json`
   - Anti-Hallucination Behavior: verbatim transcript samples
   - Session Cap Workaround Status: did session hit 15-min cap? — relevant
     only if running > 15min duration
   - Verdict: check ONE box (defer-to-v3.x toggle OR sealed-no)
   - Rationale: 2–3 sentence ear notes
7. Flip status field from `engineering-scaffolded` → `verdict-written`.
8. Commit verdict file.

### Expected time
1–2 hours total (5 min spike + 30 min offline listen + 30 min verdict writeup).

### Acceptance criteria
- `spikes/gemini-3-1-flash-live-music.md` status field == `verdict-written`
- All 6 sections filled (no blanks; "n/a — short spike" acceptable for
  Session Cap Workaround Status when duration ≤ 15 min)
- Verdict box checked (exactly one of two options)
- Recording file filed under `spikes/recordings/` (git-LFS if > 50 MB) —
  commit only at Kaan's discretion per privacy stance on session audio
