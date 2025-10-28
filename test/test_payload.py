"""Tests for APNs payload and payload alert functionality."""

import json

import pytest
from apns2.payload import MAX_PAYLOAD_SIZE, Payload, PayloadAlert


@pytest.fixture
def payload_alert() -> PayloadAlert:
    return PayloadAlert(
        title="title",
        title_localized_key="title_loc_k",
        title_localized_args=["title_loc_a"],
        subtitle="subtitle",
        subtitle_localized_key="subtitle_loc_k",
        subtitle_localized_args=["subtitle_loc_a"],
        body="body",
        body_localized_key="body_loc_k",
        body_localized_args=["body_loc_a"],
        action_localized_key="ac_loc_k",
        action="send",
        launch_image="img",
    )


def test_payload_alert_full_configuration(payload_alert: PayloadAlert) -> None:
    """Test PayloadAlert with all possible fields."""
    assert payload_alert.dict() == {
        "title": "title",
        "title-loc-key": "title_loc_k",
        "title-loc-args": ["title_loc_a"],
        "subtitle": "subtitle",
        "subtitle-loc-key": "subtitle_loc_k",
        "subtitle-loc-args": ["subtitle_loc_a"],
        "body": "body",
        "loc-key": "body_loc_k",
        "loc-args": ["body_loc_a"],
        "action-loc-key": "ac_loc_k",
        "action": "send",
        "launch-image": "img",
    }


def test_payload_alert_minimal() -> None:
    """Test PayloadAlert with minimal configuration."""
    alert = PayloadAlert(body="Simple message")
    assert alert.dict() == {"body": "Simple message"}


def test_payload_alert_empty() -> None:
    """Test PayloadAlert with no fields set."""
    alert = PayloadAlert()
    assert alert.dict() == {}


def test_payload_alert_only_title() -> None:
    """Test PayloadAlert with only title."""
    alert = PayloadAlert(title="Just a title")
    assert alert.dict() == {"title": "Just a title"}


def test_payload_alert_localized_only() -> None:
    """Test PayloadAlert with only localized content."""
    alert = PayloadAlert(
        title_localized_key="TITLE_KEY",
        title_localized_args=["arg1", "arg2"],
        body_localized_key="BODY_KEY",
        body_localized_args=["body_arg"],
    )
    assert alert.dict() == {
        "title-loc-key": "TITLE_KEY",
        "title-loc-args": ["arg1", "arg2"],
        "loc-key": "BODY_KEY",
        "loc-args": ["body_arg"],
    }


def test_payload_full_configuration() -> None:
    """Test Payload with all possible fields."""
    payload = Payload(
        alert="my_alert",
        badge=2,
        sound="chime",
        content_available=True,
        mutable_content=True,
        category="my_category",
        url_args="args",
        custom={"extra": "something"},
        thread_id="42",
    )
    assert payload.dict() == {
        "aps": {
            "alert": "my_alert",
            "badge": 2,
            "sound": "chime",
            "content-available": 1,
            "mutable-content": 1,
            "category": "my_category",
            "url-args": "args",
            "thread-id": "42",
        },
        "extra": "something",
    }


def test_payload_minimal() -> None:
    """Test Payload with minimal configuration."""
    payload = Payload(alert="Simple alert")
    assert payload.dict() == {"aps": {"alert": "Simple alert"}}


def test_payload_background_only() -> None:
    """Test background-only payload."""
    payload = Payload(content_available=True)
    assert payload.dict() == {"aps": {"content-available": 1}}


def test_payload_badge_only() -> None:
    """Test payload with only badge."""
    payload = Payload(badge=5)
    assert payload.dict() == {"aps": {"badge": 5}}


def test_payload_badge_zero() -> None:
    """Test payload with badge set to 0 (should clear badge)."""
    payload = Payload(badge=0)
    assert payload.dict() == {"aps": {"badge": 0}}


