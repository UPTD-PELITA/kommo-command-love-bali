"""Centralized catalog for user-facing messages grouped by language."""

from __future__ import annotations

from enum import Enum
from typing import Dict

from .types import AppLanguage


class MessageKey(str, Enum):
    """Identifiers for localized user-facing messages."""

    PASSPORT_PROMPT = "passport_prompt"
    PASSPORT_INVALID = "passport_invalid"
    PASSPORT_ERROR = "passport_error"
    PASSPORT_NOT_FOUND = "passport_not_found"
    PASSPORT_FOUND = "passport_found"


DEFAULT_LANGUAGE = AppLanguage.ENGLISH

# Registry of localized messages keyed by message identifier then language.
_MESSAGES: Dict[MessageKey, Dict[AppLanguage, str]] = {
    MessageKey.PASSPORT_PROMPT: {
        AppLanguage.ENGLISH: "Please enter your passport number",
        AppLanguage.INDONESIAN: "Silakan masukkan nomor paspor Anda",
    },
    MessageKey.PASSPORT_INVALID: {
        AppLanguage.ENGLISH: "Invalid passport number format",
        AppLanguage.INDONESIAN: "Format nomor paspor tidak valid",
    },
    MessageKey.PASSPORT_ERROR: {
        AppLanguage.ENGLISH: "An error occurred while processing your passport number. Please try again later.",
        AppLanguage.INDONESIAN: "Terjadi kesalahan saat memproses nomor paspor Anda. Silakan coba lagi nanti.",
    },
    MessageKey.PASSPORT_NOT_FOUND: {
        AppLanguage.ENGLISH: "Passport number not found in the database",
        AppLanguage.INDONESIAN: "Nomor paspor tidak ditemukan dalam database",
    },
    MessageKey.PASSPORT_FOUND: {
        AppLanguage.ENGLISH: (
            "Passport found.\n\n"
            "Voucher Code:\n{code_voucher}\n\n"
            "Guest Name:\n{guest_name}\n\n"
            "Arrival Date:\n{arrival_date}\n\n"
            "Expired Date:\n{expired_date}"
        ),
        AppLanguage.INDONESIAN: (
            "Paspor ditemukan.\n\n"
            "Kode Voucher:\n{code_voucher}\n\n"
            "Nama Tamu:\n{guest_name}\n\n"
            "Tanggal Kedatangan:\n{arrival_date}\n\n"
            "Tanggal Kedaluwarsa:\n{expired_date}"
        ),
    },
}


def _normalize_language(language: AppLanguage | str | None) -> AppLanguage:
    """Normalize incoming language inputs to a known AppLanguage value."""
    if isinstance(language, AppLanguage):
        return language

    if isinstance(language, str):
        cleaned = language.strip().upper()
        try:
            return AppLanguage(cleaned)
        except ValueError:
            pass

    return DEFAULT_LANGUAGE


def get_message(key: MessageKey, language: AppLanguage | str | None = None) -> str:
    """Return the localized message for the given key, falling back to default language."""
    by_language = _MESSAGES.get(key)
    if by_language is None:
        raise KeyError(f"No message configured for key: {key}")

    normalized_language = _normalize_language(language)
    message = by_language.get(normalized_language)
    if message is not None:
        return message

    default_message = by_language.get(DEFAULT_LANGUAGE)
    if default_message is not None:
        return default_message

    # Final fallback: return the first available translation to avoid raising at runtime.
    return next(iter(by_language.values()))


def get_message_catalog() -> Dict[MessageKey, Dict[AppLanguage, str]]:
    """Return a shallow copy of the message catalog for read-only operations."""
    return {key: dict(value) for key, value in _MESSAGES.items()}
