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
from mcp.server.fastmcp.utilities.logging import configure_logging


logger = get_logger(__name__)

configure_logging("DEBUG")

init_registry()

AAP_GATEWAY_URL = environ.get("AAP_GATEWAY_URL")
URL = environ.get("OPENAPI_SPEC_URL")
HOST = environ.get("HOST", "127.0.0.1")
PORT = environ.get("PORT", 8003)

logger.info(f"AAP_GATEWAY_URL: {AAP_GATEWAY_URL}")
logger.info(f"OPENAPI_SPEC_URL: {URL}")
logger.info(f"HOST: {HOST}")
logger.info(f"PORT: {PORT}")

register_service_url("gateway", AAP_GATEWAY_URL)

mcp = LightspeedOpenAPIAAPServer(
    name="AAP Gateway API 2.5 MCP Server",
    service_name="gateway",
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPTokenValidator(AAP_GATEWAY_URL, verify_cert=False),
        ]
    ),
    spec_loader=FileLoader(URL),
    host=HOST,
    port=PORT,
)

if __name__ == "__main__":
    mcp.run(transport="sse")
