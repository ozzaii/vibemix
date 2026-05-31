# Final Acceptance Contract - 2026-05-31

Purpose: define what "done" means for the whole rebuild. The app is not done
when the code compiles, when a demo runs, or when one package lands. Done means
the planned capabilities that survive the rebuild are wired together, verified,
documented, installable, and cleanly packaged into a maintainable repo.

## Product Posture

vibemix is now a monetized product, not a project that must optimize for being
fully open source. Open-source compatibility, license hygiene, and user trust
still matter, but they are constraints around a commercial app, not the north
star.

Do not slow down or weaken the product only to preserve an old open-source
claim. If a closed, paid, hosted, proprietary, or commercial component is the
right product choice, record the license/cost/privacy implications and evaluate
it honestly. The final app should deserve monetization through capability,
polish, reliability, and a clean install experience.

## Final Bar

The rebuild can be called complete only when all of these are true:

- every dirty file is integrated, intentionally deferred, or deleted;
- the package checker is green;
- the capability ledger has no `unknown` rows;
- all surviving planned capabilities are either `integrated`, `deferred`, or
  `drop` with rationale;
- all frontend surfaces that remain in product are wired to real backend/runtime
  data, not stale mocks;
- all live/runtime claims have source-mode and, when UI-visible, Tauri/UI proof;
- all model/cue/intelligence claims have real eval, fixture eval, or explicit
  deferral;
- Learn uses the shared evidence/observability/runtime spine instead of living
  as a disconnected curriculum island;
- judge voice is either live-wired with grounded citations or explicitly
  deferred;
- local TTS is either installable and license/model-source clean, or explicitly
  deferred;
- one-click install/package flow is verified through the accepted platform path;
- dependency rings are resolved or explicitly deferred without conflicts;
- old docs from the rebuild window have been read, classified, and superseded or
  preserved intentionally;
- open-source-era claims have been updated so public docs match the commercial
  product posture;
- accepted work is merged/pushed to `main` only after final verification passes;
- Codex independently accepts the final verifier packet.

## Frontend Acceptance

Frontend is complete only when:

- session UI consumes the current canonical UI bus;
- settings/profile/library surfaces do not spam or duplicate subscriptions;
- pill/next-suggestion UI preserves compact visible text plus recoverable detail;
- Learn UI uses the same bus discipline as session UI;
- library/Viber UI reflects real grounded tool output;
- visual mockups are either ported into production with tests or kept as design
  references;
- screenshots/proof JSON are tied to current code, not stale mock HTML;
- `npm --prefix tauri/ui run check:ipc`, focused UI tests, and build are green;
- UI-visible claims have screenshot or live renderer proof.

## Runtime And AI Acceptance

Runtime/AI is complete only when:

- live audio capture and `MusicState` refresh have one clear ownership path;
- event detection, drop timing, deck context, and deck vision feed the evidence
  spine with uncertainty preserved;
- co-host speech resolves through citations/evidence or honest uncertainty;
- AI-message observability records live coach, Learn tutor, bench/debrief, and
  relevant agent surfaces in one queryable stream;
- Vibe Judge voice lines are grounded and survive the production slop filter;
- TTS chain shutdown, local TTS fallback, and external TTS providers are tested
  without leaking sessions;
- no hardcoded model names bypass the model router.

## Learn Acceptance

Learn is complete only when:

- live evidence can feed tutor context and mastery credit;
- earned/mastered states require real cited producers;
- Beatmatch Judge either has a live producer or the false-mastered pin remains;
- Learn tutor speech appears in AI-message observability;
- debrief drills can feed practice suggestions or are explicitly deferred;
- Learn UI and Learn runtime use the same IPC/evidence discipline as the rest of
  the app;
- excluded beginner/GSD suites remain excluded unless the user explicitly opens
  that lane.

## Library, Cue, And Viber Acceptance

Library/cue/Viber is complete only when:

- CLAP search and ranking have real eval coverage;
- cue provenance preserves source, number, label, timing, and risk;
- Rekordbox/XML, M3U8, Serato/Mixxx, and Viber exports are each proven or
  explicitly deferred;
- cue agreement weak labels have a producer and storage/privacy story before any
  flywheel claim;
- Viber tools preserve grounded discovery and web-search/fetch provenance;
- no cue/export path silently mutates user files without explicit opt-in.

## Install, Release, And Packaging Acceptance

Install/release is complete only when:

- Python, npm, and Cargo dependency graphs are conflict-checked;
- optional extras are truthful and installable;
- sidecar freshness and binary verification run in the package path;
- signing/notarization have dry-run and real-artifact proof before release;
- one-click install path is verified on the accepted platform target;
- local model downloads have size, license, checksum, and cache behavior
  documented;
- generated artifacts are reproducible or intentionally ignored.
- final accepted work is on `main` with the release/build path documented.

## Docs And Memory Acceptance

Docs are complete only when:

- old handoffs from yesterday/today are read and classified;
- stale demo plans are marked demo-only or superseded;
- design screenshots/mockups are tied to production status;
- package checklist and capability ledger agree;
- public claims do not exceed verified capabilities;
- old "fully open-source" positioning is removed, narrowed, or replaced with the
  current monetized-product story;
- the final README/contributor docs point to the new clean architecture instead
  of the dirty-tree transition docs.

## Codex Final Verification Packet

Claude hands Codex this when it believes the rebuild is complete:

```text
Final rebuild verifier packet

Repo state:
- branch:
- head commit:
- package-checker output:
- dirty status:

Capability ledger:
- unknown rows:
- integrated rows:
- deferred rows:
- dropped rows:

Frontend proof:
- commands:
- screenshots/live renderer proof:

Runtime/AI proof:
- commands:
- ws/log/session evidence:

Learn proof:
- commands:
- evidence flow:

Library/cue/Viber proof:
- commands:
- eval/export proof:

Install/release proof:
- commands:
- artifact/signing/install evidence:

Docs sweep:
- old docs read:
- superseded docs:
- remaining docs:

Known deferrals:
- item:
- rationale:
- gate:

Request:
Codex, independently verify final acceptance. Reject if any capability, file,
doc, test, frontend surface, install path, or public claim is unclassified,
unwired, stale, or unproven.
```
