"""Detect whether the optional langchain-core dependency is installed."""

from __future__ import annotations

try:  # pragma: no cover - exercised via availability-dependent tests
    import langchain_core  # noqa: F401

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
