"""Notify about events and actions."""

import sys
from datetime import datetime, timezone
from pathlib import Path


class Notifier:
    """Send notifications about events and actions."""

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or Path.home() / ".truenex-promoter" / "activity.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def info(self, message: str) -> None:
        """Log an informational message."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{now}] INFO: {message}"
        self._safe_print(line)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def event(self, event_type: str, title: str, url: str, description: str = "") -> None:
        """Log a detected event."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "=" * 60,
            f"[{now}] EVENT: {event_type.upper()}",
            f"Title: {title}",
            f"URL: {url}",
        ]
        if description:
            lines.append(f"Description: {description[:500]}")
        lines.append("=" * 60)
        msg = "\n".join(lines)
        self._safe_print(msg)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def action_proposed(self, action_id: str, title: str, description: str) -> None:
        """Notify that a new action is pending approval."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "-" * 60,
            f"[{now}] ACTION PROPOSED (ID: {action_id})",
            f"Title: {title}",
            f"Description: {description}",
            f"Approve:  trnx-promoter --approve {action_id}",
            f"Reject:   trnx-promoter --reject {action_id}",
            "-" * 60,
        ]
        msg = "\n".join(lines)
        self._safe_print(msg)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def _safe_print(self, text: str) -> None:
        """Print to stdout, handling Windows encoding gracefully."""
        try:
            print(text)
        except UnicodeEncodeError:
            # Fallback: replace non-ASCII characters for Windows terminals
            # that don't support UTF-8 (cmd.exe without chcp 65001)
            print(text.encode("ascii", "replace").decode("ascii"))
