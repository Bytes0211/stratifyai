"""MCP stdio session connection wrapper."""

from __future__ import annotations

import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from .config import ConfiguredServer


class MCPServerConnection:
    """Manage one connected stdio ClientSession lifecycle."""

    def __init__(self, config: ConfiguredServer):
        self.config = config
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError(
                f"Session not initialized for server '{self.config.server_id}'"
            )
        return self._session

    async def connect(self) -> ClientSession:
        if self._session is not None:
            return self._session

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env or None,
            cwd=self.config.cwd,
        )

        stack = AsyncExitStack()
        read_stream, write_stream = await stack.enter_async_context(
            stdio_client(server_params)
        )
        session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._stack = stack
        self._session = session
        return session

    async def probe(self) -> float:
        """Perform a lightweight health probe and return latency in milliseconds."""
        start = time.perf_counter()
        await self.session.list_tools()
        return (time.perf_counter() - start) * 1000

    async def close(self) -> None:
        stack = self._stack
        self._session = None
        self._stack = None

        if stack is not None:
            await stack.aclose()
