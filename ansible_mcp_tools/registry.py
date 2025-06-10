from urllib.parse import urljoin

from dataclasses import dataclass


@dataclass
class AAPService:
    name: str
    gateway_base_path: str
    service_base_path: str


_hosts_registry: dict[str:str] = {}

_aap_services_registry: dict[str:AAPService] = {}


def register_service_url(name: str, service_url: str) -> None:
    _hosts_registry[name] = service_url


def get_service_url(name: str) -> str | None:
    return _hosts_registry.get(name, None)


def register_aap_service(service: AAPService) -> None:
    _aap_services_registry[service.name] = service


def get_aap_service(name: str) -> AAPService | None:
    return _aap_services_registry.get(name, None)


def register_aap_services():
    register_aap_service(
        AAPService(
            name="gateway",
            gateway_base_path="api/gateway",
            service_base_path="api/gateway",
        )
    )
    register_aap_service(
        AAPService(
            name="controller",
            gateway_base_path="api/controller",
            service_base_path="api",
        )
    )
    register_aap_service(
        AAPService(
            name="lightspeed",
            gateway_base_path="api/lightspeed",
            service_base_path="api",
        )
    )


def get_aap_service_url_base_path(service_name: str, context: str = None) -> str | None:
    service_url = get_service_url(service_name)
    if service_url is None:
        return None
    service = get_aap_service(service_name)
    if service is None:
        return None
    base_path = service.service_base_path
    if context == "gateway":
        service_url = get_service_url(context)
        base_path = service.gateway_base_path
    return urljoin(service_url, base_path)


def init():
    register_aap_services()
