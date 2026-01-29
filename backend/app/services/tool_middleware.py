"""
Tool Output Middleware for InsightAgent.

Sanitizes tool outputs before sending to UI:
- Redacts secrets and sensitive patterns
- Truncates long outputs
- Adds source citations
- Logs tool calls with PII redaction
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# Patterns to redact in logs and outputs
PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
    (r'\b\d{16}\b', '[CARD]'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),
    (r'(?i)(api[_-]?key|apikey|secret|password|token)["\s:=]+["\']?[\w-]+["\']?', '[REDACTED_SECRET]'),
]

# Maximum lengths for truncation
MAX_SQL_RESULT_ROWS = 50  # Rows to show in UI (full data still available)
MAX_KB_CONTENT_LENGTH = 2000  # Characters per KB chunk
MAX_LOG_LENGTH = 500  # Characters in log messages


def redact_pii(text: str) -> str:
    """
    Redact PII patterns from text.

    Args:
        text: The text to redact

    Returns:
        Text with PII patterns replaced
    """
    if not text:
        return text

    result = text
    for pattern, replacement in PII_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def truncate_for_log(text: str, max_length: int = MAX_LOG_LENGTH) -> str:
    """
    Truncate text for logging.

    Args:
        text: The text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return text

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


def sanitize_sql_results(
    results: list[dict],
    columns: list[str],
    max_rows: int = MAX_SQL_RESULT_ROWS,
) -> dict[str, Any]:
    """
    Sanitize SQL query results for UI display.

    Args:
        results: List of result rows
        columns: Column names
        max_rows: Maximum rows to include in display

    Returns:
        Sanitized results with truncation info
    """
    total_rows = len(results)
    truncated = total_rows > max_rows

    display_results = results[:max_rows] if truncated else results

    # Redact any PII in string values
    sanitized_results = []
    for row in display_results:
        sanitized_row = {}
        for key, value in row.items():
            if isinstance(value, str):
                sanitized_row[key] = redact_pii(value)
            else:
                sanitized_row[key] = value
        sanitized_results.append(sanitized_row)

    return {
        "data": sanitized_results,
        "columns": columns,
        "total_rows": total_rows,
        "displayed_rows": len(display_results),
        "truncated": truncated,
    }


def sanitize_kb_content(content: str, source: str) -> dict[str, Any]:
    """
    Sanitize knowledge base content.

    Args:
        content: The content chunk
        source: Source document name

    Returns:
        Sanitized content with citation
    """
    # Truncate if too long
    if len(content) > MAX_KB_CONTENT_LENGTH:
        content = content[:MAX_KB_CONTENT_LENGTH] + "..."

    # Redact any embedded secrets
    content = redact_pii(content)

    return {
        "content": content,
        "source": source,
        "citation": f"Source: {source}",
    }


def log_tool_call(
    tool_name: str,
    parameters: dict[str, Any],
    user_id: str,
    session_id: str,
) -> None:
    """
    Log a tool call with PII redaction.

    Args:
        tool_name: Name of the tool
        parameters: Tool parameters
        user_id: User ID (will be partially redacted)
        session_id: Session ID
    """
    # Redact user ID partially
    safe_user_id = user_id[:4] + "***" if len(user_id) > 4 else "***"

    # Redact parameter values
    safe_params = {}
    for key, value in parameters.items():
        if isinstance(value, str):
            safe_params[key] = truncate_for_log(redact_pii(value))
        else:
            safe_params[key] = value

    logger.info(
        f"Tool call: {tool_name} | user: {safe_user_id} | "
        f"session: {session_id[:8]}... | params: {safe_params}"
    )


def sanitize_tool_output(
    tool_name: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """
    Sanitize tool output before sending to frontend.

    Args:
        tool_name: Name of the tool
        output: Raw tool output

    Returns:
        Sanitized output safe for UI
    """
    # Apply tool-specific sanitization
    if tool_name == "query_bigquery" and output.get("success"):
        if "data" in output and "columns" in output:
            sanitized = sanitize_sql_results(
                output["data"],
                output["columns"],
            )
            output.update(sanitized)

    elif tool_name == "search_knowledge_base" and output.get("success"):
        if "results" in output:
            sanitized_results = []
            for result in output["results"]:
                sanitized = sanitize_kb_content(
                    result.get("content", ""),
                    result.get("source", "unknown"),
                )
                sanitized["relevance_score"] = result.get("relevance_score", 0)
                sanitized_results.append(sanitized)
            output["results"] = sanitized_results

    return output
