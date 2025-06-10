# MCP Server for AAP Gateway API v2.5

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8003`

## Building the Container
```commandline
docker build -f ./aap_gateway_api_2_5/Containerfile -t ansible-mcp-gateway .
```

## Running from Container

```commandline
export AAP_GATEWAY_URL=<...>
docker run \
  -p 8003:8003 \
  --env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
  --env HOST=0.0.0.0 \
  --env PORT=8003 \
  ansible-mcp-gateway
```