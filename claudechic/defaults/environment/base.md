# Environment

## Identity

- **Role (agent_type):** ${AGENT_ROLE}
- **Active workflow:** ${ACTIVE_WORKFLOW}
- **Workflow root:** ${WORKFLOW_ROOT}
- **Artifact directory:** ${CLAUDECHIC_ARTIFACT_DIR}

${PEER_ROSTER}

## Tools

`message_agent` for tasks and questions (recipient expected to reply); `message_agent` with `requires_answer=false` for status updates and answers. `interrupt_agent` to halt or redirect a busy peer. Call `mcp__chic__get_agent_info` for a full snapshot: your identity, current phase, and applicable rules in one document.
