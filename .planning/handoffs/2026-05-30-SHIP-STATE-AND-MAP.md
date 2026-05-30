# ✦ vibemix SHIP-STATE + THE MAP — 2026-05-30 (read-me-FIRST)

> **For the next AI (or human):** this is the single clean index of *what is built,
> what works, what's blocked, and WHERE EVERYTHING LIVES.* Read this first, then
> dive into the linked docs only as needed. Written after a long build-and-ship
> session; supersedes nothing but consolidates everything.
>
> **Read order:** this doc → `2026-05-30-DEEP-HANDOFF-NEXT-SESSION.md` (the prior
> session's spirit + engine-works-live milestone) → `2026-05-30-VIBEMIX-KNOWBOOK.md`
> (the grounded engine/architecture reference) → `2026-05-30-SHIP-PLAN.md` (the
> owner-tagged ship blockers). Then act.

---

## §1 · THE HEADLINE (honest)

> **UPDATE 2026-05-30 (later, boot-fix session): THE SIDECAR NOW BOOTS.** B1 is
> FIXED. The frozen sidecar boots fully and cleanly — verified on both the raw
> onedir AND the bundled `.app` sidecar: reaches `-> agent started.`, MIDI
> DDJ-FLX4, 12 IPC types, `listening to BlackHole 16ch @ 48000Hz (4ch)`, and
> `mascot bus on ws://127.0.0.1:8765`, with graceful SIGINT shutdown. B3 + B4
> (sign pipeline) are also FIXED in-repo. The `.app` now bundles a WORKING engine.
> Fixes: `0af90e90` (lazy-cli + cli-unexclude + B3/B4), `6d2dcebc` (Cartesia
> http_session), `50d78a62` (recorder mkdir), `46e21ec6` (test-iso). See §4.
> **Boot-test trick:** a clean boot block-buffers stdout — kill with **SIGINT**
> (not SIGKILL) to flush it; only a crash or graceful exit shows the log.

**(Original headline, now partly superseded.)** The engine is ALIVE and the app
BUILDS, SIGNS, and NOTARIZES:

- ✅ **Signed + notarized + Gatekeeper-accepted dmg exists**: `dist/vibemix-0.0.1.dmg`.
  `spctl` = `accepted, source=Notarized Developer ID`; signed by
  *Developer ID Application: Francesco Fasanella (UK7DYFK6F8)* → Apple Root; stapled.
  (A fresh signed dmg with the BOOTING sidecar is being produced in the boot-fix session.)
- ✅ **Its Python sidecar NOW boots** (was ❌ — the livekit circular ImportError, B1).

**The product is now well past the boot wall.** Remaining: B2 (key delivery,
kaan/momo), B5 (Windows), B6 (ear-pass, kaan) — documented below.

---

## §2 · WHAT THIS SESSION SHIPPED (commits, all on `live-tuning-or-brain`)

| Commit | What |
|---|---|
| `bb6a2cf2` | **Per-deck device upgrade fires zero-config** — BlackHole 2ch→16ch swap now triggers on the rekordbox external-mixer signal, no env var (closed the `e73911df` gap live-verify caught). `deck_capture.py` + `__main__.py`. |
| `6e26b7a6` | **Cartesia (Sonic) wired into `main()` boot + honest 3-way voice boot-log** — finishes the TTS switch. |
| `4437b57b` | Rated `livekit-plugins-cartesia` + regen `AUDIT.md` (fixed a `0589b85b` audit drift). |
| (sibling session) `e0a4aefc` | CLAP model auto-download on first use (was ship-plan item #4). |
| (sibling session) `651a62a8`, `0c6c7b6a` | SignPath OSS / Windows signer docs. |

**Verified green this session:** frontend (149 files / 1430 vitest), Python suite
(6858 passed — the only 5 failures are a *concurrent* session's uncommitted
cost-study lane: `_router_config.py`/`cost.py`/`pricing.py`/budget-CLI, NOT ship
blockers), **Cartesia voice proven end-to-end** (24kHz audio through the real
plugin path; key valid), and the **full sign→notarize→staple pipeline** (below).

**Uncommitted-mine:** `.planning/2026-05-30-SHIP-PLAN.md` (commit it).

---

## §3 · THE MAP — where everything lives

### Code (Python core — `src/vibemix/`)
- Architecture detail: **the KNOWBOOK** (`.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md`) maps all 12 homes + every engine. Start there.
- Key files this session touched: `audio/deck_capture.py` (per-deck routing global default), `__main__.py` (`_maybe_upgrade_input_device_for_deck_audio` ~line 543, Cartesia boot ~1158), `agent/tts_chain.py` + `agent/config.py` (Cartesia chain), `runtime/coach.py` (the Judge 4d join, prior session).
- The live brain: `agent/dj_cohost.py` (line 51 `from livekit.agents import Agent` = the import that triggers B1).

### Tauri shell (`tauri/`)
- Frontend: `tauri/ui/` (React/TS, build = `npm run build`, test = `npm test` from `tauri/ui`). Wizard: `tauri/ui/src/wizard/` (6 steps: PERMISSIONS·DEVICE·CONTROLLER·SKILL·PROFILE·TELEMETRY — **NO key step**, see §4 B2).
- Rust parent: `tauri/src-tauri/`. Config: `tauri/src-tauri/tauri.conf.json5` (productName vibemix, v0.0.1, id `world.bravoh.vibemix`, targets [app,dmg], `beforeBuildCommand` = `../scripts/dist/prepare_tauri_build.py`).
- **Build invocation (CI-correct):** `cd tauri/src-tauri && cargo tauri build` (NOT from `tauri/` — beforeBuildCommand resolves `../scripts` from the project root).

### Packaging / sidecar
- `scripts/build_sidecar.py` — PyInstaller onedir → `tauri/src-tauri/binaries/vibemix-core-<triple>/`. Applies the livekit patch (below) + runs an AIza-leak scan (passed: 0 Gemini keys in bundle).
- `vibemix-core.macos.spec` / `.windows.spec` — the PyInstaller specs. `runtime_hooks=["rthooks/pyi_rth_livekit_agents.py"]`.
- `rthooks/pyi_rth_livekit_agents.py` — the livekit pre-flight hook (INEFFECTIVE for B1, see §4).
- `scripts/dist/patch_livekit_agents_init.py` — patches the venv's `livekit/agents/__init__.py` to split `from . import cli, …` into cli-first (INSUFFICIENT for B1).
- `scripts/dist/prepare_tauri_build.py` — frontend build + sidecar-readiness check (the `beforeBuildCommand`).
- `scripts/dist/repair_macos_app_sidecar_symlinks.py` — Stage-1b symlink repair before codesign.

### Signing / notarization
- `scripts/dist/sign_macos.sh` — the post-build sign→create-dmg→notarize→staple→spctl pipeline. **Has 2 real bugs** (§4 B3/B4). Driven by `.github/workflows/release.yml` (gated on Apple secrets).
- `tauri/src-tauri/entitlements.macos.plist` — distribution entitlements (5 keys). **Has the AMFI `--`-comment bug** (§4 B3).
- Docs: `docs/signing-macos.md`, `docs/release-process.md`.
- **Live creds ON THE MAC (verified working):** Dev ID cert `Francesco Fasanella (UK7DYFK6F8)` in keychain; ASC API key `~/.appstoreconnect/private_keys/AuthKey_URMDRP5M3P.p8`; `APPLE_ID`/`APPLE_TEAM_ID` in shell env; app-specific password provided this session → stored in a **notarytool keychain profile named `vibemix-notarytool`** (persists; reusable via `--keychain-profile vibemix-notarytool`).

### Artifacts (on disk)
- **`dist/vibemix-0.0.1.dmg`** — the signed+notarized dmg (119M).
- `tauri/src-tauri/target/release/bundle/macos/vibemix.app` — the signed .app (sidecar inside dated 19:22 = this session's engine). ⚠ This .app was re-signed; the *running* instance broke when re-signed mid-run (don't re-sign a running app).
- `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` — the standalone rebuilt sidecar.
- **Ephemeral (in `/tmp`, WILL BE LOST):** `/tmp/vibemix_sign2.sh` (the *working* sign recipe — force-sign-all-Mach-O + keychain-profile notarize) and `/tmp/entitlements_clean.plist` (comment-stripped entitlements). The recipe is reproduced in §5; persist it into the repo if keeping.

### Planning docs (`.planning/`)
- `handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md` — engine/architecture grounded reference.
- `handoffs/2026-05-30-DEEP-HANDOFF-NEXT-SESSION.md` — prior session spirit + engine-works-live.
- `2026-05-30-SHIP-PLAN.md` — owner-tagged ship blockers (62% ship-ready, from the ship-plan Workflow).
- `2026-05-30-zero-config-ship-blockers.md` — the 44-finding zero-config audit.
- This doc — the consolidated map + state.

### Runtime config / logs (Kaan's Mac)
- Installed-app keys: `~/Library/Application Support/vibemix/.env` (GEMINI/CARTESIA/OPENROUTER keys written this session to un-block the running app).
- Dev keys: repo-root `.env` (gitignored).
- Logs: `~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/{ui.log,sidecar.log}` + `~/Library/Application Support/vibemix/install.log`.

### Memory (cross-session knowledge)
- `~/.claude/projects/-Users-ozai-projects-dj-set-ai/memory/MEMORY.md` (index) + the `project_*` / `feedback_*` files. Key ones: `project_live_verify_2026_05_30`, `project_vibemix_knowbook`, this session's signed-build + frozen-bundle facts.

---

## §4 · OPEN BLOCKERS — with exact fix recipes

### B1 — Frozen sidecar can't boot: livekit circular `ImportError` ✅ RESOLVED (`0af90e90`)
> **FIXED.** The "split cli first" guess was wrong — loading cli *at all* is the trigger
> (cli pulls voice/worker which re-enter the partial parent for cli). Real fix: cli is
> never used by vibemix (only Agent/AgentSession/RealtimeModel), so make it **lazy** via
> the module's PEP-562 `__getattr__` using `importlib.import_module` (NOT `from . import
> cli`, which recurses through `__getattr__`→`hasattr`→infinite loop). PLUS cli had to be
> *un-excluded* from `_ANALYSIS_EXCLUDES` in both specs — `start()` imports it
> unconditionally, so it's a runtime dep, not a dev CLI. Verified: clean boot to `agent
> started` + ws bus. The historical diagnosis below is kept for context.

**Symptom (historical):** `dist/vibemix-0.0.1.dmg` opens but the co-host never starts. Running the
frozen sidecar directly (`…/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin`)
boots through env/genre/MIDI/persona, then crashes:
```
File "vibemix/agent/dj_cohost.py", line 51   (from livekit.agents import Agent)
  File "livekit/agents/__init__.py", line 23  (from . import cli)
ImportError: cannot import name 'cli' from partially initialized module 'livekit.agents'
```
**Reproduces in the piped-stdio spawn context** (exactly how Tauri launches the sidecar). dev-source does NOT hit it.

**Root-cause diagnosis (grounded this session):** livekit-agents 1.5.14 `__init__.py:23`
does `from . import cli, inference, …, voice`; PyInstaller's frozen importer doesn't
bind submodules in list-order, so a chained load re-enters `livekit.agents` before
`cli` is bound. Two existing mitigations are present but **both fail**:
1. `scripts/dist/patch_livekit_agents_init.py` splits the line so `from . import cli`
   is first. Applied to the venv (confirmed). **Insufficient** — the frozen crash is
   on the `from . import cli` line *itself* (cli's own import re-enters), not on `voice`.
2. `rthooks/pyi_rth_livekit_agents.py` tries to pre-import `livekit.agents.cli` at
   frozen startup — but it's wrapped in `try/except: pass`. **Fundamentally can't
   work:** importing `livekit.agents.cli` requires `livekit.agents.__init__` to
   complete first, which is exactly the cycle; the rthook's import fails and the
   `except: pass` SWALLOWS it silently, so no pre-flight happens.

**Fix direction (for the next session — verify by rebuild+boot, no signing needed):**
- The cycle is inside `livekit.agents.__init__` + `cli/cli.py`. Read
  `.venv/.../livekit/agents/cli/cli.py` to find the exact `from livekit.agents import …`
  re-entry, then make the patch import the leaf deps *in dependency order* before `cli`,
  OR monkeypatch `sys.modules['livekit.agents']` with a pre-built stub, OR (cleanest)
  lazy-bind: have the patch set `cli` as a lazy module attribute.
- **Fast iteration loop (no sign/notarize):** edit the patch/rthook → `uv run python
  scripts/build_sidecar.py --spec vibemix-core.macos.spec` (~2 min) → run the frozen
  binary **piped** (`./vibemix-core-… 2>&1 | head`) → confirm it gets PAST the livekit
  import (it'll fail later on audio in a headless env — that's fine). Only sign once it boots.
- The rthook's `except: pass` should at minimum `print(repr(e))` so the failure isn't silent.

### B2 — Downloaded dmg is MUTE for anyone but Kaan (no key delivery) 🔴 kaan/momo
The co-host needs a key; it's read ONLY from `.env` (repo or `~/Library/Application
Support/vibemix/.env`). The **wizard has no key-collection step** (6 steps, none for
the key) and there's **no `/register` proxy** wired. A stranger hits `VIBEMIX-CORE
STOPPED`. **Decision (Kaan/Momo):** Bravoh proxy `/api/vibemix/v1/register` (was 404)
**or** a wizard BYO-key step. The wizard-step UI + keyring store is *claude-now* once
the path is chosen. (Kaan ran the app live this session and hit exactly this wall.)

### B3 — `entitlements.macos.plist` breaks codesign (AMFI) ✅ RESOLVED (`0af90e90`)
> **FIXED in-repo.** The `codesign --force --deep …` example inside the XML comment was
> rephrased into prose (no literal `--`). `xmllint` + `plutil -lint` now clean, all 5
> entitlements intact, codesign reads the repo file directly (no plutil workaround).

The committed distribution entitlements file's XML *comment block* contains `--`
sequences (`--force --deep`, box-drawing `────`). `--` is illegal inside XML comments;
`plutil` tolerates it but **codesign's AMFI parser rejects it** (`AMFIUnserializeXML:
syntax error near line 24`). The file has *never* been through a real codesign (signing
was always ungated). **Fix:** strip the comment block (or the `--`), keep the 5 keys
(`allow-jit`, `allow-unsigned-executable-memory`, `device.audio-input`,
`device.microphone`, `network.client`). Verify: `codesign … --entitlements <file> -s -
/tmp/x` succeeds. (This session worked around it with a `plutil -convert`-stripped copy.)

### B4 — `sign_macos.sh` Stage-2 leaves adhoc sigs → notarization rejects ✅ RESOLVED (`0af90e90`)
> **FIXED in-repo.** Stage 2 now force-signs EVERY nested Mach-O deepest-first (matches
> `*.so`/`*.dylib` + `-perm +111`, `LC_ALL=C` depth sort, no idempotent-skip). The
> `cargo tauri build` adhoc sigs are replaced with Developer ID + secure timestamp.

Stage 2 signs `find -perm +111` and **skips already-signed files** (`codesign --verify
--strict && continue`). But cargo's bundler **adhoc-signs** nested binaries, so the skip
leaves adhoc sigs (notarization rejects: "not signed with a valid Developer ID"), and
PyInstaller `.so`/`.dylib` lack the `+111` bit so the find misses them entirely. **Fix:**
force-sign EVERY Mach-O (`.so`/`.dylib` + executables), deepest-first, no skip (see §5).
Also Stage-5 hardcodes the ASC API-key auth (`--key/--key-id/--issuer`) — add a
`--keychain-profile` path so the app-specific-password route works.

### B5 — Windows WASAPI + mic 44.1k 🟡 (needs a Windows box) · B6 — on-decks ear-pass 👤 kaan
Audio-rate family (mirror the macOS native-rate fix) needs a Windows machine. The
anti-slop ear-pass (the final release veto) needs Kaan DJing into a *working* build —
blocked on B1.

---

## §5 · HOW TO REPRODUCE A SIGNED+NOTARIZED DMG (the recipe that worked)

```bash
# 0. (one-time) notarytool profile from the app-specific password — already done:
#    xcrun notarytool store-credentials vibemix-notarytool --apple-id "$APPLE_ID" \
#      --password <app-specific-pw> --team-id "$APPLE_TEAM_ID"
# 1. fresh sidecar from current source (applies the livekit patch + AIza scan):
uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec
# 2. build the app + dmg (CI-correct cwd):
cd tauri/src-tauri && cargo tauri build            # → target/release/bundle/macos/vibemix.app (adhoc)
# 3. comment-free entitlements (works around B3):
plutil -convert xml1 -o /tmp/ent.plist tauri/src-tauri/entitlements.macos.plist
# 4. force-sign EVERY Mach-O deepest-first (works around B4), then the bundle:
ID="Developer ID Application: Francesco Fasanella (UK7DYFK6F8)"
APP=tauri/src-tauri/target/release/bundle/macos/vibemix.app
find "$APP" -type f \( -name '*.so' -o -name '*.dylib' -o -perm +111 \) \
  | LC_ALL=C awk -F/ '{print NF"\t"$0}' | LC_ALL=C sort -rn | cut -f2- \
  | while IFS= read -r f; do codesign --force --options runtime --entitlements /tmp/ent.plist --timestamp --sign "$ID" "$f"; done
codesign --force --options runtime --entitlements /tmp/ent.plist --timestamp --sign "$ID" "$APP"
codesign --verify --deep --strict "$APP"
# 5. dmg + sign it:
create-dmg --volname vibemix --app-drop-link 425 200 dist/vibemix-0.0.1.dmg "$APP"
codesign --force --timestamp --sign "$ID" dist/vibemix-0.0.1.dmg
# 6. notarize + staple + gate:
xcrun notarytool submit dist/vibemix-0.0.1.dmg --keychain-profile vibemix-notarytool --wait
xcrun stapler staple dist/vibemix-0.0.1.dmg && spctl -a -vvv -t install dist/vibemix-0.0.1.dmg
```
⚠ **Do NOT re-sign a .app while an instance of it is running** — it invalidates the
live process (this session broke Kaan's running app that way).

---

## §6 · NEXT MOVES (ranked)

1. **🤖 Fix B1** (the frozen livekit import) — the single wall to a *working* shipped
   dmg. Fast build+boot loop, no signing. Then re-run §5 to ship a bootable signed dmg.
2. **🤖 Land B3 + B4 into the repo** (`entitlements.macos.plist` + `sign_macos.sh`) so
   the real `release.yml` pipeline works — currently it would fail on both.
3. **👤 Kaan/Momo: decide B2** (proxy vs wizard BYO-key); then 🤖 wire the wizard step.
4. **👤 Kaan: ear-pass** once B1 lands and a working dmg installs.
5. **🤖 B5** (Windows) when a Windows box is available.

**The honesty rule still governs:** the signed dmg is real, but it is NOT a working
product until B1 is fixed. Don't present it as shippable until the sidecar boots.
