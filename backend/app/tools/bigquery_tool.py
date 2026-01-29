"""
BigQuery Tool for InsightAgent.

Executes SQL queries against the company's BigQuery data warehouse
with security constraints and cost controls.
"""

from typing import Any

from app.config import get_settings, get_bigquery_dataset
from app.services.bigquery_service import get_bigquery_service
from app.services.tool_middleware import log_tool_call, sanitize_tool_output


# Tool definition for ADK/Gemini function calling
BIGQUERY_TOOL_DEFINITION = {
    "name": "query_bigquery",
    "description": """Execute a SQL query against the company's BigQuery data warehouse.

Use this tool to retrieve sales, revenue, customer, and performance data.

IMPORTANT CONSTRAINTS:
- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE, DROP)
- Maximum 1000 rows returned
- Query timeout: 30 seconds
- Results include column names and row count

AVAILABLE TABLES (use fully qualified names with dataset):
- `{dataset}.transactions`: revenue, quantity, date, region, product_id, customer_id
- `{dataset}.customers`: customer_id, segment, acquisition_date, lifetime_value, region, status
- `{dataset}.targets`: region, quarter, year, target_amount

EXAMPLE QUERIES:
1. Q4 2024 revenue by region:
   SELECT region, SUM(revenue) as total_revenue
   FROM `{dataset}.transactions`
   WHERE EXTRACT(QUARTER FROM date) = 4 AND EXTRACT(YEAR FROM date) = 2024
   GROUP BY region

2. Total Q4 2024 revenue:
   SELECT SUM(revenue) as total_revenue
   FROM `{dataset}.transactions`
   WHERE date >= '2024-10-01' AND date <= '2024-12-31'

3. Customer segments:
   SELECT segment, COUNT(*) as count, AVG(lifetime_value) as avg_ltv
   FROM `{dataset}.customers`
   GROUP BY segment

4. Q4 targets:
   SELECT region, target_amount
   FROM `{dataset}.targets`
   WHERE quarter = 4 AND year = 2024

Returns raw data. If the user asks 'why' or needs context to interpret results,
follow up with `search_knowledge_base` to provide business context.
""".format(dataset=get_bigquery_dataset()),
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


async def query_bigquery(
    sql: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute a BigQuery SQL query with security constraints.

    Args:
        sql: The SQL query to execute (must be SELECT only)
        user_id: Optional user ID for logging
        session_id: Optional session ID for logging

    Returns:
        Dict with success status, data, row_count, columns, or error
    """
    # Log tool call
    if user_id and session_id:
        log_tool_call(
            tool_name="query_bigquery",
            parameters={"sql": sql},
            user_id=user_id,
            session_id=session_id,
        )

    # Get BigQuery service and execute
    service = get_bigquery_service()
    result = await service.execute_query(sql)

    # Sanitize output before returning
    return sanitize_tool_output("query_bigquery", result)
