"""
Golden Tests for Demo Data.

Validates that seed data produces the exact values needed for the demo narrative.
These tests catch drift if someone edits the seed data CSVs.
"""

import pytest

# Demo data assertions from IMPLEMENTATION_PLAN.md Section 6.2
EXPECTED_VALUES = {
    "q4_2024_total_revenue": 12_400_000,  # $12.4M
    "q4_2024_target": 13_000_000,  # $13.0M
    "west_region_variance_pct": -25.7,  # vs target
    "q4_2023_revenue": 9_600_000,  # ~$9.6M (YoY baseline)
    "churn_rate_pct": 4.2,
    "west_q3_q4_transaction_drop_pct": 28,  # approximate
    "west_q3_q4_deal_size_change_pct": 6.9,  # approximate
}


class TestDemoDataValues:
    """Test that BigQuery data matches expected demo values."""

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_q4_2024_total_revenue(self):
        """Q4 2024 total revenue should be $12.4M."""
        # TODO: Query BigQuery and assert value
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_q4_2024_target(self):
        """Q4 2024 target should be $13.0M."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_west_region_variance(self):
        """West region should be -25.7% vs target."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_q4_2023_revenue_yoy(self):
        """Q4 2023 revenue should be ~$9.6M for YoY comparison."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_churn_rate(self):
        """Churn rate should be 4.2%."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_west_transaction_drop(self):
        """West Q3→Q4 transaction drop should be ~28%."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_west_deal_size_change(self):
        """West Q3→Q4 avg deal size change should be +6.9%."""
        pass


class TestDataIntegrity:
    """Test data integrity constraints."""

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_all_regions_have_data(self):
        """All four regions (North, South, East, West) should have Q4 data."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_transactions_have_valid_dates(self):
        """All transactions should have dates in expected range."""
        pass

    @pytest.mark.skip(reason="BigQuery not yet configured - Phase 4")
    def test_customer_segments_defined(self):
        """All customer segments (Enterprise, SMB, Consumer) should exist."""
        pass
