import pytest

from slack_cli.permalink import parse_slack_url


def test_parse_invalid_url_raises() -> None:
    with pytest.raises(ValueError, match="Not a valid Slack permalink"):
        parse_slack_url("https://example.com/not-a-slack-url")


def test_parse_basic_channel_permalink() -> None:
    url = "https://myteam.slack.com/archives/C1234ABCD/p1734567890123456"
    channel_id, ts, thread_ts = parse_slack_url(url)
    assert channel_id == "C1234ABCD"
    assert ts == "1734567890.123456"
    assert thread_ts is None


def test_parse_thread_permalink() -> None:
    url = "https://team.slack.com/archives/C1234ABCD/p1734567890123456?thread_ts=1734567800.000000&cid=C1234ABCD"
    channel_id, ts, thread_ts = parse_slack_url(url)
    assert channel_id == "C1234ABCD"
    assert ts == "1734567890.123456"
    assert thread_ts == "1734567800.000000"


def test_parse_dm_and_group_permalinks() -> None:
    dm_url = "https://team.slack.com/archives/D0123ABC/p1734567890123456"
    channel_id, ts, _ = parse_slack_url(dm_url)
    assert channel_id == "D0123ABC"
    assert ts == "1734567890.123456"

    group_url = "https://team.slack.com/archives/G9876XYZ/p1734567890123456"
    channel_id, ts, _ = parse_slack_url(group_url)
    assert channel_id == "G9876XYZ"


def test_parse_slack_url_used_in_read_thread_dispatch() -> None:
    """Verify parse_slack_url output is compatible with read_thread args."""
    url = "https://team.slack.com/archives/C1234ABCD/p1734567890123456?thread_ts=1734567800.000000&cid=C1234ABCD"
    channel_id, _ts, thread_ts = parse_slack_url(url)
    assert channel_id == "C1234ABCD"
    assert thread_ts is not None
    # thread_ts is in dot-separated format ready for API use
    assert "." in thread_ts
