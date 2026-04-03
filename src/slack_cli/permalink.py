import re
from urllib.parse import parse_qs, urlparse

_PERMALINK_RE = re.compile(r"/archives/([A-Z0-9]+)/p(\d{10})(\d{6})")


def parse_slack_url(url: str) -> tuple[str, str, str | None]:
    """Parse a Slack permalink URL into (channel_id, ts, thread_ts)."""
    m = _PERMALINK_RE.search(url)
    if not m:
        raise ValueError(f"Not a valid Slack permalink: {url}")
    channel_id = m.group(1)
    ts = f"{m.group(2)}.{m.group(3)}"
    thread_ts = parse_qs(urlparse(url).query).get("thread_ts", [None])[0]
    return channel_id, ts, thread_ts
