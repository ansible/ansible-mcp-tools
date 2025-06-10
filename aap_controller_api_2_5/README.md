# MCP Server for AAP Controller API v2.5

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `AAP_SERVICE_URL`: AAP Controller URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8004`

## Building the Container
```commandline
docker build -f ./aap_controller_api_2_5/Containerfile -t ansible-mcp-controller .
```

## Running from Container

```commandline
export AAP_GATEWAY_URL=<...>
export AAP_SERVICE_URL=<...>
docker run \
  -p 8004:8004 \
  --env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
  --env AAP_SERVICE_URL=${AAP_SERVICE_URL} \
  --env HOST=0.0.0.0 \
  --env PORT=8004 \
  ansible-mcp-controller
```