import os
from datetime import datetime, timedelta, timezone
from github import Github
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

# How far back to look for activity
LOOKBACK_HOURS = 24


def get_recent_activity(gh: Github, username: str, hours: int):
    """
    Pull commits, opened PRs, merged PRs, and reviews from the last N hours
    across all repos the user has access to.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    user = gh.get_user(username)

    activity = {
        "commits": [],
        "prs_opened": [],
        "prs_merged": [],
        "reviews": [],
    }

    # Use the Events API — single call, covers commits/PRs/reviews across all repos
    events = user.get_events()

    for event in events:
        if event.created_at.replace(tzinfo=timezone.utc) < since:
            break  # events are in reverse chronological order, so we can stop early

        repo_name = event.repo.name

        if event.type == "PushEvent":
            commits = event.payload.get("commits", [])
            for c in commits:
                activity["commits"].append({
                    "repo": repo_name,
                    "message": c["message"].split("\n")[0],  # first line only
                    "sha": c["sha"][:7],
                })

        elif event.type == "PullRequestEvent":
            action = event.payload.get("action")
            pr = event.payload.get("pull_request", {})
            entry = {
                "repo": repo_name,
                "title": pr.get("title", ""),
                "number": pr.get("number"),
                "url": pr.get("html_url", ""),
            }
            if action == "opened":
                activity["prs_opened"].append(entry)
            elif action == "closed" and pr.get("merged"):
                activity["prs_merged"].append(entry)

        elif event.type == "PullRequestReviewEvent":
            pr = event.payload.get("pull_request", {})
            activity["reviews"].append({
                "repo": repo_name,
                "title": pr.get("title", ""),
                "number": pr.get("number"),
            })

    return activity


def format_standup(activity: dict, username: str) -> str:
    """Turn raw activity dict into readable standup text."""
    lines = [f"📋 Standup for {username} — {datetime.now().strftime('%Y-%m-%d')}\n"]

    if not any(activity.values()):
        lines.append("No GitHub activity in the last 24h. Quiet day 🌙")
        return "\n".join(lines)

    if activity["commits"]:
        lines.append(f"🔨 Commits ({len(activity['commits'])}):")
        for c in activity["commits"]:
            lines.append(f"  • [{c['repo']}] {c['message']} ({c['sha']})")
        lines.append("")

    if activity["prs_opened"]:
        lines.append(f"📬 PRs opened ({len(activity['prs_opened'])}):")
        for pr in activity["prs_opened"]:
            lines.append(f"  • [{pr['repo']}] #{pr['number']}: {pr['title']}")
        lines.append("")

    if activity["prs_merged"]:
        lines.append(f"✅ PRs merged ({len(activity['prs_merged'])}):")
        for pr in activity["prs_merged"]:
            lines.append(f"  • [{pr['repo']}] #{pr['number']}: {pr['title']}")
        lines.append("")

    if activity["reviews"]:
        lines.append(f"👀 Reviews given ({len(activity['reviews'])}):")
        for r in activity["reviews"]:
            lines.append(f"  • [{r['repo']}] #{r['number']}: {r['title']}")
        lines.append("")

    return "\n".join(lines)


def main():
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        raise SystemExit(
            "Missing GITHUB_TOKEN or GITHUB_USERNAME in .env — see setup instructions."
        )

    gh = Github(GITHUB_TOKEN)
    activity = get_recent_activity(gh, GITHUB_USERNAME, LOOKBACK_HOURS)
    standup_text = format_standup(activity, GITHUB_USERNAME)
    print(standup_text)


if __name__ == "__main__":
    main()