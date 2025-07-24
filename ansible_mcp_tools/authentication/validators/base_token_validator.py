import httpx
from typing import override, Any

from ansible_mcp_tools.authentication.protocols.validator import AuthenticationValidator

from starlette.requests import HTTPConnection
from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
    AuthenticationInfo,
)

from starlette.authentication import (
    AuthCredentials,
    AuthenticationError,
    BaseUser,
)

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.authentication.context import auth_context_var

from ansible_mcp_tools.authentication.validators.base_validator import BaseValidator

logger = get_logger(__name__)

class BaseTokenValidator(BaseValidator):
    AUTHENTICATION_HEADER_NAME = "Authorization"

    def __init__(self, authentication_server_url: str, verify_cert: bool = True):
        super().__init__(authentication_server_url,verify_cert)

    @override
    def get_auth_user(self, authentication_header_value: str, data: Any) -> AuthenticationUser: 
        return AuthenticationUser(
            None,
            AuthenticationInfo(
                self.AUTHENTICATION_HEADER_NAME,
                authentication_header_value,
                self._authentication_server_url,
                verify_cert=self._verify_cert,
            ),
        )

    @override
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
        logger.debug("calling authentication server at url: %s", self._authentication_server_url)
        async with httpx.AsyncClient(verify=self._verify_cert) as client:
            response = await client.get(
                url=self._authentication_server_url,
                headers=dict(Authorization=authentication_header_value),
            )
            if not response.is_success:
                logger.error(
                    "Authentication error occurred: status: %s, body: %s ",
                    response.status_code,
                    response.text,
                )
                response = response.status_code
                raise AuthenticationError("Authentication error failed")

        auth_user = self.get_auth_user(authentication_header_value,response)
        # set user to context var
        auth_context_var.set(auth_user)
        return AuthCredentials(), auth_user
