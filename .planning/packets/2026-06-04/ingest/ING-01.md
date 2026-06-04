# ING01 — VOICE reachability adversarial verification (ship-ingestion pass)

**HEAD read at: `d7d5337a175ac90612702c3adda4d17aa3918899`** (branch `ux-redesign-impeccable`, 2026-06-04).
The SHIP-MAP-MASTER was synthesized at `7ac35a84`; the tree has advanced **26 commits** since (`git log 7ac35a84..HEAD`). The voice/start-gate landscape moved substantially in those 26 commits — several SHIP-MAP "DARK" claims are now LANDED, and the `CODEX_READY-CHATTERBOX-VOICE-WIRED.md` packet (which described a gated-OFF, MOSS-default transitional state) is fully SUPERSEDED. This pass verifies the CURRENT source, not either doc.

Proof tiers: **SRC** = green test on source · **PKG** = present/correct in a signed DMG built at HEAD · **LIVE** = a real stranger reaches it on a packaged launch. Never conflated. `test-passing-but-dark = 0`.

The 26 commits that moved the voice/boot world (newest first): `d7d5337a` test(config) device defaults · `0e5590c5` fix(voice) prefetch chatterbox for packaged launch · `18dc95cb` test(start-gate) lock idle-cold · `eec239ac` feat(voice) preflight pinned chatterbox model · `02ffb7c0` test(boot) align smoke with start-gated defaults · `de9233f9` docs(voice) remove retired moss comments · `4831b226` fix(library) route Viber auto-cues through cue landing · `8c0c0ffa` fix(learn) credit live beatmatch grade · `fddddfc9` refactor(voice) **retire legacy moss runtime** · `7082fb8d` build(voice) **require packaged chatterbox reference** · `d7c652b8` docs resolve D3 macOS arm64 v1 / Windows v1.1 · `51d91428` docs resolve D1 mlx-audio 8bit ~1GB · `23f3167d` feat(session) **SHIP-WIRE START-gate** · `1a66cca0` feat(voice) **make chatterbox the only cohost voice**.

---

## VERDICT TABLE (the 6 required wires)

| # | Wire | Verdict | Tier reached | File:line |
|---|------|---------|--------------|-----------|
| a | `mlx-audio` is a `pyproject.toml` extra | **LANDED** | SRC + (PKG-ready) | `pyproject.toml:161-168` (`tts-local` + `ai-local`) |
| b | `cohost_voice_ref.wav` is a PyInstaller `datas` asset; `resolve_ref_path()` prefers bundled | **LANDED** | SRC; PKG-conditional | spec `vibemix-core.macos.spec:307` + `.windows.spec:262`; `chatterbox_tts.py:106-116`; `scripts/dist/chatterbox_bundle.py:30-43` |
| c | `install_chatterbox_model()` in `library/model_assets.py` + a `library models --install chatterbox` verb | **PARTIAL — installer LANDED, CLI verb CLAIMED-BUT-DARK** | SRC | installer `model_assets.py:490`; CLI choices `__main__.py:4816` exclude `chatterbox` |
| d | `os.environ.setdefault("VIBEMIX_TTS_ENGINE", ...)` seeded at `__main__.py` boot/packaged-defaults | **LANDED** (two sites) | SRC | `__main__.py:1063` (`_apply_packaged_defaults`) + `:1434` |
| e | release gate swapped `--require-moss-source` → `--require-chatterbox-source` | **LANDED** | SRC | `pretag_check.sh:109/111/113`; `release.yml:356/400/427/542` |
| f | `chatterbox_available()` has a path to True on a packaged launch | **LANDED (seam correct); LIVE-unproven** | SRC TRUE on this machine; PKG/LIVE conditional | `chatterbox_tts.py:124-130`; live activation `__main__.py:1751-1755` |

Net: **5 of 6 fully LANDED**, 1 partial (the CLI `--install chatterbox` verb is missing but the wizard path covers the real fetch). The #1 ship-blocker the maps named — "mlx_audio not installed / not an extra" — **is RESOLVED at HEAD**. The real remaining gap is now LIVE-tier proof (the keystone capture) plus the GA-tag landmine, not a missing source wire.

