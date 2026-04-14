"""Kirimi SDK exceptions."""

from __future__ import annotations

from typing import Any


class KirimiError(Exception):
    """Base exception for all Kirimi SDK errors."""


class KirimiAPIError(KirimiError):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str, response_data: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"HTTP {status_code}: {message}")


class KirimiValidationError(KirimiError):
    """Raised when Pydantic validation fails."""


class KirimiConnectionError(KirimiError):
    """Raised when a network/connection error occurs."""
