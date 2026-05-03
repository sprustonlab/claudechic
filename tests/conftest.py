"""Shared test fixtures."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from claudechic.features.roborev.models import ReviewJob
from claudechic.widgets.layout.reviews import ReviewItem


async def empty_async_gen():
    """Empty async generator for mocking receive_response."""
    return
    yield  # unreachable - makes this an async generator


@pytest.fixture(autouse=True)
def _suppress_welcome_screen(monkeypatch):
    """Prevent welcome screen from showing during tests."""
    monkeypatch.setattr("claudechic.onboarding.check_onboarding", lambda *a, **kw: None)


@pytest.fixture
def real_agent_with_mock_sdk(tmp_path):
    """Create a real Agent with a mock ClaudeSDKClient.

    Returns a (agent, mock_client) tuple. The agent is connected with a
    mock SDK that supports connect/interrupt/query/receive_response as
    minimal stubs. This lets integration tests exercise real Agent state
    machine logic without needing a live SDK connection.
    """
    from claudechic.agent import Agent

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.interrupt = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = lambda: empty_async_gen()
    mock_client.get_server_info = AsyncMock(return_value={"commands": [], "models": []})
    mock_client.set_permission_mode = AsyncMock()
    mock_client._transport = None

    agent = Agent(name="test-agent", cwd=tmp_path)
    # Inject mock client directly (bypass connect() which needs real SDK)
    agent.client = mock_client
    agent.session_id = "mock-session-001"

    return agent, mock_client


async def wait_for_workers(app):
    """Wait for all workers to complete."""
    await app.workers.wait_for_complete()


async def submit_command(app, pilot, command: str):
    """Submit a command, handling autocomplete properly.

    When setting input text directly, autocomplete may activate.
    This helper hides it before submitting to ensure the command goes through.
    """
    from claudechic.widgets import ChatInput

    input_widget = app.query_one("#input", ChatInput)
    input_widget.text = command
    await pilot.pause()

    # Hide autocomplete if it's showing (triggered by / or @)
    if input_widget._autocomplete and input_widget._autocomplete.display:
        input_widget._autocomplete.action_hide()
        await pilot.pause()

    input_widget.action_submit()
    await pilot.pause()


@pytest.fixture
def mock_sdk():
    """Patch SDK to not actually connect.

    Patches both app.py and agent.py imports since agents create their own clients.
    Also patches FileIndex to avoid subprocess transport leaks during test cleanup.
    Disables analytics to avoid httpx connection leaks.
    """
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.interrupt = AsyncMock()
    mock_client.get_server_info = AsyncMock(return_value={"commands": [], "models": []})
    mock_client.set_permission_mode = AsyncMock()
    mock_client.receive_response = lambda: empty_async_gen()
    mock_client._transport = None  # For get_claude_pid_from_client

    # Mock FileIndex to avoid git subprocess transport leaks
    # The subprocess transports try to close after the event loop is closed
    from claudechic.file_index import FileIndex

    mock_file_index = MagicMock(spec=FileIndex)
    mock_file_index.refresh = AsyncMock()
    mock_file_index.files = []

    # Use ExitStack to avoid deep nesting
    with ExitStack() as stack:
        # Clear local config first so tests get fresh-install defaults
        # (prevents developer's ~/.claudechic/config.yaml from leaking in).
        # Must come before the analytics patch since they share the same dict.
        stack.enter_context(
            patch.dict(
                "claudechic.agent_manager.CONFIG",
                {"default_permission_mode": "auto"},
                clear=True,
            )
        )
        # Disable analytics to avoid httpx AsyncClient connection leaks
        stack.enter_context(
            patch.dict("claudechic.analytics.CONFIG", {"analytics": {"enabled": False}})
        )
        stack.enter_context(
            patch("claudechic.app.ClaudeSDKClient", return_value=mock_client)
        )
        stack.enter_context(
            patch("claudechic.agent.ClaudeSDKClient", return_value=mock_client)
        )
        stack.enter_context(
            patch("claudechic.agent.FileIndex", return_value=mock_file_index)
        )
        stack.enter_context(
            patch("claudechic.app.FileIndex", return_value=mock_file_index)
        )
        yield mock_client


@pytest.fixture
def mock_roborev_output():
    """Mock roborev CLI subprocess output.

    Returns a callable that patches is_roborev_available and subprocess.run
    so that the CLI functions receive the given data as JSON stdout.

    Usage::

        def test_example(mock_roborev_output, tmp_path):
            mock_roborev_output([{"id": 1, "branch": "main"}])
            reviews = list_reviews(tmp_path)
    """
    stack = ExitStack()

    def _mock(data: Any, *, returncode: int = 0, stderr: str = "") -> MagicMock:
        stdout = json.dumps(data) if not isinstance(data, str) else data
        mock_result = MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
        stack.enter_context(
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            )
        )
        stack.enter_context(patch("subprocess.run", return_value=mock_result))
        return mock_result

    yield _mock
    stack.close()


@pytest.fixture
def mock_roborev_unavailable():
    """Simulate roborev CLI not being installed."""
    with patch(
        "claudechic.features.roborev.cli.is_roborev_available", return_value=False
    ):
        yield


@pytest.fixture
def review_job_factory():
    """Create ReviewJob instances with sensible defaults.

    Usage::

        def test_example(review_job_factory):
            job = review_job_factory(status="running")
    """

    def _factory(**overrides: Any) -> ReviewJob:
        defaults: dict[str, Any] = {
            "id": "1",
            "git_ref": "abc1234",
            "commit_subject": "test",
            "status": "done",
            "verdict": "",
        }
        defaults.update(overrides)
        return ReviewJob(**defaults)

    return _factory


@pytest.fixture
def review_item_factory(review_job_factory):
    """Create ReviewItem instances (unmounted) with sensible defaults.

    Usage::

        def test_example(review_item_factory):
            item = review_item_factory(verdict="pass")
    """

    def _factory(**overrides: Any) -> ReviewItem:
        return ReviewItem(review_job_factory(**overrides))

    return _factory


# ---------------------------------------------------------------------------
# Workflow / RenderContext / GateSettings test factories
# (used by test_gate_predicate.py, test_renderer_split.py,
# test_constraints_decomposition.py, test_env_segment.py, test_peer_roster.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow_dir_factory(tmp_path):
    """Build a real workflow_dir under tmp_path mirroring claudechic/defaults/workflows/<id>/.

    Returns a callable ``_build(...)`` -> ``Path`` (the workflow dir).

    ``roles`` maps role -> list of bare phase ids for which a
    ``<role>/<phase>.md`` file is created. ``with_identity`` maps role ->
    bool (default True) controlling whether ``<role>/identity.md`` is
    written. ``manifest_extra`` is merged into the workflow YAML manifest.
    ``root`` overrides the layout root; default is ``tmp_path``.
    """

    def _build(
        *,
        workflow_id: str = "test_workflow",
        roles: dict[str, list[str]] | None = None,
        with_identity: dict[str, bool] | None = None,
        manifest_extra: dict | None = None,
        root: Path | None = None,
    ) -> Path:
        if root is None:
            root = tmp_path
        roles = roles or {}
        with_identity = with_identity or {}
        (root / "global").mkdir(parents=True, exist_ok=True)
        wf_dir = root / "workflows" / workflow_id
        wf_dir.mkdir(parents=True, exist_ok=True)

        # Discover the main role: first key in ``roles`` (or "coordinator").
        main_role = next(iter(roles), "coordinator")
        manifest: dict[str, Any] = {
            "workflow_id": workflow_id,
            "main_role": main_role,
        }
        if manifest_extra:
            manifest.update(manifest_extra)
        # Default phases: union of all bare phase ids across all roles.
        if "phases" not in manifest:
            phase_ids: list[str] = []
            seen: set[str] = set()
            for phases in roles.values():
                for p in phases:
                    if p not in seen:
                        seen.add(p)
                        phase_ids.append(p)
            if phase_ids:
                manifest["phases"] = [{"id": p, "file": p} for p in phase_ids]

        (wf_dir / f"{workflow_id}.yaml").write_text(
            yaml.dump(manifest, default_flow_style=False), encoding="utf-8"
        )

        for role, phases in roles.items():
            role_dir = wf_dir / role
            role_dir.mkdir(parents=True, exist_ok=True)
            if with_identity.get(role, True):
                (role_dir / "identity.md").write_text(
                    f"IDENTITY: {role}", encoding="utf-8"
                )
            for phase in phases:
                (role_dir / f"{phase}.md").write_text(
                    f"PHASE: {role}/{phase}", encoding="utf-8"
                )
        return wf_dir

    return _build


@pytest.fixture
def real_manifest(workflow_dir_factory):
    """Return a callable that loads a real ``LoadResult`` from a tmp_path layout.

    Usage::

        load_result = real_manifest(root)
    """
    from claudechic.workflows import register_default_parsers
    from claudechic.workflows.loader import ManifestLoader, TierRoots

    def _load(root: Path):
        loader = ManifestLoader(
            tier_roots=TierRoots(package=root, user=None, project=None)
        )
        register_default_parsers(loader)
        return loader.load()

    return _load


@pytest.fixture
def gate_settings_factory():
    """Construct a real GateSettings frozen dataclass from kwargs.

    Recognized kwargs:
      - constraints_compact (bool, default True)
      - constraints_include_skipped (bool, default False)
      - constraints_sites (frozenset[str], default = CONSTRAINTS_SEGMENT_SITES)
      - env_enabled (bool|None, default None -> resolves to True)
      - env_compact (bool, default False)
      - env_sites (frozenset[str], default = ENVIRONMENT_SEGMENT_SITES)
    """
    from claudechic.workflows.agent_folders import (
        CONSTRAINTS_SEGMENT_SITES,
        ENVIRONMENT_SEGMENT_SITES,
        ConstraintsSegmentSettings,
        EnvironmentSegmentSettings,
        GateSettings,
    )

    def _build(**kwargs):
        cs = ConstraintsSegmentSettings(
            compact=kwargs.get("constraints_compact", True),
            include_skipped=kwargs.get("constraints_include_skipped", False),
            sites=kwargs.get("constraints_sites", CONSTRAINTS_SEGMENT_SITES),
        )
        es = EnvironmentSegmentSettings(
            enabled=kwargs.get("env_enabled", None),
            compact=kwargs.get("env_compact", False),
            sites=kwargs.get("env_sites", ENVIRONMENT_SEGMENT_SITES),
        )
        return GateSettings(constraints_segment=cs, environment_segment=es)

    return _build


@pytest.fixture
def render_context_factory(gate_settings_factory):
    """Construct a real RenderContext.

    Pass any RenderContext field as a kwarg. ``settings`` defaults to a
    fresh GateSettings.
    """
    from claudechic.workflows.agent_folders import GateManifest, RenderContext

    def _build(**kwargs):
        if "settings" not in kwargs:
            kwargs["settings"] = gate_settings_factory()
        if "manifest" not in kwargs:
            kwargs["manifest"] = GateManifest()
        return RenderContext(**kwargs)

    return _build


@pytest.fixture
def agent_manager_with_peers():
    """Return a peer_agents-style mapping for use as ``peer_agents=`` kwarg."""
    return {
        "coordinator": "claudechic",
        "skeptic": "skeptic_a",
        "test_engineer": "te_1",
    }


@pytest.fixture
def project_config_writer(tmp_path):
    """Write a project/.claudechic/config.yaml under tmp_path; return the project root.

    Usage::

        root = project_config_writer({"guardrails": False, ...})
    """

    def _write(yaml_dict: dict) -> Path:
        cfg_dir = tmp_path / ".claudechic"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            yaml.dump(yaml_dict, default_flow_style=False), encoding="utf-8"
        )
        return tmp_path

    return _write
