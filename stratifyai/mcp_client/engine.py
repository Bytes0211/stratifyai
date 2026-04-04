"""Top-level MCP Client Engine orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

from .config import ConfiguredServer, load_enabled_servers
from .server_manager import ServerManager, ServerStatus
from .tool_registry import ToolDescriptor, ToolRegistry


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
            connection = await self._server_manager.spawn(server)
            tools_result = await connection.session.list_tools()
            self._tool_registry.register_server_tools(
                server.server_id, tools_result.tools
            )

    async def stop(self) -> None:
        """Stop all running servers and clear tool registry state."""
        for server_id in list(self._server_index.keys()):
            await self._server_manager.stop(server_id)
            self._tool_registry.unregister_server(server_id)

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
