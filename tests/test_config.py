import stat
from pathlib import Path

from slack_cli.config import load_config, save_config


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    save_config(config_path, xoxc="xoxc-test", xoxd="xoxd-test", workspace_name="TestOrg")
    result = load_config(config_path)
    assert result is not None
    assert result["xoxc"] == "xoxc-test"
    assert result["xoxd"] == "xoxd-test"
    assert result["workspace_name"] == "TestOrg"


def test_save_sets_permissions_0600(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    save_config(config_path, xoxc="xoxc-test", xoxd="xoxd-test", workspace_name="TestOrg")
    mode = config_path.stat().st_mode & 0o777
    assert mode == stat.S_IRUSR | stat.S_IWUSR


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    config_path = tmp_path / "nonexistent.json"
    assert load_config(config_path) is None


def test_load_corrupt_file_returns_none(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("not json{{{")
    assert load_config(config_path) is None
