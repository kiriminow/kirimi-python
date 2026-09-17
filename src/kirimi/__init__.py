"""Kirimi Python SDK — Official client for the Kirimi WhatsApp API."""

from .async_client import AsyncKirimi
from .client import Kirimi
from .exceptions import (
    KirimiAPIError,
    KirimiConnectionError,
    KirimiError,
    KirimiValidationError,
)
from .models import (
    BulkContact,
    DepositStatus,
    KirimiResponse,
    OtpMethod,
    OtpType,
)

__all__ = [
    "Kirimi",
    "AsyncKirimi",
    "KirimiError",
    "KirimiAPIError",
    "KirimiValidationError",
    "KirimiConnectionError",
    "KirimiResponse",
    "BulkContact",
    "DepositStatus",
    "OtpMethod",
    "OtpType",
]

__version__ = "0.1.0"
