# Terminology Review of SPEC.md (post-consolidation)

**Author:** TerminologyGuardian (`terminology_review` seat)
**Reviewed:** `SPEC.md` as of 2026-04-30 19:14
**Phase:** End of specification / start of implementation
**Authority:** Advisory. Composability has final say on architecture; this
review flags drift and proposes convergence. Implementers should consult
this alongside `specification/terminology.md` (the broader spec-phase
glossary) when picking variable names, function names, and prose.

This file complements `specification/terminology.md`. That file catalogs
the cluster's domain terms before consolidation; this file catalogs the
synonyms, overloads, and orphan terms that survived into the final
`SPEC.md`. Implementers should fix these as they touch each component.

---

## Executive summary for implementers

When you write code or prose during implementation, prefer the
**chosen term** column. If the SPEC.md text contradicts, follow the
chosen term and note the SPEC drift in your commit message; we will
reconcile in the documentation phase.

| Concept | Chosen term | Avoid these synonyms |
|---|---|---|
| Agent's runtime self-identity | **`agent.agent_type`** (attr); **role** (prose) | `agent_role`, `main_role` (workflow-side label only), bare `role` as attr |
| Workflow YAML field that names the main role | `main_role` | `role`, `agent_type` |
| Thinking-budget knob | **effort** | `compute budget`, `thinking budget`, `thinking-budget level` |
| Markdown block injected into agent prompts | **Constraints block** | "Rules block", "guardrails block" |
| The YAML rule entity | **guardrail rule** | bare "rule", "constraint" |
| Three inject sites | **spawn / advance / post-compact** | `kickoff`, `workflow activation` (for spawn) |
| "No role assigned" sentinel | `DEFAULT_ROLE = "default"` (per SPEC) | (see Overloaded Terms below for risk) |
| Workflow-root path token in YAML | `${WORKFLOW_ROOT}` (braced) | `$WORKFLOW_ROOT` (bare) |
| Python identifier for the workflow root | `project_root` | `workflow_root` (collides with `workflows_dir`) |

---

## Synonyms Found

### S1. Agent runtime identity has FOUR names

The same value flows through four labels:

| Label | Where it appears |
|---|---|
| `agent_type` | Component B title, instance attr (`Agent.agent_type`), env var `CLAUDE_AGENT_ROLE` source |
| `role` | "agent's role + phase" (lines 261, 311), "role identity" (line 96) |
| `main_role` | Workflow YAML field, B5 manifest validation rule |
| `agent_role` | Parameter name in `compute_digest(loader, active_workflow, agent_role, current_phase, disabled_rules)` (lines 276, 327) |

**Why this matters for implementation:** when you wire B2 -> B3 -> B4 -> D's
projection, the value `agent.agent_type` is read in B/C contexts and
passed as `agent_role=` in D's `compute_digest`. A reader sees three
names for one value across one call chain.

-> **Recommend during implementation:**
- Keep `agent_type` as the attr name (Component B is named for it).
- Rename `compute_digest`'s `agent_role` parameter to `role` OR
  `agent_type` (pick one and stay consistent).
- Use **role** in prose; reserve `main_role` for the YAML field only.
- Add a glossary entry to `context/` docs:
  > **role** (`agent.agent_type`): the agent's runtime self-identity,
  > sourced from the active workflow's `main_role` field.

### S2. Thinking-budget knob has THREE names

| Label | Where it appears |
|---|---|
| "compute budget" | Goal (line 7) |
| "thinking budget" / "thinking-budget level" / "thinking-budget knob" | Component C WHAT/WHY |
| "effort" | Decision 2 (locked), SDK kwarg, attr name `Agent.effort`, env var |

Decision 2 explicitly locked **effort** verbatim for the on-screen label.
The locked decision implies prose convergence too, but the prose did not
follow.

-> **Recommend during implementation:** in any new docstring, comment,
or commit message, use `effort`. In code, the attr is `Agent.effort`.

### S3. Inject-site naming drift (3 vocabularies for 3 sites in one component)

Component D refers to its three inject sites with three different
phrasings:

| Source line | Vocabulary used |
|---|---|
| WHAT line 263 | "workflow activation, phase advance, and `/compact`" |
| D5 lines 291-296 | "sub-agent kickoff", "main-agent phase advance", "/compact re-injection" |
| Constraints line 392 | "spawn / advance / PostCompact" |

