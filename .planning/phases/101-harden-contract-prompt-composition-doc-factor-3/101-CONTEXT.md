# Phase 101: HARDEN-CONTRACT — Prompt Composition Doc (Factor 3) - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Auto-generated (doc-only phase; ROADMAP Phase Details + 7 REQ-IDs are the spec)

<domain>
## Phase Boundary

Land `docs/PROMPT-COMPOSITION.md` as the single named contract enumerating every `EventType` × evidence-fields × citation-sources × recall-fragment shape × diet-mode eligibility × per-event-type cooldown — every cell cross-referenced to live source by `file:line`. A new mood/lens contributor reads ONE doc and knows exactly what enters the live co-host prompt per event type, without reverse-engineering `coach.py` / `evidence_registry.py` / `event_detector.py`.

Scope: ONE new file (`docs/PROMPT-COMPOSITION.md`) + ONE-LINE pointer added to `CLAUDE.md` "Architecture" section. No other code touches. No new tests beyond the write-time `grep` verification that every `file:line` reference resolves on current source. No new deps. No new IPC envelopes. No new ws ports.

Closes Factor-3 partial from today's 2026-05-28 humanlayer/12-factor-agents audit ("own your context window"). Doc itself is scoped to the LIVE CO-HOST prompt composition only — does NOT extend evidence sources, does NOT touch the Viber/library prompt surface (P99/P100 handle Viber-side; the live + Viber surfaces are intentionally documented separately).

Disjointness contract (locked): touches only `docs/` (new file) + `CLAUDE.md` (one line). Never touches `src/vibemix/agent/`, `src/vibemix/__main__.py`, `src/vibemix/intel/`, `tauri/ui/*`, or `src/vibemix/state/` source code (read-only references).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (default-YES under `gsd-autonomous fully`)

All implementation choices are at Claude's discretion — the 7 HARDEN-CONTRACT REQ-IDs in `.planning/REQUIREMENTS.md` are precise enough to constitute the spec. Document structure, cross-reference format, and prose voice are at writer's discretion within the constraints below.

### Locked by REQ-IDs (non-negotiable)

