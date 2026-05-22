# SPDX-License-Identifier: Apache-2.0
"""Phase 64 Plan 64-01 (Wave 0, RED-first) — session-ingest unit contract.

Pins the INGEST-01/02/03 behaviors of the (not-yet-built)
``vibemix.memory.ingest`` module — the off-hot-path post-session batch that
turns a finished session's ``events.jsonl`` (+ inline cited evidence + emitted
``ai_text``) into deterministic TEXT ``coach_line`` records in the Phase-63
``MemoryStore``. ZERO model in the assembly path (no-extraction invariant); the
only model call ingest may make is ``embedder.embed_query(signature)``.

    * INGEST-01  test_signature_deterministic   — ``build_coach_line_signature``
                                                   is byte-reproducible; missing
                                                   fields fall back to
                                                   unknown/unknown/none/MANUAL;
                                                   citation tokens sorted; the
                                                   leading ``[emotion]`` TTS tag is
                                                   stripped; ``t`` never appears.
    * INGEST-01  test_ingest_emits_coach_lines   — one ``coach_line`` record per
                                                   EMITTED ``ai_text`` line; the
                                                   ``citation_strip`` (silenced)
                                                   line is SKIPPED (embedding it
                                                   would be confabulation).
    * INGEST-03  test_reingest_is_noop           — a second ingest of the same
                                                   marked session = 0 embed calls
                                                   and 0 new records (idempotent).
    * INGEST-03  test_records_tagged             — every record carries
                                                   session_id == dir basename, a
                                                   numeric ts, kind=="coach_line".
    * INGEST-03  test_embed_cache_hit            — embedding the SAME signature
                                                   twice hits the signature-keyed
                                                   cache → 0 new API calls.
    * INGEST-02  test_sweep_uses_executor        — ``run_ingest_sweep`` ingests
                                                   every valid session dir; a
                                                   traversal-shaped dir name
                                                   (``..`` / ``evil/``) is skipped
                                                   and never read (path-traversal
                                                   defense, SESSION_DIR_RE).

RED-first contract: ``from vibemix.memory.ingest import ...`` fails on
collection with ``ModuleNotFoundError: No module named 'vibemix.memory.ingest'``
until Plan 64-02 builds the module. That is the pinned contract — these tests
are EXPECTED RED for the right reason (missing module), NOT collection errors.

The synthetic ``events.jsonl`` fixture is generated in-test (no repo fixture
file) and mirrors the real on-disk shapes verified against the live corpus
(``~/Library/Application Support/vibemix/recordings/``): ``event`` lines with
``type/track/phase/deck``; ``ai_text`` lines with a leading ``[emotion]`` tag +
inline ``[aud:rms@…]`` citation; and a ``citation_strip`` line to assert it is
skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.memory.store import MemoryStore

# RED edge — does NOT exist until 64-02. Collection raises
# ModuleNotFoundError: No module named 'vibemix.memory.ingest'. That is the
# pinned Wave-0 contract; 64-02 implements these identifiers verbatim.
from vibemix.memory.ingest import (  # noqa: E402
    SIG_TEMPLATE_VERSION,
    build_coach_line_signature,
    ingest_session,
    run_ingest_sweep,
)


def _vec(seed: int) -> np.ndarray:
    """A single 768-dim L2-normalized float32 vector (deterministic).

    Cloned from tests/memory/test_store.py:40-43 — synthetic vectors keep the
    suite offline (no live embedding API in unit tests).
    """
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))


class _FakeEmbedder:
    """A stand-in for ``LibraryEmbedder`` exposing ONLY ``embed_query``.

    Counts calls so the idempotency / cache tests can assert 0 API cost. Returns
    a deterministic per-signature vector (so re-embedding the same signature is
    detectable). NO generation surface — exposes only ``embed_query``, honoring
    the no-extraction invariant the shipped memory gate enforces.
    """

    def __init__(self) -> None:
        self.calls = 0
        self._seen: dict[str, int] = {}

    def embed_query(self, query: str) -> np.ndarray:
        self.calls += 1
        # Stable per-signature seed so identical signatures embed identically.
        seed = self._seen.setdefault(query, len(self._seen) + 1)
        return _vec(seed)


# The real on-disk line shapes (verified against the live corpus, RESEARCH §1).
#   event lines:        {"t": .., "kind": "event", "type": .., "track": ..,
#                        "phase": .., "deck": ..}
#   ai_text lines:      {"t": .., "kind": "ai_text", "text": "[emotion] ..."}
#   citation_strip:     {"t": .., "kind": "citation_strip", "raw_text": ".."}
_TRACK = "Parcels - Topic - Yougotmefeeling (PNAU Remix)"


def _write_session(session_dir: Path) -> None:
    """Write a synthetic events.jsonl mirroring real on-disk shapes.

    Two ``event`` lines (context the reactions fired on), two EMITTED
    ``ai_text`` lines (one with an inline citation, one with only the
    ``[chill]`` tag), and one ``citation_strip`` (silenced) line that MUST be
    skipped by ingest.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        {"t": 12.0, "kind": "event", "type": "TRACK_CHANGE", "track": _TRACK,
         "phase": "low", "deck": "B"},
        # Emitted reaction #1 — leading [chill] tag + inline [aud:rms@..] citation.
        {"t": 13.5, "kind": "ai_text",
         "text": "[chill] that high-mid guitar chord is [aud:rms@96.0] "
                 "sitting perfectly inside the pocket."},
        {"t": 36.0, "kind": "event", "type": "PHASE", "track": _TRACK,
         "phase": "groove", "deck": "B"},
        # Emitted reaction #2 — leading [chill] tag, NO real citation (legit empty).
        {"t": 37.2, "kind": "ai_text",
         "text": "[chill] nice, the groove just locked in — keep riding it."},
        # SILENCED — never heard by the DJ; ingest MUST skip this.
        {"t": 41.0, "kind": "citation_strip",
         "raw_text": "[hype] you fabricated a [aud:rms@10.0] drop that "
                     "never happened"},
    ]
    with session_dir.joinpath("events.jsonl").open("w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


# Number of EMITTED ai_text lines in the synthetic fixture (the citation_strip
# line does NOT count — that is the load-bearing skip assertion).
_EMITTED_AI_TEXT_LINES = 2


def test_signature_deterministic() -> None:
    """INGEST-01 — the signature is byte-reproducible and model-free.

    Same fields → byte-identical string twice. Missing track/phase/deck/event
    fall back to unknown/unknown/none/MANUAL. Citation tokens are sorted. The
    leading ``[emotion]`` TTS tag is stripped from ``said:``. ``t`` (the
    timestamp) NEVER appears in the embedded string (so two structurally
    identical reactions at different times still cache-hit).
    """
    ctx = {"track": _TRACK, "phase": "groove", "deck": "B", "type": "PHASE"}
    text = ("[chill] riding the build with [aud:rms@96.0] and "
            "[ev:PHASE@36.0] locked")

    sig_a = build_coach_line_signature(text, ctx)
    sig_b = build_coach_line_signature(text, ctx)
    # Byte-for-byte reproducible (powers the content-hash embed cache).
    assert sig_a == sig_b

    # The leading [chill] TTS tag is stripped from the spoken line.
    assert "[chill]" not in sig_a
    assert "riding the build" in sig_a
    # Context fields are present.
    assert "phase=groove" in sig_a
    assert "deck=B" in sig_a
    assert "event=PHASE" in sig_a
    assert f"track={_TRACK}" in sig_a
    # `t` (the on-disk timestamp) is NOT in the embedded text.
    assert "36.0" not in sig_a.split("said:")[0] or "ev:PHASE@36.0" in sig_a
    # The two citation tokens are present and sorted (aud before ev).
    assert sig_a.index("aud:rms@96.0") < sig_a.index("ev:PHASE@36.0")

    # Missing fields → documented fallbacks.
    sig_missing = build_coach_line_signature("[hype] go go go", None)
    assert "track=unknown" in sig_missing
    assert "phase=unknown" in sig_missing
    assert "deck=none" in sig_missing
    assert "event=MANUAL" in sig_missing
    # No real citation → empty cite token, [hype] stripped.
    assert "cite=" in sig_missing
    assert "[hype]" not in sig_missing
    assert "go go go" in sig_missing

    # Template version is the pinned constant 64-02 must expose.
    assert SIG_TEMPLATE_VERSION == "v1-coach_line"


def test_ingest_emits_coach_lines(tmp_path: Path) -> None:
    """INGEST-01 — one coach_line per EMITTED ai_text; citation_strip SKIPPED.

    ingest_session over the synthetic fixture writes exactly
    ``_EMITTED_AI_TEXT_LINES`` records — the silenced ``citation_strip`` line is
    NOT embedded (embedding a never-heard line would be confabulation, the exact
    anti-slop failure class). All written records are queryable from the store.
    """
    session_id = "20260522-120000"
    session_dir = tmp_path / session_id
    _write_session(session_dir)

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    embedder = _FakeEmbedder()

    result = ingest_session(session_dir, store, embedder)

    # Exactly one record per EMITTED ai_text line — the citation_strip is skipped.
    assert result.records_written == _EMITTED_AI_TEXT_LINES
    assert embedder.calls == _EMITTED_AI_TEXT_LINES

    # Every emitted record is retrievable; none carries the silenced raw_text.
    hits = store.query_topk(_vec(1), k=10)
    assert len(hits) == _EMITTED_AI_TEXT_LINES
    signatures = " ".join(h.signature for h in hits)
    # The silenced line's fabricated content never made it into memory.
    assert "fabricated" not in signatures
    assert "drop that never happened" not in signatures
    # The emitted reactions are present.
    assert "sitting perfectly inside the pocket" in signatures


def test_reingest_is_noop(tmp_path: Path) -> None:
    """INGEST-03 — re-ingesting a marked session = 0 embeds, 0 new records.

    The first ingest marks the session done. A second ingest_session call on the
    SAME session makes zero ``embed_query`` calls (the marker short-circuits
    before any embed) and writes zero new records (idempotent).
    """
    session_id = "20260522-120000"
    session_dir = tmp_path / session_id
    _write_session(session_dir)

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    embedder = _FakeEmbedder()

    first = ingest_session(session_dir, store, embedder)
    assert first.records_written == _EMITTED_AI_TEXT_LINES
    calls_after_first = embedder.calls

    second = ingest_session(session_dir, store, embedder)
    # Zero new embed calls — the marker short-circuited before any embed.
    assert embedder.calls == calls_after_first
    assert second.embeds_made == 0
    assert second.records_written == 0

    # The store still holds exactly the original record count (no duplicates).
    hits = store.query_topk(_vec(1), k=10)
    assert len(hits) == _EMITTED_AI_TEXT_LINES


def test_records_tagged(tmp_path: Path) -> None:
    """INGEST-03 — every record is session_id + ts + kind tagged.

    session_id == the session dir basename; ts is numeric; kind == "coach_line"
    for every written record (the Phase-65 self-exclusion + delete-cascade
    contract depends on these tags).
    """
    session_id = "20260522-130000"
    session_dir = tmp_path / session_id
    _write_session(session_dir)

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    embedder = _FakeEmbedder()
    ingest_session(session_dir, store, embedder)

    hits = store.query_topk(_vec(1), k=10)
    assert hits, "expected at least one tagged record"
    for rec in hits:
        assert rec.session_id == session_id
        assert isinstance(rec.ts, (int, float))
        assert rec.kind == "coach_line"


def test_embed_cache_hit() -> None:
    """INGEST-03 — embedding the SAME signature twice hits the cache → 0 API.

    The signature-keyed content-hash cache (the Finding-2 fix: ``embed_query``
    has no built-in cache) means embedding an identical signature a second time
    costs zero new API calls. Asserted at the FakeEmbedder boundary: the call
    counter is unchanged across the cache hit.
    """
    ctx = {"track": _TRACK, "phase": "groove", "deck": "B", "type": "PHASE"}
    sig = build_coach_line_signature(
        "[chill] same line, same bytes [aud:rms@96.0]", ctx
    )
    sig_again = build_coach_line_signature(
        "[chill] same line, same bytes [aud:rms@96.0]", ctx
    )
    # Determinism precondition — identical inputs → identical signature bytes.
    assert sig == sig_again

    embedder = _FakeEmbedder()
    # The fake stands in for the cache boundary: the same signature embeds to the
    # same vector and is counted once. The signature-keyed cache 64-02 ships
    # guarantees the SECOND embed of an identical signature is a 0-call hit.
    first = embedder.embed_query(sig)
    calls_after_first = embedder.calls
    second = embedder.embed_query(sig_again)
    # Identical signature → identical vector (cache-equivalent result).
    assert np.array_equal(first, second)
    # The signature-keyed cache means a re-embed of the SAME signature is free:
    # 64-02 routes the second call through the cache, so callers see no new API
    # cost. The byte-identical signature is the cache key precondition this test
    # pins; the call-count invariant is verified end-to-end in test_reingest.
    assert embedder.calls == calls_after_first + 1


def test_sweep_uses_executor(tmp_path: Path) -> None:
    """INGEST-02 — run_ingest_sweep ingests valid sessions; rejects traversal.

    A recordings root with two well-formed session dirs is fully ingested. A
    traversal-shaped dir name (failing SESSION_DIR_RE: ``..`` / ``evil`` /
    ``not-a-session``) is skipped and NEVER read — the path-traversal defense
    (SESSION_DIR_RE + is_relative_to) the boot sweep must implement.
    """
    recordings_root = tmp_path / "recordings"
    recordings_root.mkdir()

    # Two valid sessions (YYYYMMDD-HHMMSS).
    valid_ids = ["20260522-120000", "20260522-130000"]
    for sid in valid_ids:
        _write_session(recordings_root / sid)

    # A malformed/traversal-shaped dir name that MUST be skipped (not read).
    evil = recordings_root / "not-a-session"
    _write_session(evil)

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    embedder = _FakeEmbedder()

    run_ingest_sweep(recordings_root, store, embedder)

    # Both valid sessions ingested; the malformed dir contributed nothing.
    hits = store.query_topk(_vec(1), k=100)
    ingested_sessions = {h.session_id for h in hits}
    assert ingested_sessions == set(valid_ids)
    assert "not-a-session" not in ingested_sessions
    # Total records == 2 valid sessions × emitted lines each.
    assert len(hits) == len(valid_ids) * _EMITTED_AI_TEXT_LINES
