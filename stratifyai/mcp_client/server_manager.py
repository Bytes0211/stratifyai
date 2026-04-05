"""Server process lifecycle manager for MCP client engine."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .config import ConfiguredServer
from .connection import MCPServerConnection


@dataclass(slots=True)
class ServerStatus:
    """Live status and diagnostics for a configured server."""

    server_id: str
    status: str
    error: str | None = None
    transport: str = "stdio"
    latency_ms: float | None = None
    last_checked_at: float | None = None
    last_connected_at: float | None = None


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
        now = time.time()
        self._statuses[config.server_id] = ServerStatus(
            server_id=config.server_id,
            status="starting",
            transport="stdio",
            last_checked_at=now,
        )

        try:
            await connection.connect()
            self._connections[config.server_id] = connection
            self._statuses[config.server_id] = ServerStatus(
                server_id=config.server_id,
                status="connected",
                transport="stdio",
                last_checked_at=now,
                last_connected_at=now,
            )
            return connection
        except Exception as exc:
            self._statuses[config.server_id] = ServerStatus(
                server_id=config.server_id,
                status="error",
                error=str(exc),
                transport="stdio",
                last_checked_at=now,
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

    async def check_health(self, server_id: str) -> ServerStatus:
        """Probe a running server and update its diagnostics metadata."""
        existing = self._statuses.get(
            server_id,
            ServerStatus(server_id=server_id, status="stopped"),
        )
        connection = self._connections.get(server_id)
        now = time.time()

        if connection is None:
            self._statuses[server_id] = ServerStatus(
                server_id=server_id,
                status=existing.status,
                error=existing.error,
                transport=existing.transport,
                last_checked_at=now,
                last_connected_at=existing.last_connected_at,
            )
            return self._statuses[server_id]

        try:
            latency_ms = await connection.probe()
            self._statuses[server_id] = ServerStatus(
                server_id=server_id,
                status="connected",
                error=None,
                transport=existing.transport,
                latency_ms=latency_ms,
                last_checked_at=now,
                last_connected_at=existing.last_connected_at or now,
            )
        except Exception as exc:
            await connection.close()
            self._connections.pop(server_id, None)
            self._statuses[server_id] = ServerStatus(
                server_id=server_id,
                status="error",
                error=str(exc),
                transport=existing.transport,
                last_checked_at=now,
                last_connected_at=existing.last_connected_at,
            )

        return self._statuses[server_id]

    def get_connection(self, server_id: str) -> MCPServerConnection | None:
        return self._connections.get(server_id)

    def is_running(self, server_id: str) -> bool:
        return server_id in self._connections

    def list_statuses(self) -> list[ServerStatus]:
        return [self._statuses[key] for key in sorted(self._statuses)]
