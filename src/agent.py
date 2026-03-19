"""
ADK Agent implementation using Google Gemini.

The agent is built with the Google Agent Development Kit (ADK) and wires up
text-tool functions so that Gemini can call them during inference.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports – these packages may not be available in the test environment.
# The module is still importable; failures surface only when the agent is
# actually used (i.e. at runtime in Cloud Run).
# ---------------------------------------------------------------------------
try:
    import google.generativeai as genai  # type: ignore
    from google.adk.agents import Agent  # type: ignore
    from google.adk.runners import InMemoryRunner  # type: ignore
    from google.adk.sessions import InMemorySessionService  # type: ignore

    _ADK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ADK_AVAILABLE = False

from src.tools.text_tools import get_text_statistics, summarize_text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gemini-2.0-flash")
GOOGLE_API_KEY: str | None = os.environ.get("GOOGLE_API_KEY")

_AGENT_INSTRUCTION = (
    "You are a helpful text analysis assistant. "
    "When given text, use the available tools to summarize it and compute "
    "statistics. Always present the results clearly to the user. "
    "If the user just asks a question without providing text to process, "
    "answer directly from your knowledge."
)

# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def create_agent() -> Any:
    """Create and return a configured ADK Agent instance.

    Returns:
        An ``Agent`` object wired up with text tools.

    Raises:
        RuntimeError: If the ADK package is not installed.
        ValueError: If ``GOOGLE_API_KEY`` is not set.
    """
    if not _ADK_AVAILABLE:
        raise RuntimeError(
            "google-adk is not installed. "
            "Install it with: pip install google-adk"
        )
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Obtain a key at https://aistudio.google.com/app/apikey"
        )

    genai.configure(api_key=GOOGLE_API_KEY)
    logger.info("Creating ADK agent with model: %s", MODEL_NAME)

    agent = Agent(
        name="text_summarization_agent",
        model=MODEL_NAME,
        description="An agent that summarizes text and provides text statistics.",
        instruction=_AGENT_INSTRUCTION,
        tools=[summarize_text, get_text_statistics],
    )
    return agent


# ---------------------------------------------------------------------------
# Runner helper
# ---------------------------------------------------------------------------

def run_agent(user_message: str, session_id: str = "default") -> str:
    """Run the agent with *user_message* and return the response text.

    Args:
        user_message: The user's input text or question.
        session_id: An optional session identifier for multi-turn conversations.

    Returns:
        The agent's response as a string.

    Raises:
        RuntimeError: If the ADK package is not installed.
        ValueError: If ``GOOGLE_API_KEY`` is not set.
        Exception: On any Gemini API or ADK error.
    """
    agent = create_agent()
    session_service = InMemorySessionService()
    runner = InMemoryRunner(agent=agent, session_service=session_service)

    app_name = agent.name
    user_id = "user"

    session = session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    logger.info(
        "Running agent: session=%s, message_length=%d",
        session_id,
        len(user_message),
    )

    from google.genai.types import Content, Part  # type: ignore

    response_parts: list[str] = []
    for event in runner.run(
        user_id=user_id,
        session_id=session.id,
        new_message=Content(role="user", parts=[Part(text=user_message)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_parts.append(part.text)

    response = "".join(response_parts)
    logger.info("Agent response length: %d chars", len(response))
    return response
