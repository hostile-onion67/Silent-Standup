"""
utils/streaks.py
Tracks daily commit streaks per GitHub username using a local JSON file.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STREAK_FILE = Path(__file__).resolve().parent.parent / "streaks.json"


def _load() -> dict:
    if not STREAK_FILE.exists():
        return {}
    with open(STREAK_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(STREAK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def update_streak(username: str, had_activity: bool) -> int:
    """
    Call once per day after checking activity.
    Returns the current streak count after updating.
    """
    data = _load()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_data = data.get(username, {"last_date": None, "streak": 0})

    if had_activity:
        last_date = user_data["last_date"]
        if last_date:
            last = datetime.strptime(last_date, "%Y-%m-%d")
            gap = (datetime.strptime(today, "%Y-%m-%d") - last).days
            if gap == 1:
                user_data["streak"] += 1  # consecutive day
            elif gap > 1:
                user_data["streak"] = 1  # streak broken, restart
            # gap == 0 means already counted today, do nothing
        else:
            user_data["streak"] = 1  # first ever activity

        user_data["last_date"] = today
    else:
        # No activity today — only reset if it's a new day past the last one
        last_date = user_data["last_date"]
        if last_date and last_date != today:
            gap = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(last_date, "%Y-%m-%d")).days
            if gap > 1:
                user_data["streak"] = 0

    data[username] = user_data
    _save(data)
    return user_data["streak"]


def get_streak(username: str) -> int:
    data = _load()
    return data.get(username, {}).get("streak", 0)