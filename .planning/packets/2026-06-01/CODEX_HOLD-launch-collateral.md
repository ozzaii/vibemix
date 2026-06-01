# CODEX_HOLD: Launch Collateral

Date: 2026-06-01
Author: Codex
Package: 11 - Launch Collateral
Decision: HOLD
Suggested commit if repaired: `docs(launch): package honest launch collateral and screenshots`

## Summary

Do not land Package 11 as current launch collateral yet.

The mechanics are healthy: the chosen screenshots exist, image dimensions match
the screenshot README, the PDF and MP3 are valid media files, the talking-page
builder is lint-clean, generated preview HTML stays ignored, and the builder can
round-trip a generated HTML page.

But the launch-copy files are not product-honest enough for the current rebuild.
They carry stale release posture, old free/open-source positioning, cloud/privacy
overclaims, and Viber/cue-export claims that are ahead of the current product.
The screenshots can be reused, but the copy deck needs a truth rewrite before it
represents the app.

## Files Reviewed

- `docs/launch/.build_talking.py`
- `docs/launch/.partner-capabilities-tr-short.html`
- `docs/launch/.vibemix-pitch-en.html`
- `docs/launch/.vibemix-pitch-tr.html`
- `docs/launch/vibemix-yetenekler-tr.pdf`
- `docs/launch/vibemix-vo-charon.mp3`
- `docs/launch/screenshots/README.md`
- `docs/launch/screenshots/shell-live-moneyshot.png`
- `docs/launch/screenshots/shell-deck-final.png`
- `docs/launch/screenshots/viber-chat-elevated.png`
- `docs/launch/screenshots/crate-elevated.png`
- `docs/launch/screenshots/debrief-elevated.png`
- `docs/launch/screenshots/learn-elevated.png`
- `docs/launch/screenshots/settings-elevated.png`
- `docs/launch/screenshots/wizard-current.png`
- `docs/launch/screenshots/viber-chat-closeup.png`
- `docs/launch/screenshots/settings-closeup.png`
- `docs/launch/screenshots/rail-closeup.png`

## What Is Good

- `docs/launch/screenshots/README.md:9-16` clearly states generated preview HTML
  must remain generated and lists the talking-page source files.
- `docs/launch/screenshots/README.md:20-33` defines the canonical launch
  screenshot set, all eight at 1440x900.
- `docs/launch/screenshots/README.md:37-44` defines the optional detail crops.
- `file` reports the selected full screenshots as 1440x900 PNGs, the detail
  crops as PNGs, `vibemix-yetenekler-tr.pdf` as a PDF 1.7 document, and
  `vibemix-vo-charon.mp3` as a 96 kbps, 24 kHz mono MP3.
- `pdfinfo docs/launch/vibemix-yetenekler-tr.pdf` reports a 4-page A4 PDF with
  no JavaScript and no encryption.
- `afinfo docs/launch/vibemix-vo-charon.mp3` reports one 41.136s mono MP3 track.

## HOLD Blockers

### 1. Release posture is false for current proof

- `docs/launch/.partner-capabilities-tr-short.html:408` says macOS Apple Silicon
  is signed and notarized and going out today, with Windows 11 stable on the way.
  Current package/release truth is the opposite: the latest-code DMG and the
  signed/notarized DMG were split artifacts, so no launch collateral may imply a
  fresh signed/notarized product package until Package 13B/13C proof lands.
- `docs/launch/.vibemix-pitch-en.html:217` says "Free. Open source. Running on
  Mac today." This conflicts with the monetized-product posture and the package
  release gate. The safe posture is Apache client plus Bravoh-managed service,
  with release-gated packaged builds.
- `docs/launch/.vibemix-pitch-tr.html:217` carries the same claim in Turkish.

### 2. Viber/library claims outrun the product surface

- `docs/launch/.partner-capabilities-tr-short.html:374` says Viber can do
  one-click Rekordbox XML export while preserving cue and beatgrid. Current
  recovered Viber verification says the product is wired through Tauri
  `invoke()`, but cue-export GUI is still a real gap. This line must become
  "planned/export path" or wait for the cue-export GUI package.
