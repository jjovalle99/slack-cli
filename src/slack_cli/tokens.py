import os
from pathlib import Path
from urllib.parse import unquote

from slack_cli.config import load_config


def _normalize_xoxd(value: str) -> str:
    if "%" in value:
        return unquote(value)
    return value


def resolve_tokens(
    *,
    flag_token: str | None = None,
    flag_cookie: str | None = None,
    config_path: Path | None = None,
) -> tuple[str, str]:
    """Resolve xoxc/xoxd token pair. Priority: flags > env vars > config file.

    Raises:
        SystemExit: If no valid token pair is found.
    """
    xoxc = flag_token or os.environ.get("SLACK_XOXC_TOKEN")
    xoxd = flag_cookie or os.environ.get("SLACK_XOXD_TOKEN")
    xoxd_from_user = xoxd is not None

    if not (xoxc and xoxd) and config_path:
        config = load_config(config_path)
        if config:
            xoxc = xoxc or config.get("xoxc")
            if not xoxd:
                xoxd = config.get("xoxd")
                xoxd_from_user = False

    if not (xoxc and xoxd):
        raise SystemExit(
            "No tokens found. Run `slack-cli auth` or set SLACK_XOXC_TOKEN and SLACK_XOXD_TOKEN."
        )

    if xoxd_from_user:
        xoxd = _normalize_xoxd(xoxd)

    return xoxc, xoxd
