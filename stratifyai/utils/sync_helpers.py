"""Helpers for safe sync wrappers around async APIs."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine


def run_sync(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine synchronously, safe from nested event loops."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
