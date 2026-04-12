"""Unit tests for interactive command Phase 1 MCP support (cli-mcp-interactive-plan.md)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.stratifyai_cli import app
from stratifyai.mcp_client.server_manager import ServerStatus
from stratifyai.mcp_client.tool_registry import ToolDescriptor


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def simple_catalog() -> dict:
    """Minimal MODEL_CATALOG for interactive command testing."""
    return {
        "openai": {
            "gpt-4o-mini": {
                "context": 128000,
                "display_name": "GPT-4o mini",
                "description": "Fast and affordable",
            }
        }
    }


def _make_tool_descriptor(server_id: str, tool_name: str = "query") -> ToolDescriptor:
    """Create a minimal ToolDescriptor for testing.

    Args:
        server_id: The server ID to assign.
        tool_name: The tool name to assign.

    Returns:
        A ToolDescriptor with the given server_id and tool_name.
    """
    td = MagicMock(spec=ToolDescriptor)
    td.server_id = server_id
    td.tool_name = tool_name
    td.namespace = f"{server_id}.{tool_name}"
    return td


def _invoke_interactive_with_mcp(
    runner: CliRunner,
    extra_args: list[str],
    simple_catalog: dict,
    mock_engine: MagicMock,
    run_sync_side_effect=None,
    prompt_side_effect: list | None = None,
):
    """Helper that invokes 'interactive' with all required mocks in place.

    Args:
        runner: Typer CliRunner.
        extra_args: Additional CLI arguments (e.g. ['--mcp-server', 'postgresql']).
        simple_catalog: Mocked MODEL_CATALOG dict.
        mock_engine: Pre-configured MCPClientEngine mock.
        run_sync_side_effect: Optional side_effect for run_sync.
        prompt_side_effect: List of Prompt.ask return values.

    Returns:
        The invocation Result.
    """
    if prompt_side_effect is None:
        # Default: skip file prompt, then exit the chat loop
        prompt_side_effect = ["", "exit"]

    base_args = [
        "interactive",
        "--provider",
        "openai",
        "--model",
        "gpt-4o-mini",
    ]

    run_sync_kwargs: dict = {}
    if run_sync_side_effect is not None:
        run_sync_kwargs["side_effect"] = run_sync_side_effect
    else:
        run_sync_kwargs["return_value"] = None

    with (
        patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
        patch("cli.stratifyai_cli.LLMClient"),
        patch(
            "stratifyai.mcp_client.MCPClientEngine",
            return_value=mock_engine,
        ),
        patch("cli.stratifyai_cli.run_sync", **run_sync_kwargs),
        patch(
            "cli.stratifyai_cli.Prompt.ask",
            side_effect=prompt_side_effect,
        ),
    ):
        return runner.invoke(app, base_args + extra_args)


# ---------------------------------------------------------------------------
# 1.1 — CLI flag registration
# ---------------------------------------------------------------------------


class TestMCPFlagRegistration:
    """Verify that the new MCP flags appear in --help output (step 1.1)."""

    def test_mcp_server_flag_documented_in_help(self, runner: CliRunner) -> None:
        """--mcp-server must appear in 'interactive --help' output.

        Args:
            runner: Typer CliRunner fixture.
        """
        result = runner.invoke(app, ["interactive", "--help"])
        assert result.exit_code == 0, result.output
        assert "--mcp-server" in result.output

    def test_mcp_all_flag_documented_in_help(self, runner: CliRunner) -> None:
        """--mcp-all must appear in 'interactive --help' output.

        Args:
            runner: Typer CliRunner fixture.
        """
        result = runner.invoke(app, ["interactive", "--help"])
        assert result.exit_code == 0, result.output
        assert "--mcp-all" in result.output


# ---------------------------------------------------------------------------
# 1.2/1.3 — Unknown server warning (non-fatal)
# ---------------------------------------------------------------------------


class TestUnknownMCPServerWarning:
    """Requesting an unknown server ID must warn and continue (step 1.2/1.3)."""

    def test_unknown_server_id_prints_warning(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """Passing --mcp-server with an undiscovered ID must print a warning.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="stopped")
        ]
        mock_engine.list_tools.return_value = []

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "nonexistent-server"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        assert result.exit_code == 0, result.output
        assert "Unknown MCP server" in result.output
        assert "nonexistent-server" in result.output

    def test_unknown_server_does_not_crash_session(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """Session must continue normally after an unknown server warning.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="stopped")
        ]
        mock_engine.list_tools.return_value = []

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "nonexistent-server"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        # Exit code must be 0 (graceful exit, not a crash)
        assert result.exit_code == 0
        # The session must still show the interactive banner
        assert "StratifyAI Interactive Mode" in result.output


# ---------------------------------------------------------------------------
# 1.4 — Banner includes MCP info when servers are active
# ---------------------------------------------------------------------------


class TestMCPBanner:
    """Banner must show active MCP server names and tool counts (step 1.4)."""

    def test_banner_includes_mcp_line_when_server_is_active(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """When a server starts successfully, 'MCP: ...' must appear in the banner.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        # Return 3 tool descriptors for postgresql
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
            _make_tool_descriptor("postgresql", "schema"),
            _make_tool_descriptor("postgresql", "tables"),
        ]

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "postgresql"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        assert result.exit_code == 0, result.output
        assert "MCP:" in result.output
        assert "postgresql" in result.output

    def test_banner_shows_tool_count(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """The banner MCP line must include the tool count for each active server.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
            _make_tool_descriptor("postgresql", "schema"),
        ]

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "postgresql"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        assert result.exit_code == 0, result.output
        # Banner must show "postgresql (2 tools)"
        assert "2 tools" in result.output

    def test_no_mcp_line_when_no_servers_requested(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """Without --mcp-server or --mcp-all, no 'MCP:' line should appear in banner.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        with (
            patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
            patch("cli.stratifyai_cli.LLMClient"),
            patch(
                "cli.stratifyai_cli.Prompt.ask",
                side_effect=["", "exit"],
            ),
        ):
            result = runner.invoke(
                app,
                ["interactive", "--provider", "openai", "--model", "gpt-4o-mini"],
            )

        assert result.exit_code == 0, result.output
        assert "MCP:" not in result.output
