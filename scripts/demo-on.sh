#!/bin/bash
# Enable InsightAgent demo - run before demo starts
set -euo pipefail

PROJECT="${PROJECT:-insightagent-adk}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-insightagent}"

# Generate new key
NEW_KEY="$(openssl rand -base64 32 | tr -d '/+=' | head -c 43)"
if [[ -z "$NEW_KEY" ]]; then
  echo "ERROR: Failed to generate demo API key (openssl returned empty output)."
  exit 1
fi

echo "🚀 Enabling InsightAgent demo..."

# Set new API key FIRST (before restoring public access)
# This ensures no window where service is public with old key
echo "Setting new API key..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$NEW_KEY" \
  --quiet

# Restore public access AFTER key is rotated
echo "Restoring public access..."
gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

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
echo "   echo \"VITE_API_KEY=$NEW_KEY\" > .env.production"
echo "   npm run build"
echo "   firebase deploy --only hosting"
echo ""
echo "New API Key: $NEW_KEY"
