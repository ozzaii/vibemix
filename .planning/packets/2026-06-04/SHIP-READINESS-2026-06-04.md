# SHIP READINESS — 2026-06-04

Synthesis of five verified ship dimensions (integration-head, build/packaging, live-keystone, democratization, see-it-now). Tier language: SRC = current source, PKG = packaged/distributable artifact, LIVE = proven on a real rig in front of a human. The tree moved during every audit (HEAD walked `8e2a2eb4` → `91b3f002` → `ec57bd5a`, and is `b6217dde` as this is written); pin a SHA before acting on any number here.

## Are we ready to ship? (blunt)

No. The engine and the feature set are strong at SRC, but no artifact a stranger can install reflects today's work, the source those artifacts would rebuild from is RED on two gates, and no human has ever heard the co-host speak a grounded line over a real set. Every signed DMG on disk is built from this morning and is now ~104-105 commits stale, so it predates the entire coach-identity, grounded-receipt-fallback, auto-crate, and Learn-recovery body. The current source carries a committed RED anti-slop test suite (5 agent persona/grounding tests plus the `auto_crate` stop-reason whitelist gate) and a RED `tsc --noEmit` frontend gate. The proxy register→JWT→Gemini chain is wired end-to-end and live, but the Bravoh-side key is out of credits (429), so a keyless stranger gets nothing. The one keystone that validates the whole product at once (grounded line spoken over real audio) is uncrossed: the closest captured run heard real music at BlackHole 2ch, stayed grounded, and never spoke, because it ran voice-disabled from dev-source.

Readiness line: engine + features strong at SRC (~80%); PKG is structurally complete but every distributable is unsigned-or-stale and macOS-Intel + Windows are PKG=0; LIVE voice is 0%. NOT shippable until (1) the two RED gates go green, (2) sidecar+DMG rebuild+sign at HEAD, and (3) the keystone is crossed with proxy billing topped up.

## Where we are

| Dimension | SRC | PKG | LIVE | The one blocker |
|---|---|---|---|---|
| Integration (parallel-session work) | RED | n/a | n/a | 5 agent persona/grounding tests + `auto_crate` stop-reason gate committed RED; load-bearing anti-slop IP was rewritten and its guard tests left failing |
| Build / packaging | green (gates wired+honest) | STALE / unsigned | n/a | Canonical DMG unsigned; signed DMG 158-commits-stale; macOS-Intel + Windows never built |
| Live keystone | green (engine+grounding) | MOSS bundled+ready | UNPROVEN | No captured run has nonzero `voice_rms` or any `transcript_delta` over real audio; co-host has never spoken |
| Democratization | green for 3 of 6 power features | MOSS bundled, CUE/Chatterbox not | brain DEAD for keyless stranger | No in-GUI Gemini-key field or proxy toggle; proxy key at 429 (out of credits) |
| See-it-now (run HEAD today) | RUNS from dev-source | both packaged artifacts stale | demo-able, not stranger-proven | DMG/.app are ~104 commits behind; only dev-source reflects HEAD; `tsc` build gate RED |

## What's left to ship (ordered critical path)

1. **KEYSTONE — capture one clean voice-ON set at HEAD.** [engineering, config-not-build] Launch dev-source with `VIBEMIX_LOCAL_TTS=1`, a working Gemini brain (BYO key or proxy with credits), DJ app routed into BlackHole 2ch only, set driven past the speak-gate. Prove sustained nonzero `music_rms` AND nonzero `voice_rms` AND a `transcript_delta` whose citation resolves in EvidenceRegistry. MOSS is bundled and `local_tts_enabled()` returns True on this rig, so this is launch-config and wiring, not a build. This single artifact flips the LIVE keystone and validates voice + grounding + Invariant #3 at once. It must be first because every other lane's proof collapses into it, and no read-only audit can produce it.

2. **Resolve the 5 agent-lane RED tests.** [engineering] `test_persona_02/03`, `test_intermediate_hype_cell_is_v4_grounded`, and two `test_dj_cohost.py` `P1_span` deck-audio-map cases all fail on committed HEAD because the Sven coach-identity swap (`bb708077`, `HYPE_INTERMEDIATE = SVEN_COACH_IDENTITY` at `matrix.py:432`) rewrote the anti-slop persona/grounding contract and left the guard tests pinned to the old format. Re-pin the tests to the new Sven coach IP or revert the swap. This is Invariant #2 territory; nobody can certify the anti-slop gate while it is RED, and CI will block on it.

