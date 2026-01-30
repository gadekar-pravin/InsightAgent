import os
import sys


# Add backend to path so `app.*` imports work in unit tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


from app.agent.insight_agent import InsightAgent  # noqa: E402


def test_scope_filter_blocks_reverse_of():
    assert InsightAgent._is_in_scope("what is reverse of \"apple\"?") is False


def test_scope_filter_allows_bi_query():
    assert InsightAgent._is_in_scope("Q4 2024 revenue by region") is True


def test_scope_filter_allows_metric_definition():
    assert InsightAgent._is_in_scope("What is churn?") is True


def test_scope_filter_allows_capabilities_question():
    assert InsightAgent._is_in_scope("what can you do?") is True


def test_scope_filter_allows_short_followups():
    """Short follow-up messages should be allowed (they rely on conversation context)."""
    assert InsightAgent._is_in_scope("why?") is True
    assert InsightAgent._is_in_scope("break it down further") is True
    assert InsightAgent._is_in_scope("compare to last year") is True
    assert InsightAgent._is_in_scope("show me more details") is True
    assert InsightAgent._is_in_scope("what's causing that?") is True

