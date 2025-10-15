"""Factory functions for creating service instances."""

from __future__ import annotations

from .config import Settings
from .services import (
    KommoAPIService,
    FirestoreService,
    FirebaseAdminListener,
    LoveBaliAPIService,
)


def create_kommo_service(settings: Settings) -> KommoAPIService:
    """
    Create a Kommo API service instance from settings.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured KommoAPIService instance
    """
    return KommoAPIService(
        client_id=settings.kommo_client_id,
        client_secret=settings.kommo_client_secret,
        subdomain=settings.kommo_subdomain,
        access_token=settings.kommo_access_token,
    )


def create_firestore_service(settings: Settings) -> FirestoreService:
    """
    Create a Firestore service instance from settings.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured FirestoreService instance
    """
    return FirestoreService(
        project_id=settings.firebase_project_id,
        database_name=settings.firestore_database_name,
        service_account_path=settings.google_service_account_file,
    )


def create_firebase_listener(settings: Settings) -> FirebaseAdminListener:
    """
    Create a Firebase Admin listener instance from settings.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured FirebaseAdminListener instance
    """
    return FirebaseAdminListener(
        database_url=settings.firebase_database_url,
        path=settings.firebase_path,
        service_account_path=settings.google_service_account_file,
    )


def create_love_bali_service(settings: Settings) -> LoveBaliAPIService:
    """
    Create a Love Bali API service instance from settings.

    Args:
        settings: Application settings

    Returns:
        Configured LoveBaliAPIService instance
    """
    return LoveBaliAPIService(
        base_url=settings.love_bali_base_url,
        api_token=settings.love_bali_api_token,
    )