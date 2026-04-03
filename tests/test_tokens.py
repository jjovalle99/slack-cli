from pathlib import Path

import pytest

from slack_cli.config import save_config
from slack_cli.tokens import resolve_tokens


def test_resolve_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    save_config(config_path, xoxc="xoxc-from-config", xoxd="xoxd-from-config", workspace_name="W")
    xoxc, xoxd = resolve_tokens(config_path=config_path)
    assert xoxc == "xoxc-from-config"
    assert xoxd == "xoxd-from-config"


def test_flags_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_XOXC_TOKEN", "xoxc-env")
    monkeypatch.setenv("SLACK_XOXD_TOKEN", "xoxd-env")
    xoxc, xoxd = resolve_tokens(flag_token="xoxc-flag", flag_cookie="xoxd-flag")
    assert xoxc == "xoxc-flag"
    assert xoxd == "xoxd-flag"


def test_env_overrides_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    save_config(config_path, xoxc="xoxc-config", xoxd="xoxd-config", workspace_name="W")
    monkeypatch.setenv("SLACK_XOXC_TOKEN", "xoxc-env")
    monkeypatch.setenv("SLACK_XOXD_TOKEN", "xoxd-env")
    xoxc, xoxd = resolve_tokens(config_path=config_path)
    assert xoxc == "xoxc-env"
    assert xoxd == "xoxd-env"


def test_no_tokens_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SLACK_XOXC_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_XOXD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        resolve_tokens(config_path=tmp_path / "nonexistent.json")


def test_url_encoded_xoxd_is_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_XOXC_TOKEN", "xoxc-test")
    monkeypatch.setenv("SLACK_XOXD_TOKEN", "xoxd-fake%2Btoken%2Bvalue%3D%3D")
    _, xoxd = resolve_tokens()
    assert "%2B" not in xoxd
    assert "+B" in xoxd or xoxd.endswith("==")
