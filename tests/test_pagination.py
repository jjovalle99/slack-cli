from collections.abc import Callable

import httpx

from slack_cli.client import BASE_URL, SlackClient
from slack_cli.pagination import paginate


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> SlackClient:
    client = SlackClient(xoxc="xoxc-test", xoxd="xoxd-test")
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=BASE_URL,
        headers=client._http.headers,
    )
    return client


async def test_paginate_follows_cursors() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "members": [{"id": "U1"}, {"id": "U2"}],
                    "response_metadata": {"next_cursor": "cursor_page2"},
                },
            )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "members": [{"id": "U3"}],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    results = await paginate(client, "users.list", response_key="members")
    assert [r["id"] for r in results] == ["U1", "U2", "U3"]
    assert call_count == 2


async def test_paginate_respects_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "members": [{"id": "U1"}, {"id": "U2"}, {"id": "U3"}],
                "response_metadata": {"next_cursor": "more"},
            },
        )

    client = _make_client(handler)
    results = await paginate(client, "users.list", response_key="members", limit=2)
    assert len(results) == 2
