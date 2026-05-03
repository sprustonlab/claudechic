# End-to-End Walkthrough — `independent_chic` features

Read this top-to-bottom while restarting claudechic. Each section walks one feature: what to do, what to expect, what to flag if it doesn't match.

When you finish a section, drop a quick note at the bottom of that section (✓ / ✗ / NOTES). We'll come back to anything marked ✗ or NOTES after the walkthrough is done.

---

## 0. Before you restart

Take a baseline of what's currently on disk so you can tell what changes after restart. Run these in your terminal:

```bash
ls ~/.claude/rules/claudechic_*.md 2>/dev/null | wc -l
ls ~/.claudechic/ 2>/dev/null
ls .claudechic/ 2>/dev/null
cat ~/.claudechic/config.yaml 2>/dev/null
git log --oneline -5
```

Expected:
- `~/.claude/rules/claudechic_*.md` count: **0** before restart (the awareness install hasn't run yet from the new code)
- `~/.claudechic/` may exist with `config.yaml` (the relocated user config from Group B)
- `.claudechic/` in this repo: at minimum `hints_state.json`, `hits.jsonl` after the relocation
- `git log -5` should show: `06e2caf` (docs refresh) at top, then `3dc0ffd` `0e4b2e4` `efc94ed` `f5b7225`

state


(base) [slc-ws1 moharb@e02u03]~/claudechic> ls ~/.claude/rules/claudechic_*.md 2>/dev/null | wc -l
8
(base) [slc-ws1 moharb@e02u03]~/claudechic>  ls ~/.claude/rules/claudechic_*.md
/groups/spruston/home/moharb/.claude/rules/claudechic_checks-system.md        /groups/spruston/home/moharb/.claude/rules/claudechic_hints-system.md
/groups/spruston/home/moharb/.claude/rules/claudechic_claudechic-overview.md  /groups/spruston/home/moharb/.claude/rules/claudechic_manifest-yaml.md
/groups/spruston/home/moharb/.claude/rules/claudechic_CLAUDE.md               /groups/spruston/home/moharb/.claude/rules/claudechic_multi-agent-architecture.md
/groups/spruston/home/moharb/.claude/rules/claudechic_guardrails-system.md    /groups/spruston/home/moharb/.claude/rules/claudechic_workflows-system.md
(base) [slc-ws1 moharb@e02u03]~/claudechic> ls ~/.claudechic/
config.yaml
(base) [slc-ws1 moharb@e02u03]~/claudechic> ls .claudechic/
hints_state.json
(base) [slc-ws1 moharb@e02u03]~/claudechic> cat ~/.claudechic/config.yaml
analytics:
  enabled: false
default_permission_mode: auto
theme: chic
---

## 1. Restart claudechic

In another terminal (or after this session ends):

```bash
cd /groups/spruston/home/moharb/claudechic
uv run claudechic
```

Expected: TUI starts; coordinator agent appears; no errors in the status footer.

If startup hangs or errors, capture:
- The terminal output
- Any `~/.claude/logs/` updates

✓ / ✗ / NOTES:✓


---

## 2. Awareness install — first feature to verify (because it fires on startup)

After the TUI is up, **in a separate terminal**:

```bash
ls ~/.claude/rules/claudechic_*.md
```

Expected: **9 files** (`claudechic_CLAUDE.md`, `claudechic_checks-system.md`, `claudechic_claudechic-overview.md`, `claudechic_guardrails-system.md`, `claudechic_hints-system.md`, `claudechic_manifest-yaml.md`, `claudechic_multi-agent-architecture.md`, `claudechic_workflows-system.md`, plus possibly one more).




[slc-ws1 moharb@e02u03]~/claudechic> ls ~/.claude/rules/claudechic_*.md
/groups/spruston/home/moharb/.claude/rules/claudechic_checks-system.md        /groups/spruston/home/moharb/.claude/rules/claudechic_hints-system.md
/groups/spruston/home/moharb/.claude/rules/claudechic_claudechic-overview.md  /groups/spruston/home/moharb/.claude/rules/claudechic_manifest-yaml.md
/groups/spruston/home/moharb/.claude/rules/claudechic_CLAUDE.md               /groups/spruston/home/moharb/.claude/rules/claudechic_multi-agent-architecture.md
/groups/spruston/home/moharb/.claude/rules/claudechic_guardrails-system.md    /groups/spruston/home/moharb/.claude/rules/claudechic_workflows-system.md


Now compare one of them to the bundled source:

```bash
diff ~/.claude/rules/claudechic_workflows-system.md \
     /groups/spruston/home/moharb/claudechic/claudechic/context/workflows-system.md
```

Expected: **no output** (they should be identical).

Now, in the claudechic TUI, ask the agent something workflow-related (e.g., "what's a workflow?"). The agent should answer using the installed context. If it says "I don't have specific info about claudechic workflows" or similar, the install isn't actually reaching the agent.

✓ / ✗ / NOTES: Not great, i had the files before. 

---

## 3. Settings UI — three entry points

### 3a. Footer Settings button

Look at the footer of the TUI. You should see a "Settings" label/button. Click it (or use the keyboard shortcut if one exists).

Expected: a settings screen mounts showing two sections — "User settings" and "Project settings" — with a list of keys per section.

✓ / ✗ / NOTES: ✓

### 3b. `/settings` slash command

From the chat input, type `/settings` and press Enter.

Expected: the same settings screen mounts.

✓ / ✗ / NOTES: ✓ 

### 3c. Welcome screen Settings action

Use `/clear` or restart claudechic so you see the welcome screen. Look for a "Settings" action item.

Expected: choosing it opens the same settings screen.

✓ / ✗ / NOTES: ✓

### 3d. Settings parity

Confirm all three entry points open the same screen (not three different ones).

✓ / ✗ / NOTES: ✓

---

## 4. Settings UI — toggle behavior

Open the settings screen (any entry point).

### 4a. `awareness.install` toggle

Find the `awareness.install` row in User settings. Helper text should mention: *"Disabling stops new installs but does not remove already-installed files"*.

Toggle it OFF. Save (live save per edit, no Save button).

Now in another terminal:

```bash
ls ~/.claude/rules/claudechic_*.md
```

Expected: the **same 9 files** still there. Disabling does NOT delete them. (You'd have to manually `rm` them.)

Now restart claudechic. Then check the rule files again.

Expected: **same 9 files** still there. The install routine no-oped because the toggle is off.

Toggle the toggle back ON. Restart again. Files still there (or refreshed). ✓.

✓ / ✗ / NOTES: ✓

This is not the test. I also deleted them, restarted, still not there. Then I reenabled restarted and they are there.
We need to check they work from there!


### 4b. Permission mode default

Look at the footer. The permission-mode label should read something like **"Auto: safe tools auto-approved"** (the user-mandated wording).

Press Shift+Tab. The cycle should include `auto` — something like `bypassPermissions / auto / acceptEdits / plan / default` (or whatever the current cycle order is).

✓ / ✗ / NOTES: ✓

### 4c. DisabledWorkflows / DisabledIds subscreens

In the settings screen, find the "Disabled workflows" row and click into it.

Expected: subscreen with one row per `(tier, workflow_id)` tuple. Helper text says *"Disabling a workflow by ID hides it from this project regardless of which level (package / user / project) defines it."*

Try toggling one off. Esc back to settings. Toggle the parent row. Reopen. Verify state persists.

Same with "Disabled IDs" — separate subscreens for hints and guardrail rules with category headers.

✓ / ✗ / NOTES: ✗ 
There is no tuple, space does nothing.

### 4d. Reference row → MarkdownPreviewModal

Find the reference row (something like "View configuration reference"). Click it.

Expected: an in-TUI markdown preview modal opens showing `docs/configuration.md`. NOT a webbrowser launch.

Esc to close.

✓ / ✗ / NOTES: ✓

---

## 5. Workflow picker — level badges

Type `/onboarding` (or any other workflow) without choosing a chicsession yet, OR open the workflow picker via whatever entry point claudechic exposes.

Expected: each workflow row shows a level badge:
- `[pkg]` for package-tier
- `[user]` for user-tier  
- `[proj]` for project-tier

If the same workflow exists at multiple levels, the picker shows **one row per (tier, id) tuple** with badges, and a "(defined at: ...)" line listing all tiers where it's present. Sort: project > user > package.

To test multi-tier: copy a package workflow into `~/.claudechic/workflows/` (just create a directory matching one in `claudechic/defaults/workflows/` and put a stub manifest there).

✓ / ✗ / NOTES: ✗
No level badge.

---

## 6. Auto permission mode — full Shift+Tab cycle

From the chat, repeatedly press Shift+Tab. The footer permission-mode label should cycle through the modes including `auto`.

✓ / ✗ / NOTES: ✓ 

---

## 7. Phase context — verify NO file is written

Activate a workflow (e.g., `/project_team` or `/onboarding`). Pick or create a chicsession.

While the workflow is active, in another terminal:

```bash
find . -name "phase_context.md" 2>/dev/null
find ~/.claude -name "phase_context.md" 2>/dev/null
find ~/.claudechic -name "phase_context.md" 2>/dev/null
```

Expected: **no matches anywhere**. The file is gone — engine sends phase-prompt content directly to the active agent inline.

If you see the agent receiving phase instructions correctly (e.g., it knows what phase it's in, knows what to do per the phase docs), in-memory delivery is working.

✓ / ✗ / NOTES:✓ 

---

## 8. Artifact dirs — `set_artifact_dir` mechanism

Activate `/project_team`. After Vision phase, you'll be in Setup phase.

The Setup phase coordinator should call the `set_artifact_dir` MCP tool. Watch for it. Try advancing the phase WITHOUT a `set_artifact_dir` call yet.

Expected: advance is **blocked** with a user-visible error: *"Artifact directory not set — call `set_artifact_dir(...)` MCP tool before advancing."* (This is `ArtifactDirReadyCheck`.)

After the coordinator calls `set_artifact_dir(<some_path>)`, advance should succeed and the path should be created on disk.

In another terminal, verify the directory:

```bash
ls -la <the_path_the_coordinator_chose>
```

✓ / ✗ / NOTES: ✓

### 8a. Artifact dir survives resume

Close claudechic. Restart it. Resume the same chicsession.

Expected: the engine restores the artifact_dir from chicsession state without the coordinator having to re-call `set_artifact_dir`. The advance-check passes immediately. Subsequent phases get prompts with `${CLAUDECHIC_ARTIFACT_DIR}` substituted to the saved path.

 ✓/ ✗ / NOTES:  ✓

### 8b. Artifact dir survives missing-on-disk

Close claudechic. **Delete the artifact directory** from disk. Restart claudechic and resume.

Expected: a WARNING in the log saying the saved artifact_dir doesn't exist. The engine **keeps the path stored** (doesn't auto-recreate, doesn't crash). When you try to write to that path later (e.g., a sub-agent writes a spec), you'll see a real failure — by design.

✓ / ✗ / NOTES: ✗ I don't see a warning, check ~/claudechic.log?

---

## 9. Tier-aware disable — bare and tier-prefixed

Edit your project config at `<repo>/.claudechic/config.yaml`:

```yaml
disabled_workflows:
  - audit                   # bare — disables audit at all tiers
  - user:onboarding         # tier-targeted — disables only the user-tier onboarding
```

Restart claudechic. Open the workflow picker.

Expected:
- `audit` workflow does not appear at any tier.
- `onboarding` appears (assuming you don't have a user-tier override of it). If you DO have a user-tier `onboarding`, the package-tier one should win because user-tier was disabled.

Try a typo:

```yaml
disabled_workflows:
  - tpyooed_id              # unknown bare id
  - pkg:typo                # invalid tier prefix
```

Restart. Expected: both produce **WARNING** logs, no crash, claudechic still runs.

✓ / ✗ / NOTES: ✗

---

## 10. Boundary — verify state is in `.claudechic/`, not `.claude/`

```bash
ls -la ~/.claudechic/
ls -la ~/.claude/
ls -la .claudechic/
ls -la .claude/
```

Expected:
- `~/.claudechic/config.yaml` exists (relocated from `~/.claude/.claudechic.yaml`).
- `~/.claude/.claudechic.yaml` either doesn't exist, OR if it exists is leftover (per A9, no migration; you may have stale files there from before).
- `.claudechic/hints_state.json` exists.
- `.claudechic/hits.jsonl` exists (guardrail audit log).
- `.claudechic/runs/<chicsession>/` may exist if the project_team workflow ran.
- `.claude/phase_context.md` does NOT exist.

✓ / ✗ / NOTES: ___

---

## 11. Worktree symlinks (only if you use git worktrees)

Skip if you don't typically work with worktrees.

```bash
git worktree add /tmp/test-claudechic-wt -b test/claudechic-walkthrough
ls -la /tmp/test-claudechic-wt/.claude
ls -la /tmp/test-claudechic-wt/.claudechic
```

Expected: both `.claude` and `.claudechic` are **symlinks** pointing back to the main worktree. (Windows users skip — see issue #26.)

Cleanup:

```bash
git worktree remove /tmp/test-claudechic-wt
```

✓ / ✗ / NOTES: ___

---

## 12. Cherry-picked features

### 12a. Full model ID validation (`f9c9418`)

Open settings → model selection. Try entering a full model ID (e.g., `claude-opus-4-5-20250101` or however the API name looks). Loosened validation should accept it.

✓ / ✗ / NOTES: ✓

### 12b. Better guardrail messaging — REMOVED

Cherry-pick `003408a` was reverted in this run (transitive deps not in scope). The retry-loop-improvement guardrail messages from that commit should NOT be present.

To verify:

```bash
git log --oneline | grep "003408\|guardrail.*retry"
```

You should see commits about applying AND reverting `003408a`. If you see the messaging behavior of `003408a` actively in the UI, that would be wrong.

✓ / ✗ / NOTES: ___

### 12c. workflow_engine doc clarification (`9fed0f3`)

Skim `claudechic/defaults/workflows/onboarding/onboarding_helper/identity.md` (or wherever the spawn_agent docs are). The `type=` parameter explanation should match the user's mental model from the cherry-pick.

✓ / ✗ / NOTES: ___

---

## 13. Documentation sanity

Open these and skim — they should match the post-implementation reality:

- `docs/configuration.md` — the configuration reference (9 sections; awareness install, overriding workflows, etc.)
- `docs/release-notes/independent_chic.md` — the new release notes file
- `CLAUDE.md` (project root) — file map, commands list, Shift+Tab cycle
- `claudechic/context/CLAUDE.md` — the agent-facing quick reference (this is what gets installed to `~/.claude/rules/claudechic_CLAUDE.md`)

The agent-facing one (`claudechic/context/CLAUDE.md`) had a critical fix in `06e2caf` — the `disabled_ids` schema was wrong (showed nested `guardrails.disabled_ids` / `hints.disabled_ids`); now correctly shows flat `disabled_ids: [...]`.

✓ / ✗ / NOTES: ___

---

## 14. Test suite (optional but valuable)

If you have time before the final sign-off:

```bash
uv run pytest tests/ -n auto
```

Expected: 621 pass, 1 skipped (live-SDK gate), 0 failed. The 3 `test_app_ui.py` Textual-pilot timing flakes are intermittent under parallel mode but pass serially:

```bash
uv run pytest tests/test_app_ui.py -v
```

✓ / ✗ / NOTES: ___

---

## 15. After the walkthrough

When you've gone through everything, come back and tell me:
- Anything marked ✗ or with NOTES
- Anything that surprised you
- Anything you'd want changed before final sign-off

If everything is ✓, the workflow is ready to exit with your approval and the run is complete.

---

*End of walkthrough. The run state is preserved in `STATUS.md` + `SPEC.md` + `SPEC_APPENDIX.md` + this file; we can pick up wherever you stop.*
