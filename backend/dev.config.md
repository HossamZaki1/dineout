# Local development configuration

Copy `.env.example` to `.env` and fill in the Gemini key, Maps key and Firebase
project ID. Never put those backend API keys in Flutter assets.

Choose storage explicitly:

- `STORAGE_BACKEND=memory`: no cloud database credentials, history is lost on restart.
- `STORAGE_BACKEND=firestore` (default): uses application default credentials and
  the default database in `FIRESTORE_PROJECT_ID`, or `FIREBASE_PROJECT_ID` when
  no separate storage project is set. Run `gcloud auth application-default login`
  for local credentials with permission to access that database.

There is no automatic fallback. Cloud Run refuses memory storage.

If an existing `.env` does not set `STORAGE_BACKEND`, it uses Firestore. A
`DefaultCredentialsError` means the backend cannot find Google Cloud application
credentials. `firebase login` and `gcloud auth login` do not create these; use
`gcloud auth application-default login` and restart Uvicorn. Install the Google
Cloud CLI first if `gcloud` is not found. See
[Google's local credentials setup](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

For a one-off run with temporary storage, without changing `.env`:

```bash
STORAGE_BACKEND=memory uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

From `backend/`, run `python validate_config.py` to check local configuration
without printing secrets or calling providers. Start the API with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

`GET /conversations/health` returns `{"status":"healthy","storage":"memory"}`
in memory mode. Firestore health performs a real database read.

Conversation and photo requests require a Firebase ID token in local development
too. See the [root README](../README.md) for frontend setup and automated tests
using fakes and a local Firestore emulator. See [DEPLOYMENT.md](DEPLOYMENT.md)
for Cloud Run setup.
