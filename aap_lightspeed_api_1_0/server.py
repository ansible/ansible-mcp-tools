from os import environ

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.openapi.tool_rules import (
    MethodRule,
    OperationIdBlackRule,
    NoDescriptionRule,
)
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

logger.info(f"AAP_GATEWAY_URL: {AAP_GATEWAY_URL}")
logger.info(f"AAP_SERVICE_URL: {AAP_SERVICE_URL}")
logger.info(f"OPENAPI_SPEC_URL: {URL}")
logger.info(f"HOST: {HOST}")
logger.info(f"PORT: {PORT}")

register_service_url("gateway", AAP_GATEWAY_URL)
register_service_url("lightspeed", AAP_SERVICE_URL)

mcp = LightspeedOpenAPIAAPServer(
    name="AAP Lightspeed API 1.0 MCP Server",
    service_name="lightspeed",
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPJWTValidator(AAP_GATEWAY_URL, verify_cert=False),
            AAPTokenValidator(AAP_GATEWAY_URL, verify_cert=False),
        ]
    ),
    spec_loader=FileLoader(URL),
    tool_rules=[
        MethodRule(["PUT", "OPTIONS", "DELETE", "PATCH"]),
        OperationIdBlackRule(
            [
                "ai_chat_create",
                "ai_feedback_create",
                "telemetry_settings_set",
                "wca_api_key_set",
                "wca_model_id_set",
                "ai_completions_create",
            ]
        ),
        NoDescriptionRule(),
    ],
    host=HOST,
    port=PORT,
)

if __name__ == "__main__":
    mcp.run(transport="sse")
