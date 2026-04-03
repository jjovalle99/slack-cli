import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ccl_chromium_reader.ccl_chromium_localstorage import LocalStoreDb


def parse_local_config(raw: str) -> list[dict[str, Any]]:
    """Parse localConfig_v2 JSON and return list of workspace dicts with token, name, url."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse localConfig_v2: {exc}") from exc

    teams: dict[str, Any] = data.get("teams", {})
    return [
        {"team_id": tid, "token": info["token"], "name": info["name"], "url": info["url"]}
        for tid, info in teams.items()
        if "token" in info
    ]


def extract_xoxc_tokens(leveldb_dir: Path) -> list[dict[str, Any]]:
    """Read localConfig_v2 from Slack's LevelDB and extract workspace tokens.

    Copies the LevelDB dir to temp first to avoid lock conflicts with
    a running Slack app.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "leveldb"
        shutil.copytree(leveldb_dir, tmp_db)

        db = LocalStoreDb(tmp_db)
        try:
            for record in db.iter_all_records():
                if record.script_key == "localConfig_v2" and record.is_live:
                    return parse_local_config(record.value)
        finally:
            db.close()

    return []
