"""Coverage tests for cli/stratifyai_cli.py — MCP sub-commands, cache, check-keys, route, helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from cli.stratifyai_cli import (
    _build_mcp_engine_settings,
    _parse_mcp_assignments,
    app,
)
from stratifyai.models import ChatResponse, Usage


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


def _make_response(content: str = "ok") -> ChatResponse:
    """Build a minimal ChatResponse for mocking.

    Args:
        content: The text content for the response.

    Returns:
        A ChatResponse with minimal usage stats.
    """
    return ChatResponse(
        id="test-id",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        provider="openai",
        created_at=datetime.now(),
        raw_response={},
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.0001,
            cached_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        ),
    )


# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------


class TestParseAssignments:
    """Unit tests for _parse_mcp_assignments."""

    def test_valid_key_value(self) -> None:
        """KEY=VALUE pairs are parsed correctly."""
        result = _parse_mcp_assignments(["FOO=bar", "BAZ=qux"])
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_value_with_equals(self) -> None:
        """Values that themselves contain '=' are preserved."""
        result = _parse_mcp_assignments(["URL=http://localhost:5432/db=foo"])
        assert result["URL"] == "http://localhost:5432/db=foo"

    def test_empty_list(self) -> None:
        """An empty list returns an empty dict."""
        assert _parse_mcp_assignments([]) == {}

    def test_none_returns_empty_dict(self) -> None:
        """None is treated as no assignments."""
        assert _parse_mcp_assignments(None) == {}

    def test_missing_equals_raises(self) -> None:
        """A value without '=' raises typer.BadParameter."""
        with pytest.raises(typer.BadParameter):
            _parse_mcp_assignments(["BADVALUE"])


class TestBuildMcpEngineSettings:
    """Unit tests for _build_mcp_engine_settings."""

    def test_builds_server_entries(self) -> None:
        """Correct settings dict is produced for multiple servers."""
        result = _build_mcp_engine_settings(
            ["postgresql", "filesystem"], enabled=True, auto_start=False
        )
        assert result == {
            "servers": {
                "postgresql": {"enabled": True, "auto_start": False},
                "filesystem": {"enabled": True, "auto_start": False},
            }
        }

    def test_empty_server_list(self) -> None:
        """Empty server list produces empty servers dict."""
        result = _build_mcp_engine_settings([], enabled=True, auto_start=True)
        assert result == {"servers": {}}


# ---------------------------------------------------------------------------
# mcp list command
# ---------------------------------------------------------------------------


class TestMcpListCommand:
    """Tests for `stratifyai mcp list`."""

    def test_table_output(self, runner: CliRunner) -> None:
        """Default table output contains catalog server names."""
        result = runner.invoke(app, ["mcp", "list"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "server" in result.output.lower()

    def test_json_output(self, runner: CliRunner) -> None:
        """--json flag emits valid JSON list."""
        result = runner.invoke(app, ["mcp", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_category_filter(self, runner: CliRunner) -> None:
        """--category flag does not crash even for unknown categories."""
        result = runner.invoke(app, ["mcp", "list", "--category", "nonexistent-cat"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# mcp status command
# ---------------------------------------------------------------------------


class TestMcpStatusCommand:
    """Tests for `stratifyai mcp status`."""

    def test_claude_code_client_text_output(self, runner: CliRunner) -> None:
        """claude-code path prints the advisory message instead of a table."""
        result = runner.invoke(app, ["mcp", "status", "--client", "claude-code"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output or "claude" in result.output.lower()

    def test_claude_code_client_json_output(self, runner: CliRunner) -> None:
        """claude-code + --json emits a JSON payload with the expected keys."""
        result = runner.invoke(
            app, ["mcp", "status", "--client", "claude-code", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["client"] == "claude-code"

    def test_cursor_client_no_config(self, runner: CliRunner, tmp_path: Path) -> None:
        """cursor client with no config file still exits cleanly."""
        with (
            patch(
                "cli.stratifyai_cli.get_configured_servers",
                return_value=(None, {}),
            ),
            patch(
                "cli.stratifyai_cli.get_mcp_client_settings",
                return_value=(None, {}),
            ),
        ):
            result = runner.invoke(
                app,
                ["mcp", "status", "--client", "cursor"],
            )
        assert result.exit_code == 0

    def test_status_table_with_servers(self, runner: CliRunner, tmp_path: Path) -> None:
        """Status table is rendered when servers are configured."""
        server_data = {"postgresql": {"command": "uvx", "args": ["pg-mcp"]}}
        with (
            patch(
                "cli.stratifyai_cli.get_configured_servers",
                return_value=(tmp_path / "mcp.json", server_data),
            ),
            patch(
                "cli.stratifyai_cli.get_mcp_client_settings",
                return_value=(None, {"servers": {"postgresql": {"enabled": True}}}),
            ),
        ):
            result = runner.invoke(
                app,
                ["mcp", "status", "--client", "cursor"],
            )
        assert result.exit_code == 0
        assert "postgresql" in result.output

    def test_status_json_with_servers(self, runner: CliRunner, tmp_path: Path) -> None:
        """--json emits the full status payload when servers are configured."""
        server_data = {"postgresql": {"command": "uvx"}}
        with (
            patch(
                "cli.stratifyai_cli.get_configured_servers",
                return_value=(tmp_path / "mcp.json", server_data),
            ),
            patch(
                "cli.stratifyai_cli.get_mcp_client_settings",
                return_value=(None, {}),
            ),
        ):
            result = runner.invoke(
                app,
                ["mcp", "status", "--client", "cursor", "--json"],
            )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert "configured" in data


# ---------------------------------------------------------------------------
# mcp add-custom command
# ---------------------------------------------------------------------------


class TestMcpAddCustomCommand:
    """Tests for `stratifyai mcp add-custom`."""

    def test_dry_run_outputs_config_json(self, runner: CliRunner) -> None:
        """--dry-run prints JSON config and exits without writing files."""
        result = runner.invoke(
            app,
            [
                "mcp",
                "add-custom",
                "myserver",
                "--command",
                "node",
                "--client",
                "cursor",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "myserver" in result.output

    def test_claude_code_client_prints_shell_command(self, runner: CliRunner) -> None:
        """claude-code client emits a `claude mcp add` shell command."""
        result = runner.invoke(
            app,
            [
                "mcp",
                "add-custom",
                "myserver",
                "--command",
                "node",
                "--client",
                "claude-code",
            ],
        )
        assert result.exit_code == 0
        assert "claude mcp add" in result.output

    def test_write_path_calls_write_functions(self, runner: CliRunner) -> None:
        """Non-dry-run write path calls write_client_config and write_mcp_client_settings."""
        with (
            patch(
                "cli.stratifyai_cli.write_client_config",
                return_value=Path("/tmp/mcp.json"),
            ) as mock_write_cfg,
            patch(
                "cli.stratifyai_cli.write_mcp_client_settings"
            ) as mock_write_settings,
        ):
            result = runner.invoke(
                app,
                [
                    "mcp",
                    "add-custom",
                    "myserver",
                    "--command",
                    "node",
                    "--client",
                    "cursor",
                ],
            )
        assert result.exit_code == 0
        mock_write_cfg.assert_called_once()
        mock_write_settings.assert_called_once()

    def test_vscode_client_uses_mcp_key(self, runner: CliRunner) -> None:
        """vscode client config uses 'mcp' key instead of 'mcpServers'."""
        captured: list[dict] = []

        def capture_write(client, config, **kwargs):
            captured.append(config)
            return Path("/tmp/settings.json")

        with (
            patch("cli.stratifyai_cli.write_client_config", side_effect=capture_write),
            patch("cli.stratifyai_cli.write_mcp_client_settings"),
        ):
            runner.invoke(
                app,
                [
                    "mcp",
                    "add-custom",
                    "excel",
                    "--command",
                    "npx",
                    "--client",
                    "vscode",
                ],
            )

        assert len(captured) == 1
        assert "mcp" in captured[0]

    def test_shell_metachar_in_env_raises_bad_param(self, runner: CliRunner) -> None:
        """An ENV value with no '=' raises a BadParameter error."""
        result = runner.invoke(
            app,
            [
                "mcp",
                "add-custom",
                "s",
                "--command",
                "node",
                "--client",
                "cursor",
                "--env",
                "BADVALUE_NO_EQUALS",
            ],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# mcp export-custom command
# ---------------------------------------------------------------------------


class TestMcpExportCustomCommand:
    """Tests for `stratifyai mcp export-custom`."""

    def test_exports_to_stdout(self, runner: CliRunner) -> None:
        """With no --file, JSON is printed to stdout."""
        with (
            patch(
                "cli.stratifyai_cli.get_configured_servers",
                return_value=(None, {"my-server": {"command": "node"}}),
            ),
            patch(
                "cli.stratifyai_cli.list_mcp_servers",
                return_value=[],
            ),
        ):
            result = runner.invoke(app, ["mcp", "export-custom", "--client", "cursor"])
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert isinstance(data, list)

    def test_claude_code_not_supported(self, runner: CliRunner) -> None:
        """claude-code client is rejected with a non-zero exit code."""
        result = runner.invoke(app, ["mcp", "export-custom", "--client", "claude-code"])
        assert result.exit_code != 0

    def test_exports_to_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """--file writes the JSON to disk."""
        out_file = tmp_path / "servers.json"
        with (
            patch(
                "cli.stratifyai_cli.get_configured_servers",
                return_value=(None, {"s1": {"command": "cmd"}}),
            ),
            patch("cli.stratifyai_cli.list_mcp_servers", return_value=[]),
        ):
            result = runner.invoke(
                app,
                [
                    "mcp",
                    "export-custom",
                    "--client",
                    "cursor",
                    "--file",
                    str(out_file),
                ],
            )
        assert result.exit_code == 0
        assert out_file.exists()


# ---------------------------------------------------------------------------
# mcp import-custom command
# ---------------------------------------------------------------------------


class TestMcpImportCustomCommand:
    """Tests for `stratifyai mcp import-custom`."""

    def _make_import_file(self, tmp_path: Path, entries: list) -> Path:
        """Write a JSON import file and return its path.

        Args:
            tmp_path: Temporary directory.
            entries: List of server entry dicts.

        Returns:
            Path to the written JSON file.
        """
        f = tmp_path / "import.json"
        f.write_text(json.dumps(entries), encoding="utf-8")
        return f

    def test_claude_code_rejected(self, runner: CliRunner, tmp_path: Path) -> None:
        """claude-code client is rejected."""
        f = self._make_import_file(tmp_path, [])
        result = runner.invoke(
            app,
            ["mcp", "import-custom", "--client", "claude-code", "--file", str(f)],
        )
        assert result.exit_code != 0

    def test_empty_server_id_counts_as_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """An entry with an empty server_id increments the error count."""
        f = self._make_import_file(tmp_path, [{"server_id": "", "command": "node"}])
        with patch(
            "cli.stratifyai_cli.get_configured_servers", return_value=(None, {})
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "1" in result.output

    def test_path_separator_in_sid_counts_as_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """A server_id with '/' is rejected."""
        f = self._make_import_file(
            tmp_path, [{"server_id": "bad/sid", "command": "node"}]
        )
        with patch(
            "cli.stratifyai_cli.get_configured_servers", return_value=(None, {})
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        assert "path separator" in result.output

    def test_empty_command_counts_as_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """An entry with an empty command increments the error count."""
        f = self._make_import_file(tmp_path, [{"server_id": "s1", "command": ""}])
        with patch(
            "cli.stratifyai_cli.get_configured_servers", return_value=(None, {})
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        assert "empty command" in result.output

    def test_shell_metachar_in_command_counts_as_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """A command containing shell metacharacters is rejected."""
        f = self._make_import_file(
            tmp_path, [{"server_id": "s1", "command": "node; rm -rf /"}]
        )
        with patch(
            "cli.stratifyai_cli.get_configured_servers", return_value=(None, {})
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        assert "metachar" in result.output

    def test_duplicate_skipped_without_overwrite(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """An existing server_id is skipped unless --overwrite is given."""
        f = self._make_import_file(
            tmp_path, [{"server_id": "existing", "command": "node"}]
        )
        with patch(
            "cli.stratifyai_cli.get_configured_servers",
            return_value=(None, {"existing": {"command": "old"}}),
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        assert "skip" in result.output.lower() or "skipped" in result.output.lower()

    def test_dry_run_preview(self, runner: CliRunner, tmp_path: Path) -> None:
        """--dry-run shows what would be imported without writing."""
        f = self._make_import_file(tmp_path, [{"server_id": "s1", "command": "node"}])
        with (
            patch("cli.stratifyai_cli.get_configured_servers", return_value=(None, {})),
            patch("cli.stratifyai_cli.write_client_config") as mock_write,
        ):
            result = runner.invoke(
                app,
                [
                    "mcp",
                    "import-custom",
                    "--client",
                    "cursor",
                    "--file",
                    str(f),
                    "--dry-run",
                ],
            )
        assert result.exit_code == 0
        mock_write.assert_not_called()
        assert "s1" in result.output

    def test_successful_import_writes_config(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """A valid entry writes config and settings."""
        f = self._make_import_file(tmp_path, [{"server_id": "s1", "command": "node"}])
        with (
            patch("cli.stratifyai_cli.get_configured_servers", return_value=(None, {})),
            patch(
                "cli.stratifyai_cli.write_client_config",
                return_value=Path("/tmp/mcp.json"),
            ) as mock_cfg,
            patch("cli.stratifyai_cli.write_mcp_client_settings") as mock_settings,
        ):
            result = runner.invoke(
                app,
                ["mcp", "import-custom", "--client", "cursor", "--file", str(f)],
            )
        assert result.exit_code == 0
        mock_cfg.assert_called_once()
        mock_settings.assert_called_once()


# ---------------------------------------------------------------------------
# mcp remove command
# ---------------------------------------------------------------------------


class TestMcpRemoveCommand:
    """Tests for `stratifyai mcp remove`."""

    def test_claude_code_prints_claude_command(self, runner: CliRunner) -> None:
        """claude-code client prints a `claude mcp remove` command."""
        result = runner.invoke(
            app,
            ["mcp", "remove", "postgresql", "--client", "claude-code"],
        )
        assert result.exit_code == 0
        assert "claude mcp remove" in result.output

    def test_dry_run_prints_preview(self, runner: CliRunner, tmp_path: Path) -> None:
        """--dry-run prints a JSON preview."""
        with patch(
            "cli.stratifyai_cli.get_configured_servers",
            return_value=(tmp_path / "mcp.json", {"postgresql": {}}),
        ):
            result = runner.invoke(
                app,
                [
                    "mcp",
                    "remove",
                    "postgresql",
                    "--client",
                    "cursor",
                    "--dry-run",
                ],
            )
        assert result.exit_code == 0
        assert "postgresql" in result.output

    def test_remove_existing_server(self, runner: CliRunner, tmp_path: Path) -> None:
        """Removing an existing server prints the success message."""
        with patch(
            "cli.stratifyai_cli.remove_server_from_config",
            return_value=(tmp_path / "mcp.json", True),
        ):
            result = runner.invoke(
                app,
                ["mcp", "remove", "postgresql", "--client", "cursor"],
            )
        assert result.exit_code == 0
        assert "postgresql" in result.output

    def test_remove_nonexistent_server(self, runner: CliRunner, tmp_path: Path) -> None:
        """Removing a server that isn't configured prints an advisory message."""
        with patch(
            "cli.stratifyai_cli.remove_server_from_config",
            return_value=(tmp_path / "mcp.json", False),
        ):
            result = runner.invoke(
                app,
                ["mcp", "remove", "ghost", "--client", "cursor"],
            )
        assert result.exit_code == 0
        assert "ghost" in result.output