"Workflow activation" and "sub-agent kickoff" describe **different
events** -- one is workflow-level (when a workflow is activated), the
other is per-agent (when a sub-agent is spawned). The first inject site
(line 295) is `claudechic/mcp.py::spawn_agent`, which is sub-agent
spawn, not workflow activation.

-> **Recommend during implementation:** use **spawn / advance /
post-compact**, matching the function and hook names actually in code
(`spawn_agent`, `_inject_phase_prompt_to_main_agent`,
`create_post_compact_hook`). When writing the SPEC update or commit
messages, do not refer to the spawn site as "workflow activation."

### S4. Injected markdown block has THREE names

| Label | Where it appears |
|---|---|
| "Constraints block" / "`## Constraints` block" | D WHAT, D5 inject contract, constraint heading itself |
| "Rules" | The table heading inside the block (line 339) |
| "guardrail rules" | `## Applicable guardrail rules` in `get_agent_info` (line 364) |

The relationship between **constraint**, **rule**, and **guardrail** is
unstated. The file lives at `claudechic/guardrails/digest.py`. The
spec sometimes says "rules and advance-checks" and sometimes
"Constraints."

-> **Recommend during implementation:**
- **guardrail rule** = the YAML entity defined in `rules.yaml`.
- **Constraints block** = the markdown rendering of the (rules +
  advance-checks) that apply to a given (role, phase).
- "Rules" inside the block is shorthand for "guardrail rules"; do not
  introduce a third meaning.
- Unify the section heading: pick `## Applicable rules` OR
  `## Applicable guardrail rules` in `get_agent_info`. Do not use both.

---

## Overloaded Terms

### O1. "default" has FOUR meanings in Component B

1. The sentinel constant `DEFAULT_ROLE = "default"` (B1).
2. The string value `"default"` as a valid role.
3. The "engine-level default" for cwd (A3 phrasing).
4. The rejected manifest value (`main_role: default` -- B5 validation).

