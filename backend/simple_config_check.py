#!/usr/bin/env python3
"""Compatibility entrypoint for the shared configuration check."""
from validate_config import validate_config

if __name__ == "__main__":
    raise SystemExit(0 if validate_config() else 1)
