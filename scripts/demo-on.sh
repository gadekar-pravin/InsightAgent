#!/bin/bash
# Enable InsightAgent demo - run before demo starts
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
