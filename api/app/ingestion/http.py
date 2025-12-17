from __future__ import annotations

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class ExternalAPIError(Exception):
    pass


async def fetch_json(url: str, *, headers: dict[str, str] | None = None, params: dict | None = None, method: str = "GET", data: dict | None = None) -> dict:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, ExternalAPIError)),
        reraise=True,
    ):
        with attempt:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.request(
                    method, url, headers=headers, params=params, data=data
                )
                if response.status_code >= 500:
                    raise ExternalAPIError(f"Server error {response.status_code}")
                response.raise_for_status()
                return response.json()
    raise ExternalAPIError("Unreachable")
