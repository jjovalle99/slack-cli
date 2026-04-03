from collections.abc import Callable

import httpx

from slack_cli.client import BASE_URL, SlackClient
from slack_cli.transform import (
    extract_thread_refs,
    filter_and_resolve,
    filter_message,
    mrkdwn_to_plain,
)


def test_extract_thread_refs_single() -> None:
    text = "check this <https://team.slack.com/archives/C1234ABC/p1734567890123456>"
    refs = extract_thread_refs(text)
    assert len(refs) == 1
    assert refs[0]["channel_id"] == "C1234ABC"
    assert refs[0]["thread_ts"] == "1734567890.123456"


def test_extract_thread_refs_multiple() -> None:
    text = (
        "<https://t.slack.com/archives/C111/p1000000000000000> and "
        "<https://t.slack.com/archives/C222/p2000000000000000>"
    )
    refs = extract_thread_refs(text)
    assert len(refs) == 2
    assert refs[0]["channel_id"] == "C111"
    assert refs[1]["channel_id"] == "C222"


def test_extract_thread_refs_no_refs() -> None:
    assert extract_thread_refs("just plain text") == []
    assert extract_thread_refs("<https://example.com>") == []


def test_filter_message_includes_thread_refs() -> None:
    raw = {
        "text": "see <https://t.slack.com/archives/C999/p1234567890123456>",
        "user": "U1",
        "ts": "1",
    }
    result = filter_message(raw)
    assert len(result["thread_refs"]) == 1
    assert result["thread_refs"][0]["channel_id"] == "C999"


def test_filter_message_omits_thread_refs_when_none() -> None:
    raw = {"text": "no links here", "user": "U1", "ts": "1"}
    result = filter_message(raw)
    assert "thread_refs" not in result


def test_mrkdwn_to_plain_decodes_html_entities() -> None:
    assert mrkdwn_to_plain("one &amp; two &lt;three&gt;") == "one & two <three>"


def test_mrkdwn_to_plain_channel_mentions() -> None:
    assert mrkdwn_to_plain("see <#C1234ABC|general>") == "see #general"
    assert mrkdwn_to_plain("check <#C999>") == "check #C999"


def test_mrkdwn_to_plain_urls_and_mailto() -> None:
    assert mrkdwn_to_plain("<https://example.com>") == "https://example.com"
    assert mrkdwn_to_plain("<https://example.com|Example>") == "Example"
    assert mrkdwn_to_plain("<mailto:a@b.com|a@b.com>") == "a@b.com"


def test_mrkdwn_to_plain_special_commands() -> None:
    assert mrkdwn_to_plain("<!here>") == "@here"
    assert mrkdwn_to_plain("<!channel>") == "@channel"
    assert mrkdwn_to_plain("<!everyone>") == "@everyone"
    assert mrkdwn_to_plain("<!here|@here>") == "@here"
    assert mrkdwn_to_plain("<!subteam^S123|@oncall>") == "@oncall"


def test_mrkdwn_to_plain_user_mentions() -> None:
    assert mrkdwn_to_plain("<@U1234ABC>") == "@U1234ABC"
    assert mrkdwn_to_plain("<@U1234ABC>", user_cache={"U1234ABC": "Alice"}) == "@Alice"
    assert mrkdwn_to_plain("<@W5678>", user_cache={"W5678": "Bot"}) == "@Bot"
    assert mrkdwn_to_plain("<@U9999>", user_cache={"U0000": "Other"}) == "@U9999"


async def test_filter_and_resolve_cleans_mrkdwn_in_text() -> None:

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"ok": True, "user": {"id": "U1", "real_name": "Alice", "name": "alice"}},
        )

    client = _make_client(handler)
    messages = [{"text": "hey <@U1> check &amp; <#C99|general>", "user": "U1", "ts": "1"}]
    result = await filter_and_resolve(client, messages, context="channel")
    assert result[0]["text"] == "hey @Alice check & #general"


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


async def test_filter_and_resolve_replaces_user_ids_with_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        if "user=U1" in body:
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "user": {"id": "U1", "real_name": "Alice Example", "name": "alice"},
                },
            )
        return httpx.Response(
            200,
            json={"ok": True, "user": {"id": "U2", "real_name": "Bob Smith", "name": "bob"}},
        )

    client = _make_client(handler)
    messages = [
        {"text": "hello", "user": "U1", "ts": "1"},
        {"text": "hi", "user": "U2", "ts": "2"},
        {"text": "again", "user": "U1", "ts": "3"},
    ]
    result = await filter_and_resolve(client, messages, context="channel")
    assert result[0]["user"] == "Alice Example"
    assert result[1]["user"] == "Bob Smith"
    assert result[2]["user"] == "Alice Example"


