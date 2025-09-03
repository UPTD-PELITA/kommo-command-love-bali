"""Lead model for storing lead information."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base import BaseFirestoreModel


class LeadModel(BaseFirestoreModel):
    """Model for storing lead information in Firestore."""
    
    lead_id: str
    source_path: str  # Original Firebase path where the lead came from
    data: Dict[str, Any]  # The actual lead data
    created_at: datetime
    updated_at: datetime
    processed: bool = False
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if 'lead_id' not in data:
            data['lead_id'] = str(uuid.uuid4())
        
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone.utc)
        
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now(timezone.utc)
            
        super().__init__(**data)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_processed(self) -> None:
        """Mark the lead as processed."""
        self.processed = True
        self.update_timestamp()
    
    @classmethod
    def from_firebase_event(
        cls,
        event_path: str,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> LeadModel:
        """
        Create a LeadModel from Firebase event data.
        
        Args:
            event_path: The Firebase path where the event occurred
            event_data: The event data
            metadata: Additional metadata
            
        Returns:
            LeadModel instance
        """
        return cls(
            source_path=event_path,
            data=event_data,
            metadata=metadata or {}
        )


class LeadCreateRequest(BaseFirestoreModel):
    """Request model for creating a new lead."""
    
    source_path: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_lead_model(self) -> LeadModel:
        """Convert to LeadModel."""
        return LeadModel.from_firebase_event(
            event_path=self.source_path,
            event_data=self.data,
            metadata=self.metadata
        )


class LeadUpdateRequest(BaseFirestoreModel):
    """Request model for updating a lead."""
    
    data: Optional[Dict[str, Any]] = None
    processed: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None