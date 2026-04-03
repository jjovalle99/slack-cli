import platform
import sys
from pathlib import Path

from slack_cli.auth.cookies import extract_xoxd
from slack_cli.auth.extract import extract_xoxc_tokens
from slack_cli.auth.workspace import select_workspace
from slack_cli.client import SlackClient
from slack_cli.config import save_config
from slack_cli.output import write_success
from slack_cli.validation import validate_tokens

SLACK_LEVELDB_PATHS = {
    "Darwin": Path.home()
    / "Library"
    / "Application Support"
    / "Slack"
    / "Local Storage"
    / "leveldb",
    "Linux": Path.home() / ".config" / "Slack" / "Local Storage" / "leveldb",
}

SLACK_COOKIE_PATHS = {
    "Darwin": Path.home() / "Library" / "Application Support" / "Slack" / "Cookies",
    "Linux": Path.home() / ".config" / "Slack" / "Cookies",
}

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "slack-cli" / "config.json"


async def run_auth(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    is_macos: bool | None = None,
) -> None:
    """Extract tokens from Slack desktop app, validate, and save config."""
    os_name = platform.system()
    if is_macos is None:
        is_macos = os_name == "Darwin"

    leveldb_path = SLACK_LEVELDB_PATHS.get(os_name)
    cookie_path = SLACK_COOKIE_PATHS.get(os_name)

    if not leveldb_path or not cookie_path:
        raise SystemExit(f"Unsupported platform: {os_name}. Only macOS and Linux are supported.")

    if not leveldb_path.exists():
        raise SystemExit(
            f"Slack LevelDB not found at {leveldb_path}. Is the Slack desktop app installed?"
        )

    workspaces = extract_xoxc_tokens(leveldb_path)
    workspace = select_workspace(workspaces)
    xoxc = workspace["token"]

    xoxd = extract_xoxd(cookie_path, is_macos=is_macos)

    async with SlackClient(xoxc=xoxc, xoxd=xoxd) as client:
        auth_info = await validate_tokens(client)

    save_config(config_path, xoxc=xoxc, xoxd=xoxd, workspace_name=workspace["name"])

    print(f"Authenticated as {auth_info.get('user')} in {workspace['name']}", file=sys.stderr)
    write_success({"user": auth_info.get("user"), "team": auth_info.get("team")})
