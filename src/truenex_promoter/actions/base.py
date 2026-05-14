"""Base class for promoter actions."""

from abc import ABC, abstractmethod
from typing import Any

from ..action_queue import Action
from ..config import PromoterConfig


class ActionExecutor(ABC):
    """Base class for action executors."""

    def __init__(self, config: PromoterConfig) -> None:
        self.config = config

    @abstractmethod
    def generate(self, context: dict[str, Any]) -> Action | None:
        """Generate a proposed action based on context. Returns None if no action needed."""
        ...

    @abstractmethod
    def execute(self, action: Action) -> bool:
        """Execute an approved action. Returns True on success."""
        ...
