
from dataclasses import dataclass
from ansible_mcp_tools.base_service import BaseService

@dataclass
class BaseRegistry:
    targeted_services_registry: dict[str:BaseService]

    def __init__(self):
        self.targeted_services_registry = {}

    def register_targeted_service(self,service: BaseService) -> None:
        self.targeted_services_registry[service.name] = service

    def get_targeted_service(self,name: str) -> BaseService | None:
        return self.targeted_services_registry.get(name, None)
