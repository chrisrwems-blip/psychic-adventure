"""Load profile settings for use across services."""
import json
from pathlib import Path

PROFILE_FILE = Path(__file__).parent.parent.parent / "profile_settings.json"

_DEFAULTS = {
    "reviewer_name": "",
    "reviewer_title": "",
    "company_name": "",
    "company_address": "",
    "company_phone": "",
    "default_jurisdiction": "auto",
    "review_sla_days": 5,
    "report_min_severity": "minor",
    "vision_backend": "auto",
}


def get_profile() -> dict:
    """Load profile settings, returning defaults for missing fields."""
    if not PROFILE_FILE.exists():
        return dict(_DEFAULTS)
    try:
        saved = json.loads(PROFILE_FILE.read_text())
        return {**_DEFAULTS, **saved}
    except (json.JSONDecodeError, IOError):
        return dict(_DEFAULTS)
