"""Shared test fixtures."""

import pytest

from stratifyai.client import _provider_pool


@pytest.fixture(autouse=True)
def _clear_provider_pool():
    """Ensure no pooled providers leak between tests."""
    _provider_pool.clear()
    yield
    _provider_pool.clear()
