"""
Tests for visualization detection methods in InsightAgent.
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Add backend to path so `app.*` imports work in unit tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agent.insight_agent import InsightAgent


def create_agent() -> InsightAgent:
    """Create an InsightAgent instance for testing."""
    return InsightAgent(user_id="test_user", session_id="test_session")


class TestShouldVisualize:
    """Tests for _should_visualize method."""

    def test_returns_none_for_failed_result(self):
        """Should return None when query failed."""
        agent = create_agent()
        result = {"success": False, "error": "Query failed"}
        assert agent._should_visualize(result) is None

    def test_returns_none_for_single_row(self):
        """Should return None when result has only 1 row (not chartable)."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 1,
            "columns": ["region", "revenue"],
            "data": [{"region": "North", "revenue": 1000000}],
        }
        assert agent._should_visualize(result) is None

    def test_returns_none_for_too_many_rows(self):
        """Should return None when result has more than 20 rows."""
        agent = create_agent()
        data = [{"region": f"Region{i}", "revenue": i * 100000} for i in range(25)]
        result = {
            "success": True,
            "row_count": 25,
            "columns": ["region", "revenue"],
            "data": data,
        }
        assert agent._should_visualize(result) is None

    def test_returns_none_for_no_numeric_columns(self):
        """Should return None when there are no numeric columns."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 4,
            "columns": ["region", "status"],
            "data": [
                {"region": "North", "status": "Active"},
                {"region": "South", "status": "Active"},
                {"region": "East", "status": "Inactive"},
                {"region": "West", "status": "Active"},
            ],
        }
        assert agent._should_visualize(result) is None

    def test_returns_none_for_no_categorical_columns(self):
        """Should return None when there are no categorical columns."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 4,
            "columns": ["revenue", "profit"],
            "data": [
                {"revenue": 1000000, "profit": 200000},
                {"revenue": 2000000, "profit": 400000},
                {"revenue": 1500000, "profit": 300000},
                {"revenue": 2500000, "profit": 500000},
            ],
        }
        assert agent._should_visualize(result) is None

    def test_returns_valid_viz_data_for_chartable_result(self):
        """Should return visualization config for valid chartable data."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 4,
            "columns": ["region", "total_revenue"],
            "data": [
                {"region": "North", "total_revenue": 2500000},
                {"region": "South", "total_revenue": 2100000},
                {"region": "East", "total_revenue": 1800000},
                {"region": "West", "total_revenue": 1500000},
            ],
        }
        viz = agent._should_visualize(result)
        assert viz is not None
        assert viz["chart_type"] == "pie"  # 4 rows -> pie chart
        assert viz["x_axis"] == "region"
        assert viz["y_axis"] == "total_revenue"
        assert viz["title"] == "Total Revenue by Region"
        assert viz["data"] == result["data"]

    def test_handles_null_values_in_first_row(self):
        """Should find non-null sample even if first row has nulls."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 3,
            "columns": ["region", "revenue"],
            "data": [
                {"region": "North", "revenue": None},
                {"region": "South", "revenue": 2000000},
                {"region": "East", "revenue": 1500000},
            ],
        }
        viz = agent._should_visualize(result)
        assert viz is not None
        assert viz["y_axis"] == "revenue"

    def test_empty_data_returns_none(self):
        """Should return None for empty data array."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 0,
            "columns": ["region", "revenue"],
            "data": [],
        }
        assert agent._should_visualize(result) is None

    def test_handles_date_column_as_categorical(self):
        """Should treat datetime.date columns as categorical for x-axis."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 4,
            "columns": ["date", "total_revenue"],
            "data": [
                {"date": date(2024, 10, 1), "total_revenue": 500000},
                {"date": date(2024, 11, 1), "total_revenue": 600000},
                {"date": date(2024, 12, 1), "total_revenue": 700000},
                {"date": date(2025, 1, 1), "total_revenue": 550000},
            ],
        }
        viz = agent._should_visualize(result)
        assert viz is not None
        assert viz["chart_type"] == "line"  # date column triggers line chart
        assert viz["x_axis"] == "date"
        assert viz["y_axis"] == "total_revenue"

    def test_handles_datetime_column_as_categorical(self):
        """Should treat datetime.datetime columns as categorical for x-axis."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 3,
            "columns": ["timestamp", "revenue"],
            "data": [
                {"timestamp": datetime(2024, 10, 1, 10, 0, 0), "revenue": 100000},
                {"timestamp": datetime(2024, 10, 2, 10, 0, 0), "revenue": 150000},
                {"timestamp": datetime(2024, 10, 3, 10, 0, 0), "revenue": 120000},
            ],
        }
        viz = agent._should_visualize(result)
        assert viz is not None
        assert viz["x_axis"] == "timestamp"
        assert viz["y_axis"] == "revenue"

    def test_handles_decimal_column_as_numeric(self):
        """Should treat decimal.Decimal columns (BigQuery NUMERIC) as numeric."""
        agent = create_agent()
        result = {
            "success": True,
            "row_count": 4,
            "columns": ["region", "total_revenue"],
            "data": [
                {"region": "North", "total_revenue": Decimal("2500000.50")},
                {"region": "South", "total_revenue": Decimal("2100000.75")},
                {"region": "East", "total_revenue": Decimal("1800000.25")},
                {"region": "West", "total_revenue": Decimal("1500000.00")},
            ],
        }
        viz = agent._should_visualize(result)
        assert viz is not None
        assert viz["x_axis"] == "region"
        assert viz["y_axis"] == "total_revenue"
        assert viz["chart_type"] == "pie"  # 4 rows -> pie chart


class TestSelectChartType:
    """Tests for _select_chart_type method."""

    def test_returns_line_for_time_based_x_axis(self):
        """Should return 'line' for time-related column names."""
        agent = create_agent()

        assert agent._select_chart_type("month", 6) == "line"
        assert agent._select_chart_type("quarter", 4) == "line"
        assert agent._select_chart_type("year", 5) == "line"
        assert agent._select_chart_type("date", 10) == "line"
        assert agent._select_chart_type("time_period", 8) == "line"
        assert agent._select_chart_type("timestamp", 6) == "line"
        assert agent._select_chart_type("order_datetime", 6) == "line"

    def test_returns_pie_for_few_categories(self):
        """Should return 'pie' for 2-5 rows."""
        agent = create_agent()

        assert agent._select_chart_type("region", 2) == "pie"
        assert agent._select_chart_type("region", 3) == "pie"
        assert agent._select_chart_type("region", 4) == "pie"
        assert agent._select_chart_type("region", 5) == "pie"

    def test_returns_bar_for_many_categories(self):
        """Should return 'bar' for 6+ rows."""
        agent = create_agent()

        assert agent._select_chart_type("region", 6) == "bar"
        assert agent._select_chart_type("region", 10) == "bar"
        assert agent._select_chart_type("region", 20) == "bar"

    def test_time_based_takes_priority_over_row_count(self):
        """Time-based x-axis should return 'line' regardless of row count."""
        agent = create_agent()

        # Even with 3 rows (which would normally be pie), month should be line
        assert agent._select_chart_type("month", 3) == "line"

    def test_no_false_positive_for_lifetime_value(self):
        """Should NOT classify 'lifetime_value' as time-based (token matching)."""
        agent = create_agent()

        # These should NOT be classified as time-based
        assert agent._select_chart_type("lifetime_value", 6) == "bar"
        assert agent._select_chart_type("segment", 3) == "pie"
        assert agent._select_chart_type("customer_segment", 6) == "bar"


class TestGenerateChartTitle:
    """Tests for _generate_chart_title method."""

    def test_generates_title_from_columns(self):
        """Should generate 'Y by X' format title."""
        agent = create_agent()

        assert agent._generate_chart_title("region", "total_revenue") == "Total Revenue by Region"
        assert agent._generate_chart_title("month", "revenue") == "Revenue by Month"
        assert agent._generate_chart_title("customer_segment", "avg_order_value") == "Avg Order Value by Customer Segment"

    def test_handles_single_word_columns(self):
        """Should handle single-word column names."""
        agent = create_agent()

        assert agent._generate_chart_title("region", "revenue") == "Revenue by Region"
        assert agent._generate_chart_title("quarter", "profit") == "Profit by Quarter"
