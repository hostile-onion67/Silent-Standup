"""Format GitHub activity for Discord, with an optional Groq rewrite."""

import asyncio
from datetime import datetime
from typing import Any

import pytz


def format_standup(
    activity: dict[str, list[dict[str, Any]]],
    username: str,
    timezone_name: str = "UTC",
    lookback_hours: int = 24,
) -> str:
    """Turn raw GitHub event data into a concise Discord standup."""
    date = datetime.now(pytz.timezone(timezone_name)).strftime("%Y-%m-%d")
    lines = [f"📋 **Standup for {username} — {date}**\n"]
    if not any(activity.values()):
        lines.append(f"No GitHub activity in the last {lookback_hours}h. Quiet day 🌙")
        return "\n".join(lines)

    sections = (
        ("commits", "🔨 Commits", lambda item: f"• **{item['repo']}** — {item['message']} (`{item['sha']}`)"),
        ("prs_opened", "📬 PRs opened", lambda item: pull_request_line(item)),
        ("prs_merged", "✅ PRs merged", lambda item: pull_request_line(item)),
        ("reviews", "👀 Reviews given", lambda item: pull_request_line(item)),
    )
    for key, label, render in sections:
        items = activity[key]
        if items:
            lines.append(f"{label} ({len(items)}):")
            lines.extend(render(item) for item in items)
            lines.append("")
    return "\n".join(lines).rstrip()


def pull_request_line(item: dict[str, Any]) -> str:
    title = f"[#{item['number']}: {item['title']}]({item['url']})" if item.get("url") else f"#{item['number']}: {item['title']}"
    return f"• **{item['repo']}** — {title}"


async def rewrite_standup(report: str, api_key: str | None) -> str:
    """Optionally make a report more natural; fall back safely to raw output."""
    if not api_key:
        return report
    return await asyncio.to_thread(_rewrite_standup_sync, report, api_key)


def _rewrite_standup_sync(report: str, api_key: str) -> str:
    try:
        from groq import Groq

        completion = Groq(api_key=api_key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_completion_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": "Rewrite GitHub standup reports into concise, professional Discord Markdown. Do not invent, omit, or alter facts, repositories, PR numbers, links, or commit SHAs. Keep headings and bullet points.",
                },
                {"role": "user", "content": report},
            ],
        )
        return completion.choices[0].message.content or report
    except Exception:
        return report
