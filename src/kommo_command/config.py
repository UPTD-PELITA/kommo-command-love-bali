from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    firebase_database_url: str = Field(
        ...,
        description=(
            "Firebase Realtime Database root URL, e.g. "
            "https://<project-id>-default-rtdb.firebaseio.com"
        ),
    )
    firebase_path: str = Field(
        "/", description="Path within the Realtime DB to listen to, default root"
    )

    # Firestore configuration
    firebase_project_id: str = Field(
        ...,
        description="Firebase project ID for Firestore database"
    )
    firestore_database_name: str = Field(
        default="kommo-webhook",
        description="Firestore database name (default: kommo-webhook)"
    )

    # Auth options: service account file is required for Firebase Admin SDK
    google_service_account_file: str | None = Field(
        default=None, description="Path to Google service account JSON file (required)"
    )

    # Kommo API configuration
    kommo_client_id: str = Field(
        ...,
        description="Kommo OAuth client ID"
    )
    kommo_client_secret: str = Field(
        ...,
        description="Kommo OAuth client secret"
    )
    kommo_subdomain: str = Field(
        ...,
        description="Kommo account subdomain (e.g., 'example' for example.kommo.com)"
    )
    kommo_access_token: str = Field(
        ...,
        description="Kommo API access token"
    )

    love_bali_base_url: str = Field(
        default="https://lovebali.baliprov.go.id/api/v2/",
        description="Base URL for the Love Bali API"
    )
    love_bali_api_token: str = Field(
        default="",
        description="Bearer token for Love Bali API requests"
    )

    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("firebase_path")
    @classmethod
    def ensure_leading_slash(cls, v: str) -> str:
        if not v.startswith("/"):
            return "/" + v
        return v

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            firebase_database_url=os.getenv("FIREBASE_DATABASE_URL", "").rstrip("/"),
            firebase_path=os.getenv("FIREBASE_PATH", "/"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
            firestore_database_name=os.getenv("FIRESTORE_DATABASE_NAME", "kommo-webhook"),
            google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
            kommo_client_id=os.getenv("KOMMO_CLIENT_ID", ""),
            kommo_client_secret=os.getenv("KOMMO_CLIENT_SECRET", ""),
            kommo_subdomain=os.getenv("KOMMO_SUBDOMAIN", ""),
            kommo_access_token=os.getenv("KOMMO_ACCESS_TOKEN", ""),
            love_bali_base_url=os.getenv(
                "LOVE_BALI_BASE_URL",
                "https://lovebali.baliprov.go.id/api/v2/",
            ),
            love_bali_api_token=os.getenv("LOVE_BALI_API_TOKEN", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    @field_validator("firebase_database_url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("FIREBASE_DATABASE_URL must start with http:// or https://")
        return v

    @field_validator("firebase_project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("FIREBASE_PROJECT_ID is required")
        return v

    @field_validator("kommo_client_id")
    @classmethod
    def validate_kommo_client_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("KOMMO_CLIENT_ID is required")
        return v

    @field_validator("kommo_client_secret")
    @classmethod
    def validate_kommo_client_secret(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("KOMMO_CLIENT_SECRET is required")
        return v

    @field_validator("kommo_subdomain")
    @classmethod
    def validate_kommo_subdomain(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("KOMMO_SUBDOMAIN is required")
        return v

    @field_validator("kommo_access_token")
    @classmethod
    def validate_kommo_access_token(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("KOMMO_ACCESS_TOKEN is required")
        return v

    @field_validator("love_bali_base_url")
    @classmethod
    def validate_love_bali_base_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return "https://lovebali.baliprov.go.id/api/v2/"
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("LOVE_BALI_BASE_URL must start with http:// or https://")
        return v if v.endswith("/") else f"{v}/"

    @field_validator("love_bali_api_token")
    @classmethod
    def normalize_love_bali_api_token(cls, v: str) -> str:
        return v.strip()

    def auth_mode(self) -> str:
        if self.google_service_account_file:
            return "service_account"
        return "unauthenticated"
