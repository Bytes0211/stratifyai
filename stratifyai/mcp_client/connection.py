"""MCP stdio session connection wrapper."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from .config import ConfiguredServer

logger = logging.getLogger(__name__)


class MCPServerConnection:
    """Manage one connected stdio ClientSession lifecycle.

    The MCP SDK's ``stdio_client`` uses anyio task groups that must be entered
    and exited in the **same** asyncio task.  To satisfy this constraint the
    connection is owned by a dedicated background task that lives for the full
    session lifetime.  ``connect()`` launches that task and waits until the
    session is ready;  ``close()`` signals the task to tear down cleanly.
    """

    def __init__(self, config: ConfiguredServer):
        self.config = config
        self._session: ClientSession | None = None
        self._close_event: asyncio.Event | None = None
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._ready: asyncio.Event | None = None
        self._connect_error: BaseException | None = None

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

        self._close_event = asyncio.Event()
        self._ready = asyncio.Event()
        self._connect_error = None
        self._task = asyncio.create_task(
            self._run(), name=f"mcp-conn-{self.config.server_id}"
        )

        # Wait for the background task to signal that the session is ready
        # or that it failed during setup.
        await self._ready.wait()

        if self._connect_error is not None:
            raise self._connect_error

        return self.session

    async def _run(self) -> None:
        """Background task that owns the stdio_client context."""
        assert self._close_event is not None
        assert self._ready is not None

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env or None,
            cwd=self.config.cwd,
        )

        try:
            stack = AsyncExitStack()
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            self._session = session
            self._ready.set()

            # Keep the context alive until close() signals us.
            await self._close_event.wait()
        except BaseException as exc:
            self._connect_error = exc
            self._ready.set()
        finally:
            self._session = None
            try:
                await stack.aclose()
            except Exception:
                logger.debug(
                    "Suppressed error closing MCP connection for %s",
                    self.config.server_id,
                    exc_info=True,
                )

    async def probe(self) -> float:
        """Perform a lightweight health probe and return latency in milliseconds."""
        start = time.perf_counter()
        await self.session.list_tools()
        return (time.perf_counter() - start) * 1000

    async def close(self) -> None:
        if self._close_event is not None:
            self._close_event.set()

        task = self._task
        self._task = None

        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, Exception):
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        self._session = None
        self._close_event = None
        self._ready = None
