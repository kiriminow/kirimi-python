"""Synchronous Kirimi API client."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO

import httpx
from pydantic import ValidationError

from .exceptions import KirimiAPIError, KirimiConnectionError, KirimiValidationError
from .models import (
    BroadcastMessageRequest,
    DepositStatus,
    GenerateOtpRequest,
    KirimiResponse,
    ListDepositsRequest,
    ListDevicesRequest,
    ListPackagesRequest,
    OtpMethod,
    OtpType,
    SaveContactRequest,
    SendMessageFastRequest,
    SendMessageRequest,
    SendOtpV2Request,
    SendWabaMessageRequest,
    UserInfoRequest,
    ValidateOtpRequest,
    VerifyOtpV2Request,
)

_DEFAULT_BASE_URL = "https://api.kirimi.id"
_DEFAULT_TIMEOUT = 30.0


class Kirimi:
    """Synchronous client for the Kirimi WhatsApp API.

    Args:
        user_code: Your Kirimi user code.
        secret: Your Kirimi secret key.
        base_url: API base URL. Defaults to ``https://api.kirimi.id``.
        timeout: Request timeout in seconds. Defaults to 30.
        http_client: Optional custom :class:`httpx.Client` instance.
    """

    def __init__(
        self,
        user_code: str,
        secret: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._user_code = user_code
        self._secret = secret
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth(self) -> dict[str, str]:
        return {"user_code": self._user_code, "secret": self._secret}

    def _post(self, path: str, body: dict[str, Any]) -> KirimiResponse:
        url = f"{self._base_url}{path}"
        # Remove None values so optional fields are not sent
        payload = {k: v for k, v in body.items() if v is not None}
        try:
            resp = self._client.post(url, json=payload)
        except httpx.TransportError as exc:
            raise KirimiConnectionError(str(exc)) from exc

        if not resp.is_success:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise KirimiAPIError(resp.status_code, detail, resp.text)

        try:
            return KirimiResponse.model_validate(resp.json())
        except ValidationError as exc:
            raise KirimiValidationError(str(exc)) from exc

    def _post_multipart(
        self,
        path: str,
        data: dict[str, Any],
        files: dict[str, Any],
    ) -> KirimiResponse:
        url = f"{self._base_url}{path}"
        # Remove None values
        clean_data = {k: str(v) for k, v in data.items() if v is not None}
        try:
            resp = self._client.post(url, data=clean_data, files=files)
        except httpx.TransportError as exc:
            raise KirimiConnectionError(str(exc)) from exc

        if not resp.is_success:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise KirimiAPIError(resp.status_code, detail, resp.text)

        try:
            return KirimiResponse.model_validate(resp.json())
        except ValidationError as exc:
            raise KirimiValidationError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "Kirimi":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client (only if owned by this instance)."""
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        device_id: str,
        phone: str,
        message: str,
        media_url: str | None = None,
    ) -> KirimiResponse:
        """Send a text/media message to one recipient.

        Args:
            device_id: Device ID to send from.
            phone: Recipient phone number (e.g. ``628123456789``).
            message: Message text.
            media_url: Optional media URL to attach.
        """
        req = SendMessageRequest(
            **self._auth(),
            device_id=device_id,
            phone=phone,
            message=message,
            media_url=media_url,
        )
        return self._post("/v1/send-message", req.model_dump())

    def send_message_file(
        self,
        device_id: str,
        phone: str,
        file: BinaryIO | bytes | Path,
        file_name: str | None = None,
        message: str | None = None,
    ) -> KirimiResponse:
        """Send a file as a WhatsApp message (multipart upload, max 50 MB).

        Args:
            device_id: Device ID to send from.
            phone: Recipient phone number.
            file: File to send — accepts a file-like object, raw bytes, or a
                :class:`pathlib.Path`.
            file_name: Optional display name for the file.
            message: Optional caption text.
        """
        if isinstance(file, Path):
            file_name = file_name or file.name
            file_bytes = file.read_bytes()
            file_obj: BinaryIO = io.BytesIO(file_bytes)
        elif isinstance(file, bytes):
            file_obj = io.BytesIO(file)
        else:
            file_obj = file

        data = {
            **self._auth(),
            "device_id": device_id,
            "phone": phone,
            "message": message,
            "fileName": file_name,
        }
        files = {"file": (file_name, file_obj, "application/octet-stream")}
        return self._post_multipart("/v1/send-message-file", data, files)

    def send_message_fast(
        self,
        device_id: str,
        phone: str,
        message: str,
        media_url: str | None = None,
    ) -> KirimiResponse:
        """Send a message without the typing indicator effect.

        Args:
            device_id: Device ID to send from.
            phone: Recipient phone number.
            message: Message text.
            media_url: Optional media URL to attach.
        """
        req = SendMessageFastRequest(
            **self._auth(),
            device_id=device_id,
            phone=phone,
            message=message,
            media_url=media_url,
        )
        return self._post("/v1/send-message-fast", req.model_dump())

    def send_waba_message(
        self,
        device_id: str,
        phone: str,
        message: str,
    ) -> KirimiResponse:
        """Send a message via WhatsApp Business API (Meta Cloud API).

        Args:
            device_id: WABA device ID.
            phone: Recipient phone number.
            message: Message text.
        """
        req = SendWabaMessageRequest(
            **self._auth(),
            device_id=device_id,
            phone=phone,
            message=message,
        )
        return self._post("/v1/waba/send-message", req.model_dump())

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    def list_devices(self) -> KirimiResponse:
        """Return a list of all registered devices."""
        req = ListDevicesRequest(**self._auth())
        return self._post("/v1/list-devices", req.model_dump())

    def device_status(self, device_id: str) -> KirimiResponse:
        """Check connection status of a device.

        Args:
            device_id: Device ID to check.
        """
        return self._post("/v1/device-status", {**self._auth(), "device_id": device_id})

    def device_status_enhanced(self, device_id: str) -> KirimiResponse:
        """Get full enhanced status details of a device.

        Args:
            device_id: Device ID to check.
        """
        return self._post("/v1/device-status-enhanced", {**self._auth(), "device_id": device_id})

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    def user_info(self) -> KirimiResponse:
        """Return account information for the authenticated user."""
        req = UserInfoRequest(**self._auth())
        return self._post("/v1/user-info", req.model_dump())

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def save_contact(
        self,
        phone: str,
        name: str | None = None,
        email: str | None = None,
    ) -> KirimiResponse:
        """Save a contact to your Kirimi address book.

        Args:
            phone: Contact phone number.
            name: Optional contact name.
            email: Optional contact email.
        """
        req = SaveContactRequest(**self._auth(), phone=phone, name=name, email=email)
        return self._post("/v1/save-contact", req.model_dump())

    # ------------------------------------------------------------------
    # OTP v1
    # ------------------------------------------------------------------

    def generate_otp(
        self,
        device_id: str,
        phone: str,
        otp_length: int | None = None,
        otp_type: OtpType | None = None,
        custom_otp_message: str | None = None,
    ) -> KirimiResponse:
        """Generate and send an OTP via a WhatsApp device.

        Args:
            device_id: Device ID to send from.
            phone: Recipient phone number.
            otp_length: Length of the generated OTP code.
            otp_type: OTP character set — ``"numeric"``, ``"alphabetic"``, or
                ``"alphanumeric"``.
            custom_otp_message: Custom message template containing ``{otp}``
                placeholder (e.g. ``"Kode OTP Anda: {otp}"``).
        """
        req = GenerateOtpRequest(
            **self._auth(),
            device_id=device_id,
            phone=phone,
            otp_length=otp_length,
            otp_type=otp_type,
            customOtpMessage=custom_otp_message,
        )
        return self._post("/v1/generate-otp", req.model_dump())

    def validate_otp(
        self,
        device_id: str,
        phone: str,
        otp: str,
    ) -> KirimiResponse:
        """Validate a previously sent OTP code.

        Args:
            device_id: Device ID used when generating the OTP.
            phone: Recipient phone number.
            otp: The OTP code to validate.
        """
        req = ValidateOtpRequest(**self._auth(), device_id=device_id, phone=phone, otp=otp)
        return self._post("/v1/validate-otp", req.model_dump())

    # ------------------------------------------------------------------
    # OTP v2
    # ------------------------------------------------------------------

    def send_otp_v2(
        self,
        phone: str,
        device_id: str,
        method: OtpMethod | None = None,
        app_name: str | None = None,
        template_code: str | None = None,
        custom_message: str | None = None,
    ) -> KirimiResponse:
        """Send an OTP via WABA template or a WhatsApp device (V2).

        Args:
            phone: Recipient phone number.
            device_id: Device ID to use.
            method: Send method — ``"device"`` or ``"waba"``.
            app_name: Application name displayed in the OTP message.
            template_code: WABA template code (only for ``method="waba"``).
            custom_message: Custom message template (only for ``method="device"``).
        """
        req = SendOtpV2Request(
            **self._auth(),
            phone=phone,
            device_id=device_id,
            method=method,
            app_name=app_name,
            template_code=template_code,
            custom_message=custom_message,
        )
        return self._post("/v2/otp/send", req.model_dump())

    def verify_otp_v2(self, phone: str, otp_code: str) -> KirimiResponse:
        """Verify an OTP code (V2).

        Args:
            phone: Recipient phone number.
            otp_code: The OTP code to verify.
        """
        req = VerifyOtpV2Request(**self._auth(), phone=phone, otp_code=otp_code)
        return self._post("/v2/otp/verify", req.model_dump())

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    def broadcast_message(
        self,
        device_id: str,
        phones: str | list[str],
        message: str,
        delay: float | None = None,
    ) -> KirimiResponse:
        """Broadcast a message to multiple recipients.

        Args:
            device_id: Device ID to send from.
            phones: Recipient phone numbers — either a comma-separated string
                or a list of phone number strings.
            message: Message text.
            delay: Delay in seconds between each message.
        """
        phones_str = ",".join(phones) if isinstance(phones, list) else phones
        req = BroadcastMessageRequest(
            **self._auth(),
            device_id=device_id,
            phones=phones_str,
            message=message,
            delay=delay,
        )
        return self._post("/v1/broadcast-message", req.model_dump())

    # ------------------------------------------------------------------
    # Deposits & Packages
    # ------------------------------------------------------------------

    def list_deposits(self, status: DepositStatus | None = None) -> KirimiResponse:
        """Return a list of deposits.

        Args:
            status: Filter by status — ``"paid"``, ``"unpaid"``, ``"expired"``,
                or ``""`` / ``None`` for all.
        """
        req = ListDepositsRequest(**self._auth(), status=status)
        return self._post("/v1/list-deposits", req.model_dump())

    def list_packages(self) -> KirimiResponse:
        """Return available Kirimi packages."""
        req = ListPackagesRequest(**self._auth())
        return self._post("/v1/list-packages", req.model_dump())
