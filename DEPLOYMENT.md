# Google Cloud Run Deployment Guide

This guide explains how to deploy the kommo-command application to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: Ensure you have access to a Google Cloud project
2. **gcloud CLI**: Install and configure the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
3. **Firebase Project**: Have a Firebase project with Realtime Database enabled
4. **Service Account**: Firebase Admin SDK service account key file

## Quick Deployment

The easiest way to deploy is using the provided deployment script:

```bash
./deploy.sh
```

This script will:

- Check prerequisites
- Enable required Google Cloud APIs
- Guide you through setting up secrets
- Deploy using Cloud Build

## Manual Deployment

### 1. Set up Google Cloud Project

```bash
# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Create Secrets

The application requires two secrets:

#### Firebase Database URL

```bash
echo "https://your-project-default-rtdb.firebaseio.com" | \
gcloud secrets create firebase-database-url --data-file=-
```

#### Firebase Service Account Key

```bash
gcloud secrets create firebase-service-account \
  --data-file=path/to/your/serviceAccountKey.json
```

### 3. Deploy with Cloud Build

```bash
# Deploy using Cloud Build
gcloud builds submit --config=cloudbuild.yaml .
```

## Configuration

### Environment Variables

The following environment variables can be configured in Cloud Run:

- `LOG_LEVEL`: Logging level (default: "INFO")
- `FIREBASE_PATH`: Path in Firebase to listen to (default: "/")

### Secrets

Secrets are automatically mounted as environment variables:

- `FIREBASE_DATABASE_URL`: From `firebase-database-url` secret
- `GOOGLE_SERVICE_ACCOUNT_FILE`: From `firebase-service-account` secret (mounted as file)

### Resource Configuration

The default Cloud Run configuration includes:

- **Memory**: 512Mi
- **CPU**: 1 vCPU
- **Concurrency**: 10 requests per instance
- **Max Instances**: 5
- **Min Instances**: 0 (scales to zero)
- **Timeout**: 300 seconds

## Monitoring and Troubleshooting

### View Logs

```bash
# Stream logs
gcloud run services logs tail kommo-command --region=us-central1

# View recent logs
gcloud run services logs read kommo-command --region=us-central1
```

### Service Information

```bash
# Get service details
gcloud run services describe kommo-command --region=us-central1

# List all revisions
gcloud run revisions list --service=kommo-command --region=us-central1
```

### Common Issues

1. **Authentication Errors**: Ensure your Firebase service account key is properly uploaded as a secret
2. **Database Connection**: Verify your Firebase Database URL is correct and accessible
3. **Memory Issues**: Increase memory allocation if the service runs out of memory
4. **Timeout Issues**: Increase the timeout value for long-running operations

## Security Considerations

1. **Service Account Permissions**: Use a service account with minimal required permissions
2. **Network Security**: Consider using VPC connectors for additional network isolation
3. **Secrets Management**: Never commit secrets to version control; always use Google Secret Manager
4. **IAM**: Review and limit access to the Cloud Run service

## Cost Optimization

1. **Scaling**: The service is configured to scale to zero when not in use
2. **Resource Limits**: Adjust CPU and memory based on actual usage
3. **Regional Deployment**: Deploy in the region closest to your users

## Customization

### Changing Deployment Region

Edit `cloudbuild.yaml` and change the `--region` parameter:

```yaml
'--region', 'europe-west1',  # Change to your preferred region
```

### Adjusting Resources

Modify the resource settings in `cloudbuild.yaml`:

```yaml
'--memory', '1Gi',          # Increase memory
'--cpu', '2',               # Increase CPU
'--max-instances', '10',    # Increase max instances
```

### Custom Environment Variables

Add environment variables in the `--set-env-vars` parameter:

```yaml
'--set-env-vars', 'LOG_LEVEL=DEBUG,FIREBASE_PATH=/custom/path,CUSTOM_VAR=value',
```

## Development Workflow

1. **Local Testing**: Test changes locally using Docker
2. **Build and Deploy**: Use Cloud Build for consistent deployments
3. **Monitor**: Check logs and metrics after deployment
4. **Rollback**: Use revision management if issues occur

```bash
# Build locally for testing
docker build -t kommo-command .
docker run -p 8080:8080 kommo-command

# Deploy specific revision if needed
gcloud run services update-traffic kommo-command \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1
```
