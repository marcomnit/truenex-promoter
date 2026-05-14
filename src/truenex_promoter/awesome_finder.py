"""Discover Awesome Lists relevant to the project."""

import json
import urllib.parse
import urllib.request
from typing import Any

from .config import PromoterConfig


class AwesomeFinder:
    """Find Awesome Lists on GitHub that match project tags."""

    def __init__(self, config: PromoterConfig) -> None:
        self.config = config
        self.token = config.github_token

    def _search(self, query: str) -> list[dict[str, Any]]:
        """Search GitHub repositories."""
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=10"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "truenex-promoter/0.1.0")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("items", [])
        except Exception:
            return []

    def find_candidates(self) -> list[dict[str, Any]]:
        """Find Awesome Lists that might accept the project."""
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()

        # Search queries based on project tags
        queries = [
            "awesome mcp",
            "awesome ai agents",
            "awesome memory",
            "awesome local-first",
            "awesome developer tools",
        ]

        for query in queries:
            for repo in self._search(query):
                full_name = repo.get("full_name", "")
                if full_name in seen:
                    continue
                seen.add(full_name)

                # Basic relevance filter
                description = (repo.get("description") or "").lower()
                if not any(
                    tag in description or tag in repo.get("name", "").lower()
                    for tag in ["awesome", "list", "curated"]
                ):
                    continue

                candidates.append({
                    "name": repo.get("name", ""),
                    "full_name": full_name,
                    "url": repo.get("html_url", ""),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "query_matched": query,
                })

        # Sort by stars (most popular first)
        candidates.sort(key=lambda x: x["stars"], reverse=True)
        return candidates[:20]

    def generate_draft(self, candidate: dict[str, Any]) -> str:
        """Generate a draft PR description for adding the project to an Awesome List."""
        name = self.config.project_name
        url = self.config.project_url
        repo_url = f"https://github.com/{self.config.github_owner}/{self.config.github_repo}"
        desc = self.config.project_description

        lines = [
            f"## Proposal: Add {name}",
            "",
            f"**Project:** [{name}]({repo_url})",
            f"**Website:** {url}",
            "",
            f"**Description:** {desc}",
            "",
            "**Why it fits this list:**",
            f"- {name} is an open-source tool in the {candidate.get('query_matched', 'relevant')} space",
            "- It solves a real problem: persistent memory for AI agents",
            "- Active development with public releases and documentation",
            "",
            "**Suggested placement:**",
            "- In the appropriate section based on existing categorization",
            "",
            "---",
            "",
            "*This PR was drafted by Truenex Promoter, an autonomous marketing agent. Human review required.*",
        ]
        return "\n".join(lines)
