# vibemix — GitHub Repository Metadata (canonical source-of-truth)

**Owner:** Phase 39 / SHIP-05
**Consumed by:** `scripts/launch/sync_github_meta.sh`

This file is the single source-of-truth for the vibemix repo's GitHub-side metadata: description, homepage URL, topics. CI greps these values; `sync_github_meta.sh` reads + applies them via `gh api`.

## Description (≤350 chars)

```
Open-source AI co-host for live DJ sets. Listens to your master output, watches your DJ software, reads MIDI controller actions, and talks back as hype-man or coach. Gemini-grounded — never AI slop. Mac + Windows, one-click install. Bravoh's first OSS release.
```

## Homepage URL

```
https://altidus.world/vibemix?utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch
```

## Topics (10 — locked)

GitHub allows up to 20 topics; we ship exactly 10 to keep the surface signal-dense:

```
dj
ai
gemini
tauri
open-source
mascot
livekit
audio
vibemix
bravoh
```

## Real apply

Kaan-action only. Procedure:

1. Verify the description + topics here match what should ship.
2. Set `GH_META_REAL=1` in your shell.
3. Run `bash scripts/launch/sync_github_meta.sh --real`.
4. The script prints every `gh api` call before invoking; review.
5. Cross-check at <https://github.com/bravoh/vibemix> after.

The cutter NEVER applies metadata autonomously — `--real` + `GH_META_REAL=1` are required + checked.

## Repository transfer to `bravoh/vibemix` org

Separate Kaan-action. See `KAAN-ACTION-LEGAL.md §SHIP-TRANSFER`.