---

## (a) mlx-audio as a pyproject extra — LANDED [SRC]

`pyproject.toml:161-168`:
```toml
tts-local = [
    "mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'",
]
ai-local = [
    "onnxruntime>=1.20",
    "tokenizers>=0.22",
    "mlx-audio>=0.3; sys_platform == 'darwin' and platform_machine == 'arm64'",
]
```
- The extra is named **`tts-local`** (NOT `[chatterbox-mlx]` as the CODEX_READY packet predicted), and `mlx-audio` is ALSO folded into the umbrella `ai-local` extra (the one CLAUDE.md says the installer path uses). So `uv run --extra ai-local python -m vibemix` pulls the voice dep — no separate flag needed.
- The PEP 508 marker `sys_platform == 'darwin' and platform_machine == 'arm64'` correctly scopes it to Apple Silicon (decision: Intel Macs + Windows are voiceless, honest banner). This matches the SHIP-SHAPE lock (v1 = macOS arm64 only).
- **Adversarial note:** the comment claims the project is "torch-free, Transformers-free, librosa-free" yet `mlx-audio` reintroduces `transformers`. This was the CODEX_READY open-decision O1; resolution doc `51d91428` (D1) accepts the ~1GB 8-bit footprint. Not a blocker, but the CLAUDE.md "Transformers-free" claim is now FALSE for the `tts-local`/`ai-local` extras — a doc drift to flag.
- **Live probe on this machine:** `mlx_audio: INSTALLED` in the project `.venv`. (The SHIP-MAP claimed it was NOT installed — STALE; it has since been synced into the venv.)

## (b) ref clip as a PyInstaller datas asset + resolve_ref_path prefers bundled — LANDED [SRC], PKG-conditional

- The spec wires it: `vibemix-core.macos.spec:36` imports `from scripts.dist.chatterbox_bundle import collect_chatterbox_ref_datas`, and `:307` does `datas.extend(collect_chatterbox_ref_datas())`. Identical wire in `vibemix-core.windows.spec:35/262`.
- `scripts/dist/chatterbox_bundle.py:30-43` (`collect_chatterbox_ref_datas`): reads the ref from `VIBEMIX_CHATTERBOX_REF` or `~/.cache/vibemix/cohost_voice_ref.wav`, bundles it to dest `models/chatterbox/cohost_voice_ref.wav`. **CAVEAT: if the ref file is absent at build time it returns `[]` (non-fatal, prints a stderr note)** — so a release builder who forgot to place the licensed WAV ships a voiceless DMG silently-but-honestly. The pretag gate `--require-chatterbox-ref` (below) is what catches that.
- `chatterbox_tts.py:106-116 resolve_ref_path()`: precedence is **(1) `VIBEMIX_CHATTERBOX_REF` override → (2) bundled candidates → (3) dev-cache `~/.cache/vibemix/cohost_voice_ref.wav`**. `bundled_ref_candidates()` (`:93-103`) probes `sys._MEIPASS` and `sys.executable`-parent `_internal/models/chatterbox/cohost_voice_ref.wav` — exactly the spec dest. So a frozen launch resolves the bundled ref FIRST. Seam is correct.
- The release ref-readiness gate `check_sidecar_bundle_ready.py:146-177` (`_chatterbox_ref_wave_status` + `chatterbox_release_ref_ready`) validates the bundled ref is **mono / 16-bit / 24000 Hz / non-empty** at `_internal/models/chatterbox/cohost_voice_ref.wav`. This is a real PKG gate, not a stub.
- **PKG status:** the ref is NOT vendored in git (`find . -name cohost_voice_ref.wav` outside `.git` = nothing; it is release-owned/licensed content). On the dev machine it exists (`~/.cache/vibemix/cohost_voice_ref.wav`, 384 KB — note the CODEX_READY packet said 720k/15s; current is 384k). A PKG build only carries voice if the builder places the licensed WAV first. Licensing (music-stripped YouTube vocal) remains a Kaan product/legal decision.

