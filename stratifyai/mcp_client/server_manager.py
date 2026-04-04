"""Server process lifecycle manager for MCP client engine."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ConfiguredServer
from .connection import MCPServerConnection


@dataclass(slots=True)
class ServerStatus:
    """Live status for a configured server."""

    server_id: str
    status: str
    error: str | None = None


class ServerManager:
    """Spawn/connect/stop stdio MCP servers and track state."""

    def __init__(self) -> None:
        self._connections: dict[str, MCPServerConnection] = {}
        self._statuses: dict[str, ServerStatus] = {}

    async def spawn(self, config: ConfiguredServer) -> MCPServerConnection:
        existing = self._connections.get(config.server_id)
        if existing is not None:
            return existing

        connection = MCPServerConnection(config)
        self._statuses[config.server_id] = ServerStatus(
            server_id=config.server_id,
            status="starting",
        )

        try:
            await connection.connect()
            self._connections[config.server_id] = connection
            self._statuses[config.server_id] = ServerStatus(
                server_id=config.server_id,
                status="connected",
            )
            return connection
        except Exception as exc:
            self._statuses[config.server_id] = ServerStatus(
                server_id=config.server_id,
                status="error",
                error=str(exc),
            )
            await connection.close()
            raise

    async def stop(self, server_id: str) -> None:
        connection = self._connections.pop(server_id, None)
        if connection is None:
            self._statuses[server_id] = ServerStatus(
                server_id=server_id, status="stopped"
            )
            return

        await connection.close()
        self._statuses[server_id] = ServerStatus(server_id=server_id, status="stopped")

    async def restart(self, config: ConfiguredServer) -> MCPServerConnection:
        await self.stop(config.server_id)
        return await self.spawn(config)

    def get_connection(self, server_id: str) -> MCPServerConnection | None:
        return self._connections.get(server_id)

    def is_running(self, server_id: str) -> bool:
        return server_id in self._connections

    def list_statuses(self) -> list[ServerStatus]:
        return [self._statuses[key] for key in sorted(self._statuses)]
