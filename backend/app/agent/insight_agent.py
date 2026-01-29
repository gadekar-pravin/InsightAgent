"""
InsightAgent - ADK Agent Definition.

This module defines the main agent with Gemini 2.5 Flash model
and registers all four tools using google.genai.Client.
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.agent.prompts import build_system_prompt
from app.tools import (
    TOOL_DEFINITIONS,
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

    def __init__(self, user_id: str, session_id: str, memory_summary: str | None = None):
        """
        Initialize the InsightAgent.

        Args:
            user_id: The user's ID for scoping data access
            session_id: The current session ID
            memory_summary: Optional summary of user's past interactions
        """
        self.user_id = user_id
        self.session_id = session_id
        self.settings = get_settings()

        # Build system prompt with optional memory context
        self.system_prompt = build_system_prompt(memory_summary)

        # Conversation history for multi-turn
        self._history: list[types.Content] = []

        # Client will be initialized lazily
        self._client: genai.Client | None = None

        # Tool function mapping
        self._tool_functions = {
            "query_bigquery": query_bigquery,
            "search_knowledge_base": search_knowledge_base,
            "get_conversation_context": get_conversation_context,
            "save_to_memory": save_to_memory,
        }

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

        for tool_def in TOOL_DEFINITIONS:
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

        # Add user message to history
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )
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
                # Generate response - run sync call in thread to avoid blocking event loop
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.settings.gemini_model,
                    contents=self._history,
                    config=config,
                )

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

                            # Emit tool start event
                            yield {
                                "type": "reasoning",
                                "seq": next_seq(),
                                "data": {
                                    "trace_id": trace_id,
                                    "tool_name": fc.name,
                                    "status": "started",
                                },
                            }

                            # Execute the tool
                            result, event_data = await self._execute_tool(fc)

                            # Emit tool complete event
                            yield {
                                "type": "reasoning",
                                "seq": next_seq(),
                                "data": {
                                    "trace_id": trace_id,
                                    "tool_name": fc.name,
                                    "status": "completed",
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
                logger.error(f"Error in chat loop: {e}")
                yield {
                    "type": "error",
                    "seq": next_seq(),
                    "data": {
                        "error": f"An error occurred: {str(e)}",
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
            },
        }

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
