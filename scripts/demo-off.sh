#!/bin/bash
# Disable InsightAgent demo - run after demo ends
set -euo pipefail

PROJECT="${PROJECT:-insightagent-adk}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-insightagent}"

echo "🔒 Disabling InsightAgent demo..."

# Remove public access
# Check if allUsers is specifically bound to roles/run.invoker (not other roles)
echo "Checking IAM policy..."
IAM_CHECK=$(gcloud run services get-iam-policy "$SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --flatten="bindings[].members" \
    --filter="bindings.role:roles/run.invoker AND bindings.members:allUsers" \
    --format="value(bindings.members)") || {
  echo "ERROR: Failed to get IAM policy for $SERVICE."
  echo "       Check that the service exists, region is correct, and you have permission."
  exit 1
}

if echo "$IAM_CHECK" | grep -q "allUsers"; then
  echo "Removing public access (allUsers from roles/run.invoker)..."
  gcloud run services remove-iam-policy-binding "$SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --member="allUsers" \
    --role="roles/run.invoker"
  echo "  Public access removed."
else
  echo "  allUsers not bound to roles/run.invoker (nothing to remove)."
fi

# Rotate API key
echo "Rotating API key to unknown value..."
NEW_KEY="$(openssl rand -hex 32)"
if [[ -z "$NEW_KEY" ]]; then
  echo "ERROR: Failed to generate new API key (openssl returned empty output)."
  exit 1
fi
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --update-env-vars="DEMO_API_KEY=$NEW_KEY" \
  --quiet

# Scale to zero
echo "Setting min-instances to 0..."
gcloud run services update "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --min-instances=0 \
  --quiet

echo "✅ Demo disabled. Service is locked down."
