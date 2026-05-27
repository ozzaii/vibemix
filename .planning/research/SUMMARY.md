# Project Research Summary

Status: current pointer summary, refreshed 2026-05-27.

The previous v6.0 "Memory Turn" research summary is archived at
`.planning/archive/2026-05-27-stale-v6-memory-research/SUMMARY.md`. It predates
the local CLAP embedding decision, so it must not be used as live implementation
guidance.

## Current Direction

vibemix is a local-first desktop DJ co-host with a Python runtime, Tauri shell,
Vite/TypeScript webview, local library intelligence, and swappable agent seams.
Gemini remains scoped to live co-host conversation. Library search, similarity,
curation, recall, and grounding embeddings use local CLAP ONNX with 512-d
vectors. Local Codex is the current demo/test brain for Viber chat, curate, and
build-set flows; keep that backend replaceable.

Use these as active truth:

- `.planning/codebase/STACK.md` for package/runtime stack.
- `.planning/research/CODEX-full-product-sweep-map.md` for sweep status,
  verification notes, and open risks.
- `CLAUDE.md` for invariants and contributor rules.
- `docs/clap-engine.md` for local CLAP behavior.
- `docs/codex-agent.md` for the local Codex/Viber seam.

## Hard Constraints

- `vibemix.__main__:main()` remains the orchestration entry point.
- Only state refresh writes `MusicState`.
- AI reactions resolve through `EvidenceRegistry`.
- Live audio is authoritative.
- Main UI socket is `127.0.0.1:8765`; debrief uses `8766`.
- Do not hardcode model names; use router/backend seams.

## Planning Note

Historical milestone references to this filename should be read as references to
the archived v6 suite unless they have already been updated for CLAP/Codex.
