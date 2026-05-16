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
