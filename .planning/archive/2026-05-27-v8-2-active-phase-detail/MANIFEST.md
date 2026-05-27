# 2026-05-27 v8.2 Active Phase Detail Archive

Detailed v8.2 and adjacent phase folders were moved out of `.planning/phases/` because
they are historical implementation logs, not current operating guidance.

Archived folders:

- `phases/83-energy/`
- `phases/87-agent/`
- `phases/89-dj-library-ingest-auto-detect-dj-library-rekordbox-serato-tr/`
- `phases/90-clap-swap-library-curator-embedding-engine-to-on-device-xeno/`

Reason:

- v8.2 shipped status now lives in `.planning/phases/v8.2-STATUS.md`.
- Phase 89/90 prose still contained in-flight 1536-to-512 and CLAP-wiring language.
- Active product truth is local CLAP ONNX for library embeddings and local Codex for
  Library/Viber chat and set prep.
