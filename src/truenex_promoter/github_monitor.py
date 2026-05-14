"""Monitor GitHub repo for changes."""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RepoEvent:
    """An event detected on the repo."""

    event_type: str
    title: str
    url: str
    description: str = ""
    data: dict = field(default_factory=dict)


class GitHubMonitor:
    """Monitor a GitHub repo for stars, issues, releases."""

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str = "",
        state_dir: Path | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token
        self.state_dir = state_dir or Path.home() / ".truenex-promoter"
        self.state_file = self.state_dir / "github_state.json"
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"

    def _request(self, endpoint: str) -> dict[str, Any]:
        """Make a GitHub API request."""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "truenex-promoter/0.1.0")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _load_state(self) -> dict[str, Any]:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def check(self) -> list[RepoEvent]:
        """Check repo for changes and return events."""
        events: list[RepoEvent] = []
        prev = self._load_state()

        repo_info = self._request("")
        current_stars = repo_info.get("stargazers_count", 0)
        current_forks = repo_info.get("forks_count", 0)
        current_open_issues = repo_info.get("open_issues_count", 0)

        # Star milestone detection
        prev_stars = prev.get("stars", 0)
        if current_stars > prev_stars:
            milestones = (10, 25, 50, 100, 250, 500, 1000)
            for milestone in milestones:
                if prev_stars < milestone <= current_stars:
                    events.append(
                        RepoEvent(
                            event_type="star_milestone",
                            title=f"{current_stars} stars reached!",
                            url=f"https://github.com/{self.owner}/{self.repo}",
                            description=f"Milestone {milestone} stars crossed (was {prev_stars}).",
                            data={
                                "stars": current_stars,
                                "previous": prev_stars,
                                "milestone": milestone,
                            },
                        )
                    )
                    break

        # New issues detection
        try:
            issues = self._request(
                "issues?state=open&sort=created&direction=desc&per_page=10"
            )
            prev_issue_ids = set(prev.get("issue_ids", []))
            current_issue_ids: list[int] = []
            for issue in issues:
                issue_id = issue.get("id")
                if issue_id is not None:
                    current_issue_ids.append(issue_id)
                if issue_id not in prev_issue_ids:
                    if "pull_request" in issue:
                        continue
                    events.append(
                        RepoEvent(
                            event_type="new_issue",
                            title=f"New issue: {issue.get('title', 'Unknown')}",
                            url=issue.get("html_url", ""),
                            description=(issue.get("body", "") or "")[:500],
                            data={
                                "issue_number": issue.get("number"),
                                "author": issue.get("user", {}).get("login", ""),
                            },
                        )
                    )
        except urllib.error.HTTPError:
            pass

        # New release detection
        prev_release = prev.get("latest_release", "")
        try:
            release = self._request("releases/latest")
            current_release = release.get("tag_name", "")
            if current_release and current_release != prev_release:
                events.append(
                    RepoEvent(
                        event_type="new_release",
                        title=f"New release: {current_release}",
                        url=release.get("html_url", ""),
                        description=(release.get("body", "") or "")[:800],
                        data={"tag": current_release, "previous": prev_release},
                    )
                )
            prev_release = current_release
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pass  # No releases yet
            else:
                raise

        self._save_state({
            "stars": current_stars,
            "forks": current_forks,
            "open_issues": current_open_issues,
            "issue_ids": current_issue_ids,
            "latest_release": prev_release,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })

        return events
