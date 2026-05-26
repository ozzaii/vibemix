# SPDX-License-Identifier: Apache-2.0
"""Tests for the DJ-knowledge RAG (vibemix.library.dj_knowledge).

Embedder contract under test
----------------------------
``retrieve_dj_knowledge`` accepts any of: a plain ``callable(text) -> ndarray``,
an object with ``.embed_text(text)``, or an object with ``.embed_query(text)``.
These tests inject a deterministic ``FakeEmbedder`` exposing ``.embed_text`` —
a keyword bag-of-words vector over a fixed vocabulary, so a query about "EQ"
deterministically ranks the EQ chunk first (no network, fully reproducible).
"""

from __future__ import annotations

import numpy as np

from vibemix.library.dj_knowledge import (
    KnowledgeChunk,
    KnowledgeStore,
    chunk_text,
    retrieve_dj_knowledge,
)

# Fixed vocabulary → deterministic, keyword-aligned embeddings.
_VOCAB = ["eq", "bass", "phrasing", "bars", "harmonic", "key", "gain", "headroom"]


class FakeEmbedder:
    """Deterministic text embedder: one dimension per vocab keyword.

    Vector[i] = count of _VOCAB[i] (lowercased word match) in the text. A query
    sharing keywords with a chunk gets a high cosine, so ranking is predictable.
    """

    def embed_text(self, text: str) -> np.ndarray:
        words = text.lower().replace("-", " ").split()
        vec = np.zeros(len(_VOCAB), dtype=np.float32)
        for i, term in enumerate(_VOCAB):
            vec[i] = float(words.count(term))
        # Guarantee a non-zero vector so cosine is defined for any text.
        if not vec.any():
            vec[0] = 1e-3
        return vec


def _chunk(cid: str, text: str, topic: str, level: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=cid,
        text=text,
        source_title=f"Guide {cid}",
        source_url=f"https://example.com/{cid}",
        topic=topic,
        skill_level=level,
    )


def _build_store(embedder: FakeEmbedder) -> KnowledgeStore:
    store = KnowledgeStore()
    rows = [
        _chunk("eq1", "Use the EQ to cut bass when blending two tracks", "eq", "beginner"),
        _chunk("phr1", "Count phrasing in bars, mix on the 16 bars boundary", "phrasing", "intermediate"),
        _chunk("harm1", "Harmonic mixing keeps the key compatible", "harmonic", "pro"),
        _chunk("gain1", "Set gain for headroom to avoid clipping", "gain", "any"),
    ]
    for c in rows:
        store.add(c, embedder.embed_text(c.text))
    return store


def test_add_and_len():
    emb = FakeEmbedder()
    store = KnowledgeStore()
    assert len(store) == 0
    store.add(_chunk("a", "EQ the bass", "eq", "beginner"), emb.embed_text("EQ the bass"))
    store.add(_chunk("b", "phrasing in bars", "phrasing", "pro"), emb.embed_text("phrasing in bars"))
    assert len(store) == 2


def test_search_topk_ordering():
    emb = FakeEmbedder()
    store = _build_store(emb)
    hits = store.search(emb.embed_text("how do I EQ the bass"), k=2)
    assert len(hits) == 2
    # EQ chunk must rank first.
    assert hits[0][0].chunk_id == "eq1"
    # Scores are DESC.
    assert hits[0][1] >= hits[1][1]


def test_topic_filter():
    emb = FakeEmbedder()
    store = _build_store(emb)
    hits = store.search(emb.embed_text("bass phrasing key gain"), k=10, topic="harmonic")
    assert len(hits) == 1
    assert hits[0][0].topic == "harmonic"


