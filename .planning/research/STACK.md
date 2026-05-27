# Stack Research Pointer

Status: current pointer; old research archived on 2026-05-27.

The previous contents of this file were v6.0 memory-stack research from
2026-05-22. That document predates the local CLAP embedding decision and is no
longer the product direction.

Historical file:

- `.planning/archive/2026-05-27-stale-stack-research/STACK.md`

Use these sources as current stack truth instead:

- `.planning/codebase/STACK.md` for the current package and runtime stack.
- `CLAUDE.md` for repository working rules and invariants.
- `docs/clap-engine.md` for local CLAP ONNX embedding/search behavior.
- `docs/codex-agent.md` for the local Codex/Viber agent seam.
- `.planning/research/CODEX-full-product-sweep-map.md` for sweep status and
  unresolved risks.

Current product decisions:

- Gemini remains the live co-host / conversational brain.
- Library search, similarity, curation, recall, and grounding embeddings use
  local CLAP ONNX with 512-dimensional vectors.
- Local Codex is the current demo/test brain for Viber chat, curate, and
  build-set flows; keep the backend seam swappable.
- Do not hardcode model names. Route LLM/model choices through existing router
  or backend seams.
- Use `uv sync --group dev --extra ai-local` for local development that needs
  CLAP/CUE runtime dependencies.

Historical references to "Bucket 3", "Bucket 4", or "Bucket 5" belong to the
archived file above, not to current stack guidance.
