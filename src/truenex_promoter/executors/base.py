"""Base class for action executors."""

import webbrowser
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..action_queue import Action
from ..config import PromoterConfig


class Executor(ABC):
    """Base class for action executors.

    MVP philosophy: executors generate ready-to-use files and open browsers,
    rather than performing fully automated actions (to avoid bans and mistakes).
    """

    def __init__(self, config: PromoterConfig) -> None:
        self.config = config
        self.executions_dir = config.state_dir / "executions"
        self.executions_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def can_execute(self, action: Action) -> bool:
        """Return True if this executor can handle the action."""
        ...

    @abstractmethod
    def execute(self, action: Action) -> dict[str, Any]:
        """Execute the approved action.

        Returns a dict with:
        - success: bool
        - output_path: str | None
        - message: str
        - url_to_open: str | None
        """
        ...

    def _save_execution(self, action: Action, content: str, ext: str = "md") -> Path:
        """Save execution material to a file."""
        filename = f"{action.type}_{action.id}.{ext}"
        path = self.executions_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def _open_browser(self, url: str) -> None:
        """Open a URL in the default browser."""
        try:
            webbrowser.open(url)
        except Exception:
            pass
