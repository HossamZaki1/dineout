# Deploying the backend

The script builds an image in Artifact Registry and deploys Cloud Run. Run it
only when ready to change cloud resources. It enables APIs, creates the image
repository and a dedicated runtime service account, and grants that account
access to the two secrets and Firestore.

## Prerequisites

- A billed Google Cloud project, authenticated `gcloud`, and a default Firestore
  database created in your chosen location.
- Firebase Authentication configured for the client applications.
- Gemini and Maps Platform keys; the Maps key needs Geocoding API and Places API (New).
- The deploying identity needs permission to enable services, build and deploy,
  create the repository/service account/secrets, and grant the listed IAM roles.
  The Cloud Build identity needs Artifact Registry write access. The deployer
  needs Service Account User on the runtime account.

## Run

From the repository root:

```bash
export PROJECT_ID=your-cloud-project
export FIREBASE_PROJECT_ID=your-firebase-project
# Optional: defaults to FIREBASE_PROJECT_ID
export FIRESTORE_PROJECT_ID=your-firestore-project
export REGION=us-central1
# Browser origins, not the backend URL. Empty is suitable for mobile-only.
export ALLOWED_ORIGINS=https://your-frontend.example,https://your-other-frontend.example
bash backend/deploy.sh
```

The script prompts for secrets only when they do not exist. Existing secrets
must have an enabled version. It does not change your default gcloud project.
Cloud Run supplies `PORT`; never put it in `--set-env-vars`.

`cloud-run-service.yaml` is an alternative service template, not a provisioning
script. Replace its project, region, repository and account placeholders and
provision the same secrets and IAM grants before using it.

The runtime account gets `roles/datastore.user` on the storage project and
`roles/secretmanager.secretAccessor` on each API-key secret. No service-account
key file is needed. Firestore is mandatory on Cloud Run: unavailable storage
fails startup or returns HTTP 503 rather than accepting an unsaved message.
A successful `POST /chat` means both messages committed.

## Verify and connect the app

Check `GET /health` for HTTP 200 and `storage: firestore`. Conversation and
photo endpoints require a Firebase ID token even though Cloud Run's transport
allows unauthenticated requests. The token audience is `FIREBASE_PROJECT_ID`.

Set `API_URL=https://your-service.run.app` in `frontend/.env` and rebuild.
Deploy the updated client and backend together: `GET /conversations` now
returns `{items, next_cursor}` and photo resolution requires authentication.

For an optional live smoke test, supply a short-lived Firebase ID token:

```bash
API_URL=https://your-service.run.app bash test_api.sh
```

The script prompts for the token without echoing it, performs a real search,
and creates a conversation in the signed-in account. It can incur provider fees.
Automated tests in the root README use fakes and a local emulator instead.

Use `gcloud run services logs read dineout-backend --project "$PROJECT_ID"
--region "$REGION"` to inspect failures. For CORS errors, check the exact
frontend origin in `ALLOWED_ORIGINS`. Authentication failures require checking
the Firebase project and client provider configuration.

References: [Cloud Run deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy),
[environment variables and delimiter escaping](https://cloud.google.com/run/docs/configuring/services/environment-variables),
[building container images](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit).
