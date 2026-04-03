import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from slack_cli.client import BASE_URL, SlackClient
from slack_cli.commands.search import search_channels, search_users
from slack_cli.commands.read import (
    list_channels,
    read_canvas,
    read_channel,
    read_channel_info,
    read_file,
    read_thread,
    read_user,
)


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


async def test_search_channels_filters_by_name(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "channels": [
                    {
                        "id": "C1",
                        "name": "ops-alerts",
                        "topic": {"value": ""},
                        "purpose": {"value": ""},
                        "num_members": 10,
                        "is_private": False,
                    },
                    {
                        "id": "C2",
                        "name": "general",
                        "topic": {"value": ""},
                        "purpose": {"value": ""},
                        "num_members": 50,
                        "is_private": False,
                    },
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    await search_channels(client, query="ops")

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["name"] == "ops-alerts"


async def test_search_users_filters_by_name(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "members": [
                    {
                        "id": "U1",
                        "name": "alice",
                        "real_name": "Alice Example",
                        "profile": {"email": "a@test.com", "title": "Eng", "status_text": ""},
                    },
                    {
                        "id": "U2",
                        "name": "bob",
                        "real_name": "Bob Example",
                        "profile": {"email": "b@test.com", "title": "PM", "status_text": ""},
                    },
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    await search_users(client, query="alice")

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["name"] == "alice"


async def test_read_channel_returns_messages(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [
                    {"text": "hello", "user": "U1", "ts": "123"},
                    {"text": "world", "user": "U2", "ts": "124"},
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    await read_channel(client, channel_id="C456")

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[0]["text"] == "hello"


async def test_read_thread_returns_replies(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "messages": [
                    {"text": "parent", "user": "U1", "ts": "100"},
                    {"text": "reply", "user": "U2", "ts": "101"},
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    await read_thread(client, channel_id="C456", thread_ts="100")

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 2
    assert out[1]["text"] == "reply"


async def test_read_user_returns_profile(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "user": {
                    "id": "U1",
                    "name": "alice",
                    "real_name": "Alice Example",
                    "profile": {"email": "a@test.com", "title": "Eng", "status_text": "coding"},
                },
            },
        )

    client = _make_client(handler)
    await read_user(client, user_id="U1")

    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "alice"
    assert out["profile"]["email"] == "a@test.com"


async def test_list_channels_returns_all(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "channels": [
                    {
                        "id": "C1",
                        "name": "general",
                        "topic": {"value": ""},
                        "purpose": {"value": ""},
                        "num_members": 50,
                        "is_private": False,
                    },
                ],
                "response_metadata": {"next_cursor": ""},
            },
        )

    client = _make_client(handler)
    await list_channels(client)

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]["name"] == "general"


async def test_search_users_warns_at_cap(capsys: pytest.CaptureFixture[str]) -> None:
    users = [
        {
            "id": f"U{i}",
            "name": f"user-{i}",
            "real_name": f"User {i}",
            "profile": {"email": "", "title": ""},
        }
        for i in range(500)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True, "members": users, "response_metadata": {"next_cursor": ""}},
        )

    client = _make_client(handler)
    await search_users(client, query="user")

    captured = capsys.readouterr()
    assert "500" in captured.err
    assert "incomplete" in captured.err.lower()


async def test_search_channels_warns_at_cap(capsys: pytest.CaptureFixture[str]) -> None:
    channels = [
        {"id": f"C{i}", "name": f"chan-{i}", "topic": {"value": ""}, "purpose": {"value": ""}}
        for i in range(500)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True, "channels": channels, "response_metadata": {"next_cursor": ""}},
        )

    client = _make_client(handler)
    await search_channels(client, query="chan")

    captured = capsys.readouterr()
    assert "500" in captured.err
    assert "incomplete" in captured.err.lower()


async def test_read_canvas_returns_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "files.info" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "file": {
                        "id": "F123",
                        "title": "My Canvas",
                        "url_private": "https://files.slack.com/canvas",
                        "created_by": "U1",
                    },
                },
            )
        # GET to url_private
        return httpx.Response(
            200,
            content=b"<h1>Title</h1><p>Some content</p>",
            headers={"content-type": "text/html"},
        )

    client = _make_client(handler)
    await read_canvas(client, canvas_id="F123")

    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "F123"
    assert out["title"] == "My Canvas"
    assert "Title" in out["content"]
    assert "<h1>" not in out["content"]


async def test_read_channel_info_returns_channel_object(
    capsys: pytest.CaptureFixture[str],
) -> None:

    channel_data = {
        "id": "C123",
        "name": "general",
        "topic": {"value": "Company-wide"},
        "purpose": {"value": "General chat"},
        "num_members": 42,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "channel": channel_data})

    client = _make_client(handler)
    await read_channel_info(client, channel_id="C123")

    out = json.loads(capsys.readouterr().out)
    assert out["name"] == "general"
    assert out["num_members"] == 42
    assert out["topic"]["value"] == "Company-wide"


_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-image-data"
_FILE_URL = "https://files.slack.com/files-pri/T1-F1/image.png"


def _file_client() -> SlackClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_PNG_BYTES)

    return _make_client(handler)


async def test_read_file_writes_bytes_to_stdout(capfdbinary: pytest.CaptureFixture[bytes]) -> None:
    await read_file(_file_client(), url=_FILE_URL)

    assert capfdbinary.readouterr().out == _PNG_BYTES


async def test_read_file_writes_bytes_to_disk(tmp_path: Path) -> None:
    out_path = tmp_path / "image.png"

    await read_file(_file_client(), url=_FILE_URL, output=out_path)

    assert out_path.read_bytes() == _PNG_BYTES
