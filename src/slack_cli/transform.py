import html
import re
from datetime import datetime, timezone
from typing import Any, Literal

from slack_cli.client import SlackClient


def _ts_to_dt(ts: str) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def mrkdwn_to_plain(text: str, *, user_cache: dict[str, str] | None = None) -> str:
    """Convert Slack mrkdwn to plain text."""
    cache = user_cache or {}
    text = re.sub(
        r"<@([UW][A-Z0-9]+)>",
        lambda m: f"@{cache.get(m.group(1), m.group(1))}",
        text,
    )
    text = re.sub(
        r"<!([^>|]+?)(?:\^[^|>]*)?(?:\|([^>]*))?(?:\^[^>]*)?>",
        lambda m: m.group(2) or f"@{m.group(1)}",
        text,
    )
    text = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", text)
    text = re.sub(r"<#([A-Z0-9]+)>", r"#\1", text)
    text = re.sub(r"<[^>]+\|([^>]+)>", r"\1", text)
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)
    return html.unescape(text)


_SLACK_URL_RE = re.compile(r"<(https?://[^>]*?/archives/[A-Z0-9]+/p\d{16}[^>]*)>")


def extract_thread_refs(text: str) -> list[dict[str, str]]:
    """Extract Slack permalink references from message text."""
    from slack_cli.permalink import parse_slack_url

    refs = []
    for m in _SLACK_URL_RE.finditer(text):
        try:
            channel_id, ts, thread_ts = parse_slack_url(m.group(1))
            refs.append({"channel_id": channel_id, "thread_ts": thread_ts or ts})
        except ValueError:
            continue
    return refs


_FILE_KEYS = {
    "name",
    "permalink",
    "filetype",
    "mimetype",
    "size",
    "url_private_download",
    "preview",
    "plain_text",
}
_ATTACHMENT_KEYS = {"title", "text"}
_REACTION_KEYS = {"name", "count"}

_BASE_KEYS = {"text", "user", "ts", "thread_ts", "edited"}
_CHANNEL_EXTRA = {"reply_count", "latest_reply"}
_SEARCH_EXTRA = {"reply_count", "latest_reply", "channel", "permalink"}
_THREAD_EXTRA = {"parent_user_id"}


def filter_message(
    msg: dict[str, Any],
    context: Literal["channel", "thread", "search"] = "channel",
) -> dict[str, Any]:
    """Filter a raw Slack message to only agent-useful fields."""
    context_keys = {"channel": _CHANNEL_EXTRA, "search": _SEARCH_EXTRA, "thread": _THREAD_EXTRA}
    keep_keys = _BASE_KEYS | context_keys[context]

    result: dict[str, Any] = {k: msg[k] for k in keep_keys if k in msg}

    if "ts" in result:
        result["datetime"] = _ts_to_dt(result["ts"])

    if "edited" in result and "ts" in result["edited"]:
        result["edited"] = {**result["edited"], "datetime": _ts_to_dt(result["edited"]["ts"])}

    if "reactions" in msg:
        result["reactions"] = [
            {k: r[k] for k in _REACTION_KEYS if k in r} for r in msg["reactions"]
        ]

    if "files" in msg:
        result["files"] = [{k: f[k] for k in _FILE_KEYS if k in f} for f in msg["files"]]

    if "attachments" in msg:
        filtered = [{k: a[k] for k in _ATTACHMENT_KEYS if k in a} for a in msg["attachments"]]
        non_empty = [a for a in filtered if a]
        if non_empty:
            result["attachments"] = non_empty

    if "text" in result:
        refs = extract_thread_refs(result["text"])
        if refs:
            result["thread_refs"] = refs

    return result


async def _build_user_cache(
    client: SlackClient,
    user_ids: set[str],
) -> dict[str, str]:
    import asyncio

    async def _fetch(uid: str) -> tuple[str, str]:
        data = await client.api_call("users.info", params={"user": uid})
        info = data.get("user", {})
        return uid, info.get("real_name") or info.get("name", uid)

    results = await asyncio.gather(*[_fetch(uid) for uid in user_ids])
    return dict(results)


async def filter_and_resolve(
    client: SlackClient,
    messages: list[dict[str, Any]],
    context: Literal["channel", "thread", "search"],
) -> list[dict[str, Any]]:
    """Filter messages, resolve user IDs to names, and clean mrkdwn."""
    filtered = [filter_message(m, context=context) for m in messages]
    user_ids = {m["user"] for m in filtered if "user" in m}
    cache = await _build_user_cache(client, user_ids)
    return [
        {
            **m,
            "user": cache.get(m.get("user", ""), m.get("user", "")),
            **({"text": mrkdwn_to_plain(m["text"], user_cache=cache)} if "text" in m else {}),
        }
        for m in filtered
    ]
