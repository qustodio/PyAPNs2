"""Tests for APNs error classes and exception handling."""

import pytest
from apns2.errors import (
    APNsException,
    BadDeviceToken,
    BadPayloadException,
    BadTopic,
    ConnectionFailed,
    exception_class_for_reason,
    InternalException,
    PayloadTooLarge,
    Unregistered,
)


def test_apns_exception_hierarchy() -> None:
    """Test that exception classes have correct inheritance."""
    # Test base exception
    base_exc = APNsException("test message")
    assert isinstance(base_exc, Exception)
    assert str(base_exc) == "test message"

    # Test payload exceptions inherit from BadPayloadException
    payload_exc = BadTopic("Invalid topic")
    assert isinstance(payload_exc, BadPayloadException)
    assert isinstance(payload_exc, APNsException)

    # Test device token exception
    device_exc = BadDeviceToken("Invalid token")
    assert isinstance(device_exc, APNsException)
    assert not isinstance(device_exc, BadPayloadException)


def test_unregistered_exception_with_timestamp() -> None:
    """Test Unregistered exception with timestamp handling."""
    # Test without timestamp
    exc1 = Unregistered()
    assert exc1.timestamp is None

    # Test with timestamp
    timestamp = "1234567890"
    exc2 = Unregistered(timestamp=timestamp)
    assert exc2.timestamp == timestamp


def test_exception_class_for_reason_mapping() -> None:
    """Test that exception_class_for_reason returns correct exception classes."""
    # Test common error reasons
    test_cases = [
        ("BadDeviceToken", BadDeviceToken),
        ("BadTopic", BadTopic),
        ("PayloadTooLarge", PayloadTooLarge),
        ("Unregistered", Unregistered),
    ]

    for reason, expected_class in test_cases:
        result_class = exception_class_for_reason(reason)
        assert result_class == expected_class

        # Verify we can instantiate the exception
        exc_instance = result_class("test message")
        assert isinstance(exc_instance, expected_class)
        assert isinstance(exc_instance, APNsException)


def test_exception_class_for_reason_invalid() -> None:
    """Test exception_class_for_reason with invalid reason."""
    with pytest.raises(KeyError):
        exception_class_for_reason("InvalidReason")


def test_all_defined_reasons_have_classes() -> None:
    """Test that all reasons defined in the mapping have corresponding classes."""
    # This test ensures that if new reasons are added to the mapping,
    # their corresponding classes exist and can be instantiated

    # Get all defined reasons from the function's dictionary

    # Common APNs error reasons that should be supported
    known_reasons = [
        "BadCollapseId",
        "BadDeviceToken",
        "BadExpirationDate",
        "BadMessageId",
        "BadPriority",
        "BadTopic",
        "DeviceTokenNotForTopic",
        "DuplicateHeaders",
        "IdleTimeout",
        "MissingDeviceToken",
        "MissingTopic",
        "PayloadEmpty",
        "TopicDisallowed",
        "BadCertificate",
        "BadCertificateEnvironment",
        "ExpiredProviderToken",
        "Forbidden",
        "InvalidProviderToken",
        "MissingProviderToken",
        "BadPath",
        "MethodNotAllowed",
        "Unregistered",
        "PayloadTooLarge",
        "TooManyProviderTokenUpdates",
        "TooManyRequests",
        "InternalServerError",
        "ServiceUnavailable",
        "Shutdown",
    ]

    for reason in known_reasons:
        try:
            exc_class = exception_class_for_reason(reason)
            # Verify the class can be instantiated
            instance = exc_class("test")
            assert isinstance(instance, APNsException)
        except KeyError:
            pytest.fail(
                f"Reason '{reason}' is not defined in exception_class_for_reason"
            )


def test_exception_messages() -> None:
    """Test that exceptions can hold custom messages."""
    message = "Custom error message"

    # Test various exception types with custom messages
    exceptions = [
        APNsException(message),
        BadDeviceToken(message),
        BadPayloadException(message),
        ConnectionFailed(message),
        InternalException(message),
    ]

    for exc in exceptions:
        assert str(exc) == message


def test_payload_exceptions_inheritance() -> None:
    """Test that payload-related exceptions inherit from BadPayloadException."""
    from apns2.errors import (
        BadCollapseId,
        BadExpirationDate,
        BadTopic,
        MissingTopic,
        PayloadEmpty,
        TopicDisallowed,
        PayloadTooLarge,
    )

    payload_exceptions = [
        BadCollapseId("test"),
        BadExpirationDate("test"),
        BadTopic("test"),
        MissingTopic("test"),
        PayloadEmpty("test"),
        TopicDisallowed("test"),
        PayloadTooLarge("test"),
    ]

    for exc in payload_exceptions:
        assert isinstance(exc, BadPayloadException)
        assert isinstance(exc, APNsException)


def test_internal_exceptions_inheritance() -> None:
    """Test that internal exceptions inherit from InternalException."""
    from apns2.errors import (
        BadMessageId,
        BadPriority,
        DuplicateHeaders,
        MethodNotAllowed,
    )

    internal_exceptions = [
        BadMessageId("test"),
        BadPriority("test"),
        DuplicateHeaders("test"),
        MethodNotAllowed("test"),
    ]

    for exc in internal_exceptions:
        assert isinstance(exc, InternalException)
        assert isinstance(exc, APNsException)


def test_connection_and_server_exceptions() -> None:
    """Test connection and server-related exceptions."""
    from apns2.errors import (
        ConnectionFailed,
        InternalServerError,
        ServiceUnavailable,
        Shutdown,
        TooManyRequests,
    )

    server_exceptions = [
        ConnectionFailed("Connection failed"),
        InternalServerError("Server error"),
        ServiceUnavailable("Service down"),
        Shutdown("Server shutting down"),
        TooManyRequests("Rate limited"),
    ]

    for exc in server_exceptions:
        assert isinstance(exc, APNsException)
        # These should not be payload or internal exceptions
        assert not isinstance(exc, BadPayloadException)
        assert not isinstance(exc, InternalException)
