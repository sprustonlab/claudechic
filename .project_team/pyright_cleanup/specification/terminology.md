> **SUPERSEDED:** see `SPECIFICATION.md` (vocabulary folded into s 2 / s 10) and `SPECIFICATION_APPENDIX.md` (synonym audit folded into Part 2). This file is retained as authoring history.

# Terminology -- pyright_cleanup

**Status:** Specification phase, aligned with `composability.md` after vocabulary reconciliation.
**Owner:** Composability lead has final say; this file is the canonical home for naming and is consistent with the disposition vocabulary defined in `specification/composability.md`.
**Scope:** Every term used in `userprompt.md`, `STATUS.md`, the Vision, `composability.md`, and downstream worker artifacts. Other artifacts MUST reference this file rather than redefine.

> Vocabulary reconciliation note: An earlier draft of this file proposed a richer triage taxonomy (Latent issue, Type-truth fix, Refactor-required error, Test-relaxed). Composability folded those into the manifest's `disposition` field with structured `notes`. This document now mirrors composability's disposition vocabulary verbatim and adds only the synonym discipline, overload resolution, and pyright glossary needed to keep usage consistent.

---

## 1. Purpose

A pyright finding can mean very different things depending on whether it points at a runtime bug, a missing annotation, a third-party stub gap, or a config policy. Without crisp names, Implementer and Skeptic will classify the same finding differently and the manifest record will be unauditable. This document fixes one name per concept and one definition per name.

---

## 2. Canonical Disposition Vocabulary

The manifest's `disposition` field is the authoritative classification. Every pyright finding is a manifest row with exactly one disposition. Definitions are normative copies from `composability.md`; cite that file as the source of truth for the schema.

### 2.1 Allowed dispositions

| Disposition | Definition | Region | Lane | Verification |
|---|---|---|---|---|
| **`mechanical`** | A finding resolved by annotation, narrowing (`assert` / `isinstance` / `cast`), scoped `# type: ignore[<rule_id>]`, or import correction. **No runtime behavior change.** | non-test, test | sweep | pyright-only |
| **`real-bug`** | A finding reflecting a runtime defect (None deref, wrong call signature, missing branch, etc.). Fix changes runtime behavior. | non-test, test | bugfix | pyright+targeted:`<node_id>` |
| **`config-relax`** | A pyright config change in `[tool.pyright.executionEnvironments]` that downgrades a specific rule's severity (typically to `"none"`) for a scoped path. **Path is still type-checked**; specific rules are silenced. **User-approved test mechanism.** | test only | sweep | pyright-only |
| **`stub-fix`** | A finding resolved by adding or correcting a local `.pyi` stub under the project's `stubPath`, or by switching to a maintained stub package. | non-test, test | sweep | pyright-only |
| **`stub-ignore`** | A finding silenced via scoped `# type: ignore[import]` or `reportMissingTypeStubs` config because no stub is feasible. | non-test, test | sweep | pyright-only |
| **`dropped`** | A finding the team has chosen not to fix in this project. Requires structured `notes` prefix (see s 2.3, I5 amendment). | non-test, test | none | n/a |

### 2.2 Disallowed disposition

| Disposition | Status | Why named |
|---|---|---|
| **`config-exclude`** | **FORBIDDEN in both regions** (composability I8). Refers to `[tool.pyright].exclude = [...]` or file-level `# pyright: ignore`. The user explicitly rejected this mechanism: "relaxed ruleset, NOT exclusion." | Listed so triage can recognize and reject any temptation to use it. No row may have `disposition = config-exclude`. |

### 2.3 `dropped` notes-prefix convention (composability I5 amendment)

Every `dropped` row's `notes` field MUST begin with one of these prefixes, followed by a one-line justification:

