import asyncio
import collections
import json
import logging
from enum import Enum
from typing import Any, Callable, Coroutine, Iterable, TYPE_CHECKING, TypeVar

from .credentials import CertificateCredentials, Credentials
from .helpers import IS_CELERY_WORKER
from .payload import Payload

if TYPE_CHECKING:
    from httpx import Response

T = TypeVar("T")


class NotificationPriority(Enum):
    Immediate = "10"
    Delayed = "5"


class NotificationType(Enum):
    Alert = "alert"
    Background = "background"
    VoIP = "voip"
    Complication = "complication"
    FileProvider = "fileprovider"
    MDM = "mdm"


Notification = collections.namedtuple("Notification", ["token", "payload"])

DEFAULT_APNS_PRIORITY = NotificationPriority.Immediate

logger = logging.getLogger(__name__)


class APNsClient:
    SANDBOX_SERVER = "api.development.push.apple.com"
    LIVE_SERVER = "api.push.apple.com"

    DEFAULT_PORT = 443
    ALTERNATIVE_PORT = 2197

    def __init__(
        self,
        credentials: Credentials | str,
        use_sandbox: bool = False,
        use_alternative_port: bool = False,
        proto: str | None = None,
        json_encoder: type | None = None,
        password: str | None = None,
        proxy_host: str | None = None,
        proxy_port: int | None = None,
    ) -> None:
        if isinstance(credentials, str):
            self.__credentials = CertificateCredentials(credentials, password)  # type: Credentials
        else:
            self.__credentials = credentials
        self._init_connection(
            use_sandbox, use_alternative_port, proto, proxy_host, proxy_port
        )

        self.__json_encoder = json_encoder

        # Use the pre-computed Celery detection constant
        self._is_celery_worker = IS_CELERY_WORKER

    def _init_connection(
        self,
        use_sandbox: bool,
        use_alternative_port: bool,
        proto: str | None,
        proxy_host: str | None,
        proxy_port: int | None,
    ) -> None:
        self._server = self.SANDBOX_SERVER if use_sandbox else self.LIVE_SERVER
        self._port = (
            self.ALTERNATIVE_PORT if use_alternative_port else self.DEFAULT_PORT
        )
        self._connection = self.__credentials.create_connection(
            self._server, self._port, proto, proxy_host, proxy_port
        )

    def send_notification(
        self,
        token_hex: str,
        notification: Payload,
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> str | tuple[str, str]:
        return self._run_async(
            lambda: self.asend_notification(
                token_hex,
                notification,
                topic,
                priority,
                expiration,
                collapse_id,
                push_type,
            )
        )

    def send_notification_batch(
        self,
        notifications: Iterable[Notification],
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> dict[str, str | tuple[str, str]]:
        return self._run_async(
            lambda: self.asend_notification_batch(
                notifications, topic, priority, expiration, collapse_id, push_type
            )
        )

    async def asend_notification(
        self,
        token_hex: str,
        notification: Payload,
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> str | tuple[str, str]:
        temp_notification = Notification(token=token_hex, payload=notification)
        response = await self._send_single_notification(
            temp_notification, topic, priority, expiration, collapse_id, push_type
        )
        return self._process_response(response)

    async def asend_notification_batch(
        self,
        notifications: Iterable[Notification],
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> dict[str, str | tuple[str, str]]:
        notifications_list = list(notifications)
        if not notifications_list:
            return {}

        logger.info(
            f"Starting async batch send of {len(notifications_list)} notifications"
        )

        # Create all async tasks at once for HTTP/2 multiplexing
        tasks = [
            self._send_single_notification(
                notification, topic, priority, expiration, collapse_id, push_type
            )
            for notification in notifications_list
        ]

        logger.info(f"Created {len(tasks)} concurrent HTTP/2 streams")

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results: dict[str, str | tuple[str, str]] = {}
        for notification, response in zip(notifications_list, responses):
            if isinstance(response, Exception):
                logger.error(
                    f"Error sending notification to {notification.token}: {response}"
                )
                results[notification.token] = "InternalException"
            else:
                results[notification.token] = self._process_response(response)
                logger.debug(
                    f"Got result for {notification.token}: {results[notification.token]}"
                )

        logger.info(f"Completed async batch send of {len(results)} notifications")
        return results

    async def _send_single_notification(
        self,
        notification: Notification,
        topic: str | None,
        priority: NotificationPriority,
        expiration: int | None,
        collapse_id: str | None,
        push_type: NotificationType | None,
    ) -> "Response":
        json_str = json.dumps(
            notification.payload.dict(),
            cls=self.__json_encoder,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        json_payload = json_str.encode("utf-8")

        headers = {}

        inferred_push_type = None
        if topic is not None:
            headers["apns-topic"] = topic
            if topic.endswith(".voip"):
                inferred_push_type = NotificationType.VoIP.value
            elif topic.endswith(".complication"):
                inferred_push_type = NotificationType.Complication.value
            elif topic.endswith(".pushkit.fileprovider"):
                inferred_push_type = NotificationType.FileProvider.value
            elif any([
                notification.payload.alert is not None,
                notification.payload.badge is not None,
                notification.payload.sound is not None,
            ]):
                inferred_push_type = NotificationType.Alert.value
            else:
                inferred_push_type = NotificationType.Background.value

        if push_type:
            inferred_push_type = push_type.value

        if inferred_push_type:
            headers["apns-push-type"] = inferred_push_type

        if priority != DEFAULT_APNS_PRIORITY:
            headers["apns-priority"] = priority.value

        if expiration is not None:
            headers["apns-expiration"] = "%d" % expiration

        auth_header = self.__credentials.get_authorization_header(topic)
        if auth_header is not None:
            headers["authorization"] = auth_header

        if collapse_id is not None:
            headers["apns-collapse-id"] = collapse_id

        url = f"https://{self._server}:{self._port}/3/device/{notification.token}"

        # Use self._connection directly - this is the key improvement
        # Multiple calls can execute concurrently as HTTP/2 streams
        response = await self._connection.post(
            url, content=json_payload, headers=headers
        )
        return response

    def _process_response(self, response: "Response") -> str | tuple[str, str]:
        if response.status_code == 200:
            return "Success"
        else:
            try:
                data = response.json()
                if response.status_code == 410:
                    reason = str(data.get("reason", "Unregistered"))
                    timestamp = str(data.get("timestamp", ""))
                    return reason, timestamp
                else:
                    return str(data.get("reason", "InternalException"))
            except Exception:
                return "InternalException"

    def _run_async(self, coro_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """
        Run an async coroutine from a sync context in the most robust way possible.
        Takes a function that creates a fresh coroutine each time to avoid reuse issues.
        Handles all possible event loop scenarios to prevent any asyncio-related errors.

        Special handling for Celery: Uses separate thread strategy to avoid memory leaks
        caused by Celery's poor async support (see: https://github.com/celery/celery/issues/6552)
        """
        # Special case: If running in Celery, always use separate thread to avoid memory leaks
        if self._is_celery_worker:
            return self._run_in_separate_thread(coro_factory)

        # Strategy 1: Try to detect if we're in an async context
        try:
            asyncio.get_running_loop()
            # We're in an async context - must use a separate thread
            return self._run_in_separate_thread(coro_factory)
        except RuntimeError:
            # No running event loop - we can proceed with direct execution
            pass

        # Strategy 2: Try to use asyncio.run (safest for most cases)
        try:
            fresh_coro = coro_factory()
            return asyncio.run(fresh_coro)
        except RuntimeError as e:
            error_msg = str(e).lower()
            # Handle various event loop related errors
            if any(
                phrase in error_msg
                for phrase in [
                    "event loop is closed",
                    "event loop is running",
                    "cannot be called from a running event loop",
                    "there is no current event loop",
                ]
            ):
                # Fall back to manual event loop management
                return self._run_with_manual_loop(coro_factory)
            else:
                # Unknown RuntimeError, try thread approach as last resort
                return self._run_in_separate_thread(coro_factory)
        except Exception:
            # Any other exception, try thread approach as last resort
            return self._run_in_separate_thread(coro_factory)

    def _run_in_separate_thread(
        self, coro_factory: Callable[[], Coroutine[Any, Any, T]]
    ) -> T:
        """Run coroutine in a completely isolated thread with its own event loop."""
        import threading

        result: T | None = None
        exception: Exception | None = None

        def run_in_thread() -> None:
            nonlocal result, exception
            try:
                # Create completely isolated event loop in this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    fresh_coro = coro_factory()
                    result = new_loop.run_until_complete(fresh_coro)
                finally:
                    # Clean up properly
                    try:
                        new_loop.close()
                    except Exception:
                        pass  # Ignore cleanup errors
                    try:
                        asyncio.set_event_loop(None)
                    except Exception:
                        pass  # Ignore cleanup errors
            except Exception as e:
                exception = e

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=300)  # 5 minute timeout to prevent hanging

        if thread.is_alive():
            raise RuntimeError("Async operation timed out after 5 minutes")

        if exception:
            raise exception
        if result is None:
            raise RuntimeError("Failed to get result from async operation")
        return result

    def _run_with_manual_loop(
        self, coro_factory: Callable[[], Coroutine[Any, Any, T]]
    ) -> T:
        """Manually create and manage an event loop."""
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            fresh_coro = coro_factory()
            return loop.run_until_complete(fresh_coro)
        finally:
            if loop is not None:
                try:
                    loop.close()
                except Exception:
                    pass  # Ignore cleanup errors
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass  # Ignore cleanup errors
