# Quick proposal — converging claudechic forks

Hi abast team,

We've been planning some boundary cleanup work in `sprustonlab/claudechic` (issue #23 — "Settings window + configuration reference documentation," plus related work to move claudechic's own state out of `~/.claude/` so it stops mixing with Claude Code's namespace).

While scoping that, we did a deeper diff of where our forks have ended up since the common ancestor (`285b4d1`, 2026-04-20). The big thing we noticed: both forks independently solved "bundle defaults inside the package" but landed at incompatible directory structures.

- **You** (`d55d8c0`): `claudechic/defaults/{workflows,global}/` for bundled content, engine code stays in `claudechic/workflows/`.
- **Us** (`317f424`): `claudechic/workflows/` for YAML data only, engine split into `claudechic/workflow_engine/`, manifests in `claudechic/global/`.

Our analysis showed roughly 85 files that are byte-near-identical mirrors at incompatible paths between the two forks — a real silent-collision hazard if either side does a naive cherry-pick from the other.

**We'd like to converge on your `defaults/` layout** (move sprustonlab's `workflow_engine/` back into `workflows/`, move our bundled content under `defaults/workflows/` and `defaults/global/`). We restructure first, before pulling anything from you, so the convergence happens cleanly at the layout layer rather than during cherry-picks.

After the restructure we plan to selectively pull most of your divergent commits, then implement issue #23 on the merged tree.

## Why we're proposing this order

- Our analysis pointed to the layout mismatch as the largest cross-fork risk. Converging first dissolves that hazard before any pull.
- Once layouts match, your cherry-picks land cleanly on our tree — no path rewriting, no silent collision.
- It saves us doing forced renames during issue #23 implementation.
- We end up with one canonical layout — we hope yours, on its merits — that both forks share going forward.

## What we'd like to know from you

Four short questions, no rush:

1. **Are you OK with us adopting your `defaults/` layout?** And — would you be willing to pause new work in `claudechic/defaults/` for a window while we restructure, so we don't chase a moving target? If you have a preferred window, name it.

2. **Are there features in your roadmap we should know about?** Specifically anything around a `/settings` screen, the `.claude/` boundary, or config layout — these are the surfaces issue #23 will touch and we'd rather coordinate than build in parallel and discover conflicts later.

3. **Of your 8 commits ahead of merge-base, which do you consider stable / shippable, and which are still experimental?** We'd rather not pull commits you're planning to revisit. Quick gloss on what we're seeing:
   - `d55d8c0` — bundle defaults (cherry-pick the `ManifestLoader` changes; we'll have your YAML content via the restructure)
   - `8e46bca` — workflows_dir resolution fix — looks small, planning to pull
   - `9fed0f3` — docs clarification — planning to pull
   - `f9c9418` — full model ID + loosened validation — UX call on our side
   - `5700ef5` + `7e30a53` — auto-permission mode + Shift+Tab cycle — UX call
   - `26ce198` + `0ad343b` + `fast_mode_settings.json` — `/fast` mode — we're deferring (filed [sprustonlab/claudechic#25](https://github.com/sprustonlab/claudechic/issues/25) to discuss with you separately)

4. **Any commits we should NOT pull, or any dependency / ordering we should know about?** We've already noticed the `0ad343b` (anthropic 0.79.0 pin) gates `26ce198` (`/fast`); since we're skipping `/fast` for now, we're skipping the pin too. Other dependencies?

## What's deferred

- `/fast` mode — separate issue ([sprustonlab/claudechic#25](https://github.com/sprustonlab/claudechic/issues/25)). Happy to discuss when you're ready, including whether the `fast_mode_settings.json` location should change.

## Background, if useful

Full team analysis lives in our repo at `.project_team/issue_23_path_eval/`. The headline documents:
- `RECOMMENDATION.md` — the original recommendation (Path 1 vs Path 2, before this convergence-first plan was decided)
- `plan.md` — what we're planning to do, in execution order
- `fork_diff_report.md` — the concrete diff between our forks (themes, hot files, mirror pairs)
- `terminology_glossary.md` / `composability_eval.md` / `risk_evaluation.md` / `alignment_audit.md` — the four lens analyses that drove the recommendation

Happy to walk through any of these if you'd like context. We're not in a rush — the goal is to get the convergence right, not to ship by a specific date.

Thanks!

— Boaz / sprustonlab/claudechic
