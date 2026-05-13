# Phase 19: GitHub Launch Presence - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous fully — recommended answers locked; no user pause)

<domain>
## Phase Boundary

Turn `github.com/bravoh/vibemix` into a product launch page, not a code dump.
Every visitor lands on a hero banner + 30-45s demo + one-click installer
buttons + feature matrix + controller grid + screenshots + FAQ + Bravoh
waitlist funnel. OSS hygiene is locked: Apache 2.0 + DCO CONTRIBUTING +
SECURITY + CODE_OF_CONDUCT + NOTICE + TRADEMARKS + issue templates + custom
OG image + clean repo (no scratch, no .bak, no committed .env, no large
binaries in tree).

Out of scope for autonomous execution:
- Filming the 30-45s demo video (Kaan + Francesco shoot during a real set).
- Designing the hero banner artwork (Bravoh design lead — Momo or Kaan).
- Designing the OG social-preview image (same).
- Filming install GIFs (one-shot screen recording, post-binary-ship).

What CAN be shipped autonomously:
- All markdown content (README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, etc.)
- All issue templates + DCO check workflow
- `.github/repo-config.yml` for `gh repo edit` automation of description + topics + homepage
- Repo scrub: move large binaries to release assets / external CDN; delete
  `_test_*.py` scratch files; gate via pre-commit hook + CI test
- Architecture diagram as branded SVG (NOT default Mermaid)
- Feature matrix + controller grid as markdown tables with placeholder logos
  (real logos drop in when Kaan provides them)
- All FAQ entries Kaan-facing — anti-slop, plain-language
- Bravoh waitlist footer link with utm tags

</domain>

<decisions>
## Implementation Decisions

### Area 1 — README Architecture (GH-02..09, GH-10..12)
- **Order of sections (above-the-fold first):**
  1. Hero banner (artwork TBD — placeholder image path until Kaan ships final)
  2. Tagline: "vibemix — an AI co-host for your DJ set. Open source. Mac + Windows."
  3. Demo video/GIF block (placeholder MP4/GIF until shoot, with TODO comment)
  4. Badges row (build status / latest release / license / platform / stars)
  5. One-paragraph value prop: "vibemix listens to your master output, watches your DJ software's screen, ingests your controller, and talks back into your headphones — like a real DJ friend in your ear, not generic AI commentary."
  6. Install buttons (one-click download → Releases page; install GIFs placeholder)
  7. Feature matrix (Beginner/Intermediate/Pro × Hype/Coach grid with example reactions per cell)
  8. Supported-controllers grid (10 controllers from Phase 9 + "calibrate any other" callout)
  9. Screenshots gallery (5 surfaces: calibration wizard, mode picker, voice picker, in-session UI, recording browser)
  10. "How it works" branded SVG architecture diagram
  11. FAQ (8-12 entries — see Area 3)
  12. Built by Bravoh footer with utm-tagged waitlist link
- **Badges:** Use `shields.io` URL templates committed to README, not custom SVGs. Build status badge wires to Phase 18's release.yml workflow.
- **Hero artwork:** Kaan/Momo deliver `docs/assets/hero.png` (1280×640 recommended). Placeholder commits to a 1280×640 dark amber gradient PNG generated in CI from the v5 token palette so the README renders sanely until final art.
- **Demo video:** Hosted as a release asset on the first signed binary release (Phase 18 hands off the binary tag), embedded in README via `<video src="...">` HTML block with WebM + MP4 dual source. Until shoot done, README references `docs/assets/demo-placeholder.gif` (5s loop placeholder).

### Area 2 — Feature Matrix + Controller Grid (GH-05, GH-06)
- **Feature matrix** = markdown table, 3 rows (skill levels) × 2 columns (modes).
  Each cell: 2-3 example reactions in `> blockquote` styling, hand-written per
  PROJECT.md core value tone. Pulled from Phase 10's prompt templates + the
  reaction-reel rubric anchors from Phase 17.
- **Controller grid** = 5×2 table of the 10 controllers from Phase 9 with logo
  placeholders (`docs/assets/controllers/<slug>.png`). Each cell: controller
  name + manufacturer logo + "calibrated" or "generic-fallback" badge based on
  Phase 9's JSON mapping coverage. The "calibrate any other" callout sits below
  the grid with link to `docs/midi-mapping.md` (generic fallback guide).

