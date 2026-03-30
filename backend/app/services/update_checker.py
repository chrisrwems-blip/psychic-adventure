"""Update checker — compares local version against GitHub."""
import json
from pathlib import Path

import requests

REPO = "chrisrwems-blip/psychic-adventure"
VERSION_FILE = Path(__file__).parent.parent.parent / "version.json"


def get_local_version() -> dict:
    """Read local version info."""
    if not VERSION_FILE.exists():
        return {"version": "0.0.0", "commit": "unknown"}
    try:
        return json.loads(VERSION_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {"version": "0.0.0", "commit": "unknown"}


def check_for_update() -> dict:
    """Check GitHub for a newer version."""
    local = get_local_version()

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{REPO}/commits/main",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=5,
        )
        if not resp.ok:
            return {"update_available": False, "current": local, "error": "GitHub API error"}

        remote_commit = resp.json().get("sha", "")[:7]
        remote_message = resp.json().get("commit", {}).get("message", "").split("\n")[0]
        remote_date = resp.json().get("commit", {}).get("committer", {}).get("date", "")

        update_available = remote_commit != local.get("commit", "")[:7]

        return {
            "update_available": update_available,
            "current_version": local.get("version", "0.0.0"),
            "current_commit": local.get("commit", "unknown"),
            "latest_commit": remote_commit,
            "latest_message": remote_message,
            "latest_date": remote_date,
        }
    except requests.RequestException:
        return {"update_available": False, "current": local, "error": "Could not reach GitHub"}
