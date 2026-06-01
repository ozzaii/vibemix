I successfully read the packet on the first attempt and have already extracted and submitted the load-bearing claims. Here is a summary of what I delivered.

The packet `/tmp/vibemix-codex-inbox/CODEX_READY-frontend-dead-buttons.md` (91 lines, repo_head `0e7bdc1c`, branch `live-tuning-or-brain`) is a frontend "dead buttons" control-truth-table classifying live session deck + settings drawer controls as WIRED / ECHO / LOCAL / DEAD / DISPLAY-GAP.

I extracted the 12 most load-bearing checkable claims and returned them via StructuredOutput. The selection prioritizes:

**Critical claims** (the conclusions depend on these):
- Row 1 persona mood rocker WIRED — live mutation `runtime/settings.py:538-539` (`music_state.mood = value`)
- Row 2 mode rocker LOCAL — `session_loop.py:338-383` only writes `config_store.extra['session.mode']`; only THREE window commands registered (`main.rs:100/115/116`), cohost intentionally unregistered
- Row 3 H9 retry WIRED — `restart_sidecar` kill-only "Wave 2 stub", respawn is "Wave 4" TODO
- Row 6 see-all-reactions WIRED but unmounted — `renderCohostPanel` appears only in `cohost.ts` + its test, not in any production surface
- Row 8 voice picker ECHO (UNVERIFIED) — `settings.py:327-344` persist-only branch, `cascade_agent.set_voice` unreachable because cascade_agent is None
- Row 9 output device/profile NEEDS RE-CLASSIFY — phantom-tree DEAD verdict must be redone on real tree
- Row 10 deck mute DEAD/RE-VERIFY — IPC checker reports handler at `session_loop.py:261`; sender existence disputed
- Row 11 IPC sanity — 72 declared/72 shell/72 sidecar wired, checker script as reproduction

**Supporting claims:**
- Row 4 citation chip WIRED, Row 5 vibe-engine WIRED, Row 7 status-row recheck WIRED, plus the next-suggestion pill DISPLAY-GAP/ABSENT claim.

Each claim ships with the exact grep/read/command to reproduce at HEAD. The packet's own reproduction commands were preserved where given (e.g. the IPC checker invocation and the per-row greps). No claims were dropped beyond the 12-cap; the remaining DISPLAY-GAP rows (titlebar pills, MUTED pill, drop chip, deck EQ mock) and the Earned Wall seam confirmation are lower-leverage and were noted as deprioritized within the cap.