3. **Whitelist `auto_crate` in `STOP_REASON_WHITELIST` + fix the `tsc` build gate.** [engineering] `tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined_to_toolset` is RED because committed `auto_crate.py` writes a `stop_reason` not in the whitelist (one-line add plus a docstring naming the authorizing plan). Separately, `npm run build` (`tsc --noEmit && vite build`) fails on `tests/mascot/browser-organism-probe.pw.ts` (missing `@types/pngjs` + 3 possibly-undefined errors); `vite build` alone is clean so the app runs, but the documented gate is RED. Both are mechanical.

4. **Commit the dirty `src/vibemix/` work, then rebuild sidecar AND DMG at HEAD, then re-sign+notarize.** [engineering + external clock] A dirty tree trips the sidecar freshness gate's `source_dirty` check on top of stale-IPC, so commit first. Rebuild the sidecar (`scripts/build_sidecar.py`), then separately rebuild the DMG (a sidecar rebuild does NOT refresh the DMG — same family as the 165-commit-stale trap). Re-run `scripts/dist/sign_macos.sh`; signing infra is proven locally (Developer ID Francesco Fasanella UK7DYFK6F8, notarytool works). A tagged full release is additionally blocked on the SignPath OSS approval (external), but a macOS-arm64 rc path exists via `VIBEMIX_PRETAG_MAC_ONLY=1`.

5. **Top up Gemini billing on the Bravoh proxy key.** [external / Kaan-Bravoh-ops] The register→JWT→Gemini chain is live (`POST /api/vibemix/v1/register` → 200 + valid JWT), but `generateContent` returns 429 RESOURCE_EXHAUSTED ("prepayment credits depleted"). This is the only thing between the already-wired keyless chain and a no-key stranger hearing the co-host. Cheapest external unblock on the board.

6. **Build macOS-Intel and Windows packages.** [engineering + external] Every signed artifact on disk is arm64-only; the updater manifest gate requires `darwin-x86_64` and `windows-x86_64` too. Windows is SRC+CI real, PKG=0/LIVE=0 (binaries dir holds only a 76-byte `.placeholder`); it needs a Windows runner plus SignPath. Honest effort: a real second-platform body of work, not a flag flip.

7. **Clean stray secret-adjacent root files.** [engineering, fast] `codesign0/1/2` at repo root are real exported Apple Developer ID certificates (`file` = `Certificate, Version=3`); plus a `.planning_ls_scratch.txt` noise file. Confirm they are gitignored before any `git add` near root; never commit them.

## SEE IT NOW — latest + greatest

Do NOT open the .dmg or /Applications/vibemix.app — both are built from this morning (DMG 09:59, app 09:02) and are ~104 commits behind HEAD (14:57+). Only dev-source reflects current source plus uncommitted edits. The `VIBEMIX_DEV_PYTHON` pin bypasses `uv run`'s ai-local prune, which would otherwise silently drop CLAP/CUE/local-TTS.

```bash
# from repo root, one instance only (socket 127.0.0.1:8765)
pkill -f "python -m vibemix" 2>/dev/null

# frontend bundle is fresh (built 14:27); rebuild only if you edited tauri/ui/src
# ( cd tauri/ui && npm run build )   # NOTE: tsc gate is currently RED on a test file; vite build alone is clean

VIBEMIX_DEV_SIDECAR=1 \
VIBEMIX_DEV_PYTHON="$(pwd)/.venv/bin/python3" \
VIBEMIX_LOCAL_TTS=1 \
VIBEMIX_DROP_DEBUG=1 \
"/Applications/vibemix.app/Contents/MacOS/vibemix"   # Tauri shell spawns the HEAD sidecar via the dev flags above
```

Preconditions confirmed ready on this rig: `GEMINI_API_KEY` present and non-empty in `.env`; port 8765 free; MOSS cache present (`local_tts_enabled()` returns True); CLAP search path keyless. To actually hear a grounded reaction you still need a DJ app routed into BlackHole 2ch only (no Multi-Output also feeding it) and a set driven past the speak-gate.

Still dark even on HEAD:
- The keystone itself: a stranger has never heard a grounded line over a real set, and no captured run has voice ON.
- Co-host voice over real audio is unproven; the only captured runs ran voice-disabled (dev-source, `VIBEMIX_LOCAL_TTS=0`).
- Chatterbox-Turbo clone: `mlx_audio` is not in the venv and not a `pyproject.toml` extra, so `chatterbox_available()` is False and you hear MOSS, not the clone.
- Organism expressive layer is SRC-wired as of `9dfef795` (14:23) but never compiled on a real WebView (LIVE-unproven).
- Sven friend-score ≥2 is aspiration; no committed full-generation live-persona run benches the new cue-lookahead scenarios.
- Learn 28-lesson reach + auto-advance are SRC-green; the only by-bus proof predates today's playable-decks commits.
- Mid-session synth failure has no MOSS floor; never-mute is proven for selection, not for a synth failure mid-set.
- Two packaged artifacts (DMG, .app) show yesterday-morning's product.

