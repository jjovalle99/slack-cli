import subprocess


def test_cli_help_exits_zero() -> None:
    result = subprocess.run(
        ["uv", "run", "slack-cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "search" in result.stdout
    assert "read" in result.stdout
    assert "auth" in result.stdout


def test_cli_search_messages_help() -> None:
    result = subprocess.run(
        ["uv", "run", "slack-cli", "search", "messages", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "query" in result.stdout.lower() or "QUERY" in result.stdout


def test_cli_no_tokens_exits_nonzero() -> None:
    import os

    env = {**os.environ, "HOME": "/tmp/nonexistent_slack_cli_test"}
    env.pop("SLACK_XOXC_TOKEN", None)
    env.pop("SLACK_XOXD_TOKEN", None)
    result = subprocess.run(
        ["uv", "run", "slack-cli", "search", "messages", "test query"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "token" in result.stderr.lower() or "auth" in result.stderr.lower()