Implementer reading B5 has to recover that the rejected value (#4)
is rejected because it collides with the sentinel (#1+#2), separated
by 100+ lines.

-> **Recommend (escalate to Composability before implementation lands):**
rename the sentinel to `UNASSIGNED_ROLE` or `NO_WORKFLOW_ROLE`. B5's
rule then reads naturally: "manifests cannot declare `main_role:
default` because `default` is reserved for unassigned agents." If
Composability prefers the literal string `"default"` for backward
compatibility / SDK convention, keep it -- but add a one-line comment
at the constant definition site explaining all four meanings.

### O2. "cluster"

In SPEC.md: a four-commit cluster on `abast/main`.
Elsewhere in claudechic: LSF/Slurm compute cluster.

A new reader of "abast's `accf332` cluster" may read "compute cluster."

-> **Recommend:** spell it "the four-commit cluster on `abast/main`"
on first use in any user-facing doc. Acceptable to abbreviate to
"cluster" thereafter within SPEC.md.

### O3. "active" (lower priority)

`active_workflow` (param), `active: bool` (digest field), "n_active"
(count), "active phase" (current phase). Multiple senses but mostly
clear from context. Leave as-is unless implementer surfaces a real
ambiguity.

---

## Orphan Definitions / Undefined Terms

These terms are used in SPEC.md without an in-document anchor or
forward reference:

| Term | First appearance | Status |
|---|---|---|
| "engine seam" | line 16, 161, 414 | Central organizing metaphor; never defined |
| "Group C" / "Group E" | lines 78, 80 | Referenced as if defined; live in divergence map (appendix) |
| "Skeptic" | line 458 | Proper-noun agent role, not introduced in SPEC.md |
| "Composability" / "Historian" / "Terminology" | appendix | Agent seat names, used without anchor |
| "sprustonlab" / "abast" | from line 7 | Defined in "Naming conventions" at line 532, but used heavily 525 lines earlier |
| "PostCompact" (capitalized) | line 392 | Appears as a hook name; lowercase elsewhere (`create_post_compact_hook`). Pick one. |
| "F401 lint" | line 168 | Undefined; this is a Pyflakes/ruff code for unused imports |
| "+282 patch" | lines 116, 162, 215 | Referenced four times without explaining what was in the +282-line `app.py` diff |

-> **Recommend:** add a 6-10 line glossary block immediately after
the Goal in SPEC.md, OR move the "Naming conventions" subsection
(line 530) up to right after Goal so fork identifiers are defined
before first use. Implementers don't need this fixed to start work,
but it should be fixed during the documentation phase.

---

## Canonical Home Violations / Internal Contradictions

### C1. Reference to a tool that doesn't exist (BUG, not drift)

**Line 313:**
> "Can call `mcp__chic__get_applicable_rules` mid-session to re-query
> when state may have changed."

But Component D defines `mcp__chic__get_agent_info` as the unified
tool, and Decision 5 confirms `get_phase` is replaced by
`get_agent_info`. There is no `get_applicable_rules` defined in this
spec.

-> **Recommend:** treat as a bug. Replace `mcp__chic__get_applicable_rules`
with `mcp__chic__get_agent_info` on line 313. Looks like a leftover from
an earlier draft where the MCP surface had a separate rules tool.

**Implementer impact:** if you implement Component D, do not register
a `get_applicable_rules` tool. Register `get_agent_info` only.

### C2. Component count contradiction

**Line 11:**
> "Five components are in scope. Three sit on existing claudechic
> infrastructure; two are clean adoptions from `abast/main`."

But six components (A-F) are described, and Decision 1 confirms "all
six components (A, B, C, D, E, F)."

-> **Recommend:** change line 11 to "Six components are in scope" OR
explicitly demote F: "Five primary components, plus a sixth (F)
bundled as a mechanical by-product."

---

## Newcomer Blockers

These don't block implementation but should be cleaned in documentation
phase:

- **Goal paragraph (lines 5-9)** assumes the reader knows what `abast`
  is, what `accf332` is, what a "cluster" means here, and what
  "agent-self-awareness substrate" means. Add a 2-sentence preamble:
  what's `abast`, what's `accf332`, what's the substrate.

- **Hyphenation drift** ("advance-check" vs "advance check",
  "main-agent" vs "main agent"). Pick one and ripgrep-fix. Sub-agent
  is consistently hyphenated; main-agent is not.

- **"+282 patch"** -- on first use, explain it: "the +282-line
  `app.py` diff in `accf332` that bundles B, C, D's UI together."

---

## Suggested Concrete Edits to SPEC.md

Low-cost, high-clarity edits, ordered by importance:

| # | Edit | Reason |
|---|---|---|
| 1 | Line 313: `get_applicable_rules` -> `get_agent_info` | **Bug** — references nonexistent tool |
| 2 | Line 11: "Five" -> "Six" or demote F | Internal contradiction with Decision 1 |
| 3 | Line 7: "compute budget" -> "effort level" | Lock Decision 2 in prose |
| 4 | Move "Naming conventions" (line 530) up to just after Goal | Define `abast` / `sprustonlab` before first use |
| 5 | Add 6-line glossary: role / agent_type / effort / Constraints block / guardrail rule / inject sites | Anchor the most-overloaded terms |
| 6 | Pick `role` (or `agent_type`) and replace `agent_role` parameter name in `compute_digest` signature | Eliminate one synonym in the call chain |
| 7 | Pick canonical inject-site triplet (spawn / advance / post-compact) and use it uniformly in WHAT, D5, and Constraints | Eliminate inject-site vocabulary drift |

Edits #1, #3, #6, #7 land in source files implementers will touch
during this phase. Edits #2, #4, #5 are doc-only and can defer to
documentation phase.

---

## What I'm watching for during implementation

Implementers, please ping me (`message_agent terminology_review`)
if you face any of these decisions:

1. **Naming a new attribute on `Agent`.** I'll check it against the
   role / agent_type / effort vocabulary.
2. **Naming a new MCP tool or renaming an existing one.** I'll
   verify it doesn't introduce a fourth synonym for an existing
   concept.
3. **Adding a new template-variable token.** I'll check it uses
   `${VAR}` (braced), not bare `$VAR`.
4. **Naming a parameter in a public function signature** (especially
   `compute_digest`, `compute_advance_checks_digest`,
   `assemble_constraints_block`). The parameter name surfaces in
   tracebacks and IDE completions; pick wisely.
5. **Section headings in markdown injected into agent prompts.** The
   exact strings `## Constraints`, `## Identity`, etc. become part of
   the runtime contract.

No naming-architecture conflicts that need Composability adjudication
right now -- most are convergence/cleanup. Item C1 (the
`get_applicable_rules` reference) is the only finding that looks like
an actual contradiction rather than drift.