def test_filter_message_keeps_core_fields() -> None:
    raw = {
        "text": "deploy failed",
        "user": "U123",
        "ts": "1234567890.123456",
        "thread_ts": "1234567890.123456",
        "type": "message",
        "team": "T059",
        "client_msg_id": "abc-123",
        "blocks": [{"type": "rich_text", "elements": []}],
        "subscribed": False,
        "saved": False,
        "is_locked": False,
    }
    result = filter_message(raw)
    assert result["text"] == "deploy failed"
    assert result["user"] == "U123"
    assert result["ts"] == "1234567890.123456"
    assert result["thread_ts"] == "1234567890.123456"
    assert "type" not in result
    assert "team" not in result
    assert "client_msg_id" not in result
    assert "blocks" not in result
    assert "subscribed" not in result


def test_filter_message_keeps_reactions() -> None:
    raw = {
        "text": "lgtm",
        "user": "U1",
        "ts": "1",
        "reactions": [
            {"name": "white_check_mark", "count": 3, "users": ["U1", "U2", "U3"]},
        ],
    }
    result = filter_message(raw)
    assert len(result["reactions"]) == 1
    assert result["reactions"][0]["name"] == "white_check_mark"
    assert result["reactions"][0]["count"] == 3
    assert "users" not in result["reactions"][0]


def test_filter_message_keeps_files_with_content_fields() -> None:
    raw = {
        "text": "check this",
        "user": "U1",
        "ts": "1",
        "files": [
            {
                "id": "F1",
                "name": "error.log",
                "permalink": "https://slack.com/files/F1",
                "filetype": "log",
                "mimetype": "text/plain",
                "pretty_type": "Log",
                "size": 4096,
                "url_private_download": "https://files.slack.com/F1/download",
                "preview": "Error: connection refused",
                "plain_text": "Error: connection refused\nRetrying...",
                "thumb_64": "https://thumb",
                "display_as_bot": False,
            },
        ],
    }
    result = filter_message(raw)
    assert len(result["files"]) == 1
    f = result["files"][0]
    assert f["name"] == "error.log"
    assert f["permalink"] == "https://slack.com/files/F1"
    assert f["filetype"] == "log"
    assert f["mimetype"] == "text/plain"
    assert f["size"] == 4096
    assert f["url_private_download"] == "https://files.slack.com/F1/download"
    assert f["preview"] == "Error: connection refused"
    assert f["plain_text"] == "Error: connection refused\nRetrying..."
    assert "thumb_64" not in f
    assert "display_as_bot" not in f


def test_filter_message_keeps_attachment_text() -> None:
    raw = {
        "text": "see this PR",
        "user": "U1",
        "ts": "1",
        "attachments": [
            {
                "title": "Fix auth bug #123",
                "text": "This PR fixes the login timeout issue",
                "title_link": "https://github.com/org/repo/pull/123",
                "color": "36a64f",
                "footer": "GitHub",
                "author_name": "alice",
                "from_url": "https://github.com/org/repo/pull/123",
            },
        ],
    }
    result = filter_message(raw)
    assert len(result["attachments"]) == 1
    a = result["attachments"][0]
    assert a["title"] == "Fix auth bug #123"
    assert a["text"] == "This PR fixes the login timeout issue"
    assert "color" not in a
    assert "footer" not in a


def test_filter_message_drops_empty_attachments() -> None:
    raw = {
        "text": "hello",
        "user": "U1",
        "ts": "1",
        "attachments": [{"color": "36a64f", "footer": "GitHub"}],
    }
    result = filter_message(raw)
    assert "attachments" not in result


def test_filter_message_keeps_edited() -> None:
    raw = {
        "text": "corrected info",
        "user": "U1",
        "ts": "1",
        "edited": {"user": "U1", "ts": "2"},
    }
    result = filter_message(raw)
    assert result["edited"]["ts"] == "2"


def test_filter_message_keeps_reply_count_in_channel_mode() -> None:
    raw = {
        "text": "question",
        "user": "U1",
        "ts": "1",
        "reply_count": 5,
        "reply_users": ["U2", "U3"],
        "reply_users_count": 2,
        "latest_reply": "3",
    }
    result = filter_message(raw, context="channel")
    assert result["reply_count"] == 5
    assert result["latest_reply"] == "3"
    assert "reply_users" not in result
    assert "reply_users_count" not in result


def test_filter_message_adds_datetime_from_ts() -> None:
    raw = {"text": "hello", "user": "U1", "ts": "1734567890.123456"}
    result = filter_message(raw)
    assert result["datetime"] == "2024-12-19T00:24:50.123456Z"


def test_filter_message_adds_datetime_to_edited() -> None:
    raw = {
        "text": "corrected",
        "user": "U1",
        "ts": "1734567890.123456",
        "edited": {"user": "U1", "ts": "1734567900.000000"},
    }
    result = filter_message(raw)
    assert result["edited"]["datetime"] == "2024-12-19T00:25:00Z"


def test_filter_message_drops_reply_count_in_thread_mode() -> None:
    raw = {
        "text": "reply",
        "user": "U1",
        "ts": "1",
        "reply_count": 5,
        "latest_reply": "3",
        "parent_user_id": "U0",
    }
    result = filter_message(raw, context="thread")
    assert "reply_count" not in result
    assert "latest_reply" not in result
    assert result["parent_user_id"] == "U0"
