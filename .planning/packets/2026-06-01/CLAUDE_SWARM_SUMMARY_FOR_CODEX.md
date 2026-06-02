# CLAUDE ⇄ CODEX — Swarm Summary & Deep-Context Map  💙

> **Codex: start here.** This is Claude's read-only research/synthesis handoff. Claude does NOT write product code or race you — Claude runs parallel evidence swarms and hands you a ranked, evidence-backed decision engine. Everything below is durable in the repo (`.planning/packets/2026-06-01/`), never `/tmp`.

- **Author:** Claude read-only swarm lane · **Date:** 2026-06-01 · **HEAD when written:** `769e32a3` (`fix(library): reject fixture-backed user cache`)
- **Status:** LIVING hub. Re-read after each pass. The full decision engine (5 reports) is DONE — see §6.
- **Contract held:** zero product-code edits/stages/commits by Claude. Only `.planning/packets/2026-06-01/` docs written.

> **Operating model:** Claude = read-only swarm/research/verification layer. **Codex A/B/C** = implementation lanes (A routes). Claude produces packets; Codex A routes the work — Claude never implements or tells Codex to implement directly. Full contract: [`CLAUDE_CHARTER.md`](CLAUDE_CHARTER.md). **The routing surface Codex A pulls from: [`CLAUDE_LAND_QUEUE.md`](CLAUDE_LAND_QUEUE.md)** (SAFE_NOW / HOLD_WITH_GATE / DROP / RESEARCH_ONLY + the 6 release blockers). Proof is tiered: `SRC` (source+test) ≠ `PKG` (in the signed build) ≠ `LIVE` (real-rig FLX4/Rekordbox) — never conflated.

---

## 1. Where everything is (the digdown map)

**⭐ The two living surfaces (Codex A starts here):**
| Doc | What it gives you |
|---|---|
| [`CLAUDE_LAND_QUEUE.md`](CLAUDE_LAND_QUEUE.md) | **The routing board** — SAFE_NOW (11) · HOLD_WITH_GATE (8) · BLOCKERS (6, release-gating) · DROP/DEFER (7) · RESEARCH_ONLY (6). Each with proof-tier + gate + evidence. Verified HEAD `769e32a3`. |
| [`CLAUDE_CHARTER.md`](CLAUDE_CHARTER.md) | Claude's operating contract — role, evidence rules, the 3 proof tiers, blocker A/B/C/release tagging. |
| [`CODEX_VERIFICATION-769e32a3-library-freshness.md`](CODEX_VERIFICATION-769e32a3-library-freshness.md) | **Latest verifier packet** — `769e32a3`+`32873bcb` library freshness ACCEPTED (SRC) + LIVE cache probe. Spawned S9/S10/S11 + H8 + R6. |

**🟢 Current-HEAD truth — read in this order:**
| Doc | What it gives you | Raw evidence |
|---|---|---|
| [`CLAUDE_META_AUDIT_NEXT_BOARD.md`](CLAUDE_META_AUDIT_NEXT_BOARD.md) | **Ranked board rationale** (8 lenses) — the "why" behind every LAND_QUEUE row | [`_wf-meta-audit-raw-wf_053c9eb3.json`](_wf-meta-audit-raw-wf_053c9eb3.json) |
| [`CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md`](CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md) | **11 keep/drop/change decisions** — LAND/HOLD/DROP/RESEARCH + evidence | [`_wf-open-question-ledger-raw-wf_2b2c30ea.json`](_wf-open-question-ledger-raw-wf_2b2c30ea.json) |
| [`CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md`](CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md) | **The full product map** — 282 capabilities across 12 silos, each classified (PROVEN / SOURCE_ONLY / WIRED_UNPROVEN / CLI_ONLY / ORPHANED / CLAIMED_BUT_ABSENT / HOLD / DROP) with file:line | [`_wf2-inventory-raw-wf_8991ed75.json`](_wf2-inventory-raw-wf_8991ed75.json) (212KB) |
| [`CLAUDE_LAST_DELTA_DRIFT.md`](CLAUDE_LAST_DELTA_DRIFT.md) | **What landed since `c88d5f56` + drift risk** — commit verification, HOLD-bleed sentinel, checker regression | [`_wf1-last-delta-drift-raw-wf_e1200925.json`](_wf1-last-delta-drift-raw-wf_e1200925.json) |
| [`CODEX_VERIFICATION-cohost-grounding-tts-tags.md`](CODEX_VERIFICATION-cohost-grounding-tts-tags.md) | **Deep verify of the 3 grounding/TTS-tag commits** (de9a55f5/a9cb2193/c88d5f56) + sanitizer-bypass hunt | [`_verify-cohost-tts-grounding-raw-wf_458c5dcb.json`](_verify-cohost-tts-grounding-raw-wf_458c5dcb.json) |
| [`NEXT-LAND-BOARD-after-c88d5f56.md`](NEXT-LAND-BOARD-after-c88d5f56.md) | Ranked next-5 board (SAFE_NOW + HOLD) + shared-file risk register | — |
| [`INDEX.md`](INDEX.md) | The master catalog of the whole packet archive | — |

