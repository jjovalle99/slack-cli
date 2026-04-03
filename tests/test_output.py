import json

import pytest

from slack_cli.output import write_error, write_success


def test_write_success_outputs_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    write_success({"messages": [{"text": "hello"}]})
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["messages"][0]["text"] == "hello"


def test_write_error_outputs_json_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    write_error("invalid_auth", "Token is invalid")
    err = capsys.readouterr().err
    parsed = json.loads(err)
    assert parsed["error"] == "invalid_auth"
    assert parsed["message"] == "Token is invalid"
