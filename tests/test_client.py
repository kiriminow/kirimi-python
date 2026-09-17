"""Tests for Kirimi SDK — sync + async, using httpx.MockTransport."""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx
import pytest

from kirimi import AsyncKirimi, BulkContact, Kirimi
from kirimi.exceptions import KirimiAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OK_BODY = {"success": True, "data": None, "message": "ok"}


def _make_transport(status_code: int = 200, body: dict | None = None) -> httpx.MockTransport:
    """Return an httpx.MockTransport that responds with the given status + JSON body."""
    if body is None:
        body = {"success": True, "data": None, "message": "ok"}

    raw_body = json.dumps(body).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            content=raw_body,
        )

    return httpx.MockTransport(handler)


def _capture_transport() -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Return a transport that captures all outgoing requests."""
    captured: list[httpx.Request] = []
    raw_body = json.dumps(_OK_BODY).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=raw_body,
        )

    return httpx.MockTransport(handler), captured


def _sync_client(
    captured: list[httpx.Request] | None = None,
) -> Kirimi:
    transport, captured = _capture_transport()
    return Kirimi(user_code="U", secret="S", http_client=httpx.Client(transport=transport))


def _sync() -> tuple[Kirimi, list[httpx.Request]]:
    transport, captured = _capture_transport()
    client = Kirimi(user_code="U", secret="S", http_client=httpx.Client(transport=transport))
    return client, captured


def _async() -> tuple[AsyncKirimi, list[httpx.Request]]:
    transport, captured = _capture_transport()
    client = AsyncKirimi(user_code="U", secret="S", http_client=httpx.AsyncClient(transport=transport))
    return client, captured


def _json(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content)


def _multipart_fields(request: httpx.Request) -> dict[str, str]:
    """Extract simple form fields from a multipart body (ignores the file part)."""
    boundary = request.headers["content-type"].split("boundary=")[1].encode()
    fields: dict[str, str] = {}
    for part in request.content.split(b"--" + boundary):
        if b"\r\n\r\n" not in part:
            continue
        head, _, body = part.partition(b"\r\n\r\n")
        if b'name="file"' in head:
            continue
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        fields[name] = body.rstrip(b"\r\n--").decode()
    return fields


# ---------------------------------------------------------------------------
# Tests: send_message
# ---------------------------------------------------------------------------


def test_send_message_sends_receiver_not_phone() -> None:
    client, captured = _sync()
    resp = client.send_message(device_id="DEV001", receiver="628123456789", message="halo")

    assert resp.success is True
    assert resp.message == "ok"
    assert len(captured) == 1

    req = captured[0]
    assert req.url.path == "/v1/send-message"

    payload = _json(req)
    assert payload["user_code"] == "U"
    assert payload["secret"] == "S"
    assert payload["device_id"] == "DEV001"
    assert payload["receiver"] == "628123456789"
    assert payload["message"] == "halo"
    assert "phone" not in payload
    assert "media_url" not in payload  # None values must be stripped


def test_send_message_with_all_options() -> None:
    client, captured = _sync()
    client.send_message(
        device_id="D",
        receiver="628xxx",
        message="see image",
        media_url="https://example.com/img.png",
        file_name="img.png",
        enable_typing_effect=False,
        typing_speed_ms=200,
        quoted_message_id="QUOTED1",
    )

    payload = _json(captured[0])
    assert "phone" not in payload
    assert payload["media_url"] == "https://example.com/img.png"
    assert payload["fileName"] == "img.png"
    assert payload["enableTypingEffect"] is False
    assert payload["typingSpeedMs"] == 200
    assert payload["quotedMessageId"] == "QUOTED1"


def test_send_message_fast_sends_receiver() -> None:
    client, captured = _sync()
    client.send_message_fast(device_id="D", receiver="628xxx", message="fast")

    req = captured[0]
    assert req.url.path == "/v1/send-message-fast"
    payload = _json(req)
    assert payload["receiver"] == "628xxx"
    assert "phone" not in payload
    assert "enableTypingEffect" not in payload


def test_send_message_file_sends_receiver() -> None:
    client, captured = _sync()
    client.send_message_file(
        device_id="D",
        receiver="628xxx",
        file=b"binary-data",
        file_name="doc.pdf",
        message="hello",
        caption="cap",
    )

    req = captured[0]
    assert req.url.path == "/v1/send-message-file"
    fields = _multipart_fields(req)
    assert fields["receiver"] == "628xxx"
    assert "phone" not in fields
    assert fields["device_id"] == "D"
    assert fields["fileName"] == "doc.pdf"
    assert fields["message"] == "hello"
    assert fields["caption"] == "cap"


# ---------------------------------------------------------------------------
# Tests: broadcast
# ---------------------------------------------------------------------------


def test_broadcast_sends_numbers_as_list_and_label() -> None:
    client, captured = _sync()
    client.broadcast_message(
        device_id="D",
        label="promo",
        numbers=["628111", "628222", "628333"],
        message="hi all",
        delay=45,
    )

    payload = _json(captured[0])
    assert captured[0].url.path == "/v1/broadcast-message"
    assert payload["numbers"] == ["628111", "628222", "628333"]
    assert isinstance(payload["numbers"], list)
    assert payload["label"] == "promo"
    assert payload["message"] == "hi all"
    assert payload["delay"] == 45
    assert "phones" not in payload


def test_broadcast_accepts_any_iterable() -> None:
    client, captured = _sync()
    client.broadcast_message(
        device_id="D", label="lbl", numbers=("628111", "628222"), message="hi"
    )

    payload = _json(captured[0])
    assert payload["numbers"] == ["628111", "628222"]
    assert "delay" not in payload


# ---------------------------------------------------------------------------
# Tests: contacts
# ---------------------------------------------------------------------------


def test_save_contact_sends_nama_nomor() -> None:
    client, captured = _sync()
    client.save_contact(nama="Budi", nomor="628123456789")

    req = captured[0]
    assert req.url.path == "/v1/save-contact"
    payload = _json(req)
    assert payload["nama"] == "Budi"
    assert payload["nomor"] == "628123456789"
    assert "name" not in payload
    assert "phone" not in payload
    assert "email" not in payload
    assert "device_id" not in payload


def test_save_contact_with_device_id() -> None:
    client, captured = _sync()
    client.save_contact(nama="Budi", nomor="628xxx", device_id="D")

    payload = _json(captured[0])
    assert payload["device_id"] == "D"


def test_save_contacts_bulk_from_models() -> None:
    client, captured = _sync()
    client.save_contacts_bulk(
        contacts=[BulkContact(nama="A", nomor="628111"), BulkContact(nama="B", nomor="628222")],
        device_id="D",
    )

    req = captured[0]
    assert req.url.path == "/v1/save-contacts-bulk"
    payload = _json(req)
    assert payload["contacts"] == [
        {"nama": "A", "nomor": "628111"},
        {"nama": "B", "nomor": "628222"},
    ]
    assert payload["device_id"] == "D"


def test_save_contacts_bulk_from_mappings() -> None:
    client, captured = _sync()
    client.save_contacts_bulk(contacts=[{"nama": "A", "nomor": "628111"}])

    payload = _json(captured[0])
    assert payload["contacts"] == [{"nama": "A", "nomor": "628111"}]
    assert "device_id" not in payload


# ---------------------------------------------------------------------------
# Tests: WABA
# ---------------------------------------------------------------------------


def test_send_waba_message_canonical_fields() -> None:
    client, captured = _sync()
    client.send_waba_message(
        waba_id="WABA1",
        to="628xxx",
        template_name="order_update",
        variables=["Budi", "123"],
        header={"type": "image", "link": "https://example.com/a.png"},
        buttons=[{"type": "url", "url": "https://example.com"}],
    )

    req = captured[0]
    assert req.url.path == "/v1/waba/send-message"
    payload = _json(req)
    assert payload["waba_id"] == "WABA1"
    assert payload["to"] == "628xxx"
    assert payload["template_name"] == "order_update"
    assert payload["variables"] == ["Budi", "123"]
    assert payload["header"] == {"type": "image", "link": "https://example.com/a.png"}
    assert payload["buttons"] == [{"type": "url", "url": "https://example.com"}]
    assert "device_id" not in payload
    assert "phone" not in payload
    assert "message" not in payload


def test_send_waba_message_minimal() -> None:
    client, captured = _sync()
    client.send_waba_message(waba_id="W", to="628xxx", template_name="tpl")

    payload = _json(captured[0])
    assert payload["waba_id"] == "W"
    assert "variables" not in payload
    assert "header" not in payload
    assert "buttons" not in payload


def test_waba_reply() -> None:
    client, captured = _sync()
    client.waba_reply(waba_id="W", to="628xxx", message={"type": "text", "text": "hi"})

    req = captured[0]
    assert req.url.path == "/v1/waba/messages/reply"
    payload = _json(req)
    assert payload["waba_id"] == "W"
    assert payload["to"] == "628xxx"
    assert payload["message"] == {"type": "text", "text": "hi"}
    assert "phone" not in payload


def test_waba_conversations_with_pagination() -> None:
    client, captured = _sync()
    client.waba_conversations(limit=25, page=2)

    req = captured[0]
    assert req.url.path == "/v1/waba/conversations"
    payload = _json(req)
    assert payload["limit"] == 25
    assert payload["page"] == 2


def test_waba_conversations_without_options() -> None:
    client, captured = _sync()
    client.waba_conversations()

    payload = _json(captured[0])
    assert "limit" not in payload
    assert "page" not in payload


def test_waba_templates_sync() -> None:
    client, captured = _sync()
    client.waba_templates_sync(waba_id="W")

    req = captured[0]
    assert req.url.path == "/v1/waba/templates/sync"
    assert _json(req)["waba_id"] == "W"


def test_waba_send_otp() -> None:
    client, captured = _sync()
    client.waba_send_otp(waba_id="W", to="628xxx", template_name="auth_otp")

    req = captured[0]
    assert req.url.path == "/v1/waba/send-otp"
    payload = _json(req)
    assert payload["waba_id"] == "W"
    assert payload["to"] == "628xxx"
    assert payload["template_name"] == "auth_otp"
    assert "phone" not in payload


def test_waba_verify_otp() -> None:
    client, captured = _sync()
    client.waba_verify_otp(waba_id="W", to="628xxx", otp_code="123456")

    req = captured[0]
    assert req.url.path == "/v1/waba/verify-otp"
    payload = _json(req)
    assert payload["waba_id"] == "W"
    assert payload["to"] == "628xxx"
    assert payload["otp_code"] == "123456"


# ---------------------------------------------------------------------------
# Tests: devices
# ---------------------------------------------------------------------------


def test_create_device_without_voucher() -> None:
    client, captured = _sync()
    client.create_device(package_id=7)

    req = captured[0]
    assert req.url.path == "/v1/create-device"
    payload = _json(req)
    assert payload["package_id"] == 7
    assert "voucher_code" not in payload


def test_create_device_with_voucher() -> None:
    client, captured = _sync()
    client.create_device(package_id="pkg-1", voucher_code="DISC10")

    payload = _json(captured[0])
    assert payload["package_id"] == "pkg-1"
    assert payload["voucher_code"] == "DISC10"


def test_connect_device() -> None:
    client, captured = _sync()
    client.connect_device(device_id="D")

    req = captured[0]
    assert req.url.path == "/v1/connect-device"
    assert _json(req)["device_id"] == "D"


def test_renew_device() -> None:
    client, captured = _sync()
    client.renew_device(device_id="D", package_id=3, voucher_code="V")

    req = captured[0]
    assert req.url.path == "/v1/renew-device"
    payload = _json(req)
    assert payload["device_id"] == "D"
    assert payload["package_id"] == 3
    assert payload["voucher_code"] == "V"


def test_list_devices_pagination() -> None:
    client, captured = _sync()
    client.list_devices(page=2, limit=5)

    req = captured[0]
    assert req.url.path == "/v1/list-devices"
    payload = _json(req)
    assert payload["page"] == 2
    assert payload["limit"] == 5


def test_device_status_and_enhanced() -> None:
    client, captured = _sync()
    client.device_status(device_id="D")
    client.device_status_enhanced(device_id="D")

    assert captured[0].url.path == "/v1/device-status"
    assert captured[1].url.path == "/v1/device-status-enhanced"
    assert _json(captured[0])["device_id"] == "D"
    assert _json(captured[1])["device_id"] == "D"


def test_user_info_and_list_packages() -> None:
    client, captured = _sync()
    client.user_info()
    client.list_packages()

    assert captured[0].url.path == "/v1/user-info"
    assert captured[1].url.path == "/v1/list-packages"
    assert _json(captured[0]) == {"user_code": "U", "secret": "S"}


# ---------------------------------------------------------------------------
# Tests: send_otp_v2 (all three methods)
# ---------------------------------------------------------------------------


def test_send_otp_v2_whatsapp() -> None:
    client, captured = _sync()
    client.send_otp_v2(phone="628xxx", method="whatsapp", app_name="MyApp")

    req = captured[0]
    assert req.url.path == "/v2/otp/send"
    payload = _json(req)
    assert payload["phone"] == "628xxx"
    assert payload["method"] == "whatsapp"
    assert payload["app_name"] == "MyApp"
    assert "device_id" not in payload
    assert "waba_id" not in payload
    assert "template_name" not in payload
    assert "custom_message" not in payload


def test_send_otp_v2_waba_legacy_alias() -> None:
    client, captured = _sync()
    client.send_otp_v2(phone="628xxx", method="waba")

    assert _json(captured[0])["method"] == "waba"


def test_send_otp_v2_device() -> None:
    client, captured = _sync()
    client.send_otp_v2(
        phone="628xxx",
        method="device",
        device_id="D",
        custom_message="Kode OTP: {{otp}}",
    )

    payload = _json(captured[0])
    assert payload["method"] == "device"
    assert payload["device_id"] == "D"
    assert payload["custom_message"] == "Kode OTP: {{otp}}"
    assert "waba_id" not in payload
    assert "template_name" not in payload


def test_send_otp_v2_waba_user() -> None:
    client, captured = _sync()
    client.send_otp_v2(
        phone="628xxx",
        method="waba_user",
        waba_id="W",
        template_name="auth_otp",
    )

    payload = _json(captured[0])
    assert payload["method"] == "waba_user"
    assert payload["waba_id"] == "W"
    assert payload["template_name"] == "auth_otp"
    assert "device_id" not in payload
    assert "custom_message" not in payload


def test_send_otp_v2_rejects_unknown_method() -> None:
    from pydantic import ValidationError

    client, _ = _sync()
    with pytest.raises(ValidationError):
        client.send_otp_v2(phone="628xxx", method="sms")  # type: ignore[arg-type]


def test_verify_otp_v2() -> None:
    client, captured = _sync()
    client.verify_otp_v2(phone="628xxx", otp_code="1234")

    req = captured[0]
    assert req.url.path == "/v2/otp/verify"
    payload = _json(req)
    assert payload["phone"] == "628xxx"
    assert payload["otp_code"] == "1234"


# ---------------------------------------------------------------------------
# Tests: OTP v1
# ---------------------------------------------------------------------------


def test_generate_otp_minimal() -> None:
    client, captured = _sync()
    client.generate_otp(device_id="D", phone="628xxx")

    payload = _json(captured[0])
    assert payload["device_id"] == "D"
    assert payload["phone"] == "628xxx"
    assert "otp_length" not in payload
    assert "otp_type" not in payload
    assert "customOtpMessage" not in payload


def test_generate_otp_with_all_options() -> None:
    client, captured = _sync()
    client.generate_otp(
        device_id="D",
        phone="628xxx",
        otp_length=6,
        otp_type="numeric",
        custom_otp_text="KODE",
        custom_otp_message="Kode OTP: {otp}",
        enable_typing_effect=True,
        typing_speed_ms=300,
    )

    payload = _json(captured[0])
    assert payload["otp_length"] == 6
    assert payload["otp_type"] == "numeric"
    assert payload["customOtpText"] == "KODE"
    assert payload["customOtpMessage"] == "Kode OTP: {otp}"
    assert payload["enableTypingEffect"] is True
    assert payload["typingSpeedMs"] == 300


def test_validate_otp() -> None:
    client, captured = _sync()
    client.validate_otp(device_id="D", phone="628xxx", otp="1234")

    req = captured[0]
    assert req.url.path == "/v1/validate-otp"
    payload = _json(req)
    assert payload["device_id"] == "D"
    assert payload["phone"] == "628xxx"
    assert payload["otp"] == "1234"


# ---------------------------------------------------------------------------
# Tests: OTP reverse
# ---------------------------------------------------------------------------


def test_otp_reverse_create_minimal() -> None:
    client, captured = _sync()
    client.otp_reverse_create(phone="628xxx", device_id="D")

    req = captured[0]
    assert req.url.path == "/v2/otp-reverse/create"
    payload = _json(req)
    assert payload["phone"] == "628xxx"
    assert payload["device_id"] == "D"
    assert "app_name" not in payload
    assert "callback_url" not in payload
    assert "custom_message" not in payload
    assert "success_message" not in payload
    assert "failure_message" not in payload


def test_otp_reverse_create_full() -> None:
    client, captured = _sync()
    client.otp_reverse_create(
        phone="628xxx",
        device_id="D",
        app_name="MyApp",
        callback_url="https://example.com/cb",
        custom_message="Kirim {{token}} dari {{phone}}",
        success_message="ok",
        failure_message="fail",
    )

    payload = _json(captured[0])
    assert payload["app_name"] == "MyApp"
    assert payload["callback_url"] == "https://example.com/cb"
    assert payload["custom_message"] == "Kirim {{token}} dari {{phone}}"
    assert payload["success_message"] == "ok"
    assert payload["failure_message"] == "fail"


def test_otp_reverse_status() -> None:
    client, captured = _sync()
    client.otp_reverse_status(token="TOKEN123")

    req = captured[0]
    assert req.url.path == "/v2/otp-reverse/status"
    payload = _json(req)
    assert payload["token"] == "TOKEN123"


# ---------------------------------------------------------------------------
# Tests: deposits
# ---------------------------------------------------------------------------


def test_create_deposit() -> None:
    client, captured = _sync()
    client.create_deposit(nominal=50000)

    req = captured[0]
    assert req.url.path == "/v1/create-deposit"
    assert _json(req)["nominal"] == 50000


def test_deposit_status() -> None:
    client, captured = _sync()
    client.deposit_status(ref="REF1")

    req = captured[0]
    assert req.url.path == "/v1/deposit-status"
    assert _json(req)["ref"] == "REF1"


def test_cancel_deposit() -> None:
    client, captured = _sync()
    client.cancel_deposit(ref="REF1")

    req = captured[0]
    assert req.url.path == "/v1/cancel-deposit"
    assert _json(req)["ref"] == "REF1"


def test_list_deposits_status_filter() -> None:
    client, captured = _sync()
    client.list_deposits(status="unpaid", page=1, limit=10)

    req = captured[0]
    assert req.url.path == "/v1/list-deposits"
    payload = _json(req)
    assert payload["status"] == "unpaid"
    assert payload["page"] == 1
    assert payload["limit"] == 10


def test_list_deposits_invalid_status_rejected() -> None:
    from pydantic import ValidationError

    client, _ = _sync()
    with pytest.raises(ValidationError):
        client.list_deposits(status="bogus")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


def test_raises_kirimi_api_error_on_401() -> None:
    body = {"success": False, "message": "Unauthorized"}
    transport = _make_transport(status_code=401, body=body)
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="bad", secret="creds", http_client=http_client)

    with pytest.raises(KirimiAPIError) as exc_info:
        client.user_info()

    assert exc_info.value.status_code == 401
    assert "Unauthorized" in exc_info.value.message


def test_raises_kirimi_api_error_on_400() -> None:
    body = {"success": False, "message": "phone is required"}
    transport = _make_transport(status_code=400, body=body)
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="U", secret="S", http_client=http_client)

    with pytest.raises(KirimiAPIError) as exc_info:
        client.list_devices()

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Tests: async client — mirror of the sync surface
# ---------------------------------------------------------------------------


async def test_async_send_message_sends_receiver() -> None:
    client, captured = _async()
    async with client:
        resp = await client.send_message(device_id="D", receiver="628xxx", message="async test")

    assert resp.success is True
    payload = _json(captured[0])
    assert payload["receiver"] == "628xxx"
    assert "phone" not in payload
    assert payload["message"] == "async test"


async def test_async_send_message_fast_and_file() -> None:
    client, captured = _async()
    async with client:
        await client.send_message_fast(device_id="D", receiver="628xxx", message="fast")
        await client.send_message_file(device_id="D", receiver="628xxx", file=b"data")

    assert _json(captured[0])["receiver"] == "628xxx"
    assert "phone" not in _json(captured[0])
    fields = _multipart_fields(captured[1])
    assert fields["receiver"] == "628xxx"
    assert "phone" not in fields


async def test_async_broadcast_numbers_is_list() -> None:
    client, captured = _async()
    async with client:
        await client.broadcast_message(
            device_id="D", label="promo", numbers=["628111", "628222"], message="hi"
        )

    payload = _json(captured[0])
    assert payload["numbers"] == ["628111", "628222"]
    assert payload["label"] == "promo"
    assert "phones" not in payload


async def test_async_save_contact_and_bulk() -> None:
    client, captured = _async()
    async with client:
        await client.save_contact(nama="Budi", nomor="628xxx")
        await client.save_contacts_bulk(contacts=[{"nama": "A", "nomor": "628111"}])

    payload = _json(captured[0])
    assert payload["nama"] == "Budi"
    assert payload["nomor"] == "628xxx"
    assert "name" not in payload
    assert "phone" not in payload

    bulk = _json(captured[1])
    assert bulk["contacts"] == [{"nama": "A", "nomor": "628111"}]


async def test_async_waba_surface() -> None:
    client, captured = _async()
    async with client:
        await client.send_waba_message(waba_id="W", to="628xxx", template_name="tpl")
        await client.waba_reply(waba_id="W", to="628xxx", message={"type": "text", "text": "hi"})
        await client.waba_conversations(limit=10, page=1)
        await client.waba_templates_sync(waba_id="W")
        await client.waba_send_otp(waba_id="W", to="628xxx", template_name="auth")
        await client.waba_verify_otp(waba_id="W", to="628xxx", otp_code="123456")

    assert captured[0].url.path == "/v1/waba/send-message"
    assert _json(captured[0])["template_name"] == "tpl"
    assert "device_id" not in _json(captured[0])
    assert captured[1].url.path == "/v1/waba/messages/reply"
    assert _json(captured[1])["message"] == {"type": "text", "text": "hi"}
    assert captured[2].url.path == "/v1/waba/conversations"
    assert captured[3].url.path == "/v1/waba/templates/sync"
    assert captured[4].url.path == "/v1/waba/send-otp"
    assert _json(captured[4])["template_name"] == "auth"
    assert captured[5].url.path == "/v1/waba/verify-otp"
    assert _json(captured[5])["otp_code"] == "123456"


async def test_async_devices_surface() -> None:
    client, captured = _async()
    async with client:
        await client.create_device(package_id=7, voucher_code="V")
        await client.connect_device(device_id="D")
        await client.renew_device(device_id="D", package_id=3)
        await client.list_devices(page=1, limit=10)
        await client.device_status(device_id="D")
        await client.device_status_enhanced(device_id="D")
        await client.user_info()
        await client.list_packages()

    assert captured[0].url.path == "/v1/create-device"
    assert _json(captured[0])["voucher_code"] == "V"
    assert captured[1].url.path == "/v1/connect-device"
    assert captured[2].url.path == "/v1/renew-device"
    assert _json(captured[2])["package_id"] == 3
    assert captured[3].url.path == "/v1/list-devices"
    assert captured[4].url.path == "/v1/device-status"
    assert captured[5].url.path == "/v1/device-status-enhanced"
    assert captured[6].url.path == "/v1/user-info"
    assert captured[7].url.path == "/v1/list-packages"


async def test_async_otp_v2_all_methods() -> None:
    client, captured = _async()
    async with client:
        await client.send_otp_v2(phone="628xxx", method="whatsapp")
        await client.send_otp_v2(phone="628xxx", method="device", device_id="D")
        await client.send_otp_v2(
            phone="628xxx", method="waba_user", waba_id="W", template_name="auth"
        )
        await client.verify_otp_v2(phone="628xxx", otp_code="1234")

    assert _json(captured[0])["method"] == "whatsapp"
    assert "device_id" not in _json(captured[0])
    assert _json(captured[1])["device_id"] == "D"
    assert _json(captured[2])["waba_id"] == "W"
    assert _json(captured[2])["template_name"] == "auth"
    assert captured[3].url.path == "/v2/otp/verify"
    assert _json(captured[3])["otp_code"] == "1234"


async def test_async_otp_reverse_and_deposits() -> None:
    client, captured = _async()
    async with client:
        await client.otp_reverse_create(phone="628xxx", device_id="D", app_name="App")
        await client.otp_reverse_status(token="T")
        await client.create_deposit(nominal=10000)
        await client.deposit_status(ref="R")
        await client.cancel_deposit(ref="R")
        await client.list_deposits(status="paid")

    assert captured[0].url.path == "/v2/otp-reverse/create"
    assert _json(captured[0])["app_name"] == "App"
    assert captured[1].url.path == "/v2/otp-reverse/status"
    assert _json(captured[1])["token"] == "T"
    assert captured[2].url.path == "/v1/create-deposit"
    assert _json(captured[2])["nominal"] == 10000
    assert captured[3].url.path == "/v1/deposit-status"
    assert _json(captured[3])["ref"] == "R"
    assert captured[4].url.path == "/v1/cancel-deposit"
    assert captured[5].url.path == "/v1/list-deposits"
    assert _json(captured[5])["status"] == "paid"


async def test_async_raises_api_error() -> None:
    body = {"success": False, "message": "Nope"}
    transport = _make_transport(status_code=403, body=body)
    http_client = httpx.AsyncClient(transport=transport)

    client = AsyncKirimi(user_code="U", secret="S", http_client=http_client)
    async with client:
        with pytest.raises(KirimiAPIError) as exc_info:
            await client.list_devices()

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Tests: sync/async parity
# ---------------------------------------------------------------------------

_PARITY_METHODS = [
    "send_message",
    "send_message_file",
    "send_message_fast",
    "broadcast_message",
    "send_waba_message",
    "waba_reply",
    "waba_conversations",
    "waba_templates_sync",
    "waba_send_otp",
    "waba_verify_otp",
    "create_device",
    "connect_device",
    "renew_device",
    "list_devices",
    "device_status",
    "device_status_enhanced",
    "user_info",
    "save_contact",
    "save_contacts_bulk",
    "generate_otp",
    "validate_otp",
    "send_otp_v2",
    "verify_otp_v2",
    "otp_reverse_create",
    "otp_reverse_status",
    "list_deposits",
    "list_packages",
    "create_deposit",
    "deposit_status",
    "cancel_deposit",
]


@pytest.mark.parametrize("name", _PARITY_METHODS)
def test_sync_and_async_are_mirrored(name: str) -> None:
    import inspect

    from kirimi.async_client import AsyncKirimi as A
    from kirimi.client import Kirimi as K

    assert hasattr(K, name), f"Kirimi is missing {name}"
    assert hasattr(A, name), f"AsyncKirimi is missing {name}"

    sync_sig = inspect.signature(getattr(K, name))
    async_sig = inspect.signature(getattr(A, name))

    assert list(sync_sig.parameters) == list(async_sig.parameters), f"signature drift on {name}"
