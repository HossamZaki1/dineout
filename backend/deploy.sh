#!/usr/bin/env bash
# Run explicitly to build and deploy; see DEPLOYMENT.md for required permissions.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to the Google Cloud deployment project}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-dineout-backend}"
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-$PROJECT_ID}"
FIRESTORE_PROJECT_ID="${FIRESTORE_PROJECT_ID:-$FIREBASE_PROJECT_ID}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-}"
REPOSITORY="${REPOSITORY:-dineout}"
RUNTIME_ACCOUNT="dineout-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"

command -v gcloud >/dev/null || { echo "Install the Google Cloud CLI first." >&2; exit 1; }
if [[ "$ALLOWED_ORIGINS" == *"|"* ]]; then
    echo "ALLOWED_ORIGINS must not contain the deployment delimiter |." >&2
    exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

gcloud services enable --project "$PROJECT_ID" \
    cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com iam.googleapis.com
gcloud services enable --project "$FIRESTORE_PROJECT_ID" firestore.googleapis.com
# Create the database explicitly in the desired region before deployment.
gcloud firestore databases describe --project "$FIRESTORE_PROJECT_ID" --database='(default)' >/dev/null

if ! gcloud artifacts repositories describe "$REPOSITORY" --project "$PROJECT_ID" --location "$REGION" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$REPOSITORY" --project "$PROJECT_ID" \
        --location "$REGION" --repository-format=docker
fi
if ! gcloud iam service-accounts describe "$RUNTIME_ACCOUNT" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create dineout-runtime --project "$PROJECT_ID" \
        --display-name="Dineout backend runtime"
fi

ensure_secret() {
    local secret_name="$1"
    local prompt="$2"
    local key_value
    if ! gcloud secrets describe "$secret_name" --project "$PROJECT_ID" >/dev/null 2>&1; then
        read -r -s -p "$prompt: " key_value
        echo
        [[ -n "$key_value" ]] || { echo "No value entered for $secret_name." >&2; exit 1; }
        printf '%s' "$key_value" | gcloud secrets create "$secret_name" \
            --project "$PROJECT_ID" --data-file=-
        unset key_value
    fi
    gcloud secrets add-iam-policy-binding "$secret_name" --project "$PROJECT_ID" \
        --member="serviceAccount:$RUNTIME_ACCOUNT" --role=roles/secretmanager.secretAccessor >/dev/null
}
ensure_secret google-api-key "Gemini API key"
ensure_secret google-maps-api-key "Google Maps Platform API key"
gcloud projects add-iam-policy-binding "$FIRESTORE_PROJECT_ID" \
    --member="serviceAccount:$RUNTIME_ACCOUNT" --role=roles/datastore.user --condition=None >/dev/null

gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE_NAME" .
# Cloud Run supplies PORT. An alternate delimiter preserves comma-separated origins.
gcloud run deploy "$SERVICE_NAME" --project "$PROJECT_ID" \
    --image "$IMAGE_NAME" --platform managed --region "$REGION" \
    --service-account "$RUNTIME_ACCOUNT" --allow-unauthenticated \
    --set-env-vars "^|^HOST=0.0.0.0|STORAGE_BACKEND=firestore|FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID|FIRESTORE_PROJECT_ID=$FIRESTORE_PROJECT_ID|ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest,GOOGLE_MAPS_API_KEY=google-maps-api-key:latest" \
    --port 8080 --memory 2Gi --cpu 1 --timeout 300 --concurrency 80 --max-instances 10

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" \
    --region "$REGION" --format='value(status.url)')
curl --fail --silent --show-error "$SERVICE_URL/health"
echo
echo "Backend URL: $SERVICE_URL"
