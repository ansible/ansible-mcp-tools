import os
import requests
import yaml
import json
import mcp.types as types
import re

from ansible_mcp_tools.authentication.protocols.backend import AuthenticationBackend
from ansible_mcp_tools.authentication.middleware import (
    LightspeedAuthenticationMiddleware,
)
from collections.abc import Sequence
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
)
from starlette.applications import Starlette
from typing import Any, Dict, Optional, List, Tuple, override

logger = get_logger(__name__)


class LightspeedBaseAAPServer(FastMCP):
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
            logger.debug(">>>>>>>> register lightspeed AAP authentication backend")
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


class LightspeedOpenAPIAAPServer(LightspeedBaseAAPServer):
    def __init__(
        self,
        name: str,
        auth_backend: AuthenticationBackend | None,
        **settings: Any,
    ):
        super().__init__(name, auth_backend, **settings)
        self.spec = self.load_openapi_spec()
        self.tools = self.parse_tools(self.spec)

    def load_openapi_spec(self) -> Optional[Dict]:
        openapi_url = os.getenv("OPENAPI_SPEC_URL")
        if not openapi_url:
            logger.critical(
                "OPENAPI_SPEC_URL environment variable is required but not set."
            )
            raise RuntimeError(
                "OPENAPI_SPEC_URL environment variable is required but not set."
            )
        load_openapi_spec = self.fetch_openapi_spec(openapi_url)
        if not load_openapi_spec:
            logger.critical(
                "Failed to fetch or parse OpenAPI specification from OPENAPI_SPEC_URL."
            )
            raise RuntimeError(
                "Failed to fetch or parse OpenAPI specification from OPENAPI_SPEC_URL."
            )
        logger.debug("OpenAPI specification fetched successfully.")
        return load_openapi_spec

    def fetch_openapi_spec(self, url: str, retries: int = 3) -> Optional[Dict]:
        logger.debug(f"Fetching OpenAPI spec from URL: {url}")
        attempt = 0
        while attempt < retries:
            try:
                if url.startswith("file://"):
                    with open(url[7:], "r") as f:
                        content = f.read()
                else:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    content = response.text
                logger.debug(f"Fetched content length: {len(content)} bytes")
                try:
                    spec = json.loads(content)
                    logger.debug(f"Parsed as JSON from {url}")
                except json.JSONDecodeError:
                    try:
                        spec = yaml.safe_load(content)
                        logger.debug(f"Parsed as YAML from {url}")
                    except yaml.YAMLError as ye:
                        logger.error(
                            f"YAML parsing failed: {ye}. Raw content: {content[:500]}..."
                        )
                        return None
                return spec
            except requests.RequestException as e:
                attempt += 1
                logger.warning(f"Fetch attempt {attempt}/{retries} failed: {e}")
                if attempt == retries:
                    logger.error(
                        f"Failed to fetch spec from {url} after {retries} attempts: {e}"
                    )
                    return None
        return None

    def parse_tools(self, spec: Dict) -> List[types.Tool]:
        """Register tools from OpenAPI spec, preserving across calls if already populated."""
        tools: List[types.Tool] = []
        logger.debug("Clearing previously registered tools to allow re-registration")
        tools.clear()
        if not spec:
            logger.error("OpenAPI spec is None or empty.")
            return tools
        if "paths" not in spec:
            logger.error("No 'paths' key in OpenAPI spec.")
            return tools
        logger.debug(f"Spec paths available: {list(spec['paths'].keys())}")
        filtered_paths = {
            path: item
            for path, item in spec["paths"].items()
            if self.is_tool_whitelisted(path)
        }
        logger.debug(f"Filtered paths: {list(filtered_paths.keys())}")
        if not filtered_paths:
            logger.warning(
                "No whitelisted paths found in OpenAPI spec after filtering."
            )
            return tools
        for path, path_item in filtered_paths.items():
            if not path_item:
                logger.debug(f"Empty path item for {path}")
                continue
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    logger.debug(f"Skipping unsupported method {method} for {path}")
                    continue
                try:
                    raw_name = f"{method.upper()} {path}"
                    function_name = self.normalize_tool_name(raw_name)
                    description = operation.get(
                        "summary",
                        operation.get("description", "No description available"),
                    )
                    input_schema = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    }
                    parameters = operation.get("parameters", [])
                    placeholder_params = [
                        part.strip("{}")
                        for part in path.split("/")
                        if "{" in part and "}" in part
                    ]
                    for param_name in placeholder_params:
                        param_name = self.anthropic_cleanse(param_name)
                        input_schema["properties"][param_name] = {
                            "type": "string",
                            "description": f"Path parameter {param_name}",
                        }
                        input_schema["required"].append(param_name)
                        logger.debug(
                            f"Added URI placeholder {param_name} to inputSchema for {function_name}"
                        )
                    for param in parameters:
                        param_name = param.get("name")
                        param_name = self.anthropic_cleanse(param_name)
                        param_in = param.get("in")
                        if param_in in ["path", "query"]:
                            param_type = param.get("schema", {}).get("type", "string")
                            schema_type = (
                                param_type
                                if param_type
                                in ["string", "integer", "boolean", "number"]
                                else "string"
                            )
                            input_schema["properties"][param_name] = {
                                "type": schema_type,
                                "description": param.get(
                                    "description", f"{param_in} parameter {param_name}"
                                ),
                            }
                            if (
                                param.get("required", False)
                                and param_name not in input_schema["required"]
                            ):
                                input_schema["required"].append(param_name)
                    tool = types.Tool(
                        name=function_name,
                        description=description,
                        inputSchema=input_schema,
                    )
                    tools.append(tool)
                    logger.debug(
                        f"Registered function: {function_name} ({method.upper()} {path}) with inputSchema: {json.dumps(input_schema)}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error registering function for {method.upper()} {path}: {e}",
                        exc_info=True,
                    )
        logger.debug(f"Registered {len(tools)} functions from OpenAPI spec.")
        return tools

    def normalize_tool_name(self, raw_name: str) -> str:
        """Convert an HTTP method and path into a normalized tool name."""
        try:
            method, path = raw_name.split(" ", 1)
            method = method.lower()

            path_name = ""
            path_parts = path.split("/")
            for path_part in path_parts:
                pp = path_part
                if pp:
                    if pp.startswith("{"):
                        pp = pp[1:]
                    if pp.endswith("}"):
                        pp = pp[:-1]
                    path_name = path_name + "_" + pp if path_name else pp

            if not path_parts:
                return "unknown_tool"

            name = f"{method}_{path_name}"
            name = self.anthropic_cleanse(name)
            return name

        except ValueError:
            logger.debug(f"Failed to normalize tool name: {raw_name}")
            return "unknown_tool"

    # [manstis] Hack for Anthropic that limits Tool names and Tool parameter names
    def anthropic_cleanse(self, name: str) -> str:
        name.replace(" ", "_")
        name = name.replace("{", "")
        name = name.replace("}", "")
        name = name.replace(",", "_")
        name = name[:63]
        pattern = r"^[a-zA-Z0-9_-]{1,64}$"  # Raw string for regex pattern
        match = re.search(pattern, name)
        if not match:
            x = 0
        return name

    def is_tool_whitelisted(self, endpoint: str) -> bool:
        """Check if an endpoint is allowed based on TOOL_WHITELIST."""
        whitelist = os.getenv("TOOL_WHITELIST")
        logger.debug(
            f"Checking whitelist - endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}"
        )
        if not whitelist:
            logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
            return True
        import re

        whitelist_entries = [entry.strip() for entry in whitelist.split(",")]
        for entry in whitelist_entries:
            if "{" in entry:
                # Build a regex pattern from the whitelist entry by replacing placeholders with a non-empty segment match ([^/]+)
                pattern = re.escape(entry)
                pattern = re.sub(r"\\\{[^\\\}]+\\\}", r"([^/]+)", pattern)
                pattern = "^" + pattern + "($|/.*)$"
                if re.match(pattern, endpoint):
                    logger.debug(
                        f"Endpoint {endpoint} matches whitelist entry {entry} using regex {pattern}"
                    )
                    return True
            else:
                if endpoint.startswith(entry):
                    logger.debug(f"Endpoint {endpoint} matches whitelist entry {entry}")
                    return True
        logger.debug(f"Endpoint {endpoint} not in whitelist - skipping.")
        return False

    async def dispatcher(self, name: str, arguments: dict) -> list[types.TextContent]:
        try:
            logger.debug(f"Dispatcher received CallToolRequest for function: {name}")
            logger.debug(
                f"API_KEY: {os.getenv('API_KEY', '<not set>')[:5] + '...' if os.getenv('API_KEY') else '<not set>'}"
            )
            logger.debug(f"STRIP_PARAM: {os.getenv('STRIP_PARAM', '<not set>')}")
            tool = next((tool for tool in self.tools if tool.name == name), None)
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
            headers = self.handle_auth(arguments)
            additional_headers = self.get_additional_headers()
            headers = {**headers, **additional_headers}
            parameters = dict(self.strip_parameters(arguments))
            method = operation_details["method"]
            if method != "GET":
                headers["Content-Type"] = "application/json"

            path = operation_details["path"]
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

            base_url = self.build_base_url()
            if not base_url:
                logger.critical(
                    "Failed to construct base URL from spec or SERVER_URL_OVERRIDE."
                )
                return [
                    types.TextContent(
                        type="text",
                        text="No base URL defined in spec or SERVER_URL_OVERRIDE",
                    )
                ]

            api_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
            request_params = {}
            request_body = None
            if isinstance(parameters, dict):
                merged_params = []
                path_item = self.spec.get("paths", {}).get(
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

            logger.debug(f"API Request - URL: {api_url}, Method: {method}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Query Params: {request_params}")
            logger.debug(f"Request Body: {request_body}")

            try:
                response = requests.request(
                    method=method,
                    url=api_url,
                    headers=headers,
                    params=request_params if method == "GET" else None,
                    json=request_body if method != "GET" else None,
                )
                response.raise_for_status()
                response_text = (response.text or "No response body").strip()
                content, log_message = self.detect_response_type(response_text)
                logger.debug(log_message)
                final_content = [content]
            except requests.exceptions.RequestException as e:
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
        if not self.spec or "paths" not in self.spec:
            return None
        for path, path_item in self.spec["paths"].items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                raw_name = f"{method.upper()} {path}"
                current_function_name = self.normalize_tool_name(raw_name)
                if current_function_name == function_name:
                    return {
                        "path": path,
                        "method": method.upper(),
                        "operation": operation,
                        "original_path": path,
                    }
        return None

    def get_additional_headers(self) -> Dict[str, str]:
        """Parse additional headers from EXTRA_HEADERS environment variable."""
        headers = {}
        extra_headers = os.getenv("EXTRA_HEADERS")
        if extra_headers:
            for line in extra_headers.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
        return headers

    def handle_auth(self, arguments: dict) -> Dict[str, str]:
        headers = {}
        api_key = (
            arguments["__token"] if "__token" in arguments else os.getenv("API_KEY")
        )
        auth_type = os.getenv("API_AUTH_TYPE", "Bearer").lower()
        if api_key:
            if auth_type == "bearer":
                logger.debug(f"Using API_KEY as Bearer: {api_key[:5]}...")
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_type == "basic":
                logger.debug(
                    "API_AUTH_TYPE is Basic, but Basic Auth not implemented yet."
                )
            elif auth_type == "api-key":
                key_name = os.getenv("API_AUTH_HEADER", "Authorization")
                headers[key_name] = api_key
                logger.debug(
                    f"Using API_KEY as API-Key in header {key_name}: {api_key[:5]}..."
                )
        return headers

    def strip_parameters(self, parameters: Dict) -> Dict:
        """Strip specified parameters from the input based on STRIP_PARAM."""
        strip_param = os.getenv("STRIP_PARAM")
        if not strip_param or not isinstance(parameters, dict):
            return parameters
        logger.debug(f"Raw parameters before stripping: {parameters}")
        result = parameters.copy()
        if strip_param in result:
            del result[strip_param]
        logger.debug(f"Parameters after stripping: {result}")
        return result

    def build_base_url(self) -> Optional[str]:
        """Construct the base URL from the OpenAPI spec or override."""
        override = os.getenv("SERVER_URL_OVERRIDE")
        if override:
            urls = [url.strip() for url in override.split(",")]
            for url in urls:
                if url.startswith("http://") or url.startswith("https://"):
                    logger.debug(
                        f"SERVER_URL_OVERRIDE set, using first valid URL: {url}"
                    )
                    return url
            logger.error(f"No valid URLs found in SERVER_URL_OVERRIDE: {override}")
            return None
        if "servers" in self.spec and self.spec["servers"]:
            return self.spec["servers"][0]["url"]
        elif "host" in self.spec and "schemes" in self.spec:
            scheme = self.spec["schemes"][0] if self.spec["schemes"] else "https"
            return f"{scheme}://{self.spec['host']}{self.spec.get('basePath', '')}"
        logger.error(
            "No servers or host/schemes defined in spec and no SERVER_URL_OVERRIDE."
        )
        return None

    def detect_response_type(self, response_text: str) -> Tuple[types.TextContent, str]:
        """Determine response type based on JSON validity.
        If response_text is valid JSON, return a wrapped JSON string;
        otherwise, return the plain text.
        """
        try:
            json.loads(response_text)
            wrapped_text = json.dumps({"text": response_text})
            return types.TextContent(type="text", text=wrapped_text), "JSON response"
        except json.JSONDecodeError:
            return (
                types.TextContent(type="text", text=response_text.strip()),
                "non-JSON text",
            )

    @override
    async def list_tools(self) -> list[types.Tool]:
        return self.tools

    @override
    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        logger.warning(f"--> Tool call {name}, {arguments}")
        return await self.dispatcher(name, arguments)
