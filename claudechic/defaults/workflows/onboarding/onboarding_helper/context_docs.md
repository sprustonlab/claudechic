# Context Docs Phase

Re-install claudechic's bundled context docs into the user's
`~/.claude/rules/` directory by invoking the idempotent install routine.

claudechic auto-runs this install routine on every startup. This phase
is the **manual re-install primitive** — useful after the user disables
the `awareness.install` config toggle and later wants to re-sync, or
when explicitly walked through onboarding for the first time.

## Steps

1. **Run the install routine** via the Bash tool:

   ```bash
   python -c "from claudechic.awareness_install import install_awareness_rules; r = install_awareness_rules(force=True); print(r)"
   ```

   The `force=True` argument bypasses the `awareness.install` config
   toggle so the install runs even when the user has disabled the
   automatic startup install.

2. **Report the result** to the user. The printed `InstallResult`
   carries five fields:

   - `new=[...]` — files freshly installed
   - `updated=[...]` — files overwritten because content drifted
   - `skipped=[...]` — files already identical (no write)
   - `deleted=[...]` — orphan `claudechic_*.md` files removed (no
     longer in the bundled catalog)
   - `skipped_disabled=False` — should be `False` here because of
     `force=True`

   Summarize in plain language, e.g.: *"Installed 2 new context docs,
   updated 1, skipped 5 already up-to-date, removed 1 obsolete file."*

3. **Mention the symlink guard** if relevant. If the install routine
   logged any WARNING about a symlink at a `~/.claude/rules/claudechic_*.md`
   path, surface it to the user — claudechic deliberately did not touch
   that file because it appears to be user-managed.

4. **Tell the user how to refresh later.** They can re-run
   `/onboarding context_docs` after upgrading claudechic to pick up
   newly-bundled context docs, or disable the `awareness.install`
   config key (settings) to opt out of the automatic startup install.

To advance: install routine ran and the user has been informed of the
results, or the user explicitly skips.
