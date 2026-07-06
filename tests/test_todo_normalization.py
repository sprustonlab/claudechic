"""Regression tests for malformed TodoWrite payloads.

A spawned agent emitted a TodoWrite call whose ``todos`` value was a list of
plain strings instead of a list of dicts. The todo widgets assumed every item
was a dict and called ``item.get(...)``, raising
``AttributeError: 'str' object has no attribute 'get'`` inside the SDK response
loop, which tore down agents. ``_normalize_todos`` coerces the payload at the
single entry boundary so downstream widgets always receive dicts.
"""

import pytest

from claudechic.agent import _normalize_todos
from claudechic.enums import TodoStatus
from claudechic.widgets.content.todo import TodoItem


def test_normalize_list_of_strings():
    """The exact crash input: a list of plain strings."""
    result = _normalize_todos(["do thing one", "do thing two"])
    assert len(result) == 2
    assert all(isinstance(item, dict) for item in result)
    assert result[0]["content"] == "do thing one"
    assert result[0]["status"] == TodoStatus.PENDING.value
    # Every item must support .get (the operation that crashed).
    for item in result:
        assert item.get("status") == "pending"


def test_normalize_well_formed_dicts_pass_through():
    """A normal payload of dicts is preserved unchanged."""
    todos = [
        {"content": "Task 1", "status": "completed", "activeForm": "Doing 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing 2"},
    ]
    result = _normalize_todos(todos)
    assert result == todos


def test_normalize_none_and_non_list():
    """None or a non-list payload yields an empty list, never a crash."""
    assert _normalize_todos(None) == []
    assert _normalize_todos("not a list") == []
    assert _normalize_todos({"todos": []}) == []


def test_normalize_mixed_items():
    """A mix of dicts, strings, and other scalars all become dicts."""
    result = _normalize_todos([{"content": "ok", "status": "pending"}, "raw", 42])
    assert len(result) == 3
    assert all(isinstance(item, dict) for item in result)
    assert result[1]["content"] == "raw"
    assert result[2]["content"] == "42"


def test_string_item_would_crash_tooditem_without_normalization():
    """Document the original failure: a bare string breaks TodoItem.__init__."""
    with pytest.raises(AttributeError):
        TodoItem("do thing one")  # type: ignore[arg-type]


def test_normalized_strings_build_tooditem_cleanly():
    """Normalized output constructs TodoItem without raising."""
    for todo in _normalize_todos(["do thing one", "do thing two"]):
        item = TodoItem(todo)
        assert item.has_class("pending")
