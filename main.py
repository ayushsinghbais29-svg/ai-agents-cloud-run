import os
import logging
from flask import Flask, request, jsonify
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is required but not set")

client = genai.Client(api_key=GEMINI_API_KEY)


def run_agent(prompt: str) -> str:
    """Run the AI agent with the given prompt and return the response text."""
    system_instruction = (
        "You are a helpful AI assistant. "
        "Answer the user's question clearly and concisely. "
        "If asked to summarise text, provide a brief summary. "
        "If asked a factual question, answer directly. "
        "If asked to classify text, return the category and a short reason."
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_instruction,
        ),
    )
    return response.text


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint required by Cloud Run."""
    return jsonify({"status": "ok"}), 200


@app.route("/agent", methods=["POST"])
def agent():
    """AI agent endpoint. Accepts JSON body with a 'prompt' field."""
    data = request.get_json(silent=True)
    if not data or "prompt" not in data:
        return jsonify({"error": "Request body must be JSON with a 'prompt' field"}), 400

    prompt = data["prompt"]
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "'prompt' must be a non-empty string"}), 400

    try:
        result = run_agent(prompt.strip())
        return jsonify({"response": result}), 200
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error while running agent: %s", exc)
        return jsonify({"error": "An internal error occurred"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
