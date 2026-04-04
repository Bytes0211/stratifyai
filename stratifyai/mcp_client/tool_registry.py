"""Server-namespaced tool registry for MCP client engine."""

from __future__ import annotations

from dataclasses import dataclass

from mcp.types import Tool


@dataclass(slots=True)
class ToolDescriptor:
    """Unified view of one tool across a connected server."""

    server_id: str
    tool_name: str
    namespace: str
    description: str | None
    input_schema: dict


class ToolRegistry:
    """Maintain a merged server-namespaced tool map."""

    def __init__(self) -> None:
        self._tools_by_server: dict[str, dict[str, Tool]] = {}

    def register_server_tools(self, server_id: str, tools: list[Tool]) -> None:
        self._tools_by_server[server_id] = {tool.name: tool for tool in tools}

    def unregister_server(self, server_id: str) -> None:
        self._tools_by_server.pop(server_id, None)

    def find_tool(self, server_id: str, tool_name: str) -> Tool | None:
        return self._tools_by_server.get(server_id, {}).get(tool_name)

    def find_by_namespace(self, namespace: str) -> Tool | None:
        server_id, _, tool_name = namespace.partition(".")
        if not server_id or not tool_name:
            return None
        return self.find_tool(server_id, tool_name)

    def list_server_tools(self, server_id: str) -> list[ToolDescriptor]:
        tools = self._tools_by_server.get(server_id, {})
        return [
            ToolDescriptor(
                server_id=server_id,
                tool_name=tool_name,
                namespace=f"{server_id}.{tool_name}",
                description=tool.description,
                input_schema=dict(tool.inputSchema),
            )
            for tool_name, tool in sorted(tools.items())
        ]

    def list_all(self) -> list[ToolDescriptor]:
        descriptors: list[ToolDescriptor] = []
        for server_id in sorted(self._tools_by_server):
            descriptors.extend(self.list_server_tools(server_id))
        return descriptors
