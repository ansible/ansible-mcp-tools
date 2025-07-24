from os import environ
from urllib.parse import urljoin

from mcp.server.fastmcp.utilities.logging import get_logger, configure_logging

from ansible_mcp_tools.service import AAPRegistry
from ansible_mcp_tools.server import MCPOpenAPIServer
from ansible_mcp_tools.openapi.spec_loaders import FileLoader

from ansible_mcp_tools.openapi.tool_rules import MethodRule, NoDescriptionRule

from ansible_mcp_tools.authentication import LightspeedAuthenticationBackend
from ansible_mcp_tools.authentication.validators.aap_token_validator import (
    AAPTokenValidator,
)


logger = get_logger(__name__)

configure_logging("DEBUG")

SERVICE_NAME="gateway"
AAP_GATEWAY_URL = environ.get("AAP_GATEWAY_URL")
URL = environ.get("OPENAPI_SPEC_URL")
HOST = environ.get("HOST", "127.0.0.1")
PORT = environ.get("PORT", 8003)

logger.info(f"AAP_GATEWAY_URL: {AAP_GATEWAY_URL}")
logger.info(f"OPENAPI_SPEC_URL: {URL}")
logger.info(f"HOST: {HOST}")
logger.info(f"PORT: {PORT}")

registry = AAPRegistry()

service = registry.get_targeted_service(SERVICE_NAME)
validation_url = urljoin(service.targeted_services_url[SERVICE_NAME],service.validation_uri)

mcp = MCPOpenAPIServer(
    name="AAP Gateway API 2.5 MCP Server",
    service_name=SERVICE_NAME,
    service=service,
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPTokenValidator(validation_url, verify_cert=False),
        ]
    ),
    spec_loader=registry.get_targeted_service(SERVICE_NAME).get_open_api_document_loader(),
    tool_rules=[
        MethodRule(["PUT", "OPTIONS", "DELETE", "PATCH", "POST"]),
        NoDescriptionRule(),
    ],
    host=HOST,
    port=PORT,
)

if __name__ == "__main__":
    mcp.run(transport="sse")
