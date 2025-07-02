# Ansible MCP servers

## Disclaimer

These are experimental MCP servers for Ansible services to support Ansible Lightspeed Intelligent Assistant.

They are not official Ansible MCP servers and are therefore subject to change or removal.

They require an instance of Ansible Automation Platform to fully operate.

Use at your own risk.

## Use Podman instead of Docker

If you use Podman as container runtime, just set

```bash
export CONTAINER_RUNTIME=podman
```

the default is `docker`
