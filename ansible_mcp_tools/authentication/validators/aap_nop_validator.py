from ansible_mcp_tools.authentication.protocols.validator import AuthenticationValidator

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


class AAPNopValidator(AuthenticationValidator):

    async def validate(
        self, connection: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:

        auth_user = AuthenticationUser(
            "nop",
            AuthenticationInfo(
                "nop",
                "nop",
                "nop",
                verify_cert=False,
            ),
        )
        # set user to context var
        auth_context_var.set(auth_user)
        return AuthCredentials(), auth_user
