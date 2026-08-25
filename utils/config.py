"""Small JSON-backed configuration store, one record per Discord guild."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytz

DEFAULT_GUILD_SETTINGS = {
    "channel_id": None,
    "repositories": [],
    "github_users": [],
    "post_time": "09:00",
    "timezone": "UTC",
    "lookback_hours": 24,
    "llm_rewrite": False,
}


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        if not self.path.exists():
            self._write({"servers": {}})

    def get_guild(self, guild_id: int) -> dict[str, Any]:
        data = self._read()
        saved = data.get("servers", {}).get(str(guild_id), {})
        return {**deepcopy(DEFAULT_GUILD_SETTINGS), **saved}

    def guild_ids(self) -> list[int]:
        return [int(guild_id) for guild_id in self._read().get("servers", {})]

    def update_guild(self, guild_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        candidate = {**self.get_guild(guild_id), **updates}
        self._validate(candidate)
        data = self._read()
        data.setdefault("servers", {})[str(guild_id)] = candidate
        self._write(data)
        return candidate

    def _read(self) -> dict[str, Any]:
        try:
            with self.path.open(encoding="utf-8") as config_file:
                data = json.load(config_file)
        except json.JSONDecodeError as exc:
            raise ValueError("config.json is not valid JSON. Fix it before starting the bot.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("servers", {}), dict):
            raise ValueError('config.json must contain an object with a "servers" object.')
        return data

    def _write(self, data: dict[str, Any]) -> None:
        temporary_path = self.path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as config_file:
            json.dump(data, config_file, indent=2)
            config_file.write("\n")
        temporary_path.replace(self.path)

    @staticmethod
    def _validate(settings: dict[str, Any]) -> None:
        if not isinstance(settings["repositories"], list) or not all("/" in repo for repo in settings["repositories"]):
            raise ValueError("repositories must be comma-separated owner/repository names.")
        if not isinstance(settings["github_users"], list):
            raise ValueError("github_users must be a comma-separated list.")
        if settings["timezone"] not in pytz.all_timezones:
            raise ValueError("timezone must be a valid IANA timezone, for example Asia/Kolkata.")
        if not isinstance(settings["lookback_hours"], int) or not 1 <= settings["lookback_hours"] <= 168:
            raise ValueError("lookback_hours must be between 1 and 168.")
        from discord_bot.scheduler import parse_post_time

        parse_post_time(settings["post_time"])