| Prefix | Meaning | Required extra |
|---|---|---|
| **`wontfix:`** | Permanently declined; will not be revisited. | -- |
| **`refactor-required:`** | Pyright is right and the truth cannot be expressed without restructuring code. Deferred for follow-on work. | Tracking handle (issue link, TODO comment ref, or follow-on project name). |
| **`duplicate:`** | Subsumed by another manifest row. | `error_id` of the canonical row. |
| **`false-positive:`** | Pyright is wrong and there is no scoped suppression mechanism that fits. | Brief upstream-bug reference if applicable. |

This preserves discoverability of refactor-required items without adding a disposition value.

---

## 3. Other Domain Terms

These are project-level nouns referenced by composability and the workflow but not part of the `disposition` vocabulary.

| Term | Definition | Source |
|---|---|---|
| **finding** | A single pyright diagnostic at a `(file, line, col, rule_id)` tuple. Generic noun before triage assigns a disposition. | this file s 4.1 |
| **error** (composability sense) | Synonym for finding when used in `composability.md`. Stable inside that doc; outside it, prefer "finding." | `composability.md` Definitions |
| **non-test code** | Any `.py` file outside `tests/`. | `composability.md` |
| **test code** | Any `.py` file under `tests/`. | `composability.md` |
| **manifest** | The single artifact at `specification/manifest.jsonl` enumerating every finding and its disposition. | `composability.md` |
| **pyright snapshot** | Output of `uv run pyright` saved with timestamp under `specification/snapshots/`. | `composability.md` |
| **lane** | The implementer that owns a row: `sweep`, `bugfix`, or `none`. | `composability.md` |
| **verification** | Check that confirms a row is resolved: `pyright-only`, `pyright+targeted:<node_id>`, `pyright+suite`. | `composability.md` |
| **triage** | The act of assigning each finding to exactly one disposition. | this file |
| **principled suppression** | A `# type: ignore[<rule_id>]` accompanying a `mechanical` or `stub-ignore` row, with `proposed_fix` stating the reason. Required form: `# type: ignore[<rule_id>]  # <reason>`. | this file s 6 |
| **band-aid suppression** | A bare `# type: ignore` (no rule_id selector) or one used to silence a `real-bug`. **Forbidden by composability I6 and I2.** | `composability.md` I6 |
| **strict-mode creep** | Adopting `strict = true`, `typeCheckingMode = "strict"`, or enabling additional rules beyond the current basic baseline. **Out of scope** (Vision: failure mode). | this file |

---

## 4. Overloaded-Term Resolution

### 4.1 "error"

`error` is overloaded across pyright (severity level), Python (`Exception`), composability prose, and informal speech. Disambiguate:

- **finding** -- a pyright diagnostic. Preferred outside `composability.md`.
- **error** (in `composability.md`) -- synonym for finding. Stable in that document.
- **error severity** -- the pyright severity `"error"` (vs `"warning"`, `"information"`, `"none"`).
- **runtime exception** -- a Python exception raised at runtime. Reserve for what `real-bug` rows describe.

### 4.2 "fix"

- **logic fix** -- changes runtime behavior; resolves a `real-bug` row.
- **mechanical fix** -- the umbrella for everything in disposition `mechanical`: annotation, narrowing, scoped ignore, import correction.
- **suppression** -- adds `# type: ignore` (must be principled per I6).

When prose says "fix," qualify it unless context makes one of the three unambiguous.

### 4.3 "exclusion" vs "relaxation" vs "exclude"

These three were conflated in the Vision draft. They now have crisp, non-overlapping meanings:

| Word | Meaning | Disposition | Allowed? |
|---|---|---|---|
| **relaxation** / "relax" | Per-rule severity downgrade in `executionEnvironments`. Path still type-checked. | `config-relax` | Yes, test region only |
| **exclude** / "exclusion" | `[tool.pyright].exclude = [...]` or file-level `# pyright: ignore`. Path not type-checked. | `config-exclude` | **No** (forbidden by I8) |
| **scoped ignore** | Per-line `# type: ignore[<rule_id>]`. | `mechanical` (or `stub-ignore` for imports) | Yes, with rule_id |

