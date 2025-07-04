# MCP Server for AAP Controller API v2.5

## Configuration options:

- `AAP_GATEWAY_URL`: AAP Gateway URL
- `AAP_SERVICE_URL`: AAP Controller URL
- `URL`: URL for OpenAPI Spec file. This should be `file://...` when bundled in the Container image.
- `HOST`: Host name for the MCP server, default `127.0.0.1`
- `PORT`: Host port for the MCP server, default `8004`

## Building the Container
```bash
make build-controller
```

## Running from Container

```bash
export AAP_GATEWAY_URL=<...>
export AAP_SERVICE_URL=<...>
make run-controller
```