## (c) install_chatterbox_model() + CLI verb — PARTIAL [SRC]

- **Installer: LANDED.** `model_assets.py:490 install_chatterbox_model(force, progress)` — pre-fetches the pinned snapshot `mlx-community/chatterbox-turbo-8bit` @ rev `2f2e21a03863f86a1274d1060dcc188e7cde77e1` (`:34-35`) into the HF cache, verifies `CHATTERBOX_REQUIRED_FILES` (`:48-58`, incl. `model.safetensors` 706 MB), returns `installed` only when `chatterbox_model_cached()` confirms all files on disk. Intentionally NOT bundled into the DMG — model fetched at first run. `install_models(target)` (`:829`) accepts `"chatterbox"` / `"required"` / `"all"` and routes to it (`:855-859`).
- **CLI verb: CLAIMED-BUT-DARK.** `__main__.py:4815-4823` defines `--install` with `choices=("clap", "cue")` — **`chatterbox` is NOT an accepted choice.** So `library models --install chatterbox` (the verb the task asks to verify) does **not exist** on the CLI; argparse rejects it. The installer is only reachable today via the **wizard** (below) or programmatically.
- **Where it IS reached:** `runtime/wizard.py:499-534 _prefetch_chatterbox_model()` calls `install_chatterbox_model` off-thread during first-run, sets `_voice_muted` and emits a voice-status frame on failure (fail-soft, never crashes the wizard). This is the real first-run fetch path — it covers the user-facing need even though the explicit CLI verb is absent. Commit `eec239ac`/`0e5590c5` are this prefetch work.
- **Gap to close (small):** add `"chatterbox"` to the `--install` choices (+ help text + the `sp_models` epilog at `__main__.py:4950` which only lists `clap`) so ops/support can pre-fetch headless. One-line argparse change; the dispatch (`install_models`) already supports it.

## (d) env-seed VIBEMIX_TTS_ENGINE at boot — LANDED [SRC]

Two correct sites, both `setdefault` (so an explicit shell/.env override wins, AND the default survives `open -a`/Dock/launchd env-stripping — the documented packaged-launch hazard):
- `__main__.py:1049-1065 _apply_packaged_defaults()` → `:1063 os.environ.setdefault("VIBEMIX_TTS_ENGINE", tts_engine)`, seeded from `ConfigStore.tts_engine` (default `"chatterbox"`). Called at `main()` start, `:1109`.
- `__main__.py:1433-1434` — a second seed before agent construction reading the same config field.
- `config_store.DEFAULT_TTS_ENGINE = "chatterbox"` (`config_store.py:65`) is the source of truth, and `engine_selected()` (`chatterbox_tts.py:119-121`) reads `VIBEMIX_TTS_ENGINE` defaulting to `"chatterbox"` even if unset. Belt + suspenders: even with NO env and NO config, the engine selects chatterbox.

## (e) release gate swap moss→chatterbox — LANDED [SRC]

- `--require-moss-source` is **gone from the entire repo** (grep returns zero hits in `pretag_check.sh` and `release.yml`). Replaced by `--require-chatterbox-source` AND a new `--require-chatterbox-ref`:
  - `pretag_check.sh:109/111/113` — `SIDECAR_CHECK=(... --require-chatterbox-ref --require-chatterbox-source)`.
  - `release.yml:356, 400, 427, 542` — `--require-chatterbox-source`.
- The gate impl `check_sidecar_bundle_ready.py:180-200 chatterbox_release_source_ready()` does a real HF API HEAD on the pinned `repo@revision` and asserts the returned `sha` matches the pinned revision — i.e. the gate fails the tag if the pinned public source moved. Commit `7082fb8d`/`fddddfc9` are the swap + MOSS-runtime retirement.
- **No MOSS source left:** `src/vibemix/agent/local_tts.py` is **DELETED** (confirmed on disk). `tts_chain.py` is Chatterbox-only and raises `ChatterboxUnavailable` with no MOSS branch and no cloud fallback. The SHIP-MAP claim "MOSS nuked" is TRUE at HEAD. (Note: a `src/vibemix/agent/moss_tts/` directory still exists on disk — worth a follow-up grep to confirm it is dead/unreferenced, but the runtime path no longer imports it.)

