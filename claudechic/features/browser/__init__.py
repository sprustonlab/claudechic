"""Gated browser control feature (Playwright-Chromium backend).

Lets an agent drive a dedicated Chromium browser: navigate, screenshot,
click, type, scroll. Hard-gated twice:

1. Tools are NOT registered on the chic MCP server unless
   ``experimental.browser: true`` in ``~/.claudechic/config.yaml``
   (off by default; requires a claudechic restart).
2. The package-tier ``global:browser_control`` deny guardrail rule fires
   on every call -- use requires request_override (per call) or the user
   toggling the rule off in the Guards sidebar (per session).

One shared browser + page per app process (v1 limitation). Install the
backend with ``pip install "claudechic[browser]"`` then
``playwright install chromium``.
"""

from claudechic.features.browser.session import shutdown_browser
from claudechic.features.browser.tools import get_browser_tools


def browser_enabled() -> bool:
    """True when ``experimental.browser`` is enabled in user config."""
    from claudechic.config import CONFIG

    return bool(CONFIG.get("experimental", {}).get("browser", False))


__all__ = [
    "browser_enabled",
    "get_browser_tools",
    "shutdown_browser",
]
