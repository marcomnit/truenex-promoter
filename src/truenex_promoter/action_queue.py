"""Action queue with human-in-the-loop approval."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ActionStatus(str, Enum):
    """Status of an action in the queue."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Action:
    """A proposed action awaiting human approval."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""
    status: ActionStatus = ActionStatus.PENDING
    title: str = ""
    description: str = ""
    draft_content: str = ""
    target_url: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str = ""
    completed_at: str = ""
    decision_reason: str = ""


class ActionQueue:
    """Persistent queue of proposed actions."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = state_dir or Path.home() / ".truenex-promoter"
        self.queue_file = self.state_dir / "action_queue.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if self.queue_file.exists():
            return json.loads(self.queue_file.read_text(encoding="utf-8"))
        return []

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.queue_file.write_text(json.dumps(items, indent=2, default=str) + "\n", encoding="utf-8")

    def list_actions(self, status: ActionStatus | None = None) -> list[Action]:
        """List actions, optionally filtered by status."""
        items = self._load()
        actions = [self._deserialize(item) for item in items]
        if status:
            actions = [a for a in actions if a.status == status]
        return actions

    def add(self, action: Action) -> Action:
        """Add a new action to the queue."""
        items = self._load()
        items.append(self._serialize(action))
        self._save(items)
        return action

    def get(self, action_id: str) -> Action | None:
        """Get a specific action by ID."""
        for action in self.list_actions():
            if action.id == action_id:
                return action
        return None

    def approve(self, action_id: str, reason: str = "") -> Action | None:
        """Mark an action as approved."""
        return self._update_status(action_id, ActionStatus.APPROVED, reason)

    def reject(self, action_id: str, reason: str = "") -> Action | None:
        """Mark an action as rejected."""
        return self._update_status(action_id, ActionStatus.REJECTED, reason)

    def mark_done(self, action_id: str) -> Action | None:
        """Mark an action as completed."""
        return self._update_status(action_id, ActionStatus.DONE, "")

    def mark_failed(self, action_id: str, reason: str = "") -> Action | None:
        """Mark an action as failed."""
        return self._update_status(action_id, ActionStatus.FAILED, reason)

    def _update_status(
        self, action_id: str, status: ActionStatus, reason: str
    ) -> Action | None:
        items = self._load()
        for item in items:
            if item.get("id") == action_id:
                item["status"] = status.value
                item["decided_at"] = datetime.now(timezone.utc).isoformat()
                if reason:
                    item["decision_reason"] = reason
                if status in (ActionStatus.DONE, ActionStatus.FAILED):
                    item["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._save(items)
                return self._deserialize(item)
        return None

    def _serialize(self, action: Action) -> dict[str, Any]:
        return asdict(action)

    def _deserialize(self, data: dict[str, Any]) -> Action:
        data = dict(data)
        data["status"] = ActionStatus(data.get("status", "pending"))
        return Action(**data)
