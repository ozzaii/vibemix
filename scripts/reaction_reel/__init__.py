# SPDX-License-Identifier: Apache-2.0
"""Phase 17 — Reaction-reel slop grading harness.

Two CLI scripts:

* ``grade.py`` — blind-grade one rater's session. Reads ``events.jsonl``,
  builds anonymized reaction clip-cards, plays the AI voice from
  ``voice.wav`` for each reaction, prompts the rater for score + flags,
  writes ``<session>/grades/<rater>.jsonl`` incrementally.

* ``analyze.py`` (Plan 17-03) — aggregates all ``<rater>.jsonl`` files into
  a single ``report.md`` + ``scores.csv`` with pass/fail verdict against the
  rubric.

Plans 17-02 + 17-03 ship both scripts; the full pipeline is
``grade.py`` → ``<rater>.jsonl × N`` → ``analyze.py`` → ``report.md`` +
``scores.csv``.
"""
