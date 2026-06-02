# CODEX Verification — Co-host Grounding / TTS-tag cleanup

- **Date:** 2026-06-01
- **HEAD pinned this pass:** `c88d5f566ee0658c88f9e3fdc4229851fec6ed41` (`c88d5f56` — `fix(cohost): stop prompting moss voice tags`, the tip of the 3 verified commits)
- **Branch:** `live-tuning-or-brain`
- **Method:** read-only workflow `wf_458c5dcb-2ad` (`_verify-cohost-tts-grounding.workflow.js`) — 15 agents: 6 evidence × 1 adversarial skeptic each (pipelined) + 2 dedicated bypass-hunters + 1 package board. Every claim carries a `file:line` anchor, a test result, or an explicit NOT-FOUND. Commit reads via immutable `git show <sha>`; current-source reads against the working tree with per-file `git status --porcelain` cleanliness.
- **No product code was edited, staged, or committed.** The app was never launched. Only `.planning/packets/2026-06-01/` docs were written.
- **Raw evidence:** [`_verify-cohost-tts-grounding-raw-wf_458c5dcb.json`](_verify-cohost-tts-grounding-raw-wf_458c5dcb.json) (83KB, persisted from `/private/tmp` immediately).
- **Tree is MOVING:** a concurrent Codex/Claude session edits the working tree. All co-host *speech-surface* files verified here are CLEAN (== committed at `c88d5f56`); `src/vibemix/runtime/coach.py` and `src/vibemix/__main__.py` are DIRTY (the un-landed DROP-call lane — see the board doc). Env note: the repo `.venv` (Python 3.12) is required to run the suite; the machine default `python3` is 3.14 and cannot collect (no `livekit`).

---

## Verdict table

| # | Item | Verdict | Skeptic | Tests |
|---|------|---------|---------|-------|
| 1 | `de9a55f5` block no-move coaching advice | **ACCEPTED** | upheld · high | 237 passed |
| 2 | `a9cb2193` strip internal voice tags from speech | **ACCEPTED** | upheld · high | 95 passed |
| 3 | `c88d5f56` stop prompting moss voice tags | **ACCEPTED** | upheld · high | 153 passed |
| 4 | Contract — no legacy Gemini TTS tags `[chill]/[excited]/[fast]/[whisper]` in live prompt | **ABSENT (clean)** | upheld · high | 6 named passed |
| 5 | Contract — audio-vibe / grounding contract still exists | **PRESENT (intact)** | upheld · high | 109 passed |
| 6 | Contract — no psytrance/Hard-Tek persona hardcode in default prompts | **ABSENT (clean)** | upheld · high | source+trace |
| H1 | Hunt — sanitizer bypass / raw `full_text` → TTS or transcript | **NO BYPASS** | — | 95 passed |
| H2 | Hunt — raw-vs-clean split + English-only | **raw/clean OK · ⚠️ English-only UNENFORCED** | — | source+trace |

**Bottom line: all 3 commits are sound at the source+test level, and the three named anti-slop contracts hold. The one real gap is a missing runtime backstop for the English-only rule (H2). No raw model text reaches a spoken or user-visible surface.**

---

## Per-item evidence

