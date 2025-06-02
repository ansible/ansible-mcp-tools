from os import environ

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.registry import register_service_url
from ansible_mcp_tools.registry import init as init_registry
from ansible_mcp_tools.server import LightspeedOpenAPIAAPServer

from ansible_mcp_tools.authentication import LightspeedAuthenticationBackend
from ansible_mcp_tools.authentication.validators.aap_nop_validator import (
    AAPNopValidator,
)
from mcp.server.fastmcp.utilities.logging import configure_logging


logger = get_logger(__name__)

configure_logging("DEBUG")

init_registry()

AAP_URL = environ.get("AAP_URL", "https://localhost")
register_service_url("gateway", AAP_URL)
register_service_url("controller", "https://localhost:8043")
register_service_url("lightspeed", "http://localhost:7080")


mcp = LightspeedOpenAPIAAPServer(
    name="AAP Controller API 2.5 MCP Server",
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPNopValidator()
            # AAPJWTValidator(AAP_URL, verify_cert=False),
            # AAPTokenValidator(AAP_URL, verify_cert=False),
        ]
    ),
    host="127.0.0.1",
    port=8003,
)

if __name__ == "__main__":
    mcp.run(transport="sse")
