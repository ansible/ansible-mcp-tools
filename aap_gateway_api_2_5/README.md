# MCP Server for AAP Gateway API v2.5

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8003`

## Building the Container
```bash
make build-gateway
```

## Running from Container

```bash
export AAP_GATEWAY_URL=<...>
make run-gateway
```
