"""Permission evaluation and safety defaults for the MCP client engine."""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatchcase
from typing import Any

from mcp.types import Tool


class PermissionMode(str, Enum):
    """Supported permission modes for MCP tool execution."""

    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


@dataclass(slots=True)
class PermissionDecision:
    """Outcome of evaluating one MCP tool call."""

    mode: PermissionMode
    reason: str
    matched_pattern: str | None = None


@dataclass(slots=True)
class ServerPermissionConfig:
    """Per-server allow/deny/confirm rules."""

    default_mode: PermissionMode | None = None
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    confirm: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ServerPermissionConfig:
        """Build a config object from JSON-compatible data."""
        if not isinstance(data, dict):
            return cls()

        default_mode: PermissionMode | None = None
        raw_mode = data.get("default_mode") or data.get("default")
        if isinstance(raw_mode, str) and raw_mode.strip():
            try:
                default_mode = PermissionMode(raw_mode.strip().lower())
            except ValueError:
                default_mode = None

        return cls(
            default_mode=default_mode,
            allow=_coerce_string_list(data.get("allow")),
            deny=_coerce_string_list(data.get("deny")),
            confirm=_coerce_string_list(data.get("confirm")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the config back to JSON-compatible data."""
        payload: dict[str, Any] = {}
        if self.default_mode is not None:
            payload["default_mode"] = self.default_mode.value
        if self.allow:
            payload["allow"] = list(self.allow)
        if self.deny:
            payload["deny"] = list(self.deny)
        if self.confirm:
            payload["confirm"] = list(self.confirm)
        return payload


ToolConfirmationHandler = Callable[
    [str, str, dict[str, Any], PermissionDecision], bool | Awaitable[bool]
]


class MCPPermissionError(PermissionError):
    """Raised when an MCP tool call is blocked by policy."""


class MCPConfirmationRequiredError(MCPPermissionError):
    """Raised when an MCP tool needs interactive approval before execution."""


_READ_ONLY_KEYWORDS = {
    "fetch",
    "find",
    "get",
    "head",
    "inspect",
    "list",
    "peek",
    "preview",
    "query",
    "read",
    "search",
    "show",
    "status",
    "view",
}

_CONFIRM_KEYWORDS = {
    "append",
    "apply",
    "close",
    "copy",
    "create",
    "delete",
    "deploy",
    "drop",
    "edit",
    "insert",
    "merge",
    "modify",
    "move",
    "post",
    "publish",
    "push",
    "remove",
    "rename",
    "replace",
    "restart",
    "run",
    "send",
    "stop",
    "truncate",
    "unlink",
    "update",
    "upload",
    "write",
}


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _matches_pattern(tool_name: str, namespace: str, pattern: str) -> bool:
    lowered_pattern = pattern.strip().lower()
    if not lowered_pattern:
        return False

    return fnmatchcase(tool_name.lower(), lowered_pattern) or fnmatchcase(
        namespace.lower(), lowered_pattern
    )


class PermissionManager:
    """Evaluate allow/deny/confirm rules for MCP tools."""

    def __init__(
        self,
        server_policies: dict[str, ServerPermissionConfig] | None = None,
    ) -> None:
        self._server_policies = server_policies or {}

    def get_policy(self, server_id: str) -> ServerPermissionConfig:
        """Return the configured policy for one server, or a permissive default."""
        return self._server_policies.get(server_id, ServerPermissionConfig())

    def set_policy(self, server_id: str, policy: ServerPermissionConfig) -> None:
        """Update the policy for one server."""
        self._server_policies[server_id] = policy

    def evaluate(
        self,
        server_id: str,
        tool_name: str,
        tool: Tool | None = None,
    ) -> PermissionDecision:
        """Evaluate one tool against explicit rules and safety defaults."""
        policy = self.get_policy(server_id)
        namespace = f"{server_id}.{tool_name}"

        for pattern in policy.deny:
            if _matches_pattern(tool_name, namespace, pattern):
                return PermissionDecision(
                    mode=PermissionMode.DENY,
                    reason=(f"Blocked by MCP deny rule '{pattern}' for '{namespace}'."),
                    matched_pattern=pattern,
                )

        for pattern in policy.confirm:
            if _matches_pattern(tool_name, namespace, pattern):
                return PermissionDecision(
                    mode=PermissionMode.CONFIRM,
                    reason=(
                        f"'{namespace}' requires confirmation due to MCP rule '{pattern}'."
                    ),
                    matched_pattern=pattern,
                )

        for pattern in policy.allow:
            if _matches_pattern(tool_name, namespace, pattern):
                return PermissionDecision(
                    mode=PermissionMode.ALLOW,
                    reason=(
                        f"Allowed by MCP allow rule '{pattern}' for '{namespace}'."
                    ),
                    matched_pattern=pattern,
                )

        if policy.allow:
            return PermissionDecision(
                mode=PermissionMode.DENY,
                reason=(
                    f"'{namespace}' is not on the configured MCP allow list for '{server_id}'."
                ),
            )

        if policy.default_mode is not None:
            return PermissionDecision(
                mode=policy.default_mode,
                reason=(
                    f"Using default MCP permission '{policy.default_mode.value}' for '{namespace}'."
                ),
            )

        return self._evaluate_safety_default(server_id, tool_name, tool)

    async def authorize(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        tool: Tool | None = None,
        confirmation_handler: ToolConfirmationHandler | None = None,
    ) -> PermissionDecision:
        """Authorize one tool call, invoking a confirmation callback when needed."""
        decision = self.evaluate(server_id, tool_name, tool)
        namespace = f"{server_id}.{tool_name}"

        if decision.mode == PermissionMode.DENY:
            raise MCPPermissionError(decision.reason)

        if decision.mode != PermissionMode.CONFIRM:
            return decision

        if confirmation_handler is None:
            raise MCPConfirmationRequiredError(
                f"MCP tool '{namespace}' requires confirmation before execution."
            )

        approved = confirmation_handler(server_id, tool_name, arguments, decision)
        if inspect.isawaitable(approved):
            approved = await approved

        if not approved:
            raise MCPPermissionError(
                f"User declined confirmation for MCP tool '{namespace}'."
            )

        return decision

    def _evaluate_safety_default(
        self,
        server_id: str,
        tool_name: str,
        tool: Tool | None,
    ) -> PermissionDecision:
        namespace = f"{server_id}.{tool_name}"
        annotations = getattr(tool, "annotations", None)
        read_only_hint = getattr(annotations, "readOnlyHint", None)
        destructive_hint = getattr(annotations, "destructiveHint", None)

        if destructive_hint is True:
            return PermissionDecision(
                mode=PermissionMode.CONFIRM,
                reason=(
                    f"'{namespace}' is treated as a write/destructive tool by MCP annotations."
                ),
            )

        if read_only_hint is True:
            return PermissionDecision(
                mode=PermissionMode.ALLOW,
                reason=f"'{namespace}' is marked read-only by MCP annotations.",
            )

        description = getattr(tool, "description", None) or ""
        haystack = f"{tool_name} {description}".lower()

        if re.search(r"\bread(?:-|\s)?only\b", haystack):
            return PermissionDecision(
                mode=PermissionMode.ALLOW,
                reason=(
                    f"'{namespace}' is explicitly described as read-only, so it is auto-approved."
                ),
            )

        if any(re.search(rf"\b{keyword}\b", haystack) for keyword in _CONFIRM_KEYWORDS):
            return PermissionDecision(
                mode=PermissionMode.CONFIRM,
                reason=(
                    f"'{namespace}' may change external state, so it requires confirmation."
                ),
            )

        if any(
            re.search(rf"\b{keyword}\b", haystack) for keyword in _READ_ONLY_KEYWORDS
        ):
            return PermissionDecision(
                mode=PermissionMode.ALLOW,
                reason=f"'{namespace}' looks read-only, so it is auto-approved.",
            )

        # Fail-closed: unknown tools require confirmation rather than auto-allow
        return PermissionDecision(
            mode=PermissionMode.CONFIRM,
            reason=f"'{namespace}' did not match any known patterns and requires confirmation.",
        )
