from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from apns2.client import APNsClient, Notification
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


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_client.post.return_value = mock_response
    return mock_client


def test_client_initialization() -> None:
    """Test that APNsClient can be initialized with different credential types."""
    # Test with credentials object
    credentials = Credentials()
    client = APNsClient(credentials=credentials)
    assert client is not None

    # Test certificate initialization would require a valid certificate
    # So we just verify that the client can be initialized with a credentials object
    assert hasattr(client, "_APNsClient__credentials")
    assert client._APNsClient__credentials is not None


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
