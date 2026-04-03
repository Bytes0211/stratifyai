"""Pydantic schemas for MCP tool inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

MCP_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class MessageParam(BaseModel):
    role: str
    content: str


# ---------------------------------------------------------------------------
# chat_completion
# ---------------------------------------------------------------------------


class ChatCompletionInput(BaseModel):
    provider: str
    model: str
    messages: list[MessageParam]
    temperature: float | None = None
    max_tokens: int | None = None


class ChatCompletionOutput(BaseModel):
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float | None = None
    mcp_schema_version: int = MCP_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# chat_with_routing
# ---------------------------------------------------------------------------


class ChatWithRoutingInput(BaseModel):
    messages: list[MessageParam]
    strategy: str = "hybrid"
    capabilities: list[str] | None = None
    preferred_providers: list[str] | None = None
    excluded_providers: list[str] | None = None
    max_cost_usd: float | None = None
    max_latency_ms: float | None = None


class ChatWithRoutingOutput(BaseModel):
    selected_provider: str
    selected_model: str
    routing_strategy: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float | None = None
    mcp_schema_version: int = MCP_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# list_providers
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    provider: str
    model_count: int
    configured: bool


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------


class ListModelsInput(BaseModel):
    provider: str


class ModelSummary(BaseModel):
    model_id: str
    context_window: int = 0
    cost_input_per_1m: float = 0.0
    cost_output_per_1m: float = 0.0
    capabilities: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------


class ModelInfoInput(BaseModel):
    provider: str
    model: str


class ModelInfoOutput(BaseModel):
    provider: str
    model: str
    metadata: dict
    mcp_schema_version: int = MCP_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# get_cost_summary
# ---------------------------------------------------------------------------


class CostSummaryInput(BaseModel):
    provider: str | None = None
    model: str | None = None


class CostSummaryOutput(BaseModel):
    total_cost_usd: float = 0.0
    total_calls: int = 0
    total_tokens: int = 0
    by_provider: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)
    mcp_schema_version: int = MCP_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# validate_provider
# ---------------------------------------------------------------------------


class ValidateProviderInput(BaseModel):
    provider: str


class ValidateProviderOutput(BaseModel):
    provider: str
    configured: bool
    models_available: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    mcp_schema_version: int = MCP_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


class EstimateCostInput(BaseModel):
    provider: str
    model: str
    message_text: str


class EstimateCostOutput(BaseModel):
    estimated_input_tokens: int = 0
    estimated_cost_usd: float = 0.0
    provider: str
    model: str
    mcp_schema_version: int = MCP_SCHEMA_VERSION
