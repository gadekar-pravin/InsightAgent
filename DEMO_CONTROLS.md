# InsightAgent Demo Controls

This document explains how to enable and disable the InsightAgent application between demos to prevent misuse and control costs.

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Disable (after demo)** | `./scripts/demo-off.sh` |
| **Enable (before demo)** | `./scripts/demo-on.sh` |

---

## Configuration

Set these variables for your environment:

```bash
export PROJECT=insightagent-adk
export REGION=asia-south1
export SERVICE=insightagent
```

---

## Disable After Demo

Run both steps to fully lock down the application:

### Step 1: Remove Public Access (Recommended)

This removes the ability for unauthenticated users to reach the Cloud Run service at all.

```bash
gcloud run services remove-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### Step 2: Rotate API Key to Unknown Value

This ensures even if someone bypasses IAM, the API key in the frontend won't work.

```bash
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$(openssl rand -hex 32)"
```

### Verification

```bash
# Should return 403 Forbidden (or connection refused if IAM removed)
curl -X POST "https://$SERVICE-<hash>.$REGION.run.app/api/chat/session" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: old-demo-key" \
  -d '{"user_id": "test"}'
```

---

## Enable Before Demo

### Step 1: Generate New API Key

```bash
# Generate and save new key
NEW_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 43)
echo "New API Key: $NEW_KEY"

# Update Cloud Run
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$NEW_KEY"
```

### Step 2: Restore Public Access

```bash
gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### Step 3: Update Frontend

Update the frontend with the new API key and redeploy:

```bash
cd frontend

# Update .env
echo "VITE_API_KEY=$NEW_KEY" > .env.production

# Build and deploy
npm run build
firebase deploy --only hosting
```

### Step 4: Warm Up (Optional)

For faster first response, set min-instances temporarily:

```bash
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --min-instances=1
```

After the demo, set back to 0:

```bash
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --min-instances=0
```

---

## Helper Scripts

### scripts/demo-off.sh

```bash
#!/bin/bash
set -e

PROJECT="${PROJECT:-insightagent-adk}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-insightagent}"

echo "🔒 Disabling InsightAgent demo..."

# Remove public access
echo "Removing public access..."
gcloud run services remove-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  2>/dev/null || echo "  (already removed)"

# Rotate API key
echo "Rotating API key to unknown value..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$(openssl rand -hex 32)" \
  --quiet

# Scale to zero
echo "Setting min-instances to 0..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --min-instances=0 \
  --quiet

echo "✅ Demo disabled. Service is locked down."
```

### scripts/demo-on.sh

```bash
#!/bin/bash
set -e

PROJECT="${PROJECT:-insightagent-adk}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-insightagent}"

# Generate new key
NEW_KEY=$(openssl rand -base64 32 | tr -d '/+=' | head -c 43)

echo "🚀 Enabling InsightAgent demo..."

# Restore public access
echo "Restoring public access..."
gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

# Set new API key
echo "Setting new API key..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$NEW_KEY" \
  --quiet

# Warm up
echo "Warming up (min-instances=1)..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --min-instances=1 \
  --quiet

echo ""
echo "✅ Demo enabled!"
echo ""
echo "⚠️  ACTION REQUIRED: Update frontend with new API key:"
echo ""
echo "   cd frontend"
echo "   echo 'VITE_API_KEY=$NEW_KEY' > .env.production"
echo "   npm run build"
echo "   firebase deploy --only hosting"
echo ""
echo "New API Key: $NEW_KEY"
```

---

## Security Summary

| Control | What it does | When to use |
|---------|--------------|-------------|
| Remove `allUsers` invoker | Blocks all unauthenticated HTTP requests | Always (primary control) |
| Rotate API key | Invalidates keys cached in browsers | Always (defense in depth) |
| min-instances=0 | Stops billing when idle | Always |
| Delete service | Complete removal | Long-term shutdown only |

**Best practice:** Use both IAM removal AND key rotation for maximum protection between demos.

---

## Cost Control

When disabled:
- **Cloud Run**: $0 (min-instances=0, no traffic)
- **BigQuery**: $0 (no queries)
- **Vertex AI**: $0 (no API calls)
- **Firestore**: Minimal (storage only, ~$0.01/month)

The only ongoing cost when disabled is Firestore storage for existing data.