### Area 3 — FAQ Content (GH-09)
- 12 questions, locked here (Kaan-facing; uses plain language, anti-slop):
  1. "What is vibemix?" — One-paragraph product description.
  2. "Is my audio sent to the cloud?" — Yes, audio chunks are streamed to Bravoh's proxy to reach Gemini. No raw audio stored on Bravoh servers (PROJECT.md privacy commitment). Recordings stay on your machine.
  3. "Is this free?" — Yes for v1. ~50€/month Gemini API cost is absorbed by Bravoh as marketing wedge. May change post-launch with usage scale; will be announced before any change.
  4. "Why no Linux?" — Three reasons: (a) djay Pro is Mac/Win only, (b) BlackHole / PulseAudio loopback differ enough to triple maintenance, (c) Bravoh's first OSS release optimizes for narrow scope. Will reconsider in v2 based on community PRs.
  5. "Why Gemini and not GPT/Claude/etc.?" — Bravoh's product is Gemini-only. vibemix shares the brain. The proxy could in principle route elsewhere but isn't designed to.
  6. "Is the AI actually listening to my music?" — Yes. It listens to your master output via virtual audio (BlackHole on Mac, WASAPI loopback on Windows). It also watches your DJ software's screen + reads your MIDI controller. The "real friend" feel comes from grounding all three.
  7. "Can it hallucinate?" — Phase 16's hallucination gate enforces ≥95% grounded reactions before release. The whole anti-slop stack (negative dictionary, describe-before-infer, past-tense framing, `<silence/>` short-circuit) exists to keep the AI from making things up.
  8. "What's open-source / what isn't?" — vibemix client (this repo): open. Bravoh proxy + main product: closed. Gemini API: Google's. Apache 2.0 means you can fork and self-host the client against your own Gemini API key if you want to skip the proxy.
  9. "Why a Bravoh-managed proxy instead of letting me bring my own key?" — Reasoning + UX: most DJs don't want to manage an API key; quota / rate-limit / billing is centralized at Bravoh. The proxy is opt-out for forkers via env var.
  10. "Will my recordings be uploaded anywhere?" — No. Recordings (`recordings/<session>/`) stay on your machine, default 7-day retention.
  11. "What about Mixxx? Rekordbox?" — v2 candidates (per project memory `project_v2_open_candidates`). v1 = djay Pro only because that's what Kaan/Francesco use daily.
  12. "How do I contribute?" — Link to CONTRIBUTING.md with DCO + controller-mapping path + prompt-template path.

### Area 4 — OSS Hygiene Files (GH-13, GH-14, GH-15)
- **Apache 2.0 LICENSE** — already on disk; verify text matches canonical Apache-2.0 boilerplate; commit hash check.
- **NOTICE** — list all third-party deps with their license + URL. Generated from `pyproject.toml` + `tauri/ui/package.json` + `tauri/src-tauri/Cargo.toml` via a one-off `scripts/dist/gen_notice.py`. NOT regenerated on every commit; refreshed only on dep changes.
- **TRADEMARKS.md** — "vibemix" is a Bravoh trademark; usage rules. Pioneer / Numark / Hercules / Native Instruments product names referenced under nominative fair use. Apple / Microsoft / Google product names referenced under nominative fair use. Generated boilerplate based on the GitHub-recommended TRADEMARKS template.
- **CODE_OF_CONDUCT.md** — Contributor Covenant 2.1 verbatim, enforcement contact = `ozai@bravoh.com`.
- **SECURITY.md** — vuln disclosure: email security@bravoh.com with PGP key. 90-day disclosure timeline. Bug bounty: no formal program for v1; explicit "Thank you" credit in release notes.
- **CONTRIBUTING.md** — DCO sign-off mandatory + 3 contribution paths:
  - Bug fix path: standard PR, DCO, signed-off-by Trailer.
  - Controller mapping path: `midi/profiles/<slug>.json` + smoke test. Auto-merge after CI green for non-conflicting additions.
  - Prompt template path: `src/vibemix/prompts/templates/` extension + manual Kaan review (anti-slop dictionary applies).
- **Issue templates** under `.github/ISSUE_TEMPLATE/`:
  - `bug_report.yml` — version, OS, controller, repro steps, attached events.jsonl
  - `feature_request.yml` — problem statement, proposed solution, alternatives, scope assessment
  - `new_controller.yml` — controller name, manufacturer, USB VID/PID, available MIDI map JSON link, willingness to test
- **PR template** under `.github/pull_request_template.md` — DCO + linked issue + test checklist + breaking-change flag.

