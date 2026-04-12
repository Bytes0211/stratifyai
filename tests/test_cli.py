"""Unit tests for interactive command MCP support (cli-mcp-interactive-plan.md)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.stratifyai_cli import app
from stratifyai.mcp_client.permissions import PermissionDecision, PermissionMode
from stratifyai.mcp_client.server_manager import ServerStatus
from stratifyai.mcp_client.tool_registry import ToolDescriptor
from stratifyai.models import ChatResponse, Usage

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


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
        assert "--mcp-server" in strip_ansi(result.output)

    def test_mcp_all_flag_documented_in_help(self, runner: CliRunner) -> None:
        """--mcp-all must appear in 'interactive --help' output.

        Args:
            runner: Typer CliRunner fixture.
        """
        result = runner.invoke(app, ["interactive", "--help"])
        assert result.exit_code == 0, result.output
        assert "--mcp-all" in strip_ansi(result.output)


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


# ---------------------------------------------------------------------------
# Helpers for Phase 2
# ---------------------------------------------------------------------------


def _make_chat_response(
    content: str = "Hello!",
    raw_response: dict | None = None,
) -> ChatResponse:
    """Create a minimal ChatResponse for testing."""
    return ChatResponse(
        id="resp-1",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.0001,
        ),
        provider="openai",
        created_at=datetime.now(tz=timezone.utc),
        raw_response=raw_response or {},
        latency_ms=42.0,
    )


def _invoke_interactive_with_chat(
    runner: CliRunner,
    simple_catalog: dict,
    mock_engine: MagicMock,
    mock_response: ChatResponse,
    user_message: str = "Hello",
    use_mcp: bool = True,
):
    """Invoke interactive with a mock chat response, sending one message then exiting.

    Args:
        runner: Typer CliRunner.
        simple_catalog: Mocked MODEL_CATALOG dict.
        mock_engine: Pre-configured MCPClientEngine mock.
        mock_response: ChatResponse to return from the chat call.
        user_message: The message to send in the chat loop.
        use_mcp: Whether to enable MCP.

    Returns:
        The invocation Result.
    """
    extra_args = ["--mcp-server", "postgresql"] if use_mcp else []
    base_args = [
        "interactive",
        "--provider",
        "openai",
        "--model",
        "gpt-4o-mini",
    ]

    mock_client = MagicMock()
    mock_client.chat_with_mcp_sync.return_value = mock_response
    mock_client.chat_completion_sync.return_value = mock_response

    mock_client_class = MagicMock(return_value=mock_client)

    with (
        patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
        patch("cli.stratifyai_cli.LLMClient", mock_client_class),
        patch(
            "stratifyai.mcp_client.MCPClientEngine",
            return_value=mock_engine,
        ),
        patch("cli.stratifyai_cli.run_sync", return_value=None),
        patch(
            "cli.stratifyai_cli.Prompt.ask",
            side_effect=["", user_message, "exit"],
        ),
    ):
        result = runner.invoke(app, base_args + extra_args)

    return result, mock_client


# ---------------------------------------------------------------------------
# Phase 2 — Route chat through MCP engine
# ---------------------------------------------------------------------------


class TestMCPChatRouting:
    """Phase 2: MCP-active sessions must route through chat_with_mcp_sync."""

    def test_mcp_active_routes_through_chat_with_mcp_sync(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        resp = _make_chat_response()
        result, mock_client = _invoke_interactive_with_chat(
            runner,
            simple_catalog,
            mock_engine,
            resp,
            use_mcp=True,
        )

        assert result.exit_code == 0, result.output
        mock_client.chat_with_mcp_sync.assert_called_once()
        mock_client.chat_completion_sync.assert_not_called()

    def test_non_mcp_session_uses_chat_completion_sync(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        resp = _make_chat_response()
        mock_client = MagicMock()
        mock_client.chat_completion_sync.return_value = resp

        mock_client_class = MagicMock(return_value=mock_client)

        with (
            patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
            patch("cli.stratifyai_cli.LLMClient", mock_client_class),
            patch(
                "cli.stratifyai_cli.Prompt.ask",
                side_effect=["", "Hello", "exit"],
            ),
        ):
            result = runner.invoke(
                app,
                ["interactive", "--provider", "openai", "--model", "gpt-4o-mini"],
            )

        assert result.exit_code == 0, result.output
        mock_client.chat_completion_sync.assert_called_once()
        mock_client.chat_with_mcp_sync.assert_not_called()


class TestMCPToolResultDisplay:
    """Phase 2: Tool results must be displayed before the assistant response."""

    def test_tool_results_displayed_in_output(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        resp = _make_chat_response(
            content="Here are the results.",
            raw_response={
                "mcp_tool_results": [
                    {
                        "server_id": "postgresql",
                        "tool_name": "query",
                        "content": "3 rows returned",
                    },
                ],
            },
        )
        result, _ = _invoke_interactive_with_chat(
            runner,
            simple_catalog,
            mock_engine,
            resp,
        )

        assert result.exit_code == 0, result.output
        assert "postgresql.query" in result.output
        assert "3 rows returned" in result.output

    def test_mcp_warnings_displayed(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        resp = _make_chat_response(
            raw_response={
                "mcp_warnings": ["Server postgresql is running slowly"],
            },
        )
        result, _ = _invoke_interactive_with_chat(
            runner,
            simple_catalog,
            mock_engine,
            resp,
        )

        assert result.exit_code == 0, result.output
        assert "MCP:" in result.output
        assert "running slowly" in result.output

    def test_mcp_tool_count_in_metadata(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected")
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        resp = _make_chat_response(
            raw_response={
                "mcp_tool_results": [
                    {"server_id": "postgresql", "tool_name": "query", "content": "ok"},
                    {"server_id": "postgresql", "tool_name": "schema", "content": "ok"},
                ],
            },
        )
        result, _ = _invoke_interactive_with_chat(
            runner,
            simple_catalog,
            mock_engine,
            resp,
        )

        assert result.exit_code == 0, result.output
        assert "MCP tools: 2" in result.output


# ---------------------------------------------------------------------------
# Phase 3 — Interactive /mcp commands
# ---------------------------------------------------------------------------


def _make_rich_tool_descriptor(
    server_id: str,
    tool_name: str = "query",
    description: str = "Execute a SQL query",
) -> ToolDescriptor:
    """Create a ToolDescriptor with all fields populated for /mcp tools tests.

    Args:
        server_id: The server ID to assign.
        tool_name: The tool name to assign.
        description: The tool description.

    Returns:
        A ToolDescriptor with populated fields.
    """
    td = MagicMock(spec=ToolDescriptor)
    td.server_id = server_id
    td.tool_name = tool_name
    td.namespace = f"{server_id}.{tool_name}"
    td.description = description
    return td


def _invoke_interactive_with_mcp_command(
    runner: CliRunner,
    simple_catalog: dict,
    mock_engine: MagicMock,
    mcp_command: str,
    *,
    extra_prompt_values: list[str] | None = None,
):
    """Invoke interactive mode, send an /mcp command, then exit.

    Args:
        runner: Typer CliRunner.
        simple_catalog: Mocked MODEL_CATALOG dict.
        mock_engine: Pre-configured MCPClientEngine mock.
        mcp_command: The /mcp command to send (e.g. '/mcp tools').
        extra_prompt_values: Additional prompt values before exit.

    Returns:
        The invocation Result.
    """
    prompt_values = ["", mcp_command]
    if extra_prompt_values:
        prompt_values.extend(extra_prompt_values)
    prompt_values.append("exit")

    return _invoke_interactive_with_mcp(
        runner,
        extra_args=["--mcp-server", "postgresql"],
        simple_catalog=simple_catalog,
        mock_engine=mock_engine,
        prompt_side_effect=prompt_values,
    )


class TestMCPStatusCommand:
    """Verify /mcp (or /mcp status) displays the server overview table (step 3.1)."""

    def test_mcp_status_displays_server_list(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp' must display a table with server IDs, status, and active column.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
            ServerStatus(server_id="brave-search", status="stopped"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
            _make_tool_descriptor("postgresql", "schema"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "postgresql" in out
        assert "brave-search" in out
        assert "connected" in out
        assert "stopped" in out

    def test_mcp_status_shows_active_column(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """The active column must show 'yes' for active servers and 'no' for others.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
            ServerStatus(server_id="brave-search", status="stopped"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp status"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        # postgresql should be active (it was started via --mcp-server)
        assert "yes" in out
        # brave-search was not requested, so should show 'no'
        assert "no" in out


class TestMCPOnCommand:
    """Verify /mcp on <server_id> activates a server for the session (step 3.2)."""

    def test_mcp_on_adds_server_to_active_list(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp on brave-search' must activate the server and show confirmation.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
            ServerStatus(server_id="brave-search", status="stopped"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]
        mock_engine.get_server_status.return_value = ServerStatus(
            server_id="brave-search", status="stopped"
        )

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp on brave-search"
        )

        assert result.exit_code == 0, result.output
        assert "Activated brave-search" in strip_ansi(result.output)

    def test_mcp_on_already_active_shows_message(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp on postgresql' when already active must say so.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp on postgresql"
        )

        assert result.exit_code == 0, result.output
        assert "already active" in strip_ansi(result.output)

    def test_mcp_on_unknown_server_shows_warning(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp on nonexistent' must warn about unknown server.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp on nonexistent"
        )

        assert result.exit_code == 0, result.output
        assert "Unknown MCP server" in strip_ansi(result.output)


class TestMCPOffCommand:
    """Verify /mcp off <server_id> deactivates a server for the session (step 3.2)."""

    def test_mcp_off_removes_server_from_active_list(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp off postgresql' must deactivate the server.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp off postgresql"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "Deactivated postgresql" in out
        assert "server still running" in out

    def test_mcp_off_not_active_shows_message(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp off brave-search' when not active must say so.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp off brave-search"
        )

        assert result.exit_code == 0, result.output
        assert "not in the active list" in strip_ansi(result.output)


class TestMCPToolsCommand:
    """Verify /mcp tools lists discovered MCP tools (step 3.3)."""

    def test_mcp_tools_lists_all_tools(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp tools' must display namespace, description, and permission.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        perm_mock = MagicMock()
        perm_mock.evaluate.return_value = PermissionDecision(
            mode=PermissionMode.ALLOW, reason="test"
        )

        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_rich_tool_descriptor("postgresql", "query", "Execute a SQL query"),
            _make_rich_tool_descriptor("postgresql", "schema", "Get table schema"),
        ]
        mock_engine._permission_manager = perm_mock

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp tools"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "postgresql.query" in out
        assert "postgresql.schema" in out
        assert "Execute a SQL query" in out
        assert "allow" in out

    def test_mcp_tools_filters_by_server_id(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp tools postgresql' must only show tools for that server.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        perm_mock = MagicMock()
        perm_mock.evaluate.return_value = PermissionDecision(
            mode=PermissionMode.ALLOW, reason="test"
        )

        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_rich_tool_descriptor("postgresql", "query"),
            _make_rich_tool_descriptor("filesystem", "read_file", "Read a file"),
        ]
        mock_engine._permission_manager = perm_mock

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp tools postgresql"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "postgresql.query" in out
        # filesystem tools should NOT appear
        assert "filesystem.read_file" not in out

    def test_mcp_tools_unknown_server_shows_empty(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp tools nonexistent' must show no-tools message.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_rich_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/mcp tools nonexistent"
        )

        assert result.exit_code == 0, result.output
        assert "No tools found" in strip_ansi(result.output)


class TestMCPRefreshCommand:
    """Verify /mcp refresh re-reads local client configs (step 3.4)."""

    def test_mcp_refresh_calls_sync(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/mcp refresh' must invoke sync_configured_servers on the engine.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        # Track whether run_sync was called with the sync coroutine
        sync_called = []

        def track_run_sync(coro=None):
            """Track calls to run_sync, identifying sync_configured_servers."""
            if coro is not None:
                sync_called.append(str(coro))
            return None

        base_args = [
            "interactive",
            "--provider",
            "openai",
            "--model",
            "gpt-4o-mini",
            "--mcp-server",
            "postgresql",
        ]

        with (
            patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
            patch("cli.stratifyai_cli.LLMClient"),
            patch(
                "stratifyai.mcp_client.MCPClientEngine",
                return_value=mock_engine,
            ),
            patch("cli.stratifyai_cli.run_sync", side_effect=track_run_sync),
            patch(
                "cli.stratifyai_cli.Prompt.ask",
                side_effect=["", "/mcp refresh", "exit"],
            ),
        ):
            result = runner.invoke(app, base_args)

        assert result.exit_code == 0, result.output
        assert "Refreshed" in strip_ansi(result.output)
        # sync_configured_servers must have been called (via run_sync)
        mock_engine.sync_configured_servers.assert_called_once_with(client="auto")


class TestMCPHelpUpdate:
    """Verify /help output includes the new /mcp subcommands (step 3.5)."""

    def test_help_includes_mcp_subcommands(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/help' must list /mcp on, /mcp off, /mcp tools, /mcp refresh.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/help"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "/mcp on <id>" in out
        assert "/mcp off <id>" in out
        assert "/mcp tools" in out
        assert "/mcp refresh" in out

    def test_help_shows_active_mcp_servers(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """'/help' session info must show active MCP servers.

        Args:
            runner: Typer CliRunner fixture.
            simple_catalog: Minimal model catalog fixture.
        """
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        result = _invoke_interactive_with_mcp_command(
            runner, simple_catalog, mock_engine, "/help"
        )

        assert result.exit_code == 0, result.output
        out = strip_ansi(result.output)
        assert "MCP active:" in out
        assert "postgresql" in out


# ---------------------------------------------------------------------------
# Phase 4 — Error handling and edge cases
# ---------------------------------------------------------------------------


class TestMCPStartupFailureNonFatal:
    """4.1: Server startup failure must warn and continue, not crash."""

    def test_startup_failure_prints_warning_and_continues(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="broken-server", status="stopped"),
        ]
        mock_engine.list_tools.return_value = []

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "broken-server"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
            run_sync_side_effect=RuntimeError("spawn failed"),
        )

        assert result.exit_code == 0, result.output
        assert "Failed to start" in result.output
        assert "StratifyAI Interactive Mode" in result.output


class TestMCPToolExecutionError:
    """4.2: Tool execution errors must be displayed, session continues."""

    def test_tool_error_displayed_in_output(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        resp = _make_chat_response(
            content="I encountered an error.",
            raw_response={
                "mcp_tool_results": [
                    {
                        "server_id": "postgresql",
                        "tool_name": "query",
                        "error": "connection refused",
                        "result": None,
                    },
                ],
            },
        )
        result, _ = _invoke_interactive_with_chat(
            runner,
            simple_catalog,
            mock_engine,
            resp,
        )

        assert result.exit_code == 0, result.output
        assert "ERROR: connection refused" in result.output
        assert "postgresql.query" in result.output

    def test_chat_exception_does_not_crash_session(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]

        mock_client = MagicMock()
        mock_client.chat_with_mcp_sync.side_effect = RuntimeError("tool loop failed")

        mock_client_class = MagicMock(return_value=mock_client)

        with (
            patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
            patch("cli.stratifyai_cli.LLMClient", mock_client_class),
            patch(
                "stratifyai.mcp_client.MCPClientEngine",
                return_value=mock_engine,
            ),
            patch("cli.stratifyai_cli.run_sync", return_value=None),
            patch(
                "cli.stratifyai_cli.Prompt.ask",
                side_effect=["", "test query", "exit"],
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "interactive",
                    "--provider",
                    "openai",
                    "--model",
                    "gpt-4o-mini",
                    "--mcp-server",
                    "postgresql",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "tool loop failed" in result.output


class TestMCPEngineInitFailure:
    """4.3: Engine init failure must fall back to non-MCP mode."""

    def test_engine_init_failure_falls_back(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        with (
            patch("cli.stratifyai_cli.MODEL_CATALOG", simple_catalog),
            patch("cli.stratifyai_cli.LLMClient"),
            patch(
                "stratifyai.mcp_client.MCPClientEngine",
                side_effect=RuntimeError("no configs found"),
            ),
            patch(
                "cli.stratifyai_cli.Prompt.ask",
                side_effect=["", "exit"],
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "interactive",
                    "--provider",
                    "openai",
                    "--model",
                    "gpt-4o-mini",
                    "--mcp-server",
                    "postgresql",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "MCP initialization failed" in result.output
        assert "Continuing without MCP" in result.output
        assert "StratifyAI Interactive Mode" in result.output


class TestMCPGracefulShutdown:
    """4.4: Session exit must call engine.stop() for cleanup."""

    def test_exit_triggers_engine_stop(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]
        mock_engine.stop.return_value = None

        _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "postgresql"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        # The finally block calls run_sync(mcp_engine.stop()).
        # Since run_sync is mocked, the stop() coroutine is passed to it.
        # Verify the engine's stop method was at least invoked.
        assert mock_engine.stop.called

    def test_shutdown_exception_is_swallowed(
        self, runner: CliRunner, simple_catalog: dict
    ) -> None:
        """Even if engine.stop() throws, session exits cleanly."""
        mock_engine = MagicMock()
        mock_engine.list_servers.return_value = [
            ServerStatus(server_id="postgresql", status="connected"),
        ]
        mock_engine.list_tools.return_value = [
            _make_tool_descriptor("postgresql", "query"),
        ]
        mock_engine.stop.side_effect = RuntimeError("cleanup failed")

        result = _invoke_interactive_with_mcp(
            runner,
            extra_args=["--mcp-server", "postgresql"],
            simple_catalog=simple_catalog,
            mock_engine=mock_engine,
        )

        # Session must exit cleanly despite stop() failure
        assert result.exit_code == 0, result.output
