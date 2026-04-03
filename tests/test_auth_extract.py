import json

import pytest

from slack_cli.auth.extract import parse_local_config


def test_parse_local_config_extracts_workspaces() -> None:
    config = json.dumps(
        {
            "teams": {
                "T0000000001": {
                    "token": "xoxc-workspace1-token",
                    "name": "Acme Corp",
                    "url": "https://acme.slack.com",
                },
                "T12345": {
                    "token": "xoxc-workspace2-token",
                    "name": "Other Org",
                    "url": "https://other.slack.com",
                },
            }
        }
    )

    workspaces = parse_local_config(config)
    assert len(workspaces) == 2
    assert workspaces[0]["token"].startswith("xoxc-") or workspaces[1]["token"].startswith("xoxc-")
    names = {w["name"] for w in workspaces}
    assert "Acme Corp" in names
    assert "Other Org" in names


def test_parse_local_config_empty_teams() -> None:
    config = json.dumps({"teams": {}})
    workspaces = parse_local_config(config)
    assert workspaces == []


def test_parse_local_config_invalid_json() -> None:
    with pytest.raises(ValueError, match="parse"):
        parse_local_config("not json{{{")
