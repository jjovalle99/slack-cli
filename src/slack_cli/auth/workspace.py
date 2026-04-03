import sys
from typing import Any


def select_workspace(workspaces: list[dict[str, Any]]) -> dict[str, Any]:
    """Select a workspace from a list. Prompts if multiple, auto-selects if one."""
    if not workspaces:
        raise SystemExit("No workspaces found in Slack app. Is Slack installed and logged in?")

    if len(workspaces) == 1:
        return workspaces[0]

    print("Multiple workspaces found:", file=sys.stderr)
    for i, ws in enumerate(workspaces, 1):
        print(f"  {i}. {ws['name']} ({ws['url']})", file=sys.stderr)

    choice = input("Select workspace [1]: ").strip()
    idx = int(choice) - 1 if choice else 0

    if not 0 <= idx < len(workspaces):
        raise SystemExit(f"Invalid choice: {choice}")

    return workspaces[idx]
