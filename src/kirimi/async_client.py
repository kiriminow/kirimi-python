"""Asynchronous Kirimi API client."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO, Iterable, Mapping

import httpx
from pydantic import ValidationError

from .exceptions import KirimiAPIError, KirimiConnectionError, KirimiValidationError
from .models import (
    BroadcastMessageRequest,
    BulkContact,
    ConnectDeviceRequest,
    CreateDepositRequest,
    CreateDeviceRequest,
    DepositRefRequest,
    DepositStatus,
    GenerateOtpRequest,
    KirimiResponse,
    ListDepositsRequest,
    ListDevicesRequest,
    ListPackagesRequest,
    OtpMethod,
    OtpReverseCreateRequest,
    OtpReverseStatusRequest,
    OtpType,
    RenewDeviceRequest,
    SaveContactRequest,
    SaveContactsBulkRequest,
    SendMessageFastRequest,
    SendMessageRequest,
    SendOtpV2Request,
    SendWabaMessageRequest,
    UserInfoRequest,
    ValidateOtpRequest,
    VerifyOtpV2Request,
    WabaConversationsRequest,
    WabaReplyRequest,
    WabaSendOtpRequest,
    WabaTemplateSyncRequest,
    WabaVerifyOtpRequest,
)

_DEFAULT_BASE_URL = "https://api.kirimi.id"
_DEFAULT_TIMEOUT = 30.0


class AsyncKirimi:
    """Asynchronous client for the Kirimi WhatsApp API.

    Recommended usage as an async context manager::

        async with AsyncKirimi(user_code="...", secret="...") as client:
            resp = await client.send_message(device_id="DEV", receiver="628xxx", message="hi")

    Args:
        user_code: Your Kirimi user code.
        secret: Your Kirimi secret key.
        base_url: API base URL. Defaults to ``https://api.kirimi.id``.
        timeout: Request timeout in seconds. Defaults to 30.
        http_client: Optional custom :class:`httpx.AsyncClient` instance.
    """

    def __init__(
        self,
        user_code: str,
        secret: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._user_code = user_code
        self._secret = secret
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth(self) -> dict[str, str]:
        return {"user_code": self._user_code, "secret": self._secret}

    async def _post(self, path: str, body: dict[str, Any]) -> KirimiResponse:
        url = f"{self._base_url}{path}"
        payload = {k: v for k, v in body.items() if v is not None}
        try:
            resp = await self._client.post(url, json=payload)
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

    async def _post_multipart(
        self,
        path: str,
        data: dict[str, Any],
        files: dict[str, Any],
    ) -> KirimiResponse:
        url = f"{self._base_url}{path}"
        clean_data = {k: str(v) for k, v in data.items() if v is not None}
        try:
            resp = await self._client.post(url, data=clean_data, files=files)
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

    async def __aenter__(self) -> "AsyncKirimi":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client (only if owned by this instance)."""
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # WhatsApp Unofficial — Messaging
    # ------------------------------------------------------------------

    async def send_message(
        self,
        device_id: str,
        receiver: str,
        message: str,
        media_url: str | None = None,
        file_name: str | None = None,
        enable_typing_effect: bool | None = None,
        typing_speed_ms: int | None = None,
        quoted_message_id: str | None = None,
    ) -> KirimiResponse:
        """Send a text/media message to one recipient.

        Args:
            device_id: Device ID to send from.
            receiver: Recipient phone number (e.g. ``628123456789``).
            message: Message text.
            media_url: Optional media URL to attach.
            file_name: Optional custom media filename.
            enable_typing_effect: Simulate typing before sending.
            typing_speed_ms: Typing speed in ms (100–800).
            quoted_message_id: Message ID to quote/reply to.
        """
        req = SendMessageRequest(
            **self._auth(),
            device_id=device_id,
            receiver=receiver,
            message=message,
            media_url=media_url,
            fileName=file_name,
            enableTypingEffect=enable_typing_effect,
            typingSpeedMs=typing_speed_ms,
            quotedMessageId=quoted_message_id,
        )
        return await self._post("/v1/send-message", req.model_dump())

    async def send_message_file(
        self,
        device_id: str,
        receiver: str,
        file: BinaryIO | bytes | Path,
        file_name: str | None = None,
        message: str | None = None,
        caption: str | None = None,
        quoted_message_id: str | None = None,
    ) -> KirimiResponse:
        """Send a file as a WhatsApp message (multipart upload, max 50 MB).

        Args:
            device_id: Device ID to send from.
            receiver: Recipient phone number.
            file: File to send — accepts a file-like object, raw bytes, or a
                :class:`pathlib.Path`.
            file_name: Optional display name for the file.
            message: Optional caption text.
            caption: Optional caption for the uploaded media.
            quoted_message_id: Message ID to quote/reply to.
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
            "receiver": receiver,
            "message": message,
            "caption": caption,
            "fileName": file_name,
            "quotedMessageId": quoted_message_id,
        }
        files = {"file": (file_name, file_obj, "application/octet-stream")}
        return await self._post_multipart("/v1/send-message-file", data, files)

    async def send_message_fast(
        self,
        device_id: str,
        receiver: str,
        message: str,
        media_url: str | None = None,
        file_name: str | None = None,
        quoted_message_id: str | None = None,
    ) -> KirimiResponse:
        """Send a message without the typing indicator effect.

        Args:
            device_id: Device ID to send from.
            receiver: Recipient phone number.
            message: Message text.
            media_url: Optional media URL to attach.
            file_name: Optional custom media filename.
            quoted_message_id: Message ID to quote/reply to.
        """
        req = SendMessageFastRequest(
            **self._auth(),
            device_id=device_id,
            receiver=receiver,
            message=message,
            media_url=media_url,
            fileName=file_name,
            quotedMessageId=quoted_message_id,
        )
        return await self._post("/v1/send-message-fast", req.model_dump())

    async def broadcast_message(
        self,
        device_id: str,
        label: str,
        numbers: Iterable[str],
        message: str,
        delay: float | None = None,
        delay_min: float | None = None,
        delay_max: float | None = None,
        media_url: str | None = None,
        file_name: str | None = None,
        started_at: str | None = None,
        enable_typing_effect: bool | None = None,
        typing_speed_ms: int | None = None,
    ) -> KirimiResponse:
        """Broadcast a message to multiple recipients.

        Args:
            device_id: Device ID to send from.
            label: Broadcast label for identification (max 100 chars).
            numbers: Recipient phone numbers as a list (max 1000).
            message: Message text.
            delay: Delay in seconds between each message (server clamps 30–3600).
            delay_min: Lower bound of the random delay in seconds.
            delay_max: Upper bound of the random delay in seconds.
            media_url: Optional media URL to attach.
            file_name: Optional custom media filename.
            started_at: Scheduled start time (ISO 8601).
            enable_typing_effect: Simulate typing before sending.
            typing_speed_ms: Typing speed in ms (100–800).
        """
        req = BroadcastMessageRequest(
            **self._auth(),
            device_id=device_id,
            label=label,
            numbers=list(numbers),
            message=message,
            delay=delay,
            delayMin=delay_min,
            delayMax=delay_max,
            media_url=media_url,
            fileName=file_name,
            started_at=started_at,
            enableTypingEffect=enable_typing_effect,
            typingSpeedMs=typing_speed_ms,
        )
        return await self._post("/v1/broadcast-message", req.model_dump())

    # ------------------------------------------------------------------
    # WABA
    # ------------------------------------------------------------------

    async def send_waba_message(
        self,
        waba_id: str,
        to: str,
        template_name: str,
        variables: list[str] | None = None,
        header: dict[str, Any] | None = None,
        buttons: list[Any] | None = None,
    ) -> KirimiResponse:
        """Send a Meta-approved template via WhatsApp Business API.

        Args:
            waba_id: WhatsApp Business Account ID (not the device ID).
            to: Recipient phone number.
            template_name: Meta-approved template name.
            variables: Template body variables in order.
            header: Header component (media or dynamic text headers).
            buttons: Template button parameters.
        """
        req = SendWabaMessageRequest(
            **self._auth(),
            waba_id=waba_id,
            to=to,
            template_name=template_name,
            variables=variables,
            header=header,
            buttons=buttons,
        )
        return await self._post("/v1/waba/send-message", req.model_dump())

    async def waba_reply(
        self,
        waba_id: str,
        to: str,
        message: dict[str, Any],
    ) -> KirimiResponse:
        """Send a free-form reply inside the 24h customer service window.

        Args:
            waba_id: WhatsApp Business Account ID.
            to: The number that contacted you first.
            message: Meta message object, e.g. ``{"type": "text", "text": "hi"}``.
        """
        req = WabaReplyRequest(**self._auth(), waba_id=waba_id, to=to, message=message)
        return await self._post("/v1/waba/messages/reply", req.model_dump())

    async def waba_conversations(
        self,
        limit: int | None = None,
        page: int | None = None,
    ) -> KirimiResponse:
        """List conversations still inside the 24h customer service window.

        Args:
            limit: Page size, 1–200. Defaults to 50.
            page: Page number, 1-based.
        """
        req = WabaConversationsRequest(**self._auth(), limit=limit, page=page)
        return await self._post("/v1/waba/conversations", req.model_dump())

    async def waba_templates_sync(self, waba_id: str) -> KirimiResponse:
        """Refresh template status from Meta for one WABA.

        Args:
            waba_id: WhatsApp Business Account ID.
        """
        req = WabaTemplateSyncRequest(**self._auth(), waba_id=waba_id)
        return await self._post("/v1/waba/templates/sync", req.model_dump())

    async def waba_send_otp(
        self,
        waba_id: str,
        to: str,
        template_name: str,
    ) -> KirimiResponse:
        """Send an OTP through your own WABA + AUTHENTICATION template.

        Args:
            waba_id: WhatsApp Business Account ID.
            to: Recipient phone number.
            template_name: AUTHENTICATION category template, APPROVED status.
        """
        req = WabaSendOtpRequest(
            **self._auth(), waba_id=waba_id, to=to, template_name=template_name
        )
        return await self._post("/v1/waba/send-otp", req.model_dump())

    async def waba_verify_otp(
        self,
        waba_id: str,
        to: str,
        otp_code: str,
    ) -> KirimiResponse:
        """Verify an OTP previously sent through :meth:`waba_send_otp`.

        Args:
            waba_id: WhatsApp Business Account ID.
            to: Recipient phone number.
            otp_code: The OTP code to verify (4–8 digits).
        """
        req = WabaVerifyOtpRequest(**self._auth(), waba_id=waba_id, to=to, otp_code=otp_code)
        return await self._post("/v1/waba/verify-otp", req.model_dump())

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    async def create_device(
        self,
        package_id: str | int,
        voucher_code: str | None = None,
    ) -> KirimiResponse:
        """Create a new device.

        Args:
            package_id: Package ID for the new device.
            voucher_code: Optional discount voucher code.
        """
        req = CreateDeviceRequest(
            **self._auth(), package_id=package_id, voucher_code=voucher_code
        )
        return await self._post("/v1/create-device", req.model_dump())

    async def connect_device(self, device_id: str) -> KirimiResponse:
        """Connect a device and obtain its QR/session state.

        Args:
            device_id: Device ID to connect.
        """
        req = ConnectDeviceRequest(**self._auth(), device_id=device_id)
        return await self._post("/v1/connect-device", req.model_dump())

    async def renew_device(
        self,
        device_id: str,
        package_id: str | int,
        voucher_code: str | None = None,
    ) -> KirimiResponse:
        """Renew a device subscription.

        Args:
            device_id: Device ID to renew.
            package_id: Package ID to renew with.
            voucher_code: Optional discount voucher code.
        """
        req = RenewDeviceRequest(
            **self._auth(),
            device_id=device_id,
            package_id=package_id,
            voucher_code=voucher_code,
        )
        return await self._post("/v1/renew-device", req.model_dump())

    async def list_devices(
        self, page: int | None = None, limit: int | None = None
    ) -> KirimiResponse:
        """Return a list of all registered devices.

        Args:
            page: Page number, 1-based. Defaults to 1.
            limit: Page size. Defaults to 10.
        """
        req = ListDevicesRequest(**self._auth())
        body = req.model_dump()
        body["page"] = page
        body["limit"] = limit
        return await self._post("/v1/list-devices", body)

    async def device_status(self, device_id: str) -> KirimiResponse:
        """Check connection status of a device.

        Args:
            device_id: Device ID to check.
        """
        return await self._post("/v1/device-status", {**self._auth(), "device_id": device_id})

    async def device_status_enhanced(self, device_id: str) -> KirimiResponse:
        """Get full enhanced status details of a device.

        Args:
            device_id: Device ID to check.
        """
        return await self._post(
            "/v1/device-status-enhanced", {**self._auth(), "device_id": device_id}
        )

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def user_info(self) -> KirimiResponse:
        """Return account information for the authenticated user."""
        req = UserInfoRequest(**self._auth())
        return await self._post("/v1/user-info", req.model_dump())

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    async def save_contact(
        self,
        nama: str,
        nomor: str,
        device_id: str | None = None,
    ) -> KirimiResponse:
        """Save a contact to your Kirimi address book.

        Args:
            nama: Contact name.
            nomor: Contact phone number.
            device_id: Optional device to save the contact to.
        """
        req = SaveContactRequest(**self._auth(), nama=nama, nomor=nomor, device_id=device_id)
        return await self._post("/v1/save-contact", req.model_dump())

    async def save_contacts_bulk(
        self,
        contacts: Iterable[BulkContact | Mapping[str, str]],
        device_id: str | None = None,
    ) -> KirimiResponse:
        """Save up to 1000 contacts in one request.

        Args:
            contacts: Contacts to save — :class:`BulkContact` instances or
                mappings with ``nama`` / ``nomor`` keys.
            device_id: Optional device to save the contacts to.
        """
        req = SaveContactsBulkRequest(
            **self._auth(),
            contacts=[BulkContact.model_validate(c) for c in contacts],
            device_id=device_id,
        )
        return await self._post("/v1/save-contacts-bulk", req.model_dump())

    # ------------------------------------------------------------------
    # OTP v1
    # ------------------------------------------------------------------

    async def generate_otp(
        self,
        device_id: str,
        phone: str,
        otp_length: int | None = None,
        otp_type: OtpType | None = None,
        custom_otp_text: str | None = None,
        custom_otp_message: str | None = None,
        enable_typing_effect: bool | None = None,
        typing_speed_ms: int | None = None,
    ) -> KirimiResponse:
        """Generate and send an OTP via a WhatsApp device.

        Args:
            device_id: Device ID to send from.
            phone: Recipient phone number.
            otp_length: Length of the generated OTP code (4–20).
            otp_type: OTP character set — ``"numeric"``, ``"alphabetic"``, or
                ``"alphanumeric"``.
            custom_otp_text: Custom OTP text, max 20 chars.
            custom_otp_message: Custom message template containing ``{otp}``
                placeholder (e.g. ``"Kode OTP Anda: {otp}"``).
            enable_typing_effect: Simulate typing before sending.
            typing_speed_ms: Typing speed in ms (100–800).
        """
        req = GenerateOtpRequest(
            **self._auth(),
            device_id=device_id,
            phone=phone,
            otp_length=otp_length,
            otp_type=otp_type,
            customOtpText=custom_otp_text,
            customOtpMessage=custom_otp_message,
            enableTypingEffect=enable_typing_effect,
            typingSpeedMs=typing_speed_ms,
        )
        return await self._post("/v1/generate-otp", req.model_dump())

    async def validate_otp(
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
        return await self._post("/v1/validate-otp", req.model_dump())

    # ------------------------------------------------------------------
    # OTP v2
    # ------------------------------------------------------------------

    async def send_otp_v2(
        self,
        phone: str,
        method: OtpMethod | None = None,
        app_name: str | None = None,
        device_id: str | None = None,
        waba_id: str | None = None,
        template_name: str | None = None,
        custom_message: str | None = None,
    ) -> KirimiResponse:
        """Send an OTP via the Kirimi provider, a device, or your own WABA (V2).

        Args:
            phone: Recipient phone number.
            method: Delivery channel — ``"whatsapp"`` (alias ``"waba"``),
                ``"device"`` or ``"waba_user"``.
            app_name: Application name displayed in the OTP message.
            device_id: Required for ``method="device"``.
            waba_id: Required for ``method="waba_user"``.
            template_name: Required for ``method="waba_user"``
                (AUTHENTICATION + APPROVED template).
            custom_message: Required for ``method="device"`` — must contain
                ``{{otp}}`` (10–500 chars).
        """
        req = SendOtpV2Request(
            **self._auth(),
            phone=phone,
            method=method,
            app_name=app_name,
            device_id=device_id,
            waba_id=waba_id,
            template_name=template_name,
            custom_message=custom_message,
        )
        return await self._post("/v2/otp/send", req.model_dump())

    async def verify_otp_v2(self, phone: str, otp_code: str) -> KirimiResponse:
        """Verify an OTP code (V2).

        Args:
            phone: Recipient phone number.
            otp_code: The OTP code to verify.
        """
        req = VerifyOtpV2Request(**self._auth(), phone=phone, otp_code=otp_code)
        return await self._post("/v2/otp/verify", req.model_dump())

    # ------------------------------------------------------------------
    # OTP Reverse
    # ------------------------------------------------------------------

    async def otp_reverse_create(
        self,
        phone: str,
        device_id: str,
        app_name: str | None = None,
        callback_url: str | None = None,
        custom_message: str | None = None,
        success_message: str | None = None,
        failure_message: str | None = None,
    ) -> KirimiResponse:
        """Create a reverse OTP token and the message the customer must send back.

        Args:
            phone: Customer phone number to verify.
            device_id: Device that detects the customer's inbound message.
            app_name: App name shown in the message. Defaults to "Kirimi.id".
            callback_url: URL notified when verification completes (max 500).
            custom_message: Must contain ``{{token}}`` and ``{{phone}}``
                (20–500 chars).
            success_message: Message shown on success.
            failure_message: Message shown on failure.
        """
        req = OtpReverseCreateRequest(
            **self._auth(),
            phone=phone,
            device_id=device_id,
            app_name=app_name,
            callback_url=callback_url,
            custom_message=custom_message,
            success_message=success_message,
            failure_message=failure_message,
        )
        return await self._post("/v2/otp-reverse/create", req.model_dump())

    async def otp_reverse_status(self, token: str) -> KirimiResponse:
        """Check the status of a reverse OTP token.

        Args:
            token: ULID token returned by :meth:`otp_reverse_create`.
        """
        req = OtpReverseStatusRequest(**self._auth(), token=token)
        return await self._post("/v2/otp-reverse/status", req.model_dump())

    # ------------------------------------------------------------------
    # Packages & Deposits
    # ------------------------------------------------------------------

    async def list_deposits(
        self,
        status: DepositStatus | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> KirimiResponse:
        """Return a list of deposits.

        Args:
            status: Filter by status — ``"unpaid"``, ``"paid"``, ``"expired"``,
                ``"cancelled"``, or ``""`` / ``None`` for all.
            page: Page number, 1-based. Defaults to 1.
            limit: Page size. Defaults to 10.
        """
        req = ListDepositsRequest(**self._auth(), status=status, page=page, limit=limit)
        return await self._post("/v1/list-deposits", req.model_dump())

    async def list_packages(self) -> KirimiResponse:
        """Return available Kirimi packages."""
        req = ListPackagesRequest(**self._auth())
        return await self._post("/v1/list-packages", req.model_dump())

    async def create_deposit(self, nominal: float | int) -> KirimiResponse:
        """Create a deposit payment link.

        Args:
            nominal: Deposit amount in IDR. Minimum 100.
        """
        req = CreateDepositRequest(**self._auth(), nominal=nominal)
        return await self._post("/v1/create-deposit", req.model_dump())

    async def deposit_status(self, ref: str) -> KirimiResponse:
        """Check a deposit's status by reference.

        Args:
            ref: Deposit reference ID.
        """
        req = DepositRefRequest(**self._auth(), ref=ref)
        return await self._post("/v1/deposit-status", req.model_dump())

    async def cancel_deposit(self, ref: str) -> KirimiResponse:
        """Cancel an unpaid deposit.

        Args:
            ref: Deposit reference ID. Must be ``unpaid``.
        """
        req = DepositRefRequest(**self._auth(), ref=ref)
        return await self._post("/v1/cancel-deposit", req.model_dump())
