# GCP Setup Guide for InsightAgent

This guide walks through the GCP configuration required for InsightAgent.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- A GCP project with billing enabled
- Owner or Editor role on the project

## 1. Set Project Variables

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="asia-south1"  # Mumbai

# Configure gcloud
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
```

## 2. Enable Required APIs

```bash
# Enable all required APIs
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firebasehosting.googleapis.com
```

### API Descriptions

| API | Purpose |
|-----|---------|
| `aiplatform.googleapis.com` | Vertex AI (Gemini models + RAG Engine) |
| `bigquery.googleapis.com` | Data warehouse for business data |
| `firestore.googleapis.com` | User memory and session storage |
| `run.googleapis.com` | Backend API hosting |
| `cloudbuild.googleapis.com` | Container image builds |
| `firebasehosting.googleapis.com` | Frontend static hosting |

## 3. Create Service Account

```bash
# Create service account for InsightAgent
gcloud iam service-accounts create insightagent-sa \
  --display-name="InsightAgent Service Account" \
  --description="Service account for InsightAgent backend"

# Store the full service account email
export SA_EMAIL="insightagent-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

## 4. Assign IAM Roles

```bash
# Vertex AI User - for Gemini API and RAG Engine
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# BigQuery Data Viewer - for reading tables
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataViewer"

# BigQuery Job User - for executing queries
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.jobUser"

# Firestore User - for memory read/write
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"
```

### Role Descriptions

| Role | Purpose |
|------|---------|
| `roles/aiplatform.user` | Access Gemini models and RAG Engine |
| `roles/bigquery.dataViewer` | Read BigQuery tables |
| `roles/bigquery.jobUser` | Execute BigQuery queries |
| `roles/datastore.user` | Read/write Firestore documents |

## 5. Initialize Firestore

```bash
# Create Firestore database in Native mode
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native
```

## 6. Create BigQuery Dataset

```bash
# Create dataset for InsightAgent data
bq mk --dataset \
  --location=$REGION \
  --description="InsightAgent business intelligence data" \
  ${PROJECT_ID}:insightagent_data
```

## 7. Configure Local Development (ADC)

For local development, use Application Default Credentials:

```bash
# Authenticate with your personal Google account
gcloud auth application-default login

# This creates credentials at:
# ~/.config/gcloud/application_default_credentials.json

# Verify authentication
gcloud auth application-default print-access-token
```

The application will automatically use these credentials when running locally.

## 8. Create Environment File

```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit with your values
cat > backend/.env << EOF
GCP_PROJECT_ID=${PROJECT_ID}
VERTEX_LOCATION=${REGION}
BQ_DATASET_ID=insightagent_data
FIRESTORE_COLLECTION_PREFIX=insightagent
GEMINI_MODEL=gemini-2.5-flash
DEMO_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ALLOWED_CORS_ORIGIN=http://localhost:5173
ENVIRONMENT=development
EOF
```

## 9. Verify Setup

```bash
# Test BigQuery access
bq query --use_legacy_sql=false \
  "SELECT 1 as test"

# Test Vertex AI access (Python)
python -c "
from google import genai

client = genai.Client(
    vertexai=True,
    project='${PROJECT_ID}',
    location='${REGION}'
)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Hello'
)
print('Vertex AI OK:', response.text[:50])
"

# Test Firestore access (Python)
python -c "
from google.cloud import firestore
db = firestore.Client()
print('Firestore OK: Connected to project', db.project)
"
```

## Cloud Run Deployment (Phase 7)

When deploying to Cloud Run, the service account is attached automatically:

```bash
# Deploy with service account
gcloud run deploy insightagent \
  --image gcr.io/${PROJECT_ID}/insightagent \
  --service-account=${SA_EMAIL} \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --memory=2Gi \
  --cpu=2 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=${REGION}"
```

## Security Notes

1. **No API Keys Required**: InsightAgent uses IAM-based authentication via service accounts. No API keys to store, rotate, or manage.

2. **Principle of Least Privilege**: The service account has only the roles needed for the application to function.

3. **Local vs Production**:
   - Local: Uses your personal credentials via ADC
   - Cloud Run: Uses the attached service account automatically

4. **Demo API Key**: The `DEMO_API_KEY` is for frontend authentication only, not for GCP services.

## Troubleshooting

### "Permission denied" errors

```bash
# Check current identity
gcloud auth list

# Check service account roles
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL}"
```

### "API not enabled" errors

```bash
# List enabled APIs
gcloud services list --enabled

# Enable missing API
gcloud services enable <api-name>
```

### Firestore "Database not found"

```bash
# Check Firestore database
gcloud firestore databases list

# Create if missing
gcloud firestore databases create --location=$REGION --type=firestore-native
```
