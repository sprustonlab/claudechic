"""Textual widgets for Claude Code UI.

Re-exports all widgets from submodules for backward compatibility.
"""

# Base classes
# Data classes (re-exported for convenience)
from claudechic.processes import BackgroundProcess

# Base re-exports (ClickableLabel used by layout widgets)
from claudechic.widgets.base import ClickableLabel, ToolWidget

# Content widgets
from claudechic.widgets.content import (
    AgentListWidget,
    AgentToolWidget,
    ChatAttachment,
    ChatInput,
    ChatMessage,
    ConnectingIndicator,
    DiffWidget,
    EditPlanRequested,
    ErrorMessage,
    ImageAttachments,
    PendingShellWidget,
    ShellOutputWidget,
    SystemInfo,
    TaskWidget,
    ThinkingIndicator,
    TodoPanel,
    TodoWidget,
    ToolUseWidget,
)

# Input widgets
from claudechic.widgets.input import HistorySearch, TextAreaAutoComplete

# Layout widgets
from claudechic.widgets.layout import (
    AgentItem,
    AgentSection,
    ChatView,
    ChicsessionLabel,
    ContextBar,
    CPUBar,
    FileItem,
    FilesSection,
    HamburgerButton,
    IndicatorWidget,
    ModelLabel,
    PermissionModeLabel,
    PlanItem,
    PlanSection,
    ProcessIndicator,
    ProcessItem,
    ProcessPanel,
    ReviewItem,
    ReviewPanel,
    SessionItem,
    SidebarItem,
    SidebarSection,
    StatusFooter,
    WorktreeItem,
)

# Modal screens
from claudechic.widgets.modals import ProcessModal, ProfileModal

# Primitives
from claudechic.widgets.primitives import (
    AutoHideScroll,
    Button,
    QuietCollapsible,
    Spinner,
)

# Prompts
from claudechic.widgets.prompts import (
    BasePrompt,
    ModelPrompt,
    QuestionPrompt,
    SelectionPrompt,
    UncommittedChangesPrompt,
    WorktreePrompt,
)

# Report widgets
from claudechic.widgets.reports import ContextReport, UsageReport

__all__ = [
    # Base
    "ToolWidget",
    # Primitives
    "Button",
    "QuietCollapsible",
    "AutoHideScroll",
    "Spinner",
    # Content
    "ChatMessage",
    "ChatInput",
    "ThinkingIndicator",
    "ConnectingIndicator",
    "ImageAttachments",
    "ErrorMessage",
    "SystemInfo",
    "ChatAttachment",
    "ToolUseWidget",
    "TaskWidget",
    "AgentToolWidget",
    "AgentListWidget",
    "ShellOutputWidget",
    "PendingShellWidget",
    "EditPlanRequested",
    "DiffWidget",
    "TodoWidget",
    "TodoPanel",
    # Input
    "TextAreaAutoComplete",
    "HistorySearch",
    # Layout
    "ChatView",
    "AgentItem",
    "AgentSection",
    "ChicsessionLabel",
    "WorktreeItem",
    "SessionItem",
    "PlanItem",
    "PlanSection",
    "FileItem",
    "FilesSection",
    "SidebarSection",
    "SidebarItem",
    "HamburgerButton",
    "ClickableLabel",
    "PermissionModeLabel",
    "ModelLabel",
    "StatusFooter",
    "IndicatorWidget",
    "CPUBar",
    "ContextBar",
    "ProcessIndicator",
    "ProcessPanel",
    "ProcessItem",
    "ReviewPanel",
    "ReviewItem",
    "BackgroundProcess",
    # Reports
    "UsageReport",
    "ContextReport",
    # Modals
    "ProfileModal",
    "ProcessModal",
    # Prompts
    "BasePrompt",
    "SelectionPrompt",
    "QuestionPrompt",
    "ModelPrompt",
    "WorktreePrompt",
    "UncommittedChangesPrompt",
]
