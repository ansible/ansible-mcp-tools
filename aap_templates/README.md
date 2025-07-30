# Ansible MCP Playbook Server

A FastMCP-based server that integrates with Ansible AWX/Controller to provide MCP tools for managing and launching job templates.

## Features

- **🔧 Dynamic Tool Generation**: Automatically discovers Ansible job templates and creates dedicated MCP tools for each one
  - Each job template becomes a unique MCP tool (e.g., `launch_deploy_production_app`)
  - No need to remember template IDs - tools are named after the templates
  - Templates are discovered at server startup and recreated on refresh
- **🔐 Bearer Token Authentication**: Secure authentication with Ansible AWX/Controller using bearer tokens
- **📋 Comprehensive Job Management**: Launch templates, monitor job status, retrieve logs, and manage execution
- **📄 Log Retrieval**: Access stdout logs from completed or running jobs for debugging and monitoring
- **⚡ Intelligent Caching**: 5-minute TTL caching of job templates for optimal performance
- **🌐 Multiple Transport Protocols**: Support for STDIO, HTTP, and SSE transports
- **📐 AAP Version Compatibility**: Automatic API path selection based on Ansible Automation Platform version
- **🔄 Hot Reload**: Refresh templates and recreate tools without restarting the server
- **⚙️ Environment Configuration**: Flexible configuration via environment variables

## Available Tools

The server provides both static management tools and dynamic job template tools:

### Static Management Tools

1. **`list_job_templates`** - List all available Ansible job templates with their details
2. **`launch_job_template`** - Launch a specific job template by ID with optional extra variables
3. **`get_job_status`** - Check the status of a running or completed job
4. **`get_job_logs`** - Retrieve the stdout logs of a specific job
5. **`refresh_job_templates`** - Force refresh the job templates cache (⚠️ does not recreate dynamic tools)

### Dynamic Job Template Tools

For each job template discovered in your Ansible instance, the server automatically creates a dedicated MCP tool during startup:

- **Tool naming pattern**: `launch_{template_name}` (with spaces and special characters converted to underscores)
- **Direct launching**: Each tool directly launches its specific job template
- **Template-specific**: No need to specify template ID - each tool knows which template to launch
- **Extra variables**: All dynamic tools accept an optional `extra_vars` JSON string parameter
- **Survey integration**: Tools include survey questions in their documentation when available

**Examples:**
- Job template "Deploy Production App" → Tool: `launch_deploy_production_app`
- Job template "Database Backup" → Tool: `launch_database_backup`  
- Job template "Server Maintenance" → Tool: `launch_server_maintenance`

⚠️ **Important**: Dynamic tools are created only during server initialization. If you add new job templates to Ansible, restart the MCP server to register the new tools.

The `list_job_templates` tool shows the `mcp_tool_name` for each template, making it easy to discover the available dynamic tools.

## Transport Options

The server supports multiple transport protocols:

### STDIO (Default)
- **Use case**: Desktop clients like Claude Desktop, local command-line tools
- **Configuration**: `MCP_TRANSPORT=stdio` (default)
- **Access**: Server runs as subprocess, communicates via stdin/stdout
- **Best for**: Local integrations, development, desktop applications

### HTTP
- **Use case**: Web deployments, network access, microservices
- **Configuration**: `MCP_TRANSPORT=http`
- **Access**: Server runs as HTTP service on `http://{MCP_HOST}:{MCP_PORT}/mcp`
- **Best for**: Production deployments, web applications, remote access

### SSE (Legacy)
- **Use case**: Existing deployments using Server-Sent Events
- **Configuration**: `MCP_TRANSPORT=sse`
- **Access**: Server runs with SSE on `http://{MCP_HOST}:{MCP_PORT}/sse`
- **Note**: Deprecated, use HTTP for new deployments

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANSIBLE_BASE_URL` | Base URL of your Ansible AWX/Controller instance | - | ✅ |
| `ANSIBLE_TOKEN` | Bearer token for authentication | - | ✅ |
| `AAP_VERSION` | Ansible Automation Platform version (`2.4` uses `/api`, others use `/api/controller`) |  | ❌ |
| `MCP_TRANSPORT` | Transport protocol: `stdio`, `http`, or `sse` | `stdio` | ❌ |
| `MCP_HOST` | Host to bind the MCP server to (http/sse only) | `0.0.0.0` | ❌ |
| `MCP_PORT` | Port to bind the MCP server to (http/sse only) | `8200` | ❌ |

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script
./setup.sh
```

### Option 2: Manual Setup

1. **Install Dependencies**
   ```bash
   # Using uv (recommended)
   make install
   
   # Or manually with uv
   uv sync
   ```

2. **Setup Environment**
   ```bash
   # Create .env file from template
   make setup-env
   
   # Edit .env with your Ansible details
   nano .env  # or your preferred editor
   ```

3. **Run the Server**
   ```bash
   # Run with startup script (recommended)
   make start
   
   # Or run directly
   make run
   ```

## Detailed Setup

### Manual Setup

