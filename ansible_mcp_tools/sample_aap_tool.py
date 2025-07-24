import httpx

from ansible_mcp_tools.registry import AAPRegistry

from mcp.server.fastmcp.utilities.logging import get_logger

from ansible_mcp_tools.authentication.context import (
    auth_context_var,
    get_authentication_headers,
)

logger = get_logger(__name__)

registry = AAPRegistry()

async def fetch_current_user_data(context="lightspeed") -> str:
    """return the current logged-in AAP user information"""
    auth_user = auth_context_var.get()
    auth_headers = get_authentication_headers()
    registry = AAPRegistry()
    server_url_path = registry.get_aap_service_url_path(
        "controller", auth_user.authentication_info.header_name, "/v2/me/"
    )
    verify_cert = auth_user.authentication_info.verify_cert if auth_user else True

    async with httpx.AsyncClient(verify=verify_cert) as client:
        response = await client.get(server_url_path, headers=auth_headers)
        return response.text


async def fetch_aap_controller_jobs_list(
    order_by: str = "-finished", page: int = 1, page_size: int = 10
) -> str:
    """return the latest AAP controller jobs information"""
    auth_user = auth_context_var.get()
    auth_headers = get_authentication_headers()
    verify_cert = auth_user.authentication_info.verify_cert if auth_user else True
    server_url_path = registry.get_aap_service_url_path(
        "controller", auth_user.authentication_info.header_name, "/api/v2/jobs/"
    )
    async with httpx.AsyncClient(verify=verify_cert) as client:
        response = await client.get(
            server_url_path,
            headers=auth_headers,
            params={"order_by": order_by, "page": page, "page_size": page_size},
        )
        return response.text
