#!/bin/bash

# Google Cloud deployment script for DineOut backend
set -e

# Configuration
PROJECT_ID="your-project-id-here"  # ⚠️ REPLACE THIS with your actual Google Cloud Project ID
REGION="us-central1"  # Change to your preferred region
SERVICE_NAME="dineout-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Google Cloud deployment for DineOut backend...${NC}"

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: PROJECT_ID is not set in this script.${NC}"
    echo -e "${YELLOW}Please edit this script and set your Google Cloud Project ID.${NC}"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI is not installed.${NC}"
    echo -e "${YELLOW}Please install Google Cloud CLI: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  Not authenticated with Google Cloud. Please run 'gcloud auth login'${NC}"
    exit 1
fi

# Set the project
echo -e "${GREEN}📝 Setting Google Cloud project to: ${PROJECT_ID}${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${GREEN}🔧 Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create secret for Google API key (if it doesn't exist)
echo -e "${GREEN}🔐 Setting up Google API key secret...${NC}"
if ! gcloud secrets describe google-api-key >/dev/null 2>&1; then
    echo -e "${YELLOW}Creating new secret for Google API key...${NC}"
    echo -n "Please enter your Google API key: "
    read -s GOOGLE_API_KEY
    echo
    echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=-
    echo -e "${GREEN}✅ Secret created successfully${NC}"
else
    echo -e "${GREEN}✅ Secret already exists${NC}"
fi

# Build and push the Docker image
echo -e "${GREEN}🐳 Building and pushing Docker image...${NC}"
gcloud builds submit --tag $IMAGE_NAME .

# Deploy to Cloud Run
echo -e "${GREEN}☁️  Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars HOST=0.0.0.0,PORT=8080 \
    --set-secrets GOOGLE_API_KEY=google-api-key:latest \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}📍 Your backend is now running at: ${SERVICE_URL}${NC}"
echo -e "${YELLOW}📝 Don't forget to update your Flutter app's API_BASE_URL to: ${SERVICE_URL}${NC}"

# Test the deployment
echo -e "${GREEN}🧪 Testing the deployment...${NC}"
if curl -s "$SERVICE_URL" | grep -q "Welcome to the Restaurant Finder AI API"; then
    echo -e "${GREEN}✅ Backend is responding correctly!${NC}"
else
    echo -e "${RED}⚠️  Backend might not be responding as expected. Check the logs:${NC}"
    echo -e "${YELLOW}gcloud run logs read --service=$SERVICE_NAME --region=$REGION${NC}"
fi
