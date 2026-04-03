"""Tests for MCP prompt registrations."""

from stratifyai.mcp_server.server import mcp


def _get_prompt(name: str):
    """Get a registered MCP prompt function by name."""
    return mcp._prompt_manager._prompts[name].fn


class TestNamedPrompts:
    def test_compare_models_returns_messages(self):
        result = _get_prompt("compare_models")(
            models="openai/gpt-4.1,anthropic/claude-sonnet-4-5"
        )
        assert isinstance(result, list)
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert "openai/gpt-4.1" in result[1]["content"]
        assert "anthropic/claude-sonnet-4-5" in result[1]["content"]

    def test_recommend_model_basic(self):
        result = _get_prompt("recommend_model")(
            task_description="Summarize a 10-page legal document"
        )
        assert isinstance(result, list)
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert "Summarize" in result[1]["content"]

    def test_recommend_model_with_budget(self):
        result = _get_prompt("recommend_model")(
            task_description="Code review", budget="low"
        )
        assert "budget" in result[1]["content"].lower()

    def test_recommend_model_with_priority(self):
        result = _get_prompt("recommend_model")(
            task_description="Chat", priority="cost"
        )
        assert "priority" in result[1]["content"].lower()
        assert "cost" in result[1]["content"].lower()

    def test_analyze_costs_basic(self):
        result = _get_prompt("analyze_costs")()
        assert isinstance(result, list)
        assert "cost" in result[1]["content"].lower()

    def test_analyze_costs_with_period(self):
        result = _get_prompt("analyze_costs")(time_period="last hour")
        assert "last hour" in result[1]["content"]


class TestDynamicTemplatePrompts:
    def test_template_prompts_registered(self):
        registered = list(mcp._prompt_manager._prompts.keys())
        named_prompts = {"compare_models", "recommend_model", "analyze_costs"}
        dynamic_prompts = [n for n in registered if n not in named_prompts]
        assert len(dynamic_prompts) >= 10

    def test_template_prompt_returns_messages(self):
        fn = _get_prompt("code_review")
        result = fn()
        assert isinstance(result, list)
        assert len(result) >= 1
        for msg in result:
            assert "role" in msg
            assert "content" in msg

    def test_code_review_template_exists(self):
        assert "code_review" in mcp._prompt_manager._prompts

    def test_summarize_template_exists(self):
        assert "summarize" in mcp._prompt_manager._prompts


class TestPromptRegistration:
    def test_named_prompts_registered(self):
        expected = ["compare_models", "recommend_model", "analyze_costs"]
        registered = list(mcp._prompt_manager._prompts.keys())
        for name in expected:
            assert name in registered, f"Prompt '{name}' not registered"

    def test_total_prompt_count(self):
        registered = list(mcp._prompt_manager._prompts.keys())
        # 3 named + at least 10 dynamic templates
        assert len(registered) >= 13
