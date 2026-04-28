# Setup Phase

1. Determine working_dir (must be absolute path)
2. Check for existing state at `{working_dir}/.project_team/*/STATUS.md`
   - If exists: ask user to resume or start fresh
3. Derive project_name from vision (short, lowercase, underscores)
4. Call `set_artifact_dir(<absolute_path>)` MCP tool. Choose a path for the
   project state directory — common conventions are
   `<working_dir>/.project_team/<project_name>/` (preserves the existing
   `.project_team/` layout) or `<working_dir>/.claudechic/runs/<project_name>/`
   (under `.claudechic/`). The tool resolves the path, creates it, and binds
   it to this run. Then create STATUS.md and userprompt.md at the resolved
   path. Subsequent agents spawned in Phase 3 (Leadership) see the resolved
   path baked into their workflow markdown via `${CLAUDECHIC_ARTIFACT_DIR}`
   substitution; any agent MAY also call `get_artifact_dir()` to query the
   path at runtime.
5. Check for git -- advise user if no version control detected
