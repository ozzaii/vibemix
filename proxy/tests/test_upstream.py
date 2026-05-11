# SPDX-License-Identifier: Apache-2.0
"""UP-01..02 — upstream singleton + reset helpers."""

from __future__ import annotations

import httpx
import pytest
from google import genai

import app.upstream as up


def test_up_01_gemini_client_is_singleton(monkeypatch):
    up.reset_gemini_client()
    c1 = up.get_gemini_client()
    c2 = up.get_gemini_client()
    assert c1 is c2
    assert isinstance(c1, genai.Client)


@pytest.mark.asyncio
async def test_up_02_http_client_is_singleton_until_close():
    await up.close_http_client()
    c1 = up.get_http_client()
    c2 = up.get_http_client()
    assert c1 is c2
    assert isinstance(c1, httpx.AsyncClient)
    await up.close_http_client()
    c3 = up.get_http_client()
    assert c3 is not c1
    await up.close_http_client()
