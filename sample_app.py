from os import environ

from ansible_mcp_tools.service import register_service_url
from ansible_mcp_tools.service import init as init_registry
from ansible_mcp_tools.server import MCPBaseServer

from ansible_mcp_tools.authentication import LightspeedAuthenticationBackend
from ansible_mcp_tools.authentication.validators.aap_token_validator import (
    AAPTokenValidator,
)
from ansible_mcp_tools.authentication.validators.aap_jwt_validator import (
    AAPJWTValidator,
)
from ansible_mcp_tools.sample_aap_tool import (
    fetch_current_user_data,
    fetch_aap_controller_jobs_list,
)

from mcp.server.fastmcp.utilities.logging import configure_logging


configure_logging("DEBUG")

init_registry()

AAP_URL = environ.get("AAP_URL", "https://localhost")
register_service_url("gateway", AAP_URL)
register_service_url("controller", "https://localhost:8043")
register_service_url("lightspeed", "http://localhost:7080")


mcp = MCPBaseServer(
    auth_backend=LightspeedAuthenticationBackend(
        authentication_validators=[
            AAPJWTValidator(AAP_URL, verify_cert=False),
            AAPTokenValidator(AAP_URL, verify_cert=False),
        ]
    ),
    host="127.0.0.1",
    port=3180,
)

mcp.add_tool(fetch_current_user_data)
mcp.add_tool(fetch_aap_controller_jobs_list)

if __name__ == "__main__":
    mcp.run(transport="sse")
