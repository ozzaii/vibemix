# Pitfalls Research Pointer

Status: current pointer, refreshed 2026-05-27.

The previous v6.0 pitfalls research is archived at
`.planning/archive/2026-05-27-stale-v6-memory-research/PITFALLS.md`. It
predates the current local CLAP embedding path and is historical.

Current high-risk areas:

- Do not regress library embeddings back to cloud-era dimensional assumptions;
  active product embeddings are local CLAP ONNX/512.
- Do not present CLAP text prompts as exact semantic truth. They are useful for
  coarse vibe/genre search, not fine-grained factual claims.
- Keep local model setup clear: required CLAP must be first-run reliable;
  optional CUE failures must not look like app setup failure.
- Preserve the evidence contract: AI reactions must cite registered evidence and
  live audio remains authoritative.
- Do not hardcode model names or couple Viber to a single backend.
- Treat packaging/signing/updater claims as unproven until the release runner
  and previous-version updater rehearsal have exercised them end to end.
- Do not confuse historical planning docs with active truth; use the sweep map
  and `.planning/codebase/STACK.md`.

Historical section references to this file belong to the archived v6 file unless
the referencing phase has been refreshed.
