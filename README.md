# Silent Standup

A Discord bot that turns recent GitHub activity into a team standup. It can post
on demand with `!standup` or `/standup`, and automatically at each server's
configured local time.

## Setup

1. Create a Discord application and bot, then enable **Message Content Intent**
   in the Discord Developer Portal if you want the `!standup` command. Invite it
   with the `bot` and `applications.commands` scopes.
2. Create a GitHub token that can read the activity and private repositories you
   intend to track. Copy `.env.example` to `.env` and enter `DISCORD_TOKEN` and
   `GITHUB_TOKEN`. `GROQ_API_KEY` is optional.
3. Install and run:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python bot.py
   ```

4. In each Discord server, use `/standup-config` as a server manager. For
   example, select a channel, set `github_users` to `octocat,hubot`, set
   `repositories` to `owner/api,owner/web`, `post_time` to `09:30`, and
   `timezone` to `Asia/Kolkata`.

Leave `repositories` empty to include all repositories visible to the GitHub
token. Use `/standup-config` with no options to view the saved settings.

## Commands

- `/standup [github_username] [rewrite]` — generate a report now.
- `!standup [github_username]` — prefix-command equivalent.
- `/standup-config` — view or update this server's delivery channel, users,
  repositories, schedule, timezone, lookback period, and Groq rewrite setting.

Slash commands normally appear shortly after startup; for immediate testing,
invite the bot into a test guild and allow Discord a moment to synchronize.

## Deployment

Set the same environment variables on Railway or Render and use this start
command:

```bash
python bot.py
```

The service must run continuously for APScheduler to make the daily posts.
`config.json` is local disk storage; on platforms with ephemeral disks, attach a
persistent volume or move the configuration to a database before relying on
changes across redeploys.
