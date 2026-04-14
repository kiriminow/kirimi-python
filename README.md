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
    phone="628123456789",
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

### Messaging

```python
# Send text/media message
client.send_message(device_id="D", phone="628xxx", message="hi", media_url="https://...")

# Send file (BinaryIO, bytes, or pathlib.Path)
with open("doc.pdf", "rb") as f:
    client.send_message_file(device_id="D", phone="628xxx", file=f, file_name="doc.pdf", message="see attached")

# Send message fast (no typing indicator)
client.send_message_fast(device_id="D", phone="628xxx", message="hi")

# Send via WABA (WhatsApp Business API)
client.send_waba_message(device_id="D", phone="628xxx", message="hi")
```

### Devices

```python
client.list_devices()
client.device_status(device_id="D")
client.device_status_enhanced(device_id="D")
```

### User

```python
client.user_info()
```

### Contacts

```python
client.save_contact(phone="628xxx", name="John Doe", email="john@example.com")
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

```python
# Send OTP (device or WABA method)
client.send_otp_v2(
    phone="628xxx",
    device_id="D",
    method="device",             # "device" | "waba"
    app_name="MyApp",
    custom_message="Your OTP for {app}: {otp}",
)

# Verify OTP
client.verify_otp_v2(phone="628xxx", otp_code="123456")
```

### Broadcast

```python
# phones can be a list or comma-separated string
client.broadcast_message(
    device_id="D",
    phones=["628111", "628222", "628333"],
    message="Promo spesial!",
    delay=2.0,  # seconds between each message
)
```

### Deposits & Packages

```python
client.list_deposits(status="paid")   # "" | "paid" | "unpaid" | "expired"
client.list_packages()
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
    resp = client.send_message(device_id="D", phone="628xxx", message="hi")
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
