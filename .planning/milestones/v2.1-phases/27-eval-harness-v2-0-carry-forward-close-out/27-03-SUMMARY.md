---
phase: 27-eval-harness-v2-0-carry-forward-close-out
plan: 03
subsystem: eval-corpus
tags: [eval-03, corpus, public-domain, git-lfs]
requires:
  - phase: 27
    provides: Plan 27-01 corpus_manifest validator
provides:
  - 6-session skeleton (2 hard_tek + 2 techno + 2 house) under eval/corpus/sessions/
  - eval/corpus/manifest.json passing the diversity gate (33% hard_tek, 3 genres)
  - eval/corpus/LICENSES.md per-session license-record template
  - scripts/eval/source_corpus.py (archive.org / CCMixter / FMA candidate sourcing CLI)
  - scripts/eval/label_corpus.py (curator-note stub for ground-truth labeling)
  - .gitattributes LFS rule for eval/corpus/sessions/**/*.wav
  - 14 corpus-diversity-gate tests
affects:
  - Plan 27-04 (CI gate runs replay_harness against eval/corpus)
  - KAAN-ACTION-LEGAL.md Item 4 (WAV acquisition + labeling)
tech-stack:
  added: []
  patterns:
    - "Skeleton manifest passes diversity gate AS-IS; WAVs land via KAAN-ACTION"
    - "Reproducible sourcing CLI returns candidates for human curation (NEVER auto-downloads)"
    - "Public-domain ONLY: archive.org licenseurl filter + CCMixter CC0/by + FMA Electronic"
requirements-completed:
  - EVAL-03
duration: ~15 min
completed: 2026-05-15
---

# Phase 27 Plan 03: Corpus Skeleton Summary

**Six-session diversity-gate-passing skeleton + reproducible sourcing CLI ready for Kaan's WAV acquisition step. No Kaan recordings, no proprietary tracks — public-domain only.**

## Accomplishments

- 6 session directories created with genre.txt + source.txt + events.jsonl stubs
- eval/corpus/manifest.json declares 6 sessions across 3 genres (33% hard_tek — passes the ≤ 70% cap)
- eval/corpus/LICENSES.md placeholder records (Kaan fills from source_corpus.py output)
- scripts/eval/source_corpus.py: argparse CLI querying archive.org advanced-search + CCMixter API + FMA Electronic. Returns candidates for human review.
- scripts/eval/label_corpus.py: curator-note stub. Real auto-labeling deferred (requires state_refresh_loop + audible_track resolution out of scope).
- .gitattributes routes eval/corpus/sessions/**/*.wav through Git LFS.
- 14 tests covering manifest diversity, validator integration, session structure, LICENSES.md, LFS rule, CLI --help.

## Task Commits
1. `5a7ee8b` feat(27-03)

## Deferred to KAAN-ACTION-LEGAL.md Item 4

WAV file acquisition (~200 MB total). The skeleton passes the diversity gate; PR CI uses [skip-eval] tag until corpus is populated.

## Self-Check: PASSED
- [x] 14 tests pass
- [x] Diversity gate passes via Plan 27-01 validate_manifest
- [x] Git LFS rule in place
- [x] No POC files modified
