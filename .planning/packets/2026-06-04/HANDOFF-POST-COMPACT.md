# HANDOFF — post-compact re-entry (2026-06-04, ingest done)

The organizer (read-only swarm Claude; Codex lanes build) ran the full ship-ingestion, hand-synthesized it, wrote the start-gate fix goal, and de-slopped the README. Kaan compacts now. This is how you re-orient.

## First action on wake
1. **READ `SHIP-INGEST-2026-06-04.md` FIRST** (committed `b078a176`). It is the consolidated post-codexes-done ship state, HEAD-verified, full context. Supersedes SHIP-MAP-MASTER for current state. The 14 raw surface ingests are in `.planning/packets/2026-06-04/ingest/ING-01..14.md`.
2. Then `git log --oneline -8` + `git status --porcelain -- src/vibemix/__main__.py src/vibemix/runtime/session_loop.py` to see if the start-gate seam has been committed since (the #1 blocker below).

## The state in 6 lines
- **3 of 4 locked decisions LANDED + committed:** VOICE (Chatterbox-only, mlx extra, ref bundle, model fetch, env-seed, gate-swap — the maps' "#1 voice blocker" is RESOLVED), BRAIN (proxy-default + set_brain + no-key graceful, no crash), STREAK (correctly deferred).
- **#1 BLOCKER — START-GATE backend is REAL but UNCOMMITTED:** an 803-line dirty diff in `__main__.py` (+738) + `session_loop.py` (+72); `git show HEAD` has 0 start-gate symbols; committed smoke tests assert against it (clean-checkout RED); one sibling `git checkout` from oblivion. HEAD-verified at `23bd6c0e`.
- **NEW severe bug:** the start-gate `main()` refactor returns at `__main__.py:2314` but `LessonRuntime` is built at `:3606` + loops at `:3890/:3891` = dead code → committing as-is darkens Learn live. W12 live credit dark for the same family (`learn_progress=None` at `:2010`).
- **README de-slopped THIS session** (`23bd6c0e`): model names/altidus/MOSS/bravoh.com/ozzaii/Phase-dump all gone, 2 coupled tests re-pinned, 5 matrix-sync tests retired, all 4 README gates green. The ingests' README findings are STALE (they read the pre-fix README).
- **Proxy is live + funded.** GA-tag landmine ARMED (`release.yml` + `companion-sign` fire Windows+Intel on a `v*` tag; `VIBEMIX_PRETAG_MAC_ONLY` does NOT gate the Actions matrix). PKG=0 (all DMGs stale), LIVE=0 (co-host never spoke over real audio).
- **Honest calibration (Kaan challenged "too good to be true"):** the audit verified WIRING, not QUALITY. 6 of 14 agents got the start-gate WRONG; I HEAD-resolved it. The product thesis (real friend, no slop, grounded, on-time) is UNVERIFIED — LIVE=0. The narrator→coach gap (only the EQ-move guard speaks on the master-only rig) is the real product risk a static audit can't fix.

## The single next move
The backend-boot Codex lane runs `CODEX_READY-STARTGATE-COMMIT-LEARN-ORPHAN.md` (committed `b0c0e291`; paste-ready `/goal` block inside): lift LessonRuntime above the `main()` return + wire learn_progress/learn_state into the live path + prune the dead tail + R10 one-kwarg + commit the seam surgically. Proof = clean-checkout green + by-bus, NOT working-tree-green. **Kaan pastes the goal into the loop; the organizer only writes packets.**

## Open decision for Kaan (offered, not yet answered)
Write the **narrator→coach engine goal** next (make transition scorer/judge/move-grade speak on a single master mix, or default per-deck capture on, so the co-host coaches instead of narrating on the bare rig)? Or hold until the start-gate lands + a keystone ear-pass.

## Ownership / law (unchanged)
Claude = read-only swarm (packets/docs only, never product code); Codex lanes build; Kaan pastes goals into loops + owns the keystone/Apple-notarize/secrets/`v*`-tag. `__main__.py`/`config_store.py` = single-owner (backend-boot lane). IPC schema = frontend lane. Commit packets via pathspec (`git add <exact paths>`, verify `git diff --cached --name-only`, never `-A`). One socket `127.0.0.1:8765` (pkill before any probe).

## Kaan-only (no autonomous lane)
GA-tag matrix de-arm + org signing secrets + updater keypair; Apple notarize + licensed-ref placement + DMG sign; the keystone LIVE capture (his ear); the `v0.1.0` tag push; proxy credits top-up; Free/Pro/Studio tier shape.

## Doc index (live 2026-06-04)
- `SHIP-INGEST-2026-06-04.md` — THE consolidated ship state (read first). `ingest/ING-01..14.md` = raw.
- `CODEX_READY-STARTGATE-COMMIT-LEARN-ORPHAN.md` — the #1 next goal (paste-ready).
- `SHIP-NEXT-GOALS-2026-06-04.md` — per-lane goals + resolved decisions (D1 mlx 8bit, D3 macOS-arm64-v1, GA-tag landmine).
- `SHIP-MAP-MASTER.md` — architecture orientation (superseded for ship state).
- README de-slop landed `23bd6c0e`.
