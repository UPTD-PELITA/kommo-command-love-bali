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

    # Auth options: service account file is required for Firebase Admin SDK
    google_service_account_file: str | None = Field(
        default=None, description="Path to Google service account JSON file (required)"
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
            google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
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

    def auth_mode(self) -> str:
        if self.google_service_account_file:
            return "service_account"
        return "unauthenticated"