### Area 5 — Repo Scrub (GH-18)
- Delete `_test_multimodal.py` + `_test_tts.py` from repo root. They're POC scratch.
- Delete `sprite-1.png` / `sprite-2.png` / `sprite-3.png` from root (2.3 MB each — mascot sprite artifacts that shouldn't be in tree).
- Move `tauri/ui/assets/mascot/character.glb` (20 MB) to a release asset or `git lfs` track. Recommendation: **`git lfs`** for v1 — keeps the file logically in-repo for the Tauri build, but doesn't blow up clone size. Alternative: download-on-build script. LFS is simpler.
- Add `.gitignore` rules for: `*.pyc`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `target/`, `.env`, `.env.local`, `recordings/`, `.claude/worktrees/`, `.planning/.archived/`, `*.bak`, `.playwright-mcp/`.
- Add a pre-commit hook (`scripts/hooks/pre-commit-no-binaries.sh`) that rejects any commit adding files >1 MB (LFS bypass exempt).
- Add a CI scrub test: `tests/repo/test_repo_scrub.py` greps for `_test_*.py` at root + `.bak` files + .env in tracked files + files >1 MB outside LFS. Runs on every PR.
- Cohost POC files (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v3.py`, `cohost_v4.py`, `cohost.streaming.py.bak`, `mascot.html`, `run_v3.sh`, `run_v4.sh`, `fillers/`) are EXEMPT from scrub — per PROJECT.md and CLAUDE.md they're "POC = reference, devour it" reference material. Move them to `archive/poc/` per Phase 1 success criterion (already-in-roadmap action). DEFERRED if not done in Phase 1 — surface in Phase 19 SUMMARY.

### Area 6 — Repo Metadata (GH-17)
- `.github/repo-config.yml` — declarative YAML consumed by a one-off `scripts/dist/configure_repo.sh` wrapping `gh repo edit`:
  - `description`: "AI co-host for your DJ set. Listens to your master output, watches your DJ software, talks back into your headphones. Open source. Mac + Windows."
  - `homepage`: `https://altidus.world/vibemix` (or `https://bravoh.com/vibemix` once that exists)
  - `topics`: ["dj", "livekit", "gemini", "ai-assistant", "audio", "midi", "pioneer-ddj", "realtime-ai", "tauri", "open-source"]
  - `default_branch`: `main`
  - `enable_issues`: true, `enable_projects`: false, `enable_wiki`: false
  - `delete_branch_on_merge`: true
  - `allow_squash_merge`: true, `allow_merge_commit`: false, `allow_rebase_merge`: false (squash-only for cleanliness)
- Script is idempotent; safe to re-run.

### Area 7 — Architecture Diagram (GH-08)
- Branded SVG, NOT auto-generated Mermaid. Saved at `docs/assets/architecture.svg`.
- Generated by an inline HTML/SVG generator script `scripts/dist/render_architecture.py` that emits the SVG from a data dict (boxes, arrows, labels). Uses CDJ Whisper v5 token colors (amber accent, void blacks, silk muted text).
- Layout: 4 horizontal swim-lanes — User Hardware (controller + headphones), vibemix Client (Python sidecar + Tauri UI), Network (Bravoh proxy), Gemini.
- Re-generation: `python -m scripts.dist.render_architecture > docs/assets/architecture.svg` is idempotent. Committed for review.

### Claude's Discretion
- Exact wording of README sections beyond what CONTEXT pins.
- Exact SVG diagram styling within the v5 token palette.
- Whether to add additional badges beyond the 5 listed.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Apache 2.0 LICENSE on disk.
- README.md exists (needs major rewrite per Area 1).
- `mocks/vibemix-cinematic-storyboard.html` — defines the 30-45s demo storyboard (referenced from README via `docs/assets/demo-storyboard.html` link or hosted Bravoh page).
- Phase 9's MIDI profile JSONs — source of truth for controller grid.
- Phase 10's prompt templates — source for feature matrix example reactions.
- Phase 17's RUBRIC — anchor descriptions feed FAQ Q7 "Can it hallucinate?".

### Established Patterns
- `docs/` is the directory for markdown documentation.
- `.github/` for GitHub-specific files.
- Scripts under `scripts/dist/` for distribution-related tooling (Phase 18 will land there too).

### Integration Points
- `.github/workflows/release.yml` (Phase 18) → README badge wires.
- `mocks/` directory must NOT be modified per "POC = reference, devour it" rule.

</code_context>

<specifics>
## Specific Ideas

- README's hero banner placeholder gradient is generated from `--void-1` → `--amber-22` → `--void-1` per the v5 palette.
- FAQ Q2 (audio privacy) gets a one-paragraph standalone callout in README's value-prop section since it's the #1 user concern.
- Feature matrix example reactions are quoted as `> "Wow that bassline switch was clean."` — direct human voice, no AI slop framing.
- Bravoh footer uses utm tags: `?utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch`.
- Squash-only merge policy keeps git log clean for first-time contributors browsing history.

</specifics>

<deferred>
## Deferred Ideas

- **Live demo / interactive playground** — out of scope for v1; would require running vibemix as a hosted demo.
- **Documentation site (docusaurus / mdbook)** — README + a few `docs/` markdown files is enough for v1. Full docs site is v2.
- **Internationalization of README** — Bravoh proper has Italian + English; vibemix v1 ships English-only README. Italian translation is a v1.1 nice-to-have.
- **Press kit (media assets, brand colors, fonts)** — assemble post-launch based on Press inquiries.
- **Discord / community server invite** — wait for actual community signal before standing one up. Stub link in README → roadmap doc.

</deferred>