## (f) chatterbox_available() path-to-True on a packaged launch — LANDED (seam), LIVE-unproven

`chatterbox_tts.py:124-130 chatterbox_available()` returns True iff ALL THREE: (1) `importlib.util.find_spec("mlx_audio")` is not None, (2) `resolve_ref_path()` is not None, (3) `chatterbox_model_cached()` True (offline, no first-line download). `chatterbox_unavailable_reason()` (`:133-143`) gives a distinct actionable string per failing condition.

**Live probe on THIS machine (dev):** `chatterbox_available()` returns **True** — `mlx_audio` installed + ref present + model cached. The activation path uses it: `__main__.py:1751-1755` builds `ChatterboxLocalTTS()` only when `engine_selected() and chatterbox_available()`, else mute via `_build_tts_chain_or_mute` (`:243-259`, returns `_livekit_not_given()` on `ChatterboxUnavailable` — never crashes, prints a banner `:1768`). Never-mute → never-crash is honest.

**Path-to-True on a real PKG launch requires, in order:** (1) the DMG was built with the `tts-local`/`ai-local` extra so `mlx_audio` is frozen in (spec hiddenimports `mlx`/`mlx_audio`/`mlx_lm` at `vibemix-core.macos.spec:151-153` and `:185-187` — **the third-party dep IS in the spec**, satisfying the CLAUDE.md "new third-party dep must be added to the spec" rule); (2) the builder placed the licensed ref so `collect_chatterbox_ref_datas()` bundled it; (3) the first-run wizard prefetched the 706 MB model (or the user ran it online once). All three are wired; **none is proven on a current signed DMG (PKG tier) and the co-host has never spoken over real audio (LIVE tier = 0).** That LIVE capture is Kaan-only and remains the keystone.

---

## Locked-decision cross-check (the 4)

1. **VOICE = Chatterbox only, MOSS nuked, Mac=mlx-audio, no-GPU=voiceless+banner** — **LANDED in source.** `local_tts.py` deleted; `tts_chain.py:38-39` raises `ChatterboxUnavailable` if engine not selected, Chatterbox-only chain; `DEFAULT_TTS_ENGINE="chatterbox"`; voiceless-not-crash via `_build_tts_chain_or_mute`. Remaining = PKG/LIVE proof + the licensed-ref placement, not a code wire.
2. **BRAIN = hosted Bravoh proxy DEFAULT, client flips direct→proxy, set_brain BYO, no-key graceful (no sys.exit)** — **LANDED [SRC].** `config_store.py:271 llm_mode = "proxy"`. `__main__.py:1131-1181`: env>config mode resolve; **direct-without-key falls back to proxy (`:1157-1166`)**; proxy setup/network failure sets `brain_unavailable_reason` + logs, **no `sys.exit`** (the `sys.exit(3)` at `:1517/:1573` are audio-device-missing sentinels for the Tauri setup banner, NOT brain crashes — verified in context). `set_brain` handler wired both-ends: `session_loop.py:288 register_handler("ipc.settings.set_brain", self._on_settings_set_brain)` → `:486` persists `llm_mode` + writes key to `brain_env_path()`. The map's "crash fixed" claim holds.
3. **START GATE = no heavy model at idle, Start button, silent pre-warm, Stop releases** — **LANDED [SRC]** (the SHIP-MAP `7ac35a84` "backend handler DARK" is STALE; landed in `23f3167d`). Backend handler: `session_loop.py:278-279 register_handler("ipc.session.start"/"stop", _on_session_start/_on_session_stop)` → `:331/:356`, gated on `_session_active()` (`:322`), wired to lifecycle callbacks. `main()` idle/activate split: `__main__.py:1592 "--- SHIP-WIRE START gate ---"` boots light (`_RunGatedMusicState` cold bus view `:1624`), heavy graph built only in `_activate_session()` (`:1704`); "chatterbox armed (loads on Start)" banner `:1446`. Frontend Start button: `SessionLayout.ts:1046-1058` (armed-gate `start` button, optimistic `data-runstate="running"` repaint per CLAUDE.md rule) → `onStart` → `render-loop.ts:73-80 sessionStartHandler()` → `emitIpc("ipc.session.start", {})`. Stop symmetric (`:982`, `render-loop.ts:86-93`). IPC both-ends: schema `messages.schema.json:1430-1463` (with explicit both-ends `$comment`), TS types `ipc/messages.ts:31-32/324-329`. SRC test: `test_smoke_03b_idle_is_cold_until_start` (commit `18dc95cb`) proves idle leaves build_llm / build_tts_chain / AgentSession / DJCoHostAgent UNcalled — verified GREEN (5 passed). Silent prewarm hook exists (`chatterbox_tts.py:258 prewarm()`, daemon thread, fail-soft).
4. **STREAK = Daft-Punk Technologic robot voice, SEQUENCED behind rebinding to a cited EXECUTED transition first** — **NOT-STARTED (correct, per lock).** Recipe lives in `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`; the self-applause signal it must be rebound off (`runtime/suggestion.py:1365/1391/1450 _attach_grade_progress`) is unchanged. Out of ING01 voice-reachability scope; flagged here only for completeness.