1. **Install Dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   
   Create a `.env` file or set environment variables:
   ```bash
   export ANSIBLE_BASE_URL="https://your-ansible-instance.com"
   export ANSIBLE_TOKEN="your-bearer-token-here"
   export AAP_VERSION="2.4"      # Optional: AAP version (2.4 or other, default "" and so it will use /api/controller uri prefix to reach the controler)
   export MCP_TRANSPORT="sse"  # Optional: stdio, http, or sse
   export MCP_HOST="0.0.0.0"     # Optional (for http/sse only)
   export MCP_PORT="8200"        # Optional (for http/sse only)
   ```

3. **Run the Server**
   ```bash
   # Using uv (recommended)
   uv run python server.py
   
   # Or using python directly
   python server.py
   ```

### Using Make Commands

The project includes a Makefile for easy management:

```bash
# Show available commands
make help

# Install dependencies with uv
make install

# Setup environment file
make setup-env

# Start server (recommended)
make start

# Development mode
make dev

# Check environment configuration
make check-env

# Clean cache files
make clean

# UV-specific commands
make uv-sync      # Sync dependencies
make uv-sync-dev  # Sync with dev dependencies
make uv-add       # Show how to add dependencies
make uv-add-dev   # Show how to add dev dependencies
```

## Getting Your Ansible Bearer Token

To get a bearer token from Ansible AWX/Controller:

1. **Via Web UI**:
   - Navigate to your Ansible AWX/Controller web interface
   - Go to **Users** → Select your user → **Tokens**
   - Create a new token with appropriate scopes

2. **Via API**:
   ```bash
   curl -X POST https://your-ansible-instance.com/api/v2/tokens/ \
        -H "Content-Type: application/json" \
        -u username:password \
        -d '{"description": "MCP Server Token", "application": null, "scope": "read write"}'
   ```

## Usage Examples

### List Available Job Templates
```python
# The MCP client will call this tool
templates = await list_job_templates()
```

### Launch a Job Template

**Using Generic Tool (by ID):**
```python
# Launch with no extra variables
result = await launch_job_template(template_id=123)

# Launch with extra variables
result = await launch_job_template(
    template_id=123, 
    extra_vars='{"environment": "production", "debug": false}'
)
```

**Using Dynamic Template-Specific Tools:**
```python
# First, list templates to see available dynamic tools
templates = await list_job_templates()
for template in templates:
    print(f"Template: {template['name']} → Tool: {template['mcp_tool_name']}")

# Launch specific job templates directly (assuming these templates exist)
deploy_result = await launch_deploy_production_app(
    extra_vars='{"environment": "production", "version": "v2.1.0"}'
)

backup_result = await launch_database_backup()

maintenance_result = await launch_server_maintenance(
    extra_vars='{"maintenance_window": "2024-01-15T02:00:00Z"}'
)
```

### Extra Variables Format

The `extra_vars` parameter must be a valid JSON string. Here are examples of correct formats:

**✅ Correct JSON formats:**
```python
# Simple key-value pairs
extra_vars='{"key": "value", "number": 42, "boolean": true}'

# Nested objects
extra_vars='{"config": {"environment": "prod", "debug": false}}'

# Arrays
extra_vars='{"servers": ["server1", "server2"], "ports": [80, 443]}'

# Survey answers (for templates with surveys)
extra_vars='{"subscription_id": "sub-123", "region": "us-east-1"}'
```

**❌ Common mistakes to avoid:**
```python
# Don't use JavaScript object notation
extra_vars='{key: "value"}'  # Missing quotes around keys

# Don't use single quotes for JSON strings
extra_vars='{'key': 'value'}'  # Single quotes not valid in JSON

# Don't pass Python dictionaries directly
extra_vars={"key": "value"}  # Must be a string, not a dict

# Don't use malformed JSON from JavaScript
extra_vars='[object Object]{"key": "value"}'  # Invalid prefix
```

**💡 Tips:**
- Always use double quotes for JSON strings
- Escape any quotes within string values
- Use `json.dumps()` in Python to convert dictionaries to JSON strings
- The server will automatically clean up common malformations like `[object Object]` prefixes

### Check Job Status
```python
status = await get_job_status(job_id=456)
```

### Get Job Logs
```python
# Get the stdout logs of a completed job
logs = await get_job_logs(job_id=456)
print(f"Job: {logs['job_name']}")
print(f"Status: {logs['job_status']}")
print(f"Log lines: {logs['log_lines']}")
print("Logs:")
print(logs['stdout_content'])
```

## API Integration

The server integrates with Ansible AWX/Controller API endpoints. The API path prefix depends on your AAP version:

### AAP Version 2.4:
- **GET** `/api/v2/job_templates/` - Fetch available job templates
- **GET** `/api/v2/job_templates/{id}/survey_spec/` - Fetch survey specifications
- **POST** `/api/v2/job_templates/{id}/launch/` - Launch a job template
- **GET** `/api/v2/jobs/{id}/` - Get job status and details
- **GET** `/api/v2/jobs/{id}/stdout/` - Get job stdout logs

