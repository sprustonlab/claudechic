"""Pre-test for SPEC §6.2 / cherry-pick 5700ef5.

Per the Leadership-required guard against L10.c risk ("accept ours" silently
dropping the new auto default during the manual 5700ef5 config.py conflict
resolution): assert that the default permission mode is ``"auto"`` for both
new-install and existing-install setdefault paths.

This test is added BEFORE the cherry-pick batch lands and is expected to fail
on the pre-cherry-pick tree (where the default is still ``"default"``); after
``5700ef5`` is cherry-picked it should pass. If the test still fails post-pick,
the manual conflict resolution dropped the change — STOP and re-resolve.
"""

from __future__ import annotations

from pathlib import Path


def test_default_permission_mode_is_auto_in_existing_install_branch() -> None:
    """The setdefault() for default_permission_mode must default to 'auto'."""
    source = (Path(__file__).parent.parent / "claudechic" / "config.py").read_text()
    assert 'config.setdefault("default_permission_mode", "auto")' in source, (
        "Existing-install branch must setdefault default_permission_mode to 'auto' "
        "(SPEC §6.2 / cherry-pick 5700ef5). If this fails after the cherry-pick, "
        "the manual config.py conflict resolution dropped the new default."
    )


def test_default_permission_mode_is_auto_in_new_install_branch() -> None:
    """The new-install initialization dict must set default_permission_mode='auto'."""
    source = (Path(__file__).parent.parent / "claudechic" / "config.py").read_text()
    assert '"default_permission_mode": "auto"' in source, (
        "New-install initialization dict must set default_permission_mode='auto' "
        "(SPEC §6.2 / cherry-pick 5700ef5). If this fails after the cherry-pick, "
        "the manual config.py conflict resolution dropped the new default."
    )
