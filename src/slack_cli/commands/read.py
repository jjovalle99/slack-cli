import sys
from pathlib import Path

from slack_cli.client import SlackClient
from slack_cli.output import write_success
from slack_cli.pagination import paginate
from slack_cli.transform import filter_and_resolve


async def read_file(
    client: SlackClient,
    *,
    url: str,
    output: Path | None = None,
) -> None:
    data = await client.fetch_url_bytes(url)
    if output:
        output.write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


async def read_channel(
    client: SlackClient,
    *,
    channel_id: str,
    limit: int = 100,
) -> None:
    """Fetch message history of a channel."""
    messages = await paginate(
        client,
        "conversations.history",
        response_key="messages",
        params={"channel": channel_id},
        limit=limit,
    )
    write_success(await filter_and_resolve(client, messages, "channel"))


async def read_thread(
    client: SlackClient,
    *,
    channel_id: str,
    thread_ts: str,
) -> None:
    """Fetch all replies in a thread."""
    messages = await paginate(
        client,
        "conversations.replies",
        response_key="messages",
        params={"channel": channel_id, "ts": thread_ts},
        limit=1000,
    )
    write_success(await filter_and_resolve(client, messages, "thread"))


async def read_channel_info(
    client: SlackClient,
    *,
    channel_id: str,
) -> None:
    """Fetch channel metadata: name, topic, purpose, members count."""
    data = await client.api_call("conversations.info", params={"channel": channel_id})
    write_success(data["channel"])


async def read_user(
    client: SlackClient,
    *,
    user_id: str,
) -> None:
    """Fetch a user's full profile."""
    data = await client.api_call("users.info", params={"user": user_id})
    write_success(data["user"])


async def list_channels(
    client: SlackClient,
    *,
    limit: int = 100,
) -> None:
    """List all visible channels."""
    channels = await paginate(client, "conversations.list", response_key="channels", limit=limit)
    write_success(channels)


async def read_canvas(
    client: SlackClient,
    *,
    canvas_id: str,
) -> None:
    """Fetch a canvas and return its content as markdown."""
    import markdownify  # noqa: E402

    data = await client.api_call("files.info", params={"file": canvas_id})
    file_info: dict[str, object] = data["file"]
    url_private = str(file_info.get("url_private", ""))

    html = await client.fetch_url(url_private)
    content: str = markdownify.markdownify(html)

    write_success(
        {
            "id": file_info.get("id"),
            "title": file_info.get("title"),
            "content": content.strip(),
            "created_by": file_info.get("created_by"),
        }
    )
