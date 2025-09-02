"""Configuration validation utilities for Firebase setup."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_firebase_project_id(firebase_url: str) -> str | None:
    """Extract project ID from Firebase Realtime Database URL."""
    if "firebaseio.com" in firebase_url:
        # Format: https://project-id-default-rtdb.firebaseio.com/
        match = re.search(r"https://([^.]+).*\.firebaseio\.com", firebase_url)
        if match:
            project_part = match.group(1)
            # Remove -default-rtdb suffix if present
            return project_part.replace("-default-rtdb", "")
    elif "firebasedatabase.app" in firebase_url:
        # Format: https://project-id-default-rtdb.europe-west1.firebasedatabase.app/
        match = re.search(r"https://([^.]+).*\.firebasedatabase\.app", firebase_url)
        if match:
            project_part = match.group(1)
            return project_part.replace("-default-rtdb", "")
    return None


def get_service_account_info(service_account_path: str) -> dict[str, str] | None:
    """Get project ID and email from service account file."""
    try:
        with open(service_account_path, 'r') as f:
            data = json.load(f)
            return {
                'project_id': data.get('project_id'),
                'client_email': data.get('client_email'),
                'type': data.get('type')
            }
    except Exception as e:
        logger.error(f"Failed to read service account file: {e}")
        return None


def suggest_firebase_url(service_account_path: str) -> str | None:
    """Suggest the correct Firebase URL based on service account project."""
    info = get_service_account_info(service_account_path)
    if info and info['project_id']:
        return f"https://{info['project_id']}-default-rtdb.firebaseio.com/"
    return None


def validate_firebase_config(firebase_url: str, service_account_path: str | None = None) -> list[str]:
    """Validate Firebase configuration and return list of issues/suggestions."""
    issues = []
    
    if not firebase_url:
        issues.append("Firebase database URL is required")
        return issues
    
    firebase_project = extract_firebase_project_id(firebase_url)
    if not firebase_project:
        issues.append(f"Could not extract project ID from Firebase URL: {firebase_url}")
    
    if service_account_path:
        if not Path(service_account_path).exists():
            issues.append(f"Service account file not found: {service_account_path}")
        else:
            service_info = get_service_account_info(service_account_path)
            if not service_info:
                issues.append("Could not read service account file")
            elif service_info['type'] != 'service_account':
                issues.append("Invalid service account file format")
            else:
                service_project = service_info['project_id']
                if firebase_project and service_project != firebase_project:
                    issues.append(
                        f"Project mismatch: Service account is for '{service_project}' "
                        f"but Firebase URL is for '{firebase_project}'"
                    )
                    suggested_url = suggest_firebase_url(service_account_path)
                    if suggested_url:
                        issues.append(f"Suggested Firebase URL: {suggested_url}")
                    issues.append(
                        f"Or get a service account for the '{firebase_project}' project"
                    )
    
    return issues


def print_config_help(firebase_url: str, service_account_path: str | None = None) -> None:
    """Print helpful configuration information."""
    print("\n🔧 Firebase Configuration Analysis")
    print("=" * 50)
    
    issues = validate_firebase_config(firebase_url, service_account_path)
    
    if not issues:
        print("✅ Configuration looks good!")
        return
    
    print("❌ Configuration Issues Found:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print("\n💡 Quick Fixes:")
    print("  1. Update FIREBASE_DATABASE_URL in your .env file to match your service account project")
    print("  2. Or get the correct service account file for your target Firebase project")
    print("  3. Ensure the service account has 'Firebase Realtime Database Editor' role")
    
    if service_account_path:
        service_info = get_service_account_info(service_account_path)
        if service_info:
            print(f"\n📋 Current Service Account: {service_info['client_email']}")
            print(f"🏷️  Project: {service_info['project_id']}")
    
    firebase_project = extract_firebase_project_id(firebase_url)
    if firebase_project:
        print(f"🎯 Target Firebase Project: {firebase_project}")