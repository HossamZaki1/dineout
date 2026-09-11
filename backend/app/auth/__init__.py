"""Request authentication against Firebase Auth."""

from .dependencies import (
    AuthenticationError,
    current_user_id,
    initialize_firebase,
)

__all__ = ["AuthenticationError", "current_user_id", "initialize_firebase"]
