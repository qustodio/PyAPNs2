import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _is_celery_worker() -> bool:
    """
    Detect if we're running inside a Celery worker.
    This helps avoid memory leaks caused by Celery's poor async support.
    """
    logger.info("Detecting if running in Celery worker environment...")
    # Check environment variables that Celery sets
    celery_env_vars = [
        "CELERY_LOADER",
        "CELERY_WORKER_DIRECT",
        "CELERY_CURRENT_TASK",
        "C_FORCE_ROOT",
    ]
    if any(key in os.environ for key in celery_env_vars):
        return True

    # Check if we're in a process that looks like a Celery worker
    try:
        if "celery" in sys.argv[0].lower():
            return True
        if any("celery" in arg.lower() for arg in sys.argv):
            return True
    except (AttributeError, IndexError):
        pass

    # Check if celery modules are in the call stack
    try:
        import inspect

        for frame_info in inspect.stack():
            filename = frame_info.filename.lower()
            if "celery" in filename and ("worker" in filename or "task" in filename):
                return True
    except Exception:
        pass

    # Check if current task context exists (most reliable for active tasks)
    try:
        from celery import current_task

        if current_task and current_task.request:
            return True
    except (ImportError, AttributeError):
        pass

    return False


# Constant that gets computed once when the module is imported
IS_CELERY_WORKER: bool = _is_celery_worker()
