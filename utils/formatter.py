"""
utils/formatter.py
Turns raw GitHub activity dicts into readable standup text.
"""

from datetime import datetime


def format_standup(activity: dict, username: str, streak: int = None) -> str:
    """Turn raw activity dict into readable standup text (Discord-friendly)."""
    lines = [f" **Standup for {username}** — {datetime.now().strftime('%Y-%m-%d')}\n"]

    if streak is not None and streak > 1:
        lines.append(f"🔥 {streak}-day commit streak!\n")

    if not any(activity.values()):
        lines.append("No GitHub activity in the last 24h. Quiet day 🌙")
        return "\n".join(lines)


    if activity["commits"]:
        lines.append(f"🔨 **Commits** ({len(activity['commits'])}):")
        for c in activity["commits"]:
            lines.append(f"  • [{c['repo']}] {c['message']} (`{c['sha']}`)")
        lines.append("")

    if activity["prs_opened"]:
        lines.append(f" **PRs opened** ({len(activity['prs_opened'])}):")
        for pr in activity["prs_opened"]:
            lines.append(f"  • [{pr['repo']}] #{pr['number']}: {pr['title']}")
        lines.append("")

    if activity["prs_merged"]:
        lines.append(f" **PRs merged** ({len(activity['prs_merged'])}):")
        for pr in activity["prs_merged"]:
            lines.append(f"  • [{pr['repo']}] #{pr['number']}: {pr['title']}")
        lines.append("")

    if activity["reviews"]:
        lines.append(f" **Reviews given** ({len(activity['reviews'])}):")
        for r in activity["reviews"]:
            lines.append(f"  • [{r['repo']}] #{r['number']}: {r['title']}")
        lines.append("")

    return "\n".join(lines)


def format_weekly_digest(activity: dict, username: str) -> str:
    """Turn a week's worth of raw activity into a digest summary."""
    lines = [f" **Weekly digest for {username}**\n"]

    if not any(activity.values()):
        lines.append("No GitHub activity in the last 7 days. 🌙")
        return "\n".join(lines)

    lines.append(f"🔨 {len(activity['commits'])} commits")
    lines.append(f"{len(activity['prs_opened'])} PRs opened")
    lines.append(f" {len(activity['prs_merged'])} PRs merged")
    lines.append(f" {len(activity['reviews'])} reviews given\n")

    repos_touched = set()
    for c in activity["commits"]:
        repos_touched.add(c["repo"])
    for pr in activity["prs_opened"] + activity["prs_merged"]:
        repos_touched.add(pr["repo"])

    if repos_touched:
        lines.append(f"📂 Repos touched: {', '.join(sorted(repos_touched))}")

    return "\n".join(lines)