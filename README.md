# kirimi-python

Official Python SDK for the [Kirimi](https://kirimi.id) WhatsApp API.

## Installation

```bash
pip install kirimi
```

## Quick Start

```python
from kirimi import Kirimi

client = Kirimi(user_code="YOUR_USER_CODE", secret="YOUR_SECRET")

resp = client.send_message(
    device_id="YOUR_DEVICE_ID",
    receiver="628123456789",
    message="Halo dari Kirimi SDK!",
)
print(resp.success, resp.message)
```

## Sync vs Async

Both interfaces share the same method signatures. Use `Kirimi` for synchronous code and `AsyncKirimi` for async/await code.

```python
# Sync
from kirimi import Kirimi

with Kirimi(user_code="...", secret="...") as client:
    resp = client.list_devices()

# Async
import asyncio
from kirimi import AsyncKirimi

async def main():
    async with AsyncKirimi(user_code="...", secret="...") as client:
        resp = await client.list_devices()
    print(resp.data)

asyncio.run(main())
```

## Constructor

```python
Kirimi(
    user_code="...",          # required
    secret="...",             # required
    base_url="https://api.kirimi.id",  # optional
    timeout=30.0,             # optional, seconds
    http_client=None,         # optional, inject custom httpx.Client
)
```

`user_code` and `secret` are automatically added to every request body.

## All Methods

### Messaging (WhatsApp Unofficial)

```python
# Send text/media message. `receiver` is the canonical field name.
client.send_message(device_id="D", receiver="628xxx", message="hi", media_url="https://...")

# Send file (BinaryIO, bytes, or pathlib.Path)
with open("doc.pdf", "rb") as f:
    client.send_message_file(device_id="D", receiver="628xxx", file=f, file_name="doc.pdf", message="see attached")

# Send message fast (no typing indicator)
client.send_message_fast(device_id="D", receiver="628xxx", message="hi")
```

### WABA (WhatsApp Business API)

WABA endpoints use `waba_id`, never `device_id`.

```python
# Send a Meta-approved template
client.send_waba_message(
    waba_id="W",
    to="628xxx",
    template_name="order_update",
    variables=["Budi", "123"],
    header={"type": "image", "link": "https://..."},
    buttons=[{"type": "url", "url": "https://..."}],
)

# Free-form reply (inside the 24h customer service window)
client.waba_reply(waba_id="W", to="628xxx", message={"type": "text", "text": "hi"})

client.waba_conversations(limit=50, page=1)
client.waba_templates_sync(waba_id="W")
client.waba_send_otp(waba_id="W", to="628xxx", template_name="auth_otp")
client.waba_verify_otp(waba_id="W", to="628xxx", otp_code="123456")
```

### Devices

```python
client.create_device(package_id=7, voucher_code="DISC10")
client.connect_device(device_id="D")
client.renew_device(device_id="D", package_id=7)
client.list_devices(page=1, limit=10)
client.device_status(device_id="D")
client.device_status_enhanced(device_id="D")
```

### User

```python
client.user_info()
```

### Contacts

```python
# The API accepts `nama` + `nomor` only.
client.save_contact(nama="John Doe", nomor="628xxx")

# Bulk save up to 1000 contacts
from kirimi import BulkContact

client.save_contacts_bulk(
    contacts=[BulkContact(nama="John Doe", nomor="628xxx"), {"nama": "Jane", "nomor": "628yyy"}],
    device_id="D",
)
```

### OTP v1

```python
# Generate & send OTP
client.generate_otp(
    device_id="D",
    phone="628xxx",
    otp_length=6,
    otp_type="numeric",          # "numeric" | "alphabetic" | "alphanumeric"
    custom_otp_message="Kode: {otp}",
)

# Validate OTP
client.validate_otp(device_id="D", phone="628xxx", otp="123456")
```

### OTP v2

`method` is one of `whatsapp` (alias `waba`), `device`, or `waba_user`.

```python
# whatsapp — Kirimi official provider (Rp 595 / delivered)
client.send_otp_v2(phone="628xxx", method="whatsapp", app_name="MyApp")

# device — your own connected device, free
client.send_otp_v2(
    phone="628xxx",
    method="device",
    device_id="D",
    custom_message="Your OTP for {app}: {{otp}}",   # must contain {{otp}}
)

# waba_user — your own WABA + AUTHENTICATION template, free
client.send_otp_v2(
    phone="628xxx",
    method="waba_user",
    waba_id="W",
    template_name="auth_otp",
)

# Verify OTP
client.verify_otp_v2(phone="628xxx", otp_code="123456")
```

### OTP Reverse

```python
client.otp_reverse_create(
    phone="628xxx",
    device_id="D",
    app_name="MyApp",
    callback_url="https://example.com/cb",
    custom_message="Kirim {{token}} dari {{phone}}",  # must contain both placeholders
)
client.otp_reverse_status(token="TOKEN123")   # pending | verified | phone_mismatch | expired
```

### Broadcast

`numbers` must be a list — the API rejects a joined string. `label` is required.

```python
client.broadcast_message(
    device_id="D",
    label="promo-juli",
    numbers=["628111", "628222", "628333"],   # max 1000
    message="Promo spesial!",
    delay=45,  # seconds between each message, server clamps 30–3600
)
```

### Deposits & Packages

```python
client.list_packages()
client.create_deposit(nominal=50000)        # minimum 100
client.deposit_status(ref="REF1")
client.cancel_deposit(ref="REF1")
client.list_deposits(status="paid")          # "unpaid" | "paid" | "expired" | "cancelled"
```

## Response Model

All methods return a `KirimiResponse` Pydantic model:

```python
class KirimiResponse(BaseModel):
    success: bool
    data: Any | None
    message: str | None
```

## Error Handling

```python
from kirimi import Kirimi
from kirimi.exceptions import KirimiAPIError, KirimiConnectionError

client = Kirimi(user_code="...", secret="...")

try:
    resp = client.send_message(device_id="D", receiver="628xxx", message="hi")
except KirimiAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
except KirimiConnectionError as e:
    print(f"Network error: {e}")
```

| Exception | When raised |
|---|---|
| `KirimiAPIError` | Non-2xx HTTP response |
| `KirimiValidationError` | Pydantic response parsing failure |
| `KirimiConnectionError` | Network/transport error |
| `KirimiError` | Base class for all SDK errors |

## License

MIT — Copyright 2026 Kirimi
