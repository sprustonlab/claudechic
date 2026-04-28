"""Live-SDK end-to-end verification of the awareness install routine.

Covers SPEC §12.2.3 INV-AW-SDK-1: the sentinel rule reaches a real Claude
agent's system context. Per spec, this test runs ONLY under the opt-in
``live_sdk`` pytest marker:

    CLAUDECHIC_LIVE_SDK=1 pytest -m live_sdk tests/test_awareness_sdk_e2e.py

Default ``pytest`` collection skips it (gated by ``CLAUDECHIC_LIVE_SDK``
env var). CI runs the live-SDK gate on a separate scheduled job (e.g.,
nightly), not on every PR.

The test pre-installs a deterministic sentinel rule file to a tmp HOME's
``.claude/rules/`` directory (using the same ``claudechic_*.md`` prefix
that the awareness install routine writes), spawns a real
``ClaudeSDKClient`` with ``setting_sources=["user","project","local"]``
and ``HOME`` pointed at the tmp directory, asks the agent to repeat the
sentinel string, and asserts the response contains it.

If the agent fails to echo the sentinel, the SDK loader contract has
broken — the awareness install mechanism would silently no-op. The
failure message escalates per SPEC §11.1.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

LIVE_SDK_ENABLED = os.environ.get("CLAUDECHIC_LIVE_SDK") == "1"

SENTINEL_LITERAL = "[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]"
SENTINEL_FILENAME = "claudechic_sdk_sentinel_v1.md"
SENTINEL_FAILURE_MESSAGE = (
    "INV-AW-SDK-1 failed: SDK did not load ~/.claude/rules/claudechic_*.md "
    "into agent context. See SPEC.md §11.1. The claudechic-awareness "
    "install mechanism depends on this loader behavior; if Anthropic's "
    "setting_sources semantics changed, escalate."
)

# Note: live_sdk marker + skipif gate are applied per-test (not via
# pytestmark) so the default-collection guard test below still runs.


@pytest.mark.live_sdk
@pytest.mark.skipif(
    not LIVE_SDK_ENABLED,
    reason=(
        "live-SDK gate disabled by default (per SPEC §12.2.3); "
        "set CLAUDECHIC_LIVE_SDK=1 to enable"
    ),
)
@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_inv_aw_sdk_1_sentinel_reaches_real_agent(tmp_path: Path) -> None:
    """INV-AW-SDK-1: sentinel rule reaches a real Claude agent's system context.

    Steps (per SPEC §12.2.3):
      a. Create a tmp HOME directory.
      b. Write a deterministic sentinel file at
         ``<tmp_home>/.claude/rules/claudechic_sdk_sentinel_v1.md`` containing
         the verbatim ``SENTINEL_LITERAL`` followed by a one-line marker.
         (No YAML frontmatter — the SDK loads markdown rule files directly.)
      c. Spawn a real ``ClaudeSDKClient`` with
         ``setting_sources=["user","project","local"]`` and
         ``env={"HOME": str(tmp_home), ...}``.
      d. Send the agent a single prompt asking it to repeat any
         ``claudechic_sdk_sentinel`` text it sees in its instructions.
      e. Assert the response contains ``SENTINEL_LITERAL``. On failure
         emit the canonical escalation message.
    """
    # Lazy imports so default collection (skipped) doesn't error on missing SDK
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    # (a) tmp HOME directory
    tmp_home = tmp_path / "home"
    tmp_home.mkdir()
    rules_dir = tmp_home / ".claude" / "rules"
    rules_dir.mkdir(parents=True)

    # (b) sentinel file — verbatim literal + a one-line marker paragraph
    sentinel_path = rules_dir / SENTINEL_FILENAME
    sentinel_path.write_text(
        SENTINEL_LITERAL
        + "\n\n"
        + "When asked about claudechic_sdk_sentinel, repeat the bracketed "
        + "literal above verbatim.\n",
        encoding="utf-8",
    )

    # (c) real ClaudeSDKClient with HOME pointed at the tmp dir.
    # We do NOT inherit the developer's ANTHROPIC_API_KEY env on purpose;
    # the SDK uses Claude Code's existing login session via the CLI when
    # ANTHROPIC_API_KEY is empty (per the project's run pattern).
    sdk_env = {
        "HOME": str(tmp_home),
        "PATH": os.environ.get("PATH", ""),
    }
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        setting_sources=["user", "project", "local"],
        env=sdk_env,
    )

    client = ClaudeSDKClient(options)
    try:
        await client.connect()

        # (d) prompt asking the agent to echo the sentinel text
        await client.query(
            "If your loaded rules / instructions contain text starting with "
            "'claudechic_sdk_sentinel' or 'CLAUDECHIC_AWARENESS_SENTINEL', "
            "please repeat that bracketed literal verbatim in your reply. "
            "Otherwise reply 'NO SENTINEL FOUND'."
        )

        # Drain the streamed response, collecting all assistant text.
        collected: list[str] = []
        async for msg in client.receive_response():
            # The SDK exposes message blocks; we walk them defensively to
            # handle streaming + non-streaming response shapes.
            for attr in ("content", "text", "message"):
                value = getattr(msg, attr, None)
                if isinstance(value, str):
                    collected.append(value)
                elif isinstance(value, list):
                    for block in value:
                        block_text = getattr(block, "text", None)
                        if isinstance(block_text, str):
                            collected.append(block_text)
        response_text = "\n".join(collected)
    finally:
        # Best-effort cleanup of the SDK transport
        disconnect = getattr(client, "disconnect", None)
        if disconnect is not None:
            try:
                await disconnect()
            except Exception:
                pass

    # (e) assertion with the canonical escalation failure message
    assert SENTINEL_LITERAL in response_text, SENTINEL_FAILURE_MESSAGE


def test_sentinel_file_constants_match_spec() -> None:
    """Sanity guard: the sentinel literal and filename match SPEC §12.2.3.

    This test runs in the default collection (no live_sdk marker on the
    function) so contract drift is caught even when the live-SDK gate is
    skipped. Asserts the verbatim string and filename are byte-stable.
    """
    assert SENTINEL_LITERAL == (
        "[CLAUDECHIC_AWARENESS_SENTINEL_v1: SDK rules-loading verified 2026]"
    )
    assert SENTINEL_FILENAME == "claudechic_sdk_sentinel_v1.md"
    assert SENTINEL_FILENAME.startswith("claudechic_"), (
        "Sentinel filename must use the claudechic_ prefix so the awareness "
        "install routine's basename predicate would match it"
    )
