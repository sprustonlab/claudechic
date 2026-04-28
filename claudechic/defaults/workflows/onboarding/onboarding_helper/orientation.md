# Orientation Phase

Give the user a friendly tour of claudechic. Start with what it IS, then show
what they can do, then suggest next steps. Be a tour guide, not a config manager.

## Steps

1. **Explain what claudechic is** -- a terminal UI for Claude Code that adds:
   - A rich TUI with panels, sidebar, and visual feedback (not just a CLI)
   - Multi-agent orchestration -- spawn multiple Claude agents, each with their
     own context, and coordinate them
   - Guardrails -- rules that catch common mistakes before they happen (force push,
     running bare pytest, etc.). Three levels: deny (blocked), warn (ask first),
     log (record only)
   - Workflows -- structured multi-phase guides for common tasks. Each phase has
     instructions and advance checks that gate progression
   - Hints -- contextual tips that appear as toasts to help discover features

2. **Show what they can do** -- key features and commands:
   - **Workflows:** Type `/{id}` to start (e.g., `/git_setup`, `/tutorial`). Show
     the full list grouped by category:
     - Setup: `/git_setup`, `/codebase_setup`, `/cluster_setup`
     - Learning: `/tutorial`, `/tutorial_extending`, `/tutorial_toy_project`
     - Development: `/project_team` (14-role team), `/audit`
   - **Agents:** `/agent <name>` to spawn, Ctrl+1-9 or sidebar to switch,
     Ctrl+G to search, `/agent close` to close
   - **Shell:** `!command` for inline, `/shell -i command` for interactive
   - **Other:** `/diff` (review changes), `/vim` (toggle vi mode),
     `/resume` (session picker), `/compactish` (save context space)
   - **Keybindings:** Enter (send), Ctrl+C x2 (quit), Shift+Tab (cycle permission
     mode), Ctrl+R (history search), Ctrl+L (clear)

3. **Detect project state** and suggest what to do next:
   - Check `git rev-parse --git-dir` -- is this a git repo?
   - Check for non-hidden directories that look like existing codebases.
   - Based on what you find, suggest the most relevant workflow to start with.
   - For users who already have everything set up, suggest `/tutorial` or
     `/tutorial_extending` to learn customization.

4. **Mention configuration briefly:** "You can customize claudechic via
   `.claudechic.yaml` at your project root -- disable specific workflows, suppress
   individual rules or hints. Defaults work well for most users."

5. **Invite questions** -- remind the user they can ask about anything. "Feel free
   to ask about any of these features -- I'm happy to explain in more detail."

6. **Transition:** "Next, we'll install context docs that help Claude agents
   understand claudechic's systems when working on your project."

To advance: user confirms they've seen the tour and are ready to continue.
