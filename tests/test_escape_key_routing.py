"""Regression tests for Escape key routing from the chat input.

Textual's TextArea with tab_behavior="indent" consumes Escape to
focus_next(), and _on_key handlers are dispatched per MRO class, so a
naive early-return in ChatInput._on_key does not stop TextArea from
eating the key.  This silently broke Escape-to-interrupt whenever the
chat input was focused (which is nearly always).  See
ChatInput._on_key for the fix.
"""

import pytest
from claudechic import ChatApp
from claudechic.widgets import ChatInput, TextAreaAutoComplete


@pytest.mark.asyncio
async def test_escape_reaches_app_action_when_input_focused(mock_sdk):
    """Escape pressed while the chat input is focused must invoke the
    app-level escape action (agent interrupt / prompt dismissal), not be
    consumed by TextArea's focus_next behavior."""
    app = ChatApp()
    async with app.run_test(size=(80, 24)) as pilot:
        input_widget = app.query_one(ChatInput)
        input_widget.focus()
        await pilot.pause()
        assert app.focused is input_widget

        calls: list[bool] = []
        app.action_escape = lambda: calls.append(True)  # type: ignore[method-assign]

        await pilot.press("escape")
        await pilot.pause()

        assert calls, "Escape did not reach the app-level escape action"
        # Focus must stay on the input (TextArea would have moved it away)
        assert app.focused is input_widget


@pytest.mark.asyncio
async def test_escape_closes_autocomplete_without_app_action(mock_sdk):
    """With the autocomplete dropdown open, Escape closes it and does NOT
    fall through to the app-level escape action."""
    app = ChatApp()
    async with app.run_test(size=(80, 24)) as pilot:
        input_widget = app.query_one(ChatInput)
        autocomplete = app.query_one(TextAreaAutoComplete)
        input_widget.focus()

        input_widget.text = "/"
        await pilot.pause()
        assert autocomplete.styles.display == "block"

        calls: list[bool] = []
        app.action_escape = lambda: calls.append(True)  # type: ignore[method-assign]

        await pilot.press("escape")
        await pilot.pause()

        assert autocomplete.styles.display == "none"
        assert not calls, "Escape should be consumed by the autocomplete"
