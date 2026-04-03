"""Tests for MCP schemas and error mapping."""

import json

import pytest

from stratifyai.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    InvalidModelError,
    InvalidProviderError,
    ProviderAPIError,
    RateLimitError,
    ValidationError,
)
from stratifyai.mcp_server.errors import (
    EXCEPTION_MAP,
    MCPErrorCode,
    mcp_error,
    raise_tool_error,
)
from stratifyai.mcp_server.schemas import (
    MCP_SCHEMA_VERSION,
    ChatCompletionInput,
    ChatCompletionOutput,
    ChatWithRoutingInput,
    ChatWithRoutingOutput,
    CostSummaryInput,
    CostSummaryOutput,
    EstimateCostInput,
    EstimateCostOutput,
    ListModelsInput,
    MessageParam,
    ModelInfoInput,
    ModelInfoOutput,
    ModelSummary,
    ProviderInfo,
    ValidateProviderInput,
    ValidateProviderOutput,
)


class TestMCPSchemaVersion:
    def test_schema_version_is_one(self):
        assert MCP_SCHEMA_VERSION == 1

    def test_output_schemas_include_version(self):
        output = ChatCompletionOutput(
            content="hi", provider="openai", model="gpt-4.1-mini"
        )
        assert output.mcp_schema_version == 1

    def test_routing_output_includes_version(self):
        output = ChatWithRoutingOutput(
            selected_provider="openai",
            selected_model="gpt-4.1-mini",
            routing_strategy="hybrid",
            content="hi",
        )
        assert output.mcp_schema_version == 1


