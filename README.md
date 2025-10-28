# PyAPNs2

[![PyPI version](https://img.shields.io/pypi/v/apns2.svg)](https://pypi.python.org/pypi/apns2)
[![PyPI version](https://img.shields.io/pypi/pyversions/apns2.svg)](https://pypi.python.org/pypi/apns2)
[![Build Status](https://drone.pr0ger.dev/api/badges/Pr0Ger/PyAPNs2/status.svg)](https://drone.pr0ger.dev/Pr0Ger/PyAPNs2)

A modern Python library for interacting with the Apple Push Notification service (APNs) via HTTP/2 protocol using httpx
with full async support.

## Features

- ✅ **HTTP/2 Support**: Native HTTP/2 with httpx for optimal performance
- ✅ **Async/Await**: Full async support with sync wrapper for compatibility
- ✅ **Batch Processing**: Efficient batch notification sending with HTTP/2 multiplexing
- ✅ **Token & Certificate Auth**: Both JWT token and certificate authentication
- ✅ **Modern Python**: Python 3.13+ with full type hints
- ✅ **High Performance**: Optimized for high-throughput scenarios
- ✅ **Comprehensive Testing**: 93% test coverage with 60+ tests
- ✅ **Production Ready**: Battle-tested with proper error handling

## Quick Start

### Certificate Authentication

```python
from apns2.client import APNsClient
from apns2.payload import Payload

# Initialize client with certificate
client = APNsClient('path/to/cert.pem', use_sandbox=True)

# Create payload
payload = Payload(
    alert="Hello World!",
    sound="default",
    badge=1,
    custom={"user_id": 123}
)

# Send notification
token = 'device_token_hex_string'
topic = 'com.example.App'
result = client.send_notification(token, payload, topic)
print(f"Notification result: {result}")
```

### JWT Token Authentication

```python
from apns2.client import APNsClient
from apns2.credentials import TokenCredentials
from apns2.payload import Payload

# Initialize with JWT token credentials
credentials = TokenCredentials(
    auth_key_path='path/to/AuthKey_XXXXXXXXXX.p8',
    auth_key_id='XXXXXXXXXX',
    team_id='XXXXXXXXXX'
)
client = APNsClient(credentials=credentials, use_sandbox=True)

# Send notification
payload = Payload(alert="Hello from JWT!")
result = client.send_notification(token, payload, topic)
```

### Batch Notifications

```python
from apns2.client import APNsClient, Notification
from apns2.payload import Payload

client = APNsClient('cert.pem', use_sandbox=True)

# Create multiple notifications
notifications = [
    Notification(token='token1', payload=Payload(alert="Message 1")),
    Notification(token='token2', payload=Payload(alert="Message 2")),
    Notification(token='token3', payload=Payload(alert="Message 3")),
]

# Send batch (uses HTTP/2 multiplexing for efficiency)
results = client.send_notification_batch(notifications, topic='com.example.App')

# Process results
for token, result in results.items():
    if result == "Success":
        print(f"✅ {token}: Delivered")
    else:
        print(f"❌ {token}: {result}")
```

### Async Usage

```python
import asyncio
from apns2.client import APNsClient
from apns2.payload import Payload


async def send_notifications():
    client = APNsClient('cert.pem', use_sandbox=True)
    payload = Payload(alert="Async notification!")

    # Send single notification asynchronously
    result = await client.asend_notification(token, payload, topic)

    # Send batch asynchronously
    results = await client.asend_notification_batch(notifications, topic)

    return results


# Run async function
results = asyncio.run(send_notifications())
```

### Advanced Payload Configuration

```python
from apns2.payload import Payload, PayloadAlert

# Rich alert with title and subtitle
alert = PayloadAlert(
    title="New Message",
    subtitle="From John Doe",
    body="Hey, how are you doing?",
    title_localized_key="NEW_MESSAGE_TITLE",
    title_localized_args=["John Doe"]
)

payload = Payload(
    alert=alert,
    badge=5,
    sound="custom_sound.caf",
    category="MESSAGE_CATEGORY",
    thread_id="conversation_123",
    mutable_content=True,
    content_available=True,
    custom={
        "user_info": {"user_id": 12345},
        "deep_link": "app://conversation/123"
    }
)
```

### Push Type Configuration

```python
from apns2.client import APNsClient, NotificationPriority, NotificationType

client = APNsClient('cert.pem')

# VoIP notification
result = client.send_notification(
    token=voip_token,
    notification=payload,
    topic='com.example.App.voip',
    push_type=NotificationType.VoIP,
    priority=NotificationPriority.Immediate
)

# Background notification
background_payload = Payload(content_available=True)
result = client.send_notification(
    token=token,
    notification=background_payload,
    topic='com.example.App',
    push_type=NotificationType.Background
)
```

### Error Handling

```python
from apns2.client import APNsClient
from apns2.payload import Payload

client = APNsClient('cert.pem')
payload = Payload(alert="Test")

result = client.send_notification(token, payload, topic)

if result == "Success":
    print("✅ Notification sent successfully")
elif result == "BadDeviceToken":
    print("❌ Invalid device token")
elif result == "PayloadTooLarge":
    print("❌ Payload exceeds 4KB limit")
elif isinstance(result, tuple) and result[0] == "Unregistered":
    print(f"❌ Device unregistered at timestamp: {result[1]}")
else:
    print(f"❌ Error: {result}")
```

## Requirements

- **Python**: 3.13+ (with full type hints support)
- **httpx**: 0.28.1+ with HTTP/2 support (`pip install httpx[http2]`)
- **cryptography**: 1.7.2+ for certificate handling
- **PyJWT**: 2.0.0+ for token authentication

## Configuration Options

### Client Configuration

```python
client = APNsClient(
    credentials='cert.pem',  # Certificate path or credentials object
    use_sandbox=True,  # Use sandbox APNs server
    use_alternative_port=False,  # Use port 2197 instead of 443
    json_encoder=CustomEncoder,  # Custom JSON encoder class
    password='cert_password',  # Certificate password
    proxy_host='proxy.example.com',  # Proxy configuration
    proxy_port=8080
)
```

### Connection Settings

The client automatically configures optimal settings for APNs:

- **HTTP/2**: Enabled by default for multiplexing
- **Connection pooling**: Up to 1500 concurrent connections
- **Keep-alive**: 600 seconds for connection reuse
- **Timeouts**: Optimized for APNs (10s connect, 30s read)

## Development

This project uses Poetry for dependency management and modern Python tooling.

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Pr0Ger/PyAPNs2.git
cd PyAPNs2

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with test,dev

# Activate virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=apns2 --cov-report=html

# Run specific test file
poetry run pytest test/test_client.py

# Run async tests only
poetry run pytest -k "async"
```

### Code Quality

```bash
# Run pre-commit hooks
poetry run pre-commit run --all-files

# Type checking with mypy
poetry run mypy apns2/

# Format code
poetry run ruff format

# Lint code
poetry run ruff check --fix
```

## Performance

PyAPNs2 is optimized for high-performance scenarios:

- **HTTP/2 Multiplexing**: Send multiple notifications concurrently over a single connection
- **Async Support**: Non-blocking I/O for maximum throughput
- **Connection Reuse**: Efficient connection pooling and keep-alive
- **Batch Processing**: Optimized batch sending with proper error handling

## Migration from hyper-based versions

If migrating from older hyper-based versions:

1. **Update Python**: Minimum Python 3.13+
2. **Install new version**: `poetry add apns2` or `pip install apns2`
3. **Update imports**: Same API, no changes needed
4. **Async support**: New `asend_notification` and `asend_notification_batch` methods
5. **Improved performance**: Automatic HTTP/2 multiplexing

## Contributing

Contributions are welcome! Please read our contributing guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with tests
4. **Run** tests and linting (`poetry run pre-commit run --all-files`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to the branch (`git push origin feature/amazing-feature`)
7. **Create** a Pull Request

### Development Guidelines

- **Type hints**: All code must have proper type annotations
- **Tests**: Maintain 90%+ coverage for new code
- **Documentation**: Update README and docstrings
- **Code style**: Follow PEP 8 with ruff formatting

## License

PyAPNs2 is distributed under the terms of the MIT license.

See [LICENSE](LICENSE) file for the complete license details.

## Further Reading

- [Apple Push Notification Service Documentation](https://developer.apple.com/documentation/usernotifications)
- [HTTP/2 Protocol Specification](https://tools.ietf.org/html/rfc7540)
- [APNs Provider API](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/sending_notification_requests_to_apns)
