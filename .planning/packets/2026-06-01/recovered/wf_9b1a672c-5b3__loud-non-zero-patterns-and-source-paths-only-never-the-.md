# Loud non-zero — patterns and source paths only; never the bytes.
for hit in result.hits:
    log.error("LEAK pattern=%s source=%s (value redacted)", hit.pattern, hit.source)
return 1
```
So it returns 0 on success, 1 if leaks found, 2 on MsiInspectionUnavailable/FileNotFoundError.

**FACT 3: Release.yml verify step** (lines 424-441 for macOS, 630-640 for Windows):
The workflow runs:
```yaml
uv run python -m scripts.dist.verify_binary "$TARGET" --report dist/verify-report-macos.json
```
And then IMMEDIATELY continues to upload artifacts with NO exit code check. There is NO `if: ${{ ... }}` condition that gates on the exit code.

**FACT 4: Binary states**:
- `dist/vibemix-0.0.1.dmg` (14:19:54, ~119M) — SIGNED by "Francesco Fasanella (UK7DYFK6F8)", STAPLED (notarized)
- `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg` (15:15:47, ~119M) — UNSIGNED, NOT STAPLED

The UNSIGNED DMG is newer (15:15 vs 14:19, 56 minutes later).
