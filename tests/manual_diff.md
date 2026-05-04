# Manual verification -- `diff_review_ux`

This file is the manual-check landing pad for behaviors that cannot
reasonably be expressed inside the Textual `app.run_test()` pilot
(per `TEST_SPECIFICATION.md` s7). Run these checks once at sign-off
and record the result in
`.project_team/diff_review_ux/STATUS.md`.

## M1 -- Session-lifetime hide loss / `--resume` non-restoration

**What the spec promises (`SPECIFICATION.md` s15):**

> `claudechic --resume` does not preserve hide state. A fresh process
> means a fresh `HideStore`. Documented; not a future bug.

**Why this is manual:**
Process restart cannot be expressed inside `app.run_test()`. A
subprocess-per-test runner harness is more weight than this
single behavior justifies; one manual verification at sign-off is
cheaper.

**Steps:**

1. From the repo root, launch claudechic:

   ```
   uv run claudechic
   ```

2. In any subdirectory of the repo with at least one tracked file
   modified in the working tree, run `/diff` to mount `DiffScreen`.

3. Press `f` on at least one file to hide it. Confirm the file
   greys out in `DiffSidebar` and its `FileDiffPanel` is hidden.
   Optionally also press `d` on a file in a subdirectory so a
   prefix is in `hide_prefixes` too.

4. Press `q` (or `escape`) to dismiss `DiffScreen`. Then press
   `Ctrl+C` twice (or run `/exit`) to quit claudechic.

5. Relaunch claudechic, with EITHER:

   ```
   uv run claudechic
   ```

   OR (the more interesting case for the documented behavior):

   ```
   uv run claudechic --resume
   ```

6. Open `/diff` again in the same repo / cwd you used in step 2.

**Expected outcome:**

- Every file from step 2 is fully visible (NOT greyed). Status
  letter in `DiffSidebar` is the normal `M` / `A` / `D` / `R` / `U`
  rather than `.`. No `.hidden-entry` styling.
- `FileDiffPanel.display` is True for every file.
- Pressing `r` is a no-op visually -- there is nothing to reset.

This confirms that `HideStore` does NOT persist across process
exit, even with `--resume`. The behavior matches `SPECIFICATION.md`
s15 ("`claudechic --resume` does not preserve hide state. A fresh
process means a fresh HideStore").

**Recording the result:**

Append a line to `.project_team/diff_review_ux/STATUS.md` of the
form:

```
M1 manual: PASS at <YYYY-MM-DD> by <reviewer>; hides cleared on
restart with and without --resume; no .hidden-entry styling on
relaunch.
```

If the manual check FAILS (any file from step 2 is still greyed on
relaunch), that is a regression against `SPECIFICATION.md` s15.
File a bug; do NOT mark M1 as passed.
