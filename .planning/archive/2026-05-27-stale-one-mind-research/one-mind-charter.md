# Milestone Charter — v8.1 "One Mind"

> Seed document for `gsd-new-milestone`. Expands Kaan's vision (the two long messages of 2026-05-25) + the night's synthesis + the 4 research reports in this folder. The roadmapper consumes this at the research gate.

## ★ NORTH STAR — The Idea (top-down; everything below serves this)

> This is the idea in Kaan's mind, confirmed 2026-05-26. It is the source of truth. The codebase "islands" are not the idea — they are raw material wired INTO it.

**An AI that hears music *with* you — and *gets* you.** Not a tool; a **presence**. It listens alongside you, grounded and real, and it knows who you are. Kaan's years-old dream, verbatim: *"As soon as AI was there, I always wanted AI to hear music with me."*

This is **ONE idea** with five faculties and a soul — NOT a pile of features or code islands. The "minor thing which is major": today these live as disconnected pieces; plugging them all into the one idea is the unlock ("blowing minds").

**Faculties — what it does:**
- **HEARS** — perceives what's playing: track, vibe, genre, structure, energy, and *your moves*. Uses whatever it can, even imperfect ("if it can hear in hollow space, still use it"). Grounded in real audio/data.
- **GETS YOU** — knows your taste, your semantics, your history, what *clicked* for you. Personal to your lived experience.
- **SPEAKS IN THREE VOICES** — *hype* (rides the party with you) · *critique* (coach: what would've been better) · *tutor* (teaches DJing through who YOU are — semantics, reality, taste). One being, three lenses.
- **CURATES** — builds playlists/sets that understand you; hears tracks, finds meaning, sequences to your vibe. The agentic engine (both backends + transports).
- **NEVER LIES** — hallucination always guarded; if it isn't real, it isn't said.

**The substrate — the philosophy under the idea:**
- Understanding music is **semantic + felt**. Meaning lives in experience. *You are the semantic representation of everything you've lived.* The product translates *how it feels to hear music* — the clicked moment — into the machine.
- AI = the interpreter / voice. Perception = grounded. **Taste / judgment = YOURS, encoded** — the non-outsourceable soul. (This is why Kaan is the one to build it; the felt layer can't be scraped from the web.)

**Idea → phase map (how the islands serve the idea):**

| Idea faculty | Phase(s) serving it |
|---|---|
| **HEARS** (grounded perception) | 77 grounding→agent · 78 deeper ear · 80 Gemini secondary ear |
| **GETS YOU** (taste / semantics / memory) | 77 memory ingest · 81 BENCH (your taste rubric) · 82 shared taste |
| **THREE VOICES** (hype / critique / tutor) | 79 LENS |
| **CURATES** (agentic engine) | 82 CURATE (gemini + codex backends + Telegram/pill transports) |
| **NEVER LIES** (anti-slop) | every phase — additive, citation-grounded |
| **ONE IDEA** (the unification) | the milestone itself: "One Mind" |

Emotional frame: this is the module where Kaan's lived experience — three years of raving, the felt sense of when a drop *clicked* — becomes the product's non-outsourceable moat. Built while he rests; honest green, never faked. Kaan's ear is the final judge of "did it click."

## The Problem (why it's not connected yet — Kaan's "minor thing which is major")

The pieces are strong but **disconnected islands** (see `connection-map.md`): the live co-host runs as one spine; the library/Viber curator is a fully parallel surface; they share only a file on disk — no shared engine, no shared persona, no shared taste layer. And the "shallowness" Kaan feels is NOT a Gemini limitation — it is (1) a **wiring gap** (the deepest DSP perception is discarded at the prompt boundary → "React naturally."), and (2) **asking Gemini to be the ear** when its training made it a culture/taste *interpreter*, not a perceiver. Proven empirically tonight: 3 frontier models gave 3 different genres for one track (raw-audio bench floor).

## The Architecture (the diamond at the core)

ONE product = **two surfaces** (live co-host + library curator) sharing **ONE engine** + **ONE taste layer**, exposed as **THREE lenses**.

1. **Perception engine (the EAR — DSP/MIDI/embeddings, NOT Gemini):** real-time, deterministic, grounded. Multi-scale trajectory (bar → phrase → track → set), the DJ's *moves* (MIDI/EQ/fader/blend), timbre/layer events (the 8 detectors, now wired), harmonic (Camelot), genre via mean-centered embedding cosine (86.5%, €0). Delivers a **structured state** both surfaces read.
2. **Interpreter (the VOICE — Gemini, grounded):** takes structured state + trajectory + calibrated confidence + deltas (not raw scalars) and reacts with taste and culture. Gemini *may also hear* the audio as a secondary grounding input ("if it can hear in hollow space, use it") — but never as the primary perceiver. Hallucination-guarded throughout (citation grounding, abstain-when-unsure).
3. **Taste layer (the SOUL — Kaan's rubric):** what "clicked," what deserves praise, what to fix — authored from lived experience. The reward signal. Shared by both surfaces.
4. **Three lenses on the same data:** **hype** (party hype-man), **critique** (coach — what to fix), **tutor** (explains DJing based on who you are, the semantics, reality, taste). Lens selection shared across surfaces.

## Requirement Categories → Phases (proposed)

- **WIRE — connect the islands** (connection-map top-5): grounding→live agent (#1), detectors→prompt+registry (#2), genre→evidence (#4), persona/lens unify across surfaces (#3), memory ingest on live path (#5). Plus the **env-key override fix** (ghost `GEMINI_API_KEY` shadows `.env` → app must load with `override=True`).
- **PERCEIVE — the ear gets deeper, generalized:** trajectory/phrase-grid contexting (snapshot→narrative), deltas + calibrated confidence in evidence, genre-prototype table from embeddings. NO new DSP detectors, NO new MIR libraries (GPL/AGPL/NC license wall — Apache-2.0 + Bravoh reuse).
- **LENS — the three modes:** hype / critique / tutor as grounded prompt lenses on shared state, persona shared across co-host + curator.
- **GROUND — Gemini as secondary ear:** audio part fed alongside structured evidence, hallucination-guarded; measured against the bench.
- **BENCH — the validation instrument (multi-dimensional):** the experiment that proves the architecture. Dimensions: model × input-grounding (raw audio | DSP-evidence-only/no-audio | audio+DSP | audio+DSP+trajectory+genre) × prompting (generic | structured) × contexting (snapshot | trajectory) × lens (hype/critique/tutor) × taste (with/without rubric). Two studies (architecture-axis with 1 model; model-axis with best architecture) + the no-audio cell that tests "intelligence resides elsewhere." Eval: automated first-pass (groundedness vs DSP facts, specificity, mode-fidelity) → **Kaan's ear is the final judge** (Phase-16 rule).
- **CURATE — unify curator + co-host:** the agentic playlist engine that understands who you are shares the engine/taste/lens; both are facets of "AI that hears music with you." **Scope covers it ALL:** the curator is the shared grounded `library/toolset.py` core driving BOTH backends — **gemini** (`library/agent.py`) and **codex** (`library/codex_curate.py` + `library/mcp_server.py`, the Codex MCP STDIO agent we added) — plus the Telegram bridge + `next_suggestion` (the pill) transports riding over it. The unification (persona/lens/taste/grounding) reaches every backend + transport; nothing is orphaned.

## Constraints (locked)

- **Ship, don't over-engineer** (the DSP rabbit-hole was the lesson). Each phase ships one connected, tested wire.
- **Gemini-only** AI provider; no CLAP/MERT/torch; no new MIR libs; no new ws ports; no new managed-memory frameworks.
- Four cardinal invariants hold by additive design (gated-off cold path = byte-identical).
- **Honest green** — unit-testable without the API; live e2e verified with the working key (`...32u744`, project 709533190790, funded); never fake results.
- Autonomous overnight: drive GSD gates without blocking Kaan; defer blockers to KAAN-ACTION.

## Status at charter time (2026-05-25)

- ✅ Research done: connection-map, genre-from-embeddings (the win), gemini-audio-truth-test (floor data in), gsd-operational-playbook.
- 🔨 In flight: WIRE #2+#4 (detectors+genre → prompt, TDD) — background agent.
- 🟢 Unblocked: env-key override solved; working funded key in `.env`; bench floor data captured (3-model genre disagreement = thesis proof).
- ⏭️ Next: open milestone (this charter) → `gsd-autonomous` per the playbook.
