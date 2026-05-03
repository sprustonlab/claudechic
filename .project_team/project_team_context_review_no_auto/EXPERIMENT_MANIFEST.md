# Experiment manifest -- no-auto-mode comparison run

Truncated copies of the original JSONLs and chicsession, cut just after the four Leadership leads delivered their reports and BEFORE the coordinator's `advance_phase` call to specification.

## Source -> destination

| Agent | Source session | Destination session | Cut at line |
|---|---|---|---:|
| claudechic     | 7cda1c83-374d-4415-b285-f1d797afce52 | 50e1972e-1f02-45ce-93b6-1f90af820924 | 166 |
| composability  | 1d5568eb-c51d-40ea-af7d-8d075e362a10 | c48ba5da-b0c9-42c3-879d-a1fb41ba57dd | 61 |
| terminology    | 73554ac4-80a1-4238-b719-2488ab14431f | 96fa1a8a-b3b4-433e-9b3d-0eb259c3113b | 68 |
| skeptic        | 93cfa471-ea70-4ea1-be31-195e2fd3b654 | 47f65a48-0bb4-4ce8-9f9d-cca335a9d75d | 79 |
| user_alignment | 0bd46d13-2a0f-4d82-9385-f51ceb526bb5 | b0849c08-50ce-4222-93dc-c863748447a8 | 31 |

## Chicsession

`/groups/spruston/home/moharb/claudechic/.chicsessions/Improve_docs_injection_no_auto.json`

## Artifact dir

`/groups/spruston/home/moharb/claudechic/.project_team/project_team_context_review_no_auto/`

Contents (leadership-phase only):
- STATUS.md (trimmed to leadership-phase state)
- userprompt.md
- leadership_findings.md

## How to run

1. Start claudechic.
2. `/resume` and pick the `Improve_docs_injection_no_auto` chicsession.
3. Confirm Auto mode is OFF (Shift+Tab cycles permission modes; default / acceptEdits / plan / bypassPermissions are the non-auto options).
4. Continue from where the original cut. The coordinator should be in leadership phase with all 4 lead reports delivered, about to advance to specification.

## Note on JSONL sessionId rewrites

Inside each new JSONL, every event's `sessionId` field has been rewritten from the old to the new UUID. Other UUIDs (parentUuid, uuid, tool_use_id) were NOT rewritten -- those are event-internal references and do not need updating.
