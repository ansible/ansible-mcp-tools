import httpx

import jwt

import cachetools

from urllib.parse import urljoin

from .aap_base_validator import AAPBaseValidator

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.authentication.auth_user import (
    AuthenticationUser,
    AuthenticationInfo,
)

from starlette.authentication import (
    AuthCredentials,
    AuthenticationError,
    BaseUser,
)

from starlette.requests import HTTPConnection

from ansible_mcp_tools.authentication.context import auth_context_var
from ansible_mcp_tools.authentication.validators.base_jwt_validator import BaseJWTValidator

logger = get_logger(__name__)


_cache = cachetools.TTLCache(maxsize=100, ttl=600)


class AAPJWTValidator(BaseJWTValidator):
    def __init__(self, authentication_server_url: str, verify_cert: bool = True):
        super().__init__(authentication_server_url, verify_cert)
