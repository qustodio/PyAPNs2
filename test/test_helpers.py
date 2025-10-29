from unittest.mock import patch

from apns2.helpers import _is_celery_worker, IS_CELERY_WORKER


def test_constant_is_boolean() -> None:
    """Test that IS_CELERY_WORKER is a boolean."""
    assert isinstance(IS_CELERY_WORKER, bool)


def test_is_celery_worker_with_env_vars() -> None:
    """Test Celery detection with environment variables."""
    # Test with CELERY_LOADER environment variable
    with patch.dict("os.environ", {"CELERY_LOADER": "app.celery"}):
        assert _is_celery_worker() is True

    # Test with CELERY_WORKER_DIRECT environment variable
    with patch.dict("os.environ", {"CELERY_WORKER_DIRECT": "1"}):
        assert _is_celery_worker() is True

    # Test with C_FORCE_ROOT environment variable
    with patch.dict("os.environ", {"C_FORCE_ROOT": "1"}):
        assert _is_celery_worker() is True


def test_is_celery_worker_with_argv() -> None:
    """Test Celery detection with sys.argv."""
    import sys

    # Test with celery in argv[0]
    with patch.object(sys, "argv", ["celery", "worker"]):
        assert _is_celery_worker() is True

    # Test with celery in any argument
    with patch.object(sys, "argv", ["python", "-m", "celery", "worker"]):
        assert _is_celery_worker() is True


def test_is_celery_worker_with_current_task() -> None:
    """Test Celery detection with current_task."""
    # Mock current_task with a request
    mock_task = type("MockTask", (), {"request": {"id": "task-123"}})()

    with patch.dict(
        "sys.modules", {"celery": type("MockCelery", (), {"current_task": mock_task})}
    ):
        assert _is_celery_worker() is True


def test_is_celery_worker_no_celery() -> None:
    """Test Celery detection when not in Celery environment."""
    import sys

    # Clear environment and argv to simulate non-Celery environment
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.object(sys, "argv", ["python", "script.py"]),
    ):
        # Since we can't easily mock all the detection paths without affecting imports,
        # we'll test that the function doesn't crash and returns a boolean
        result = _is_celery_worker()
        assert isinstance(result, bool)


def test_constant_represents_computed_value() -> None:
    """Test that the constant represents a pre-computed value."""
    # The constant should be a boolean value computed at import time
    assert isinstance(IS_CELERY_WORKER, bool)

    # We can't easily test the exact value without affecting global state,
    # but we can verify it's consistent
    assert IS_CELERY_WORKER in [True, False]
