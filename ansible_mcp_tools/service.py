from urllib.parse import urljoin
from mcp.server.fastmcp.utilities.logging import get_logger, configure_logging

from dataclasses import dataclass
from ansible_mcp_tools.base_registry import BaseRegistry
from ansible_mcp_tools.base_service import BaseService
from typing import override

AAP_JWT_HEADER_NAME = "X-DAB-JW-TOKEN"

logger = get_logger(__name__)

configure_logging("DEBUG")

@dataclass
class AAPService(BaseService):
    gateway_base_path: str
    service_base_path: str

    def __init__(self,name, targeted_service_url, open_api_document_url, service_base_path, validation_uri, gateway_base_path=None):
        super().__init__(name, targeted_service_url, open_api_document_url, validation_uri)
        self.gateway_base_path=gateway_base_path
        self.service_base_path=service_base_path

    @override
    def build_path(self, path: str) -> str:
        path = path.lstrip("/")
        return path.lstrip(self.gateway_base_path)
    
    def api_url_builder(self, path: str, **kwargs) -> str | None:
        logger.debug(f"self: {self}")
        path = self.build_path(path)
        base_url_path = self.get_aap_service_url_base_path_by_header_name(
            self.name, kwargs["header_name"]
        )
        logger.debug(f"base_url_path: {base_url_path}")
        if base_url_path is None:
            return None
        for text in ("api/", "/api/"):
            if path.startswith(text):
                path = path[len(text) :]
                break

        if path.startswith("/"):
            path = path[1:]

        return f"{base_url_path}/{path}"

    def get_aap_service_url_base_path_by_header_name(self, 
        service_name: str,auth_header_name: str
    ) -> str | None:
        if auth_header_name != AAP_JWT_HEADER_NAME and service_name != "controller24":
            return self.get_aap_service_url_base_path(service_name, context="gateway")
        return self.get_aap_service_url_base_path(service_name)

    def get_aap_service_url_base_path(self, service_name: str, context: str = None) -> str | None:
        logger.debug(f"context: {context}")
        service_url = self.targeted_services_url[service_name]
        if service_url is None:
            return None
        base_path = self.service_base_path
        if context == "gateway":
            service_url = self.targeted_services_url[context]
            base_path = self.gateway_base_path
        logger.debug(f"service_url: {service_url} base_path:{base_path}")
        return urljoin(service_url, base_path)
