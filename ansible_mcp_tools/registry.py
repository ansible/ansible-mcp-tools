from os import environ

from dataclasses import dataclass
from ansible_mcp_tools.base_registry import BaseRegistry
from ansible_mcp_tools.service import AAPService

@dataclass
class AAPRegistry(BaseRegistry):
    def __init__(self):
        super().__init__()
        self.register_aap_services()

    def register_aap_services(self):
        self.register_targeted_service(
            AAPService(
                name="gateway",
                gateway_base_path="api/gateway",
                service_base_path="api/gateway",
                targeted_service_url={"gateway":environ.get("AAP_GATEWAY_URL")},
                open_api_document_url=environ.get("OPENAPI_SPEC_URL"),
                validation_uri="api/gateway/v1/me/"
            )
        )
        self.register_targeted_service(
            AAPService(
                name="controller24",
                service_base_path="api",
                targeted_service_url={"controller24":environ.get("AAP_SERVICE_URL")},
                open_api_document_url=environ.get("OPENAPI_SPEC_URL"),
                validation_uri="api/v2/me/"
            )
        )
        self.register_targeted_service(
            AAPService(
                name="controller",
                gateway_base_path="api/controller",
                service_base_path="api",
                targeted_service_url={"gateway":environ.get("AAP_GATEWAY_URL"),
                                    "controller":environ.get("AAP_SERVICE_URL")},
                open_api_document_url=environ.get("OPENAPI_SPEC_URL"),
                validation_uri="api/gateway/v1/me/"
            )
        )
        self.register_targeted_service(
            AAPService(
                name="lightspeed",
                gateway_base_path="api/lightspeed",
                service_base_path="api",
                targeted_service_url={"gateway":environ.get("AAP_GATEWAY_URL"),
                                    "controller":environ.get("AAP_SERVICE_URL")},
                open_api_document_url=environ.get("OPENAPI_SPEC_URL"),
                validation_uri="api/gateway/v1/me/"
            )
        )
