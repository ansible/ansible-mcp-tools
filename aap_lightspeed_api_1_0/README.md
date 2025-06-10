# MCP Server for AAP Lightspeed API v1.0

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `AAP_SERVICE_URL`: AAP Lightspeed URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8005`

## Building the Container
```commandline
docker build -f ./aap_lightspeed_api_1_0/Containerfile -t ansible-mcp-lightspeed .
```

## Running from Container

```commandline
export AAP_GATEWAY_URL=<...>
export AAP_SERVICE_URL=<...>
docker run \
  -p 8005:8005 \
  --env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
  --env AAP_SERVICE_URL=${AAP_SERVICE_URL} \
  --env HOST=0.0.0.0 \
  --env PORT=8005 \
  ansible-mcp-lightspeed
```