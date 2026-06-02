# CODEX_READY — MOSS Voice: Default-Host + First-Run Auto-Download (ship kill-shot ①)

> **THE #1 ship gate** (RED-TEAM ①, MASTER "the one next move"). On any machine but Kaan's the co-host boots **MUTE** — the MOSS download pipeline is fully built, but there is no *default* hosted archive, so `moss_model_installable()` is false out of the box and nothing fetches the weights. Until a fresh machine speaks, nothing else matters.
> **Owner: Codex A** (code) + **Kaan/Momo** (the one ops action: host the archive). Claude is read-only; produced this packet + will do the LIVE verify. Re-verified at HEAD `e49b2f63`.

## Why (precisely — the infra is DONE, only the default + first-run are missing)
The hard part already shipped. Verified at HEAD:
- `library/model_assets.py:545` `_moss_archive_config()` — validates `VIBEMIX_MOSS_TTS_ARCHIVE_URL` / `_SHA256` / `_SIZE` (`:31-33`).
- `model_assets.py:576` `install_moss_model()` — downloads, verifies SHA+size, safe-extracts the archive into the cache (zip-slip guarded `:532`).
- `model_assets.py:571` `moss_model_installable()` — **returns True ONLY if the env URL is set** (`:573`). No env → false → no install path.
- `model_assets.py:581-582` docstring: *"The repo does not ship or guess a public 600MB+ model URL."* `:623-626` is the user-facing "not hosted by default" error.
- `agent/local_tts.py:191` `local_tts_enabled()` = flag AND model-cached → **false on every fresh install**.
- `__main__.py:7603,7628` only *reads* `moss_model_installable()` for a status surface — **nothing calls `install_moss_model()` at startup.**

Net: the machine that can download + verify + extract MOSS exists; it's just never given a URL and never triggered. This is a **default-pin + a first-run call**, not a new system. (Mirror the CLAP pattern: `_CLAP_BASE_URL` constant `model_assets.py:27` + verified per-file fetch `:239`.)

## Scope
**IN:** (1) default archive pins so `moss_model_installable()` is true out of the box; (2) a first-run auto-download wired to startup with a visible "preparing voice / unavailable:[reason]" state; (3) keep the env override as the ops/enterprise escape. **OUT:** bundling the 728 MB weights into the DMG (too big — download is correct); changing the voice engine or `tts_chain`.

## The one ops action (Kaan/Momo — blocks this packet)
Host the `MOSS-TTS-Nano-100M-ONNX` archive (≈728 MB `.zip`/`.tar.gz`) at a stable HTTPS URL (HF release asset, Bravoh CDN, or S3), then compute and hand back: **URL + SHA-256 + byte size**. The grounding (728 MB, host+download mirroring CLAP's `_ensure_onnx_assets`) is already done — this is just publishing the file. Until this exists the code change can't have real default pins (only a placeholder + test).

## 1. Default pins — `library/model_assets.py`
Add module constants beside the env-name constants (`:31-33`):
```python
_MOSS_DEFAULT_ARCHIVE_URL  = "<hosted https url>"   # from the ops action
_MOSS_DEFAULT_ARCHIVE_SHA  = "<64-char lowercase sha256>"
_MOSS_DEFAULT_ARCHIVE_SIZE = <int bytes>
```
In `_moss_archive_config()` (`:545`): when the env vars are unset, fall back to the default triple (env still overrides). `moss_model_installable()` (`:571`) then returns True by default. Keep all existing validation (https-only, 64-char SHA, positive size) applied to the defaults too.

## 2. First-run auto-download — startup wiring
At launch, when `local_tts_enabled()` is false (`local_tts.py:191`) AND `moss_model_installable()` is true:
- kick `install_moss_model()` off the event loop (`loop.run_in_executor` — it's blocking network+IO; never block the audio/event loop), and
- broadcast a **"preparing voice"** status over the ws bus while it runs, then **"voice ready"** or **"voice unavailable: <reason>"** on failure (reuse the existing status surface at `__main__.py:7628`; the `drive-vibemix` skill must be able to read this state). On failure the co-host stays grounded-but-silent (never crashes, never routes to a paid/cloud voice — `local_tts.py:17-18` contract).
- One download per machine — the content-addressed cache makes re-launch free.

## 3. DMG (sequenced after this — do NOT rebuild before)
RED-TEAM ② / B-4: the shippable `dist/vibemix-0.0.1.dmg` is ~177 commits stale and **born mute**. Rebuild + sign + notarize from clean HEAD **only after this lands**, or the signed build re-ships silent. (Separate packet `CODEX_READY-macos-signing-notarization-flow.md`.)

## Acceptance
**SRC (Codex):** `tests/library/test_model_assets.py` — `moss_model_installable()` true with defaults + no env; env still overrides defaults; bad default triple rejected by the same validators. First-run trigger covered with a mocked `install_moss_model` (no real 728 MB fetch in CI). Suite green, ruff clean.
**LIVE (Claude verifies on a clean cache):** wipe `~/.cache/vibemix/moss-tts-onnx/`, launch from source → "preparing voice" → download+verify+extract → co-host **speaks**. The kill-shot is the gate: *a machine that is not Kaan's produces audible voice.*
**Proof tiers:** SRC (Codex) → LIVE (Claude, clean-cache) → PKG (rebuilt DMG, after). Don't conflate.

## Gate
No grounding-review needed (doesn't change what it SAYS, only that it CAN say it). Gate = the LIVE clean-cache speak test. **External dependency: the ops hosting action — this packet is BLOCKED until the URL+SHA+size exist.**
