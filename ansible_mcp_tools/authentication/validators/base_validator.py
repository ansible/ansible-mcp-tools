from typing import Any
from abc import ABC, abstractmethod
from ansible_mcp_tools.authentication.protocols.validator import AuthenticationValidator

from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
)

from starlette.requests import HTTPConnection
from starlette.authentication import (
    AuthCredentials,
    BaseUser,
)

from mcp.server.fastmcp.utilities.logging import get_logger


logger = get_logger(__name__)

class BaseValidator(AuthenticationValidator, ABC):
    AUTHENTICATION_HEADER_NAME: str

    def __init__(self, authentication_server_url: str, verify_cert: bool = True):
        self._authentication_server_url = authentication_server_url
        self._verify_cert = verify_cert

    @abstractmethod
    def get_auth_user(self, authentication_header_value: str, data: Any) -> AuthenticationUser: 
        return None

    @abstractmethod
    async def validate(
        self, connection: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        return None
