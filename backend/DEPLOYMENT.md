# Google Cloud Deployment Guide for DineQuest Backend

## Prerequisites

1. **Install Google Cloud CLI**: https://cloud.google.com/sdk/docs/install
2. **Create a Google Cloud Project** or use an existing one
3. **Enable billing** for your Google Cloud project

## Step 1: Setup Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID (replace with your actual project ID)
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## Step 2: Configure the Deployment Script

1. Open `deploy.sh` and set your `PROJECT_ID`:
   ```bash
   PROJECT_ID="your-actual-project-id"  # Replace with your project ID
   ```

2. Optionally change the region (default is `us-central1`)

## Step 3: Deploy to Google Cloud

```bash
# Navigate to backend directory
cd backend

# Make the script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

The script will:
- Build a Docker image of your FastAPI app
- Upload it to Google Container Registry
- Deploy it to Cloud Run
- Set up secrets for your Google API key
- Configure environment variables

## Step 4: Update Flutter App

After deployment, update your Flutter app's `.env` file:

```
API_BASE_URL=https://your-service-url-from-cloud-run.run.app
```

## Monitoring and Logs

```bash
# View logs
gcloud run logs read --service=dinequest-backend --region=us-central1

# Get service info
gcloud run services describe dinequest-backend --region=us-central1
```

## Cost Optimization

Cloud Run pricing:
- **Free tier**: 2 million requests/month
- **CPU**: Only charged when processing requests
- **Memory**: 2GB allocated (adjust in deploy.sh if needed)
- **Estimated cost**: ~$5-20/month for moderate usage

## Troubleshooting

1. **Build fails**: Check Dockerfile and requirements.txt
2. **Secret issues**: Ensure Google API key is set correctly
3. **CORS errors**: The FastAPI app already has CORS configured for all origins
4. **Memory issues**: Increase memory in deploy.sh if needed
