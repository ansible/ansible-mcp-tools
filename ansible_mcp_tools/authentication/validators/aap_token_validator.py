from typing import override

from ansible_mcp_tools.authentication.validators.base_token_validator import BaseTokenValidator
from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
    AuthenticationInfo,
)

from starlette.authentication import AuthenticationError
class AAPTokenValidator(BaseTokenValidator):

    def __init__(self, authentication_server_url: str, verify_cert: bool = True):
        super().__init__(authentication_server_url, verify_cert)

    @override
    def get_auth_user(self, authentication_header_value, data):
        results = data.json()
        if len(results.get("results", [])) == 0:
            AuthenticationError("Authentication error, no user returned")

        auth_user = AuthenticationUser(
            results["results"][0]["username"],
            AuthenticationInfo(
                self.AUTHENTICATION_HEADER_NAME,
                authentication_header_value,
                self._authentication_server_url,
                verify_cert=self._verify_cert,
            ),
        )
        return auth_user
