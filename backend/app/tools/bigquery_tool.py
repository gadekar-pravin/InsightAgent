"""
BigQuery Tool for InsightAgent.

Executes SQL queries against the company's BigQuery data warehouse
with security constraints and cost controls.
"""

from functools import lru_cache
from typing import Any

from app.services.bigquery_service import get_bigquery_service
from app.services.tool_middleware import log_tool_call, sanitize_tool_output


# Tool description template - dataset placeholder resolved at runtime
_BIGQUERY_TOOL_DESCRIPTION_TEMPLATE = """Execute a SQL query against the company's BigQuery data warehouse.

Use this tool to retrieve sales, revenue, customer, and performance data.

IMPORTANT CONSTRAINTS:
- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE, DROP)
- Maximum 1000 rows returned
- Query timeout: 30 seconds
- Results include column names and row count

AVAILABLE TABLES (with column types):

1. `{dataset}.transactions`
   - revenue (FLOAT64), quantity (INT64), date (DATE), region (STRING), product_id (STRING), customer_id (STRING)

2. `{dataset}.customers`
   - customer_id (STRING), segment (STRING), acquisition_date (DATE), lifetime_value (FLOAT64), region (STRING), status (STRING)

3. `{dataset}.targets`
   - region (STRING), quarter (STRING - values like 'Q1', 'Q2', 'Q3', 'Q4'), year (INT64), target_amount (FLOAT64)

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

4. Q4 targets (note: quarter is STRING like 'Q4'):
   SELECT region, target_amount
   FROM `{dataset}.targets`
   WHERE quarter = 'Q4' AND year = 2024

Returns raw data. If the user asks 'why' or needs context to interpret results,
follow up with `search_knowledge_base` to provide business context.
"""


@lru_cache(maxsize=1)
def get_bigquery_tool_definition() -> dict:
    """
    Get the BigQuery tool definition with resolved dataset name.

    Deferred to runtime to avoid import-time ADC lookups.
    """
    from app.config import get_bigquery_dataset
    dataset = get_bigquery_dataset()

    return {
        "name": "query_bigquery",
        "description": _BIGQUERY_TOOL_DESCRIPTION_TEMPLATE.format(dataset=dataset),
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


# Note: BIGQUERY_TOOL_DEFINITION removed to avoid incomplete dict-like wrapper.
# Use get_bigquery_tool_definition() instead for runtime resolution.


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