Never write "test exclusion" to mean "config-relax." That is the precise wording the user rejected.

### 4.4 "test"

- **test code** / **test file** -- any `.py` under `tests/`.
- **test run** -- an execution of pytest.
- **test region** -- the Region axis value `test` (composability Axis R).

---

## 5. Pyright Glossary (newcomer onboarding)

Terms a newcomer will encounter; defined here once.

| Term | Definition |
|---|---|
| **rule_id** / **error code** | A pyright identifier like `reportOptionalMemberAccess` naming the rule that fired. Always cited in `error_id` and in scoped ignores. |
| **strictness level** | Pyright preset bundle: `off` / `basic` / `strict` / `all`. claudechic uses `basic`. Changing this is strict-mode creep -- out of scope. |
| **`py.typed`** | An empty marker file inside a package indicating its source ships inline type annotations. Absence forces stubs. |
| **execution environment** | A `[[tool.pyright.executionEnvironments]]` block scoping rule overrides to a path. **The mechanism for `config-relax`.** |
| **`stubPath`** | `[tool.pyright].stubPath` -- directory pyright searches for local `.pyi` files. Required to use `stub-fix`. |
| **`reveal_type(x)`** | Diagnostic call that prints x's inferred type. Debug-only; never commit. |
| **`cast(T, x)`** | `typing.cast` -- tells pyright "treat x as T" without runtime check. Acceptable inside `mechanical`; suspect when the underlying finding is really a `real-bug`. |
| **`assert isinstance(x, T)`** | Narrowing via runtime check. Preferred over `cast` when x's type is genuinely uncertain at runtime. |
| **`exclude`** | `[tool.pyright].exclude = [...]` -- removes paths from type-checking. **Forbidden** mechanism (`config-exclude`). |

---

## 6. Triage Decision Tree

A newcomer with a fresh pyright finding follows this tree to assign exactly one disposition.

```
1. Does pyright complain about a third-party import or attribute it cannot see?
   YES -> Can a local stub or maintained stub package fix it?
            YES -> stub-fix.
            NO  -> stub-ignore.        (scoped # type: ignore[import] + reason)
   NO  -> continue.

2. Is there a code path -- reachable from a public entry, CLI, slash command,
   MCP tool, or executed test -- that would raise at runtime, OR does the
   finding violate a documented invariant?
   YES -> real-bug.                    (logic fix; verification: pyright+targeted)
   NO  -> continue.

3. Can the truth be made visible by adding annotation / narrowing / cast / a
   scoped # type: ignore[rule_id] with reason, without restructuring code?
   YES -> mechanical.
   NO  -> continue.

4. Is the finding in test code, AND can a per-rule severity downgrade in an
   executionEnvironments block resolve it cleanly?
   YES -> config-relax.                (test region only; never non-test)
   NO  -> continue.

5. The finding cannot be resolved within scope.
   -> dropped, with notes prefix:
        - refactor-required:<tracker>     (pyright right; needs restructuring)
        - false-positive:<reason>         (pyright wrong; no scoped fix fits)
        - duplicate:<canonical_error_id>
        - wontfix:<reason>
```

Forbidden outcomes (Skeptic flags any row matching these):
- `disposition = config-exclude` (I8: forbidden in both regions).
- `disposition = config-relax` AND `region = non-test`.
- `disposition = mechanical` paired with a bare `# type: ignore` (no rule_id) -- I6.
- `disposition = mechanical` AND `lane = bugfix` (I2), or `disposition = real-bug` AND `lane = sweep` (I2).

---

## 7. Synonym Audit

Terms below have appeared (or will likely appear) and MUST be normalized.

