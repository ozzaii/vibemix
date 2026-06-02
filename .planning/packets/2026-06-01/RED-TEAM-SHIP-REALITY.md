# RED-TEAM — Ship Reality + Kill Squad (2026-06-01)

> Adversarial workflow (`wf_8a9d4872`, 11 assassins + synthesis, ~987k tokens, codegraph-verified). Mined the capability inventory, Mixxx-gold archive, research/handoffs, and today's LIVE capture. Raw: `_red-team-ship-reality-raw-wf_8a9d4872.json`.
> HEAD at run: `cb16053d`/`d17afead` (tree moving, Codex landing). Read-only — 0 product files touched.

## VERDICT: **FIXABLE-NEAR-MISS — not a failure.**
The brain is **real and honest** — it grounds on live audio+MIDI and *refuses to slop* (proven LIVE today). Shipped as-is it dies for one reason: **a fresh machine cannot speak** (MOSS voice not bundled/hosted) and the **signed DMG is 165 commits stale**. The engine earns the "real DJ friend" promise; the packaging strands it. Both are fixable before ship.

---

## 1. WHAT ACTUALLY SHIPS (real vs claim)
- **REAL:** master audio + FLX4 MIDI → event detection → **grounded, anti-slop** reactions. LIVE-proven 2026-06-01: citations resolve; ungrounded HEARTBEAT → `action=strip` → *"I can't call that a transition until I have clear two-deck proof."*
- **CLAIM≠REAL — voice:** "talks into your headphones" → on any machine but Kaan's, **MUTE**. `model_assets.py:624`: *"MOSS TTS ONNX is not hosted by default."*
- **CLAIM≠REAL — two decks:** "deck-aware" → in practice **master-mix + MIDI**; deck B silent on the real rig (per-deck routing is advanced). Brain honestly reports `B_silent`, doesn't invent.
- **REAL but thin:** starved input (no library, mono master, one deck) → co-host **narrates** ("heavy grinding synth, vocal repeating") = Kaan's *"sadece açıklama yapıyor."* Root cause = input, not code.
- **NOT in v1 reality:** mascot 3D, live screen-vision (`dj_cohost.py:2199` `screen_jpeg=None`, deliberate), Mixxx OSC/key/beatgrid (NOT-FOUND), beatmatch "Mastered" credit (no producer).

## 2. THE 5 WAYS THIS DIES (ranked)

| # | Threat | Evidence | Tier | Verdict | Fix |
|---|--------|----------|------|---------|-----|
| ① | **Fresh machine = silent co-host** — MOSS neither bundled nor hosted | `vibemix-core.macos.spec` no moss in `datas`; `model_assets.py:624` "not hosted by default"; `local_tts_enabled()` = flag AND model-cached → false on every new install | PKG | **KILL-SHOT** | **YES** — host MOSS archive, pin URL+SHA+size, first-run auto-download (B-1/B-2) |
| ② | **Signed DMG 165 commits stale + arm64-only** — every install ships known-bad behavior; the slop Kaan heard came from THIS binary | `dist/vibemix-0.0.1.dmg` 31 May; 165 commits since; LIVE Finding 6 | PKG | **KILL-SHOT** | **YES** — rebuild+sign+notarize from clean HEAD *after* ①; x86_64 leg or scope "Apple Silicon v1" (B-4) |
| ③ | **Keyless brain (proxy) unconfirmed live** — default `direct` needs `GEMINI_API_KEY`; keyless stranger (the actual market) unproven | `__main__.py:933` FATAL no-key; proxy → `api.altidus.world` :913, round-trip never confirmed | LIVE/infra | **WOUND** | **HARD** — valid upstream key on proxy + 1 live round-trip (B-3, Kaan) |
| ④ | **Per-deck identity needs a rig 90% won't build** — deck B silent, library empty → never names tracks | LIVE Findings 2,5; `deck_pairs` opened but `B_silent`; `library_tracks=0` | LIVE | **WOUND** | **YES (scope)** — ship master+MIDI common case; per-deck = honest bonus (Kaan decision) |
| ⑤ | **Cost claim "free at scale/<€50" unbackable** | `pricing.py:117` true only if ① ships; budget XFAIL (H7) | SRC | **WOUND** | **YES** — keep `budget` internal, strip claim from launch copy |

## 3. FUD GRAVEYARD (scary-sounding, evidence says FINE — stop worrying)
- **"co-host slops/hallucinates"** — FUD on current source. Gate strips ungrounded lines (LIVE-verified). The slop Kaan heard = **stale DMG ②**, not the engine.
- **"Mixxx/OSC/key/beatgrid broken"** — not broken, **never existed** (NOT-FOUND). Just DROP the claims.
- **"clean-room Mixxx = legal risk"** — mitigated: `NOTICE`/`NOTICE.md`/`THIRD_PARTY_LICENSES.md` exist (S2 landed). Needs 1-line Kaan sign-off.
- **"demo_mode violates trust-the-audio"** — already deleted (S3, zero importers).
- **"screen-vision dead"** — intentional invariant (`screen_jpeg=None`), not a bug. DROP the live-vision claim.

## 4. WHAT TO DO (routing per kill-shot)
1. **① MOSS bundling → NEW CODEX LANE** *(release-critical).* Host MOSS-TTS-Nano ONNX, pin URL+SHA+size, first-run auto-download + a `drive-vibemix`-captured "preparing voice / unavailable:[reason]" state (folds B-2).
2. **② DMG rebuild → Codex lane, SEQUENCED after ①.** Rebuild/sign/notarize from clean HEAD; x86_64 vs "Apple Silicon v1" (Kaan). Never rebuild before ① or you re-ship the mute.
3. **③ Proxy brain → KAAN-ONLY INFRA.** Live Gemini key on `api.altidus.world` + one keyless round-trip.
4. **④ Per-deck scope → KAAN-ONLY DECISION** + tiny copy edit. Adopt master+MIDI v1; per-deck = bonus. Optional R3 routing-wrong detector spike.
5. **⑤ Cost claim → DROP NOW** (budget internal); re-baseline later (R5).

### THE SINGLE NEXT MOVE
**Spin the MOSS-weights-hosting + first-run-auto-download Codex lane (①).** Until a fresh machine can speak, nothing else matters — and it must land **before** the DMG rebuild so the signed build isn't born mute.
