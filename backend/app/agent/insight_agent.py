"""
InsightAgent - ADK Agent Definition.

This module defines the main agent with Gemini 2.5 Flash model
and registers all four tools using google.genai.Client.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from typing import AsyncGenerator, Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.agent.prompts import build_system_prompt
from app.tools import (
    get_tool_definitions,
    query_bigquery,
    search_knowledge_base,
    get_conversation_context,
    save_to_memory,
)

logger = logging.getLogger(__name__)


class InsightAgent:
    """
    InsightAgent using Google Gemini with function calling.

    This agent orchestrates tool calls for business intelligence queries,
    combining BigQuery data, knowledge base context, and persistent memory.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        memory_summary: str | None = None,
        conversation_history: list[dict] | None = None,
    ):
        """
        Initialize the InsightAgent.

        Args:
            user_id: The user's ID for scoping data access
            session_id: The current session ID
            memory_summary: Optional summary of user's past interactions
            conversation_history: Optional list of previous messages in the session
        """
        self.user_id = user_id
        self.session_id = session_id
        self.settings = get_settings()

        # Store memory summary for reasoning trace
        self._memory_summary = memory_summary

        # Build system prompt with optional memory context
        self.system_prompt = build_system_prompt(memory_summary)

        # Conversation history for multi-turn - initialize from previous messages
        self._history: list[types.Content] = self._load_conversation_history(conversation_history)

        # Client will be initialized lazily
        self._client: genai.Client | None = None

        # Tool function mapping
        self._tool_functions = {
            "query_bigquery": query_bigquery,
            "search_knowledge_base": search_knowledge_base,
            "get_conversation_context": get_conversation_context,
            "save_to_memory": save_to_memory,
        }

    # Maximum number of recent messages to load from history
    # Keeps context manageable and avoids Gemini context overflow
    MAX_HISTORY_MESSAGES = 20

    # Valid role mappings from Firestore to Gemini
    ROLE_MAPPING = {
        "user": "user",
        "assistant": "model",
        "model": "model",  # Handle if Gemini's role name is stored directly
    }

    # Simple scope guardrails to avoid answering unrelated, non-BI questions.
    # This is intentionally conservative: if we are not confident it's out-of-scope,
    # let the model handle it using the system prompt.
    _IN_SCOPE_HINTS = {
        "revenue",
        "sales",
        "transaction",
        "transactions",
        "customer",
        "customers",
        "segment",
        "segments",
        "churn",
        "retention",
        "ltv",
        "lifetime value",
        "conversion",
        "pipeline",
        "forecast",
        "target",
        "targets",
        "goal",
        "quota",
        "region",
        "regions",
        "north",
        "south",
        "east",
        "west",
        "quarter",
        "q1",
        "q2",
        "q3",
        "q4",
        "kpi",
        "metric",
        "metrics",
        "bigquery",
        "sql",
        "knowledge base",
    }

    _ALLOWLIST_META = {
        "help",
        "what can you do",
        "what do you do",
        "capabilities",
        "how do i use you",
    }

    _OUT_OF_SCOPE_PATTERNS = [
        r"\breverse\s+of\b",
        r"\banagram\b",
        r"\bpalindrome\b",
        r"\btell\s+me\s+a\s+joke\b",
        r"\bwrite\s+(a|an)\s+(poem|song|story)\b",
    ]

    @classmethod
    def _is_in_scope(cls, message: str) -> bool:
        msg = (message or "").strip().lower()
        if not msg:
            return True

        if any(meta in msg for meta in cls._ALLOWLIST_META):
            return True

        if any(hint in msg for hint in cls._IN_SCOPE_HINTS):
            return True

        for pattern in cls._OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, msg):
                return False

        # If it's short and has no BI hints, treat as out-of-scope.
        if len(msg) <= 60:
            return False

        # Otherwise, defer to the model + system prompt.
        return True

    def _load_conversation_history(
        self,
        conversation_history: list[dict] | None,
    ) -> list[types.Content]:
        """
        Convert conversation history from Firestore format to Gemini Content format.

        Args:
            conversation_history: List of message dicts with 'role' and 'content' keys

        Returns:
            List of types.Content objects for Gemini
        """
        if not conversation_history:
            return []

        # Limit to most recent messages to avoid context overflow
        recent_messages = conversation_history[-self.MAX_HISTORY_MESSAGES:]

        history = []
        for msg in recent_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Skip empty messages
            if not content:
                continue

            # Map to Gemini role, skip unknown roles
            gemini_role = self.ROLE_MAPPING.get(role)
            if not gemini_role:
                logger.warning(f"Skipping message with unknown role: {role}")
                continue

            history.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)],
                )
            )

        # Ensure history starts with a user message (Gemini requirement)
        while history and history[0].role == "model":
            logger.warning("Dropping leading model message to ensure valid role ordering")
            history.pop(0)

        return history

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of Gemini client."""
        if self._client is None:
            # Use project from settings if set, otherwise let ADC resolve it
            project = self.settings.gcp_project_id or None
            location = self.settings.vertex_location or "us-central1"
            self._client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )
        return self._client

    def _build_tools(self) -> list[types.Tool]:
        """Build tool declarations for Gemini."""
        function_declarations = []

        for tool_def in get_tool_definitions():
            func_decl = types.FunctionDeclaration(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"],
            )
            function_declarations.append(func_decl)

        return [types.Tool(function_declarations=function_declarations)]

    async def _execute_tool(
        self,
        function_call: types.FunctionCall,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Execute a tool function.

        Args:
            function_call: The function call from Gemini

        Returns:
            Tuple of (result_dict, event_data)
        """
        tool_name = function_call.name
        args = dict(function_call.args) if function_call.args else {}

        logger.info(f"Executing tool: {tool_name} with args: {list(args.keys())}")

        # Add user_id and session_id for tools that need them
        if tool_name in ["get_conversation_context", "save_to_memory"]:
            args["user_id"] = self.user_id
            args["session_id"] = self.session_id
        elif tool_name in ["query_bigquery", "search_knowledge_base"]:
            args["user_id"] = self.user_id
            args["session_id"] = self.session_id

        # Execute the tool
        tool_func = self._tool_functions.get(tool_name)
        if not tool_func:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }, {"tool_name": tool_name, "error": "Unknown tool"}

        try:
            result = await tool_func(**args)

            # Build event data for frontend
            event_data = {
                "tool_name": tool_name,
                "success": result.get("success", True),
            }

            # Add relevant summary info
            if tool_name == "query_bigquery" and result.get("success"):
                event_data["row_count"] = result.get("row_count", 0)
            elif tool_name == "search_knowledge_base" and result.get("success"):
                event_data["result_count"] = len(result.get("results", []))
            elif tool_name == "save_to_memory" and result.get("success"):
                event_data["key"] = result.get("key")
                event_data["memory_type"] = result.get("memory_type")

            return result, event_data

        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }, {"tool_name": tool_name, "error": str(e)}

    async def chat(self, message: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a chat message and stream the response.

        Args:
            message: The user's message

        Yields:
            Dict events for reasoning traces, content deltas, and memory saves
        """
        seq = 0

        def next_seq() -> int:
            nonlocal seq
            seq += 1
            return seq

        gemini_calls: list[dict[str, Any]] = []

        def record_gemini_call(
            *,
            iteration: int,
            latency_ms: int,
            response: Any | None,
            error: str | None = None,
        ) -> None:
            usage_metadata = getattr(response, "usage_metadata", None) if response is not None else None
            gemini_calls.append(
                {
                    "iteration": iteration,
                    "model": self.settings.gemini_model,
                    "model_version": getattr(response, "model_version", None) if response is not None else None,
                    "response_id": getattr(response, "response_id", None) if response is not None else None,
                    "latency_ms": latency_ms,
                    "status": "error" if error else "ok",
                    "error": error,
                    "usage": {
                        "prompt_token_count": getattr(usage_metadata, "prompt_token_count", None),
                        "candidates_token_count": getattr(usage_metadata, "candidates_token_count", None),
                        "total_token_count": getattr(usage_metadata, "total_token_count", None),
                        "thoughts_token_count": getattr(usage_metadata, "thoughts_token_count", None),
                        "cached_content_token_count": getattr(usage_metadata, "cached_content_token_count", None),
                        "tool_use_prompt_token_count": getattr(usage_metadata, "tool_use_prompt_token_count", None),
                    },
                }
            )

        def usage_summary() -> dict[str, Any]:
            def _sum_int(field_path: list[str]) -> int | None:
                total = 0
                found_any = False
                for call in gemini_calls:
                    value: Any = call
                    for key in field_path:
                        value = value.get(key) if isinstance(value, dict) else None
                    if isinstance(value, int):
                        total += value
                        found_any = True
                return total if found_any else None

            return {
                "calls": len(gemini_calls),
                "total_latency_ms": sum(int(c.get("latency_ms") or 0) for c in gemini_calls),
                "prompt_token_count": _sum_int(["usage", "prompt_token_count"]),
                "candidates_token_count": _sum_int(["usage", "candidates_token_count"]),
                "total_token_count": _sum_int(["usage", "total_token_count"]),
                "thoughts_token_count": _sum_int(["usage", "thoughts_token_count"]),
                "cached_content_token_count": _sum_int(["usage", "cached_content_token_count"]),
                "tool_use_prompt_token_count": _sum_int(["usage", "tool_use_prompt_token_count"]),
                "per_call": gemini_calls,
            }

        # Emit memory context trace if we have saved memory
        if self._memory_summary:
            trace_id = str(uuid.uuid4())[:8]
            # Emit started event first (frontend requires this to add trace)
            yield {
                "type": "reasoning",
                "seq": next_seq(),
                "data": {
                    "trace_id": trace_id,
                    "tool_name": "recall_memory",
                    "status": "started",
                    "input": "Loading saved findings from previous sessions...",
                },
            }
            # Then emit completed event
            yield {
                "type": "reasoning",
                "seq": next_seq(),
                "data": {
                    "trace_id": trace_id,
                    "tool_name": "recall_memory",
                    "status": "completed",
                    "summary": "Using remembered context to inform response",
                },
            }

        # Add user message to history
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )
        if not self._is_in_scope(message):
            refusal = (
                "I’m built to help with company metrics and performance analysis (revenue, targets, regions, "
                "customer segments, etc.). That request isn’t related to business intelligence.\n\n"
                "If you tell me the metric/timeframe you care about (e.g., “Q4 revenue by region” or "
                "“why West missed target”), I can pull the data and explain what’s driving it."
            )

            self._history.append(user_content)
            self._history.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=refusal)],
                )
            )

            yield {
                "type": "content",
                "seq": next_seq(),
                "data": {"delta": refusal},
            }
            yield {
                "type": "done",
                "seq": next_seq(),
                "data": {
                    "suggested_followups": [
                        "What was our Q4 revenue?",
                        "Revenue by region vs target for Q4",
                        "Why did we miss our target last quarter?",
                    ],
                    "tools_used": [],
                    "gemini_usage": usage_summary(),
                },
            }
            return

        self._history.append(user_content)

        # Build generation config
        config = types.GenerateContentConfig(
            temperature=0.2,  # Low temperature for demo consistency
            system_instruction=self.system_prompt,
            tools=self._build_tools(),
        )

        # Track tool calls for this turn
        tool_calls_made = []

        # Agentic loop - keep going until model produces final text
        max_iterations = 10  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                start = time.perf_counter()
                # Generate response - run sync call in thread to avoid blocking event loop
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.settings.gemini_model,
                    contents=self._history,
                    config=config,
                )
                latency_ms = int((time.perf_counter() - start) * 1000)
                record_gemini_call(iteration=iteration, latency_ms=latency_ms, response=response)

                # Check if model wants to call functions
                if response.candidates and response.candidates[0].content:
                    response_content = response.candidates[0].content

                    # Check for function calls
                    function_calls = []
                    text_parts = []

                    for part in response_content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
                        elif hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)

                    if function_calls:
                        # Process function calls
                        function_responses = []

                        for fc in function_calls:
                            trace_id = str(uuid.uuid4())[:8]
                            args = dict(fc.args) if fc.args else {}

                            # Build input display for the trace
                            input_display = self._format_tool_input(fc.name, args)

                            # Emit tool start event with input details
                            start_data = {
                                "trace_id": trace_id,
                                "tool_name": fc.name,
                                "status": "started",
                            }
                            if input_display is not None:
                                start_data["input"] = input_display
                            yield {
                                "type": "reasoning",
                                "seq": next_seq(),
                                "data": start_data,
                            }

                            # Execute the tool
                            result, event_data = await self._execute_tool(fc)

                            # Build summary for completed trace
                            summary = self._format_tool_summary(fc.name, result)

                            # Emit tool complete event with summary
                            yield {
                                "type": "reasoning",
                                "seq": next_seq(),
                                "data": {
                                    "trace_id": trace_id,
                                    "tool_name": fc.name,
                                    "status": "completed",
                                    "summary": summary,
                                    **event_data,
                                },
                            }

                            # Track for memory events
                            if fc.name == "save_to_memory" and result.get("success"):
                                yield {
                                    "type": "memory",
                                    "seq": next_seq(),
                                    "data": {
                                        "key": result.get("key"),
                                        "memory_type": result.get("memory_type"),
                                        "saved_at": result.get("saved_at"),
                                    },
                                }

                            tool_calls_made.append(fc.name)

                            # Build function response
                            function_responses.append(
                                types.Part.from_function_response(
                                    name=fc.name,
                                    response=result,
                                )
                            )

                        # Add model response and function results to history
                        self._history.append(response_content)
                        self._history.append(
                            types.Content(
                                role="user",
                                parts=function_responses,
                            )
                        )

                        # Continue loop - model may want to call more tools or respond
                        continue

                    elif text_parts:
                        # Model produced text response - we're done
                        full_text = "".join(text_parts)

                        # Add to history
                        self._history.append(response_content)

                        # Stream the text content
                        # For now, yield as single chunk (streaming can be added later)
                        yield {
                            "type": "content",
                            "seq": next_seq(),
                            "data": {
                                "delta": full_text,
                            },
                        }

                        # Generate follow-up suggestions based on response
                        followups = self._generate_followups(full_text, tool_calls_made)

                        yield {
                            "type": "done",
                            "seq": next_seq(),
                            "data": {
                                "suggested_followups": followups,
                                "tools_used": tool_calls_made,
                                "gemini_usage": usage_summary(),
                            },
                        }
                        return

                    else:
                        # Empty response - break out
                        logger.warning("Model returned empty response")
                        break

                else:
                    # No content - break out
                    logger.warning("Model returned no candidates")
                    break

            except Exception as e:
                record_gemini_call(iteration=iteration, latency_ms=0, response=None, error=str(e))
                logger.error(f"Error in chat loop: {e}")
                yield {
                    "type": "error",
                    "seq": next_seq(),
                    "data": {
                        "error": f"An error occurred: {str(e)}",
                        "gemini_usage": usage_summary(),
                    },
                }
                return

        # If we get here, something went wrong
        yield {
            "type": "content",
            "seq": next_seq(),
            "data": {
                "delta": "I encountered an issue processing your request. Please try again.",
            },
        }
        yield {
            "type": "done",
            "seq": next_seq(),
            "data": {
                "suggested_followups": [
                    "What was our Q4 revenue?",
                    "How are we tracking against targets?",
                ],
                "gemini_usage": usage_summary(),
            },
        }

    def _format_tool_input(self, tool_name: str, args: dict) -> str | None:
        """
        Format tool input for display in reasoning trace.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool

        Returns:
            Formatted input string for display, or None if not applicable
        """
        if tool_name == "query_bigquery":
            sql = str(args.get("sql") or "")
            # Truncate very long queries but keep them readable
            if len(sql) > 500:
                sql = sql[:500] + "..."
            return sql if sql else None
        elif tool_name == "search_knowledge_base":
            query = args.get("query", "")
            top_k = args.get("top_k", 3)
            return f'"{query}" (top {top_k} results)'
        elif tool_name == "get_conversation_context":
            return "Loading previous session context..."
        elif tool_name == "save_to_memory":
            memory_type = args.get("memory_type", "finding")
            key = args.get("key", "")
            return f'Saving {memory_type}: "{key}"'
        return None

    def _format_tool_summary(self, tool_name: str, result: dict) -> str:
        """
        Format tool result for display in reasoning trace.

        Args:
            tool_name: Name of the tool that was called
            result: Result dictionary from tool execution

        Returns:
            Formatted summary string for display
        """
        if not result.get("success", False):
            error = result.get("error", "Unknown error")
            return f"Error: {error}"

        if tool_name == "query_bigquery":
            row_count = result.get("row_count", 0)
            columns = result.get("columns", [])
            # Show a preview of the data if available
            data = result.get("data", [])
            if data and len(data) > 0:
                # Format first row as preview
                first_row = data[0]
                preview_parts = []
                # Identify likely currency columns by name
                currency_columns = {"revenue", "total_revenue", "amount", "target_amount", "lifetime_value", "avg_ltv"}
                for col in columns[:3]:  # Show first 3 columns
                    val = first_row.get(col, "")
                    # Only format as currency if column name suggests it's a monetary value
                    if isinstance(val, (int, float)) and col.lower() in currency_columns:
                        if val >= 1000000:
                            val = f"${val/1000000:.1f}M"
                        elif val >= 1000:
                            val = f"${val/1000:.1f}K"
                        else:
                            val = f"${val:,.2f}"
                    elif isinstance(val, float):
                        val = f"{val:,.2f}"
                    preview_parts.append(f"{col}: {val}")
                preview = ", ".join(preview_parts)
                return f"Found {row_count} rows. Sample: {preview}"
            return f"Found {row_count} rows"

        elif tool_name == "search_knowledge_base":
            results = result.get("results", [])
            if results:
                sources = [r.get("source", "unknown") for r in results[:3]]
                source_list = ", ".join(sources)
                return f"Found {len(results)} relevant documents: {source_list}"
            return "No matching documents found"

        elif tool_name == "get_conversation_context":
            context = result.get("data", {})
            if context:
                return "Loaded context from previous session"
            return "No previous context found"

        elif tool_name == "save_to_memory":
            memory_type = result.get("memory_type", "finding")
            key = result.get("key", "")
            return f'Saved {memory_type}: "{key}"'

        return "Completed"

    def _generate_followups(
        self,
        response_text: str,
        tools_used: list[str],
    ) -> list[str]:
        """
        Generate relevant follow-up suggestions based on the response.

        Args:
            response_text: The agent's response
            tools_used: List of tools that were used

        Returns:
            List of suggested follow-up questions
        """
        # Default follow-ups based on context
        followups = []

        # If BigQuery was used, suggest drilling down
        if "query_bigquery" in tools_used:
            followups.append("Can you break this down by region?")
            followups.append("How does this compare to last quarter?")

        # If knowledge base was used, suggest more context
        if "search_knowledge_base" in tools_used:
            followups.append("What are our targets for next quarter?")

        # If memory was saved, acknowledge and suggest next steps
        if "save_to_memory" in tools_used:
            followups.append("What other insights should we capture?")

        # Default suggestions if none generated
        if not followups:
            followups = [
                "What was our Q4 revenue?",
                "Why did we miss our target?",
                "How is the West region performing?",
            ]

        return followups[:3]  # Return max 3 suggestions

    async def close(self) -> None:
        """Clean up resources."""
        self._history = []
        self._client = None
