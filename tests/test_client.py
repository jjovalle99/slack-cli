from collections.abc import Callable

import httpx
import pytest

from slack_cli.client import BASE_URL, SlackAPIError, SlackClient


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    xoxc: str = "xoxc-test-token",
    xoxd: str = "xoxd-test-cookie",
) -> SlackClient:
    client = SlackClient(xoxc=xoxc, xoxd=xoxd)
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=BASE_URL,
        headers=client._http.headers,
    )
    return client


async def test_api_call_sends_auth_headers() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    client = _make_client(handler)
    await client.api_call("auth.test")

    req = captured[0]
    assert req.headers["authorization"] == "Bearer xoxc-test-token"
    assert "d=xoxd-test-cookie" in req.headers["cookie"]


async def test_api_call_returns_parsed_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "user": "testuser"})

    client = _make_client(handler)
    result = await client.api_call("auth.test")
    assert result["ok"] is True
    assert result["user"] == "testuser"


async def test_api_call_posts_to_correct_url_with_params() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    client = _make_client(handler)
    await client.api_call("search.messages", params={"query": "hello"})

    req = captured[0]
    assert req.url.path == "/api/search.messages"
    assert req.content == b"query=hello"


async def test_api_call_raises_on_slack_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

    client = _make_client(handler)
    with pytest.raises(SlackAPIError, match="invalid_auth"):
        await client.api_call("auth.test")


async def test_api_call_retries_on_429(capsys: pytest.CaptureFixture[str]) -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True, "retried": True})

    client = _make_client(handler)
    result = await client.api_call("auth.test")
    assert result["retried"] is True
    assert call_count == 2
    assert "rate limited" in capsys.readouterr().err.lower()


async def test_fetch_url_bytes_returns_binary() -> None:
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=image_bytes)

    client = _make_client(handler)
    result = await client.fetch_url_bytes("https://files.slack.com/F1/image.png")
    assert result == image_bytes
