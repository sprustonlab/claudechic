# UserAlignment -- Specification Phase Findings

> Historical / rationale document. Canonical naming lives in `specification/terminology.md`; this file uses some pre-lockdown draft terms (e.g. `un-hide` prose, `in-memory only`, `NV2`, `A1`/`A2` in resolution context). Its operational findings were absorbed into `specification/SPECIFICATION.md` and userprompt.md v5.

**Reviewer:** UserAlignment
**Sources of truth (in priority order):**
1. `userprompt.md` v4 (approved 2026-05-03).
2. GitHub issues #18, #19, #20.
3. User decisions captured post-v4 in `uidesigner_design_v4.md` (v4.1, v4.2 feedback rounds) and locked into `STATUS.md`.

This document checks the locked Leadership decisions and UIDesigner v4.2 design
against userprompt.md v4. Findings are graded:

- **MISALIGNMENT** -- Locked decision contradicts userprompt.md text. Must be
  resolved before Specification finalizes (either userprompt updated to v5
  with explicit user approval, or decision revised).
- **PROCESS** -- Decision is consistent with user intent but recorded only in
  derivative artifacts (STATUS, UIDesigner v4.x), not in userprompt. Source
  of truth is fragmenting.
- **PENDING REPRO** -- Decision is contingent on Specification investigation
  that has not happened yet.
- **OK** -- Aligned and recorded.

---

## MISALIGNMENT-1 -- "directories carry no stored state" vs `hide_prefixes`

**userprompt.md v4 line 19 (verbatim):**
> "Directory hide is a simple bulk action over descendants; directories carry
> no stored state."

**Locked Leadership decision (STATUS.md line 17):**
> "**#20 hide**: three-set state, app-scoped `dict[cwd, HideState]` where
> `HideState = (hide_files, hide_prefixes, force_visible)`."

These are contradictory. `hide_prefixes` IS stored directory state. The
userprompt explicitly forbids it.

**UIDesigner v4.1 captures the user re-authorization:**
> "User decisions applied: NV2 directory hide: PREFIX semantics confirmed
> (session `set[str]` of hidden prefixes; new files under a hidden prefix
> inherit hidden)."

So the user approved prefix semantics during the UIDesigner feedback round,
which **overrides userprompt.md v4 on this point**, but userprompt.md was not
updated to a v5 to reflect it.

**Required action:** Bump userprompt.md to v5 and replace the line "directories
carry no stored state" with the actual approved model (per-session
`hide_prefixes` set + new descendants inherit hidden + `force_visible` override
axis). Without this, downstream phases reading userprompt.md as the source of
truth will see an instruction that contradicts the implementation.

---

## MISALIGNMENT-2 -- "new files start visible" vs prefix-inheritance

**userprompt.md v4 line 17 (verbatim):**
> "Within a session, hide state persists across `/diff` re-runs in the same
> repo (hidden file reappearing in a later diff returns hidden; new files
> start visible)."

**STATUS.md line 21:**
> "New descendants of hidden prefixes inherit hidden unless force-visible."

These contradict for the case of a new file that lands under a previously
hidden directory prefix. userprompt says "new files start visible"
unconditionally; the locked model says "new descendants of hidden prefixes
inherit hidden."

This is the same user redirect as MISALIGNMENT-1 (prefix semantics) -- but the
userprompt's "new files start visible" line was not updated to carve out the
prefix case.

**Required action:** In the v5 userprompt update, rewrite this clause as: "New
files start visible UNLESS their path is under a hidden directory prefix, in
which case they inherit hidden (and may be individually un-hidden via the
`force_visible` override)."

---

## MISALIGNMENT-3 -- `force_visible` axis is not in userprompt at all

