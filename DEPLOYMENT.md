# Deployment Guide

This guide covers deploying the AI Text Summarization Agent to **Google Cloud Run**.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [gcloud CLI](https://cloud.google.com/sdk/docs/install) | latest | GCP management |
| [Docker](https://docs.docker.com/get-docker/) | 20.10+ | Image builds |
| Python | 3.11+ | Local testing |

## Step 1 – Google Cloud Project Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com
```

## Step 2 – Obtain a Gemini API Key

1. Navigate to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API key**
3. Copy the key – you will store it in Secret Manager in Step 4

## Step 3 – Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `GOOGLE_API_KEY` – your Gemini API key
- `GOOGLE_PROJECT_ID` – your GCP project ID
- `GOOGLE_CLOUD_REGION` – preferred region (default: `us-central1`)

## Step 4 – Deploy with One Command

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Create an Artifact Registry repository (if it does not exist)
2. Build and push the Docker image
3. Store `GOOGLE_API_KEY` in Secret Manager
4. Deploy the service to Cloud Run

## Step 5 – Manual Deployment (alternative)

If you prefer to deploy manually:

```bash
# Set variables
PROJECT_ID=your-project-id
REGION=us-central1
SERVICE_NAME=ai-text-agent
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:latest"

# Create Artifact Registry repo
gcloud artifacts repositories create ${SERVICE_NAME} \
  --location=${REGION} \
  --repository-format=docker

# Configure Docker
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
docker build -t ${IMAGE} .
docker push ${IMAGE}

# Store API key
echo -n "YOUR_API_KEY" | gcloud secrets create GOOGLE_API_KEY \
  --replication-policy=automatic \
  --data-file=-

# Deploy
gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE} \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="MODEL_NAME=gemini-2.0-flash,LOG_LEVEL=INFO" \
  --update-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

## Step 6 – Test the Deployed Service

```bash
# Retrieve the service URL
SERVICE_URL=$(gcloud run services describe ai-text-agent \
  --region=us-central1 \
  --format="value(status.url)")

# Health check
curl ${SERVICE_URL}/health

# Summarize text
curl -X POST ${SERVICE_URL}/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Please summarize: Google Cloud Run is a managed compute platform that lets you run stateless containers. Cloud Run abstracts away all infrastructure management so you can focus on what matters most: building great applications."
  }'
```

## CI/CD with Cloud Build

Trigger a build automatically on every commit:

```bash
gcloud builds triggers create github \
  --repo-name=ai-agents-cloud-run \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_PROJECT_ID=${PROJECT_ID}
```

Or run manually:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=ai-text-agent,_REGION=us-central1 \
  .
```

## IAM Configuration

### Service-to-Service Authentication

If another Cloud Run service needs to call this agent, grant the **Cloud Run Invoker** role to its service account:

```bash
gcloud run services add-iam-policy-binding ai-text-agent \
  --region=us-central1 \
  --member="serviceAccount:CALLER_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### Vertex AI Access

If you switch to Vertex AI instead of the Gemini API, grant the **Vertex AI User** role:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:AGENT_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Secret Manager Access

Grant the Cloud Run service account access to read the API key secret:

```bash
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --member="serviceAccount:SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Monitoring

View logs in real time:

```bash
gcloud run services logs tail ai-text-agent --region=us-central1
```

Or navigate to the **Cloud Run** section of the [Google Cloud Console](https://console.cloud.google.com/run) and select your service.

## Cost Management

Cloud Run uses a **pay-per-request** model. To avoid unexpected costs:

- Set `--min-instances=0` (the default in `deploy.sh`) to scale to zero when idle
- Set an appropriate `--max-instances` limit
- Monitor usage in the [Cloud Billing console](https://console.cloud.google.com/billing)

To delete the service and free all resources:

```bash
# Delete the Cloud Run service
gcloud run services delete ai-text-agent --region=us-central1 --quiet

# Delete the Artifact Registry repository
gcloud artifacts repositories delete ai-text-agent \
  --location=us-central1 --quiet

# Delete the secret
gcloud secrets delete GOOGLE_API_KEY --quiet
```
