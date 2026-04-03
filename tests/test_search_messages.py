import json
from collections.abc import Callable

import httpx
import pytest

from slack_cli.client import BASE_URL, SlackClient
from slack_cli.commands.search import search_messages


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


async def test_search_messages_returns_matches(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "text": "deploy failed",
                            "user": "U123",
                            "channel": {"id": "C456", "name": "ops"},
                            "ts": "1234567890.123456",
                            "permalink": "https://slack.com/archives/C456/p1234",
                        }
                    ],
                    "paging": {"count": 20, "total": 1, "page": 1, "pages": 1},
                },
            },
        )

    client = _make_client(handler)
    await search_messages(client, query="deploy failed")

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["text"] == "deploy failed"
    assert out[0]["channel"]["name"] == "ops"


async def test_search_messages_public_only_filters_private(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "text": "public msg",
                            "channel": {"id": "C1", "name": "general", "is_private": False},
                            "ts": "1",
                            "permalink": "https://slack.com/1",
                        },
                        {
                            "text": "private msg",
                            "channel": {"id": "C2", "name": "secret", "is_private": True},
                            "ts": "2",
                            "permalink": "https://slack.com/2",
                        },
                        {
                            "text": "dm msg",
                            "channel": {"id": "D1", "name": "dm", "is_im": True},
                            "ts": "3",
                            "permalink": "https://slack.com/3",
                        },
                    ],
                    "paging": {"count": 20, "total": 3, "page": 1, "pages": 1},
                },
            },
        )

    client = _make_client(handler)
    await search_messages(client, query="msg", public_only=True)

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["text"] == "public msg"


async def test_search_messages_public_only_paginates_until_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With public_only=True, should keep fetching pages until limit public results are found."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "messages": {
                        "matches": [
                            {
                                "text": "public1",
                                "channel": {"id": "C1", "name": "general"},
                                "ts": "1",
                                "permalink": "https://slack.com/1",
                            },
                            {
                                "text": "private1",
                                "channel": {"id": "C2", "name": "secret", "is_private": True},
                                "ts": "2",
                                "permalink": "https://slack.com/2",
                            },
                        ],
                        "paging": {"count": 2, "total": 4, "page": 1, "pages": 2},
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "text": "public2",
                            "channel": {"id": "C3", "name": "ops"},
                            "ts": "3",
                            "permalink": "https://slack.com/3",
                        },
                    ],
                    "paging": {"count": 2, "total": 4, "page": 2, "pages": 2},
                },
            },
        )

    client = _make_client(handler)
    await search_messages(client, query="test", public_only=True, limit=2)

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[0]["text"] == "public1"
    assert out[1]["text"] == "public2"
