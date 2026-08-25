import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from discord_bot.commands import StandupService, register_commands
from discord_bot.scheduler import DailyStandupScheduler
from utils.config import ConfigStore

BASE_DIR = Path(__file__).resolve().parent


class SilentStandupBot(commands.Bot):
    def __init__(self, config_store: ConfigStore, github_token: str) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # Required only for the !standup command.
        super().__init__(command_prefix="!", intents=intents)

        self.config_store = config_store
        self.standup_service = StandupService(config_store, github_token)
        self.scheduler = DailyStandupScheduler(config_store, self.post_scheduled_standup)

    async def setup_hook(self) -> None:
        register_commands(self, self.standup_service, self.config_store, self.scheduler)
        self.scheduler.start()
        await self.scheduler.sync_jobs()
        await self.tree.sync()
        logging.info("Slash commands synced and daily standup scheduler started.")

    async def post_scheduled_standup(self, guild_id: int) -> None:
        """Generate and post a configured guild's standup from the scheduler."""
        settings = self.config_store.get_guild(guild_id)
        channel_id = settings.get("channel_id")
        if not channel_id:
            logging.warning("Guild %s has no standup channel configured.", guild_id)
            return

        channel = self.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(channel_id)
            except discord.DiscordException:
                logging.exception("Could not find configured channel %s.", channel_id)
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logging.warning("Configured channel %s is not a text channel.", channel_id)
            return

        try:
            standup = await self.standup_service.generate(guild_id)
            for message in split_discord_messages(standup):
                await channel.send(message)
        except Exception:
            logging.exception("Scheduled standup failed for guild %s.", guild_id)


def split_discord_messages(text: str, limit: int = 2_000) -> list[str]:
    """Split long reports at line boundaries so they fit Discord's message limit."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current.rstrip())
            current = ""
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current += line
    if current:
        chunks.append(current.rstrip())
    return chunks


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    discord_token = os.getenv("DISCORD_TOKEN")
    github_token = os.getenv("GITHUB_TOKEN")
    if not discord_token or not github_token:
        raise SystemExit("Missing DISCORD_TOKEN or GITHUB_TOKEN. Add them to .env first.")

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = SilentStandupBot(ConfigStore(BASE_DIR / "config.json"), github_token)
    bot.run(discord_token, log_handler=None)


if __name__ == "__main__":
    main()
