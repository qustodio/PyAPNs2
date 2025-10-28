"""Tests for credentials functionality including token management."""

import ssl
from unittest.mock import Mock, patch

import pytest
from apns2.credentials import CertificateCredentials, Credentials, TokenCredentials
from freezegun import freeze_time

TOPIC: str = "com.example.first_app"


@pytest.fixture
def token_credentials() -> TokenCredentials:
    return TokenCredentials(
        auth_key_path="test/eckey.pem",
        auth_key_id="1QBCDJ9RST",
        team_id="3Z24IP123A",
        token_lifetime=30,  # seconds
    )


def test_token_expiration_and_reuse(token_credentials: TokenCredentials) -> None:
    """Test that tokens are reused when not expired and regenerated when expired."""
    with freeze_time("2012-01-14 12:00:00"):
        header1 = token_credentials.get_authorization_header(TOPIC)
        assert header1.startswith("bearer ")

    # 20 seconds later, before expiration, same JWT
    with freeze_time("2012-01-14 12:00:20"):
        header2 = token_credentials.get_authorization_header(TOPIC)
        assert header1 == header2

    # 35 seconds later, after expiration, new JWT
    with freeze_time("2012-01-14 12:00:40"):
        header3 = token_credentials.get_authorization_header(TOPIC)
        assert header3 != header1
        assert header3.startswith("bearer ")


def test_token_credentials_initialization() -> None:
    """Test TokenCredentials initialization with different parameters."""
    # Test with custom encryption algorithm
    creds = TokenCredentials(
        auth_key_path="test/eckey.pem",
        auth_key_id="TEST123",
        team_id="TEAM456",
        encryption_algorithm="ES384",
        token_lifetime=60,
    )

    header = creds.get_authorization_header(TOPIC)
    assert header.startswith("bearer ")

    # Test that the token contains expected claims by decoding header
    import jwt

    token = header.split(" ")[1]
    # We can't verify signature without the actual key, but we can decode without verification
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["iss"] == "TEAM456"
    assert "iat" in payload


def test_base_credentials_ssl_context() -> None:
    """Test base Credentials class with SSL context."""
    ssl_context = ssl.create_default_context()
    credentials = Credentials(ssl_context=ssl_context)

    # Test connection creation
    connection = credentials.create_connection("api.push.apple.com", 443, None)
    assert connection is not None

    # Test authorization header (should be None for base class)
    assert credentials.get_authorization_header(TOPIC) is None


def test_base_credentials_proxy_configuration() -> None:
    """Test proxy configuration in base credentials."""
    credentials = Credentials()

    # Test with proxy
    connection = credentials.create_connection(
        "api.push.apple.com", 443, None, proxy_host="proxy.example.com", proxy_port=8080
    )
    assert connection is not None


@patch("apns2.credentials.ssl.create_default_context")
def test_certificate_credentials_initialization(mock_ssl_context: Mock) -> None:
    """Test CertificateCredentials initialization."""
    mock_context = Mock()
    mock_ssl_context.return_value = mock_context

    # Test with cert file only
    CertificateCredentials(cert_file="test.pem")
    mock_context.load_cert_chain.assert_called_once_with("test.pem", password=None)

    # Test with cert file and password
    mock_context.reset_mock()
    CertificateCredentials(cert_file="test.pem", password="secret")
    mock_context.load_cert_chain.assert_called_with("test.pem", password="secret")


@patch("apns2.credentials.ssl.create_default_context")
def test_certificate_credentials_with_cert_chain(mock_ssl_context: Mock) -> None:
    """Test CertificateCredentials with certificate chain."""
    mock_context = Mock()
    mock_ssl_context.return_value = mock_context

    # Test with both cert file and cert chain
    CertificateCredentials(cert_file="test.pem", cert_chain="chain.pem")

    # Should be called twice - once for cert_file, once for cert_chain
    assert mock_context.load_cert_chain.call_count == 2


def test_token_credentials_authorization_header_format() -> None:
    """Test that authorization header has correct format."""
    creds = TokenCredentials(
        auth_key_path="test/eckey.pem",
        auth_key_id="TEST123",
        team_id="TEAM456",
    )

    header = creds.get_authorization_header(TOPIC)

    # Should start with "bearer " (lowercase)
    assert header.startswith("bearer ")

    # Token part should be a valid JWT format (3 parts separated by dots)
    token = header.split(" ")[1]
    parts = token.split(".")
    assert len(parts) == 3  # header.payload.signature


def test_token_credentials_multiple_calls_same_topic() -> None:
    """Test multiple calls for the same topic reuse token when not expired."""
    creds = TokenCredentials(
        auth_key_path="test/eckey.pem",
        auth_key_id="TEST123",
        team_id="TEAM456",
        token_lifetime=60,
    )

    # Multiple calls should return the same token
    header1 = creds.get_authorization_header(TOPIC)
    header2 = creds.get_authorization_header(TOPIC)
    header3 = creds.get_authorization_header(TOPIC)

    assert header1 == header2 == header3


@patch("builtins.open", side_effect=FileNotFoundError("No such file"))
def test_token_credentials_invalid_key_path(mock_open: Mock) -> None:
    """Test TokenCredentials with invalid key path."""
    with pytest.raises(FileNotFoundError):
        TokenCredentials(
            auth_key_path="nonexistent.pem",
            auth_key_id="TEST123",
            team_id="TEAM456",
        )


def test_credentials_connection_configuration() -> None:
    """Test various connection configurations."""
    credentials = Credentials()

    # Test different server configurations
    connection1 = credentials.create_connection("api.push.apple.com", 443, "https")
    connection2 = credentials.create_connection(
        "api.development.push.apple.com", 2197, "https"
    )

    assert connection1 is not None
    assert connection2 is not None

    # Connections should be different instances
    assert connection1 is not connection2