### 1. `de9a55f5` — block no-move coaching advice → ACCEPTED
The co-host no longer prescribes a fix ("try the 1 next time") when there is no real move evidence. Defense in depth:
- **Result-boundary guard** — `apply_live_claim_guard` at `src/vibemix/state/deck_context.py:2356-2364`: when `recent_moves` is empty AND the text trips the detector, the advice is replaced by `LIVE_COACHING_ADVICE_HELD_REPLY` with `policy='coaching_advice_not_grounded'`, `reason='advice_without_recent_move_proof'`.
- **Detector** — `_NO_MOVE_COACHING_ADVICE_RE` (`deck_context.py` ~`192-206` committed / `2613-2620` working tree) matches coaching prescriptions ("try…next time", "wait N bars", "tighten/ride/cut cleaner/kill…next time", "release on the 1"), unless an audio-source/move-effect disclaimer boundary is present.
- **Streaming defer** — `src/vibemix/agent/dj_cohost.py:2733-2739`: `advice_risky = not live_claim_moves and has_unsupported_no_move_coaching_advice(full_text)` → `continue`, so no-move advice never streams to TTS; the held output is re-decided post-stream by the guard.
- **PHASE no longer grants license** — `should_defer_live_claim_stream` returns True for `not moves and event_type=='PHASE'` (`deck_context.py:2298-2299`): a valid PHASE citation does not authorize coaching without move proof.
- **Prompt reinforcement** — `matrix.py:324` (recent_moves NONE rule: "do not give 'try next time' coaching advice or timing prescriptions"); `coach.py:763-768/825-828` (PHASE/HEARTBEAT fragments).
- **Tests:** `tests/state/test_deck_context.py` (strip-no-move-advice + a false-positive guard on pure-audio description "crawl under the pads"), `tests/agent/test_dj_cohost_linter.py:239-281` (full agent, valid `[ev:PHASE@22.4]` + `recent_moves=[]` → `chunks==[]`, nothing spoken, `playback.push` not called), `tests/prompts/test_matrix.py:242-270`. **237 passed.**
- **Skeptic (upheld, high):** confirmed ancestry (`de9a55f5` is an ancestor of `c88d5f56`), all 8 files CLEAN, re-read every anchor in the working tree. Minor phrasing note: the guard *replaces* the whole text with the held reply (it does not surgically excise "try the 1").
- **Bonus discovery (folded into this commit, beyond the headline):** `matrix.py` also **removed the Hard-Tek/Acidcore taste hard-coding** and rewrote `_PSY_TRIPPER_TR_OVERLAY` from Turkish to English — relevant to contract #6.
- **Caveats:** the detector is a **regex heuristic**, not semantic — novel phrasings could dodge it (the streaming-defer + post-stream guard reduce but don't eliminate this). Live-ear muting in real audio is unobservable under the read-only contract (Kaan-action).

### 2. `a9cb2193` — strip internal voice tags from speech → ACCEPTED
- `emote_parser.strip_emote_tags` now also strips the **six legacy voice tags** via a narrow exact-word regex: `VOICE_TAGS = {whisper, laugh, fast, slow, excited, chill}`, `_VOICE_TAG_RE` (`src/vibemix/agent/emote_parser.py`).
- **Citations preserved:** the strip regex matches only those exact words; citation atoms (`[aud:…]`, `[ev:…]`, `[src:…]`, etc.) are left untouched.
- **Tests:** `tests/agent/test_emote_parser.py` + `test_dj_cohost.py` (`test_llm_node_strips_legacy_voice_tags_from_speech_and_ai_message`, ~`348-374`) + `test_dj_cohost_streaming_pipe.py`. **95 passed.**
- **Skeptic (upheld, high):** verified the frozenset + regex via `git show`, all 4 files CLEAN. Caveat: the strip set is intentionally narrow (6 words) — not a general "preserve anything with a colon" guard, but emote/voice regexes are structurally separate from citation atoms.

### 3. `c88d5f56` — stop prompting moss voice tags → ACCEPTED (== HEAD)
- Both `_resolve_prompt_cell` call sites now pass `include_tag_dsl=False` (`src/vibemix/agent/dj_cohost.py:982, 995`), so the assembled system instruction no longer tells the model to wrap speech in voice/emote tags. The audio-vibe contract and coach closing are retained.
- **Tests:** `tests/agent/test_dj_cohost.py` + `tests/prompts/test_matrix.py` (tag-free prompt assertions). **153 passed.**
- **Skeptic (upheld, high):** grepped all 4 `build_system_instruction` callers — both `_resolve_prompt_cell` branches, `persona.py`, `learn/prompts.py` — none re-enable the DSL on the live path.

### 4. Contract — no legacy Gemini TTS tags in the live prompt → ABSENT (clean)
- `build_system_instruction` **defaults** `include_tag_dsl=True` (`matrix.py:837`), so the contract hinges on every live call site passing False — and **all four do**: `dj_cohost.py:982` and `:995` (both `_resolve_prompt_cell` branches), `persona.py:37`, `learn/prompts.py:184`.
- Every occurrence of `[chill]/[excited]/[fast]/[whisper]` in the prompt path is a **comment**, the **`TTS_TAGS` reference tuple**, or one of the **two DSL blocks gated behind `include_tag_dsl=True`** (off on the live path). None enter the outgoing prompt (the same `prompt_body` feeds the LiveKit `instructions`, the `google.genai` `system_instruction`, and the OpenRouter system message).
- **Skeptic (upheld, high):** attacked the default-leak angle and the 4 call sites; could not find a live builder that re-enables the DSL.

### 5. Contract — audio-vibe / grounding contract still exists → PRESENT (intact)
- HEAD **decoupled** the `AUDIO_VIBE_CONTRACT_BLOCK` from the obsolete TTS tag DSL (the gate changed to `include_audio_vibe_contract`) and the live path re-asserts it: `dj_cohost.py:983, 996` pass `include_audio_vibe_contract=True` alongside `include_tag_dsl=False`.
- Citation grammar (`[aud:rms@…]`), the `hearing[rms…bpm]` audio injection, the evidence registry, and the citation linter are untouched. Runtime check produced `AUDIO_VIBE_CONTRACT=True, CITATION_GRAMMAR=True, [aud:rms@45.2]=True, COACH_CLOSING=True, TTS_TAG_DSL suppressed=True`.
- **Tests:** `tests/prompts/test_matrix.py` + `tests/agent/test_coach_prompt_grounding.py` — **109 passed.**
- **Skeptic (upheld, high):** confirmed no commit deleted grounding scaffolding; the gate rename is the only structural change.

### 6. Contract — no psytrance/Hard-Tek persona hardcode in default prompts → ABSENT (clean)
- The default HYPE/COACH personas are **genre-agnostic and explicitly forbid assuming a genre** (`matrix.py:355/447/591`). Genre enters the prompt **only as gated live-detected evidence**: `coach.py:500-501` injects `genre=<detected>` only when `detected_genre != "unknown"` and `genre_confidence >= 0.5`.
- Genre-named literals in `state/genre/profiles/*.json` and `intel/musical_ontology.py` are **detector/profile infrastructure** (explicitly allowed by the contract).
- **Skeptic (upheld, high) — found one symbol the evidence agent's literal grep missed:** `_PSY_TRIPPER_TR_OVERLAY` at `matrix.py:774` (the name is `PSY_TRIPPER`, not "psytrance", so the regex never caught it). Independent evaluation: the overlay's **actual text is genre-agnostic** and it is **per-session opt-in via `VIBEMIX_PROMPT_OVERLAY`**, never a default → not a hardcode. Verdict unchanged. *(Note: `de9a55f5` had already rewritten this overlay TR→EN and stripped the Hard-Tek taste hardcode — see item 1.)*

---

## Adversarial hunters (Phase 2)

### H1 — sanitizer-bypass → **NO BYPASS FOUND** (clean)
Tried to disprove "every spoken/user-visible co-host output is sanitized." Could not route raw model text to TTS or the transcript:
- **`DJCoHostAgent` is the ONLY `Agent` subclass and the ONLY `llm_node` override** — no RealtimeModel / `tts_node` / `transcription_node` alternate path. TTS text is fed exclusively by what `llm_node` yields.
- **Every model-text yield passes through `strip_emote_tags`:** the two mid-stream yields (`dj_cohost.py:2753, 2774`, `strip_emote_tags(segment, normalize=False)`) and the three post-stream re-yields from `buffered_chunks` (`3052-3054 / 3084-3086 / 3151-3153`). The re-yields are safe because `buffered_chunks` is collapsed to the stripped `spoken_text` whenever `has_emote_tag(full_text)` (`2974-2980`); when no tag, raw == stripped.
- **No split-tag leak:** the mid-stream clip uses `last_balanced_position` (only advances past CLOSED brackets), so a bracketed tag is always whole inside one segment before strip runs.
- **Transcript surface** (`transcript_delta`) is fed only by `_push_transcript(spoken_stripped[:140])` (`3069/3110/3161`); `SessionLoop.append_transcript` has **NO production callers** (codegraph + grep). The cohost-reaction bus (`3275`) sends `text=spoken_text` (stripped).
- **MOSS is the single TTS provider** in both direct and proxy modes; `local_tts`/`proxy_client` add no separate text path.
- **The only `strip`-bypassing spoken paths are FIXED-TEXT `session.say` hooks** — DROP `reaction_line` (`runtime/coach.py:714`) and Mastered-unlock vocal (`runtime/coach.py:201`). These speak hand-authored deterministic English templates (`drop_reaction.REACTION_LINES`, `mastered_vocals.json`), **never model output** → cannot leak internal tags or non-English. **Not a violation.**
- **Judge** `verdict_evidence_line` (`intel/judge_voice.py:63`) is **not spoken directly** — it is routed back into the LLM prompt (`coach.py:831`) and voiced through `llm_node` (sanitized).

### H2 — raw-vs-clean + English-only → raw/clean split CORRECT · ⚠️ **English-only UNENFORCED on the spoken path**
- **Raw-vs-clean is correct:** the raw model response (`full_text`) is logged raw **only to observability** — `record_session_ai_message(response=full_text)` → `events.jsonl` + the `response_path` artifact (`dj_cohost.py:3409`, `ai_observability.py:285-306,411`). The message field there is `text=spoken_text` (clean, `3399`). **No raw field reaches TTS, `transcript_delta`, or `ai_message.message`.**
- **⚠️ THE ONE REAL FINDING — English-only has no runtime backstop.** English is enforced **only as a prompt instruction** (`matrix.py:372/483/526/581/778`, pinned by `test_matrix.py:825/833`). There is **no language-detection filter** on the spoken path; `filter_for_slop` (`negative_dict.py`) is an English AI-slop banlist with **zero general-Turkish coverage** (the only Turkish guard is ~4 canned hype words banned *in-prompt*). Because the persona is explicitly Turkish-flavored (the prompt itself bans `süper/harika/muhteşem/evet` and references `abi/knk/lan/dostum`), **a fluent non-English emission that isn't a canned phrase would pass straight through `strip_emote_tags` + `filter_for_slop` and reach both TTS and the transcript unfiltered.**

---

## Ship blockers & findings (this pass)

| Severity | Finding | Where | Disposition |
|---|---|---|---|
| **MEDIUM** | **English-only unenforced at runtime** — prompt-instruction only, no language filter / backstop on the spoken path. Non-English (esp. Turkish, given the persona) could reach TTS + transcript. | `matrix.py` (instruction) · `negative_dict.py` (English-only filter) · `dj_cohost.py` spoken path | **New work** — add a spoken-path English-only backstop (lightweight language guard or a hold-to-ack on non-Latin/non-English detection). Tie to the "English only" product constraint. |
| **MEDIUM (open Q)** | **Citation atoms reach TTS text verbatim** — `[aud:rms@45.2]`/`[ev:…]` are preserved into `spoken_text` (correct for the visible receipt/chip-strip) but, per both hunters, are passed to MOSS "as literal bracket characters with no human-readable rendering step." Unclear whether MOSS *speaks* the bracket tokens. | `emote_parser.strip_emote_tags` (preserves citations) → TTS | **Verify next:** does the TTS input get a citation-strip the visible transcript doesn't? If MOSS vocalizes `[aud:rms@45.2]`, that's audible slop. Quick live/source check (not a code change yet). |
| LOW | No-move-advice block is a **regex heuristic** — novel coaching phrasings could dodge `_NO_MOVE_COACHING_ADVICE_RE`. | `deck_context.py` | Accept for now (defense-in-depth: streaming-defer + post-stream guard). Expand the pattern if a live slip is observed. |
| INFO | **Live-ear pass unproven** — all verification is source + tests; the app was never launched (read-only contract). | — | Kaan-action: live FLX4/audio ear-pass. |

**There is no CRITICAL ship blocker in this pass.** Notably, the prior `DRIFT-current-head.md` CRITICAL (MOSS-only → fresh-machine boot crash) is **RESOLVED at `c88d5f56`** — see Ground-state notes.

---

## Ground-state notes / corrections (verified at `c88d5f56`)

1. **MOSS boot-crash CRITICAL is RESOLVED.** `7e496239` boots **muted** when the MOSS model is unavailable (no more unwrapped `LocalTTSUnavailable` crash); `07bf2f34` (+ spec edits) put **`sentencepiece` AND `watchfiles` in both PyInstaller specs**. The DRIFT blocker no longer stands at this HEAD.
2. **HOLD-bleed is CLEAN.** The DROP-call speech path is **dirty-only — never committed**. `git show HEAD:src/vibemix/runtime/coach.py` has no DROP block; the voiced text lives in the committed-but-orphaned `runtime/drop_reaction.py`.
3. **The on-by-default DROP aggravator is GONE.** Older docs flagged `setdefault('VIBEMIX_DROP_CALL','1')` at `__main__.py:803` — it no longer exists in committed OR dirty `__main__.py`. The env flag is dormant/opt-in.
4. **Package checker is GREEN at `c88d5f56`.** `scripts/check_dirty_package_plan.py --strict-assignments --summary` exits 0 — the DRIFT RED (4 unassigned library-freshness paths) is resolved.
5. **Two `coach.py` files exist — do not conflate:** `src/vibemix/state/coach.py` (the brain / prompt builder, **CLEAN**) and `src/vibemix/runtime/coach.py` (the reaction loop, **DIRTY** with the DROP block).
6. **Nothing is currently staged** (`git diff --cached --name-only` empty).

## Limits
- Source + unit-test verification only. No packaged-DMG, live-audio, or real-Gemini/MOSS runtime behavior was observed (read-only contract). The English-only finding and the citation-in-TTS open question are the items most worth a live check.
- Pinned to `c88d5f56` on a shared, moving tree — re-pin before reuse.
