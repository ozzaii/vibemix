# SPDX-License-Identifier: Apache-2.0
"""Phase 65 Plan 65-01 (Wave 0, RED-first) — MemoryRecall unit contract.

Pins the RECALL-03/04 behaviors of the (not-yet-built)
``vibemix.memory.retrieval`` module — the event-gated, off-hot-path,
deadline-bounded retrieval seam that turns a track-aware live event into a
short list of past-session ``Record`` moments for the coach prompt to fence.
ZERO generation in the path (no-extraction invariant); the only model call the
service may make is ``embedder.embed_query(query_text)``.

    * RECALL-04  test_heartbeat_never_retrieves   — ``on_event("HEARTBEAT", …)``
                                                     returns ``[]`` AND never
                                                     calls ``embed_query`` (the
                                                     event gate short-circuits
                                                     BEFORE any embed; HEARTBEAT
                                                     is never a retrieval event).
    * RECALL-03  test_below_floor_injects_nothing  — survivors filtered by the
                                                     0.7 cosine floor; a hit
                                                     whose score < floor is
                                                     dropped → ``[]`` → no block.
    * RECALL-03  test_current_session_excluded      — the live session's own
                                                     records are excluded from
                                                     its retrieval
                                                     (``exclude_session=`` is
                                                     threaded through).
    * RECALL-04  test_deadline_miss_injects_nothing — the service-level contract
                                                     the agent relies on: after
                                                     ``clear()`` (the per-turn
                                                     reset that fires when a
                                                     dispatch missed its
                                                     deadline) ``get_latest()``
                                                     is ``[]`` — nothing leaks
                                                     into the next turn.
    * RECALL-04  test_embed_called_once             — a single track-aware
                                                     ``on_event`` triggers
                                                     exactly one
                                                     ``embed_query`` (no
                                                     fan-out / no retry storm).

RED-first contract: ``from vibemix.memory.retrieval import …`` fails on
collection with ``ModuleNotFoundError: No module named
'vibemix.memory.retrieval'`` until Plan 65-03 builds the module. That is the
pinned contract — these tests are EXPECTED RED for the right reason (missing
module), NOT collection errors.

Sibling fixture conventions mirror tests/memory/test_ingest.py: a
``MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)``, a
call-counting ``_FakeEmbedder`` exposing ONLY ``embed_query`` (no generation
surface), and synthetic 768-dim L2-normalized vectors. Cosine score == dot of
two L2-normalized vectors, so we craft a query vector and seed records whose
dot with it is above / below the 0.7 floor on demand — no live API.

NOTE — the shipped static gates already cover this future file (no edit here):
  * tests/memory/test_no_live_path_import.py rglobs ``memory/*.py`` (asserts
    retrieval.py imports no live-reaction-path module).
  * tests/memory/test_no_extraction.py rglobs ``memory/*.py`` (asserts
    retrieval.py calls only ``embed_content``-class surfaces, no generation).
Both auto-cover ``retrieval.py`` the moment Plan 65-03 lands it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.memory.store import MemoryStore

# RED edge — does NOT exist until 65-03. Collection raises
# ModuleNotFoundError: No module named 'vibemix.memory.retrieval'. That is the
# pinned Wave-0 contract; 65-03 implements these identifiers verbatim.
from vibemix.memory.retrieval import (  # noqa: E402
    RECALL_EVENT_GATE,
    RECALL_SIMILARITY_FLOOR,
    RECALL_TOP_K,
    MemoryRecall,
)


# ---------------------------------------------------------------------------
# Synthetic vector helpers — cosine == dot of two L2-normalized vectors.
# ---------------------------------------------------------------------------


def _unit(seed: int) -> np.ndarray:
    """A single 768-dim L2-normalized float32 vector (deterministic)."""
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))


def _aligned(query: np.ndarray, target_cos: float, seed: int) -> np.ndarray:
    """Build a unit vector whose cosine with ``query`` is ~``target_cos``.

    Mixes the query direction with an orthogonal-ish noise component, then
    re-normalizes. ``v = a*query + b*noise_perp`` with ``a = target_cos`` makes
    ``cos(query, v) ≈ target_cos`` after L2-normalization (query is already
    unit, noise_perp is orthogonalized + unit). Used to land records reliably
    above / below the 0.7 floor.
    """
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    # Gram-Schmidt: strip the query component so noise ⟂ query.
    noise = noise - float(np.dot(noise, query)) * query
    noise = l2_normalize(noise)
    a = float(target_cos)
    b = float(np.sqrt(max(0.0, 1.0 - a * a)))
    return l2_normalize(a * query + b * noise)


class _SpyEmbedder:
    """Stand-in for ``LibraryEmbedder`` exposing ONLY ``embed_query``.

    Counts calls (so the event-gate test can assert ZERO embeds) and returns a
    fixed query vector so the seeded-record cosines are deterministic. NO
    generation surface — honors the no-extraction invariant.
    """

    def __init__(self, query_vec: np.ndarray) -> None:
        self.calls = 0
        self._query_vec = query_vec

    def embed_query(self, query: str) -> np.ndarray:
        self.calls += 1
        return self._query_vec


# Pick a track-aware event from the gate constant so the test stays in lock-step
# with whatever the canonical trio ends up being (TRACK_CHANGE / PHASE /
# LAYER_ARRIVAL per RESEARCH §Open-Q1).
_TRACK_AWARE = "TRACK_CHANGE"
_CURRENT_SESSION = "20260522-120000"
_PAST_SESSION = "20260520-2200"


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)


# ---------------------------------------------------------------------------
# RECALL-04 — HEARTBEAT (and any non-track-aware event) never retrieves.
# ---------------------------------------------------------------------------


def test_heartbeat_never_retrieves(tmp_path: Path) -> None:
    """HEARTBEAT short-circuits the gate → ``[]`` AND zero embed calls.

    The event gate (RECALL_EVENT_GATE) excludes HEARTBEAT — the single most
    important non-retrieval event (it fires on a timer, carries no track-aware
    signal). on_event MUST return ``[]`` BEFORE any embed, so a periodic
    heartbeat never costs an embedding round-trip and never injects a recall.
    """
    assert "HEARTBEAT" not in RECALL_EVENT_GATE
    assert _TRACK_AWARE in RECALL_EVENT_GATE

    query = _unit(1)
    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, _store(tmp_path))

    out = recall.on_event("HEARTBEAT", "anything", _CURRENT_SESSION)

    assert out == []
    # The gate ran BEFORE the embed — no API round-trip on a heartbeat.
    assert embedder.calls == 0
    # Nothing latched for the prompt builder to pull.
    assert recall.get_latest() == []


# ---------------------------------------------------------------------------
# RECALL-03 — below the cosine floor → survivors [] → no block.
# ---------------------------------------------------------------------------


def test_below_floor_injects_nothing(tmp_path: Path) -> None:
    """A hit whose cosine < RECALL_SIMILARITY_FLOOR (0.7) is dropped.

    Seed a single past-session record whose vector sits well BELOW the floor
    relative to the query. query_topk returns it (it is the only candidate),
    but the floor filter strips it → survivors ``[]`` → the coach gate emits
    NOTHING. This is the conservative-default anti-slop guard: a weak callback
    is no callback.
    """
    assert RECALL_SIMILARITY_FLOOR == 0.7

    store = _store(tmp_path)
    query = _unit(2)
    # ~0.30 cosine — comfortably below the 0.7 floor.
    below = _aligned(query, target_cos=0.30, seed=20)
    store.add_record(
        record_id=f"{_PAST_SESSION}:1",
        session_id=_PAST_SESSION,
        ts=10.0,
        kind="coach_line",
        signature="that bassline swap was filthy",
        embedding=below,
    )

    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, store)

    survivors = recall.on_event(_TRACK_AWARE, "filthy bass", _CURRENT_SESSION)

    assert survivors == []
    assert recall.get_latest() == []
    assert embedder.calls == 1  # the gate let it through; one embed happened


# ---------------------------------------------------------------------------
# RECALL-03 — the live session is excluded from its own retrieval.
# ---------------------------------------------------------------------------


def test_current_session_excluded(tmp_path: Path) -> None:
    """A record under the current session_id is excluded from retrieval.

    Seed a STRONGLY-matching record (cosine well above the floor) but tag it
    with the CURRENT session id. on_event threads
    ``exclude_session=current_session_id`` through ``query_topk`` → the live
    session's own moment is dropped BEFORE ranking → survivors ``[]``. Without
    this, the co-host would "recall" something that is literally happening now.
    """
    store = _store(tmp_path)
    query = _unit(3)
    # ~0.95 cosine — would easily survive the floor if not excluded.
    strong = _aligned(query, target_cos=0.95, seed=30)
    store.add_record(
        record_id=f"{_CURRENT_SESSION}:1",
        session_id=_CURRENT_SESSION,  # the LIVE session
        ts=5.0,
        kind="coach_line",
        signature="you just did this same blend a minute ago",
        embedding=strong,
    )

    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, store)

    survivors = recall.on_event(_TRACK_AWARE, "this blend", _CURRENT_SESSION)

    # The only candidate belonged to the current session → excluded → [].
    assert survivors == []
    assert recall.get_latest() == []


# ---------------------------------------------------------------------------
# RECALL-04 — deadline miss injects nothing (service-level contract).
# ---------------------------------------------------------------------------


def test_deadline_miss_injects_nothing(tmp_path: Path) -> None:
    """After ``clear()`` the latched survivors are ``[]`` — nothing leaks.

    The hard deadline (RECALL_DEADLINE_S) is enforced AGENT-side: when a
    pre-dispatched ``on_event`` overruns the deadline, the agent abandons the
    result and calls ``clear()`` so the missed retrieval cannot bleed into a
    later turn. The service-level behavior the agent relies on is: after
    ``clear()``, ``get_latest()`` is ``[]`` regardless of what a prior on_event
    latched. (The agent-side ``asyncio.wait_for`` + no-inline-await guarantee is
    covered by Plan 65-04's static assert; here we pin the clear() contract.)
    """
    store = _store(tmp_path)
    query = _unit(4)
    strong = _aligned(query, target_cos=0.92, seed=40)
    store.add_record(
        record_id=f"{_PAST_SESSION}:2",
        session_id=_PAST_SESSION,
        ts=12.0,
        kind="coach_line",
        signature="that filter sweep into the drop was clean",
        embedding=strong,
    )

    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, store)

    # A successful retrieval latches a survivor for the prompt builder.
    survivors = recall.on_event(_TRACK_AWARE, "filter sweep", _CURRENT_SESSION)
    assert survivors, "precondition: a strong match should survive the floor"
    assert recall.get_latest(), "precondition: get_latest reflects the latch"

    # The deadline-miss path: the agent abandons + clears. Nothing leaks.
    recall.clear()
    assert recall.get_latest() == []


def test_clear_during_inflight_on_event_discards_stale_latch(tmp_path: Path) -> None:
    """Phase 65 review CR-04 — generation token discards a stale on_event write.

    Simulates the race where the agent's ``asyncio.wait_for`` fires
    ``TimeoutError`` and calls ``recall.clear()`` while the executor thread
    is still inside ``on_event`` (between embed and the final ``_latest =
    survivors`` write). The per-dispatch generation token in
    ``MemoryRecall.on_event`` must detect the intervening ``clear()`` and
    DROP the (now-stale) survivors instead of overwriting the cleared
    latch — otherwise the "missed deadline → no recall this turn" contract
    is violated.

    The race is staged by wrapping ``embed_query`` with a callable that fires
    ``recall.clear()`` after the generation token has been captured but
    BEFORE the final lock-protected write — the same window the executor
    thread sits in under live load.
    """
    store = _store(tmp_path)
    query = _unit(4)
    strong = _aligned(query, target_cos=0.92, seed=44)
    store.add_record(
        record_id=f"{_PAST_SESSION}:9",
        session_id=_PAST_SESSION,
        ts=18.0,
        kind="coach_line",
        signature="late-running riser into the bridge",
        embedding=strong,
    )

    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, store)

    # Stage the race: when embed_query is called, fire clear() AFTER the
    # generation token has been captured (the token is bumped at the very
    # start of on_event, BEFORE embed_query is invoked) but BEFORE the
    # final lock-write. The clear() bumps the generation again, so the
    # final token check fails and survivors are dropped.
    original_embed = embedder.embed_query

    def racing_embed(text: str):  # noqa: ANN202 — test shim
        vec = original_embed(text)
        recall.clear()  # bumps _inflight_gen between dispatch and write
        return vec

    embedder.embed_query = racing_embed  # type: ignore[method-assign]

    survivors = recall.on_event(_TRACK_AWARE, "riser into bridge", _CURRENT_SESSION)
    # The caller still sees the result (the floor + ranking happened) but
    # the latch was NOT mutated — the deadline contract holds.
    assert survivors, "ranking still produces survivors for the caller"
    assert recall.get_latest() == [], (
        "stale executor write must be discarded after intervening clear()"
    )


# ---------------------------------------------------------------------------
# RECALL-04 — exactly one embed per track-aware on_event (no fan-out).
# ---------------------------------------------------------------------------


def test_embed_called_once(tmp_path: Path) -> None:
    """A single track-aware on_event triggers exactly ONE embed_query.

    No retry storm, no per-candidate re-embed: the query is embedded once, then
    ranked against the stored vectors. RECALL_TOP_K bounds the candidate pull,
    not the embed count.
    """
    assert RECALL_TOP_K == 3

    store = _store(tmp_path)
    query = _unit(5)
    # Three above-floor records so query_topk has real candidates to rank.
    for i, cos in enumerate((0.90, 0.85, 0.80), start=1):
        store.add_record(
            record_id=f"{_PAST_SESSION}:{i}",
            session_id=_PAST_SESSION,
            ts=float(i),
            kind="coach_line",
            signature=f"past moment {i}",
            embedding=_aligned(query, target_cos=cos, seed=50 + i),
        )

    embedder = _SpyEmbedder(query)
    recall = MemoryRecall(embedder, store)

    recall.on_event(_TRACK_AWARE, "past moment", _CURRENT_SESSION)

    # Exactly one embed for the one query — never per-candidate.
    assert embedder.calls == 1


# ---------------------------------------------------------------------------
# RECALL-04 — STATIC GATE: llm_node MUST NOT inline-await embed_query.
# ---------------------------------------------------------------------------


def test_llm_node_does_not_inline_await_embed_query() -> None:
    """Static assertion — ``DJCoHostAgent.llm_node`` MUST NEVER inline-await
    ``embed_query``. TTFT regression is the existential failure of RECALL-04;
    the structural guarantee is that the embed runs off-loop via the
    pre-dispatched ``MemoryRecall.on_event`` (run_in_executor + wait_for) and
    that ``llm_node`` only pulls survivors via the LOCK-FREE
    ``recall.get_latest()`` — which returns ``[]`` if the deadline missed, so
    no block, no stall.

    This guard is intentionally cheap + structural: we read the body of
    ``llm_node`` between its ``async def`` header and the next sibling method
    and assert NO ``await ... embed_query`` substring appears. A future
    refactor that inlines the embed (e.g. ``await self._recall._embedder.
    embed_query(…)``) will trip this. The legitimate dispatch path lives in
    ``_maybe_dispatch_recall`` (a separate method) — that does not match
    the substring search inside llm_node's body.

    The recall service itself MAY synchronously call ``embed_query`` (it runs
    off-loop in an executor, that is exactly the point); only ``llm_node``'s
    body is checked here.
    """
    import inspect

    from vibemix.agent.dj_cohost import DJCoHostAgent

    src = inspect.getsource(DJCoHostAgent.llm_node)
    # Defense in depth: assert both spellings of an inline-await would-be
    # offender. The error message names the violation explicitly so a
    # future maintainer who trips this knows WHY the rule exists.
    assert "embed_query" not in src, (
        "RECALL-04 TTFT static gate: DJCoHostAgent.llm_node MUST NOT "
        "reference embed_query — the embed is pre-dispatched off-loop via "
        "_maybe_dispatch_recall + asyncio.wait_for(RECALL_DEADLINE_S). "
        "llm_node only pulls survivors via recall.get_latest() (no await). "
        "If you need the live query embedded, do it at the set_next_event "
        "dispatch seam, not inside the reaction body."
    )
    assert "await " in src and ".embed_query" not in src, (
        "llm_node must be async (await present) and must NOT call .embed_query "
        "anywhere in its body. Sanity check on the inspect.getsource path."
    )
