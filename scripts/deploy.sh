#!/bin/bash
# InsightAgent Deployment Script
# Deploys backend and/or frontend to Google Cloud Run

set -e

# Configuration
PROJECT_ID="insightagent-adk"
REGION="asia-south1"
ARTIFACT_REGISTRY="asia-south1-docker.pkg.dev/${PROJECT_ID}/insightagent"

# Service names
BACKEND_SERVICE="insightagent"
FRONTEND_SERVICE="insightagent-frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

deploy_backend() {
    print_status "Deploying backend..."

    cd "${PROJECT_ROOT}/backend"

    # Build and push image
    print_status "Building backend Docker image..."
    gcloud builds submit \
        --tag="${ARTIFACT_REGISTRY}/backend:latest" \
        --project="${PROJECT_ID}" \
        --region="${REGION}"

    # Deploy to Cloud Run
    print_status "Deploying backend to Cloud Run..."
    gcloud run deploy "${BACKEND_SERVICE}" \
        --image="${ARTIFACT_REGISTRY}/backend:latest" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --allow-unauthenticated \
        --port=8080 \
        --memory=2Gi \
        --cpu=2 \
        --min-instances=0 \
        --max-instances=5 \
        --service-account="insightagent-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=${REGION},ENVIRONMENT=production"

    BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format="value(status.url)")

    print_status "Backend deployed: ${BACKEND_URL}"
    echo "${BACKEND_URL}"
}

deploy_frontend() {
    local backend_url="$1"

    print_status "Deploying frontend..."

    cd "${PROJECT_ROOT}/frontend"

    # Update nginx.conf with backend URL if provided
    if [ -n "${backend_url}" ]; then
        print_status "Updating nginx.conf with backend URL: ${backend_url}"
        # Extract hostname from URL
        BACKEND_HOST=$(echo "${backend_url}" | sed 's|https://||')
        sed -i.bak "s|proxy_pass https://.*asia-south1.run.app;|proxy_pass ${backend_url};|" nginx.conf
        sed -i.bak "s|proxy_set_header Host .*asia-south1.run.app;|proxy_set_header Host ${BACKEND_HOST};|" nginx.conf
        rm -f nginx.conf.bak
    fi

    # Build and push image
    print_status "Building frontend Docker image..."
    gcloud builds submit \
        --tag="${ARTIFACT_REGISTRY}/frontend:latest" \
        --project="${PROJECT_ID}" \
        --region="${REGION}"

    # Deploy to Cloud Run
    print_status "Deploying frontend to Cloud Run..."
    gcloud run deploy "${FRONTEND_SERVICE}" \
        --image="${ARTIFACT_REGISTRY}/frontend:latest" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --allow-unauthenticated \
        --port=8080 \
        --memory=512Mi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=5

    FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format="value(status.url)")

    print_status "Frontend deployed: ${FRONTEND_URL}"
    echo "${FRONTEND_URL}"
}

update_cors() {
    local frontend_url="$1"

    print_status "Updating backend CORS to allow: ${frontend_url}"

    gcloud run services update "${BACKEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --update-env-vars="ALLOWED_CORS_ORIGIN=${frontend_url}"

    print_status "CORS updated"
}

warmup_instances() {
    local min_instances="${1:-1}"

    print_status "Setting min instances to ${min_instances} for both services..."

    gcloud run services update "${BACKEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --min-instances="${min_instances}" &

    gcloud run services update "${FRONTEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --min-instances="${min_instances}" &

    wait
    print_status "Min instances updated"
}

show_status() {
    print_status "Current deployment status:"
    echo ""

    echo "Backend:"
    gcloud run services describe "${BACKEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format="table(status.url,status.conditions[0].status,spec.template.spec.containers[0].resources.limits.memory)" 2>/dev/null || echo "  Not deployed"

    echo ""
    echo "Frontend:"
    gcloud run services describe "${FRONTEND_SERVICE}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --format="table(status.url,status.conditions[0].status,spec.template.spec.containers[0].resources.limits.memory)" 2>/dev/null || echo "  Not deployed"
}

usage() {
    cat << EOF
InsightAgent Deployment Script

Usage: $0 [command] [options]

Commands:
  all         Deploy both backend and frontend (default)
  backend     Deploy only the backend
  frontend    Deploy only the frontend
  cors        Update backend CORS with frontend URL
  warmup      Set min-instances=1 to reduce cold starts
  cooldown    Set min-instances=0 to save costs
  status      Show current deployment status

Options:
  -h, --help  Show this help message

Examples:
  $0                  # Deploy both services
  $0 all              # Deploy both services
  $0 backend          # Deploy only backend
  $0 frontend         # Deploy only frontend
  $0 warmup           # Warm up instances before demo
  $0 cooldown         # Cool down after demo
  $0 status           # Check deployment status

EOF
}

# Main
main() {
    local command="${1:-all}"

    case "${command}" in
        -h|--help)
            usage
            exit 0
            ;;
        all)
            print_status "Starting full deployment..."
            BACKEND_URL=$(deploy_backend)
            FRONTEND_URL=$(deploy_frontend "${BACKEND_URL}")
            update_cors "${FRONTEND_URL}"
            print_status "Deployment complete!"
            echo ""
            echo "Frontend: ${FRONTEND_URL}"
            echo "Backend:  ${BACKEND_URL}"
            echo "API Docs: ${BACKEND_URL}/docs"
            ;;
        backend)
            deploy_backend
            ;;
        frontend)
            # Get current backend URL
            BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
                --project="${PROJECT_ID}" \
                --region="${REGION}" \
                --format="value(status.url)" 2>/dev/null)

            if [ -z "${BACKEND_URL}" ]; then
                print_error "Backend not deployed. Deploy backend first or use 'all' command."
                exit 1
            fi

            FRONTEND_URL=$(deploy_frontend "${BACKEND_URL}")
            update_cors "${FRONTEND_URL}"
            ;;
        cors)
            FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
                --project="${PROJECT_ID}" \
                --region="${REGION}" \
                --format="value(status.url)" 2>/dev/null)

            if [ -z "${FRONTEND_URL}" ]; then
                print_error "Frontend not deployed."
                exit 1
            fi

            update_cors "${FRONTEND_URL}"
            ;;
        warmup)
            warmup_instances 1
            ;;
        cooldown)
            warmup_instances 0
            ;;
        status)
            show_status
            ;;
        *)
            print_error "Unknown command: ${command}"
            usage
            exit 1
            ;;
    esac
}

main "$@"
