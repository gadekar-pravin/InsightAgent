"""
Tests for visualization detection methods in InsightAgent.
"""

import os
import sys

# Add backend to path so `app.*` imports work in unit tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agent.insight_agent import InsightAgent  # noqa: E402


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


class TestSelectChartType:
    """Tests for _select_chart_type method."""

    def test_returns_line_for_time_based_x_axis(self):
        """Should return 'line' for time-related column names."""
        agent = create_agent()
        data = [{"month": "Jan", "revenue": 100}]

        assert agent._select_chart_type(data, "month", 6) == "line"
        assert agent._select_chart_type(data, "quarter", 4) == "line"
        assert agent._select_chart_type(data, "year", 5) == "line"
        assert agent._select_chart_type(data, "date", 10) == "line"
        assert agent._select_chart_type(data, "time_period", 8) == "line"

    def test_returns_pie_for_few_categories(self):
        """Should return 'pie' for 2-5 rows."""
        agent = create_agent()
        data = [{"region": "North", "revenue": 100}]

        assert agent._select_chart_type(data, "region", 2) == "pie"
        assert agent._select_chart_type(data, "region", 3) == "pie"
        assert agent._select_chart_type(data, "region", 4) == "pie"
        assert agent._select_chart_type(data, "region", 5) == "pie"

    def test_returns_bar_for_many_categories(self):
        """Should return 'bar' for 6+ rows."""
        agent = create_agent()
        data = [{"region": "North", "revenue": 100}]

        assert agent._select_chart_type(data, "region", 6) == "bar"
        assert agent._select_chart_type(data, "region", 10) == "bar"
        assert agent._select_chart_type(data, "region", 20) == "bar"

    def test_time_based_takes_priority_over_row_count(self):
        """Time-based x-axis should return 'line' regardless of row count."""
        agent = create_agent()
        data = [{"month": "Jan", "revenue": 100}]

        # Even with 3 rows (which would normally be pie), month should be line
        assert agent._select_chart_type(data, "month", 3) == "line"


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
