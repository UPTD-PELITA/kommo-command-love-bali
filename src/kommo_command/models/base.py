"""Base model classes for the kommo_command application."""

from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel


class BaseFirestoreModel(BaseModel):
    """Base model for Firestore document models with common serialization methods."""
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {}
        
    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert the model to a Firestore-compatible dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> BaseFirestoreModel:
        """Create a model instance from Firestore data."""
        return cls(**data)