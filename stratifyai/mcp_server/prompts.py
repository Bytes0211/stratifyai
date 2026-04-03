"""MCP prompt registrations — expose prompt templates as MCP prompts."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from stratifyai.prompts import registry


def register(mcp: FastMCP) -> None:
    """Register all MCP prompts on the server instance."""

    # ------------------------------------------------------------------
    # Named prompts
    # ------------------------------------------------------------------

    @mcp.prompt()
    def compare_models(models: list[str] | str) -> list[dict[str, str]]:
        """Compare multiple LLM models side by side.

        Args:
            models: List (or comma-separated string) of provider/model pairs
                    (e.g. ["openai/gpt-4.1", "anthropic/claude-sonnet-4-5"])
        """
        if isinstance(models, str):
            model_list = [m.strip() for m in models.split(",") if m.strip()]
        else:
            model_list = [m.strip() for m in models if m.strip()]
        formatted = "\n".join(f"- {m}" for m in model_list)
        return [
            {
                "role": "system",
                "content": (
                    "You are an expert model selection assistant. Compare models "
                    "objectively across capability, cost, context window, speed, "
                    "and output quality."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Compare the following models and provide a structured summary:\n\n"
                    f"{formatted}\n\n"
                    "Include tradeoffs and recommendations for common use cases."
                ),
            },
        ]

    @mcp.prompt()
    def recommend_model(
        task_description: str,
        budget: str | None = None,
        priority: str | None = None,
    ) -> list[dict[str, str]]:
        """Recommend the best LLM model for a specific task.

        Args:
            task_description: Description of the task to accomplish
            budget: Optional budget constraint (e.g. "low", "$0.01 per request")
            priority: Optional priority — cost, quality, or latency
        """
        parts = [f"Task:\n{task_description}"]
        if budget:
            parts.append(f"Budget constraint: {budget}")
        if priority:
            parts.append(f"Priority: {priority}")
        parts.append("Provide the top recommendation and one lower-cost fallback.")

        return [
            {
                "role": "system",
                "content": (
                    "You are a routing and cost-aware model advisor for StratifyAI."
                ),
            },
            {
                "role": "user",
                "content": "\n".join(parts),
            },
        ]

    @mcp.prompt()
    def analyze_costs(time_period: str | None = None) -> list[dict[str, str]]:
        """Generate a cost analysis prompt for the current session.

        Args:
            time_period: Optional time period filter (e.g. "last hour", "today")
        """
        prompt = "Analyze LLM usage costs for the current session."
        if time_period:
            prompt += f" Focus on the period: {time_period}."
        prompt += (
            "\n\nUse the get_cost_summary tool, then provide:\n"
            "1. Spend breakdown by provider and model\n"
            "2. Cost per request estimate\n"
            "3. Actionable optimization recommendations"
        )
        return [
            {
                "role": "system",
                "content": "You are a cost optimization analyst for LLM workloads.",
            },
            {"role": "user", "content": prompt},
        ]

    # ------------------------------------------------------------------
    # Dynamic prompts from registry templates
    # ------------------------------------------------------------------

    for template in registry.list():
        _register_template_prompt(mcp, template.name, template.description)


def _register_template_prompt(
    mcp: FastMCP,
    template_name: str,
    description: str,
) -> None:
    """Register a single prompt template from the registry as an MCP prompt."""

    @mcp.prompt(name=template_name, description=description)
    def template_prompt(**kwargs: Any) -> list[dict[str, str]]:
        template = registry.get(template_name)

        # Provide placeholder values for missing required parameters so prompts
        # remain discoverable/callable even without explicit args.
        params = {param.name: kwargs.get(param.name) for param in template.parameters}
        for param in template.parameters:
            if params[param.name] is None:
                if param.default is not None:
                    params[param.name] = param.default
                elif param.required:
                    params[param.name] = f"<{param.name}>"

        rendered = template.render(**params)
        return [{"role": msg.role, "content": msg.content} for msg in rendered]
