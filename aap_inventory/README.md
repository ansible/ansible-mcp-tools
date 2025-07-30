# AI Installer Inventory MCP Server

## Install
In the project root directory, execute following commands:
```commandline
uv venv
source .venv/bin/activate
uv sync
```

## Execution
```commandline
cd aap_inventory
fastmcp run ./server.py --transport sse --port 20000
```

## Manual Test using MCP Inspector
```commandline
cd aap_inventory
uv run fastmcp dev ./server.py
```

1. Set Transport Type to Streamable SSE
1. Set URL to http://127.0.0.1:20000/sse/
1. Click Connect
1. Switch to Tools tab
1. Click List Tools
1. Click get_inventory
1. Set `containerized` to platform
1. Set `growth` to topology
1. Set 'localhost' to host
1. Click **Run Tool**