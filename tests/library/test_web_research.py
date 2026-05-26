# SPDX-License-Identifier: Apache-2.0
"""Unit tests for vibemix.library.web_research — fake-client, zero network.

Every external HTTP call goes through an injected ``FakeClient`` whose
``.post`` returns a ``FakeResponse`` with ``.status_code`` + ``.json()``. No
real httpx, no Tavily, no network. Covers the grounding contract: success
mapping/truncation/url-less drop, missing key, HTTP error, bad JSON, k clamp,
and the fetch_url success + bad-scheme paths.
"""

from __future__ import annotations

from typing import Any

import pytest

from vibemix.library import web_research


class FakeResponse:
    def __init__(self, status_code: int, payload: Any, *, raise_json: bool = False) -> None:
        self.status_code = status_code
        self._payload = payload
        self._raise_json = raise_json

    def json(self) -> Any:
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


class FakeClient:
    """Records the last POST and returns a queued FakeResponse."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, json: dict[str, Any]) -> FakeResponse:  # noqa: A002
        self.calls.append((url, json))
        return self._response


# -- web_search --------------------------------------------------------------- #


def test_web_search_success_maps_truncates_drops_urlless(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    long = "z" * 5000
    resp = FakeResponse(
        200,
        {
            "results": [
                {"title": "Good", "url": "https://a.com", "content": long, "score": 0.9},
                {"title": "NoUrl", "url": "", "content": "dropme", "score": 0.5},
                {"title": "NoUrlKey", "content": "alsodrop", "score": 0.4},
            ]
        },
    )
    client = FakeClient(resp)
    out = web_research.web_search("techno labels", k=5, client=client)

    assert "error" not in out
    assert out["query"] == "techno labels"
    # url-less rows dropped → only the first survives.
    assert len(out["results"]) == 1
    row = out["results"][0]
    assert row["url"] == "https://a.com"
    assert row["title"] == "Good"
    assert row["score"] == pytest.approx(0.9)
    # content → snippet, truncated to the 1200 cap.
    assert len(row["snippet"]) == 1200
    # request body shape.
    url, body = client.calls[0]
    assert url == "https://api.tavily.com/search"
    assert body == {"api_key": "x", "query": "techno labels", "max_results": 5}


def test_web_search_missing_key(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = FakeClient(FakeResponse(200, {"results": []}))
    out = web_research.web_search("anything", client=client)
    assert "error" in out
    assert "TAVILY_API_KEY" in out["error"]
    # Honest degrade — we never even hit the client.
    assert client.calls == []


def test_web_search_http_non_200(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    client = FakeClient(FakeResponse(429, {"detail": "rate limited"}))
    out = web_research.web_search("q", client=client)
    assert "error" in out
    assert "429" in out["error"]


def test_web_search_bad_json(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    client = FakeClient(FakeResponse(200, None, raise_json=True))
    out = web_research.web_search("q", client=client)
    assert "error" in out
    assert out["error"].startswith("web_search failed")


@pytest.mark.parametrize("k_in,k_expected", [(0, 1), (-5, 1), (50, 10), (7, 7)])
def test_web_search_k_clamped(monkeypatch, k_in, k_expected) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    client = FakeClient(FakeResponse(200, {"results": []}))
    web_research.web_search("q", k=k_in, client=client)
    _, body = client.calls[0]
    assert body["max_results"] == k_expected


# -- fetch_url ---------------------------------------------------------------- #


def test_fetch_url_success(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    long = "y" * 9000
    resp = FakeResponse(
        200,
        {"results": [{"url": "https://a.com", "title": "Page", "raw_content": long}]},
    )
    client = FakeClient(resp)
    out = web_research.fetch_url("https://a.com", client=client)

    assert "error" not in out
    assert out["url"] == "https://a.com"
    assert out["title"] == "Page"
    assert len(out["text"]) == 4000  # truncated to the 4000 cap
    url, body = client.calls[0]
    assert url == "https://api.tavily.com/extract"
    assert body == {"api_key": "x", "urls": ["https://a.com"]}


def test_fetch_url_bad_scheme(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    client = FakeClient(FakeResponse(200, {"results": []}))
    out = web_research.fetch_url("ftp://nope.com", client=client)
    assert "error" in out
    assert "http" in out["error"]
    # Scheme rejected before any request goes out.
    assert client.calls == []


def test_fetch_url_missing_key(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = FakeClient(FakeResponse(200, {"results": []}))
    out = web_research.fetch_url("https://a.com", client=client)
    assert "error" in out
    assert client.calls == []
