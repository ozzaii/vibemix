# SPDX-License-Identifier: Apache-2.0
"""Daily per-UUID quota tracking via Redis INCR + EXPIRE NX.

From RESEARCH Q5 (verified canonical pattern). Requires Redis 7.0+ for
the `EXPIRE key seconds NX` semantics — see Pitfall 4. Production
deployment verifies `INFO server redis_version >= 7.0` (documented in
plan 05-05 README).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import redis.asyncio as redis_async


class QuotaExceeded(Exception):
    """Raised when daily quota for install_uuid is exhausted."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(f"daily quota exceeded, retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class QuotaClient:
    """Per-UUID daily-counter Redis client.

    Key shape: ``vibemix:quota:<install_uuid>:<YYYYMMDD>`` (UTC date).
    TTL: 86400s, set with NX on first consume so subsequent INCRs do
    NOT extend the original expiry.
    """

    def __init__(self, redis_url: str, *, daily_quota: int = 2000):
        self._redis = redis_async.from_url(redis_url, decode_responses=True)
        self._daily_quota = daily_quota

    @classmethod
    def from_redis(cls, redis_client, *, daily_quota: int = 2000) -> "QuotaClient":
        """Test-only constructor: inject a pre-built (fake)redis client."""
        inst = cls.__new__(cls)
        inst._redis = redis_client
        inst._daily_quota = daily_quota
        return inst

    async def consume(self, install_uuid: str) -> int:
        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        key = f"vibemix:quota:{install_uuid}:{today}"

        async with self._redis.pipeline(transaction=False) as pipe:
            pipe.incr(key)
            pipe.expire(key, 86400, nx=True)
            count, _ttl_set = await pipe.execute()

        if count > self._daily_quota:
            now = datetime.now(tz=timezone.utc)
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            retry_after = max(1, int((tomorrow - now).total_seconds()))
            raise QuotaExceeded(retry_after_seconds=retry_after)

        return count

    async def close(self) -> None:
        await self._redis.aclose()
