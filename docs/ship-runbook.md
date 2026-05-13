# vibemix v0.1.0 — Ship Runbook (Kaan-only steps)

> The single doc that, when every step is checked, lets you run
> `git tag v0.1.0 && git push --tags` and ship.
>
> Everything an LLM could ship has shipped. This doc covers the human
> bits — credentials, accounts, content, and the one ear-test gate
> Kaan reserved.
>
> **Verify state at any time with:**
> ```bash
> scripts/dist/pretag_check.sh
> ```

---

## Status snapshot (as of 2026-05-13)

| # | Item                                              | Owner       | Blocker class | Done? |
|---|---------------------------------------------------|-------------|---------------|-------|
| A | Phase 16 ear-test signoff                         | Kaan        | DJ session    | ☐    |
| B | Phase 17 reaction-reel grading (4 raters)         | Kaan + crew | Coord         | ☐    |
| C | Apple app-specific password generation            | Francesco   | Account       | ☐    |
| D | Tauri updater keypair generation                  | Kaan        | One command   | ☐    |
| E | Configure 11 GitHub secrets                       | Kaan        | Account       | ☐    |
| F | bravoh/vibemix GitHub org/repo created            | Kaan        | Account       | ☐    |
| G | Discord server + invite link                      | Kaan        | Account       | ☐    |
| H | SignPath OSS Foundation cert approval             | Kaan        | 3-week SLA    | ☐    |
| I | Hero artwork + controller logos + demo GIF        | Kaan + crew | Creative      | ☐    |
| J | Day-zero analytics on api.altidus.world           | Musa        | Bravoh-side   | ☐    |
| K | Fresh-machine install rehearsal both platforms    | Kaan        | Physical mach | ☐    |

Once all 11 are ☑, run `scripts/dist/pretag_check.sh` → it should exit 0.

---

## A — Phase 16 ear-test signoff

1. Run `./run_v4.sh` (your canonical baseline) on your DJ rig.
2. Play a real set — at least 30 minutes, mix of genres.
3. Listen for slop: reactions that don't tie to what you're doing, generic
   AI-assistant tone, talking over you, hallucinations.
4. When you're satisfied, create
   `.planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md`
   with the frontmatter `status: passed` and a paragraph describing what
   you tested + what passed.

Template:
```markdown
---
gsd_verification_version: 1.0
phase: 16
phase_name: Hallucination Verification Gate
status: passed
verified_at: 2026-MM-DD
verifier: Kaan
---

# Phase 16 — Kaan's ear-test signoff

Tested on <date> at <location> using <controller>. Played <X> minutes
across <genres>. Both hype-man and coach modes.

## What passed
- ...

## What I'm watching but didn't block on
- ...
```

## B — Phase 17 reaction-reel grading

1. Record a 30-min reel with vibemix running (already wired in Phase 17 —
   see `benchmarks/reaction_reel/grade.py`).
2. Ship the reel to Francesco + 2 DJ network friends with `grade.py`
   instructions.
3. Each rater fills a row in `benchmarks/reaction_reel/grading-sheet.csv`.
4. Run `python -m benchmarks.reaction_reel.analyze` — get average + flag any 1-2 ratings.
5. ≥4.0 average + zero 1-2 ratings → pass.

## C — Apple app-specific password

**Findings from the BRAVOH server audit (2026-05-13):**
- Apple Developer ID Application cert: `Francesco Fasanella (UK7DYFK6F8)`
- Cert installed in your local Mac Keychain ✓
- `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID` already exported
  in zsh from BRAVOH desktop setup
- **Only missing: `APPLE_APP_PASSWORD`** — Francesco generates one at
  appleid.apple.com → Sign-In and Security → App-Specific Passwords →
  label it "vibemix notarytool"

Once Francesco hands it over, paste into the GitHub secret
`APPLE_APP_PASSWORD` (step E).

**Server-side App Store Connect API key** (`AuthKey_G26449M849.p8`,
Key ID `G26449M849`, on altidus at `/var/www/bravoh-backend/keys/`) is
for the iOS BRAVOH app — NOT for vibemix desktop notarization. Different
cert class. Don't confuse them.

## D — Tauri updater keypair

```bash
npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key
```

Two files emerge:
- Private: `~/.tauri/vibemix_updater.key` (treat like an SSH key)
- Public: `~/.tauri/vibemix_updater.key.pub` (paste into config)

Then:
1. base64 the private half:
   ```bash
   base64 -i ~/.tauri/vibemix_updater.key | pbcopy
   ```
   Paste into GitHub secret `TAURI_UPDATER_PRIVATE_KEY` (step E).
2. Open `tauri/src-tauri/tauri.conf.json5` → find the
   `plugins.updater.pubkey` field with the placeholder sentinel → replace
   with the contents of `~/.tauri/vibemix_updater.key.pub` (it's a
   single base64 line).
3. The pretag gate validates the placeholder is gone.

Full procedure: `tauri/src-tauri/keys/README.md`.

## E — Configure 11 GitHub secrets

