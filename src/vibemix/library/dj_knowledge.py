# SPDX-License-Identifier: Apache-2.0
"""DJ-knowledge RAG — a SEPARATE text knowledge store for technique grounding.

This is the TUTOR-lens grounding layer: a tiny retrieval-augmented store over
DJ *technique / knowledge* text (EQ-ing, phrasing, gain staging, harmonic
mixing, etc.). It is deliberately NOT the audio CLAP store — CLAP embeds
*audio*, this embeds *text*. The two never share a backend.

Data flow
=========

    ingest (future):  source article → chunk_text() → KnowledgeChunk[] +
                      text-embeddings → KnowledgeStore.add() → save() to
                      a JSONL (chunk rows) + .npy (parallel vector matrix).

    retrieve (live):  query string → injected text embedder → query vector →
                      KnowledgeStore.search() cosine top-k (topic / skill_level
                      filtered) → retrieve_dj_knowledge() returns paraphrased,
                      *attributed* citations ({text, source_title, source_url,
                      topic, skill_level, score}).

Grounding contract (mirrors ``toolset.py``)
-------------------------------------------
- Sources are LINK-OUT: each chunk carries a ``source_url`` we attribute and
  link, never a mirrored full article. The store holds short paraphrase chunks.
- Honest-null: an empty store returns ``{"results": [], "note": ...}`` — the
  agent must never invent technique facts when the KB is empty.
- Functions RETURN error dicts, never raise (the agent loop can't be wedged).

Embedder contract (the injected ``embedder``)
---------------------------------------------
``retrieve_dj_knowledge`` accepts ANY of:
  * a plain ``callable(text: str) -> np.ndarray``  (simplest), OR
  * an object exposing ``.embed_text(text) -> np.ndarray``, OR
  * an object exposing ``.embed_query(text) -> np.ndarray``  (the product
    library embedder shape).
The first match wins. The returned vector is L2-normalized here before cosine,
so the embedder need not normalize. Vectors stored via ``add()`` are likewise
L2-normalized on the way in, so ``search`` is a plain dot product.

skill_level maps to vibemix's user levels: "beginner" / "intermediate" / "pro",
plus "any" for level-agnostic facts. A ``skill_level`` filter matches the
requested level OR "any".
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Skill levels mirror vibemix's three user levels + a level-agnostic bucket.
VALID_SKILL_LEVELS = ("beginner", "intermediate", "pro", "any")

# Default on-disk home, sibling to library.db / embeddings.db under the cache.
DEFAULT_KNOWLEDGE_DIR = Path.home() / ".cache" / "vibemix" / "knowledge"
DEFAULT_KNOWLEDGE_EMBEDDING_DIM = 1536
KNOWLEDGE_EMBEDDING_TIMEOUT_MS = 120_000


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize → float32 unit vector; zero vectors pass through unchanged."""
    v = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(v))
    if norm < 1e-12:
        return v
    return (v / norm).astype(np.float32, copy=False)


def _embed_with(embedder: Any, text: str) -> np.ndarray:
    """Embed ``text`` via the injected embedder, supporting the 3 contract shapes.

    Raises only inside the caller's try/except; callers convert to error dicts.
    """
    if callable(embedder):
        return np.asarray(embedder(text), dtype=np.float32).reshape(-1)
    fn = getattr(embedder, "embed_text", None) or getattr(embedder, "embed_query", None)
    if fn is None:
        raise TypeError("embedder must be callable or expose .embed_text/.embed_query")
    return np.asarray(fn(text), dtype=np.float32).reshape(-1)


class GeminiKnowledgeTextEmbedder:
    """Text-only Gemini embedder for the DJ-knowledge store.

    This is intentionally separate from ``LibraryEmbedder`` / ``ClapEmbedder``.
    Music-library search stays local CLAP/512; DJ technique RAG uses the text
    store's own dimensionality, which is 1536 for the bundled corpus.
    """

    def __init__(
        self,
        client: Any,
        *,
        output_dimensionality: int = DEFAULT_KNOWLEDGE_EMBEDDING_DIM,
        model: str | None = None,
    ) -> None:
        if output_dimensionality <= 0:
            raise ValueError("output_dimensionality must be positive")
        self._client = client
        self.output_dimensionality = int(output_dimensionality)
        if model is None:
            from vibemix.llm.model_router import resolve_model

            model = resolve_model("embedding")
        self._model = model

    def embed_text(self, text: str) -> np.ndarray:
        from google.genai import types

        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality,
            ),
        )
        values = list(result.embeddings[0].values)
        return np.asarray(values, dtype=np.float32).reshape(-1)


