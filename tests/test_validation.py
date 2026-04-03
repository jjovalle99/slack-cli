from collections.abc import Callable

import httpx
import pytest

from slack_cli.client import BASE_URL, SlackClient
from slack_cli.validation import validate_tokens


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> SlackClient:
    client = SlackClient(xoxc="xoxc-test", xoxd="xoxd-test")
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=BASE_URL,
        headers=client._http.headers,
    )
    return client


async def test_validate_returns_user_and_team() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "user": "testuser", "team": "Acme Corp"})

    client = _mock_client(handler)
    result = await validate_tokens(client)
    assert result["user"] == "testuser"
    assert result["team"] == "Acme Corp"


async def test_validate_raises_on_invalid_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

    client = _mock_client(handler)
    with pytest.raises(SystemExit, match="invalid_auth"):
        await validate_tokens(client)


async def test_validate_error_does_not_leak_tokens(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "error": "invalid_auth"})

    client = _mock_client(handler)
    with pytest.raises(SystemExit):
        await validate_tokens(client)

    stderr = capsys.readouterr().err
    assert "xoxc-test" not in stderr
    assert "xoxd-test" not in stderr