| Do not use | Use instead | Reason |
|---|---|---|
| "type-truth fix" / "annotation fix" / "typing fix" / "narrowing fix" | **`mechanical`** disposition | One umbrella per composability. Sub-mechanism recorded in `proposed_fix`. |
| "latent issue" | **`mechanical`** disposition | Folded by composability; reachability commentary goes in `notes`. |
| "refactor-required error" | **`dropped`** with `notes: refactor-required:<tracker>` | Composability folds into `dropped`; prefix preserves filterability. |
| "test-relaxed" / "test rule relaxation" / "relaxed ruleset" | **`config-relax`** | Disposition name is canonical. |
| "test exclusion" / "exclude tests" / "skip tests in pyright" | **`config-exclude`** -- and remember it is FORBIDDEN | The user's locked answer rejected this mechanism. Naming it precisely lets us reject it precisely. |
| "test typing exclusion" (Vision draft) | **`config-relax`** if you mean per-rule downgrade; NEVER as a synonym for the rejected `exclude` mechanism | Vision draft phrasing was ambiguous; reconciliation chose `config-relax`. |
| "ignore" / "suppress" (bare) | **principled suppression** (with rule_id) -- **band-aid suppression** is forbidden | Always specify rule_id. |
| "genuine bug" / "logic error" / "real error" | **`real-bug`** disposition | One name. |
| "false positive" | **`stub-ignore`** if it's a stub gap; **`dropped`** with `notes: false-positive:` if no scoped fix fits | The phrase hid which case applied. |
| "fix later" / "TODO type" | **`dropped`** with `notes: refactor-required:<tracker>` | Forces a tracking handle. |
| "pyright finding" / "pyright complaint" / "type error" / "type-check error" | **finding** as the generic noun; otherwise the disposition name | Generic noun OK pre-triage. |

---

## 8. Newcomer Simulation

Open questions a newcomer might still ask, and where this doc answers them:

| Newcomer question | Answer location |
|---|---|
| "What is a pyright finding?" | s 4.1 |
| "What dispositions can a finding have?" | s 2.1, s 2.2 |
| "When is `# type: ignore` allowed?" | s 3 (principled vs band-aid), s 6 (forbidden outcomes) |
| "What's the difference between `config-relax` and `config-exclude`?" | s 2.1, s 2.2, s 4.3 |
| "Why is `config-exclude` forbidden?" | s 2.2 (user's locked answer); composability I8 |
| "Are we using strict mode?" | s 3 (strict-mode creep, out of scope) |
| "What happens to errors in tests/?" | s 2.1 -- `config-relax` for mechanical-shaped ones, `real-bug` for actual defects, `mechanical` for everything fixable inline |
| "What's `executionEnvironments`?" | s 5 |
| "Where do I record an error I'm deferring?" | s 2.3 (`dropped` with `refactor-required:` prefix) |
| "What is `stubPath` and when do I need it?" | s 5 -- needed for any `stub-fix` row |

Remaining newcomer blockers (escalated):
1. **`stubs/` directory + `stubPath` config** -- not yet present in `pyproject.toml`. Needed before any `stub-fix` row can be implemented. Composability/Coordinator decision.

---

## 9. Cross-References

Other artifacts reference this file rather than redefining:

- `STATUS.md` "Domain terms" section -> replace with: *See `specification/terminology.md` and `specification/composability.md`.*
- `specification/SPECIFICATION.md` -> use disposition names verbatim from s 2; cite section numbers.
- `specification/composability.md` -> canonical for disposition schema; this file aligns to it.
- Implementer / Skeptic prompts -> link to s 6 (Triage Decision Tree) and s 7 (Synonym Audit).

---

## 10. Change Control

Any new term, renamed term, or definition change requires:
1. A note from the Composability lead approving the change.
2. An update to this file (the canonical home for naming).
3. A grep across artifacts to update any stale usages.

Terminology guardian (this agent) owns step 3. The disposition vocabulary in s 2 is locked to `composability.md`; changes there propagate here.