- `docs/launch/.vibemix-pitch-en.html:153-154` and
  `docs/launch/.vibemix-pitch-tr.html:153-154` say full-set generation happens
  and everything stays on the machine, never cloud. That needs narrower wording:
  library analysis/search can be local, but the live co-host stack and hosted
  service path are not a blanket "never cloud" product claim.

### 3. Grounding and Learn claims are too absolute

- `docs/launch/.partner-capabilities-tr-short.html:387` says every reaction is
  structurally forced to cite evidence and every release must pass a hallucination
  gate at real-set groundedness of at least 95 percent. That is an aspiration/gate,
  not something Package 11 proves as launch collateral.
- `docs/launch/.partner-capabilities-tr-short.html:377-379`,
  `docs/launch/.vibemix-pitch-en.html:166-168`, and
  `docs/launch/.vibemix-pitch-tr.html:166-168` present the beginner/Learn path as
  a clean product story. Current Learn packages improved operator actions and
  Earned Wall refresh, but Course 3 routed-audio release readiness and Beatmatch
  live credit remain explicitly unproven.

### 4. Visual/copy system is stale

Impeccable/product context loaded from `PRODUCT.md` and `DESIGN.md` says the
current product language is precise, restrained, alive, rose-shifted tozpembe,
and commercially framed. These launch HTML files still use the older amber-era
pitch style and patterns that the current design system rejects:

- `docs/launch/.vibemix-pitch-en.html:11-14` and
  `docs/launch/.vibemix-pitch-tr.html:11-14` define amber/magenta CSS variables.
- `docs/launch/.vibemix-pitch-en.html:75-76`,
  `docs/launch/.vibemix-pitch-tr.html:75-76`, and
  `docs/launch/.partner-capabilities-tr-short.html:202,250,277` use thick
  side-stripe card borders.
- The launch HTML includes many em-dash copy marks. The current design/copy
  guidance says launch copy should use cleaner punctuation.

## Small Fix Applied

One immediate public-claim issue was corrected in
`docs/launch/.vibemix-pitch-en.html:192`: the line no longer says every hardware
sale "ships with a coach included." It now says partner bundles can carry that
message once release gates pass.

That patch reduces one overclaim, but it does not repair the rest of the deck.

## Verification Run

Command:

```bash
uv run ruff check docs/launch/.build_talking.py
```

Result:

```text
All checks passed!
```

Command:

```bash
uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan-codex.html && uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan-codex.html --check
```

Result:

```text
OK 652 KB -> /tmp/vibemix-konusan-codex.html
```

Command:

```bash
git check-ignore -v docs/launch/.vibemix-konusan.html docs/launch/.partner-capabilities.html docs/launch/.partner-capabilities-short.html
```

Result: all three generated preview files are ignored by `.gitignore`.

Command:

```bash
git diff --check -- docs/launch/.build_talking.py docs/launch/.partner-capabilities-tr-short.html docs/launch/.vibemix-pitch-en.html docs/launch/.vibemix-pitch-tr.html docs/launch/vibemix-yetenekler-tr.pdf docs/launch/vibemix-vo-charon.mp3 docs/launch/screenshots/README.md docs/launch/screenshots/shell-live-moneyshot.png docs/launch/screenshots/shell-deck-final.png docs/launch/screenshots/viber-chat-elevated.png docs/launch/screenshots/crate-elevated.png docs/launch/screenshots/debrief-elevated.png docs/launch/screenshots/learn-elevated.png docs/launch/screenshots/settings-elevated.png docs/launch/screenshots/wizard-current.png docs/launch/screenshots/viber-chat-closeup.png docs/launch/screenshots/settings-closeup.png docs/launch/screenshots/rail-closeup.png
```

Result: passed with no output.

## Verdict

HOLD Package 11 as current launch collateral.

Recommended split:

- LAND later as `docs(launch): archive selected screenshots` if the team only
  wants the screenshot/media assets and README.
- Rewrite the pitch/partner HTML/PDF copy against the current Product Reality
  Spine, Package 0I posture, Viber correction, Learn boundaries, and packaging
  gates before any public/partner use.
