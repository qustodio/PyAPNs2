from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apns2.client import (
    APNsClient,
    Notification,
    NotificationPriority,
    NotificationType,
)
from apns2.credentials import Credentials
from apns2.payload import Payload

TOPIC: str = "com.example.App"


@pytest.fixture(scope="session")
def tokens() -> list[str]:
    return ["%064x" % i for i in range(10)]  # Reducido para tests más rápidos


@pytest.fixture(scope="session")
def notifications(tokens: list[str]) -> list[Notification]:
    payload = Payload(alert="Test alert")
    return [Notification(token=token, payload=payload) for token in tokens]


@pytest.fixture
def mock_credentials() -> Mock:
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()

    # Mock the post method to return a successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response

    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    return credentials


@pytest.fixture
def client(mock_credentials: Mock) -> APNsClient:
    return APNsClient(credentials=mock_credentials)


def test_celery_detection_optimization() -> None:
    """Test that Celery detection uses the pre-computed constant."""
    mock_credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_credentials.create_connection.return_value = mock_connection

    # Import the constant to verify it exists and is accessible
    from apns2.helpers import IS_CELERY_WORKER

    # Verify the constant is a boolean
    assert isinstance(IS_CELERY_WORKER, bool)

    # Create clients and verify they use the constant
    client1 = APNsClient(credentials=mock_credentials)
    client2 = APNsClient(credentials=mock_credentials)

    # Verify both clients have the same Celery detection result
    assert client1._is_celery_worker == IS_CELERY_WORKER
    assert client2._is_celery_worker == IS_CELERY_WORKER
    assert client1._is_celery_worker == client2._is_celery_worker


def test_multiple_clients_performance() -> None:
    """Test that creating multiple clients is efficient (uses pre-computed constant)."""
    from apns2.helpers import IS_CELERY_WORKER

    mock_credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_credentials.create_connection.return_value = mock_connection

    # Create 10 clients - all should use the same pre-computed constant
    clients = []
    for i in range(10):
        client = APNsClient(credentials=mock_credentials)
        clients.append(client)

    # Verify all clients have the same result (from the constant)
    expected_result = IS_CELERY_WORKER
    for client in clients:
        assert client._is_celery_worker == expected_result


def test_client_initialization_with_different_options() -> None:
    """Test APNsClient initialization with various configuration options."""
    # Test basic initialization
    credentials = Credentials()
    client = APNsClient(credentials=credentials)
    assert client._server == APNsClient.LIVE_SERVER
    assert client._port == APNsClient.DEFAULT_PORT

    # Test sandbox mode
    client_sandbox = APNsClient(credentials=credentials, use_sandbox=True)
    assert client_sandbox._server == APNsClient.SANDBOX_SERVER

    # Test alternative port
    client_alt_port = APNsClient(credentials=credentials, use_alternative_port=True)
    assert client_alt_port._port == APNsClient.ALTERNATIVE_PORT

    # Test both sandbox and alternative port
    client_both = APNsClient(
        credentials=credentials, use_sandbox=True, use_alternative_port=True
    )
    assert client_both._server == APNsClient.SANDBOX_SERVER
    assert client_both._port == APNsClient.ALTERNATIVE_PORT


def test_send_notification_success(client: APNsClient, mock_credentials: Mock) -> None:
    """Test sending a single notification successfully."""
    token = "1" * 64
    payload = Payload(alert="Test message")

    # Mock successful response
    mock_connection = mock_credentials.create_connection.return_value
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response

    result = client.send_notification(token, payload, TOPIC)
    assert result == "Success"

    # Verify the connection was called
    mock_connection.post.assert_called_once()


def test_send_notification_error_response(
    client: APNsClient, mock_credentials: Mock
) -> None:
    """Test handling error responses from APNs."""
    token = "1" * 64
    payload = Payload(alert="Test message")

    # Mock error response
    mock_connection = mock_credentials.create_connection.return_value
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"reason": "BadDeviceToken"}
    mock_connection.post.return_value = mock_response

    result = client.send_notification(token, payload, TOPIC)
    assert result == "BadDeviceToken"


def test_send_notification_410_response(
    client: APNsClient, mock_credentials: Mock
) -> None:
    """Test handling 410 (Gone) responses with timestamp."""
    token = "1" * 64
    payload = Payload(alert="Test message")

    # Mock 410 response
    mock_connection = mock_credentials.create_connection.return_value
    mock_response = Mock()
    mock_response.status_code = 410
    mock_response.json.return_value = {
        "reason": "Unregistered",
        "timestamp": 1234567890,
    }
    mock_connection.post.return_value = mock_response

    result = client.send_notification(token, payload, TOPIC)
    assert result == ("Unregistered", "1234567890")


def test_send_empty_batch_returns_empty_dict(
    client: APNsClient, mock_credentials: Mock
) -> None:
    """Test that sending an empty batch returns an empty dictionary."""
    results = client.send_notification_batch([], TOPIC)
    assert results == {}


