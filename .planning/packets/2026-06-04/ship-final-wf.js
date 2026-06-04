export const meta = {
  name: 'ship-final',
  description: 'Final ship verification across the 3 proof tiers (SRC/PKG/LIVE), score the ship DoD, and emit 2 Codex goals for the last push. Fired when the all-landed monitor trips.',
  phases: [
    { title: 'Verify', detail: '4 parallel: python gates, frontend gates, packaging/DMG freshness, keystone+democratization status' },
    { title: 'Synthesis', detail: 'score the ship DoD + write SHIP-FINAL-VERDICT.md + 2 Codex final-push goals' },
  ],
}

const CTX = `vibemix = a commercial AI DJ co-host in the final ship push. Read .planning/packets/2026-06-04/SHIP-DRIVE.md and SHIP-READINESS-2026-06-04.md first (the ship DoD + the 5-session board + the 2 RED gates + the keystone/packaging goal). 3 proof tiers, never conflated: SRC (green tests) != PKG (in the signed DMG at HEAD) != LIVE (a real user runs it + hears a grounded line). "test-passing-but-dark = 0." Read-only verification: code + git + artifacts + committed eval-runs. Do NOT launch the live sidecar (one socket). Be exact: pass/fail with the command output, never a guess.`

phase('Verify')

const checks = await parallel([
  () => agent(
    `Verify the SRC tier — PYTHON. ${CTX}
Run the full Python suite at HEAD and the two RED gates specifically:
- full suite: source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q  (report pass/fail/skip counts; if it is too long, run tests/ excluding -m slow/integration/e2e and say so).
- auto_crate stop-reason gate: pytest tests/repo/test_no_seen_relaxation.py -q (GREEN or RED?).
- the 5 agent persona/grounding tests flagged in SHIP-READINESS (find them: grep the agent/state persona+grounding tests; run them; GREEN or RED?).
- model-literal grep gate + the import/clean-checkout gate if present.
Output "## SRC (Python)": each gate GREEN/RED with the actual counts/first failure line. Verdict: is the Python SRC tier ship-clean?`,
    { label: 'verify:python', phase: 'Verify' }
  ),
  () => agent(
    `Verify the SRC tier — FRONTEND. ${CTX}
In tauri/ui: run npm run build (tsc --noEmit && vite build) and npm test (vitest run). Report pass/fail + counts. Confirm npm run codegen:ipc is a no-op (schema in sync). Note any RED.
Output "## SRC (Frontend)": build GREEN/RED, vitest counts, codegen-current yes/no. Verdict: is the frontend SRC tier ship-clean?`,
    { label: 'verify:frontend', phase: 'Verify' }
  ),
  () => agent(
    `Verify the PKG tier — packaging + DMG freshness. ${CTX}
Check (read-only, do not build): is there a DMG in dist/? its date + which commit it was built from vs HEAD (the stale-DMG trap — SHIP-READINESS said ~158 commits behind). Inspect the PyInstaller specs + the release gate scripts (MOSS bundle gate, learn wavs gate, Developer-ID signing, notarize/staple, updater + source-freshness manifest) — what do they enforce and is the current artifact signed/fresh? Is the sidecar binary current vs source? Windows path state.
Output "## PKG (packaging)": DMG fresh-or-stale (with commit distance), what the gates enforce, the exact remaining steps to a fresh signed+notarized HEAD DMG, and which are external (SignPath/Apple). Verdict: is the PKG tier ship-ready or what's left?`,
    { label: 'verify:packaging', phase: 'Verify' }
  ),
  () => agent(
    `Verify the LIVE tier — keystone + democratization. ${CTX}
Read-only (do NOT launch the sidecar): inspect the committed audio-doctor eval-runs for whether the 2ch-vs-16ch flip is now resolved (auto_master_recommendation deterministic), and whether ANY captured set exists with nonzero music_rms AND voice_rms AND a resolving co-host citation (search .planning/eval-runs for a real driven capture). Check democratization: is there now an in-GUI Gemini-key field + proxy toggle (grep tauri/ui settings), do CLAP/CUE/MOSS models auto-fetch, does the proxy have credits (note if unknown).
Output "## LIVE (keystone + democratization)": keystone CROSSED or NOT (with the artifact or its absence), the deterministic-device status, and the democratization readiness. Verdict: can a fresh stranger run it and hear a grounded line, or what's the exact blocker?`,
    { label: 'verify:live', phase: 'Verify' }
  ),
])

const cPy = checks[0] || '(python verify failed)'
const cFe = checks[1] || '(frontend verify failed)'
const cPkg = checks[2] || '(packaging verify failed)'
const cLive = checks[3] || '(live verify failed)'

phase('Synthesis')

const report = await agent(
  `Write .planning/packets/2026-06-04/SHIP-FINAL-VERDICT.md scoring the vibemix ship definition-of-done from the four verified tiers below. Be blunt and evidence-backed; no hype.

Sections:
1. "## Ship verdict" — SHIP / NOT-YET, one line, with the single gating reason if not.
2. "## DoD scorecard" — a table: dimension (SRC-py, SRC-fe, PKG, LIVE-keystone, democratization, honesty) | PASS/FAIL | the evidence.
3. "## The last push — 2 Codex goals" — TWO paste-ready /goal blocks that close whatever is still FAIL, on disjoint islands. Typically: Codex-A = keystone + packaging (audio doctor determinism + rebuild/sign DMG at HEAD); Codex-B = any RED gate or cleanup still open (auto_crate whitelist / 5 persona tests / democratization key-field). If a dimension is already PASS, say "no goal needed" for it. Each goal names its island + proof + the SHARED LAW (one tree, git add exact paths never -A, IPC Frontend-only, socket 8765 one, commit -s Kaan Özkan <rahipdotaci@gmail.com>).
4. "## External clock (Kaan only)" — what only Kaan/external can do: SignPath/Apple notarization, the live keystone capture on the rig, proxy credits.

Use only evidence from the inputs; no invented numbers. Anti-slop: no em-dashes, active voice, specific. Do NOT commit (the organizer commits after). After writing, return a tight chat-ready summary (~12 lines): the SHIP/NOT-YET verdict, the scorecard one-liners, and the 2 Codex goals' headlines.

--- SRC PYTHON ---
${cPy}
--- SRC FRONTEND ---
${cFe}
--- PKG ---
${cPkg}
--- LIVE ---
${cLive}
---`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return report
