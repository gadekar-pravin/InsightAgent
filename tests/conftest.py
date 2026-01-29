"""
Pytest configuration for InsightAgent tests.
"""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require RUN_INTEGRATION_TESTS=1)"
    )
