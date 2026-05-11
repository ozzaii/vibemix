# SPDX-License-Identifier: Apache-2.0
"""QI-01..02 — Quota client wired onto app.state.

For Wave 3, the production app.state.quota_client is replaced by tests via
the `app_with_fake_quota` conftest fixture (fakeredis-backed). QI-01 pins
that wiring. QI-02 pins that 2001 calls exceed the default daily_quota=2000.
"""

from __future__ import annotations

import pytest

from app.quota import QuotaClient, QuotaExceeded


@pytest.mark.asyncio
async def test_qi_01_quota_client_on_app_state(app_with_fake_quota):
    qc = app_with_fake_quota.state.quota_client
    assert isinstance(qc, QuotaClient)


@pytest.mark.asyncio
async def test_qi_02_quota_exceeded_at_2001_calls(redis_client):
    # Direct on the client — faster than going through 2001 HTTP requests.
    qc = QuotaClient.from_redis(redis_client, daily_quota=2000)
    for _ in range(2000):
        await qc.consume("uuid-x")
    with pytest.raises(QuotaExceeded):
        await qc.consume("uuid-x")
