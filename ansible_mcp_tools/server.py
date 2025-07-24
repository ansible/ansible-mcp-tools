import mcp.types as types

from ansible_mcp_tools.authentication.protocols.backend import AuthenticationBackend
from ansible_mcp_tools.authentication.middleware import (
    LightspeedAuthenticationMiddleware,
)
from ansible_mcp_tools.openapi.protocols.spec_loader import SpecLoader
from ansible_mcp_tools.openapi.protocols.tool_name_strategy import ToolNameStrategy
from ansible_mcp_tools.openapi.protocols.tool_rule import ToolRule

from ansible_mcp_tools.openapi.tool_parsers import DefaultToolParser
from ansible_mcp_tools.openapi.tool_callers import DefaultToolCaller
from ansible_mcp_tools.openapi.tool_name_strategies import DefaultToolNameStrategy
from collections.abc import Sequence
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
)
from starlette.applications import Starlette
from typing import Any, override
from ansible_mcp_tools.service import AAPService

logger = get_logger(__name__)


class MCPBaseServer(FastMCP):
    def __init__(
        self,
        name: str = "Lightspeed AAP MCP",
        auth_backend: AuthenticationBackend | None = None,
        **settings: Any,
    ):
        self._auth_backend = auth_backend
        super().__init__(name, **settings)

    def init_app_authentication_backend(self, app: Starlette):
        if isinstance(self._auth_backend, AuthenticationBackend):
            logger.debug(f">>>>>>>> {self.name} authentication backend")
            app.add_middleware(
                LightspeedAuthenticationMiddleware, backend=self._auth_backend
            )

    @override
    def sse_app(self, mount_path: str | None = None) -> Starlette:
        app = super().sse_app(mount_path=mount_path)
        self.init_app_authentication_backend(app)
        return app

    @override
    def streamable_http_app(self) -> Starlette:
        app = super().streamable_http_app()
        self.init_app_authentication_backend(app)
        return app


class MCPOpenAPIServer(MCPBaseServer):
    def __init__(
        self,
        name: str,
        service: AAPService,
        auth_backend: AuthenticationBackend | None,
        spec_loader: SpecLoader,
        tool_name_strategy: ToolNameStrategy | None = None,
        tool_rules: list[ToolRule] | None = None,
        **settings: Any,
    ):
        super().__init__(name, auth_backend, **settings)
        self._service = service
        _spec = spec_loader.load()
        _tool_name_strategy = (
            tool_name_strategy if tool_name_strategy else DefaultToolNameStrategy()
        )
        _tool_parser = DefaultToolParser(
            _spec, service.name, _tool_name_strategy, tool_rules=tool_rules
        )
        self._tools = _tool_parser.parse_tools()
        self._tool_caller = DefaultToolCaller(
            _spec, self._tools, self._service, _tool_name_strategy
        )

    @override
    async def list_tools(self) -> list[types.Tool]:
        return self._tools

    @override
    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        logger.warning(f"--> Tool call {name}, {arguments}")
        return await self._tool_caller.tool_call(name, arguments)
