"""Kirimi Python SDK — Official client for the Kirimi WhatsApp API."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

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
    "__version__",
]

# Read the version from the installed distribution so it can never drift from
# pyproject.toml the way a hardcoded string does.
try:
    __version__ = _distribution_version("kirimi-sdk")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "0.0.0"
