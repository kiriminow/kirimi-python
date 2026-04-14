"""Basic tests for Kirimi SDK using httpx.MockTransport."""

from __future__ import annotations

import json

import httpx
import pytest

from kirimi import AsyncKirimi, Kirimi
from kirimi.exceptions import KirimiAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    body = {"success": True, "data": None, "message": "ok"}
    raw_body = json.dumps(body).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=raw_body,
        )

    return httpx.MockTransport(handler), captured


# ---------------------------------------------------------------------------
# Tests: send_message
# ---------------------------------------------------------------------------


def test_send_message_sends_correct_body() -> None:
    transport, captured = _capture_transport()
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="USER123", secret="SECRET456", http_client=http_client)
    resp = client.send_message(device_id="DEV001", phone="628123456789", message="halo")

    assert resp.success is True
    assert len(captured) == 1

    req = captured[0]
    assert req.url.path == "/v1/send-message"

    payload = json.loads(req.content)
    assert payload["user_code"] == "USER123"
    assert payload["secret"] == "SECRET456"
    assert payload["device_id"] == "DEV001"
    assert payload["phone"] == "628123456789"
    assert payload["message"] == "halo"
    assert "media_url" not in payload  # None values must be stripped


def test_send_message_with_media_url() -> None:
    transport, captured = _capture_transport()
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="U", secret="S", http_client=http_client)
    client.send_message(
        device_id="D",
        phone="628xxx",
        message="see image",
        media_url="https://example.com/img.png",
    )

    payload = json.loads(captured[0].content)
    assert payload["media_url"] == "https://example.com/img.png"


# ---------------------------------------------------------------------------
# Tests: generate_otp
# ---------------------------------------------------------------------------


def test_generate_otp_minimal() -> None:
    transport, captured = _capture_transport()
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="U", secret="S", http_client=http_client)
    client.generate_otp(device_id="D", phone="628xxx")

    payload = json.loads(captured[0].content)
    assert payload["device_id"] == "D"
    assert payload["phone"] == "628xxx"
    # Optional fields must not be present when not supplied
    assert "otp_length" not in payload
    assert "otp_type" not in payload
    assert "customOtpMessage" not in payload


def test_generate_otp_with_all_options() -> None:
    transport, captured = _capture_transport()
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="U", secret="S", http_client=http_client)
    client.generate_otp(
        device_id="D",
        phone="628xxx",
        otp_length=6,
        otp_type="numeric",
        custom_otp_message="Kode OTP: {otp}",
    )

    payload = json.loads(captured[0].content)
    assert payload["otp_length"] == 6
    assert payload["otp_type"] == "numeric"
    assert payload["customOtpMessage"] == "Kode OTP: {otp}"


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
# Tests: async client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_send_message() -> None:
    captured: list[httpx.Request] = []
    body = {"success": True, "data": None, "message": "ok"}
    raw_body = json.dumps(body).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=raw_body,
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)

    async with AsyncKirimi(user_code="U", secret="S", http_client=http_client) as client:
        resp = await client.send_message(device_id="D", phone="628xxx", message="async test")

    assert resp.success is True
    assert len(captured) == 1
    payload = json.loads(captured[0].content)
    assert payload["message"] == "async test"


# ---------------------------------------------------------------------------
# Tests: broadcast phones handling
# ---------------------------------------------------------------------------


def test_broadcast_list_phones_joined() -> None:
    transport, captured = _capture_transport()
    http_client = httpx.Client(transport=transport)

    client = Kirimi(user_code="U", secret="S", http_client=http_client)
    client.broadcast_message(
        device_id="D",
        phones=["628111", "628222", "628333"],
        message="hi all",
    )

    payload = json.loads(captured[0].content)
    assert payload["phones"] == "628111,628222,628333"
