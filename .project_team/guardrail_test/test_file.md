# Guardrail Validation Test

This file is added intentionally to validate that the
`Block .project_team/ additions on main` GitHub Action and the
`main protection` ruleset correctly block PRs to main that add
.project_team/ paths.

If the PR opens and the check passes, the guardrail is broken.
If the PR opens and the check fails (red X, merge button blocked),
the guardrail works as designed.

This file should never reach main. The PR will be closed without
merging once we confirm the check fails.
