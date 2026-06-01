# SPDX-License-Identifier: Apache-2.0
"""Session-ingest — the off-hot-path post-session batch (Phase 64, v6.0).

Reads a finished session's ``events.jsonl`` and turns each EMITTED ``ai_text``
reaction into ONE deterministic TEXT ``coach_line`` record in the Phase-63
``MemoryStore``. The silenced ``citation_strip`` lines are SKIPPED — embedding a
reaction the DJ never heard would be confabulation (the exact anti-slop failure
class this milestone exists to close).

Hard invariants (64-CONTEXT / 64-RESEARCH / 64-PATTERNS):

    * ONE kind only: ``coach_line`` (no ``moment``/``audio_moment``).
    * ``build_coach_line_signature`` is a PURE deterministic string assembly —
      regex + string ops only. NO genai client, NO generation/chat call, NO I/O.
      The ingest path's ONLY model call is ``embedder.embed_query(signature)``.
      (The shipped static no-extraction gate globs ``memory/*.py`` → covers this
      module; the new ingest-dormancy subprocess gate proves no live-path leak.)
    * Idempotency is TWO layers (Finding 2): a ``memory_ingested`` marker (skip
      the whole session) + a signature-keyed content-hash embed cache (skip the
      API call even on a marker loss / template bump). Re-ingest = 0 embeds, 0
      new records.
    * A4 marker↔retention coupling — solved WITHOUT editing Phase-63 code: the
      idempotency short-circuit is gated on BOTH the marker row (with a matching
      ``SIG_TEMPLATE_VERSION``) AND ``COUNT(*) FROM moments WHERE session_id=?``
      > 0, so a retention-evicted session (0 moments) re-ingests even though its
      stale marker survives.
    * MIRROR, don't import: the ~12-line malformed-tolerant JSONL read is
      re-implemented here (no 5-min ``SessionTooShort`` floor); ``SESSION_DIR_RE``
      + ``is_relative_to(root.resolve())`` are copied for the sweep path defense.
    * No live-path import: this module imports NO coach loop / MusicState /
      ws_bus / agent / prompts. Any ``vibemix.runtime`` import is FUNCTION-LOCAL
      (mirrors ``store.py``'s lazy ``app_data_dir`` import) so the dormancy gate
      prints CLEAN.

Runtime wiring (``run_in_executor`` enqueue at session-close / boot) is Wave 3
(64-03); this module only exposes ``ingest_session`` + ``run_ingest_sweep`` for
that wiring to call. Both are pure / executor-safe (no asyncio, no live state).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.memory.store import MemoryStore
from vibemix.state.deck_context import normalize_audio_window_context_text

logger = logging.getLogger(__name__)

__all__ = [
    "SIG_TEMPLATE_VERSION",
    "IngestResult",
    "build_coach_line_signature",
    "ingest_session",
    "run_ingest_sweep",
]


# ─── Locked constants ──────────────────────────────────────────────────────────

# Bump to re-embed ALL signatures if the template changes (mirrors embed.py's
# EXCERPT_STRATEGY_VERSION). Flows into the embed-cache key SHA256 + the
# memory_ingested marker's sig_template_version column.
SIG_TEMPLATE_VERSION = "v9-coach_line-deck-audio-context"

# COPIED VERBATIM from state/evidence_registry.py:133 — the LOCKED citation
# grammar. lock-step source-of-truth: state/evidence_registry.py:133 (keep in
# sync; copied rather than imported to keep ingest.py's import surface minimal
# and unambiguously gate-clean — RESEARCH A5).
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|key"
_INNER_ATOM = rf"(?:{_SOURCE_ALT}):[^\s,\]]+"
EVIDENCE_CITATION_RE: re.Pattern[str] = re.compile(rf"\[{_INNER_ATOM}(?:,{_INNER_ATOM})*\]")

# The leading ``[chill]`` / ``[hype]`` TTS directive — NOT a citation (no
# ``source:`` colon-form). Stripped from the embedded reaction text so the
# signature is the actual spoken line.
_EMOTION_TAG_RE: re.Pattern[str] = re.compile(r"^\[[a-z]+\]\s*")
_UNTRUSTED_AUDIO_WINDOW = "omitted_untrusted_audio_window"
_AUDIO_WINDOW_DECK_A_RE = re.compile(r"\bdeckA_audio=(P[2-9][0-9]?)\b")
_AUDIO_WINDOW_DECK_B_RE = re.compile(r"\bdeckB_audio=(P[2-9][0-9]?)\b")
_AUDIO_WINDOW_FORBIDDEN_ATOMS = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
)


# ─── Pure signature builder (NO model, NO I/O) ──────────────────────────────────


def build_coach_line_signature(reaction_text: str, ctx: dict | None) -> str:
    """Assemble the deterministic, byte-reproducible ``coach_line`` signature.

    PURE: regex + string assembly only — no genai client, no generation call,
    no I/O. Same artifacts → same bytes → same content-hash → 0-cost re-embed.

    Template (64-RESEARCH §Signature Template Spec, implement verbatim)::

        coach_line | track={track} | phase={phase} | deck={deck}
            | event={event_type} | context_feed={context_feed_contract}
            | deck_lane={deck_lane_context}
            | deck_ref={deck_reference_context} | deck_source={deck_source_context}
            | deck_audio={deck_audio_context}
            | deck_audio_separation={deck_audio_separation_context}
            | deck_audio_features={deck_audio_features_context}
            | deck_audio_delta={deck_audio_delta_context}
            | deck_audio_window={deck_audio_window_context}
            | audio_window={audio_window_context}
            | live_evidence={live_evidence_context}
            | move={move_context} | move_effect={move_effect_context}
            | audio_delta={audio_delta} | cite={citation_tokens}
            | said: {reaction_text}

    Field rules:
        * ``track`` / ``phase`` from the nearest preceding ``event`` line;
          missing → ``unknown``.
        * ``deck`` missing → ``none``.
        * ``event_type`` missing → ``MANUAL``.
        * ``citation_tokens`` = ``EVIDENCE_CITATION_RE`` matches with the outer
          brackets stripped, SORTED, ``,``-joined; legitimately empty for the
          common ``[chill]``-only lines.
        * ``reaction_text`` = the line with its leading ``[emotion]`` TTS tag
          stripped.
        * ``t`` (the on-disk timestamp) NEVER appears in the embedded string —
          it goes into the ``MemoryStore`` ``ts`` column (metadata), so two
          structurally-identical reactions at different times still cache-hit.
    """
    ctx = ctx or {}
    track = ctx.get("track") or "unknown"
    phase = ctx.get("phase") or "unknown"
    deck = ctx.get("deck") or "none"
    etype = ctx.get("type") or "MANUAL"
    context_feed = _ctx_field(ctx.get("context_feed_contract"), cap=420)
    deck_lane = _ctx_field(ctx.get("deck_lane_context"))
    deck_ref = _ctx_field(ctx.get("deck_reference_context"))
    deck_source = _ctx_field(ctx.get("deck_source_context"))
    deck_audio = _ctx_field(ctx.get("deck_audio_context"))
    deck_audio_separation = _ctx_field(ctx.get("deck_audio_separation_context"))
    deck_audio_features = _ctx_field(ctx.get("deck_audio_features_context"))
    deck_audio_delta = _ctx_field(ctx.get("deck_audio_delta_context"))
    deck_audio_window = _ctx_field(ctx.get("deck_audio_window_context"))
    audio_window = _audio_window_ctx_field(ctx.get("audio_window_context"))
    live_evidence = _ctx_field(ctx.get("live_evidence_context"), cap=640)
    move_context = _ctx_field(ctx.get("move_context"))
    move_effect = _ctx_field(ctx.get("move_effect_context"))
    audio_delta = _ctx_field(ctx.get("audio_delta"))
    # Sorted so a re-ordering in the text can never change the hash (defensive;
    # in practice text order is stable). strip("[]") drops the outer brackets.
    cites = sorted(m.group(0).strip("[]") for m in EVIDENCE_CITATION_RE.finditer(reaction_text))
    cite_str = ",".join(cites)
    # Dedupe: the citation tokens already live (sorted) in ``cite=``; strip the
    # inline ``[ev:drop]``/``[track:...]`` brackets from ``said:`` too so a
    # citation is never repeated within the signature and the embedded vector
    # encodes pure spoken language, not machine tokens (IN-01). Deterministic +
    # order-stable: regex sub over a fixed grammar → same input, same bytes.
    said = EVIDENCE_CITATION_RE.sub("", _EMOTION_TAG_RE.sub("", reaction_text)).strip()
    return (
        f"coach_line | track={track} | phase={phase} | deck={deck} "
        f"| event={etype} | context_feed={context_feed} "
        f"| deck_lane={deck_lane} | deck_ref={deck_ref} "
        f"| deck_source={deck_source} "
        f"| deck_audio={deck_audio} "
        f"| deck_audio_separation={deck_audio_separation} "
        f"| deck_audio_features={deck_audio_features} "
        f"| deck_audio_delta={deck_audio_delta} "
        f"| deck_audio_window={deck_audio_window} "
        f"| audio_window={audio_window} "
        f"| live_evidence={live_evidence} | move={move_context} "
        f"| move_effect={move_effect} | audio_delta={audio_delta} "
        f"| cite={cite_str} | said: {said}"
    )


def _ctx_field(value: object, *, cap: int = 240) -> str:
    """Render bounded event-context metadata for deterministic signatures."""
    if isinstance(value, (list, tuple)):
        raw = "; ".join(str(item) for item in value[:4] if item)
    else:
        raw = str(value) if value else ""
    raw = " ".join(raw.split()).replace("|", "/")
    return raw[:cap] if raw else "none"


def _audio_window_ctx_field(value: object, *, cap: int = 240) -> str:
    rendered = _ctx_field(value, cap=900)
    if rendered == "none":
        return "none"
    trusted = normalize_audio_window_context_text(rendered, max_len=900)
    if trusted:
        return _ctx_field(trusted, cap=cap)
    if _audio_window_context_is_untrusted(rendered):
        return _UNTRUSTED_AUDIO_WINDOW
    return _ctx_field(rendered, cap=cap)


def _audio_window_context_is_untrusted(text: str) -> bool:
    if "audio_window_context[" not in text:
        return False
    if any(atom in text for atom in _AUDIO_WINDOW_FORBIDDEN_ATOMS):
        return True
    deck_a = _AUDIO_WINDOW_DECK_A_RE.search(text)
    deck_b = _AUDIO_WINDOW_DECK_B_RE.search(text)
    if deck_a or deck_b:
        return not (deck_a and deck_b) or deck_a.group(1) == deck_b.group(1)
    return "per_deck_audio=deck_pair_parts" in text


# ─── Malformed-tolerant JSONL reader (MIRROR of session_loader._read_events) ────


def _read_events_jsonl(events_jsonl_path: Path) -> list[dict]:
    """Parse events.jsonl into a list of dicts; skip malformed lines.

    Mirrors ``debrief/session_loader.py:74-88`` — per-line ``json.loads`` with
    skip-on-error (T-64-04: a crash-truncated last line never blocks ingest).
    Deliberately does NOT inherit the 5-min ``SessionTooShort`` floor: ingest
    has no minimum-duration UX gate. NOT imported (Mirror not import, RESEARCH
    Open Q2).
    """
    events: list[dict] = []
    with events_jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.warning("[ingest] events.jsonl line %d malformed: %s", line_no, e)
                continue
            if isinstance(obj, dict):
                events.append(obj)
    return events


# ─── Path-traversal defense (COPIED from recordings_index.py) ───────────────────

# COPIED VERBATIM from runtime/recordings_index.py:78 — the V12 path-traversal
# gate shape (YYYYMMDD-HHMMSS). Mirrored (not imported) to keep the live-path
# import surface clean; pairs with the is_relative_to containment check in
# run_ingest_sweep.
SESSION_DIR_RE: re.Pattern[str] = re.compile(r"^\d{8}-\d{6}$")


def _session_dir_is_safe(name: str, recordings_root: Path) -> bool:
    """Two-layer path-traversal gate (COPY of recordings_index.py:388-401).

    1. shape: ``SESSION_DIR_RE`` (``YYYYMMDD-HHMMSS``) — rejects ``..`` /
       ``evil`` / ``not-a-session`` BEFORE any read.
    2. containment: resolve as a child of ``recordings_root`` and assert it
       stays inside (symlink-escape-proof); refuse the root itself.
    """
    if not isinstance(name, str) or not SESSION_DIR_RE.match(name):
        return False
    try:
        target = (recordings_root / name).resolve()
        root_resolved = recordings_root.resolve()
    except OSError:
        return False
    if not target.is_relative_to(root_resolved):
        return False
    if target == root_resolved:
        return False
    return True


# ─── Idempotency + embed-cache sqlite layer (owned by ingest, sibling DBs) ──────


def _ingest_db_path(store: MemoryStore) -> Path:
    """Resolve the ingest-owned sqlite DB path (marker + embed cache).

    A sibling of the store's ``memory.db`` so it lives in the same dir (durable
    ``app_data_dir()`` in production; the test's ``tmp_path`` in tests) and is
    isolated per-install. We own this connection — we do NOT reuse the store's
    backend connection (that would couple to Phase-63 internals; the marker +
    cache are a Phase-64 concern).
    """
    return store._db_path.parent / "memory_ingest.db"


def _open_ingest_db(store: MemoryStore) -> sqlite3.Connection:
    """Open the ingest sqlite DB and ensure both tables exist (idempotent)."""
    db_path = _ingest_db_path(store)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    # memory_ingested marker (RESEARCH §idempotency marker schema; mirrors
    # store.py's CREATE TABLE IF NOT EXISTS idiom).
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory_ingested ("
        "session_id           TEXT PRIMARY KEY, "
        "ingested_at          REAL NOT NULL, "
        "sig_template_version TEXT NOT NULL"
        ")"
    )
    # embed_cache — CLONE of embed.py:146-157 (shape verbatim). Lives in the
    # memory layer; library/embed.py is UNMODIFIED.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS embed_cache ("
        "key TEXT PRIMARY KEY, "
        "vector BLOB NOT NULL, "
        "ts REAL NOT NULL"
        ")"
    )
    conn.commit()
    return conn


def _embed_cache_key(signature: str, model_id: str) -> str:
    """SHA256(signature || model_id || SIG_TEMPLATE_VERSION) — Finding 2.

    The signature-keyed content-hash key: an identical signature embedded under
    the same model + template version re-uses the cached vector at 0 API cost.
    ``model_id`` is the probe-derived ``embedder._model`` — NEVER a literal.
    """
    h = hashlib.sha256()
    h.update(signature.encode())
    h.update(b"||")
    h.update(model_id.encode())
    h.update(b"||")
    h.update(SIG_TEMPLATE_VERSION.encode())
    return h.hexdigest()


def _cache_get(conn: sqlite3.Connection, key: str) -> np.ndarray | None:
    """Round-trip clone of embed.py:605-612."""
    row = conn.execute("SELECT vector FROM embed_cache WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return np.frombuffer(row[0], dtype=np.float32).copy()


def _cache_put(conn: sqlite3.Connection, key: str, vector: np.ndarray) -> None:
    """Round-trip clone of embed.py:614-623."""
    assert vector.dtype == np.float32 and vector.shape == (EMBEDDING_DIM,)
    conn.execute(
        "INSERT OR REPLACE INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
        (key, vector.tobytes(), time.time()),
    )
    conn.commit()


def _marker_present(conn: sqlite3.Connection, session_id: str) -> bool:
    """True iff a memory_ingested row exists with a MATCHING template version.

    A ``sig_template_version`` mismatch forces re-ingest (the template changed).
    """
    row = conn.execute(
        "SELECT 1 FROM memory_ingested WHERE session_id = ? AND sig_template_version = ?",
        (session_id, SIG_TEMPLATE_VERSION),
    ).fetchone()
    return row is not None


def _write_marker(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO memory_ingested "
        "(session_id, ingested_at, sig_template_version) VALUES (?, ?, ?)",
        (session_id, time.time(), SIG_TEMPLATE_VERSION),
    )
    conn.commit()


def _session_has_moments(store: MemoryStore, session_id: str) -> bool:
    """COUNT(*) FROM moments WHERE session_id=? > 0 — the A4 reconciliation.

    The idempotency short-circuit requires BOTH the marker AND live moments, so
    a retention-evicted session (whose moments are gone but whose marker may
    survive) re-ingests. Reads the store's moments connection directly (a cheap
    read; ``store.delete_session`` is UNMODIFIED).
    """
    row = store._moments.execute(
        "SELECT COUNT(*) FROM moments WHERE session_id = ?", (session_id,)
    ).fetchone()
    return bool(row and row[0] > 0)


# ─── Result type ────────────────────────────────────────────────────────────────


@dataclass
class IngestResult:
    """Outcome of one ``ingest_session`` call.

    ``records_written`` / ``embeds_made`` are both 0 on the idempotent
    short-circuit (the 0-cost re-ingest invariant the contract pins).
    """

    session_id: str
    records_written: int = 0
    embeds_made: int = 0
    skipped: bool = False


# ─── ingest_session ──────────────────────────────────────────────────────────────


def ingest_session(
    session_dir: Path,
    store: MemoryStore,
    embedder,
) -> IngestResult:
    """Ingest one finished session into ``store`` (idempotent, executor-safe).

    Flow:
        1. Guard: ``session_dir`` is a dir AND ``events.jsonl`` exists (mirror
           session_loader.py:130-136).
        2. Idempotency short-circuit: marker present (matching template version)
           AND the session already has moments rows → 0 embeds, 0 writes (A4 —
           the moments-count gate lets an evicted session re-ingest WITHOUT
           touching Phase-63 ``delete_session``).
        3. For each EMITTED ``ai_text`` line (kind=="ai_text"; SKIP
           ``citation_strip`` — the silenced/never-heard lines), find the
           nearest preceding ``event`` line for context, build the signature,
           embed it cache-guarded, and ``store.add_record`` it as a
           ``coach_line`` tagged session_id + ts.
        4. Write the ``memory_ingested`` marker last.

    Returns an ``IngestResult``.
    """
    session_dir = Path(session_dir)
    if not session_dir.is_dir():
        logger.info("[ingest] not a directory, skipping: %s", session_dir)
        return IngestResult(session_id=session_dir.name, skipped=True)

    events_jsonl = session_dir / "events.jsonl"
    if not events_jsonl.exists():
        logger.info("[ingest] no events.jsonl, skipping: %s", session_dir)
        return IngestResult(session_id=session_dir.name, skipped=True)

    session_id = session_dir.name
    conn = _open_ingest_db(store)
    try:
        # A4: marker AND live moments both required to skip — so an evicted
        # session (0 moments) re-ingests despite a surviving marker.
        if _marker_present(conn, session_id) and _session_has_moments(store, session_id):
            logger.debug(
                "[ingest] %s already ingested (marker + moments) — skip",
                session_id,
            )
            return IngestResult(session_id=session_id, skipped=True)

        events = _read_events_jsonl(events_jsonl)
        # Model id is the cache-key model component. A stand-in embedder that
        # exposes only ``embed_query`` (no ``_model``) namespaces to "" — its
        # signatures still cache by text+version, just under a stable empty
        # model component.
        model_id = getattr(embedder, "_model", "") or ""

        records_written = 0
        embeds_made = 0
        seq = 0
        ctx: dict | None = None  # nearest preceding `event` line context

        for ev in events:
            kind = ev.get("kind")
            if kind == "event":
                ctx = {
                    "track": ev.get("track"),
                    "phase": ev.get("phase"),
                    "deck": ev.get("deck"),
                    "type": ev.get("type"),
                    "context_feed_contract": ev.get("context_feed_contract"),
                    "deck_lane_context": ev.get("deck_lane_context"),
                    "deck_reference_context": ev.get("deck_reference_context"),
                    "deck_source_context": ev.get("deck_source_context"),
                    "deck_audio_context": ev.get("deck_audio_context"),
                    "deck_audio_separation_context": ev.get(
                        "deck_audio_separation_context"
                    ),
                    "deck_audio_features_context": ev.get("deck_audio_features_context"),
                    "deck_audio_delta_context": ev.get("deck_audio_delta_context"),
                    "deck_audio_window_context": ev.get("deck_audio_window_context"),
                    "audio_window_context": ev.get("audio_window_context"),
                    "live_evidence_context": ev.get("live_evidence_context"),
                    "move_context": ev.get("move_context"),
                    "move_effect_context": ev.get("move_effect_context"),
                    "audio_delta": ev.get("audio_delta"),
                }
                continue
            if kind != "ai_text":
                # citation_strip (silenced — confabulation if embedded) and any
                # other kind are skipped. Only EMITTED ai_text reaches memory.
                #
                # INTENTIONAL skip — NOT an oversight (IN-02): ``citation_bypass``
                # (dj_cohost.py — the one-shot heard-but-unverified bypass) is a
                # line the DJ *did* hear, yet it is deliberately excluded. The
                # confabulation guard says memory must encode only what was
                # GROUNDED+verified; letting the coach "remember" an unverified
                # utterance would teach it to recall things the audio never
                # justified. Do NOT add ``citation_bypass`` to the embed set.
                continue

            text = ev.get("text") or ""
            signature = build_coach_line_signature(text, ctx)
            key = _embed_cache_key(signature, model_id)
            vector = _cache_get(conn, key)
            if vector is None:
                vector = embedder.embed_query(signature)
                embeds_made += 1
                _cache_put(conn, key, vector)

            record_id = f"{session_id}:{seq}"
            store.add_record(
                record_id,
                session_id,
                float(ev.get("t", 0.0)),
                "coach_line",
                signature,
                vector,
            )
            records_written += 1
            seq += 1

        _write_marker(conn, session_id)
        return IngestResult(
            session_id=session_id,
            records_written=records_written,
            embeds_made=embeds_made,
        )
    finally:
        conn.close()


# ─── run_ingest_sweep (boot sweep — best-effort, path-defended) ─────────────────


def run_ingest_sweep(
    recordings_root: Path,
    store: MemoryStore,
    embedder,
) -> list[str]:
    """Ingest every valid, un-ingested session under ``recordings_root``.

    Best-effort boot sweep (mirror of recordings_index.run_retention_sweep's
    scandir/best-effort shape, :490-524). For each entry:
        * the two-layer path-traversal gate (``SESSION_DIR_RE`` +
          ``is_relative_to``) runs BEFORE any read — a traversal-shaped name is
          skipped and NEVER read (T-64-03);
        * ``ingest_session`` handles its own marker/moments idempotency;
        * one session's failure logs + continues — it never raises, so one bad
          session can never block boot or the others (T-64-04).

    Returns the list of session_ids that wrote ≥1 record this pass.
    """
    recordings_root = Path(recordings_root)
    if not recordings_root.exists() or not recordings_root.is_dir():
        return []

    ingested: list[str] = []
    try:
        entries = list(os.scandir(recordings_root))
    except OSError as e:  # pragma: no cover - root scandir rarely fails
        logger.warning("[ingest] scandir %s failed: %s", recordings_root, e)
        return []

    for entry in entries:
        name = entry.name
        # Path-traversal gate BEFORE touching the entry (no is_dir read on a
        # rejected name).
        if not _session_dir_is_safe(name, recordings_root):
            logger.debug("[ingest] skip non-session dir: %s", name)
            continue
        try:
            if not entry.is_dir():
                continue
            result = ingest_session(Path(entry.path), store, embedder)
            if result.records_written > 0:
                ingested.append(result.session_id)
        except Exception as e:
            logger.warning("[ingest] session %s failed: %s", name, e)
            continue
    return ingested
