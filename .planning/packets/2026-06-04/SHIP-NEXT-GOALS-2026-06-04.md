# SHIP-NEXT-GOALS — post-map re-rail (2026-06-04)

The whole-system fresh-eye map landed (`SHIP-MAP-MASTER.md`, committed `d1b925db`, synth HEAD `7ac35a84`). It confirms the previous re-rail goals (`SHIP-WIRE-GOALS-RERAIL.md`) are now LARGELY DONE in source: MOSS nuked, Chatterbox-only `tts_chain`, proxy default, `set_brain` handler, the fresh-user crash fixed, learn live-grade loop closed, cue provenance leak closed. The loops need NEW bounded targets or they will rabbit-hole. These goals are the map's critical path, one bounded piece per lane, each ending at a by-ear/by-eye DoD.

## ⛔ STOP PROTOCOL — carried forward (paste into every looping session, overrides any "keep goal active" text)

> STOP CONDITION: do exactly ONE bounded piece, commit it surgically when it is green + grounding-review-clean, then HALT and report — end the loop. Do NOT keep the goal active waiting for a live / by-ear / driven-set / DMG proof: that gate is KAAN's, not yours. If a sibling's uncommitted file blocks you, STOP and report the blocker — do not spin or clobber. The LIVE/ear/DMG proof is owned by Kaan + the organizer, never self-certified by a loop.

## The critical path (map §"Critical path to v1") — ordered

