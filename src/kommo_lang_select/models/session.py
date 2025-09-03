"""Session models for the kommo_lang_select application."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import Field

from .base import BaseFirestoreModel
from ..types import Command


class SessionModel(BaseFirestoreModel):
    """Session model for storing user session data in Firestore."""
    
    session_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique session identifier")
    entity_id: Optional[int] = Field(default=None, description="Entity identifier if authenticated")
    language: Optional[str] = Field(default=None, description="Selected language code (e.g., 'en', 'fr', 'de')")
    command: Optional[Command] = Field(default=None, description="Active command for user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Session creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Session expiration timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    is_active: bool = Field(default=True, description="Whether the session is active")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert the model to a Firestore-compatible dictionary."""
        data = self.model_dump()
        
        # Convert datetime objects to Firestore timestamps
        for field_name in ['created_at', 'updated_at', 'expires_at']:
            if data.get(field_name):
                # Firestore expects datetime objects, not ISO strings
                data[field_name] = data[field_name]
        
        # Convert Command enum to its value
        if isinstance(data.get('command'), Command):
            data['command'] = data['command'].value
        
        return data
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> SessionModel:
        """Create a SessionModel instance from Firestore data."""
        # Handle datetime fields that might come as Firestore timestamps
        for field_name in ['created_at', 'updated_at', 'expires_at']:
            if field_name in data and data[field_name]:
                if hasattr(data[field_name], 'timestamp'):
                    # Firestore timestamp object
                    data[field_name] = datetime.fromtimestamp(
                        data[field_name].timestamp(), 
                        tz=timezone.utc
                    )
                elif isinstance(data[field_name], str):
                    # ISO string
                    data[field_name] = datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
        
        # Convert command string back to enum
        if 'command' in data and data['command'] and isinstance(data['command'], str):
            try:
                data['command'] = Command(data['command'])
            except ValueError:
                # If the string doesn't match any enum value, set to None
                data['command'] = None
        
        # Convert entity_id string to int if necessary
        if 'entity_id' in data and data['entity_id'] and isinstance(data['entity_id'], str):
            try:
                data['entity_id'] = int(data['entity_id'])
            except ValueError:
                # If conversion fails, set to None
                data['entity_id'] = None
        
        return cls(**data)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to the current time."""
        self.updated_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def set_language(self, language: str) -> None:
        """Set the session language and update timestamp."""
        self.language = language
        self.update_timestamp()
    
    def deactivate(self) -> None:
        """Deactivate the session."""
        self.is_active = False
        self.update_timestamp()


class SessionCreateRequest(BaseFirestoreModel):
    """Request model for creating a new session."""
    
    entity_id: Optional[int] = None
    language: Optional[str] = None
    command: Optional[Command] = None
    expires_in_hours: Optional[int] = Field(default=1, ge=1, le=8760, description="Session duration in hours (max 1 year)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_session_model(self) -> SessionModel:
        """Convert to a SessionModel instance."""
        expires_at = None
        if self.expires_in_hours:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.expires_in_hours)
        
        return SessionModel(
            entity_id=self.entity_id,
            language=self.language,
            command=self.command,
            expires_at=expires_at,
            metadata=self.metadata
        )


class SessionUpdateRequest(BaseFirestoreModel):
    """Request model for updating an existing session."""
    
    language: Optional[str] = None
    command: Optional[Command] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=8760, description="Update session duration in hours")