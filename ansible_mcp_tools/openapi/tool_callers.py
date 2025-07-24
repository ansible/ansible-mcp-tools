import httpx
import json
import mcp.types as types

from abc import ABC
from os import environ
from typing import Dict, List, override

from ansible_mcp_tools.service import BaseService
from ansible_mcp_tools.openapi.protocols.tool_caller import ToolCaller
from ansible_mcp_tools.openapi.protocols.tool_name_strategy import ToolNameStrategy
from ansible_mcp_tools.authentication.context import (
    auth_context_var,
    get_authentication_headers,
)
from ansible_mcp_tools import utils

from mcp.server.fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


class BaseToolCaller(ToolCaller, ABC):
    def __init__(
        self,
        spec: Dict,
        tools: List[types.Tool],
        service_name: str,
        tool_name_strategy: ToolNameStrategy,
    ):
        self._spec = spec
        self._tools = tools
        self._service_name = service_name
        self._tool_name_strategy = tool_name_strategy

class DefaultToolCaller(BaseToolCaller):
    def __init__(
        self,
        spec: Dict,
        tools: List[types.Tool],
        service: BaseService,
        tool_name_strategy: ToolNameStrategy,
    ):
        super().__init__(spec, tools, service.name, tool_name_strategy)
        self._service = service

    @override
    async def tool_call(self, name: str, arguments: dict) -> list[types.TextContent]:
        try:
            logger.debug(f"ToolCaller received CallToolRequest for function: {name}")
            logger.debug(f"STRIP_PARAM: {environ.get('STRIP_PARAM', '<not set>')}")
            tool = next((tool for tool in self._tools if tool.name == name), None)
            if not tool:
                logger.error(f"Unknown function requested: {name}")
                return [
                    types.TextContent(type="text", text="Unknown function requested")
                ]
            logger.debug(f"Raw arguments before processing: {arguments}")

            operation_details = self.lookup_operation_details(name)
            if not operation_details:
                logger.error(f"Could not find OpenAPI operation for function: {name}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Could not find OpenAPI operation for function: {name}",
                    )
                ]

            operation = operation_details["operation"]
            operation["method"] = operation_details["method"]
            method = operation_details["method"]
            path = operation_details["path"]

            # llama-stack adds a 'session_id' parameter to all calls
            # This leads to remote API invocations failing due to the additional parameter
            # Therefore remove 'session_id' from the arguments dictionary
            parameters = arguments.copy()

            if "session_id" in parameters:
                del parameters["session_id"]

            try:
                path = path.format(**parameters)
                logger.debug(f"Substituted path using format(): {path}")
                if method == "GET":
                    placeholder_keys = [
                        seg.strip("{}")
                        for seg in operation_details["original_path"].split("/")
                        if seg.startswith("{") and seg.endswith("}")
                    ]
                    for key in placeholder_keys:
                        parameters.pop(key, None)
            except KeyError as e:
                logger.error(f"Missing parameter for substitution: {e}")
                return [types.TextContent(type="text", text=f"Missing parameter: {e}")]

            request_params = {}
            request_body = None
            if isinstance(parameters, dict):
                merged_params = []
                path_item = self._spec.get("paths", {}).get(
                    operation_details["original_path"], {}
                )
                if isinstance(path_item, dict) and "parameters" in path_item:
                    merged_params.extend(path_item["parameters"])
                if "parameters" in operation:
                    merged_params.extend(operation["parameters"])
                path_params_in_openapi = [
                    param["name"]
                    for param in merged_params
                    if param.get("in") == "path"
                ]
                if path_params_in_openapi:
                    missing_required = [
                        param["name"]
                        for param in merged_params
                        if param.get("in") == "path"
                        and param.get("required", False)
                        and param["name"] not in arguments
                    ]
                    if missing_required:
                        logger.error(
                            f"Missing required path parameters: {missing_required}"
                        )
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Missing required path parameters: {missing_required}",
                            )
                        ]
                if method == "GET":
                    request_params = parameters
                else:
                    request_body = parameters
            else:
                logger.debug(
                    "No valid parameters provided, proceeding without params/body"
                )

            # Look-up and construct applicable URL
 
            auth_user = auth_context_var.get()

            headers = get_authentication_headers()
            verify_cert = (
                auth_user.authentication_info.verify_cert if auth_user else True
            )

            api_url =  self._service.api_url_builder(path, header_name=auth_user.authentication_info.header_name)

            if method != "GET":
                headers["Content-Type"] = "application/json"

            logger.debug(f"API Request - URL: {api_url}, Method: {method}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Query Params: {request_params}")
            logger.debug(f"Request Body: {request_body}")

            try:
                async with httpx.AsyncClient(verify=verify_cert) as client:
                    response = await client.request(
                        method=method,
                        url=api_url,
                        headers=headers,
                        params=request_params if method == "GET" else None,
                        json=request_body if method != "GET" else None,
                    )
                    response.raise_for_status()
                    response_text = (response.text or "No response body").strip()
                    content = self.format_response(response_text)
                    final_content = [content]

            except httpx.RequestError as e:
                logger.error(f"API request failed: {e}")
                return [types.TextContent(type="text", text=str(e))]

            logger.debug(f"Response content type: {content.type}")
            logger.debug(f"Response sent to client: {content.text}")

            return final_content

        except Exception as e:
            logger.error(
                f"Unhandled exception in dispatcher_handler: {e}", exc_info=True
            )
            return [types.TextContent(type="text", text=f"Internal error: {str(e)}")]

    def lookup_operation_details(self, function_name: str) -> Dict or None:
        if not self._spec or "paths" not in self._spec:
            return None
        for path, path_item in self._spec["paths"].items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                raw_name = f"{self._service_name}_{method.upper()} {path}"
                operation_id = operation.get("operationId", "")
                current_function_name = utils.get_tool_name_from_operation_id(
                    operation_id, raw_name, self._tool_name_strategy.normalize_tool_name
                )
                if current_function_name == function_name:
                    return {
                        "path": path,
                        "method": method.upper(),
                        "operation": operation,
                        "original_path": path,
                    }
        return None

    def format_response(self, response_text: str) -> types.TextContent:
        """Determine response type based on JSON validity.
        If response_text is valid JSON, return a wrapped JSON string;
        otherwise, return the plain text.
        """
        try:
            json.loads(response_text)
            wrapped_text = json.dumps({"text": response_text})
            logger.debug("JSON response")
            return types.TextContent(type="text", text=wrapped_text)
        except json.JSONDecodeError:
            logger.debug("Non-JSON text")
            return types.TextContent(type="text", text=response_text.strip())
