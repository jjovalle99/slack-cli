from typing import Any

from slack_cli.client import SlackClient

DEFAULT_LIMIT = 100


async def paginate(
    client: SlackClient,
    method: str,
    *,
    response_key: str,
    params: dict[str, Any] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Auto-paginate a Slack API method that uses cursor-based pagination."""
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    base_params = dict(params) if params else {}

    while len(results) < limit:
        page_params = {**base_params, "limit": min(200, limit - len(results))}
        if cursor:
            page_params["cursor"] = cursor

        data = await client.api_call(method, params=page_params)
        page_items = data.get(response_key, [])
        results.extend(page_items)

        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break

    return results[:limit]