class TestMessageParam:
    def test_valid_message(self):
        msg = MessageParam(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestChatCompletionInput:
    def test_required_fields(self):
        inp = ChatCompletionInput(
            provider="openai",
            model="gpt-4.1-mini",
            messages=[MessageParam(role="user", content="Hi")],
        )
        assert inp.provider == "openai"
        assert inp.temperature is None
        assert inp.max_tokens is None

    def test_optional_fields(self):
        inp = ChatCompletionInput(
            provider="anthropic",
            model="claude-sonnet-4-5",
            messages=[MessageParam(role="user", content="Hi")],
            temperature=0.5,
            max_tokens=100,
        )
        assert inp.temperature == 0.5
        assert inp.max_tokens == 100


class TestChatCompletionOutput:
    def test_defaults(self):
        output = ChatCompletionOutput(
            content="Hello", provider="openai", model="gpt-4.1-mini"
        )
        assert output.prompt_tokens == 0
        assert output.completion_tokens == 0
        assert output.cost_usd == 0.0
        assert output.latency_ms is None

    def test_model_dump(self):
        output = ChatCompletionOutput(
            content="Hello",
            provider="openai",
            model="gpt-4.1-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.001,
            latency_ms=200.0,
        )
        d = output.model_dump()
        assert d["content"] == "Hello"
        assert d["cost_usd"] == 0.001
        assert d["mcp_schema_version"] == 1


class TestChatWithRoutingInput:
    def test_defaults(self):
        inp = ChatWithRoutingInput(messages=[MessageParam(role="user", content="Hi")])
        assert inp.strategy == "hybrid"
        assert inp.capabilities is None
        assert inp.preferred_providers is None


class TestProviderInfo:
    def test_creation(self):
        info = ProviderInfo(provider="openai", model_count=12, configured=True)
        assert info.provider == "openai"
        assert info.model_count == 12


class TestModelSummary:
    def test_defaults(self):
        summary = ModelSummary(model_id="gpt-4.1-mini")
        assert summary.context_window == 0
        assert summary.capabilities == []

    def test_with_capabilities(self):
        summary = ModelSummary(
            model_id="gpt-4.1",
            context_window=128000,
            capabilities=["vision", "tools"],
        )
        assert "vision" in summary.capabilities


class TestModelInfoOutput:
    def test_creation(self):
        output = ModelInfoOutput(
            provider="openai",
            model="gpt-4.1-mini",
            metadata={"context": 128000},
        )
        assert output.metadata["context"] == 128000
        assert output.mcp_schema_version == 1


class TestCostSummarySchemas:
    def test_input_defaults(self):
        inp = CostSummaryInput()
        assert inp.provider is None
        assert inp.model is None

    def test_output_defaults(self):
        output = CostSummaryOutput()
        assert output.total_cost_usd == 0.0
        assert output.total_calls == 0
        assert output.by_provider == {}


class TestValidateProviderSchemas:
    def test_input(self):
        inp = ValidateProviderInput(provider="openai")
        assert inp.provider == "openai"

    def test_output_defaults(self):
        output = ValidateProviderOutput(provider="openai", configured=True)
        assert output.models_available == []
        assert output.validation_errors == []


class TestEstimateCostSchemas:
    def test_input(self):
        inp = EstimateCostInput(
            provider="openai", model="gpt-4.1-mini", message_text="Hello"
        )
        assert inp.message_text == "Hello"

    def test_output(self):
        output = EstimateCostOutput(
            estimated_input_tokens=10,
            estimated_cost_usd=0.001,
            provider="openai",
            model="gpt-4.1-mini",
        )
        assert output.mcp_schema_version == 1


class TestListModelsInput:
    def test_creation(self):
        inp = ListModelsInput(provider="anthropic")
        assert inp.provider == "anthropic"


class TestModelInfoInput:
    def test_creation(self):
        inp = ModelInfoInput(provider="openai", model="gpt-4.1-mini")
        assert inp.model == "gpt-4.1-mini"


class TestMCPErrorCode:
    def test_all_codes_are_strings(self):
        for code in MCPErrorCode:
            assert isinstance(code.value, str)

    def test_expected_codes_exist(self):
        assert MCPErrorCode.AUTH_FAILED == "auth_failed"
        assert MCPErrorCode.INVALID_PROVIDER == "invalid_provider"
        assert MCPErrorCode.INVALID_MODEL == "invalid_model"
        assert MCPErrorCode.INTERNAL_ERROR == "internal_error"


class TestExceptionMap:
    def test_all_mapped_exceptions_resolve(self):
        for _exc_type, code in EXCEPTION_MAP.items():
            assert isinstance(code, MCPErrorCode)

    def test_auth_error_maps_correctly(self):
        assert EXCEPTION_MAP[AuthenticationError] == MCPErrorCode.AUTH_FAILED

    def test_invalid_provider_maps_correctly(self):
        assert EXCEPTION_MAP[InvalidProviderError] == MCPErrorCode.INVALID_PROVIDER

    def test_invalid_model_maps_correctly(self):
        assert EXCEPTION_MAP[InvalidModelError] == MCPErrorCode.INVALID_MODEL

    def test_budget_maps_correctly(self):
        assert EXCEPTION_MAP[BudgetExceededError] == MCPErrorCode.BUDGET_EXCEEDED

    def test_rate_limit_maps_correctly(self):
        assert EXCEPTION_MAP[RateLimitError] == MCPErrorCode.RATE_LIMITED

    def test_validation_maps_correctly(self):
        assert EXCEPTION_MAP[ValidationError] == MCPErrorCode.VALIDATION_ERROR


class TestMCPError:
    def test_basic_error(self):
        exc = InvalidProviderError("nonexistent")
        result = mcp_error(exc, provider="nonexistent")
        assert result["error_code"] == "invalid_provider"
        assert result["error_type"] == "InvalidProviderError"
        assert result["provider"] == "nonexistent"
        assert "model" not in result

    def test_with_model(self):
        exc = InvalidModelError("bad-model", "openai")
        result = mcp_error(exc, provider="openai", model="bad-model")
        assert result["error_code"] == "invalid_model"
        assert result["provider"] == "openai"
        assert result["model"] == "bad-model"

    def test_unknown_exception_maps_to_internal(self):
        exc = RuntimeError("unexpected")
        result = mcp_error(exc)
        assert result["error_code"] == "internal_error"
        assert result["error_type"] == "RuntimeError"

    def test_message_is_sanitized(self):
        exc = ProviderAPIError("Error with key sk-ant-abc123def456ghi789", "anthropic")
        result = mcp_error(exc, provider="anthropic")
        assert "sk-ant-" not in result["message"]

    def test_no_provider_or_model(self):
        exc = RuntimeError("oops")
        result = mcp_error(exc)
        assert "provider" not in result
        assert "model" not in result


class TestRaiseToolError:
    def test_raises_value_error(self):
        exc = InvalidProviderError("bad")
        with pytest.raises(ValueError) as exc_info:
            raise_tool_error(exc, provider="bad")
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_provider"

    def test_chains_original_exception(self):
        exc = RuntimeError("original")
        with pytest.raises(ValueError) as exc_info:
            raise_tool_error(exc)
        assert exc_info.value.__cause__ is exc
