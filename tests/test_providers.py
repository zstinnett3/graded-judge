"""
Providers: mock returns canned response; no real API calls in tests.
"""

import pytest
from graded_judge.providers import MockProvider


def test_mock_provider_returns_canned_response():
    """MockProvider returns configured response text and latency."""
    p = MockProvider(response_text="Hello", latency_ms=5.0)
    text, cost, latency = p.complete(prompt="Hi", model="mock", max_tokens=10)
    assert text == "Hello"
    assert cost == 0.0
    assert latency == 5.0
    assert p.name() == "mock"


def test_mock_provider_default_json():
    """Default mock response is Tier1-style JSON."""
    p = MockProvider()
    text, cost, latency = p.complete(prompt="x", model="mock", max_tokens=512)
    assert "score" in text
    assert "reasoning" in text
    assert cost == 0.0
