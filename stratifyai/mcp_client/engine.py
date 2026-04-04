"""Top-level MCP Client Engine orchestrator."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.types import Tool

from ..models import ChatRequest, ChatResponse, Message
from .config import ConfiguredServer, load_enabled_servers
from .server_manager import ServerManager, ServerStatus
from .tool_registry import ToolDescriptor, ToolRegistry

_MAX_TOOL_CONTEXT_CHARS = 12_000


@dataclass(slots=True)
class ToolCallRequest:
    """One tool call requested by the model."""

    call_id: str | None
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolExecutionResult:
    """Structured record of one MCP tool execution."""

    call_id: str | None
    server_id: str
    tool_name: str
    namespace: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "server_id": self.server_id,
            "tool_name": self.tool_name,
            "namespace": self.namespace,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }

    def render_for_prompt(self) -> str:
        status = "error" if self.error else "ok"
        result_payload = self.error if self.error is not None else self.result
        return (
            f"Tool: {self.namespace}\n"
            f"Status: {status}\n"
            f"Arguments:\n{_render_tool_payload(self.arguments)}\n"
            f"Output:\n{_render_tool_payload(result_payload)}"
        )


def _render_tool_payload(value: Any) -> str:
    """Render tool payloads safely for conversation context."""
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
    if len(rendered) > _MAX_TOOL_CONTEXT_CHARS:
        return rendered[:_MAX_TOOL_CONTEXT_CHARS] + "\n... [truncated]"
    return rendered


class MCPClientEngine:
    """Manage MCP client server lifecycle and tool/resource calls."""

    def __init__(
        self,
        servers: list[ConfiguredServer] | None = None,
        client: str = "cursor",
        project_root: str | Path | None = None,
        output_path: str | Path | None = None,
    ) -> None:
        self._server_manager = ServerManager()
        self._tool_registry = ToolRegistry()
        self._servers = (
            servers
            if servers is not None
            else load_enabled_servers(
                client=client,
                project_root=project_root,
                output_path=output_path,
            )
        )
        self._server_index = {server.server_id: server for server in self._servers}

    async def start(self) -> None:
        """Start all enabled auto-start servers and register their tools."""
        for server in self._servers:
            if not server.enabled or not server.auto_start:
                continue
            await self.start_server(server.server_id)

    async def start_server(self, server_id: str) -> ServerStatus:
        """Start one configured server and register its tools.

        If tool discovery fails after a successful spawn, the server is
        stopped to avoid a half-initialized state (connected but no tools).
        """
        config = self._server_index.get(server_id)
        if config is None:
            raise KeyError(f"Unknown server: {server_id}")

        connection = await self._server_manager.spawn(config)
        try:
            tools_result = await connection.session.list_tools()
            self._tool_registry.register_server_tools(server_id, tools_result.tools)
        except Exception:
            await self._server_manager.stop(server_id)
            raise
        return self.get_server_status(server_id)

    async def stop(self) -> None:
        """Stop all running servers and clear tool registry state."""
        for server_id in list(self._server_index.keys()):
            await self.stop_server(server_id)

    async def stop_server(self, server_id: str) -> ServerStatus:
        """Stop one server and unregister its tools."""
        await self._server_manager.stop(server_id)
        self._tool_registry.unregister_server(server_id)
        return self.get_server_status(server_id)

    async def restart_server(self, server_id: str) -> ServerStatus:
        """Restart one server and refresh its tool registration."""
        config = self._server_index.get(server_id)
        if config is None:
            raise KeyError(f"Unknown server: {server_id}")

        self._tool_registry.unregister_server(server_id)
        connection = await self._server_manager.restart(config)
        tools_result = await connection.session.list_tools()
        self._tool_registry.register_server_tools(server_id, tools_result.tools)
        return self.get_server_status(server_id)

    async def build_tool_definitions(
        self,
        provider: str,
        active_servers: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Build provider-ready tool definitions for one chat session."""
        warnings: list[str] = []
        selected_servers = (
            [server.server_id for server in self._servers]
            if active_servers is None
            else list(active_servers)
        )
        descriptors: list[ToolDescriptor] = []
        seen_servers: set[str] = set()

        for server_id in selected_servers:
            if server_id in seen_servers:
                continue
            seen_servers.add(server_id)

            if server_id not in self._server_index:
                warnings.append(f"Unknown MCP server '{server_id}' was ignored.")
                continue

            status = self.get_server_status(server_id)
            if status.status != "connected":
                try:
                    await self.start_server(server_id)
                except Exception as exc:
                    warnings.append(
                        f"MCP server '{server_id}' is offline and was excluded: {exc}"
                    )
                    continue

            descriptors.extend(self._tool_registry.list_server_tools(server_id))

        return [
            self._format_tool_definition(provider, item) for item in descriptors
        ], warnings

    async def chat_with_mcp(
        self,
        llm_client: Any,
        provider: str,
        model: str,
        messages: list[Message],
        active_servers: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        max_tool_roundtrips: int = 3,
        **kwargs: Any,
    ) -> ChatResponse:
        """Run a chat completion with MCP tool-use support."""
        conversation = list(messages)
        all_warnings: list[str] = []
        tool_results: list[ToolExecutionResult] = []
        response: ChatResponse | None = None

        extra_params_input = kwargs.pop("extra_params", None)
        base_extra_params = (
            dict(extra_params_input) if isinstance(extra_params_input, dict) else {}
        )

        rounds = max(1, max_tool_roundtrips + 1)
        for _ in range(rounds):
            tool_definitions, warnings = await self.build_tool_definitions(
                provider=provider,
                active_servers=active_servers,
            )
            for warning in warnings:
                if warning not in all_warnings:
                    all_warnings.append(warning)

            request_extra_params = dict(base_extra_params)
            if tool_definitions:
                request_extra_params["tools"] = tool_definitions
                if provider != "anthropic":
                    request_extra_params.setdefault("tool_choice", "auto")

            request = ChatRequest(
                model=model,
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_params=request_extra_params,
                **kwargs,
            )
            response = await llm_client.chat_completion(request)

            pending_calls = self._extract_tool_requests(response)
            if not pending_calls or not tool_definitions:
                break

            executed_results = await self._execute_tool_requests(
                pending_calls,
                active_servers=active_servers,
            )
            tool_results.extend(executed_results)
            conversation.extend(
                self._build_followup_messages(response, executed_results)
            )

        if response is None:
            raise RuntimeError("MCP chat did not produce a response")

        if tool_results or all_warnings:
            response.raw_response = dict(response.raw_response)
            if tool_results:
                response.raw_response["mcp_tool_results"] = [
                    item.to_dict() for item in tool_results
                ]
            if all_warnings:
                response.raw_response["mcp_warnings"] = all_warnings
            response.raw_response["mcp_active_servers"] = (
                [server.server_id for server in self._servers]
                if active_servers is None
                else list(active_servers)
            )

        return response

    async def call_tool(self, server: str, tool: str, args: dict) -> dict:
        """Call one tool on a connected server."""
        connection = await self._require_connection(server)
        result = await connection.session.call_tool(tool, args)
        return dict(result.model_dump(mode="json"))

    async def get_resource(self, server: str, uri: str) -> str:
        """Read a resource URI on a connected server and normalize content."""
        connection = await self._require_connection(server)
        result = await connection.session.read_resource(uri)

        rendered: list[str] = []
        for item in result.contents:
            if hasattr(item, "text") and item.text is not None:
                rendered.append(str(item.text))
            elif hasattr(item, "blob") and item.blob is not None:
                rendered.append(str(item.blob))
            else:
                rendered.append(json.dumps(item.model_dump(mode="json"), indent=2))

        return "\n".join(rendered)

    def list_tools(self) -> list[ToolDescriptor]:
        """Return all discovered tools with server namespaces."""
        return list(self._tool_registry.list_all())

    def list_servers(self) -> list[ServerStatus]:
        """Return all known server statuses."""
        existing = {
            status.server_id: status for status in self._server_manager.list_statuses()
        }
        merged: list[ServerStatus] = []
        for server in self._servers:
            merged.append(
                existing.get(
                    server.server_id,
                    ServerStatus(server_id=server.server_id, status="stopped"),
                )
            )
        return merged

    def get_server_status(self, server: str) -> ServerStatus:
        """Get status for one server id."""
        for status in self.list_servers():
            if status.server_id == server:
                return status
        raise KeyError(f"Unknown server: {server}")

    def find_tool(self, server_id: str, tool_name: str) -> Tool | None:
        """Find one registered tool by server-local name."""
        return self._tool_registry.find_tool(server_id, tool_name)

    def _format_tool_definition(
        self,
        provider: str,
        descriptor: ToolDescriptor,
    ) -> dict[str, Any]:
        schema = descriptor.input_schema or {"type": "object", "properties": {}}
        if provider == "anthropic":
            return {
                "name": descriptor.namespace,
                "description": descriptor.description or "",
                "input_schema": schema,
            }
        return {
            "type": "function",
            "function": {
                "name": descriptor.namespace,
                "description": descriptor.description or "",
                "parameters": schema,
            },
        }

    def _extract_tool_requests(self, response: ChatResponse) -> list[ToolCallRequest]:
        raw_response = response.raw_response or {}
        requests: list[ToolCallRequest] = []

        if response.provider == "anthropic":
            for block in raw_response.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                arguments = block.get("input", {})
                if not isinstance(arguments, dict):
                    arguments = {}
                requests.append(
                    ToolCallRequest(
                        call_id=block.get("id"),
                        name=str(block.get("name", "")),
                        arguments=arguments,
                    )
                )
            return requests

        for choice in raw_response.get("choices", []):
            if not isinstance(choice, dict):
                continue
            message = choice.get("message", {})
            if not isinstance(message, dict):
                continue
            for tool_call in message.get("tool_calls", []) or []:
                if not isinstance(tool_call, dict):
                    continue
                function = tool_call.get("function", {})
                if not isinstance(function, dict):
                    continue
                arguments: dict[str, Any]
                raw_arguments = function.get("arguments", {})
                if isinstance(raw_arguments, str):
                    try:
                        parsed = json.loads(raw_arguments) if raw_arguments else {}
                    except json.JSONDecodeError:
                        parsed = {"raw": raw_arguments}
                    arguments = (
                        parsed if isinstance(parsed, dict) else {"value": parsed}
                    )
                elif isinstance(raw_arguments, dict):
                    arguments = raw_arguments
                else:
                    arguments = {}

                requests.append(
                    ToolCallRequest(
                        call_id=tool_call.get("id"),
                        name=str(function.get("name", "")),
                        arguments=arguments,
                    )
                )
        return requests

    async def _execute_tool_requests(
        self,
        requests: list[ToolCallRequest],
        active_servers: list[str] | None = None,
    ) -> list[ToolExecutionResult]:
        selected_servers = set(
            self._server_index.keys() if active_servers is None else active_servers
        )
        results: list[ToolExecutionResult] = []

        for request in requests:
            server_id, tool_name = self._resolve_tool_target(
                request.name, selected_servers
            )
            if server_id is None:
                results.append(
                    ToolExecutionResult(
                        call_id=request.call_id,
                        server_id="unknown",
                        tool_name=tool_name,
                        namespace=request.name,
                        arguments=request.arguments,
                        error=(
                            f"Unknown or inactive MCP tool '{request.name}'. "
                            "Ask for a namespaced tool from one of the active servers."
                        ),
                    )
                )
                continue

            start_time = time.perf_counter()
            try:
                result = await self.call_tool(server_id, tool_name, request.arguments)
                results.append(
                    ToolExecutionResult(
                        call_id=request.call_id,
                        server_id=server_id,
                        tool_name=tool_name,
                        namespace=f"{server_id}.{tool_name}",
                        arguments=request.arguments,
                        result=result,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                    )
                )
            except Exception as exc:
                results.append(
                    ToolExecutionResult(
                        call_id=request.call_id,
                        server_id=server_id,
                        tool_name=tool_name,
                        namespace=f"{server_id}.{tool_name}",
                        arguments=request.arguments,
                        error=str(exc),
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                    )
                )

        return results

    def _resolve_tool_target(
        self,
        tool_name: str,
        selected_servers: set[str],
    ) -> tuple[str | None, str]:
        server_id, _, local_name = tool_name.partition(".")
        if server_id and local_name:
            if selected_servers and server_id not in selected_servers:
                return None, local_name
            return server_id, local_name

        matches = [
            candidate
            for candidate in sorted(selected_servers)
            if self.find_tool(candidate, tool_name) is not None
        ]
        if len(matches) == 1:
            return matches[0], tool_name
        return None, tool_name

    def _build_followup_messages(
        self,
        response: ChatResponse,
        results: list[ToolExecutionResult],
    ) -> list[Message]:
        assistant_content = response.content.strip()
        if not assistant_content:
            assistant_content = "I used MCP tools to gather more information."

        rendered_results = "\n\n".join(result.render_for_prompt() for result in results)
        user_content = (
            "Tool results from the MCP client engine are available below.\n\n"
            f"{rendered_results}\n\n"
            "Use these results to answer the original request. "
            "If you still need another tool, request it using the available tool definitions."
        )

        return [
            Message(role="assistant", content=assistant_content),
            Message(role="user", content=user_content),
        ]

    async def _require_connection(self, server_id: str):
        connection = self._server_manager.get_connection(server_id)
        if connection is None:
            config = self._server_index.get(server_id)
            if config is None:
                raise KeyError(f"Unknown server: {server_id}")
            connection = await self._server_manager.spawn(config)
            tools_result = await connection.session.list_tools()
            self._tool_registry.register_server_tools(server_id, tools_result.tools)
        return connection
