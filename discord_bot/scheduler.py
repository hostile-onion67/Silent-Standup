"""APScheduler integration for per-guild daily posts."""

from collections.abc import Awaitable, Callable
from datetime import datetime
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.config import ConfigStore


class DailyStandupScheduler:
    def __init__(self, config_store: ConfigStore, post_callback: Callable[[int], Awaitable[None]]) -> None:
        self.config_store = config_store
        self.post_callback = post_callback
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def sync_jobs(self) -> None:
        """Make APScheduler jobs exactly match saved, complete guild settings."""
        configured_ids = set(self.config_store.guild_ids())
        for job in self.scheduler.get_jobs():
            if job.id.removeprefix("daily-standup-") not in {str(guild_id) for guild_id in configured_ids}:
                self.scheduler.remove_job(job.id)

        for guild_id in configured_ids:
            settings = self.config_store.get_guild(guild_id)
            job_id = f"daily-standup-{guild_id}"
            if not settings.get("channel_id") or not settings.get("github_users"):
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                continue

            hour, minute = parse_post_time(settings["post_time"])
            timezone = pytz.timezone(settings["timezone"])
            self.scheduler.add_job(
                self.post_callback,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
                args=[guild_id],
                id=job_id,
                replace_existing=True,
                coalesce=True,
                misfire_grace_time=3_600,
            )
            logging.info("Scheduled guild %s for %s %s", guild_id, settings["post_time"], settings["timezone"])


def parse_post_time(value: str) -> tuple[int, int]:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError("post_time must use 24-hour HH:MM format, for example 09:30.") from exc
    return parsed.hour, parsed.minute