1. **VOICE reachability** (the #1 blocker now) — keystone/backend-boot lane
2. **START GATE backend handler** — keystone lane (touches `main()`, sequence behind/with #1)
3. **CITATION ts-carry** — sven lane (`dj_cohost.py`)
4. **PACKAGING (arm64-only)** — backend-boot + Kaan (Apple sign/notarize only; `VIBEMIX_PRETAG_MAC_ONLY=1`, NO SignPath/Windows on the v1 path). ⚠ **GA TAG LANDMINE:** the repo now lives at `Bravoh-ai/vibemix` (pushed `main` = `eec239ac`, 2026-06-04). `release.yml` AND `companion-sign.yml` fire on a **`v*` tag push** = the full signed matrix (macOS + **Windows** + SignPath + the now-BROKEN `--require-moss-source` gate). Do NOT push `v0.1.0` until: voice + start-gate land, the MOSS→chatterbox gate-swap is in, Windows is excluded from the v1 matrix, and the org repo has the signing secrets. The current **`0.1.0` source-snapshot pre-release** (non-`v` tag, fired only the benign SBOM job) is the interim marker, NOT the signed GA.
5. **KEYSTONE capture** — Kaan-only (LIVE=0 today)
6. **STREAK robot voice** — deferred, sequenced (not v1-launch-critical)
7. **[v1.1] WINDOWS** — kicked off once macOS v1 ships: GPU-backend Chatterbox build + Windows spec + SignPath (its own milestone, not v1)

## Owner decisions Kaan must make (gate the path)

- **D1 — `mlx-audio` as a `pyproject.toml` extra. ✅ RESOLVED (Kaan 2026-06-04: "1 gb is cool"):** APPROVED. Ship the **8bit** model (`mlx-community/chatterbox-turbo-8bit`, 675MB) — no need to drop to 4bit. Total footprint ~1.0–1.1GB (403MB deps incl. transformers 5.x but NO torch + 675MB model + 720KB ref). Measured: deps `mlx` 189M / `scipy` 82M / `transformers` 49M / `numpy` 24M. ONNX path rejected (5.7GB AND benched-dead live on Mac: CPU 1.3–2.5s TTFT, CoreML vocoder fails). The backend-boot lane executes immediately, no further gate.
- **D2 — the "no API-key surface" CI gate vs the BYO key field.** `tests/security/test_no_api_key_surface.py` fails on the in-GUI Gemini key field shipped under locked decision #2. The gate (Phase-33 "never ship a key surface") and the BYO field are in head-on conflict. Retire or scope-narrow the gate (1-test policy call). Blocks `full-test-matrix` CI → blocks a tag.
- **D3 — Windows v1 scope. ✅ RESOLVED (Kaan 2026-06-04: "macos ship first"):** v1 = **macOS Apple-Silicon (arm64) ONLY**. Windows + macOS-Intel are post-v1 fast-follows. Note: `mlx-audio` is Apple-Silicon-only (Metal), so an Intel Mac would be voiceless anyway — arm64 IS the only platform that can run the locked voice; this is the correct and clean v1 target. **Consequences:** (a) SignPath OSS approval (Windows) drops OFF the v1 critical path — the tag no longer waits on that external clock; use `VIBEMIX_PRETAG_MAC_ONLY=1` for the arm64 tag. (b) The Windows GPU-backend BUILD is explicitly deferred (not a v1 goal). (c) Packaging implication for the backend-boot lane: the updater-manifest gate (`scripts/.../check_updater_manifest_ready.py:15`) hard-requires all 3 platform binaries → either relax it to arm64-only for a v1 `latest.json`, or ship v1 without auto-update (manual download) and add the updater when Windows/Intel land. Implementation choice, not a Kaan gate. **(d) Windows is the IMMEDIATE NEXT milestone (v1.1), kicked off the moment macOS v1 ships (Kaan: "as we finish macos we start shipping win") — NOT abandoned. The Windows GPU-backend Chatterbox build (ONNX-DirectML preferred, else torch+CUDA) + Windows PyInstaller spec + SignPath are the v1.1 spine. Sequence after the macOS keystone capture, do not parallelize into v1.**

## Re-rail — one bounded goal per session

### BACKEND-BOOT / KEYSTONE lane (owns `main()` + `config_store` + voice) → VOICE REACHABILITY (#1)
```
/goal SHIP-WIRE — make the locked Chatterbox voice REACHABLE on a packaged launch. The source-side
MOSS-nuke + Chatterbox-only tts_chain already landed; the voice is still voiceless because mlx_audio is
not installed and not a dependency, and the ref clip is unbundled. DISTRIBUTION (Kaan-decided): the
~400MB Python deps + the 720KB ref clip ride IN the DMG (PyInstaller, unavoidable); the 675MB 8bit MODEL
is NOT in the DMG — it is FIRST-RUN fetched from HF hub (the repo is public; mlx_audio.load_model already
auto-downloads it at chatterbox_tts.py:154), pre-fetched via the wizard with progress, NEVER mid-set.
Bounded piece:
(1) Add `mlx-audio` as a `pyproject.toml` extra, 8bit model (Kaan-approved ~1GB; Apple-only; gated
    import, no hard dep on non-Apple).
(2) Bundle `cohost_voice_ref.wav` as a PyInstaller `datas` asset in vibemix-core.macos.spec at
    models/chatterbox/cohost_voice_ref.wav; chatterbox_tts.py:46 already defines that bundled path —
    make resolve_ref_path() prefer it, fall back to the dev-cache path.
(3) Add `install_chatterbox_model()` to library/model_assets.py + register in the `library models
    --install chatterbox|all` CLI + ModelProgress callback (mirror install_clap_model/install_moss_model)
    so the 675MB weights pre-fetch with a progress bar + a pinned HF revision + an actionable offline
    message — NOT a silent first-generate() stall. Trigger it once from the wizard (download before the
    first set); offline -> voiceless banner, then pre-warm once on disk.
(4) Env-seed os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine) at __main__.py:~1420 +
    in the packaged-defaults path (launchd/Dock strip VIBEMIX_*; this is the "always silent" root cause).
    ⚠ DE-CONFLICT: if the START-GATE lane is running CONCURRENTLY (it restructures main()), SKIP this
    step here and hand the env-seed to the START-GATE lane — `__main__.py` is single-owner, never edit it
    from two loops. This VOICE goal then lives entirely on its own island (no __main__.py) = parallel-safe.
(5) Swap the release gate --require-moss-source -> --require-chatterbox-source across
    scripts/dist/pretag_check.sh + .github/workflows/release.yml (every site) — verify the chatterbox HF
    repo + pinned revision (no self-hosted archive; simpler than MOSS).
PROOF (by-ear, not test-green): on a packaged-style launch reading config.json (NOT env), after the
wizard fetch chatterbox_available() is True and the cohost speaks in the pranker voice; grep shows no
MOSS gate left. ISLAND: pyproject.toml + vibemix-core.macos.spec + agent/chatterbox_tts.py +
library/model_assets.py + the wizard install trigger + __main__.py(env-seed only) + the dist scripts.
STOP PROTOCOL applies. git add <exact paths> NEVER -A; socket 8765 one (pkill before probe);
commit -s Kaan Özkan <rahipdotaci@gmail.com>.
```

### KEYSTONE lane (owns `main()`) → START GATE backend handler (#2, sequence behind/with #1)
```
/goal SHIP-WIRE — wire the START GATE backend (Kaan: "when we pre-ship this is the only thing"). The
frontend half + IPC schema (ipc.session.start/stop) already landed; the backend handler is absent and
heavy models sit resident at idle. Bounded piece:
(1) register_handler("ipc.session.start", _on_session_start) + "ipc.session.stop" in session_loop.py.
(2) Split main() into a light idle boot + an _activate_session() that starts capture + reactions; idle =
    cold, Start activates, Stop/idle releases the heavy models. v1 scope = Start + Stop-releases + the
    silent background pre-warm hook, NOT a full eager->lazy refactor.
(3) ⚠ YOU OWN __main__.py — also add the VOICE lane's env-seed here in the same edit:
    os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine) at the boot/packaged-defaults path
    (the VOICE lane is skipping it to avoid a two-loop race on this single-owner file).
PROOF (by-eye/by-bus): app idle = no Start = no reactions/no resident model; Start flips to active;
Stop releases. ISLAND: __main__.py + runtime/session_loop.py. Do NOT edit the IPC schema (frontend owns
it; the types already exist). STOP PROTOCOL applies. SHARED LAW as above.
```

### SVEN lane (owns `dj_cohost.py`) → CITATION ts-carry (#3)
```
/goal SHIP-WIRE — make the deck "underline its own citation" gesture fire LIVE. Today _push_transcript
(dj_cohost.py:1880) emits no ts and ws_bus.py:783 stamps a separate _now_iso(), so SessionLayout.ts:1171
joins on a ts that never byte-matches the reaction ts -> the gesture fires only in unit tests, silently
dark live (Seam D). Bounded piece: thread ONE reaction_ts from the reaction through _push_transcript so
the transcript event and the citation event carry the SAME ts the frontend joins on.
PROOF (by-bus): a live reaction's transcript_delta and its [ev:...] citation share a ts; the FE join
resolves. ISLAND: agent/dj_cohost.py (+ the ws field if needed, NOT the schema shape). STOP PROTOCOL
applies. SHARED LAW as above.
```

### LIBRARY lane → CI RED-gate + cue-landing consolidation (unblocks the tag)
```
/goal SHIP-WIRE — clear the stale CI RED gates that block a tag, then resolve W13. Bounded pieces (commit
each separately): (1) re-pin tests/repo/test_readme_shape.py + test_readme_feature_matrix_sync.py to the
deliberate bravoh.ai README swap (commit 5a1e3533). (2) Per Kaan's D2 decision, retire/scope-narrow
tests/security/test_no_api_key_surface.py so the BYO key field passes. (3) W13: route the live Viber
auto-cue (toolset.py:2231 _auto_cue_marks_for_export) through the reusable cue_landing.land() so the two
cue spines cannot diverge — OR, if Kaan defers, leave a one-line note and STOP.
PROOF: full default suite + the named gates green at HEAD. ISLAND: tests/** + library/**. Do NOT edit
product behavior to satisfy a test — fix the test policy. STOP PROTOCOL applies. SHARED LAW as above.
```

### LEARN lane → already ~90% closed; bound the remaining wire
```
/goal SHIP-WIRE — wire [ev:BEATMATCH_GRADED] into the LIVE credit path (W12). The learn live-grade loop
closes (OBSERVE->GRADE->IPC->credit->unlock) but runtime/coach.py has 0 references to BEATMATCH_GRADED,
so on a real driven set the highest-value DJ skill can only be credited from practice, never a live
demonstration. Bounded piece: consume [ev:BEATMATCH_GRADED@t] in runtime/coach.py's credit path
(_credit_live_skill_demo) honoring Invariant #3 (practice audio never over a live set) + Invariant #2
(cited demonstration only). PROOF (by-bus): a cited live beatmatch demonstration credits the skill.
ISLAND: src/vibemix/learn/** + runtime/coach.py (credit path only). STOP PROTOCOL applies. SHARED LAW.
```

### ORGANIZER (me) → packaging coordination + verify
Verify each lane's commit against the 3 proof tiers (SRC ≠ PKG ≠ LIVE), enforce grounding-review on any
new co-host utterance + Invariant #3 on learn audio, and coordinate the fresh signed arm64 DMG once the
voice + Start-gate land + the dirty seam files commit. The keystone LIVE capture stays Kaan's hand on the rig.
