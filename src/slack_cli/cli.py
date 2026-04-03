import asyncio
from collections.abc import Awaitable, AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import cyclopts

from slack_cli.auth.command import DEFAULT_CONFIG_PATH, run_auth
from slack_cli.client import SlackClient
from slack_cli.commands.read import (
    list_channels,
    read_canvas,
    read_channel,
    read_channel_info,
    read_file,
    read_thread,
    read_user,
)
from slack_cli.commands.search import search_channels, search_messages, search_users
from slack_cli.tokens import resolve_tokens
from slack_cli.validation import validate_tokens

app = cyclopts.App(name="slack-cli", help="Read-only Slack CLI for coding agents.")
search_app = cyclopts.App(name="search", help="Search Slack data.")
read_app = cyclopts.App(name="read", help="Read Slack data.")
list_app = cyclopts.App(name="list", help="List Slack data.")
app.command(search_app)
app.command(read_app)
app.command(list_app)


@asynccontextmanager
async def _get_client(
    token: str | None = None, cookie: str | None = None
) -> AsyncIterator[SlackClient]:
    xoxc, xoxd = resolve_tokens(
        flag_token=token, flag_cookie=cookie, config_path=DEFAULT_CONFIG_PATH
    )
    async with SlackClient(xoxc=xoxc, xoxd=xoxd) as client:
        await validate_tokens(client)
        yield client


def _run_with_client(
    fn: Callable[[SlackClient], Awaitable[None]],
    token: str | None,
    cookie: str | None,
) -> None:
    async def _run() -> None:
        async with _get_client(token, cookie) as client:
            await fn(client)

    asyncio.run(_run())


@app.command
def auth() -> None:
    """Extract tokens from Slack desktop app and save to config."""
    asyncio.run(run_auth())


@search_app.command(name="messages")
def search_messages_cmd(
    query: str,
    *,
    public_only: bool = False,
    limit: int = 100,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Search Slack messages."""
    _run_with_client(
        lambda c: search_messages(c, query=query, public_only=public_only, limit=limit),
        token,
        cookie,
    )


@search_app.command(name="channels")
def search_channels_cmd(
    query: str,
    *,
    limit: int = 100,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Search channels by name or description."""
    _run_with_client(lambda c: search_channels(c, query=query, limit=limit), token, cookie)


@search_app.command(name="users")
def search_users_cmd(
    query: str,
    *,
    limit: int = 100,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Search users by name, email, or role."""
    _run_with_client(lambda c: search_users(c, query=query, limit=limit), token, cookie)


@read_app.command(name="channel")
def read_channel_cmd(
    channel_id: str = "",
    *,
    url: str | None = None,
    limit: int = 100,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch message history of a channel. Use --url with a Slack permalink instead of channel_id."""
    if url:
        from slack_cli.permalink import parse_slack_url

        channel_id, _, _ = parse_slack_url(url)
    if not channel_id:
        raise SystemExit("Provide channel_id or use --url with a Slack permalink.")
    _run_with_client(lambda c: read_channel(c, channel_id=channel_id, limit=limit), token, cookie)


@read_app.command(name="thread")
def read_thread_cmd(
    channel_id: str = "",
    thread_ts: str = "",
    *,
    url: str | None = None,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch all replies in a thread. Use --url with a Slack permalink instead of positional args."""
    if url:
        from slack_cli.permalink import parse_slack_url

        channel_id, ts, thread_ts_parsed = parse_slack_url(url)
        thread_ts = thread_ts_parsed or ts
    if not channel_id or not thread_ts:
        raise SystemExit("Provide channel_id and thread_ts, or use --url with a Slack permalink.")
    _run_with_client(
        lambda c: read_thread(c, channel_id=channel_id, thread_ts=thread_ts), token, cookie
    )


@read_app.command(name="channel-info")
def read_channel_info_cmd(
    channel_id: str,
    *,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch channel metadata: name, topic, purpose, members count."""
    _run_with_client(lambda c: read_channel_info(c, channel_id=channel_id), token, cookie)


@read_app.command(name="user")
def read_user_cmd(
    user_id: str,
    *,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch a user's full profile."""
    _run_with_client(lambda c: read_user(c, user_id=user_id), token, cookie)


@read_app.command(name="canvas")
def read_canvas_cmd(
    canvas_id: str,
    *,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch a canvas document as markdown."""
    _run_with_client(lambda c: read_canvas(c, canvas_id=canvas_id), token, cookie)


@read_app.command(name="file")
def read_file_cmd(
    *,
    url: str,
    output: str | None = None,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """Fetch a file by URL and write raw bytes to stdout, or save to disk with --output."""
    _run_with_client(
        lambda c: read_file(c, url=url, output=Path(output) if output else None), token, cookie
    )


@list_app.command(name="channels")
def list_channels_cmd(
    *,
    limit: int = 100,
    token: str | None = None,
    cookie: str | None = None,
) -> None:
    """List all visible channels."""
    _run_with_client(lambda c: list_channels(c, limit=limit), token, cookie)


def main() -> None:
    app()
