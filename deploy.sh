#!/usr/bin/env bash
# deploy.sh – One-command deployment to Google Cloud Run
#
# Usage:
#   ./deploy.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed (for local builds) OR Artifact Registry access
#   - The following environment variables set (or in .env):
#       GOOGLE_PROJECT_ID, GOOGLE_API_KEY
#       Optionally: GOOGLE_CLOUD_REGION, SERVICE_NAME, MODEL_NAME

set -euo pipefail

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -o allexport
  source .env
  set +o allexport
fi

# ---------------------------------------------------------------------------
# Configuration (with defaults)
# ---------------------------------------------------------------------------
PROJECT_ID="${GOOGLE_PROJECT_ID:?'ERROR: GOOGLE_PROJECT_ID is not set'}"
API_KEY="${GOOGLE_API_KEY:?'ERROR: GOOGLE_API_KEY is not set'}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-ai-text-agent}"
MODEL_NAME="${MODEL_NAME:-gemini-2.0-flash}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest"

echo "============================================================"
echo " Deploying ${SERVICE_NAME} to Cloud Run"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Image   : ${IMAGE}"
echo "  Model   : ${MODEL_NAME}"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Ensure Artifact Registry repository exists
# ---------------------------------------------------------------------------
echo ""
echo "[1/5] Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --format="value(name)" 2>/dev/null || \
gcloud artifacts repositories create "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --repository-format=docker \
  --description="Docker images for ${SERVICE_NAME}"

# ---------------------------------------------------------------------------
# 2. Configure Docker auth
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ---------------------------------------------------------------------------
# 3. Build and push the Docker image
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] Building and pushing Docker image..."
docker build -t "${IMAGE}" .
docker push "${IMAGE}"

# ---------------------------------------------------------------------------
# 4. Store the API key in Secret Manager (idempotent)
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] Storing GOOGLE_API_KEY in Secret Manager..."
if gcloud secrets describe GOOGLE_API_KEY \
    --project="${PROJECT_ID}" &>/dev/null; then
  echo "Secret GOOGLE_API_KEY already exists; adding a new version."
  echo -n "${API_KEY}" | gcloud secrets versions add GOOGLE_API_KEY \
    --project="${PROJECT_ID}" \
    --data-file=-
else
  echo "Creating secret GOOGLE_API_KEY..."
  echo -n "${API_KEY}" | gcloud secrets create GOOGLE_API_KEY \
    --project="${PROJECT_ID}" \
    --replication-policy=automatic \
    --data-file=-
fi

# ---------------------------------------------------------------------------
# 5. Deploy to Cloud Run
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="MODEL_NAME=${MODEL_NAME},LOG_LEVEL=INFO" \
  --update-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo "============================================================"
echo " Deployment complete!"
echo " Service URL: ${SERVICE_URL}"
echo ""
echo " Test the health endpoint:"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo " Send a test request:"
echo "   curl -X POST ${SERVICE_URL}/agent/run \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"Summarize: The quick brown fox.\"}'"
echo "============================================================"
