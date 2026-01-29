"""
InsightAgent - ADK Agent Definition.

This module defines the main ADK agent with Gemini 2.5 Flash model
and registers all four tools.
"""

from typing import AsyncGenerator, Any

from app.config import get_settings
from app.agent.prompts import build_system_prompt


class InsightAgent:
    """
    InsightAgent using Google ADK.

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

        # Agent and runner will be initialized in Phase 2
        self._agent = None
        self._runner = None

    async def initialize(self) -> None:
        """
        Initialize the ADK agent and runner.

        This sets up:
        - Gemini 2.5 Flash model
        - All four tools (BigQuery, Knowledge, Context, Memory)
        - Session service for conversation management
        """
        # TODO: Phase 2 implementation
        # from google.adk import Agent, Runner
        # from app.tools import (
        #     query_bigquery_tool,
        #     search_knowledge_base_tool,
        #     get_conversation_context_tool,
        #     save_to_memory_tool,
        # )
        #
        # self._agent = Agent(
        #     model=self.settings.gemini_model,
        #     system_prompt=self.system_prompt,
        #     tools=[
        #         query_bigquery_tool,
        #         search_knowledge_base_tool,
        #         get_conversation_context_tool,
        #         save_to_memory_tool,
        #     ],
        #     temperature=0.2,  # Low temperature for demo consistency
        # )
        #
        # self._runner = Runner(
        #     agent=self._agent,
        #     app_name="insightagent",
        #     session_service=session_service,
        # )
        pass

    async def chat(self, message: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a chat message and stream the response.

        Args:
            message: The user's message

        Yields:
            Dict events for reasoning traces, content deltas, and memory saves
        """
        # TODO: Phase 2 implementation
        # This will use runner.run_async() to stream events
        #
        # async for event in self._runner.run_async(
        #     user_id=self.user_id,
        #     session_id=self.session_id,
        #     new_message=message,
        # ):
        #     # Process and yield events
        #     yield process_event(event)

        # Placeholder response for Phase 1
        yield {
            "type": "content",
            "data": {
                "delta": "InsightAgent is ready. Full implementation coming in Phase 2."
            }
        }
        yield {
            "type": "done",
            "data": {
                "suggested_followups": [
                    "What was our Q4 revenue?",
                    "How are we tracking against targets?",
                    "What's our current churn rate?",
                ]
            }
        }

    async def close(self) -> None:
        """Clean up resources."""
        # TODO: Phase 2 - cleanup any open connections
        pass