def test_skill_level_filter_includes_any_excludes_others():
    emb = FakeEmbedder()
    store = _build_store(emb)
    hits = store.search(emb.embed_text("eq bass phrasing harmonic gain"), k=10, skill_level="beginner")
    levels = {c.skill_level for c, _ in hits}
    ids = {c.chunk_id for c, _ in hits}
    # beginner chunk + the "any" chunk are returned; intermediate/pro excluded.
    assert "eq1" in ids       # beginner
    assert "gain1" in ids     # any
    assert "phr1" not in ids  # intermediate
    assert "harm1" not in ids # pro
    assert levels <= {"beginner", "any"}


def test_retrieve_happy_path_returns_cited_results():
    emb = FakeEmbedder()
    store = _build_store(emb)
    out = retrieve_dj_knowledge(store, "EQ the bass on a blend", embedder=emb, k=3)
    assert "results" in out
    assert out["query"] == "EQ the bass on a blend"
    assert len(out["results"]) >= 1
    top = out["results"][0]
    assert top["topic"] == "eq"
    assert top["source_url"].startswith("https://")
    assert set(top) == {"text", "source_title", "source_url", "topic", "skill_level", "score"}


def test_retrieve_empty_store_returns_note():
    out = retrieve_dj_knowledge(KnowledgeStore(), "anything", embedder=FakeEmbedder())
    assert out == {"results": [], "note": "knowledge base empty"}


def test_retrieve_no_embedder_returns_error():
    emb = FakeEmbedder()
    store = _build_store(emb)
    out = retrieve_dj_knowledge(store, "EQ the bass", embedder=None)
    assert out == {"error": "retrieve_dj_knowledge needs a text embedder"}


def test_retrieve_k_clamped():
    emb = FakeEmbedder()
    store = _build_store(emb)
    # k above 10 clamps; store only has 4 → at most 4 returned.
    out_hi = retrieve_dj_knowledge(store, "eq bass phrasing harmonic gain", embedder=emb, k=999)
    assert len(out_hi["results"]) == 4
    # k below 1 clamps to 1.
    out_lo = retrieve_dj_knowledge(store, "eq bass phrasing harmonic gain", embedder=emb, k=0)
    assert len(out_lo["results"]) == 1


def test_retrieve_callable_embedder_contract():
    emb = FakeEmbedder()
    store = _build_store(emb)
    # A plain callable also satisfies the contract.
    out = retrieve_dj_knowledge(store, "harmonic key mixing", embedder=lambda t: emb.embed_text(t), k=1)
    assert out["results"][0]["topic"] == "harmonic"


def test_save_load_round_trip(tmp_path):
    emb = FakeEmbedder()
    store = KnowledgeStore()
    c1 = _chunk("eq1", "EQ the bass", "eq", "beginner")
    c2 = _chunk("phr1", "phrasing in bars", "phrasing", "pro")
    store.add(c1, emb.embed_text(c1.text))
    store.add(c2, emb.embed_text(c2.text))

    base = tmp_path / "kb"
    res = store.save(base)
    assert res.get("saved") == 2

    loaded = KnowledgeStore.load(base)
    assert len(loaded) == 2
    assert [c.to_dict() for c in loaded.chunks] == [c1.to_dict(), c2.to_dict()]
    # Retrieval works on the loaded store and ranks EQ first.
    out = retrieve_dj_knowledge(loaded, "EQ the bass", embedder=emb, k=2)
    assert out["results"][0]["topic"] == "eq"


def test_load_missing_files_returns_empty(tmp_path):
    loaded = KnowledgeStore.load(tmp_path / "does_not_exist")
    assert len(loaded) == 0


def test_chunk_text_paragraph_aware():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    text = "Para one." + "\n\n" + "Para two."
    assert chunk_text(text, max_chars=100) == ["Para one.\n\nPara two."]
    # Forced split when over budget.
    parts = chunk_text("aaaa\n\nbbbb", max_chars=4)
    assert all(len(p) <= 4 for p in parts)
    assert len(parts) == 2


def test_chunk_text_hard_split_oversized_paragraph():
    big = "x" * 25
    parts = chunk_text(big, max_chars=10)
    assert all(len(p) <= 10 for p in parts)
    assert "".join(parts) == big
