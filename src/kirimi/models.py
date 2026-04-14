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
# Request models (internal, used for body construction)
# ---------------------------------------------------------------------------


class _AuthBase(BaseModel):
    """Fields injected automatically by the client."""

    user_code: str
    secret: str


class SendMessageRequest(_AuthBase):
    device_id: str
    phone: str
    message: str
    media_url: str | None = None


class SendMessageFastRequest(_AuthBase):
    device_id: str
    phone: str
    message: str
    media_url: str | None = None


class SendWabaMessageRequest(_AuthBase):
    device_id: str
    phone: str
    message: str


class DeviceRequest(_AuthBase):
    device_id: str


class UserInfoRequest(_AuthBase):
    pass


class ListDevicesRequest(_AuthBase):
    pass


class SaveContactRequest(_AuthBase):
    phone: str
    name: str | None = None
    email: str | None = None


OtpType = Literal["numeric", "alphabetic", "alphanumeric"]


class GenerateOtpRequest(_AuthBase):
    device_id: str
    phone: str
    otp_length: int | None = None
    otp_type: OtpType | None = None
    customOtpMessage: str | None = None  # noqa: N815 — matches API field name


class ValidateOtpRequest(_AuthBase):
    device_id: str
    phone: str
    otp: str


OtpMethod = Literal["device", "waba"]


class SendOtpV2Request(_AuthBase):
    phone: str
    device_id: str
    method: OtpMethod | None = None
    app_name: str | None = None
    template_code: str | None = None
    custom_message: str | None = None


class VerifyOtpV2Request(_AuthBase):
    phone: str
    otp_code: str


class BroadcastMessageRequest(_AuthBase):
    device_id: str
    phones: str
    message: str
    delay: float | None = None


DepositStatus = Literal["", "paid", "unpaid", "expired"]


class ListDepositsRequest(_AuthBase):
    status: DepositStatus | None = None


class ListPackagesRequest(_AuthBase):
    pass
