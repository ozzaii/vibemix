# SPDX-License-Identifier: Apache-2.0
"""APP-01..04 — FastAPI app shape + healthz + OpenAPI."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI


def test_app_01_app_is_fastapi_with_docs_urls():
    from app.main import app

    assert isinstance(app, FastAPI)
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"


@pytest.mark.asyncio
async def test_app_02_healthz_returns_ok(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_app_03_openapi_schema_includes_healthz(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "/healthz" in data["paths"]


def test_app_04_app_boots_fast():
    """Sanity timer — catches accidental sync-blocking imports at startup."""
    start = time.monotonic()
    from app.main import make_app

    _ = make_app()
    assert time.monotonic() - start < 2.0