def build_default_knowledge_embedder(
    *,
    output_dimensionality: int = DEFAULT_KNOWLEDGE_EMBEDDING_DIM,
) -> tuple[GeminiKnowledgeTextEmbedder | None, str | None]:
    """Build the default text embedder for DJ-knowledge retrieval.

    Returns ``(embedder, None)`` on success or ``(None, actionable_error)`` on a
    missing/unbuildable credential path. No network call happens here; the
    first actual embed still occurs inside ``retrieve_dj_knowledge``.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    proxy_jwt = os.environ.get("VIBEMIX_PROXY_JWT")
    proxy_url = os.environ.get("VIBEMIX_PROXY_BASE_URL", "https://api.altidus.world")

    try:
        if api_key:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=KNOWLEDGE_EMBEDDING_TIMEOUT_MS),
            )
            return (
                GeminiKnowledgeTextEmbedder(
                    client,
                    output_dimensionality=output_dimensionality,
                ),
                None,
            )
        if proxy_jwt:
            from vibemix.agent.proxy_client import build_proxy_genai_client

            return (
                GeminiKnowledgeTextEmbedder(
                    build_proxy_genai_client(proxy_jwt, proxy_url),
                    output_dimensionality=output_dimensionality,
                ),
                None,
            )
    except Exception as exc:
        return None, f"text embedder setup failed: {type(exc).__name__}"

    return (
        None,
        "set GEMINI_API_KEY or VIBEMIX_PROXY_JWT so DJ-knowledge can embed text queries",
    )


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """One paraphrased, attributed slice of DJ-technique text.

    ``source_url`` is the link-out we attribute — we never mirror full articles.
    ``skill_level`` is one of ``VALID_SKILL_LEVELS``.
    """

    chunk_id: str
    text: str
    source_title: str
    source_url: str
    topic: str
    skill_level: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "topic": self.topic,
            "skill_level": self.skill_level,
        }


class KnowledgeStore:
    """In-memory chunks + a parallel float32 embedding matrix; cosine retrieval.

    Vectors are L2-normalized on ``add`` so ``search`` is a plain dot product.
    Persistence (``save``/``load``) is a JSONL (chunk rows) + ``.npy`` (matrix)
    pair — guarded + lazy so tests build a store with zero disk touch.
    """

    def __init__(self) -> None:
        self._chunks: list[KnowledgeChunk] = []
        # Stored row-wise, L2-normalized, float32; shape (N, D). None until first add.
        self._matrix: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def chunks(self) -> list[KnowledgeChunk]:
        return list(self._chunks)

    @property
    def dim(self) -> int | None:
        """Embedding dimensionality of the stored matrix; ``None`` when empty.

        Lets the retrieval entry point detect a wrong-space query embedder
        (e.g. 512-d audio/CLAP against a 1536-d Gemini text store) and fail
        loudly instead of letting ``search`` swallow the mismatch as ``[]``.
        """
        return None if self._matrix is None else int(self._matrix.shape[1])

    def add(self, chunk: KnowledgeChunk, vector: np.ndarray) -> None:
        """Append a chunk + its (L2-normalized-here) embedding row.

        First add fixes the dimensionality; mismatched-dim adds are rejected
        (raises ValueError — callers that need error-dicts wrap this).
        """
        vec = _l2_normalize(vector)
        if self._matrix is None:
            self._matrix = vec.reshape(1, -1).astype(np.float32, copy=False)
        else:
            if vec.shape[0] != self._matrix.shape[1]:
                raise ValueError(
                    f"vector dim {vec.shape[0]} != store dim {self._matrix.shape[1]}"
                )
            self._matrix = np.vstack([self._matrix, vec.reshape(1, -1)]).astype(
                np.float32, copy=False
            )
        self._chunks.append(chunk)

    def search(
        self,
        query_vec: np.ndarray,
        *,
        k: int,
        topic: str | None = None,
        skill_level: str | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Cosine top-k over stored chunks, filtered by topic / skill_level.

        - ``topic`` filter: exact match (case-insensitive) when given.
        - ``skill_level`` filter: matches the requested level OR "any".
        - Returns ``(chunk, score)`` tuples sorted DESC by score, ties broken
          ASC by ``chunk_id`` for determinism.
        """
        if self._matrix is None or len(self._chunks) == 0:
            return []
        q = _l2_normalize(query_vec)
        if q.shape[0] != self._matrix.shape[1]:
            return []

        topic_lc = topic.lower() if topic else None
        level_lc = skill_level.lower() if skill_level else None

        sims = self._matrix @ q  # (N,) float32; both sides L2-normalized
        scored: list[tuple[KnowledgeChunk, float]] = []
        for i, chunk in enumerate(self._chunks):
            if topic_lc is not None and chunk.topic.lower() != topic_lc:
                continue
            if level_lc is not None and chunk.skill_level.lower() not in (level_lc, "any"):
                continue
            scored.append((chunk, float(sims[i])))

        scored.sort(key=lambda p: (-p[1], p[0].chunk_id))
        return scored[: max(1, k)]

    # -- persistence (guarded + lazy; tests stay in-memory) ----------------- #

    @staticmethod
    def _paths(path: str | Path) -> tuple[Path, Path]:
        """Resolve a base path to its (JSONL chunks, .npy matrix) pair."""
        base = Path(path)
        return base.with_suffix(".jsonl"), base.with_suffix(".npy")

    def save(self, path: str | Path) -> dict[str, Any]:
        """Persist to ``<path>.jsonl`` + ``<path>.npy``. Returns a status dict."""
        try:
            jsonl_path, npy_path = self._paths(path)
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with jsonl_path.open("w", encoding="utf-8") as fh:
                for chunk in self._chunks:
                    fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
            matrix = (
                self._matrix
                if self._matrix is not None
                else np.zeros((0, 0), dtype=np.float32)
            )
            np.save(npy_path, matrix)
            return {"saved": len(self._chunks), "jsonl": str(jsonl_path)}
        except Exception as e:
            return {"error": f"save failed: {type(e).__name__}"}

    @classmethod
    def load(cls, path: str | Path) -> KnowledgeStore:
        """Load from ``<path>.jsonl`` + ``<path>.npy``. Missing files → empty store."""
        store = cls()
        jsonl_path, npy_path = cls._paths(path)
        if not jsonl_path.exists() or not npy_path.exists():
            return store
        try:
            matrix = np.load(npy_path).astype(np.float32, copy=False)
            rows: list[KnowledgeChunk] = []
            with jsonl_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    rows.append(
                        KnowledgeChunk(
                            chunk_id=str(d["chunk_id"]),
                            text=str(d["text"]),
                            source_title=str(d["source_title"]),
                            source_url=str(d["source_url"]),
                            topic=str(d["topic"]),
                            skill_level=str(d["skill_level"]),
                        )
                    )
            # Only adopt the matrix if it lines up row-wise with the chunks.
            if matrix.ndim == 2 and matrix.shape[0] == len(rows) and len(rows) > 0:
                store._chunks = rows
                store._matrix = matrix
        except Exception:
            return cls()
        return store


