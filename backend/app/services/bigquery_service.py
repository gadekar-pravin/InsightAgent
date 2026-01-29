"""
BigQuery Service for InsightAgent.

Provides secure query execution with SQL injection prevention,
cost controls, and error handling.
"""

import logging
import re
from typing import Any

from google.cloud import bigquery
from google.api_core.exceptions import BadRequest, Forbidden, NotFound

from app.config import get_settings, get_bigquery_dataset

logger = logging.getLogger(__name__)

# Prohibited SQL keywords (case-insensitive)
PROHIBITED_KEYWORDS = [
    r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
    r'\bCREATE\b', r'\bALTER\b', r'\bTRUNCATE\b', r'\bMERGE\b',
    r'\bGRANT\b', r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b',
]

# Maximum query length (characters)
MAX_QUERY_LENGTH = 10000


class BigQueryService:
    """Service for executing BigQuery queries with security constraints."""

    def __init__(self):
        """Initialize the BigQuery service."""
        self.settings = get_settings()
        self._client: bigquery.Client | None = None

    @property
    def client(self) -> bigquery.Client:
        """Lazy initialization of BigQuery client."""
        if self._client is None:
            self._client = bigquery.Client(project=self.settings.gcp_project_id)
        return self._client

    @property
    def dataset(self) -> str:
        """Get the fully qualified dataset ID."""
        return get_bigquery_dataset()

    def validate_query(self, sql: str) -> tuple[bool, str | None]:
        """
        Validate a SQL query for security.

        Args:
            sql: The SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Query cannot be empty"

        # Check query length
        if len(sql) > MAX_QUERY_LENGTH:
            return False, f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters"

        # Check for multiple statements (semicolons not in strings)
        # Simple check: reject if semicolon found outside of quotes
        # This is a basic check - dry_run provides server-side validation
        clean_sql = re.sub(r"'[^']*'", "", sql)  # Remove single-quoted strings
        clean_sql = re.sub(r'"[^"]*"', "", clean_sql)  # Remove double-quoted strings
        if ';' in clean_sql:
            return False, "Multiple statements not allowed (semicolon detected)"

        # Check for prohibited keywords
        sql_upper = sql.upper()
        for pattern in PROHIBITED_KEYWORDS:
            if re.search(pattern, sql_upper):
                keyword = pattern.replace(r'\b', '').strip()
                return False, f"Prohibited keyword detected: {keyword}. Only SELECT queries allowed."

        return True, None

    def _add_limit_if_missing(self, sql: str) -> str:
        """
        Add LIMIT clause if not present in the query.

        Args:
            sql: The SQL query

        Returns:
            SQL with LIMIT clause added if missing
        """
        # Check if LIMIT is already present (case-insensitive)
        if re.search(r'\bLIMIT\s+\d+', sql, re.IGNORECASE):
            return sql

        # Wrap query with LIMIT
        max_rows = self.settings.max_result_rows
        return f"SELECT * FROM ({sql.rstrip().rstrip(';')}) AS limited_query LIMIT {max_rows}"

    async def dry_run(self, sql: str) -> dict[str, Any]:
        """
        Perform a dry run to validate query and estimate cost.

        Args:
            sql: The SQL query to validate

        Returns:
            Dict with validation results and cost estimate
        """
        try:
            job_config = bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
            )

            # Execute dry run
            dry_run_job = self.client.query(sql, job_config=job_config)

            # Check statement type (server-side truth)
            statement_type = dry_run_job.statement_type
            if statement_type != "SELECT":
                return {
                    "valid": False,
                    "statement_type": statement_type,
                    "bytes_processed": 0,
                    "error": f"Only SELECT queries allowed. Got: {statement_type}",
                }

            bytes_processed = dry_run_job.total_bytes_processed or 0

            # Check cost estimate
            if bytes_processed > self.settings.max_query_bytes:
                return {
                    "valid": False,
                    "statement_type": statement_type,
                    "bytes_processed": bytes_processed,
                    "error": f"Query too expensive: {bytes_processed:,} bytes exceeds limit of {self.settings.max_query_bytes:,} bytes",
                }

            return {
                "valid": True,
                "statement_type": statement_type,
                "bytes_processed": bytes_processed,
                "error": None,
            }

        except BadRequest as e:
            return {
                "valid": False,
                "statement_type": None,
                "bytes_processed": 0,
                "error": f"Invalid query syntax: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Dry run failed: {e}")
            return {
                "valid": False,
                "statement_type": None,
                "bytes_processed": 0,
                "error": f"Query validation failed: {str(e)}",
            }

    async def execute_query(self, sql: str) -> dict[str, Any]:
        """
        Execute a validated SQL query.

        Args:
            sql: The SQL query to execute

        Returns:
            Dict with success status, data, columns, row_count, or error
        """
        # Step 1: Basic validation
        is_valid, error = self.validate_query(sql)
        if not is_valid:
            return {
                "success": False,
                "error": error,
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": 0,
            }

        # Step 2: Dry run validation
        dry_run_result = await self.dry_run(sql)
        if not dry_run_result["valid"]:
            return {
                "success": False,
                "error": dry_run_result["error"],
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": dry_run_result["bytes_processed"],
            }

        # Step 3: Add LIMIT if missing
        safe_sql = self._add_limit_if_missing(sql)

        # Step 4: Execute with timeout and cost limits
        try:
            job_config = bigquery.QueryJobConfig(
                maximum_bytes_billed=self.settings.max_query_bytes,
            )

            query_job = self.client.query(safe_sql, job_config=job_config)

            # Wait for results with timeout
            result = query_job.result(timeout=self.settings.query_timeout_seconds)

            # Convert to list of dicts
            rows = [dict(row) for row in result]
            columns = [field.name for field in result.schema]

            # Get actual bytes processed/billed
            bytes_processed = query_job.total_bytes_processed or 0
            bytes_billed = query_job.total_bytes_billed or 0

            logger.info(
                f"Query executed: {len(rows)} rows, "
                f"{bytes_processed:,} bytes processed, "
                f"{bytes_billed:,} bytes billed"
            )

            return {
                "success": True,
                "error": None,
                "data": rows,
                "columns": columns,
                "row_count": len(rows),
                "bytes_processed": bytes_processed,
                "bytes_billed": bytes_billed,
            }

        except TimeoutError:
            return {
                "success": False,
                "error": f"Query timed out after {self.settings.query_timeout_seconds} seconds",
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": 0,
            }
        except Forbidden as e:
            return {
                "success": False,
                "error": f"Access denied: {str(e)}",
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": 0,
            }
        except NotFound as e:
            return {
                "success": False,
                "error": f"Table or dataset not found: {str(e)}",
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": 0,
            }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "data": [],
                "columns": [],
                "row_count": 0,
                "bytes_processed": 0,
            }

    def close(self):
        """Close the BigQuery client."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance
_bigquery_service: BigQueryService | None = None


def get_bigquery_service() -> BigQueryService:
    """Get the BigQuery service singleton."""
    global _bigquery_service
    if _bigquery_service is None:
        _bigquery_service = BigQueryService()
    return _bigquery_service
