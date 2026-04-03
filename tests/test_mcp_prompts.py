"""Tests for MCP prompt registrations."""

from stratifyai.mcp_server.server import mcp


def _get_prompt(name: str):
    """Get a registered MCP prompt function by name."""
    return mcp._prompt_manager._prompts[name].fn


class TestNamedPrompts:
    def test_compare_models_returns_string(self):
        result = _get_prompt("compare_models")(
            models="openai/gpt-4.1,anthropic/claude-sonnet-4-5"
        )
        assert isinstance(result, str)
        assert "openai/gpt-4.1" in result
        assert "anthropic/claude-sonnet-4-5" in result
        assert "Compare" in result

    def test_recommend_model_basic(self):
        result = _get_prompt("recommend_model")(
            task_description="Summarize a 10-page legal document"
        )
        assert isinstance(result, str)
        assert "Summarize" in result

    def test_recommend_model_with_budget(self):
        result = _get_prompt("recommend_model")(
            task_description="Code review", budget="low"
        )
        assert "budget" in result.lower() or "Budget" in result

    def test_recommend_model_with_priority(self):
        result = _get_prompt("recommend_model")(
            task_description="Chat", priority="cost"
        )
        assert "cost" in result.lower() or "Priority" in result

    def test_analyze_costs_basic(self):
        result = _get_prompt("analyze_costs")()
        assert isinstance(result, str)
        assert "cost" in result.lower()

    def test_analyze_costs_with_period(self):
        result = _get_prompt("analyze_costs")(time_period="last hour")
        assert "last hour" in result


class TestDynamicTemplatePrompts:
    def test_template_prompts_registered(self):
        registered = list(mcp._prompt_manager._prompts.keys())
        template_prompts = [n for n in registered if n.startswith("template_")]
        assert len(template_prompts) >= 5  # at least some built-in templates

    def test_template_prompt_returns_messages(self):
        # Find any template prompt
        registered = list(mcp._prompt_manager._prompts.keys())
        template_names = [n for n in registered if n.startswith("template_")]
        assert len(template_names) > 0

        # Call the first template prompt
        fn = _get_prompt(template_names[0])
        result = fn()
        assert isinstance(result, list)
        for msg in result:
            assert "role" in msg
            assert "content" in msg

    def test_code_review_template_exists(self):
        assert "template_code_review" in mcp._prompt_manager._prompts

    def test_summarize_template_exists(self):
        assert "template_summarize" in mcp._prompt_manager._prompts


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
