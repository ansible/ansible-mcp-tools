# AI Installer Inventory MCP Server

## Install
```commandline
uv venv
source .venv/bin/activate
uv sync
```

## Execution
```commandline
PYTHONPATH=. uv run fastmcp run ai_installer_template/server.py --transport http --port 20000
```

## Manual Test using MCP Inspector
```commandline
uv run fastmcp dev ai_installer_template/server.py
```

1. Set Transport Type to Streamable HTTP
1. Set URL to http://127.0.0.1:20000/mcp/
1. Click Connect
1. Switch to Tools tab
1. Click List Tools
1. Click get_template
1. Set `container` to platform
1. Set `enterprise` to topology
1. Click **Run Tool**