def test_payload_with_payload_alert(payload_alert: PayloadAlert) -> None:
    """Test Payload using PayloadAlert object."""
    payload = Payload(alert=payload_alert)
    assert payload.dict() == {
        "aps": {
            "alert": {
                "title": "title",
                "title-loc-key": "title_loc_k",
                "title-loc-args": ["title_loc_a"],
                "subtitle": "subtitle",
                "subtitle-loc-key": "subtitle_loc_k",
                "subtitle-loc-args": ["subtitle_loc_a"],
                "body": "body",
                "loc-key": "body_loc_k",
                "loc-args": ["body_loc_a"],
                "action-loc-key": "ac_loc_k",
                "action": "send",
                "launch-image": "img",
            }
        }
    }


def test_payload_complex_custom_data() -> None:
    """Test payload with complex custom data."""
    custom_data = {
        "user_info": {
            "user_id": 12345,
            "preferences": ["pref1", "pref2"],
            "metadata": {"timestamp": "2023-01-01T00:00:00Z", "version": "1.0"},
        },
        "action_data": {"type": "navigate", "target": "home_screen"},
    }

    payload = Payload(alert="You have a new message", badge=1, custom=custom_data)

    result = payload.dict()
    assert result["aps"]["alert"] == "You have a new message"
    assert result["aps"]["badge"] == 1
    assert result["user_info"] == custom_data["user_info"]
    assert result["action_data"] == custom_data["action_data"]


def test_payload_sound_variations() -> None:
    """Test different sound configurations."""
    # Default sound
    payload1 = Payload(alert="Test", sound="default")
    assert payload1.dict()["aps"]["sound"] == "default"

    # Custom sound
    payload2 = Payload(alert="Test", sound="custom.caf")
    assert payload2.dict()["aps"]["sound"] == "custom.caf"

    # No sound
    payload3 = Payload(alert="Test")
    assert "sound" not in payload3.dict()["aps"]


def test_payload_url_args_list() -> None:
    """Test payload with url_args as list."""
    payload = Payload(alert="Open URL", url_args=["arg1", "arg2", "arg3"])
    assert payload.dict()["aps"]["url-args"] == ["arg1", "arg2", "arg3"]


def test_payload_serialization_size() -> None:
    """Test that payload serialization respects size limits."""
    # Create a payload that's close to the limit
    large_text = "x" * 3000
    payload = Payload(alert=large_text, custom={"data": "small"})

    # Serialize to JSON to check size
    json_str = json.dumps(payload.dict(), separators=(",", ":"))

    # Should be under the limit
    assert len(json_str.encode("utf-8")) < MAX_PAYLOAD_SIZE


def test_payload_empty() -> None:
    """Test completely empty payload."""
    payload = Payload()
    assert payload.dict() == {"aps": {}}


def test_payload_thread_id_variations() -> None:
    """Test different thread_id configurations."""
    # String thread ID
    payload1 = Payload(alert="Test", thread_id="conversation-123")
    assert payload1.dict()["aps"]["thread-id"] == "conversation-123"

    # Numeric thread ID (as string)
    payload2 = Payload(alert="Test", thread_id="456")
    assert payload2.dict()["aps"]["thread-id"] == "456"


def test_payload_boolean_flags() -> None:
    """Test boolean flag handling."""
    # Both flags true
    payload1 = Payload(content_available=True, mutable_content=True)
    result1 = payload1.dict()["aps"]
    assert result1["content-available"] == 1
    assert result1["mutable-content"] == 1

    # Both flags false (should not appear in dict)
    payload2 = Payload(content_available=False, mutable_content=False)
    result2 = payload2.dict()["aps"]
    assert "content-available" not in result2
    assert "mutable-content" not in result2

    # Mixed flags
    payload3 = Payload(content_available=True, mutable_content=False)
    result3 = payload3.dict()["aps"]
    assert result3["content-available"] == 1
    assert "mutable-content" not in result3


def test_payload_with_none_values() -> None:
    """Test that None values are properly handled."""
    payload = Payload(
        alert="Test", badge=None, sound=None, category=None, thread_id=None, custom=None
    )

    result = payload.dict()
    assert result == {"aps": {"alert": "Test"}}

    # None values should not create keys
    assert "badge" not in result["aps"]
    assert "sound" not in result["aps"]
    assert "category" not in result["aps"]
    assert "thread-id" not in result["aps"]
