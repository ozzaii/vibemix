# vibemix {{ tag }} — Release Notes

**Tag:** `{{ tag }}`
**Released:** {{ release_date }}
**Platforms:** macOS (Apple Silicon) · Windows 11

> The first public release candidate of vibemix — the open-source AI co-host for live DJ sets. Bravoh's first OSS warm-up cut.

---

## Highlights

- **Real DJ friend in your ear, no AI slop.** Reactions are tied to real events via a Gemini-grounded evidence registry. The model has to cite what just happened (BPM jump, layer arrival, track change, MIDI move) before it speaks.
- **Mac + Windows.** One-click install via signed `.dmg` (Apple-notarized) + `.msi` (SignPath OSS-foundation signed).
- **Hype-man or coach.** Two modes × three skill levels (Beginner / Intermediate / Pro). Coach is past-tense — it won't talk while you're working.
- **Library intelligence.** Drag-drop import; Gemini-Embedding-2 powered vibe search + "what's playing" grounding from YOUR library. 30-day staleness nudge keeps it fresh.
- **Post-session debrief.** Chaptered review with 60–90s voiced TL;DR + 3 personalized drills + clickable timeline + cited critique.
- **4-layer mascot.** Base + Emotion + Anticipation + Reaction additive state machine. Sub-budget GLB animations within 25 MB.
- **Free, Apache 2.0.** Bravoh-managed Gemini proxy means no API keys in the binary (solves the "API key in distributed binary" problem).

---

## v2.0 Research-Driven Ship close (Phases 15–26)

v2.1 builds on the v2.0 architectural foundation:

- 3-process Tauri-shell + Python-sidecar + FastAPI-proxy locked.
- 1961 v2.0 tests / 10 pre-existing failures preserved.
- v2.0 final-mile orphan (`register_library`) closed via Phase 28 grounding wire-in.
- POC files (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `mascot.html`) byte-frozen against the `v2.0` git tag (Phase 37 AUDIT-06).

Full v2.0 close summary: [.planning/milestones/v2.0-ROADMAP.md](.planning/milestones/v2.0-ROADMAP.md).

---

## v2.1 The Unified Cut — shipped surfaces

<!-- AUTO-GEN: phase-summaries START -->
{{ phase_summaries }}
<!-- AUTO-GEN: phase-summaries END -->

---

## Known not in this RC (honest list)

- **Linux:** explicitly excluded for v1; loopback-audio stack differs enough that the OS-platform layer triples in maintenance. v2.x with community PR signal.
- **Mixxx + Rekordbox parsing:** scaffolded but not first-party here. v2.2 candidates.
- **Mac App Store / MS Store distribution:** v2.2 stretch.
- **Translation beyond IT for social copy:** v2.2.
- **Real-VM matrix install rehearsal (≤60s onboarding validation):** scaffold ships green; real execution deferred to Kaan-action (`KAAN-ACTION-LEGAL.md INSTALL-VM-RUN`).
- **Apple notarization + SignPath signing (real secrets):** wired and tested with empty-secret skip protocol. External approvals (Apple Developer Program Agreement update + SignPath OSS Foundation application) are legal-capacity carveouts (P46) and ship `:warning::` annotation until populated. Once secrets land, the pipeline lights up automatically.
- **Phase 16 ear-test override expires post-RC bake.** Autonomous hallucination-proxy gates (Phase 27) substitute for Kaan-ear-only test for v2.1 only; expires post-this-RC (P85).

Full Kaan/Francesco-action list: [`KAAN-ACTION-LEGAL.md`](KAAN-ACTION-LEGAL.md) — §SHIP, §POST-RC-CLEANUP, §DIST-09, §DIST-11.

---

## Install

| OS | Download |
|----|----------|
| macOS (Apple Silicon) | `vibemix.dmg` (Apple Developer ID + notarized) |
| Windows 11 | `vibemix-installer.msi` (SignPath Foundation OSS) |

After install, the calibration wizard runs once: TCC permissions (mic + screen recording + accessibility), BlackHole 2ch auto-detect (macOS), MIDI controller pairing.

---

## Verifying signatures

```bash
# macOS
codesign -dvv ~/Downloads/vibemix.app
spctl -a -v ~/Downloads/vibemix.app

# Windows (PowerShell)
Get-AuthenticodeSignature .\vibemix-installer.msi
```

---

## Acknowledgements

- Built by [Bravoh](https://altidus.world) as our first open-source release.
- Special thanks to closed-beta DJs who tested early builds.
- POC encoded decisions (mic-gating, evidence-packet shape, audible-deck heuristics, MIDI maps) lift from `cohost_v4.py` and v2 ancestors — months of real DJ-session iteration ported wholesale.

---

## Feedback

- Bug reports + feature requests: [GitHub Issues](https://github.com/bravoh/vibemix/issues)
- Discord community: see README footer for invite
- Anti-slop bug reports especially welcome — if a reaction feels scripted, late, or hallucinated, please open an issue with the session recording (recordings stay local; you choose what to share).
