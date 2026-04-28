# Context Docs Phase

Install claudechic context docs into the project's `.claude/rules/` directory.

## Steps

1. **Locate the package context directory:**
   ```bash
   python -c "from pathlib import Path; print(Path(__import__('claudechic').__file__).parent / 'context')"
   ```

2. **List available context docs** (all `.md` files in that directory).

3. **Check `.claude/rules/`** for existing files with the same names. For each:
   - If missing: mark as NEW.
   - If present and identical: mark as SKIP.
   - If present and different: mark as UPDATE.

4. **Present the installation plan** as a table:
   ```
   File                          Status
   claudechic-overview.md        NEW (will create)
   workflows-system.md           SKIP (identical)
   hints-system.md               UPDATE (content changed)
   ```

5. **Ask the user** if they want to proceed, or skip context docs entirely.

6. **If proceeding:** Create `.claude/rules/` if needed, then copy NEW and UPDATE
   files using Read and Write tools. Report what was installed/updated/skipped.

7. **Tell the user** they can re-run `/onboarding` after upgrading claudechic to
   pick up updated context docs.

To advance: context docs installed, or user explicitly skips.
