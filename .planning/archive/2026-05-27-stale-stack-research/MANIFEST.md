# Stale Stack Research Archive

Date: 2026-05-27

Archived file:

- `.planning/archive/2026-05-27-stale-stack-research/STACK.md`

Reason:

- The original `.planning/research/STACK.md` was v6.0 memory-stack research
  from 2026-05-22. It treated Gemini Embedding 2 and the Gemini-only/no-CLAP
  constraint as current library-embedding guidance.
- The current product stack uses local CLAP ONNX/512 for library embeddings and
  local Codex for Viber set-prep/chat seams, while Gemini remains scoped to the
  live co-host/conversation path.

Replacement:

- `.planning/research/STACK.md` is now a short pointer to current stack sources.
- Use `.planning/codebase/STACK.md`, `CLAUDE.md`, `docs/clap-engine.md`,
  `docs/codex-agent.md`, and
  `.planning/research/CODEX-full-product-sweep-map.md` as active guidance.
