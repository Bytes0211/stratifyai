"""Phase 14 developer experience tests."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from cli.stratifyai_cli import app
from stratifyai.exceptions import AuthenticationError, MaxRetriesExceededError

runner = CliRunner()


def test_route_dry_run_does_not_execute_api_call() -> None:
    """Dry-run route should print reasoning output without provider calls."""
    with patch("cli.stratifyai_cli.LLMClient") as mock_client:
        result = runner.invoke(app, ["route", "Hello world", "--dry-run"])

    assert result.exit_code == 0
    assert "Routing Candidates (Dry Run)" in result.output
    mock_client.assert_not_called()


def test_doctor_reports_when_no_keys_configured() -> None:
    """Doctor command should report missing provider keys without crashing."""
    with patch(
        "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
        return_value={"openai": False, "anthropic": False},
    ):
        result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "No provider API keys configured" in result.output


def test_doctor_json_output_structure() -> None:
    """Doctor JSON mode should emit machine-readable diagnostics payload."""
    with patch(
        "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
        return_value={"openai": False, "anthropic": False},
    ):
        result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload["ok"] is True
    assert payload["live_enabled"] is False
    assert payload["configured_providers"] == []
    assert any(check["name"] == "API keys" for check in payload["checks"])


def test_doctor_json_exits_nonzero_on_init_failure() -> None:
    """Doctor should return non-zero when a configured provider fails init."""
    with (
        patch(
            "stratifyai.api_key_helper.APIKeyHelper.check_available_providers",
            return_value={"openai": True},
        ),
        patch("cli.stratifyai_cli.LLMClient", side_effect=Exception("init failure")),
    ):
        result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output.strip())
    assert payload["ok"] is False
    assert payload["init_failures"]


def test_structured_error_codes_available() -> None:
    """Exceptions should expose stable error codes for programmatic handling."""
    auth_error = AuthenticationError(provider="openai")
    assert auth_error.error_code == "AUTHENTICATION_FAILED"
    assert auth_error.to_dict()["error_type"] == "AuthenticationError"

    retries_error = MaxRetriesExceededError(attempts=3, last_error=Exception("boom"))
    assert retries_error.error_code == "MAX_RETRIES_EXCEEDED"
    assert retries_error.to_dict()["message"].startswith("Maximum retry attempts")
