#!/usr/bin/env python3
"""Check configuration without printing secrets or making network calls."""
import os
from pathlib import Path
from dotenv import load_dotenv


def validate_config():
    load_dotenv(Path(__file__).with_name(".env"))
    valid = True
    for name in ("GOOGLE_API_KEY", "GOOGLE_MAPS_API_KEY", "FIREBASE_PROJECT_ID"):
        value = os.getenv(name, "").strip()
        configured = bool(value) and not value.startswith("your-")
        print(f"{name}: {'configured' if configured else 'missing or placeholder'}")
        valid = valid and configured
    storage = os.getenv("STORAGE_BACKEND", "firestore").lower()
    storage_valid = storage in ("memory", "firestore")
    if storage == "memory" and os.getenv("K_SERVICE"):
        storage_valid = False
    print(f"STORAGE_BACKEND: {storage if storage_valid else 'invalid for this environment'}")
    if storage == "firestore":
        print("Firestore requires application default credentials and an accessible default database.")
    return valid and storage_valid


if __name__ == "__main__":
    raise SystemExit(0 if validate_config() else 1)
