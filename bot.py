"""
bot.py
Entry point for the Silent Standup Discord bot.

Commands:
  !standup            -> posts your GitHub standup for the last 24h, with streak count
  !weeksummary        -> posts a digest of the last 7 days of GitHub activity
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from github import Github

from gh_activity.activity import get_recent_activity
from utils.formatter import format_standup, format_weekly_digest
from utils.streaks import update_streak

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

if not DISCORD_TOKEN or not GITHUB_TOKEN or not GITHUB_USERNAME:
    raise SystemExit(
        "Missing DISCORD_TOKEN, GITHUB_TOKEN, or GITHUB_USERNAME in .env"
    )

# Discord requires explicit intents for reading message content (for prefix commands)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

gh_client = Github(GITHUB_TOKEN)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")


@bot.command(name="standup")
async def standup(ctx: commands.Context):
    """Fetch and post the last 24h of GitHub activity."""
    await ctx.send("Pulling your GitHub activity... 🔍")

    try:
        activity = get_recent_activity(gh_client, GITHUB_USERNAME, hours=24)
        had_activity = any(activity.values())
        streak = update_streak(GITHUB_USERNAME, had_activity)
        standup_text = format_standup(activity, GITHUB_USERNAME, streak=streak)
    except Exception as e:
        await ctx.send(f"⚠️ Couldn't fetch activity: {e}")
        return

    # Discord messages cap at 2000 chars — split if needed
    if len(standup_text) <= 2000:
        await ctx.send(standup_text)
    else:
        for i in range(0, len(standup_text), 2000):
            await ctx.send(standup_text[i:i + 2000])


@bot.command(name="weeksummary")
async def weeksummary(ctx: commands.Context):
    """Fetch and post the last 7 days of GitHub activity as a digest."""
    await ctx.send("Pulling your week's GitHub activity... 🔍")

    try:
        activity = get_recent_activity(gh_client, GITHUB_USERNAME, hours=24 * 7)
        digest_text = format_weekly_digest(activity, GITHUB_USERNAME)
    except Exception as e:
        await ctx.send(f"⚠️ Couldn't fetch activity: {e}")
        return

    if len(digest_text) <= 2000:
        await ctx.send(digest_text)
    else:
        for i in range(0, len(digest_text), 2000):
            await ctx.send(digest_text[i:i + 2000])


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)