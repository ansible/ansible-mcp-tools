from os import environ

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.registry import register_service_url
from ansible_mcp_tools.registry import init as init_registry
from ansible_mcp_tools.server import LightspeedOpenAPIAAPServer
from ansible_mcp_tools.openapi.spec_loaders import FileLoader

from ansible_mcp_tools.authentication import LightspeedAuthenticationBackend
from ansible_mcp_tools.authentication.validators.aap_token_validator import (
    AAPTokenValidator,
)
from ansible_mcp_tools.authentication.validators.aap_jwt_validator import (
    AAPJWTValidator,
)
from mcp.server.fastmcp.utilities.logging import configure_logging


logger = get_logger(__name__)

configure_logging("DEBUG")

init_registry()

AAP_GATEWAY_URL = environ.get("AAP_GATEWAY_URL")
AAP_SERVICE_URL = environ.get("AAP_SERVICE_URL")
URL = environ.get("OPENAPI_SPEC_URL")
HOST = environ.get("HOST", "127.0.0.1")
PORT = environ.get("PORT", 8004)

register_service_url("gateway", AAP_GATEWAY_URL)
register_service_url("controller", AAP_SERVICE_URL)

mcp = LightspeedOpenAPIAAPServer(
    name="AAP Controller API 2.5 MCP Server",
    service_name="controller",
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPJWTValidator(AAP_GATEWAY_URL, verify_cert=False),
            AAPTokenValidator(AAP_GATEWAY_URL, verify_cert=False),
        ]
    ),
    spec_loader=FileLoader(URL),
    host=HOST,
    port=PORT,
)

if __name__ == "__main__":
    mcp.run(transport="sse")
