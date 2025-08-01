# server.py
import inspect
import tempfile
from typing import Annotated, Literal
from pydantic import Field
from fastmcp import FastMCP

from aap_inventory_tool import generate_command


mcp = FastMCP("AI Installer Template MCP Server")


@mcp.tool(
    name="get_inventory",
    description="Get AAP(Ansible Automation Patform) 2.5 inventory file in INI format.",
    tags={"aap, inventory"},
)
def get_inventory(
        platform: Annotated[
            Literal['containerized', 'rpm'],
            Field(description='Platform type (containerized or rpm)'),
        ],
        topology: Annotated[
            Literal['growth', 'enterprise'],
            Field(description='Topology type (growth or enterprise)'),
        ],
        # required for containerized growth topology
        host: Annotated[
            str,
            Field(description='Host (hostname or IP) for all-in-one deployment (required for containerized growth topology)'),
        ] = '',
        # required for containerized enterprise topology
        gateway_hosts: Annotated[
            list[str],
            Field(description='Gateway hosts (required for containerized enterprise topology)'),
        ] = [],
        controller_hosts: Annotated[
            list[str],
            Field(description='Controller hosts (required for containerized enterprise topology)'),
        ] = [],
        hop_host: Annotated[
            str,
            Field(description='Hop node host (required for containerized enterprise topology)'),
        ] = '',
        execution_hosts: Annotated[
            list[str],
            Field(description='Execution node hosts (required for containerized enterprise topology, minimum 2 hosts)'),
        ] = [], # minimum 2
        hub_hosts:  Annotated[
            list[str],
            Field(description='Automation Hub hosts (required for containerized enterprise topology)'),
        ] = [],
        eda_hosts: Annotated[
            list[str],
            Field(description='EDA Controller hosts (required for containerized enterprise topology)'),
        ] = [],
        external_database: Annotated[
            str,
            Field(description='External database host (required for containerized enterprise topology)'),
        ] = '',
        # RPM specfic arguments
        gateway_host: Annotated[
            str,
            Field(description='Gateway host (required for RPM growth topology)'),
        ] = '',
        controller_host: Annotated[
            str,
            Field(description='Controller host (required for RPM growth topology)'),
        ] = '',
        execution_host: Annotated[
            str,
            Field(description='Execution host (required for RPM growth topology)'),
        ] = '',
        hub_host: Annotated[
            str,
            Field(description='Hub host (required for RPM growth topology)'),
        ] = '',
        eda_host: Annotated[
            str,
            Field(description='EDA host (required for RPM growth topology)'),
        ] = '',
        database_host: Annotated[
            str,
            Field(description='Database host (required for RPM growth topology)'),
        ] = '',
        redis:  Annotated[
            list[str],
            Field(description='Redis cluster hosts (optional for enterprise topologies, requires exactly 6 hosts. If not provided, uses 2 gateway + 2 hub + 2 eda hosts)'),
        ] = [],
        # Custom CA certificate parameters
        custom_ca_cert: Annotated[
            str,
            Field(description='Path to custom CA certificate file (optional). If specified without value, will create templated variable.'),
        ] = '',
        ca_tls_cert: Annotated[
            str,
            Field(description='Path to CA TLS certificate file (optional). If specified without value, will create templated variable.'),
        ] = '',
        ca_tls_key: Annotated[
            str,
            Field(description='Path to CA TLS certificate file (optional). If specified without value, will create templated variable.''Path to CA TLS key file (optional). If specified without value, will create templated variable.'),
        ] = '',
        # Hub signing parameters
        hub_signing_auto_sign: Annotated[
            str,
            Field(description='Enable automatic signing for hub collections. If specified without value, will create templated variable.'),
        ] = '',
        hub_signing_require_content_approval: Annotated[
            str,
            Field(description='Require content approval for hub collections. If specified without value, will create templated variable.'),
        ] = '',
        hub_signing_collection_key: Annotated[
            str,
            Field(description='Path to collection signing key. If specified without value, will create templated variable.'),
        ] = '',
        hub_signing_collection_pass: Annotated[
            str,
            Field(description='Passphrase for collection signing key. If specified without value, will create templated variable.'),
        ] = '',
        hub_signing_container_key: Annotated[
            str,
            Field(description='Path to container signing key. If specified without value, will create templated variable.'),
        ] = '',
        hub_signing_container_pass: Annotated[
            str,
            Field(description='Passphrase for container signing key. If specified without value, will create templated variable.'),
        ] = '',
        session_id: Annotated[
            str,
            Field(description='This is a dummy argument added only for llama-stack compatibility'),
        ] = '',
) -> str:
    frame = inspect.currentframe()
    args_dict = inspect.getargvalues(frame).locals

    class Args:
        pass

    args = Args()
    for k,v in args_dict.items():
        if k != "session_id":
            setattr(args, k, v)

    print(f"args: {args}")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        args.output_path = tmp.name
        generate_command(args)
        with open(tmp.name) as f:
            output = f.read()
        return output

    return "An error occurred"



if __name__ == "__main__":
    mcp.run(transport="sse")