The `force_visible` set is part of the locked HideState tuple. userprompt.md
v4 does not mention it. UIDesigner v4.2 surfaced it as Option A2 vs A1
("remove the prefix entirely"). The choice between A1 and A2 is listed as an
open question in UIDesigner v4.2; STATUS.md line 17 shows A2 is the locked
choice (force_visible is in the tuple), but the v4.2 doc itself still flags
A1-vs-A2 as outstanding.

**Two possible states:**
- (a) User has authorized A2 (force_visible) and the v4.2 "open question" is
  stale. Confirm.
- (b) User has not yet picked; STATUS.md prematurely locks A2.

**Required action:** Specification user-checkpoint must explicitly resolve A1
vs A2 with the user, then update both userprompt.md (v5) and the v4.2 doc to
remove the dead open question.

---

## PROCESS-1 -- Source of truth is fragmenting

User decisions made AFTER userprompt.md v4 was written:
- Sort default = `directory` (UIDesigner v4.1).
- Keybindings `s f d r` (UIDesigner v4.1, confirmed v4.2).
- App-scoped HideStore, not DiffScreen-scoped (UIDesigner v4.1).
- Repo key = raw cwd, no symlink resolution (v4.2).
- `d` never prompts for confirmation (v4.2).
- Sidebar UX = in-place greyed entries, NOT collapsed `[+] Hidden (N)` group
  (v4.2 retracted v4.1).
- `hidden: N` DiffHeader badge clickable -> un-hide all (v4.2).
- Badge flash on toggle DROPPED (v4.2).
- Below-60-cols behavior = aggressive truncate, no row stacking (v4.2).
- Prefix semantics on directory hide (v4.1).

These are all user-authorized, but they live ONLY in the UIDesigner doc and in
STATUS.md. userprompt.md is the document the team treats as source of truth
("userprompt.md is the source of truth -- not your interpretation"). Future
agents reading userprompt.md will see v4, not v4.x decisions.

**Required action:** Bump userprompt.md to v5 capturing all of the above with
brief one-liners. The v5 should be small (these decisions are point edits, not
a redirect).

---

## PENDING-REPRO-1 -- #18 design committed before reproduction

**userprompt.md v4 line 9:**
> "Specification phase MUST first reproduce the symptom and identify the actual
> widget; Leadership flagged that no widget today renders such a string -- this
> may be a missing-feature ('show the originating command') rather than a logic
> bug."

**Leadership locked decision (STATUS.md line 15):**
> "**#18 source command**: new `DiffHeader` widget at top of DiffScreen;
> renders `$ git diff <target>` + `sort: <mode>` + `hidden: N` (latter
> clickable -> un-hide all). Specification phase reproduces the bug first;
> #18 is most likely missing-feature, not wiring bug."

The decision is to build a NEW DiffHeader widget. The userprompt mandates
reproduction FIRST, with the implicit option that reproduction might find an
existing widget that should be fixed in place (a wiring bug, minimum-scope
fix). Leadership has pre-committed to the new-widget path.

**This is not necessarily a misalignment** -- the userprompt allows the
new-widget interpretation -- but it pre-empts the investigation the userprompt
required. If reproduction reveals an existing widget already attempting to
render a command, the locked DiffHeader design is over-scoped.

**Required action:** Specification phase MUST do the reproduction before
ratifying the DiffHeader-as-new-widget design. If reproduction finds an
existing widget, escalate to user before proceeding.

This is a continuation of my prior-round Flag A.

---

## PROCESS-2 -- Repo key edge case not surfaced to user

UIDesigner v4.2 user decision #4: "Repo key: raw cwd as DiffScreen receives
it; no symlink/git-toplevel resolution."

This is a real trade-off: a user who launches claudechic from a symlinked path
(e.g., `~/work/claudechic` -> `/groups/.../claudechic`) and then from the real
path, in the same session, will see two separate hide states. Same for users
who `cd` into a subdirectory of the repo and re-launch.

The userprompt-v4 invariant "no cross-repo leakage" is preserved (raw cwd is
strictly more conservative), but "per-repo within session" is weaker than the
user may expect: it is "per-launch-cwd within session."

