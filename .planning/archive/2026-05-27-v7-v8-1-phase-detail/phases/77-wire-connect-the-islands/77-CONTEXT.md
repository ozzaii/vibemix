# Phase 77: WIRE — Connect the Islands - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous; grey areas auto-resolved with charter-recommended answers per Kaan's overnight authorization)

<domain>
## Phase Boundary

Turn the strongest disconnected islands into one grounded mind. Four wires (WIRE-02 + WIRE-03 already shipped green as commits `ccf4930` + `a9979b8` — not re-planned):

- **WIRE-01** — the live co-host references what is actually playing, via the already-armed-but-orphaned `Grounding` engine.
- **WIRE-04** — both surfaces (live co-host + library curator) speak with ONE persona/lens; BOTH curator backends (gemini + codex) stop hardcoding their voice.
- **WIRE-05** — the recall store (`memory.db`) actually fills on a real live session.
- **WIRE-06** — the app loads its API key without a ghost shell env var shadowing `.env`.

**Out:** no new DSP, no MIR libs, no new ws ports, no new IPC envelopes, no AI/embedding provider beyond Gemini. The four cardinal invariants hold by additive design (gated-off cold path = byte-identical).
</domain>

<decisions>
## Implementation Decisions

### WIRE-01 — Grounding → live agent
- `DJCoHostAgent.__init__` gains an optional `grounding=None` parameter (DI-over-globals; matches the convention of allocating state in `main()` and passing explicitly).
- `__main__.py` passes the already-boot-armed `Grounding` instance (built ~`__main__.py:1147`, currently never passed) into the agent.
- The agent consults `grounding` **read-only** inside the reaction-building path, alongside the existing evidence — never writes `MusicState` (single-writer invariant #1 holds).
- Cold path: when `grounding is None`, behavior is byte-identical to today (the gate). Existing tests stay green unchanged.

### WIRE-04 — Shared persona / lens across surfaces
- `prompts/matrix.py` (the live co-host persona matrix) is the single source of truth for voice/lens.
- `library/agent.py` (gemini backend) stops hardcoding `_SYSTEM_INSTRUCTION` voice; it reads the shared persona seam.
- `library/codex_curate.py` + `library/mcp_server.py` (codex backend) read the same shared seam — neither backend is orphaned (CURATE acid test).
- Lens selection is exposed as shared state so the curator and co-host can be set to the same lens; curator default = the curator-appropriate lens (tutor/curator voice), overridable.

### WIRE-05 — Memory ingest on the live path
- `main()` calls the same boot-sweep / ingest entry that `SessionLoop.run()` uses (`run_boot_sweeps` / `_fire_ingest`) so recall personalization fills during a real session, not only the stub loop.
- Gated behind `VIBEMIX_RECALL_ENABLED` (default OFF) — additive no-op by default; memory subsystem stays opt-in (no behavior change for the default user).

### WIRE-06 — Env-key override
- App entry loads dotenv with `override=True` so a stale/ghost `GEMINI_API_KEY` in the shell environment can no longer shadow the funded key in `.env`.
- This is the app-level fix of the bug diagnosed this session (ghost `...QSFyBQ` shadowed `.env`'s funded `...32u744`).

### Claude's Discretion
- Exact method names, helper extraction, and test file placement — follow existing `src/vibemix/` conventions.
- Whether grounding consultation is a new helper or inline in the existing reaction builder — planner's call, smallest additive diff preferred.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Grounding` engine — built + armed at boot (`__main__.py` ~1147), fully functional, just never passed downstream.
- `prompts/matrix.py` — existing persona matrix (the live persona source; curator should consume it).
- `run_boot_sweeps` / `_fire_ingest` — memory ingest entries already used by `SessionLoop.run()`.
- `model_router.resolve(...)` — config-driven model resolution (no hardcoded literals; CI grep-gated).

### Established Patterns
- DI-over-globals: state allocated in `main()`, passed explicitly. Only module-level singletons are feature flags.
- Additive gated design: new capability behind a flag / optional param; cold path byte-identical (preserves the four cardinal invariants).
- `from __future__ import annotations`, PEP 604 unions, `snake_case` modules, `_prefixed` private helpers, `*_loop` async tasks.

### Integration Points
- `DJCoHostAgent.__init__` (`agent/dj_cohost.py` ~340-421) — grounding injection point.
- `__main__.py` ~1147 (grounding armed) + ~1219-1221 (where `SessionLoop.run()` ingest is bypassed by `main()`).
- `library/agent.py:58,189` (hardcoded voice) ↔ `prompts/matrix.py:698` (shared persona).

### Verification reality (per memory)
- Unit-testable without the API (honest green). Live e2e on the funded key `...32u744` is a KAAN-ACTION/produce-and-park item — never faked.
</code_context>

<specifics>
## Specific Ideas

- Highest-leverage wire is WIRE-01 (grounding→agent) — it is "one shared engine" made concrete and matches the known grounding gap from the master handoff.
- WIRE-06 is a real shipped-bug fix, not cosmetic: without it the live runtime can use the dead ghost key even with credits in `.env`.
</specifics>

<deferred>
## Deferred Ideas

- Deeper perception (deltas, trajectory, genre-prototype) → Phase 78.
- The three lenses as distinct grounded modes → Phase 79 (this phase only unifies the persona *seam*, not the three modes).
- Gemini-as-secondary-ear → Phase 80.
</deferred>
