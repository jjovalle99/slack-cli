import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from slack_cli.auth.command import run_auth


async def test_run_auth_writes_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "config.json"
    workspaces = [
        {
            "team_id": "T1",
            "token": "xoxc-extracted",
            "name": "TestOrg",
            "url": "https://test.slack.com",
        }
    ]

    with (
        patch("slack_cli.auth.command.extract_xoxc_tokens", return_value=workspaces),
        patch("slack_cli.auth.command.extract_xoxd", return_value="xoxd-extracted"),
        patch(
            "slack_cli.auth.command.validate_tokens",
            new_callable=AsyncMock,
            return_value={"ok": True, "user": "testuser", "team": "TestOrg"},
        ),
    ):
        await run_auth(config_path=config_path, is_macos=True)

    config = json.loads(config_path.read_text())
    assert config["xoxc"] == "xoxc-extracted"
    assert config["xoxd"] == "xoxd-extracted"
    assert config["workspace_name"] == "TestOrg"

    out = json.loads(capsys.readouterr().out)
    assert out["user"] == "testuser"