- **HARDEN-CONTRACT-01** — Every `EventType` emitted by `EventDetector._fire(...)` listed with a column showing the evidence fields populated for that event. The 9 event types in current source: `KAAN_SPOKE`, `MANUAL`, `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `KEY_CLASH`, `TRANSITION_OPPORTUNITY`, `HEARTBEAT` (verified by `grep -n "self._fire(" src/vibemix/state/event_detector.py`).
- **HARDEN-CONTRACT-02** — All 11 `EVIDENCE_SOURCES` (`src/vibemix/state/evidence_registry.py:129`) listed with body grammar (`ev:<TYPE>@<t>`, `key:<deck>:<camelot>`, `recall:<record_id>`, `exemplar:<track_id>`, `cue:<anchor_id>`, etc.) and which event types may cite which sources.
- **HARDEN-CONTRACT-03** — Recall-fragment shape per event family (TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL / PHASE) with concrete worked examples, cross-referenced to `src/vibemix/state/coach.py:158 recall_fragment_for_event`.
- **HARDEN-CONTRACT-04** — Diet-mode-eligible events (per `ACK_ELIGIBLE_EVENTS = {"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}` at `src/vibemix/state/coach.py:54` and the `if diet:` branch at `src/vibemix/state/coach.py:824`) called out vs full-prompt events, with the rationale (TTFT budget on ack-eligible events).
- **HARDEN-CONTRACT-05** — Every `file:line` reference resolves on current source. Verification: write-time `grep -n` shell loop against current `src/vibemix/` before committing the doc. CI smoke check is OPTIONAL (per REQ-05 explicit) and not blocking.
- **HARDEN-CONTRACT-06** — `CLAUDE.md` "Architecture" section gains a one-line pointer ("for prompt composition, see `docs/PROMPT-COMPOSITION.md`"). One line, no other CLAUDE.md edits.
- **HARDEN-CONTRACT-07** — Per-event-type cooldowns from `src/vibemix/audio/constants.py:77 MIN_EVENT_GAP_PER_TYPE` cross-referenced. The composite table answers "this event fires at most every Xs, surfaces these evidence fields, may cite these sources, follows this recall shape, eligible-or-not for diet mode" in one place.

### Doc structure (writer's call within the locked spec)

Composite "EventType × everything" table is the load-bearing artifact (satisfies REQs 01/02/04/07 in one cell-grid). Per-event-family sections expand recall-fragment shapes (REQ-03). One short "How to grep-verify this doc" appendix documents the REQ-05 acid test for future doc updates.

Tone is reference-doc neutral (not narrative). Bullet lists + tables, not paragraphs. Code citations are GitHub-style `path:line` (e.g. `src/vibemix/state/coach.py:794`) — clickable in most editors. No code blocks for full function bodies — just the anchor cite. The doc is a CONTRACT, not a tutorial.

</decisions>

<code_context>
## Existing Code Insights

**The contract surface (read-only references for the doc):**

- `src/vibemix/state/event_detector.py` — 9 `self._fire(...)` call sites enumerate the live `EventType` taxonomy. Lines: 239 (`KAAN_SPOKE`), 243 (`MANUAL`), 273 (`TRACK_CHANGE`), 289 (`PHASE`), 312 (`LAYER_ARRIVAL`), 340 (`MIX_MOVE`), 383 (`KEY_CLASH`), 443 (`TRANSITION_OPPORTUNITY`), 464 (extra `_fire` branch), 469 (`HEARTBEAT`). Event types are STRING LITERALS, not an enum.
- `src/vibemix/state/evidence_registry.py:129` — `EVIDENCE_SOURCES: frozenset[str]` defines the 11 locked sources. Adjacent CITATION_RE alternation comments at lines 145, 153, 162 enumerate the body-grammar discipline.
- `src/vibemix/state/coach.py:54` — `ACK_ELIGIBLE_EVENTS` frozenset.
- `src/vibemix/state/coach.py:158` — `recall_fragment_for_event(...)`.
- `src/vibemix/state/coach.py:794` — `build_prompt(...)` — the prompt assembler.
- `src/vibemix/state/coach.py:824` — `if diet:` branch (diet-mode dispatch).
- `src/vibemix/state/coach.py:847` — `recall_frag = recall_fragment_for_event(...)` — the conditional-append site.
- `src/vibemix/audio/constants.py:77` — `MIN_EVENT_GAP_PER_TYPE: dict[str, float]` — per-event-type cooldowns.

**Established patterns (this milestone reuses):**

- `docs/` is the canonical home for contributor-facing contracts (e.g. `docs/clap-engine.md`, `docs/library.md`, `docs/windows-setup.md`). `docs/PROMPT-COMPOSITION.md` slots in alongside.
- The `gsd-autonomous fully` discipline: doc-only phase ships with a single `feat(101)`-style commit touching exactly two files (`docs/PROMPT-COMPOSITION.md` + `CLAUDE.md`).
- Concurrent-sessions discipline (per `feedback_concurrent_sessions_one_tree` memory): commit named paths, never `git add -A`. P99/P100's pattern of one commit per plan applies here too.

**What this phase does NOT touch:**

- No source code in `src/vibemix/state/` (read-only references only — the doc enumerates what's there, never edits it).
- No `src/vibemix/__main__.py` (LiveKit-upgrade handoff owns `:1353` `turn_handling` — disjoint).
- No `src/vibemix/agent/` (live co-host streaming pipeline is structurally NOT a tool-call loop — Factor 10).
- No `tauri/ui/*` (frontend wiring handoff territory).
- No tests beyond the write-time `grep` verification appendix.
- No new evidence sources, no new event types, no new cooldown values — the doc enumerates the SHIPPED surface.

</code_context>

<specifics>
## Specific Ideas

### The composite table (the load-bearing artifact)

| EventType | Fires from | Cooldown (s) | Evidence fields | Citation sources | Recall-fragment family | Diet-mode eligible? |
|-----------|-----------|--------------|-----------------|------------------|------------------------|---------------------|
| `KAAN_SPOKE`            | event_detector.py:239 | (MIC key)              | mic gate | `recall:`           | KAAN_SPOKE recall    | ✓ |
| `MANUAL`                | event_detector.py:243 | (per type)             | manual trigger | (none required)     | (none)               | (per ACK rule) |
| `TRACK_CHANGE`          | event_detector.py:273 | per `MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"]` | audible_track, confidence | `ev:`, `key:`, `recall:` | TRACK_CHANGE recall  | ✗ |
| `PHASE`                 | event_detector.py:289 | per `MIN_EVENT_GAP_PER_TYPE["PHASE"]` | phase, prev phase | `ev:`, `recall:` | PHASE recall         | ✗ |
| `LAYER_ARRIVAL`         | event_detector.py:312 | per `MIN_EVENT_GAP_PER_TYPE["LAYER_ARRIVAL"]` | band signature | `ev:` | LAYER_ARRIVAL recall | ✓ |
| `MIX_MOVE`              | event_detector.py:340 | per `MIN_EVENT_GAP_PER_TYPE["MIX_MOVE"]` | last 3 moves | `ev:` | MIX_MOVE recall      | ✓ |
| `KEY_CLASH`             | event_detector.py:383 | per `MIN_EVENT_GAP_PER_TYPE["KEY_CLASH"]` | deck keys, camelot | `key:` | (none)               | ✗ |
| `TRANSITION_OPPORTUNITY`| event_detector.py:443 | per `MIN_EVENT_GAP_PER_TYPE["TRANSITION_OPPORTUNITY"]` | deck readiness | `ev:`, `cue:` | (none)               | ✗ |
| `HEARTBEAT`             | event_detector.py:469 | per `MIN_EVENT_GAP_PER_TYPE["HEARTBEAT"]` | (none required) | (none required)     | HEARTBEAT recall     | ✓ |

(Final table comes from a write-time `grep` sweep of current source — the above is the DRAFT layout. The writer fills concrete cooldown seconds + actual evidence-fields list + actual EVIDENCE_SOURCES citations per event by reading the live `evidence_registry.py` + `event_detector.py` + `audio/constants.py` at write-time. REQ-CONTRACT-05 gates correctness.)

### Section ordering

1. **Purpose** — 1 paragraph: "this is the single named contract for what enters the live prompt"
2. **Reading guide** — 3 lines: where to find each thing (table = quick reference, sections = depth)
3. **The composite table** (REQs 01/02/04/07)
4. **Citation source grammar** (REQ-02 detail) — each of the 11 EVIDENCE_SOURCES with body grammar, examples, and which event types may cite
5. **Recall-fragment shapes per event family** (REQ-03) — TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL / PHASE / HEARTBEAT each with template + worked example
6. **Diet-mode** (REQ-04) — what triggers diet path, what gets stripped, why (TTFT budget)
7. **Per-event-type cooldowns** (REQ-07) — `MIN_EVENT_GAP_PER_TYPE` table with rationale per value
8. **Appendix: how to grep-verify this doc** (REQ-05) — one paragraph + the actual `grep` invocations

### CLAUDE.md pointer placement

Insert into the "## Architecture" section near the top — right after the `(test-enforced — do not break)` cardinal-invariants box would put it where contributors scanning for prompt-path orientation land first. One line: `> **Prompt composition contract:** see [docs/PROMPT-COMPOSITION.md](docs/PROMPT-COMPOSITION.md) — single named source for what enters the live prompt per event type (EventType × evidence-fields × citation-sources × recall-fragment × diet-mode × cooldown).`

### Write-time verification protocol (REQ-CONTRACT-05)

Before committing the doc, run a `grep -n` for every `file:line` reference cited in the doc against current `src/vibemix/`. Any reference that doesn't resolve → fix the cite before commit. The doc itself ends with a 5-line "How to re-verify this doc" appendix showing the exact shell loop so future contributors can re-verify on rebase.

</specifics>

<deferred>
## Deferred Ideas

- **CI smoke check on `file:line` resolution.** REQ-CONTRACT-05 explicitly marks this OPTIONAL and not blocking. A future CI gate that runs the grep loop on every PR touching `src/vibemix/state/` would close the staleness risk, but it's HARDEN-FUTURE territory — not v10.0 scope.
- **Documenting the Viber/library prompt surface** in this same doc. Scope is intentionally LIVE-CO-HOST-ONLY. The Viber side is documented by REQ traceability + tool docstrings + P99/P100 SUMMARYs; a separate `docs/VIBER-PROMPT-COMPOSITION.md` is HARDEN-FUTURE if/when needed.
- **Extending evidence sources or event types**. Explicitly out of scope per `Out of Scope` table in REQUIREMENTS.md ("New evidence sources for live co-host"). The doc enumerates the SHIPPED 11+9 surface; growing it is a different milestone.
- **Cooldown rationale write-up beyond one-line per value**. The doc cites cooldowns; an essay on WHY each value is what it is would be useful for tuning work but is out of scope for the contract. Cooldowns have inline comments in `audio/constants.py:77` already.
- **§HARDEN-PHASE-C-DOC-READTHROUGH KAAN-ACTION** — Kaan-eye scan of the rendered doc for "is this useful as a contract?" feel. Rides forward as a parked KAAN-ACTION (per `gsd-autonomous fully` mode, blockers defer to KAAN-ACTION queue at phase close — analog to the §HARDEN-PHASE-A/B ear-pass parks from P99/P100).

</deferred>
