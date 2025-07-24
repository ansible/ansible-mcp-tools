from typing import override, Any

from ansible_mcp_tools.authentication.validators.base_validator import BaseValidator

from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
    AuthenticationInfo,
)

from starlette.requests import HTTPConnection
from starlette.authentication import (
    AuthCredentials,
    BaseUser,
)

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.authentication.context import auth_context_var

logger = get_logger(__name__)


class BaseNopValidator(BaseValidator):

    @override
    def get_auth_user(self, authentication_header_value: str, data: Any) -> AuthenticationUser: 
        return AuthenticationUser(
            "nop",
            AuthenticationInfo(
                "nop",
                authentication_header_value,
                "nop",
                verify_cert=False,
            ),
        )

    @override
    async def validate(
        self, connection: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        auth_user = self.get_auth_user(self,"nop",None)
        # set user to context var
        auth_context_var.set(auth_user)
        return AuthCredentials(), auth_user
