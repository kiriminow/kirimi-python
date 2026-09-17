"""Pydantic models for Kirimi API request and response."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base response
# ---------------------------------------------------------------------------


class KirimiResponse(BaseModel):
    """Generic response model returned by all Kirimi API endpoints."""

    success: bool
    data: Any | None = None
    message: str | None = None


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

OtpType = Literal["numeric", "alphabetic", "alphanumeric"]

OtpMethod = Literal["whatsapp", "waba", "device", "waba_user"]

DepositStatus = Literal["", "unpaid", "paid", "expired", "cancelled"]


# ---------------------------------------------------------------------------
# Request models (internal, used for body construction)
# ---------------------------------------------------------------------------


class _AuthBase(BaseModel):
    """Fields injected automatically by the client."""

    user_code: str
    secret: str


# ---------------------------------------------------------------------------
# WhatsApp Unofficial
# ---------------------------------------------------------------------------


class SendMessageRequest(_AuthBase):
    """Request body for ``/v1/send-message``."""

    device_id: str
    receiver: str
    message: str
    media_url: str | None = None
    fileName: str | None = None  # noqa: N815 — matches API field name
    enableTypingEffect: bool | None = None  # noqa: N815 — matches API field name
    typingSpeedMs: int | None = None  # noqa: N815 — matches API field name
    quotedMessageId: str | None = None  # noqa: N815 — matches API field name


class SendMessageFastRequest(_AuthBase):
    """Request body for ``/v1/send-message-fast``."""

    device_id: str
    receiver: str
    message: str
    media_url: str | None = None
    fileName: str | None = None  # noqa: N815 — matches API field name
    quotedMessageId: str | None = None  # noqa: N815 — matches API field name


class BulkContact(BaseModel):
    """A single recipient for a bulk contact save."""

    nama: str
    nomor: str


class BroadcastMessageRequest(_AuthBase):
    """Request body for ``/v1/broadcast-message``.

    ``numbers`` must be a list of recipient numbers — the API rejects a
    joined string and does not accept a ``phones`` field.
    """

    device_id: str
    label: str
    numbers: list[str]
    message: str
    delay: float | None = None
    delayMin: float | None = None  # noqa: N815 — matches API field name
    delayMax: float | None = None  # noqa: N815 — matches API field name
    media_url: str | None = None
    fileName: str | None = None  # noqa: N815 — matches API field name
    started_at: str | None = None
    enableTypingEffect: bool | None = None  # noqa: N815 — matches API field name
    typingSpeedMs: int | None = None  # noqa: N815 — matches API field name


# ---------------------------------------------------------------------------
# WABA
# ---------------------------------------------------------------------------


class SendWabaMessageRequest(_AuthBase):
    """Request body for ``/v1/waba/send-message``. Uses ``waba_id``, never ``device_id``."""

    waba_id: str
    to: str
    template_name: str
    variables: list[str] | None = None
    header: dict[str, Any] | None = None
    buttons: list[Any] | None = None


class WabaReplyRequest(_AuthBase):
    """Request body for ``/v1/waba/messages/reply``."""

    waba_id: str
    to: str
    message: dict[str, Any]


class WabaConversationsRequest(_AuthBase):
    """Request body for ``/v1/waba/conversations``."""

    limit: int | None = None
    page: int | None = None


class WabaTemplateSyncRequest(_AuthBase):
    """Request body for ``/v1/waba/templates/sync``."""

    waba_id: str


class WabaSendOtpRequest(_AuthBase):
    """Request body for ``/v1/waba/send-otp``."""

    waba_id: str
    to: str
    template_name: str


class WabaVerifyOtpRequest(_AuthBase):
    """Request body for ``/v1/waba/verify-otp``."""

    waba_id: str
    to: str
    otp_code: str


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


class DeviceRequest(_AuthBase):
    """Request body for endpoints that only need a device ID."""

    device_id: str


class CreateDeviceRequest(_AuthBase):
    """Request body for ``/v1/create-device``."""

    package_id: str | int
    voucher_code: str | None = None


class ConnectDeviceRequest(_AuthBase):
    """Request body for ``/v1/connect-device``."""

    device_id: str


class RenewDeviceRequest(_AuthBase):
    """Request body for ``/v1/renew-device``."""

    device_id: str
    package_id: str | int
    voucher_code: str | None = None


class UserInfoRequest(_AuthBase):
    """Request body for ``/v1/user-info``."""

    pass


class ListDevicesRequest(_AuthBase):
    """Request body for ``/v1/list-devices``."""

    pass


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


class SaveContactRequest(_AuthBase):
    """Request body for ``/v1/save-contact``.

    The API only accepts ``nama`` + ``nomor``; ``name``/``phone`` are rejected.
    """

    nama: str
    nomor: str
    device_id: str | None = None


class SaveContactsBulkRequest(_AuthBase):
    """Request body for ``/v1/save-contacts-bulk``."""

    contacts: list[BulkContact]
    device_id: str | None = None


# ---------------------------------------------------------------------------
# OTP v1
# ---------------------------------------------------------------------------


class GenerateOtpRequest(_AuthBase):
    """Request body for ``/v1/generate-otp``."""

    device_id: str
    phone: str
    otp_length: int | None = None
    otp_type: OtpType | None = None
    customOtpText: str | None = None  # noqa: N815 — matches API field name
    customOtpMessage: str | None = None  # noqa: N815 — matches API field name
    enableTypingEffect: bool | None = None  # noqa: N815 — matches API field name
    typingSpeedMs: int | None = None  # noqa: N815 — matches API field name


class ValidateOtpRequest(_AuthBase):
    """Request body for ``/v1/validate-otp``."""

    device_id: str
    phone: str
    otp: str


# ---------------------------------------------------------------------------
# OTP v2
# ---------------------------------------------------------------------------


class SendOtpV2Request(_AuthBase):
    """Request body for ``/v2/otp/send``.

    ``method`` is one of ``whatsapp``, ``device`` or ``waba_user``.

    - ``whatsapp``: uses the Kirimi provider, only ``phone`` + ``app_name``.
    - ``device``: requires ``device_id`` and ``custom_message`` (``{{otp}}``).
    - ``waba_user``: requires ``waba_id`` and ``template_name``.
    """

    phone: str
    method: OtpMethod | None = None
    app_name: str | None = None
    device_id: str | None = None
    waba_id: str | None = None
    template_name: str | None = None
    custom_message: str | None = None


class VerifyOtpV2Request(_AuthBase):
    """Request body for ``/v2/otp/verify``."""

    phone: str
    otp_code: str


# ---------------------------------------------------------------------------
# OTP Reverse
# ---------------------------------------------------------------------------


class OtpReverseCreateRequest(_AuthBase):
    """Request body for ``/v2/otp-reverse/create``."""

    phone: str
    device_id: str
    app_name: str | None = None
    callback_url: str | None = None
    custom_message: str | None = None
    success_message: str | None = None
    failure_message: str | None = None


class OtpReverseStatusRequest(_AuthBase):
    """Request body for ``/v2/otp-reverse/status``."""

    token: str


# ---------------------------------------------------------------------------
# Packages & Deposits
# ---------------------------------------------------------------------------


class ListDepositsRequest(_AuthBase):
    """Request body for ``/v1/list-deposits``."""

    page: int | None = None
    limit: int | None = None
    status: DepositStatus | None = None


class ListPackagesRequest(_AuthBase):
    """Request body for ``/v1/list-packages``."""

    pass


class CreateDepositRequest(_AuthBase):
    """Request body for ``/v1/create-deposit``."""

    nominal: float | int


class DepositRefRequest(_AuthBase):
    """Request body for ``/v1/deposit-status`` and ``/v1/cancel-deposit``."""

    ref: str
