import json
import os
from pathlib import Path
from typing import Any


def save_config(path: Path, *, xoxc: str, xoxd: str, workspace_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps({"xoxc": xoxc, "xoxd": xoxd, "workspace_name": workspace_name}, indent=2)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data.encode())
    finally:
        os.close(fd)


def load_config(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
