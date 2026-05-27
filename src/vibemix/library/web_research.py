# SPDX-License-Identifier: Apache-2.0
"""web_research — grounded web search + page-fetch for the Viber DJ agent.

Roadmap item #1 of the Viber/Codex capability expansion: give the curator a
way to reach OUTSIDE the user's library for DJ knowledge (track/label/artist
facts, release info, scene context) without inventing it. Both functions are
thin, side-effect-free wrappers over the **Tavily** API:

* ``web_search`` → ``POST https://api.tavily.com/search`` — a query becomes a
  list of ``{title, url, snippet, score}`` hits (Tavily's ``content`` field is
  mapped to ``snippet`` and truncated).
* ``fetch_url`` → ``POST https://api.tavily.com/extract`` — one URL becomes its
  readable ``text`` (Tavily's ``raw_content``, truncated).

Grounding contract (mirrors :mod:`vibemix.library.toolset`): these are tool
handlers, so they **RETURN** dicts — including ``{"error": ...}`` — and NEVER
raise. A missing ``TAVILY_API_KEY``, an HTTP failure, or bad JSON all degrade
to an honest error dict the agent loop can recover from, never a crash. The
HTTP client is **injected** (``client=`` an ``httpx.Client``-like object); when
``None``, ``httpx`` is lazy-imported and a short-timeout client is built on the
fly. The injection seam is what lets the unit tests cover every branch with a
fake client and zero network.

The Tavily key is read from the environment at call time (``TAVILY_API_KEY``),
never inlined or cached at import — so importing this module pulls in nothing
heavy and asserts no config.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Tavily REST endpoints (the key travels in the JSON body, not a header).
_SEARCH_URL = "https://api.tavily.com/search"
_EXTRACT_URL = "https://api.tavily.com/extract"

# Short wall-clock on the auto-built client — a tool call must never park the
# agent loop on a hung connection.
_HTTP_TIMEOUT_S = 8.0

# Result-field caps: enough context for the model to reason, bounded so one
# fetch can't blow the prompt budget.
_SNIPPET_MAX = 1200
_TEXT_MAX = 4000

# k bounds for web_search.
_K_MIN = 1
_K_MAX = 10

# Honest-degrade message when the key is absent (no raise).
_NO_KEY_ERR = "web_search unavailable: set TAVILY_API_KEY (https://tavily.com)"


def _truncate(s: str, n: int) -> str:
    """Coerce to a clean ``str`` and clamp to ``n`` chars (defensive on non-str)."""
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    return s if len(s) <= n else s[:n]


def _build_client() -> Any:
    """Lazy-build a short-timeout httpx client (heavy dep imported only here)."""
    import httpx

    return httpx.Client(timeout=_HTTP_TIMEOUT_S)


def web_search(query: str, k: int = 5, *, client: Any | None = None) -> dict[str, Any]:
    """Web-search ``query`` via Tavily; return grounded ``{results, query}``.

    ``k`` is clamped to [1, 10]. Reads ``TAVILY_API_KEY`` from the environment;
    absent → honest ``{"error": ...}`` (never raises). The HTTP POST goes
    through the injected ``client`` (an ``httpx.Client``-like object with
    ``.post(url, json=...) -> resp`` where ``resp.status_code`` and
    ``resp.json()`` exist); ``None`` lazy-builds one. Every returned result has
    a non-empty ``url`` — rows without one are dropped (a citation needs a
    source). On any HTTP / JSON failure returns ``{"error": ...}``.
    """
    if not isinstance(query, str) or not query.strip():
        return {"error": "web_search: 'query' must be a non-empty string"}
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"error": _NO_KEY_ERR}
    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 5
    k = max(_K_MIN, min(_K_MAX, k))

    own_client = client is None
    try:
        if own_client:
            client = _build_client()
        resp = client.post(
            _SEARCH_URL,
            json={"api_key": api_key, "query": query, "max_results": k},
        )
    except Exception as e:
        logger.warning("[web_research] web_search request failed: %s", e)
        return {"error": f"web_search failed: {type(e).__name__}"}
    finally:
        # Only close a client we created — a caller-injected client is theirs.
        if own_client and client is not None:
            try:
                client.close()
            except Exception:
                pass

    status = getattr(resp, "status_code", None)
    if status != 200:
        return {"error": f"web_search failed: HTTP {status}"}
    try:
        payload = resp.json()
    except Exception as e:
        logger.warning("[web_research] web_search bad JSON: %s", e)
        return {"error": f"web_search failed: {type(e).__name__}"}
    if not isinstance(payload, dict):
        return {"error": "web_search failed: response was not a JSON object"}

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raw_results = []
    results: list[dict[str, Any]] = []
    for r in raw_results:
        if not isinstance(r, dict):
            continue
        url = r.get("url")
        if not (isinstance(url, str) and url.strip()):
            continue  # a citation with no source is useless — drop it
        try:
            score = float(r.get("score")) if r.get("score") is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0
        results.append(
            {
                "title": _truncate(r.get("title", ""), _SNIPPET_MAX),
                "url": url,
                "snippet": _truncate(r.get("content", ""), _SNIPPET_MAX),
                "score": score,
            }
        )
    return {"results": results, "query": query}


def fetch_url(url: str, *, client: Any | None = None) -> dict[str, Any]:
    """Fetch one page's readable text via Tavily Extract → ``{url, title, text}``.

    Validates that ``url`` is an http(s) URL (else error), reads
    ``TAVILY_API_KEY`` (absent → error), and POSTs through the injected/auto
    client (same seam as :func:`web_search`). ``text`` is Tavily's
    ``raw_content`` truncated to 4000 chars. Never raises — any failure becomes
    an ``{"error": ...}`` dict.
    """
    if not isinstance(url, str) or not (
        url.startswith("http://") or url.startswith("https://")
    ):
        return {"error": "fetch_url: 'url' must start with http:// or https://"}
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"error": _NO_KEY_ERR}

    own_client = client is None
    try:
        if own_client:
            client = _build_client()
        resp = client.post(
            _EXTRACT_URL,
            json={"api_key": api_key, "urls": [url]},
        )
    except Exception as e:
        logger.warning("[web_research] fetch_url request failed: %s", e)
        return {"error": f"fetch_url failed: {type(e).__name__}"}
    finally:
        if own_client and client is not None:
            try:
                client.close()
            except Exception:
                pass

    status = getattr(resp, "status_code", None)
    if status != 200:
        return {"error": f"fetch_url failed: HTTP {status}"}
    try:
        payload = resp.json()
    except Exception as e:
        logger.warning("[web_research] fetch_url bad JSON: %s", e)
        return {"error": f"fetch_url failed: {type(e).__name__}"}
    if not isinstance(payload, dict):
        return {"error": "fetch_url failed: response was not a JSON object"}

    raw_results = payload.get("results")
    if not isinstance(raw_results, list) or not raw_results:
        return {"error": "fetch_url failed: no extractable content"}
    first = raw_results[0]
    if not isinstance(first, dict):
        return {"error": "fetch_url failed: malformed extract result"}
    return {
        "url": url,
        "title": _truncate(first.get("title", ""), _SNIPPET_MAX),
        "text": _truncate(first.get("raw_content", ""), _TEXT_MAX),
    }


__all__ = ["fetch_url", "web_search"]
