# MCP Server for AAP Lightspeed API v1.0

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `AAP_SERVICE_URL`: AAP Lightspeed URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8005`

## Building the Container
```bash
make build-lightspeed
```

## Running from Container

```bash
export AAP_GATEWAY_URL=<...>
export AAP_SERVICE_URL=<...>
make run-lightspeed
```