**🟡 Landing the verified packages:** [`CODEX_PACKAGE_SWEEP_STATUS.md`](CODEX_PACKAGE_SWEEP_STATUS.md) (start-here for landing) · [`CODEX_GOLD_STRUCTURE.md`](CODEX_GOLD_STRUCTURE.md) (Gold 0–7 batching) · `.planning/handoffs/2026-05-31-package-checklist.md` (3499L — the package lanes 0–17).

**🔵 Per-package proof packets:** the `CODEX_READY-*.md` / `CODEX_HOLD-*.md` set (50+ files in this dir) — one per package lane, each with its acceptance evidence. Notably the two that closed Claude's prior findings: [`CODEX_READY-cohost-english-only-runtime-guard.md`](CODEX_READY-cohost-english-only-runtime-guard.md) and [`CODEX_READY-cohost-tts-citation-sanitizer.md`](CODEX_READY-cohost-tts-citation-sanitizer.md).

**⚙️ Re-runnable workflow utilities** (Claude's swarm scripts — read-only by contract): `_wf1_last_delta_drift.workflow.js`, `_wf2_capability_inventory.workflow.js`, `_wf3_meta_audit_strategy.workflow.js`, `_wf_drift_refresh.workflow.js`, `_verify-cohost-tts-grounding.workflow.js`, `_drift_verify.workflow.js`.

**🗄️ Raw outputs / transcripts:** final JSON per run is the `_*-raw-wf_*.json` files above (durable). Live agent transcripts (ephemeral, do NOT rely on) live under `~/.claude/projects/-Users-ozai-projects-dj-set-ai/<session>/subagents/workflows/wf_*/`. **Rule: Codex reads only the durable layer-A docs here — never `/tmp`, never transcripts.**

---

## 2. Top verified truths (high confidence, skeptic-upheld)

1. **The 3 grounding/TTS-tag commits are sound** — `de9a55f5` (block no-move coaching advice), `a9cb2193` (strip internal voice tags), `c88d5f56` (stop prompting moss voice tags): all ACCEPTED, 237/95/153 tests green. `CODEX_VERIFICATION-cohost-grounding-tts-tags.md`.
2. **No legacy Gemini TTS tags in the live prompt** — `[chill]/[excited]/[fast]/[whisper]` only exist in comments / the gated `TTS_TAGS` DSL (off on the live path via `include_tag_dsl=False` at `dj_cohost.py:982,995`). ABSENT = clean.
3. **Audio-vibe grounding contract intact** — decoupled from the obsolete tag-DSL, re-asserted on the live path (`include_audio_vibe_contract=True`). Citation grammar + evidence registry + linter untouched. PRESENT.
4. **No psytrance/Hard-Tek persona hardcode** in default prompts — genre enters ONLY as gated live-detected evidence (`coach.py:500-501`, conf ≥ 0.5). `_PSY_TRIPPER_TR_OVERLAY` is opt-in (`VIBEMIX_PROMPT_OVERLAY`), genre-agnostic text.
5. **Sanitizer-bypass = CLEAN** — no raw `full_text` reaches TTS or transcript. Every model-text yield passes `strip_emote_tags`; the only bypass is fixed-text `session.say()` (deterministic English templates, not model output).
6. **English-only is NOW runtime-enforced** — was prompt-only (Claude's MEDIUM finding); Codex landed `b5916eb0` with new `agent/language_guard.py` wired at `dj_cohost.py:2758,3009`. RESOLVED.
7. **Citation atoms are NOW stripped from TTS** — Claude's open question; Codex landed `54ec38be` with new `agent/tts_sanitizer.py`, `model_text_for_tts` at `dj_cohost.py:2638`. Citations stay on the visible receipt, leave the spoken stream. RESOLVED.
8. **Library fixture-reject (`769e32a3`) works AND the bug was real** — Kaan's own `~/.cache/vibemix/library.pkl` literally pointed at `tests/library/fixtures/synthetic_collection.xml` (Viber was answering from 5 fake tracks). HEAD's guard rejects it. **LIVE truth: the co-host does NOT load empty — `try_load_cache()` falls through to `library.pkl.v1bak`, a real 1547-track backup, and loads it.** The `.v1bak` "dormant fallback" is load-bearing on this rig. `CODEX_VERIFICATION-769e32a3-library-freshness.md`.
9. **Folder-backed freshness nudge is honest on the anti-slop axis, wrong on remediation** — a stale folder library is correctly nudged (never falsely "fresh") but told "Drop the Rekordbox XML" with no re-index button → the `folder-reindex-from-nudge` package (H8) closes it. Consent intact (folders never auto-detected).
8. **HOLD-bleed CLEAN** — the DROP-call live hype SPEECH block is DIRTY-ONLY (never committed); `git show HEAD:src/vibemix/runtime/coach.py` has no DROP block. The on-by-default `VIBEMIX_DROP_CALL` aggravator is GONE. `4ac30b5d` explicitly records the hold.
9. **MOSS boot-crash CRITICAL is RESOLVED** — `7e496239` boots muted when the model is absent; `07bf2f34` put `sentencepiece` in both PyInstaller specs. No more fresh-machine crash.
10. **Package checker GREEN** at HEAD (`scripts/check_dirty_package_plan.py --strict-assignments` exit 0; all dirty paths lane-assigned).

---

## 3. The product, classified (from the 282-capability inventory)

| Class | Count | Meaning |
|---|---|---|
| WORKS_AND_PROVEN | 108 | source + passing test/artifact |
| WORKS_SOURCE_ONLY | 106 | correct + unit-tested, no live/packaged proof (app never launched this pass) |
| WIRED_BUT_UNPROVEN | 27 | both ends wired, no proof it fires → **e2e proof candidates** |
| CLAIMED_BUT_ABSENT | 17 | **doc says yes, code says no → honesty gaps to reconcile** |
| CLI_ONLY | 8 | works from CLI, not surfaced in GUI |
| DROP_OR_DELETE | 7 | dead/superseded/placeholder → cleanup candidates |
| PRESENT_ORPHANED | 5 | code exists, no live call-site |
| HOLD | 4 | gated behind review/proof/ear-pass |

Full per-silo breakdown + the exact DROP / CLAIMED_BUT_ABSENT rollups: `CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md` §DROP and §CLAIMED_BUT_ABSENT.

---

## 4. Top next LAND packages (what Codex should do next)

1. **P0 — re-sync stale jsdom fixtures** `tauri/ui/src/library/chat.test.ts` (29 fail) + `curate.test.ts` (5 fail) with `library.html` (add `#vmx-lib-cue-folder` + new ids). This is a STALE-TEST gap, NOT an app gap — `build.test.ts` (20/20) and the real markup have the element. Turns the vitest suite green. _Evidence: inventory app-ui silo._
2. **Confirm/close the `tests/repo` regression** — WF1 flagged `tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined…` RED (HIGH). `d321eef5 test(cohost): close drift guard expectations` may have fixed it — the pending drift-refresh confirms.
3. **`4446f674` FLX4 cc34 binding — supply the missing proof artifact** (HOLD-EVIDENCE): the commit cites a "2026-06-01 FLX4 proof, 134 MIDI frames" that is NOT-FOUND in the tree, and it touches the speech path via `recent_moves` without a grounding-review. Either land the proof artifact or grounding-review the coupling.
4. **Rebuild + re-sign + notarize the DMG from clean HEAD** — every packaged claim is currently unproven (newest DMG predates the MOSS/voice-tag/English-only fixes). Build from a CLEAN tree (the dirty DROP block in `runtime/coach.py` MUST NOT be included).
5. **Reconcile the 17 CLAIMED_BUT_ABSENT** — for each: delete the false claim or build the real thing (honest-product priority).

---

## 5. Top HOLD gates (do NOT land without these)

- **DROP-call live hype speech** → `vibemix-grounding-review` PASS + on-beat live proof + predicted-drop false-positive rate. Dirty-only today; keep it out of any whole-file `git add runtime/coach.py`.
- **BEATMATCH_GRADED Mastered** → needs a real-time owned-deck grading PRODUCER before unmasking stored mastery (consumer/payload exist; producer NOT-FOUND). The honesty boundary must hold.
- **FLX4 live acceptance** → still HOLD (`173399ae`): deck_state unresolved + BlackHole 16ch proved only A_active+B_silent, not both deck lanes. The hold is recorded honestly — do not flip to "accepted."

---

## 6. Claude workflows — all DONE (sequential, one swarm at a time to dodge the rate-limit)

| Workflow | Output doc | Status |
|---|---|---|
| drift-refresh (`f29defb6..173399ae`) | [`CLAUDE_LAST_DELTA_DRIFT.md`](CLAUDE_LAST_DELTA_DRIFT.md) (update appended) | ✅ **DONE** — 6/6 LAND, HOLD-bleed NO, prior `tests/repo` regression RESOLVED by `d321eef5` (with a gate-widening flag) |
| open-question decision ledger (11 questions → LAND/HOLD/DROP/RESEARCH) | [`CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md`](CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md) | ✅ **DONE** — 6 LAND/close-out · 3 HOLD · 2 RESEARCH · 1 DROP |
| meta-audit → ranked board (SAFE_NOW / HOLD_WITH_GATE / DROP / RESEARCH_WITH_WORKFLOW) | [`CLAUDE_META_AUDIT_NEXT_BOARD.md`](CLAUDE_META_AUDIT_NEXT_BOARD.md) | ✅ **DONE** — 8-lens ranked board + coherent-v1 thesis (3 lenses recovered after a rate-limit; see its § Supplemental lenses) |

**The decision engine is complete.** Read order for landing: this summary → `CLAUDE_META_AUDIT_NEXT_BOARD.md` (the ranked board) → `CLAUDE_OPEN_QUESTION_DECISION_LEDGER.md` (per-question decisions) → `CLAUDE_EVERYTHING_CAPABILITY_INVENTORY.md` (full map) → `CLAUDE_LAST_DELTA_DRIFT.md` (current-head safety).

---

## 7. What Claude is uncertain about (verify before trusting)

- **No live ear-pass** — the app was never launched (read-only contract). All "WORKS" is source/test-level. The 106 SOURCE_ONLY + 27 WIRED_UNPROVEN surfaces need a real `drive-vibemix` / live run to promote.
- **The 17 CLAIMED_BUT_ABSENT** — these are Claude's read of "doc claims X, grep didn't find it"; a renamed symbol could be a false-absent. Confirm each before deleting a claim.
- **Deck identity source** — screen-vision vs Rekordbox-live vs MIDI as the authoritative deck_state resolver is unresolved (it's the core of the FLX4 hold). Open question in the pending ledger.
- **English-only guard coverage** — `language_guard.py` is wired + tested at the unit level, but its real-world precision on Turkish-flavored persona output isn't live-verified.

---

### Process rules (so this stays clean)
1. Durable packets → `.planning/packets/2026-06-01/`, in the git tree, **never `/tmp`**.
2. Codex reads layer-A docs here; if a doc is missing it wasn't persisted yet → ask, don't hunt `/tmp`.
3. Claude stages nothing of Codex's; Codex stages nothing Claude is mid-writing. Shared files = hunk-stage only (`git add -p` unavailable → filtered patch + `git apply --cached --recount`).
4. If HEAD moves while you read this, note the stale head — Claude re-pins every pass and records it.

💙 — Claude
