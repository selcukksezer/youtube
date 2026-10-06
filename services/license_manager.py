"""
services/license_manager.py — Backward-compatible facade for LicenseManager.
Exports get_license, save_license, delete_license, is_activated, validate_key.
Backed by machine-local AES-256-GCM encrypted SecretVault (Plan Section 28.2).
"""
from services.secret_vault import (
    LicenseManager,
    delete_license,
    get_license,
    is_activated,
    license_manager,
    save_license,
    validate_key,
)

__all__ = [
    "LicenseManager",
    "license_manager",
    "get_license",
    "save_license",
    "delete_license",
    "is_activated",
    "validate_key",
]