**Status:** STATUS.md line 17 notes "revisit if real-world breakage." User
appears to have accepted this. **Not a blocker**, but should be a one-line
note in the v5 userprompt so the trade-off is explicit.

---

## OK items (verified aligned)

1. **Hide state is in-memory only, resets on claudechic exit.** App-scoped
   store satisfies this; closing DiffScreen within a session preserves hides.
   Aligned with userprompt v4 line 11 + line 17.
2. **No "reviewed" semantics.** No tri-state, no content_sha, no rename
   migration. Aligned with userprompt v4 line 19.
3. **Sort mode persisted per-repo in `<repo>/.claudechic/`.** Aligned with
   userprompt v4 line 16.
4. **Branch = develop.** Aligned with userprompt v4 line 20.
5. **Sort change preserves in-progress hunk comments via in-place DOM
   reorder.** This invariant lives in userprompt v4 line 45 ("sort change
   preserves in-progress hunk comments (in-place DOM reorder, not rebuild)")
   and is grounded in existing `HunkWidget.has-comment` functionality. My
   prior-round Flag B is RESOLVED -- hunk comments are an existing feature,
   not scope creep.
6. **Keep name `DiffScreen`, no rename.** Aligned (userprompt does not request
   a rename; Leadership confirmed no refactor).
7. **Three-issue scope, no creep.** Aligned with userprompt v4 line 7-11.
8. **Failure modes from userprompt v4 (sort losing comments, hide state
   surviving exit, cross-repo leakage, cosmetic-only #18, keybinding clashes)
   are all addressed in the locked design or risk register.** Aligned.

---

## Domain term check

userprompt v4 canonical terms:
- `DiffScreen` -- preserved.
- `source command` -- preserved (used in DiffHeader spec).
- `sort mode` (alphabetical | directory) -- preserved.
- `hide state` -- preserved.
- `directory hide action` -- present, but the implementation introduces
  `hide_prefixes` (a stored set) which contradicts userprompt's "directories
  carry no stored state" framing. See MISALIGNMENT-1.

No term has been silently renamed or repurposed.

---

## Wording-change check

User said "checkmark" in issue #20; userprompt v4 (per v3 redirect) drops the
checkmark concept entirely. UIDesigner v4.2 in-place-greyed design uses a `.`
dot glyph and strike-through, not a checkmark. **This is user-authorized** by
the v3/v4 redirect ("Simplified scope: this is a plain hide/show, NOT a
'reviewed' tracker."). Recorded; not a misalignment.

User said "show/hide checkmark toggle" in issue #20; UIDesigner v4.2 uses
`hidden: N` clickable badge plus `f`/`d`/`r` keybindings instead of a single
toggle. The "toggle" framing is not literally preserved, but the user
authorized this in v4.1/v4.2. Recorded; not a misalignment.

---

## Recommendation to Coordinator

**Specification cannot finalize until:**
1. userprompt.md is bumped to v5 with the prefix-semantics, force_visible,
   sort-default, keybinding, sidebar-UX, and clickable-badge decisions
   captured. Without this, MISALIGNMENT-1 and -2 are live contradictions
   between source-of-truth and locked design.
2. A1 vs A2 (force_visible) is explicitly confirmed with the user at the
   Specification user-checkpoint.
3. #18 reproduction is performed (PENDING-REPRO-1) before ratifying the
   DiffHeader-as-new-widget design.

**Process recommendation:** establish a rule that any user decision captured
in a derivative artifact (UIDesigner doc, STATUS.md) must be back-propagated
into userprompt.md before the next phase advances. Otherwise we will keep
finding contradictions.

**No findings require overriding Skeptic, escalating Vision, or rolling back
any locked decision -- the locked decisions appear consistent with the user's
actual intent, just out of sync with the userprompt document.**