### AAP Version ≠ 2.4:
- **GET** `/api/controller/v2/job_templates/` - Fetch available job templates
- **GET** `/api/controller/v2/job_templates/{id}/survey_spec/` - Fetch survey specifications
- **POST** `/api/controller/v2/job_templates/{id}/launch/` - Launch a job template
- **GET** `/api/controller/v2/jobs/{id}/` - Get job status and details
- **GET** `/api/controller/v2/jobs/{id}/stdout/` - Get job stdout logs

The server automatically selects the correct API prefix based on the `AAP_VERSION` environment variable.

## Pagination

The server automatically handles API pagination to fetch all job templates:
- **Page Size**: Uses 200 templates per page by default (configurable)
- **Auto-fetching**: Continues fetching until all pages are retrieved
- **Progress Logging**: Shows pagination progress in server logs
- **Error Resilience**: Handles partial failures gracefully

## Caching

Job templates are cached for 5 minutes (300 seconds) by default to improve performance. The cache is automatically refreshed when:
- The server starts up
- The cache expires
- The `refresh_job_templates` tool is called (cache only - see limitations below)

### Refresh Limitations

⚠️ **Important**: The `refresh_job_templates` tool only refreshes the template cache, not the dynamic MCP tools themselves. Due to FastMCP's architecture, dynamic tools can only be registered during server initialization.

- **Cache Refresh**: ✅ Updates the template data used by `list_job_templates`
- **Tool Registration**: ❌ Cannot create new MCP tools for new templates
- **Recommendation**: Restart the MCP server to register tools for newly created templates

## Error Handling

The server includes comprehensive error handling for:
- Authentication failures
- Network connectivity issues
- Invalid job template IDs
- Malformed extra variables JSON
- API rate limiting

## Development

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) - install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Access to an Ansible AWX/Controller instance
- Valid authentication token

### Running in Development
```bash
# Install development dependencies with uv
uv sync --dev

# Set environment variables
export ANSIBLE_BASE_URL="https://your-dev-ansible-instance.com"
export ANSIBLE_TOKEN="your-dev-token"

# Run the server
uv run python server.py
```

### Testing
The server will attempt to connect to your Ansible instance on startup and cache available job templates. Check the logs for any connectivity or authentication issues.

## Logging

The server uses Python's standard logging module. Logs include:
- Server startup and configuration
- API requests and responses
- Cache operations
- Error details

## Security Considerations

- Store bearer tokens securely (use environment variables, not hardcoded values)
- Use HTTPS for your Ansible AWX/Controller instance
- Consider network access controls for the MCP server
- Regularly rotate authentication tokens

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Verify `ANSIBLE_TOKEN` is correct and not expired
   - Check token has appropriate permissions

2. **Connection Error**
   - Verify `ANSIBLE_BASE_URL` is accessible
   - Check network connectivity and firewall rules
   - Ensure HTTPS certificate is valid

3. **No Job Templates Found**
   - Verify your user has permission to view job templates
   - Check if any job templates exist in your Ansible instance

4. **Server Won't Start**
   - Ensure required environment variables are set
   - Check if port is already in use
   - Verify Python dependencies are installed with `uv sync`

### Debug Mode

For additional debugging, you can modify the logging level in `server.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Adding Dependencies

To add new dependencies to the project:

```bash
# Add a production dependency
uv add requests

# Add a development dependency
uv add --dev pytest

# Sync after adding dependencies
uv sync
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details. 

## Template Seeding

You can seed your AAP instance with some templates in order to test the mcp server.

### Environment variables:

- ANSIBLE_BASE_URL: The base url, for example if you use aap-dev 2.5-next then it is http://localhost:44925
- GATEWAY_USERNAME: Default `admin`
- GATEWAY_PASSWORD: Gateway password
- GITHUB_USER: Your gihub user, it is needed to download the SCM which is in fact this project or a clone of it.
- GITHUB_SSH_KEY: Your `base64 encoded` Github SSH key with no passphrase (read: [Generate SSH KEY](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key) and [Adding a new SSH key to your account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account#adding-a-new-ssh-key-to-your-account))
- SCM_REPO_ORGANIZATION: The project organization (default ansible), can be set to your fork organization.
- SCM_REPO_BRANCH: The branch you want to use (default main)

### Launch the playbook:

Then run the playbook from the aap_templates directory:
```bash
ansible-playbook test/playbooks/templates_seeding.yml 
```

## Create token

In order to launch the mcp server, you need to create an controller application and a token.
This playbook do that for you. It creates the application 'Ansible MCP Templates' on the controller and a token for the admin user.

### Environment variables:

- ANSIBLE_BASE_URL: The base url, for example if you use aap-dev 2.5-next then it is http://localhost:44925
- GATEWAY_USERNAME: Default `admin`
- GATEWAY_PASSWORD: Gateway password

### Launch the playbook

Then run the playbook from the aap_templates directory:
```bash
ansible-playbook test/playbooks/create_token.yml 
```

Then you can use the displayed token in the mcp configuration for the stack (Cursor or other) and when launching the mcp server.
