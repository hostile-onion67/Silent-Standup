"""Prefix and slash command handlers."""

import asyncio
import os
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from github import Github

from github.activity import get_recent_activity
from utils.config import ConfigStore
from utils.formatter import format_standup, rewrite_standup

if TYPE_CHECKING:
    from discord_bot.scheduler import DailyStandupScheduler


class StandupConfigurationError(ValueError):
    """Raised when a guild has not supplied enough settings to make a report."""


class StandupService:
    def __init__(self, config_store: ConfigStore, github_token: str) -> None:
        self.config_store = config_store
        self.github_token = github_token

    async def generate(
        self,
        guild_id: int,
        github_username: str | None = None,
        use_llm: bool | None = None,
    ) -> str:
        settings = self.config_store.get_guild(guild_id)
        users = [github_username] if github_username else settings.get("github_users", [])
        if not users:
            raise StandupConfigurationError(
                "No GitHub users configured. Use /standup-config with github_users first."
            )

        reports = await asyncio.gather(
            *[
                asyncio.to_thread(
                    self._get_user_report,
                    username,
                    settings.get("lookback_hours", 24),
                    settings.get("repositories", []),
                    settings.get("timezone", "UTC"),
                )
                for username in users
            ]
        )
        report = "\n\n".join(reports)
        should_rewrite = settings.get("llm_rewrite", False) if use_llm is None else use_llm
        if should_rewrite:
            return await rewrite_standup(report, os.getenv("GROQ_API_KEY"))
        return report

    def _get_user_report(
        self,
        username: str,
        lookback_hours: int,
        repositories: list[str],
        timezone_name: str,
    ) -> str:
        github = Github(self.github_token, per_page=100)
        activity = get_recent_activity(github, username, lookback_hours, repositories)
        return format_standup(activity, username, timezone_name, lookback_hours)


def register_commands(
    bot: commands.Bot,
    service: StandupService,
    config_store: ConfigStore,
    scheduler: "DailyStandupScheduler",
) -> None:
    """Register the command set once during the bot's setup hook."""

    @bot.command(name="standup")
    @commands.guild_only()
    async def prefix_standup(ctx: commands.Context, github_username: str | None = None) -> None:
        """Post a report, optionally for one GitHub username."""
        try:
            report = await service.generate(ctx.guild.id, github_username)
            for message in split_discord_messages(report):
                await ctx.send(message)
        except StandupConfigurationError as exc:
            await ctx.send(f"⚙️ {exc}")
        except Exception:
            await ctx.send("I couldn't fetch the GitHub activity. Check the token and configured users.")
            raise

    @bot.tree.command(name="standup", description="Generate a GitHub standup report now.")
    @app_commands.guild_only()
    @app_commands.describe(github_username="Optional GitHub user to report on", rewrite="Rewrite with Groq")
    async def slash_standup(
        interaction: discord.Interaction,
        github_username: str | None = None,
        rewrite: bool | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            report = await service.generate(interaction.guild_id, github_username, rewrite)
            messages = split_discord_messages(report)
            await interaction.followup.send(messages[0])
            for message in messages[1:]:
                await interaction.channel.send(message)
        except StandupConfigurationError as exc:
            await interaction.followup.send(f"⚙️ {exc}", ephemeral=True)
        except Exception:
            await interaction.followup.send(
                "I couldn't fetch the GitHub activity. Check the token and configured users.",
                ephemeral=True,
            )
            raise

    @bot.tree.command(name="standup-config", description="Configure daily standups for this server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        channel="Channel for the daily standup",
        github_users="Comma-separated GitHub usernames",
        repositories="Comma-separated owner/repository names; leave blank to track all",
        post_time="Daily post time in 24-hour HH:MM format",
        timezone="IANA timezone, for example Asia/Kolkata",
        lookback_hours="Hours of GitHub activity to include",
        enable_llm="Use Groq to rewrite reports",
    )
    async def standup_config(
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        github_users: str | None = None,
        repositories: str | None = None,
        post_time: str | None = None,
        timezone: str | None = None,
        lookback_hours: app_commands.Range[int, 1, 168] | None = None,
        enable_llm: bool | None = None,
    ) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permission to configure standups.", ephemeral=True)
            return

        updates: dict[str, object] = {}
        if channel is not None:
            updates["channel_id"] = channel.id
        if github_users is not None:
            updates["github_users"] = csv_values(github_users)
        if repositories is not None:
            updates["repositories"] = csv_values(repositories)
        if post_time is not None:
            updates["post_time"] = post_time
        if timezone is not None:
            updates["timezone"] = timezone
        if lookback_hours is not None:
            updates["lookback_hours"] = lookback_hours
        if enable_llm is not None:
            updates["llm_rewrite"] = enable_llm

        if not updates:
            settings = config_store.get_guild(interaction.guild_id)
            await interaction.response.send_message(settings_summary(settings), ephemeral=True)
            return

        try:
            settings = config_store.update_guild(interaction.guild_id, updates)
            await scheduler.sync_jobs()
        except ValueError as exc:
            await interaction.response.send_message(f"⚙️ {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"Saved.\n{settings_summary(settings)}", ephemeral=True)


def csv_values(value: str) -> list[str]:
    return [entry.strip() for entry in value.split(",") if entry.strip()]


def settings_summary(settings: dict) -> str:
    channel = f"<#{settings['channel_id']}>" if settings.get("channel_id") else "not set"
    users = ", ".join(settings.get("github_users", [])) or "not set"
    repositories = ", ".join(settings.get("repositories", [])) or "all accessible repositories"
    return (
        f"**Standup settings**\n"
        f"Channel: {channel}\nUsers: {users}\nRepositories: {repositories}\n"
        f"Schedule: {settings['post_time']} ({settings['timezone']})\n"
        f"Lookback: {settings['lookback_hours']} hours\nGroq rewrite: {settings['llm_rewrite']}"
    )


def split_discord_messages(text: str, limit: int = 2_000) -> list[str]:
    """Local copy to avoid a circular import with the bot entry point."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current.rstrip())
            current = ""
        current += line
    if current:
        chunks.append(current.rstrip())
    return chunks
