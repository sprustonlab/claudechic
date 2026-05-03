# prompt_audit/test_engineer.md

**Role:** `test_engineer` (writes and maintains tests; "Generalprobe" standard).
**Source:** `test_engineer/identity.md` (102 lines). **No phase markdown today.**
**Phase coverage gap:** test_engineer has no `<phase>.md` files; misclassified as standing-by everywhere under the v1 static predicate. v1 fix: add testing-specification.md and testing-implementation.md.

Glossary: `GLOSSARY.md`. Authority contract: skeptic R3.

---

## 1. What the role actually needs

TestEngineer writes tests honoring the no-mock / no-skip / public-API / real-infrastructure contract. To do its job it must:

- Hold the testing principles (no-mock, no-skip, public-API, real-infra).
- Hold the testing strategy + output format.
- Hold the tooling reference.
- Hold the interaction map.
- Hold the Rules.
- Receive phase-specific operating instructions for testing-* phases (currently absent).
- Receive constraints (especially `global:no_bare_pytest`, `global:pytest_needs_timeout`).
- Receive environment knowledge.

## 2. What's currently in identity.md (categorized)

| Category | Lines | Content |
|---|---|---|
| **Role-defining authority** | L1-L13 | Role banner |
| **Role-defining authority** | L15-L21 | "First step: read the testing standard" |
| **Role-defining authority** | L23-L31 | Default testing principles (no-mock / no-skip / public-API / real-infra) |
| **Role-defining authority** | L33-L60 | Testing strategy + output format |
| **Role-defining authority** | L62-L73 | Tooling |
| **Cross-role coordination** | L75-L82 | Interactions |
| **claudechic-environment boilerplate** | L84-L93 | `## Communication` block |
| **Role-defining authority** | L95-L100 | Rules |
| **Role-defining authority** | L101-L102 (Rule #6) | Pytest policy. **Per user clarification 2026-05-02: stays in identity prose; do NOT reference constraints segment.** |

## 3. Load-bearing (R3) -- preserve verbatim

| Line | Quote |
|---|---|
| L25 | *"No mocking -- tests run against real infrastructure."* |
| L26 | *"No skipping ... Do not use pytest.skip(), xfail, or importorskip."* |
| L27 | *"Public API only ... opaque handles."* |
| L29 | *"Real infrastructure -- A test is a production run with assertions."* |
| L100 | *"Don't test mocks -- Test real behavior."* |

These five together = the team's testing contract (the "Generalprobe standard" referenced by `coordinator/testing_vision.md`). Skeptic and UserAlignment lean on them.

## 4. Could move to environment segment

**L84-L93 (`## Communication` block)** -- identical boilerplate. Move to env segment.

## 5. Could move to constraints segment

**Nothing.** Per user clarification 2026-05-02 (verbatim): *"don't reference something we can gate with settings"*. The constraints segment is configurable via `constraints_segment.scope.sites` (#28); an identity reference to it is fragile. Pytest-policy prose at L101-L102 stays unchanged. Asymmetric on purpose: comm-block is recoverable boilerplate; pytest is bad-thing-prevention (must remain in-prose).

## 6. Could move to manifest YAML / shared reference

None.

## 7. Per-phase needs

| phase | file (today) | proposed file (v1) | role status | notes |
|---|---|---|---|---|
| vision | -- | -- | (not spawned) | -- |
| setup | -- | -- | (not spawned) | -- |
| leadership | -- | -- | (not spawned) | -- |
| specification | -- | -- | (not spawned) | -- |
| implementation | -- | -- | (not spawned) | -- |
| testing-vision | -- | -- | active per gating matrix | optional v2 add |
| testing-specification | **MISSING** | **add `testing-specification.md`** | active | v1 add |
| testing-implementation | **MISSING** | **add `testing-implementation.md`** | active | v1 add |
| documentation | -- | -- | (not spawned) | -- |
| signoff | -- | -- | (not spawned) | -- |

**Phase-md gap fix (v1):** add `testing-specification.md` and `testing-implementation.md`. Without these, test_engineer is classified standing-by in its **active** phases under the v1 static predicate -- which would mean identity is correctly suppressed at T3/T4 (per #27) but the phase segment renders empty when test_engineer most needs phase guidance. The fix is to author the phase mds.

**Phase-md content (proposed):** mirrors implementer/testing.md and skeptic/testing-*.md patterns -- tight ops steps for the phase, pointer to the testing standard.

## 8. Proposed identity.md edits

**v1 (this run):**

1. **Delete L84-L93** -- `## Communication` block. Replaced by env segment.
2. **Pytest-policy rule (L101-L102): NO CHANGE.** Per user clarification 2026-05-02, stays in-prose. Constraints reference rolled back.

**Net change:** identity.md goes from 102 lines to ~91 lines (comm-block hoist only). R3 statements (L25-L29, L100, **L101-L102**) untouched.

**v1 phase-md adds:**

3. New file: `test_engineer/testing-specification.md` (TBD content; coordinator/test_engineer to author during Implementation).
4. New file: `test_engineer/testing-implementation.md` (TBD content).

## 9. Per-(time, place) cell map

| Time | identity | phase | constraints | environment |
|---|---|---|---|---|
| T1 spawn | fires | fires (after phase-md adds) | fires | fires |
| T2 activation | n/a | n/a | n/a | n/a |
| T3 phase-advance.main | n/a | n/a | n/a | n/a |
| T4 broadcast (active phase) | suppress (#27) | fires (after phase-md adds) | **fires (F1 floor)** | fires |
| T4 broadcast (standing-by) | suppress | empty | **fires (F1 floor)** | fires |
| T5 post-compact | re-fires | re-fires | re-fires | re-fires |

## 10. Open questions

- **Phase-md content:** coordinator + test_engineer to author. **Marked: needs role-agent review during Implementation.**
- **testing-vision:** active per gating matrix (`A**`). v2 add `testing-vision.md`?

## 11. Review status

- **Self-review:** **needs role-agent review during Implementation.** test_engineer is not spawned during Specification.

---

*Author: role-axis. Specification phase. Marked: needs role-agent review during Implementation.*
