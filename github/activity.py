"""Read recent GitHub activity through the authenticated user's Events API."""

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from github import Github

Activity = dict[str, list[dict[str, Any]]]


def empty_activity() -> Activity:
    return {"commits": [], "prs_opened": [], "prs_merged": [], "reviews": []}


def get_recent_activity(
    gh: Github,
    username: str,
    hours: int = 24,
    repositories: Iterable[str] | None = None,
) -> Activity:
    """Return a user's recent commits, PRs, merged PRs, and reviews.

    GitHub returns Events API entries newest first. Filtering against a tracked
    repository list happens locally, so one user can be used across servers
    without expanding the GitHub API request count.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    tracked_repositories = {repo.strip().lower() for repo in repositories or [] if repo.strip()}
    activity = empty_activity()

    for event in gh.get_user(username).get_events():
        created_at = event.created_at.replace(tzinfo=timezone.utc)
        if created_at < since:
            break

        repo_name = event.repo.name
        if tracked_repositories and repo_name.lower() not in tracked_repositories:
            continue

        payload = event.payload
        if event.type == "PushEvent":
            for commit in payload.get("commits", []):
                activity["commits"].append(
                    {
                        "repo": repo_name,
                        "message": commit.get("message", "No commit message").split("\n", 1)[0],
                        "sha": commit.get("sha", "")[:7],
                    }
                )
        elif event.type == "PullRequestEvent":
            pull_request = payload.get("pull_request", {})
            entry = {
                "repo": repo_name,
                "title": pull_request.get("title", "Untitled pull request"),
                "number": pull_request.get("number", "?"),
                "url": pull_request.get("html_url", ""),
            }
            if payload.get("action") == "opened":
                activity["prs_opened"].append(entry)
            elif payload.get("action") == "closed" and pull_request.get("merged"):
                activity["prs_merged"].append(entry)
        elif event.type == "PullRequestReviewEvent":
            pull_request = payload.get("pull_request", {})
            activity["reviews"].append(
                {
                    "repo": repo_name,
                    "title": pull_request.get("title", "Untitled pull request"),
                    "number": pull_request.get("number", "?"),
                    "url": pull_request.get("html_url", ""),
                }
            )

    return activity
