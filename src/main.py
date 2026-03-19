"""
FastAPI entry-point for the AI Text Summarization Agent.

Endpoints
---------
GET  /health        – liveness/readiness probe (no auth required)
POST /agent/run     – send a message to the ADK agent and get a response
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AgentRequest(BaseModel):
    """Request body for the /agent/run endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The text or question to send to the agent.",
        examples=["Please summarize this text: The quick brown fox jumps over the lazy dog."],
    )
    session_id: str = Field(
        default="default",
        max_length=128,
        description="Optional session identifier for multi-turn conversations.",
    )


class AgentResponse(BaseModel):
    """Response body from the /agent/run endpoint."""

    response: str = Field(..., description="The agent's response.")
    session_id: str = Field(..., description="The session identifier used.")
    processing_time_ms: float = Field(..., description="Server-side processing time in ms.")


class HealthResponse(BaseModel):
    """Response body from the /health endpoint."""

    status: str
    model: str
    version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    logger.info("Starting AI Agents Cloud Run service (model=%s)", os.environ.get("MODEL_NAME", "gemini-2.0-flash"))
    yield
    logger.info("Shutting down AI Agents Cloud Run service")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Text Summarization Agent",
    description=(
        "A production-ready AI agent built with Google ADK and Gemini "
        "that summarizes text and computes text statistics."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – restrict to same-origin by default; override via ALLOWED_ORIGINS env var
_allowed_origins: list[str] = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check() -> HealthResponse:
    """Liveness and readiness probe for Cloud Run."""
    return HealthResponse(
        status="healthy",
        model=os.environ.get("MODEL_NAME", "gemini-2.0-flash"),
    )


@app.post("/agent/run", response_model=AgentResponse, tags=["agent"])
async def run_agent_endpoint(request: AgentRequest) -> AgentResponse:
    """Send a message to the ADK agent and receive a response.

    The agent will use the ``summarize_text`` and ``get_text_statistics``
    tools as needed based on the provided message.
    """
    start_time = time.perf_counter()
    logger.info(
        "POST /agent/run session=%s message_length=%d",
        request.session_id,
        len(request.message),
    )

    try:
        from src.agent import run_agent  # local import to allow unit testing without ADK

        response_text = run_agent(
            user_message=request.message,
            session_id=request.session_id,
        )
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("Runtime error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error running agent")
        raise HTTPException(status_code=500, detail="Internal server error") from exc

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info("Completed in %.1f ms", elapsed_ms)

    return AgentResponse(
        response=response_text,
        session_id=request.session_id,
        processing_time_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# Dev-server entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
