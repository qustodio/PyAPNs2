import ssl
import time

import httpx
import jwt

DEFAULT_TOKEN_LIFETIME = 2700
DEFAULT_TOKEN_ENCRYPTION_ALGORITHM = "ES256"


# Abstract Base class. This should not be instantiated directly.
class Credentials(object):
    def __init__(self, ssl_context: ssl.SSLContext | None = None) -> None:
        super().__init__()
        self.__ssl_context = ssl_context

    # Creates a connection with the credentials, if available or necessary.
    def create_connection(
        self,
        server: str,
        port: int,
        proto: str | None,
        proxy_host: str | None = None,
        proxy_port: int | None = None,
    ) -> httpx.AsyncClient:
        proxies = None
        if proxy_host and proxy_port:
            proxies = f"http://{proxy_host}:{proxy_port}"

        return httpx.AsyncClient(
            http2=True,
            verify=self.__ssl_context if self.__ssl_context else True,
            proxy=proxies,
            # Optimized settings for APNs batch processing
            limits=httpx.Limits(
                max_keepalive_connections=1000,
                max_connections=1500,
                keepalive_expiry=600,
            ),
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=60.0),
        )

    def get_authorization_header(self, topic: str | None) -> str | None:
        return None


# Credentials subclass for certificate authentication
class CertificateCredentials(Credentials):
    def __init__(
        self,
        cert_file: str | None = None,
        password: str | None = None,
        cert_chain: str | None = None,
    ) -> None:
        ssl_context = ssl.create_default_context()
        if cert_file:
            ssl_context.load_cert_chain(cert_file, password=password)
        if cert_chain:
            ssl_context.load_cert_chain(cert_chain)
        super(CertificateCredentials, self).__init__(ssl_context)


# Credentials subclass for JWT token based authentication
class TokenCredentials(Credentials):
    def __init__(
        self,
        auth_key_path: str,
        auth_key_id: str,
        team_id: str,
        encryption_algorithm: str = DEFAULT_TOKEN_ENCRYPTION_ALGORITHM,
        token_lifetime: int = DEFAULT_TOKEN_LIFETIME,
    ) -> None:
        self.__auth_key = self._get_signing_key(auth_key_path)
        self.__auth_key_id = auth_key_id
        self.__team_id = team_id
        self.__encryption_algorithm = encryption_algorithm
        self.__token_lifetime = token_lifetime

        self.__jwt_token: tuple[float, str] | None = None

        # Use the default constructor because we don't have an SSL context
        super(TokenCredentials, self).__init__()

    def get_authorization_header(self, topic: str | None) -> str:
        token = self._get_or_create_topic_token()
        return "bearer %s" % token

    def _is_expired_token(self, issue_date: float) -> bool:
        return time.time() > issue_date + self.__token_lifetime

    @staticmethod
    def _get_signing_key(key_path: str) -> str:
        secret = ""
        if key_path:
            with open(key_path) as f:
                secret = f.read()
        return secret

    def _get_or_create_topic_token(self) -> str:
        # dict of topic to issue date and JWT token
        token_pair = self.__jwt_token
        if token_pair is None or self._is_expired_token(token_pair[0]):
            # Create a new token
            issued_at = time.time()
            token_dict = {
                "iss": self.__team_id,
                "iat": issued_at,
            }
            headers = {
                "alg": self.__encryption_algorithm,
                "kid": self.__auth_key_id,
            }
            jwt_token = str(
                jwt.encode(
                    token_dict,
                    self.__auth_key,
                    algorithm=self.__encryption_algorithm,
                    headers=headers,
                )
            )

            # Cache JWT token for later use. One JWT token per connection.
            # https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/establishing_a_token-based_connection_to_apns
            self.__jwt_token = (issued_at, jwt_token)
            return jwt_token
        else:
            return token_pair[1]
