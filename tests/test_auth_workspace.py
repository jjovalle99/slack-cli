import pytest

from slack_cli.auth.workspace import select_workspace


def test_auto_selects_single_workspace() -> None:
    workspaces = [
        {"team_id": "T1", "token": "xoxc-1", "name": "Only Org", "url": "https://only.slack.com"}
    ]
    result = select_workspace(workspaces)
    assert result["name"] == "Only Org"


def test_prompts_for_multiple_workspaces(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspaces = [
        {"team_id": "T1", "token": "xoxc-1", "name": "Org A", "url": "https://a.slack.com"},
        {"team_id": "T2", "token": "xoxc-2", "name": "Org B", "url": "https://b.slack.com"},
    ]
    monkeypatch.setattr("builtins.input", lambda _: "2")
    result = select_workspace(workspaces)
    assert result["name"] == "Org B"
    stderr = capsys.readouterr().err
    assert "Org A" in stderr
    assert "Org B" in stderr


def test_raises_on_empty_workspaces() -> None:
    with pytest.raises(SystemExit):
        select_workspace([])