## Democratization polish (ship-blocking subset)

Ranked — the changes that make the power features stranger-usable. Note Viber's "build a set" path is already democratic; the assessment that called all of Viber dev-gated is stale.

1. **In-GUI Gemini-key field + proxy-mode toggle.** [ship-blocking] The no-key failure IS surfaced (exit-4 → `sidecar.rs:575` crash banner → `crash-banner.ts:49` `api-key-missing` with remediation), but the only fix it offers is hand-editing `~/Library/Application Support/vibemix/.env`. There is no in-GUI key input and no proxy toggle anywhere in `tauri/ui/src/` (grep finds only display strings). Without one of these, the visible error is terminal for a non-dev.
2. **Top up the proxy key + flip packaged default to proxy.** [ship-blocking, Kaan] The keyless brain path exists and is live; it just needs credits (429) and the `__main__.py:1108-1111` KAAN-ACTION default flip. This is the only way a stranger gets a brain without a personal key.
3. **Surface CLAP model install in the wizard.** [polish] One-click `vmx-lib-install-models` → keyless checksummed HF download exists, but the wizard never mentions it; discoverability gap, not a wall.
4. **Wire `export-set --allow-unvalidated` into the GUI export path.** [follow-up, not blocking] The permissive flag is CLI-only; GUI export goes through stricter `library_build_set`/`library_cue_folder`. A stranger who builds a set with new local files hits the default stricter behavior. Additive.
5. **BlackHole install assist.** [setup wall] Wizard detects but does not install; it only deep-links to existential.audio. No code removes this step, and master capture `[FATAL]`s without it (`__main__.py:1483`). Hardest non-dev step; clearer in-wizard guidance is the realistic polish.
6. **curate/chat stay Codex-gated.** [opt-in power feature, not blocking] These two Viber sub-surfaces need `codex login` + `VIBEMIX_CODEX_ALLOW_SHELL=1`; ship them as power-user opt-ins. The deterministic keyless `auto_crate` build-set path covers the democratic case.

## Integration health

Not fragmented in the commit graph, but RED on the shared tree and actively churning. The commit history is clean: 173 commits today, zero merges, single-parent linear, branch tip == HEAD; the one orphan (`5eea9a8e`) is unreachable from HEAD with no content lost. So this is NOT an orphaned-branch problem. The fragmentation is entirely in the source-vs-(tests/artifacts) gap: a lane rewrote the load-bearing anti-slop persona/grounding IP and left its guard tests RED (5 agent tests), the committed `auto_crate` breaks its own repo whitelist gate, and the documented `tsc` frontend gate fails on a committed test file. The tree was being written by 2+ concurrent sessions during the audit (HEAD moved 3 times mid-read; `learn/runtime.py` and other edits appeared and were committed by a sibling under the auditors). Any "HEAD is X / N failures" snapshot has roughly a 10-minute half-life. The earlier worries that `auto_crate.py` was untracked and that the `dj_cohost.py` WIP was orphaned are both STALE: `auto_crate.py` is committed (`bde5df09` + follow-ups) and the grounded-receipt-fallback `dj_cohost.py` work landed cleanly (`ec57bd5a`). Net: no green-because-not-run can be distinguished from green-because-correct on Invariant #2 territory until the RED gates are resolved.

## Owner-gates (Kaan's calls)

- **Gemini key / proxy credits.** Top up the Bravoh-side key (429 RESOURCE_EXHAUSTED) and decide whether to flip the packaged default from `direct` to `proxy`. The register→JWT chain is already live; this is the cheapest unblock to let a keyless stranger hear the co-host.
- **Keystone capture sign-off.** Approve and (with hardware) perform the one driven-set capture with voice ON over real BlackHole 2ch audio. No read-only lane can produce this; it is the hard release gate.
- **Viber democratization path.** Confirm shipping the deterministic keyless `auto_crate` build-set as the democratic path while keeping `curate`/`chat` as Codex-gated opt-in power features.
- **mlx-audio dependency.** Decide whether to add `mlx_audio` as a `pyproject.toml` extra so Chatterbox-Turbo voice clone is reachable; today there is no install path for a stranger to enable it at all (default-OFF is correct, but it is permanently dark without this call).
- **Windows scope for v1.** Windows is SRC+CI real but PKG=0/LIVE=0 and needs a runner + SignPath. Decide whether v1 ships macOS-only (arm64 + Intel) or holds for Windows. macOS-Intel is also PKG=0 today and is a real second-platform gap even if Windows is deferred.
- **Free-vs-Pro tier shape.** Confirm the tier boundaries (Free / €4.99 Pro / €9.99 Studio per prior decision) so packaging and the proxy rate-cap tiers match the launch story.
