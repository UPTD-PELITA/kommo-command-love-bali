#!/bin/bash

# Cloud Run Deployment Script for kommo-lang-select
# 
# This script helps deploy the kommo-lang-select application to Google Cloud Run
# using Cloud Build for automated building and deployment.

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="kommo-lang-select"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        echo_error "gcloud CLI is not installed. Please install it first."
        echo "Visit: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
        echo_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check if project is set
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    if [[ -z "$CURRENT_PROJECT" ]]; then
        echo_error "No project set. Please run 'gcloud config set project YOUR_PROJECT_ID'"
        exit 1
    fi
    
    PROJECT_ID=$CURRENT_PROJECT
    echo_info "Using project: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    echo_info "Enabling required Google Cloud APIs..."
    
    APIs=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "containerregistry.googleapis.com"
    )
    
    for api in "${APIs[@]}"; do
        echo_info "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    done
}

# Create secrets for Firebase configuration
create_secrets() {
    echo_info "Setting up secrets for Firebase configuration..."
    
    # Check if FIREBASE_DATABASE_URL secret exists
    if ! gcloud secrets describe firebase-database-url --project="$PROJECT_ID" &>/dev/null; then
        echo_warn "Secret 'firebase-database-url' does not exist."
        echo "Please create it manually with:"
        echo "gcloud secrets create firebase-database-url --data-file=- --project=$PROJECT_ID"
        echo "Then paste your Firebase Database URL and press Ctrl+D"
    fi
    
    # Check if service account key secret exists
    if ! gcloud secrets describe firebase-service-account --project="$PROJECT_ID" &>/dev/null; then
        echo_warn "Secret 'firebase-service-account' does not exist."
        echo "Please create it manually with:"
        echo "gcloud secrets create firebase-service-account --data-file=path/to/serviceAccountKey.json --project=$PROJECT_ID"
    fi
}

# Deploy using Cloud Build
deploy() {
    echo_info "Starting deployment with Cloud Build..."
    
    # Submit build
    gcloud builds submit \
        --config=cloudbuild.yaml \
        --project="$PROJECT_ID" \
        .
    
    echo_info "Deployment completed!"
    echo_info "Your service should be available at:"
    echo "https://${SERVICE_NAME}-$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)' | cut -d'/' -f3)"
}

# Main execution
main() {
    echo_info "Starting Cloud Run deployment for kommo-lang-select"
    
    check_prerequisites
    enable_apis
    create_secrets
    deploy
    
    echo_info "Deployment process completed!"
    echo ""
    echo "Next steps:"
    echo "1. Set up your Firebase secrets if you haven't already"
    echo "2. Configure environment variables in Cloud Run console if needed"
    echo "3. Monitor logs: gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}"
}

# Run main function
main "$@"