---

## SRC test confirmation (run at HEAD)

- `tests/agent/test_chatterbox_tts.py` + `tests/agent/test_tts_chain.py`: **18 passed** (1.45s).
- `-k "smoke_03b or idle_is_cold or start_gate or session_start"`: **5 passed** (idle-cold START-gate lock GREEN).
- **Dark-but-green caveat held to account:** the chatterbox tests pass even with `mlx_audio` mocked via the injectable `ChatterboxEngine` seam, so SRC-green alone does NOT prove voice plays. On THIS dev machine the real path is genuinely available (probed True), but a green CI box without `mlx_audio`/ref/model would still pass these tests while shipping voiceless — exactly the PKG/LIVE-vs-SRC gap. The pretag gates (`--require-chatterbox-ref`/`--require-chatterbox-source`) are the PKG-tier backstop; the LIVE keystone has none by definition.

---

## GA-TAG LANDMINE — STILL LIVE (PKG/release-infra, not a code wire)

`release.yml:57-60` fires on `push: tags: 'v*'`. The build matrix at `:271-291` includes **`build-macos` arm64 (macos-14) AND x86_64 (macos-13)**, and `:470-540` is a full **`build-windows`** job (SignPath signing). The local `VIBEMIX_PRETAG_MAC_ONLY=1` escape only suppresses SignPath gates in `scripts/dist/pretag_check.sh:148` — **it does NOT alter the GitHub Actions matrix.** So pushing a real `v*` tag today WILL fire the Windows + Intel-mac matrix. Both Intel-mac and Windows are voiceless (mlx-audio is Apple-arm64-only by the PEP 508 marker) and Windows additionally needs SignPath. The moss→chatterbox gate-swap (e) means the gate won't FAIL on missing MOSS anymore, but the cross-platform matrix is still wired hot. **Do NOT push `v0.1.0` until the matrix is scoped to arm64-mac-only (or Windows/Intel jobs are conditioned off) — this is the SHIP-SHAPE-vs-release.yml mismatch, an infra edit + secrets call, owner-gated.** The `0.1.0` source-snapshot pre-release on a non-`v` tag did NOT fire the matrix (correct).

---

## README / DOCS PARTNER-COPY — STILL VIOLATING ALL POLICIES (CLAIMED-BUT-DARK on the policy)

