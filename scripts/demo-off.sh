#!/bin/bash
# Disable InsightAgent demo - run after demo ends
set -e

PROJECT="${PROJECT:-insightagent-adk}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-insightagent}"

echo "🔒 Disabling InsightAgent demo..."

# Remove public access
# Check if binding exists first to distinguish "not found" from real errors
echo "Removing public access..."
if gcloud run services get-iam-policy "$SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --format="value(bindings.members)" 2>/dev/null | grep -q "allUsers"; then
  gcloud run services remove-iam-policy-binding "$SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --member="allUsers" \
    --role="roles/run.invoker"
  echo "  Public access removed."
else
  echo "  Public access was not enabled (nothing to remove)."
fi

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
