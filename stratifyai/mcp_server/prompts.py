"""MCP prompt registrations — expose prompt templates as MCP prompts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from stratifyai.prompts import registry


def register(mcp: FastMCP) -> None:
    """Register all MCP prompts on the server instance."""

    # ------------------------------------------------------------------
    # Named prompts
    # ------------------------------------------------------------------

    @mcp.prompt()
    def compare_models(models: str) -> str:
        """Compare multiple LLM models side by side.

        Args:
            models: Comma-separated list of provider/model pairs
                    (e.g. "openai/gpt-4.1,anthropic/claude-sonnet-4-5")
        """
        model_list = [m.strip() for m in models.split(",")]
        formatted = "\n".join(f"- {m}" for m in model_list)
        return (
            f"Compare the following LLM models across key dimensions "
            f"(capabilities, pricing, context window, speed, quality):\n\n{formatted}\n\n"
            f"Provide a structured comparison table and recommend which model "
            f"is best for different use cases."
        )

    @mcp.prompt()
    def recommend_model(
        task_description: str,
        budget: str | None = None,
        priority: str | None = None,
    ) -> str:
        """Recommend the best LLM model for a specific task.

        Args:
            task_description: Description of the task to accomplish
            budget: Optional budget constraint (e.g. "low", "$0.01 per request")
            priority: Optional priority — cost, quality, or latency
        """
        parts = [
            f"Recommend the best LLM model for the following task:\n\n{task_description}"
        ]
        if budget:
            parts.append(f"\nBudget constraint: {budget}")
        if priority:
            parts.append(f"\nPriority: {priority}")
        parts.append(
            "\n\nConsider the available providers (OpenAI, Anthropic, Google, DeepSeek, "
            "Groq, Grok, OpenRouter, Ollama, Bedrock) and their models. "
            "Explain your reasoning."
        )
        return "\n".join(parts)

    @mcp.prompt()
    def analyze_costs(time_period: str | None = None) -> str:
        """Generate a cost analysis prompt for the current session.

        Args:
            time_period: Optional time period filter (e.g. "last hour", "today")
        """
        prompt = "Analyze the LLM usage costs for the current session."
        if time_period:
            prompt += f" Focus on the period: {time_period}."
        prompt += (
            "\n\nUse the `get_cost_summary` tool to retrieve current cost data, "
            "then provide:\n"
            "1. Total spend breakdown by provider and model\n"
            "2. Cost per request average\n"
            "3. Recommendations for cost optimization"
        )
        return prompt

    # ------------------------------------------------------------------
    # Dynamic prompts from registry templates
    # ------------------------------------------------------------------

    for template in registry.list():
        _register_template_prompt(mcp, template)


def _register_template_prompt(mcp: FastMCP, template: object) -> None:
    """Register a single prompt template from the registry as an MCP prompt."""
    name = getattr(template, "name", "")
    description = getattr(template, "description", "")
    system_template = getattr(template, "system", "")
    user_template = getattr(template, "user", "")

    @mcp.prompt(name=f"template_{name}", description=description)
    def template_prompt(**kwargs: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_template:
            try:
                messages.append(
                    {"role": "system", "content": system_template.format(**kwargs)}
                )
            except KeyError:
                messages.append({"role": "system", "content": system_template})
        if user_template:
            try:
                messages.append(
                    {"role": "user", "content": user_template.format(**kwargs)}
                )
            except KeyError:
                messages.append({"role": "user", "content": user_template})
        return messages