def test_send_notification_batch_success(
    client: APNsClient,
    mock_credentials: Mock,
    tokens: list[str],
    notifications: list[Notification],
) -> None:
    """Test sending a batch of notifications successfully."""
    # Mock successful responses for all notifications
    mock_connection = mock_credentials.create_connection.return_value
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response

    results = client.send_notification_batch(notifications, TOPIC)

    # All notifications should succeed
    expected_results = {token: "Success" for token in tokens}
    assert results == expected_results

    # Should have called post for each notification
    assert mock_connection.post.call_count == len(notifications)


def test_send_notification_batch_mixed_results(
    client: APNsClient, mock_credentials: Mock, tokens: list[str]
) -> None:
    """Test batch sending with mixed success/error results."""
    notifications = [
        Notification(token=tokens[0], payload=Payload(alert="Test 1")),
        Notification(token=tokens[1], payload=Payload(alert="Test 2")),
        Notification(token=tokens[2], payload=Payload(alert="Test 3")),
    ]

    mock_connection = mock_credentials.create_connection.return_value

    # Define different responses for each call based on URL
    def mock_post_url_check(url: str, **kwargs: Any) -> Mock:
        if tokens[0] in url:
            response = Mock()
            response.status_code = 200
            response.json.return_value = {}
            return response
        elif tokens[1] in url:
            response = Mock()
            response.status_code = 400
            response.json.return_value = {"reason": "BadDeviceToken"}
            return response
        else:  # tokens[2]
            response = Mock()
            response.status_code = 410
            response.json.return_value = {
                "reason": "Unregistered",
                "timestamp": 1234567890,
            }
            return response

    mock_connection.post.side_effect = mock_post_url_check

    results = client.send_notification_batch(notifications, TOPIC)

    expected_results = {
        tokens[0]: "Success",
        tokens[1]: "BadDeviceToken",
        tokens[2]: ("Unregistered", "1234567890"),
    }
    assert results == expected_results


def test_send_notification_json_exception_handling(
    client: APNsClient, mock_credentials: Mock
) -> None:
    """Test handling JSON parsing exceptions."""
    token = "1" * 64
    payload = Payload(alert="Test message")

    # Mock response that throws JSON exception
    mock_connection = mock_credentials.create_connection.return_value
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.side_effect = Exception("Invalid JSON")
    mock_connection.post.return_value = mock_response

    result = client.send_notification(token, payload, TOPIC)
    assert result == "InternalException"


def test_notification_priority_and_type_inference() -> None:
    """Test that push types are correctly inferred from topic and payload."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64

    # Test VoIP inference
    payload = Payload(alert="Test")
    client.send_notification(token, payload, "com.example.app.voip")

    # Check that the call was made with VoIP push type
    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert headers.get("apns-push-type") == "voip"


def test_notification_with_custom_priority() -> None:
    """Test sending notification with custom priority."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    # Test with delayed priority
    client.send_notification(
        token, payload, TOPIC, priority=NotificationPriority.Delayed
    )

    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert headers.get("apns-priority") == "5"


def test_notification_with_collapse_id_and_expiration() -> None:
    """Test notification with collapse ID and expiration."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    client.send_notification(
        token,
        payload,
        TOPIC,
        collapse_id="test-collapse",
        expiration=1234567890,
        push_type=NotificationType.Alert,
    )

    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert headers.get("apns-collapse-id") == "test-collapse"
    assert headers.get("apns-expiration") == "1234567890"
    assert headers.get("apns-push-type") == "alert"


def test_certificate_credentials_initialization() -> None:
    """Test client initialization with certificate path."""
    with patch("apns2.client.CertificateCredentials") as mock_cert_creds:
        mock_cert_instance = Mock()
        mock_cert_creds.return_value = mock_cert_instance

        client = APNsClient(credentials="fake_cert.pem", password="test_password")

        mock_cert_creds.assert_called_once_with("fake_cert.pem", "test_password")
        # Verify credentials were set (accessing private attribute for testing)
        assert hasattr(client, "_APNsClient__credentials")
        assert client._APNsClient__credentials == mock_cert_instance  # type: ignore[attr-defined]


def test_push_type_inference_background() -> None:
    """Test background push type inference."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64

    # Background payload (no alert, badge, or sound)
    payload = Payload(content_available=True)
    client.send_notification(token, payload, TOPIC)

    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert headers.get("apns-push-type") == "background"


def test_authorization_header_inclusion() -> None:
    """Test that authorization header is included when provided by credentials."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = "Bearer test-token"

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    client.send_notification(token, payload, TOPIC)

    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert headers.get("authorization") == "Bearer test-token"


def test_multiple_topic_types_inference() -> None:
    """Test push type inference for different topic suffixes."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    # Test different topic suffixes
    test_cases = [
        ("com.example.app.complication", "complication"),
        ("com.example.app.pushkit.fileprovider", "fileprovider"),
        ("com.example.app.voip", "voip"),
        ("com.example.app", "alert"),  # regular app with alert
    ]

    for topic, expected_type in test_cases:
        mock_connection.reset_mock()
        client.send_notification(token, payload, topic)

        call_args = mock_connection.post.call_args
        headers = (
            call_args[1]["headers"]
            if "headers" in call_args[1]
            else call_args.kwargs["headers"]
        )
        assert headers.get("apns-push-type") == expected_type, (
            f"Failed for topic {topic}"
        )


