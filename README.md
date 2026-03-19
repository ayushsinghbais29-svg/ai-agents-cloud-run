# AI Text Summarization Agent

A production-ready AI agent built with **Google Agent Development Kit (ADK)** and **Gemini**, deployed as a serverless service on **Google Cloud Run**.

## Overview

This project demonstrates how to build and deploy a tool-using AI agent that:

- Accepts free-form text and returns a concise extractive summary
- Computes text statistics (word count, sentence count, average lengths, etc.)
- Exposes a REST API via **FastAPI**
- Runs as a containerised, serverless workload on **Cloud Run**

## Project Structure

```
ai-agents-cloud-run/
├── src/
│   ├── __init__.py
│   ├── agent.py              # ADK agent implementation
│   ├── tools/
│   │   ├── __init__.py
│   │   └── text_tools.py     # Tool implementations
│   └── main.py               # FastAPI entry-point
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   └── test_tools.py
├── Dockerfile
├── requirements.txt
├── .env.example
├── cloudbuild.yaml
├── deploy.sh
├── README.md
└── DEPLOYMENT.md
```

## Quick Start (local)

### 1. Prerequisites

- Python 3.11+
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

### 4. Run the server

```bash
python -m uvicorn src.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`.

### 5. Test locally

**Health check:**
```bash
curl http://localhost:8080/health
```

**Summarise text:**
```bash
curl -X POST http://localhost:8080/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Please summarize the following: The quick brown fox jumps over the lazy dog. This classic sentence is used by typographers to test fonts because it contains every letter of the alphabet."}'
```

## API Reference

### `GET /health`

Returns service health and current model name.

```json
{
  "status": "healthy",
  "model": "gemini-2.0-flash",
  "version": "1.0.0"
}
```

### `POST /agent/run`

Send a message to the AI agent.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ | Text or question (1–50 000 chars) |
| `session_id` | string | ❌ | Session identifier (default: `"default"`) |

**Response body:**

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Agent's response |
| `session_id` | string | Session identifier used |
| `processing_time_ms` | float | Server-side processing time |

**Example:**

```bash
curl -X POST http://localhost:8080/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize: Artificial intelligence is the simulation of human intelligence processes by computer systems.",
    "session_id": "my-session"
  }'
```

## Running Tests

```bash
pytest tests/ -v
```

## Docker

**Build:**
```bash
docker build -t ai-text-agent .
```

**Run:**
```bash
docker run -p 8080:8080 -e GOOGLE_API_KEY=your-key ai-text-agent
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step Cloud Run deployment instructions.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | – | **Required.** Gemini API key |
| `GOOGLE_PROJECT_ID` | – | GCP project ID (for Cloud Run) |
| `GOOGLE_CLOUD_REGION` | `us-central1` | Deployment region |
| `MODEL_NAME` | `gemini-2.0-flash` | Gemini model name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `PORT` | `8080` | Server port |

## Security

- API keys are stored in environment variables, never in code
- Docker container runs as a non-root user
- CORS origins are configurable
- Input validated with Pydantic (max 50 000 chars)
- Secret Manager integration for Cloud Run deployments

## License

This project is provided for educational purposes.