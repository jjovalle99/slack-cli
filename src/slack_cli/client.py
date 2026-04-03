import asyncio
import sys
from typing import Any

import httpx

BASE_URL = "https://slack.com/api"
_ALLOWED_HOSTS = (".slack.com", ".slack-edge.com")


class SlackAPIError(Exception):
    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__(error)


class SlackClient:
    def __init__(self, *, xoxc: str, xoxd: str) -> None:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {xoxc}",
                "Cookie": f"d={xoxd}",
            },
        )

    async def api_call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._http.post(f"/{method}", data=params)

        if response.status_code == 429:
            retry_after = min(int(response.headers.get("Retry-After", "1")), 60)
            print(f"Rate limited by Slack API. Waiting {retry_after}s...", file=sys.stderr)
            await asyncio.sleep(retry_after)
            response = await self._http.post(f"/{method}", data=params)

        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if not data.get("ok"):
            raise SlackAPIError(data.get("error", "unknown_error"))
        return data

    @staticmethod
    def _validate_url(url: str) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not any(host == h.lstrip(".") or host.endswith(h) for h in _ALLOWED_HOSTS):
            msg = f"Refusing to fetch URL with host '{host}' — only *.slack.com allowed"
            raise ValueError(msg)

    async def _fetch(self, url: str) -> httpx.Response:
        self._validate_url(url)
        response = await self._http.get(url)
        response.raise_for_status()
        return response

    async def fetch_url(self, url: str) -> str:
        """GET a URL with the same auth headers. Returns response text."""
        return (await self._fetch(url)).text

    async def fetch_url_bytes(self, url: str) -> bytes:
        """GET a URL with the same auth headers. Returns raw bytes."""
        return (await self._fetch(url)).content

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "SlackClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