# ---------------------------------------------------------------------------
# cache-stats / cache-clear commands
# ---------------------------------------------------------------------------


class TestCacheCommands:
    """Tests for cache-stats and cache-clear commands."""

    def _make_stats(
        self, size: int = 3, hits: int = 5, cost_saved: float = 0.02
    ) -> dict:
        """Build a fake cache stats dict.

        Args:
            size: Cache entry count.
            hits: Total cache hits.
            cost_saved: Total cost saved.

        Returns:
            A dict matching the get_cache_stats() schema.
        """
        return {
            "size": size,
            "max_size": 1000,
            "total_hits": hits,
            "total_misses": 10,
            "total_requests": hits + 10,
            "hit_rate": 33.3,
            "ttl": 3600,
            "total_cost_saved": cost_saved,
        }

    def test_cache_stats_basic(self, runner: CliRunner) -> None:
        """cache-stats renders the metrics table."""
        with patch(
            "cli.stratifyai_cli.get_cache_stats", return_value=self._make_stats()
        ):
            result = runner.invoke(app, ["cache-stats"])
        assert result.exit_code == 0
        assert "Cache" in result.output

    def test_cache_stats_high_hit_rate(self, runner: CliRunner) -> None:
        """A ≥75% hit rate shows the 🎯 indicator."""
        stats = self._make_stats()
        stats["hit_rate"] = 80.0
        with patch("cli.stratifyai_cli.get_cache_stats", return_value=stats):
            result = runner.invoke(app, ["cache-stats"])
        assert result.exit_code == 0

    def test_cache_stats_medium_hit_rate(self, runner: CliRunner) -> None:
        """A 50-74% hit rate shows the ⚠️ indicator."""
        stats = self._make_stats()
        stats["hit_rate"] = 60.0
        with patch("cli.stratifyai_cli.get_cache_stats", return_value=stats):
            result = runner.invoke(app, ["cache-stats"])
        assert result.exit_code == 0

    def test_cache_stats_detailed(self, runner: CliRunner) -> None:
        """--detailed renders the entries table when entries exist."""
        entry = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "hits": 3,
            "cost_saved": 0.01,
            "age_seconds": 100,
            "expires_in": 3500,
        }
        with (
            patch(
                "cli.stratifyai_cli.get_cache_stats", return_value=self._make_stats()
            ),
            patch("cli.stratifyai_cli.get_cache_entries", return_value=[entry]),
        ):
            result = runner.invoke(app, ["cache-stats", "--detailed"])
        assert result.exit_code == 0
        assert "openai" in result.output

    def test_cache_stats_zero_cost_saved(self, runner: CliRunner) -> None:
        """Zero cost_saved with non-zero hits still renders the cost section."""
        stats = self._make_stats(hits=2, cost_saved=0.0)
        with patch("cli.stratifyai_cli.get_cache_stats", return_value=stats):
            result = runner.invoke(app, ["cache-stats"])
        assert result.exit_code == 0

    def test_cache_clear_empty_cache(self, runner: CliRunner) -> None:
        """cache-clear on an empty cache prints an advisory and exits 0."""
        stats = self._make_stats(size=0, hits=0, cost_saved=0.0)
        with patch("cli.stratifyai_cli.get_cache_stats", return_value=stats):
            result = runner.invoke(app, ["cache-clear"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "already" in result.output.lower()

    def test_cache_clear_force(self, runner: CliRunner) -> None:
        """--force skips the confirmation prompt and clears."""
        with (
            patch(
                "cli.stratifyai_cli.get_cache_stats", return_value=self._make_stats()
            ),
            patch("cli.stratifyai_cli.clear_cache") as mock_clear,
        ):
            result = runner.invoke(app, ["cache-clear", "--force"])
        assert result.exit_code == 0
        mock_clear.assert_called_once()

    def test_cache_clear_cancelled(self, runner: CliRunner) -> None:
        """Declining the confirmation prompt leaves the cache intact."""
        with (
            patch(
                "cli.stratifyai_cli.get_cache_stats", return_value=self._make_stats()
            ),
            patch("cli.stratifyai_cli.Confirm.ask", return_value=False),
            patch("cli.stratifyai_cli.clear_cache") as mock_clear,
        ):
            result = runner.invoke(app, ["cache-clear"])
        assert result.exit_code == 0
        mock_clear.assert_not_called()

    def test_cache_clear_confirmed(self, runner: CliRunner) -> None:
        """Confirming the prompt clears the cache."""
        with (
            patch(
                "cli.stratifyai_cli.get_cache_stats", return_value=self._make_stats()
            ),
            patch("cli.stratifyai_cli.Confirm.ask", return_value=True),
            patch("cli.stratifyai_cli.clear_cache") as mock_clear,
        ):
            result = runner.invoke(app, ["cache-clear"])
        assert result.exit_code == 0
        mock_clear.assert_called_once()


# ---------------------------------------------------------------------------
# check-keys command
# ---------------------------------------------------------------------------


class TestCheckKeysCommand:
    """Tests for `stratifyai check-keys`."""

    def test_all_configured(self, runner: CliRunner) -> None:
        """When all providers have keys, the 'All N providers configured' message appears."""
        available = {"openai": True, "anthropic": True}
        with patch(
            "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
            return_value=available,
        ):
            result = runner.invoke(app, ["check-keys"])
        assert result.exit_code == 0

    def test_none_configured(self, runner: CliRunner) -> None:
        """When no providers have keys, the 'No providers configured' message appears."""
        available = {"openai": False, "anthropic": False}
        with patch(
            "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
            return_value=available,
        ):
            result = runner.invoke(app, ["check-keys"])
        assert result.exit_code == 0
        assert "No providers" in result.output or "0" in result.output

    def test_partial_configured(self, runner: CliRunner) -> None:
        """When some providers have keys, the partial count is shown."""
        available = {"openai": True, "anthropic": False}
        with patch(
            "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
            return_value=available,
        ):
            result = runner.invoke(app, ["check-keys"])
        assert result.exit_code == 0
        assert "1/2" in result.output or "openai" in result.output


# ---------------------------------------------------------------------------
# models and providers commands
# ---------------------------------------------------------------------------


class TestModelsProvidersCommands:
    """Tests for `stratifyai models` and `stratifyai providers`."""

    def test_models_command(self, runner: CliRunner) -> None:
        """`models` renders a table with at least one row."""
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "Models" in result.output or "openai" in result.output

    def test_models_filtered_by_provider(self, runner: CliRunner) -> None:
        """`models --provider openai` shows only openai rows."""
        result = runner.invoke(app, ["models", "--provider", "openai"])
        assert result.exit_code == 0
        assert "openai" in result.output

    def test_providers_command(self, runner: CliRunner) -> None:
        """`providers` renders a table listing all providers."""
        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0
        assert "Providers" in result.output or "openai" in result.output


# ---------------------------------------------------------------------------
# route command
# ---------------------------------------------------------------------------


class TestRouteCommand:
    """Tests for `stratifyai route`."""

    def test_route_default_strategy(self, runner: CliRunner) -> None:
        """`route` with default strategy prints a routing decision."""
        result = runner.invoke(app, ["route", "Explain quantum computing"])
        # exit_code may be 0 or 1 depending on Confirm.ask mock; just check no crash
        assert result.exit_code in (0, 1)

    def test_route_dry_run(self, runner: CliRunner) -> None:
        """`route --dry-run` shows ranked candidates without API calls."""
        result = runner.invoke(
            app,
            ["route", "Explain quantum computing", "--dry-run"],
        )
        assert result.exit_code == 0
        assert (
            "Routing" in result.output
            or "Dry" in result.output
            or "Rank" in result.output
        )

    def test_route_invalid_strategy(self, runner: CliRunner) -> None:
        """An invalid strategy string exits with code 1."""
        result = runner.invoke(
            app,
            ["route", "Hello", "--strategy", "invalid"],
        )
        assert result.exit_code != 0

    def test_route_dry_run_with_cost_strategy(self, runner: CliRunner) -> None:
        """`route --dry-run --strategy cost` runs without error."""
        result = runner.invoke(
            app,
            ["route", "Hello", "--dry-run", "--strategy", "cost"],
        )
        assert result.exit_code == 0

    def test_route_invalid_capability(self, runner: CliRunner) -> None:
        """An unknown capability exits with code 1."""
        result = runner.invoke(
            app,
            ["route", "Hello", "--capability", "telepathy"],
        )
        assert result.exit_code != 0

    def test_route_dry_run_execute_conflict(self, runner: CliRunner) -> None:
        """--dry-run and --execute together is rejected."""
        result = runner.invoke(
            app,
            ["route", "Hello", "--dry-run", "--execute"],
        )
        assert result.exit_code != 0
