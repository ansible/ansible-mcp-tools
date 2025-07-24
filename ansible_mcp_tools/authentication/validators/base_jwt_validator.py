import httpx
from typing import override, Any
import jwt
import cachetools

from ansible_mcp_tools.authentication.protocols.validator import AuthenticationValidator
from urllib.parse import urljoin

from starlette.requests import HTTPConnection
from starlette.authentication import (
    AuthCredentials,
    AuthenticationError,
    BaseUser,
)

from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
    AuthenticationInfo,
)

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.authentication.context import auth_context_var

from ansible_mcp_tools.authentication.validators.base_validator import BaseValidator

logger = get_logger(__name__)

_cache = cachetools.TTLCache(maxsize=100, ttl=600)

class BaseJWTValidator(BaseValidator):
    AUTHENTICATION_HEADER_NAME = "X-DAB-JW-TOKEN"

    def __init__(self, authentication_server_url: str, verify_cert: bool = True):
        super().__init__(authentication_server_url,verify_cert)

    @override
    def get_auth_user(self, authentication_header_value: str, data: Any) -> AuthenticationUser: 
        username = data["user_data"]["username"]

        auth_user = AuthenticationUser(
            username,
            AuthenticationInfo(
                self.AUTHENTICATION_HEADER_NAME,
                authentication_header_value,
                self._authentication_server_url,
                verify_cert=self._verify_cert,
            ),
        )
        # set user to context var
        auth_context_var.set(auth_user)
        return auth_user
 
    @override
    async def _get_decryption_key(self) -> str:
        url = urljoin(self._authentication_server_url, "api/gateway/v1/jwt_key/")
        public_key = _cache.get(url)
        if public_key:
            return public_key
        logger.debug("calling authentication server at url: %s", url)
        async with httpx.AsyncClient(verify=self._verify_cert) as client:
            response = await client.get(url)
            if not response.is_success:
                raise AuthenticationError("failed to retrieve decryption key from AAP")
            public_key = response.text
            _cache[url] = public_key
            return public_key

    def decode_jwt_token(self, unencrypted_token, decryption_key):
        options = {"require": ["user_data", "exp"]}
        return jwt.decode(
            unencrypted_token,
            decryption_key,
            audience="ansible-services",
            options=options,
            issuer="ansible-issuer",
            algorithms=["RS256"],
        )

    async def validate(
        self, connection: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        authentication_header_value = connection.headers.get(
            self.AUTHENTICATION_HEADER_NAME, None
        )
        logger.debug(
            "header: %s >>>>> %s ",
            self.AUTHENTICATION_HEADER_NAME,
            authentication_header_value,
        )
        if authentication_header_value is None:
            return None
        try:
            decryption_key = await self._get_decryption_key()
        except Exception as exp:
            logger.error("failed to get the jwt public key: %s", exp)
            raise AuthenticationError("failed to get the jwt public key")

        try:
            jwt_token_data = self.decode_jwt_token(
                authentication_header_value, decryption_key
            )
        except Exception as exp:
            logger.error("failed to decode jwt token: %s", exp)
            raise AuthenticationError("failed to decode jwt token")

        auth_user = self.get_auth_user(authentication_header_value,jwt_token_data)
        # set user to context var
        auth_context_var.set(auth_user)
        return AuthCredentials(), auth_user

    