def retrieve_dj_knowledge(
    store: KnowledgeStore,
    query: str,
    *,
    embedder: Any | None = None,
    topic: str | None = None,
    skill_level: str | None = None,
    k: int = 4,
) -> dict[str, Any]:
    """Grounded TUTOR-lens retrieval over the DJ-knowledge store.

    Honest-null + RETURN-error contract:
      - empty store → ``{"results": [], "note": "knowledge base empty"}``
      - no embedder → ``{"error": "retrieve_dj_knowledge needs a text embedder"}``
      - otherwise   → ``{"results": [...citations...], "query": query}``

    ``k`` is clamped to [1, 10]. Each citation carries its ``source_url`` so the
    agent attributes + links out rather than presenting paraphrase as its own.
    """
    if not isinstance(query, str) or not query.strip():
        return {"error": "retrieve_dj_knowledge: 'query' must be a non-empty string"}
    if len(store) == 0:
        return {"results": [], "note": "knowledge base empty"}
    if embedder is None:
        return {"error": "retrieve_dj_knowledge needs a text embedder"}

    k = max(1, min(10, int(k)))
    try:
        qvec = _embed_with(embedder, query)
    except Exception as e:
        return {"error": f"retrieve_dj_knowledge embed failed: {type(e).__name__}"}

    # Fail LOUD on a wrong-space embedder. The toolset injects ONE embedder for
    # everything; if the audio/CLAP embedder (512-d) reaches this text store
    # (Gemini text-embedding, 1536-d), the dims don't match and `search` would
    # silently return [] — masking a wiring bug as "empty knowledge base". Name
    # both dims + the cause so the fix (wire a matching text embedder) is obvious.
    store_dim = store.dim
    if store_dim is not None and int(qvec.shape[0]) != store_dim:
        return {
            "error": (
                f"retrieve_dj_knowledge: query embedder produced dim "
                f"{int(qvec.shape[0])} but the knowledge store is dim {store_dim} "
                f"— a TEXT embedder matching the store (Gemini text-embedding) "
                f"must be wired for DJ-knowledge retrieval, not the audio/CLAP "
                f"embedder."
            )
        }

    try:
        hits = store.search(qvec, k=k, topic=topic, skill_level=skill_level)
    except Exception as e:
        return {"error": f"retrieve_dj_knowledge search failed: {type(e).__name__}"}

    results = [
        {
            "text": chunk.text,
            "source_title": chunk.source_title,
            "source_url": chunk.source_url,
            "topic": chunk.topic,
            "skill_level": chunk.skill_level,
            "score": round(score, 6),
        }
        for chunk, score in hits
    ]
    return {"results": results, "query": query}


def chunk_text(text: str, *, max_chars: int = 800) -> list[str]:
    """Paragraph-aware splitter for future ingestion.

    Splits on blank lines, then greedily packs paragraphs into chunks up to
    ``max_chars``. A single oversized paragraph is hard-split at ``max_chars``.
    Returns ``[]`` for empty/whitespace input.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        # Hard-split a paragraph longer than the whole budget.
        while len(para) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(para[:max_chars].strip())
            para = para[max_chars:].strip()
        if not para:
            continue
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return chunks


__all__ = [
    "DEFAULT_KNOWLEDGE_DIR",
    "DEFAULT_KNOWLEDGE_EMBEDDING_DIM",
    "VALID_SKILL_LEVELS",
    "GeminiKnowledgeTextEmbedder",
    "KnowledgeChunk",
    "KnowledgeStore",
    "build_default_knowledge_embedder",
    "chunk_text",
    "retrieve_dj_knowledge",
]