def test_json_encoder_usage() -> None:
    """Test that custom JSON encoder is used when provided."""
    import json

    class CustomEncoder(json.JSONEncoder):
        def encode(self, obj: Any) -> str:
            return super().encode({"custom": True, **obj})

    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials, json_encoder=CustomEncoder)
    token = "1" * 64
    payload = Payload(alert="Test")

    client.send_notification(token, payload, TOPIC)

    # Verify the custom encoder was used
    call_args = mock_connection.post.call_args
    sent_data = (
        call_args[1]["content"]
        if "content" in call_args[1]
        else call_args.kwargs["content"]
    )
    parsed_data = json.loads(sent_data.decode())
    assert "custom" in parsed_data


@pytest.mark.asyncio
async def test_async_send_notification_direct() -> None:
    """Test async notification sending directly."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test message")

    result = await client.asend_notification(token, payload, TOPIC)
    assert result == "Success"
    mock_connection.post.assert_called_once()


@pytest.mark.asyncio
async def test_async_batch_with_exception_handling() -> None:
    """Test async batch handling when some requests fail with exceptions."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    notifications = [
        Notification(token="1" * 64, payload=Payload(alert="Test 1")),
        Notification(token="2" * 64, payload=Payload(alert="Test 2")),
    ]

    # Mock one success and one exception
    mock_success_response = Mock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {}

    mock_connection.post.side_effect = [
        mock_success_response,
        Exception("Connection error"),
    ]

    results = await client.asend_notification_batch(notifications, TOPIC)

    assert results["1" * 64] == "Success"
    assert results["2" * 64] == "InternalException"


def test_payload_size_limits() -> None:
    """Test notification with very large payload."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 413  # Payload Too Large
    mock_response.json.return_value = {"reason": "PayloadTooLarge"}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64

    # Create a very large payload
    large_custom_data = {"large_data": "x" * 5000}  # > 4KB
    payload = Payload(alert="Test", custom=large_custom_data)

    result = client.send_notification(token, payload, TOPIC)
    assert result == "PayloadTooLarge"


def test_various_http_error_codes() -> None:
    """Test handling of various HTTP error codes from APNs."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    # Test different error scenarios
    error_cases = [
        (400, {"reason": "BadDeviceToken"}, "BadDeviceToken"),
        (403, {"reason": "Forbidden"}, "Forbidden"),
        (404, {"reason": "BadPath"}, "BadPath"),
        (405, {"reason": "MethodNotAllowed"}, "MethodNotAllowed"),
        (413, {"reason": "PayloadTooLarge"}, "PayloadTooLarge"),
        (429, {"reason": "TooManyRequests"}, "TooManyRequests"),
        (500, {"reason": "InternalServerError"}, "InternalServerError"),
        (503, {"reason": "ServiceUnavailable"}, "ServiceUnavailable"),
    ]

    for status_code, json_response, expected_result in error_cases:
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_response
        mock_connection.post.return_value = mock_response

        result = client.send_notification(token, payload, TOPIC)
        assert result == expected_result, f"Failed for status code {status_code}"


def test_missing_topic_handling() -> None:
    """Test notification sending without topic."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    client = APNsClient(credentials=credentials)
    token = "1" * 64
    payload = Payload(alert="Test")

    # Send without topic (None)
    client.send_notification(token, payload, None)

    call_args = mock_connection.post.call_args
    headers = (
        call_args[1]["headers"]
        if "headers" in call_args[1]
        else call_args.kwargs["headers"]
    )
    assert "apns-topic" not in headers


def test_notification_url_construction() -> None:
    """Test that notification URLs are constructed correctly."""
    credentials = Mock(spec=Credentials)
    mock_connection = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_connection.post.return_value = mock_response
    credentials.create_connection.return_value = mock_connection
    credentials.get_authorization_header.return_value = None

    # Test with different configurations
    client_prod = APNsClient(credentials=credentials, use_sandbox=False)
    client_sandbox = APNsClient(
        credentials=credentials, use_sandbox=True, use_alternative_port=True
    )

    token = "1" * 64
    payload = Payload(alert="Test")

    # Test production URL
    client_prod.send_notification(token, payload, TOPIC)
    call_args = mock_connection.post.call_args
    url = call_args[0][0] if len(call_args[0]) > 0 else call_args.args[0]
    assert (
        f"https://{APNsClient.LIVE_SERVER}:{APNsClient.DEFAULT_PORT}/3/device/{token}"
        in url
    )

    # Reset mock and test sandbox URL
    mock_connection.reset_mock()
    client_sandbox.send_notification(token, payload, TOPIC)
    call_args = mock_connection.post.call_args
    url = call_args[0][0] if len(call_args[0]) > 0 else call_args.args[0]
    assert (
        f"https://{APNsClient.SANDBOX_SERVER}:{APNsClient.ALTERNATIVE_PORT}/3/device/{token}"
        in url
    )
