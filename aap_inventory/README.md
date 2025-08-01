# AI Installer Inventory MCP Server

## Install
```commandline
uv venv
source .venv/bin/activate
uv sync
```

## Execution
```commandline
cd aap_inventory
fastmcp run server.py --transport sse --port 20000
```

## Manual Test using MCP Inspector
```commandline
cd aap_inventory
fastmcp dev ./server.py
```

1. Set Transport Type to SSE
1. Set URL to http://127.0.0.1:20000/sse/
1. Click Connect
1. Switch to Tools tab
1. Click List Tools
1. Click get_template
1. Set platform to `containerized`
1. Set topology to `growth`
1. Set host to `localhost`
1. Click **Run Tool**