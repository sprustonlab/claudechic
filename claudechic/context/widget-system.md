---
paths:
  - claudechic/widgets/**
  - claudechic/screens/**
---

# Widget System

## Widget Hierarchy

```
ChatApp
└── ChatScreen (default screen, owns chat-specific bindings)
    ├── Horizontal #main
    │   ├── Vertical #chat-column
    │   │   ├── ChatView (one per agent, only active visible)
    │   │   │   ├── ChatMessage (user/assistant)
    │   │   │   ├── ToolUseWidget (collapsible tool display)
    │   │   │   ├── TaskWidget (for Task tool - nested content)
    │   │   │   └── ThinkingIndicator (animated spinner)
    │   │   └── Vertical #input-container
    │   │       ├── ImageAttachments (hidden by default)
    │   │       ├── ChatInput (or SelectionPrompt/QuestionPrompt)
    │   │       └── TextAreaAutoComplete
    │   └── Vertical #right-sidebar (hidden when narrow)
    │       ├── AgentSection
    │       ├── TodoPanel
    │       └── ProcessPanel
    └── StatusFooter
```

## Styling

Visual language uses left border bars to indicate content type:
- **Orange** (`#cc7700`) - User messages
- **Blue** (`#334455`) - Assistant messages
- **Gray** (`#333333`) - Tool uses (brightens on hover)
- **Blue-gray** (`#445566`) - Task widgets

Context/CPU bars color-code by threshold (dim -> yellow -> red).

Copy buttons appear on hover. Collapsibles auto-collapse older tool uses.
