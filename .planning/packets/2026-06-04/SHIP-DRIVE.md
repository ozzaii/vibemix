# SHIP-DRIVE — the self-driving ship loop (2026-06-04)

The plan Kaan set: delegate the finish, Claude hands off, Kaan compacts, the lanes finish, a monitor trips when everything has landed, Claude says "all landed" and fires the ship workflow, and the ship workflow's results route to 2 Codex for the final push. This file is the durable spine so the loop survives a compaction.

## The 5 sessions (disjoint islands — do not cross)

| Session | Island | State |
|---|---|---|
| cclaude (Claude) | `tauri/ui/**` + IPC schema + `ui_bus` + `check_ipc_schema.py` | Frontend/organism; settings purge + organism + tsc-fix landed; knob + typeset in flight |
| Codex-1 | `src/vibemix/library/**` + `intel/**` | Library/cue; cue-landing engine LANDED + PROVEN |
| Codex-2 | `src/vibemix/learn/**` (+ `audio/miniplayer.py`) | Learn; cue-grade + Course-1 by-bus proven |
| Codex-3 | `src/vibemix/agent/dj_cohost.py` + `prompts/**` + `state/coach.py` + `scripts/eval/respan_*` | Sven; strict Respan gate in flight |
| Claude (organizer) | read-only: packets, scan, last-checks | this session — drives the loop below |

**Unowned, ship-critical → goes to the next free Codex (keystone+packaging goal in this file).**

**Hot file:** `src/vibemix/learn/runtime.py` — organism `teaching_focus` emit (cclaude) AND learn cue-grade (Codex-2) both touch it. Single owner = Codex-2; Frontend requests learn IPC, never edits runtime.py.

## "ALL LANDED" = the monitor trip condition

A background monitor (armed 2026-06-04) polls every 2 min and fires ONE notification when:
- the product tree is clean (`git status --porcelain src/vibemix tauri/ui/src` empty), AND
- no new commit for >=10 min (lanes quiesced).

When that notification arrives, the organizer Claude:
1. Says "all landed."
2. Fires the ship workflow: `Workflow({scriptPath: ".planning/packets/2026-06-04/ship-final-wf.js"})`.
3. Reads its `SHIP-FINAL-VERDICT.md` output. If the DoD is met → declare ship-ready + the residual external steps (sign/notarize, keystone capture). If NOT met → route the named fixes to 2 Codex (goals the workflow prints) and re-arm the monitor.

If the monitor trips early (a lane just paused) and the ship workflow finds RED gates, that is self-correcting: hand the RED fix to the owning Codex, re-arm.

## The two open RED gates (must be green before ship)

1. **auto_crate stop-reason whitelist** (`test_no_seen_relaxation`) → Codex-1's island (`library/auto_crate.py` + the toolset whitelist). Whitelist the writer or revert.
2. **5 RED agent persona/grounding tests** → Codex-3 (Sven). The Respan 9/9 number is NOT the same as these unit tests; they must go green at HEAD. (tsc gate already fixed in `6538cf51`.)

## Unowned ship-critical goal — Keystone + Packaging (paste to the next free Codex)

```
/goal SHIP-FINISH — Keystone + Packaging (ship #1 LIVE gate, currently unowned).
(1) KEYSTONE: make the audio route-doctor deterministic — resolve the BlackHole 2ch-vs-16ch
flip, make auto_master_recommendation stable across repeated runs, doctor names ONE master
device (so the live capture cannot land on a coin-flip). The live capture itself is Kaan's hand.
(2) PACKAGING: with SRC green at HEAD, rebuild the sidecar AND the DMG at HEAD (shipped DMG is
~158 commits stale), run the release gates (MOSS bundle / learn wavs / Developer-ID sign /
notarize+staple / updater + freshness manifest), report which gates pass vs wait on the external
SignPath/Apple clock, confirm the sidecar boots clean.
ISLAND: src/vibemix/audio/**, src/vibemix/platform/_audio_*.py, scripts/** (release/build),
the PyInstaller specs. NOT tauri/ui, NOT the IPC schema, NOT library/learn/agent/prompts.
PROOF: doctor names a deterministic device across 3 repeated runs; a fresh HEAD sidecar+DMG with
an honest gate report; boot-clean check.
SHARED LAW — one shared tree; git add <exact paths> NEVER -A; verify git diff --cached; IPC =
Frontend-only; sidecar 127.0.0.1:8765 one socket (pkill before any probe); commit -s, Kaan Özkan
<rahipdotaci@gmail.com>; commit each piece the moment it is green+proven.
```

## Ship definition-of-done (the ship workflow scores this)

1. **SRC** — full pytest green at HEAD; `npm run build && npm test` green; both RED gates cleared; IPC codegen current.
2. **PKG** — fresh sidecar + DMG at HEAD (not the stale one), all release gates pass, Developer-ID signed + notarized + stapled, sidecar boots clean.
3. **LIVE / keystone** — one captured real set: nonzero music_rms + voice_rms + a grounded co-host line whose citation resolves. (Kaan's hand; doctor must name a deterministic device first.)
4. **Democratization** — a fresh non-dev reaches the brain (in-GUI key field / hosted proxy), models auto-fetch, wizard routes audio.
5. **No ship-critical dark gold left** (latest scan clean) + honesty/grounding intact (provenance, no slop).

When 1-5 hold: ship.