In the `bravoh/vibemix` repo settings → Secrets and variables → Actions:

| Secret name                              | Source                                                                  |
|------------------------------------------|-------------------------------------------------------------------------|
| `APPLE_DEVELOPER_ID_P12_BASE64`          | Export cert from Keychain → base64 the .p12                             |
| `APPLE_DEVELOPER_ID_P12_PASSWORD`        | The password you used during .p12 export                                |
| `APPLE_ID`                               | Francesco's Apple ID email (already in `$APPLE_ID` env var locally)     |
| `APPLE_APP_PASSWORD`                     | From step C                                                             |
| `APPLE_TEAM_ID`                          | `UK7DYFK6F8`                                                            |
| `SIGNPATH_API_TOKEN`                     | From SignPath dashboard after step H approval                           |
| `SIGNPATH_ORGANIZATION_ID`               | From SignPath dashboard                                                 |
| `SIGNPATH_PROJECT_SLUG`                  | `vibemix` (or whatever you named the project in SignPath)               |
| `TAURI_UPDATER_PRIVATE_KEY`              | base64 of `~/.tauri/vibemix_updater.key` from step D                    |
| `TAURI_UPDATER_PRIVATE_KEY_PASSWORD`     | Whatever password you set during keypair generation (can be empty)      |
| `BRAVOH_MANIFEST_UPLOAD_TOKEN`           | Bearer token for `api.altidus.world/vibemix/updates/upload` — ask Musa  |

Full reference: `.github/workflows/README.md`.

## F — Create bravoh/vibemix GitHub org/repo

1. Create the `bravoh` organization at github.com/organizations/new (or
   reuse if it exists).
2. Create the `vibemix` repo as a public repo.
3. Push this local clone:
   ```bash
   git remote set-url origin git@github.com:bravoh/vibemix.git
   git push -u origin main
   ```
4. Repo settings:
   - Allow Discussions: ON
   - Allow Issues: ON
   - Default branch: main
   - Branch protection on `main`: require status checks + PR review for v0.1.1+
5. Run `bash scripts/dist/configure_repo.sh --apply` (Phase 19 19-01) to
   bulk-apply topics, description, social preview image.

## G — Discord server

1. Create a Discord server (or use Bravoh's existing one with a vibemix channel).
2. Generate an invite link with no expiry, unlimited uses, for #vibemix-launch.
3. Edit `README.md`: replace `Discord: **TBD**` with
   `Discord: <https://discord.gg/YOUR_CODE>`.
4. Remove the `<!-- TODO(kaan, pre-tag-v0.1.0) -->` marker on the line above.

## H — SignPath OSS Foundation cert

Approval SLA is ~3 weeks. If you haven't already:
1. Apply via the doc at `.planning/research/signpath-application.md` (or
   the SignPath website if that path doesn't exist yet).
2. Provide: project name `vibemix`, GitHub org `bravoh`, license Apache 2.0,
   maintainer contact, link to README.
3. Track approval in `gh issue create --title "Track SignPath approval"`.

Until approved, `release.yml` runs Windows in mock-signing mode and
publish is blocked.

## I — Hero artwork + controller logos + demo GIF

1. Hero PNG: `docs/assets/hero.png` currently a placeholder. Drop the
   final artwork that matches the [CDJ Whisper](#) direction.
2. Controller logos: `docs/assets/controllers/*.png` — 10 files needed,
   one per supported controller, neutral product shot 400px wide.
3. Demo GIF: `docs/assets/demo-placeholder.gif` — shoot a 30–45s screen
   recording showing the live session UI reacting in real time, encode
   to GIF + WebM. Replace the placeholder.
4. OG image: `docs/assets/og-image.png` — 1200×630, for social
   embeds. Hero artwork + tagline.

Phase 19 SUMMARY tracks the asset list (`19-04-SUMMARY.md`).

## J — Day-zero analytics on api.altidus.world

Hand off to Musa. The contract:
- vibemix client emits telemetry to `/v1/telemetry/event` (already wired).
- Musa wires dashboards on the existing event tables.
- Alerts: `verify_binary_failed > 1% / 1h` and `per-DAU Gemini cost >
  median + 3·MAD` over rolling 7d baseline.
- Both alerts arm 24h after v0.1.0 push (baseline warm-up).

## K — Fresh-machine install rehearsal

Follow `docs/install-rehearsal.md`. Two platforms. Stopwatch each step.
Target: under 10 minutes from "click download" to "first AI reaction".

Log the results in `.planning/phases/20-day-zero-operations/20-VERIFICATION.md`.

---

## When everything's ☑

```bash
# Final readiness check
scripts/dist/pretag_check.sh    # must exit 0

# Bump version
# - tauri/src-tauri/tauri.conf.json5 → "version": "0.1.0"
# - pyproject.toml → version = "0.1.0"

# Tag + push
git tag -s v0.1.0 -m "vibemix v0.1.0 — first public release"
git push origin main --tags

# Now follow docs/post-launch-playbook.md from T+0.
```