`README.md` (30 KB, unchanged 15:35) violates every stated public-copy rule AND now carries STALE voice copy:
- **Leaks `api.altidus.world`** — lines 39, 61, 241. Policy: say "Bravoh's hosted service".
- **Names `Gemini`** — lines 39, 61, 149, 241. Policy: "AI model".
- **Names `MOSS` (and STALE — MOSS is nuked)** — lines 229 ("Sven speaks through the local MOSS voice path"), 241 ("Speech is rendered locally through the MOSS voice path"). Double problem: model-name leak + factually wrong at HEAD (voice is Chatterbox now).
- **`bravoh.com` not `bravoh.ai`** — line 63 (`security@bravoh.com`).
- **Dev feature-matrix dump / internal slop** — lines 130-149 (Phase numbers, "SHIPPED 2026-05-28" dates), line 69 ("Kaan ear-passes daily"), lines 86/198 ("KAAN-ACTION-LEGAL.md"), AST-gate/commit chatter.
- **README CI gates that pin this** (per the task's stated 4): `tests/repo/test_readme_shape.py`, `test_readme_feature_matrix_sync.py` (AUTO-GEN + `sync_feature_matrix.py --check`), `scripts/launch/check_readme_grids_a11y.py` (dj grid 6 imgs / controller grid 10 cells vs `midi/profiles`), `scripts/check_readme_hero_hash.py` (hero sha256 PLACEHOLDER sentinel). **Adversarial note from the SHIP-MAP:** two of these gates (`test_readme_shape`/`feature_matrix_sync`) historically ASSERTED `altidus.world/vibemix` in the README; a later commit swapped the funnel to `bravoh.ai` and re-pinned the gate (`aaa330ad test(repo): re-pin README funnel to bravoh.ai`). So the README rewrite for partner-copy must be coordinated with these gates or `full-test-matrix` CI (and therefore a tag) breaks. This is a real, scoped, NOT-STARTED rewrite task — owner-visible.

---

## What ING01 confirms vs corrects

- **CONFIRMED LANDED:** voice reachability source wiring (a/b/d/e/f), the START gate both-ends (decision 3), proxy-default + set_brain + no-key-graceful (decision 2), MOSS nuke (decision 1 source-side).
- **CORRECTS the maps (stale at `7ac35a84`):** START-gate backend is no longer DARK (landed `23f3167d`); `mlx_audio` is no longer "not installed / not an extra" (it's the `tts-local`/`ai-local` extra AND installed in the dev venv); `chatterbox_available()` returns True on the dev rig.
- **CORRECTS the CODEX_READY packet (fully superseded):** it described MOSS-default gated-OFF Chatterbox with a `[chatterbox-mlx]` extra and MOSS fallback — none of that is HEAD. HEAD is Chatterbox-default, MOSS-deleted, extra named `tts-local`.
- **REMAINING GAPS (precise):**
  1. CLI `library models --install chatterbox` verb absent — argparse choices are `("clap","cue")` (`__main__.py:4816`); fetch only reachable via wizard. Small one-line fix. [SRC]
  2. PKG tier = 0: no current signed HEAD DMG carries the verified voice (licensed ref must be placed at build; mlx-audio extra must be in the build env; model fetched first-run). [PKG]
  3. LIVE tier = 0: the co-host has never spoken over real audio — the keystone capture is Kaan-only. [LIVE]
  4. GA-tag landmine: `release.yml` matrix still fires Windows + x86_64-mac on a `v*` tag; `VIBEMIX_PRETAG_MAC_ONLY` does not gate the Actions matrix. Infra/secrets, owner-gated. [PKG/release]
  5. README partner-copy violations + STALE MOSS copy, pinned by 4 CI gates — coordinated rewrite NOT-STARTED. [docs]
  6. Doc drift: CLAUDE.md "Transformers-free" is now false for `tts-local`/`ai-local` (mlx-audio pulls transformers 5.x); `moss_tts/` dir still on disk (confirm dead).

**Bottom line:** the #1 blocker the ship-map named (voice reachability source wiring) is **RESOLVED at `d7d5337a`**. The honest #1 blocker is now the **LIVE keystone capture** (Kaan's hand on the rig), gated practically by a fresh signed arm64 DMG that bundles the licensed ref + mlx-audio (PKG), and the **GA-tag matrix landmine** must be scoped to arm64-mac before any `v*` push.
