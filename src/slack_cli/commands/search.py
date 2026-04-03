import sys
from typing import Any

from slack_cli.client import SlackClient
from slack_cli.output import write_success
from slack_cli.pagination import paginate
from slack_cli.transform import filter_and_resolve

SEARCH_FETCH_CAP = 500


def _warn_if_at_cap(items: list[dict[str, Any]], kind: str) -> None:
    if len(items) >= SEARCH_FETCH_CAP:
        print(
            f"Warning: fetched {SEARCH_FETCH_CAP} {kind} (cap reached). "
            f"Results may be incomplete in large workspaces.",
            file=sys.stderr,
        )


async def search_messages(
    client: SlackClient,
    *,
    query: str,
    public_only: bool = False,
    limit: int = 100,
) -> None:
    """Search Slack messages. Outputs JSON array of matches to stdout."""
    params: dict[str, Any] = {"query": query, "count": min(limit, 100)}

    data = await client.api_call("search.messages", params=params)
    matches: list[dict[str, Any]] = data.get("messages", {}).get("matches", [])

    # search.messages uses page-based pagination, not cursors
    paging = data.get("messages", {}).get("paging", {})
    total_pages = paging.get("pages", 1)
    page = 2

    if public_only:
        matches = [m for m in matches if not _is_private(m)]

    while len(matches) < limit and page <= total_pages:
        params["page"] = page
        data = await client.api_call("search.messages", params=params)
        page_matches = data.get("messages", {}).get("matches", [])
        matches.extend(m for m in page_matches if not public_only or not _is_private(m))
        page += 1

    write_success(await filter_and_resolve(client, matches[:limit], "search"))


def _is_private(match: dict[str, Any]) -> bool:
    ch = match.get("channel", {})
    return bool(ch.get("is_private") or ch.get("is_im") or ch.get("is_mpim"))


async def search_channels(
    client: SlackClient,
    *,
    query: str,
    limit: int = 100,
) -> None:
    """Search channels by name/topic/purpose. Client-side filter on conversations.list."""

    all_channels = await paginate(
        client, "conversations.list", response_key="channels", limit=SEARCH_FETCH_CAP
    )
    _warn_if_at_cap(all_channels, "channels")
    q = query.lower()
    matched = [
        ch
        for ch in all_channels
        if q in ch.get("name", "").lower()
        or q in ch.get("topic", {}).get("value", "").lower()
        or q in ch.get("purpose", {}).get("value", "").lower()
    ]
    write_success(matched[:limit])


async def search_users(
    client: SlackClient,
    *,
    query: str,
    limit: int = 100,
) -> None:
    """Search users by name/email/title. Client-side filter on users.list."""

    all_users = await paginate(client, "users.list", response_key="members", limit=SEARCH_FETCH_CAP)
    _warn_if_at_cap(all_users, "users")
    q = query.lower()
    matched = [
        u
        for u in all_users
        if q in u.get("name", "").lower()
        or q in u.get("real_name", "").lower()
        or q in u.get("profile", {}).get("email", "").lower()
        or q in u.get("profile", {}).get("title", "").lower()
    ]
    write_success(matched[:limit])
