"""Tests for the action queue."""

import tempfile
from pathlib import Path

from truenex_promoter.action_queue import Action, ActionQueue, ActionStatus


def test_add_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ActionQueue(state_dir=Path(tmp))
        action = Action(type="test", title="Test Action", description="desc")
        result = queue.add(action)
        assert result.id
        pending = queue.list_actions(status=ActionStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].title == "Test Action"


def test_approve_and_reject():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ActionQueue(state_dir=Path(tmp))
        action = queue.add(Action(type="test", title="Test"))
        approved = queue.approve(action.id, "looks good")
        assert approved is not None
        assert approved.status == ActionStatus.APPROVED

        rejected = queue.reject("nonexistent", "nope")
        assert rejected is None


def test_get_by_id():
    with tempfile.TemporaryDirectory() as tmp:
        queue = ActionQueue(state_dir=Path(tmp))
        action = queue.add(Action(type="test", title="Test"))
        found = queue.get(action.id)
        assert found is not None
        assert found.title == "Test"
