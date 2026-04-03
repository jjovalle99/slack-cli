import sys
from typing import Any

from slack_cli.client import SlackAPIError, SlackClient


async def validate_tokens(client: SlackClient) -> dict[str, Any]:
    """Call auth.test to verify tokens. Exits on failure with actionable message."""
    try:
        return await client.api_call("auth.test")
    except SlackAPIError as exc:
        print(f"Token validation failed: {exc.error}", file=sys.stderr)
        print("Run `slack-cli auth` to re-extract tokens.", file=sys.stderr)
        raise SystemExit(f"Token validation failed: {exc.error}") from exc
