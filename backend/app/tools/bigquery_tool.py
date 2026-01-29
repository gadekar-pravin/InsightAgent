"""
BigQuery Tool for InsightAgent.

Executes SQL queries against the company's BigQuery data warehouse
with security constraints and cost controls.
"""

from typing import Any

from app.config import get_settings


# Tool definition for ADK
BIGQUERY_TOOL_DEFINITION = {
    "name": "query_bigquery",
    "description": """Execute a SQL query against the company's BigQuery data warehouse.

Use this tool to retrieve sales, revenue, customer, and performance data.

IMPORTANT CONSTRAINTS:
- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE, DROP)
- Maximum 1000 rows returned
- Query timeout: 30 seconds
- Results include column names and row count

AVAILABLE TABLES:
- transactions: revenue, quantities, dates, regions, products
- customers: segments, acquisition dates, lifetime value
- targets: region, quarter, year, target_amount

EXAMPLE QUERIES:
1. Q4 revenue by region:
   SELECT region, SUM(revenue) as total_revenue
   FROM transactions
   WHERE EXTRACT(QUARTER FROM date) = 4 AND EXTRACT(YEAR FROM date) = 2024
   GROUP BY region

2. Customer segments:
   SELECT segment, COUNT(*) as count, AVG(lifetime_value) as avg_ltv
   FROM customers
   GROUP BY segment

Returns raw data. If the user asks 'why' or needs context to interpret results,
follow up with `search_knowledge_base` to provide business context.
""",
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The SQL SELECT query to execute"
            }
        },
        "required": ["sql"]
    }
}


async def query_bigquery(sql: str) -> dict[str, Any]:
    """
    Execute a BigQuery SQL query with security constraints.

    Args:
        sql: The SQL query to execute (must be SELECT only)

    Returns:
        Dict with success status, data, row_count, columns, or error
    """
    # TODO: Phase 2 implementation
    # This will:
    # 1. Validate single statement (no semicolons)
    # 2. Dry-run to verify SELECT only
    # 3. Check cost estimate
    # 4. Execute with timeout and row limit
    # 5. Return formatted results

    settings = get_settings()

    return {
        "success": False,
        "error": "BigQuery tool not yet implemented. Coming in Phase 2.",
        "data": None,
        "row_count": 0,
        "columns": [],
    }
