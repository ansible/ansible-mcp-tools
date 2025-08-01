#!/usr/bin/env python3
"""
AAP Inventory Tool

This tool provides validation and comparison functionality for Ansible Automation
Platform inventories (INI format) for containerized and RPM installations
across growth and enterprise topologies.
"""

import argparse
import sys
import configparser
import re
import ipaddress
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple


class InventoryProcessor:
    """Base class for processing AAP inventory files."""

    def __init__(self, platform: str = None, topology: str = None):
        self.platform = platform
        self.topology = topology
        self.errors = []
        self.warnings = []

        # Define required sections for each platform/topology combination
        self.required_sections = {
            'containerized': {
                'growth': ['automationgateway', 'automationcontroller', 'automationhub', 'automationeda', 'database'],
                'enterprise': ['automationgateway', 'automationcontroller', 'automationhub', 'automationeda',
                               'execution_nodes', 'redis']
            },
            'rpm': {
                'growth': ['automationgateway', 'automationcontroller', 'execution_nodes', 'automationhub',
                           'automationedacontroller', 'database'],
                'enterprise': ['automationgateway', 'automationcontroller', 'execution_nodes', 'automationhub',
                               'automationedacontroller', 'redis']
            }
        }

        # Define required variables for each platform
        self.required_vars = {
            'containerized': {
                'common': ['postgresql_admin_password'],
                'gateway': ['gateway_admin_password', 'gateway_pg_host', 'gateway_pg_password'],
                'controller': ['controller_admin_password', 'controller_pg_host', 'controller_pg_password'],
                'hub': ['hub_admin_password', 'hub_pg_host', 'hub_pg_password'],
                'eda': ['eda_admin_password', 'eda_pg_host', 'eda_pg_password']
            },
            'rpm': {
                'common': [],
                'gateway': ['automationgateway_admin_password', 'automationgateway_pg_host',
                            'automationgateway_pg_password'],
                'controller': ['admin_password', 'pg_host', 'pg_password'],
                'hub': ['automationhub_admin_password', 'automationhub_pg_host', 'automationhub_pg_password'],
                'eda': ['automationedacontroller_admin_password', 'automationedacontroller_pg_host',
                        'automationedacontroller_pg_password']
            }
        }

    def parse_inventory(self, inventory_path: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """Parse inventory file and return sections and variables."""
        # Check if file exists first
        if not Path(inventory_path).exists():
            raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

        try:
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(inventory_path)
        except Exception as e:
            raise Exception(f"Error parsing inventory file: {e}")

        sections = self._extract_sections(config)
        variables = self._extract_variables(config)

        return sections, variables

    def _extract_sections(self, config: configparser.ConfigParser) -> Dict[str, List[str]]:
        """Extract Ansible group sections from the INI config."""
        sections = {}

        for section_name in config.sections():
            # Skip variable sections
            if section_name.endswith(':vars'):
                continue

            # Extract hosts from the section
            hosts = []
            for key, value in config.items(section_name):
                if value is None or value.strip() == '':
                    # Host without variables
                    hosts.append(key.strip())
                else:
                    # Host with variables
                    hosts.append(f"{key.strip()} {value.strip()}")

            sections[section_name] = hosts

        return sections

    def _extract_variables(self, config: configparser.ConfigParser) -> Dict[str, str]:
        """Extract variables from the [all:vars] section."""
        variables = {}

        if 'all:vars' in config:
            for key, value in config['all:vars'].items():
                variables[key] = value

        return variables

    def get_results(self) -> Dict[str, List[str]]:
        """Get processing results."""
        return {
            'errors': self.errors,
            'warnings': self.warnings
        }


class InventoryValidator(InventoryProcessor):
    """Validates AAP inventory files based on platform and topology."""

    def validate_inventory(self, inventory_path: str) -> bool:
        """Main validation method."""
        try:
            sections, variables = self.parse_inventory(inventory_path)
        except Exception as e:
            self.errors.append(str(e))
            return False

        # Validate sections
        self._validate_sections(sections)

        # Validate variables
        self._validate_variables(variables)

        # Validate topology-specific requirements
        self._validate_topology_requirements(sections)

        # Validate host entries
        self._validate_host_entries(sections)

        return len(self.errors) == 0

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if a string is a valid hostname."""
        if not hostname or len(hostname) > 253:
            return False

        # Remove trailing dot if present
        if hostname.endswith('.'):
            hostname = hostname[:-1]

        # Check each label in the hostname
        labels = hostname.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return False

        return True

    def _is_valid_ip(self, ip: str) -> bool:
        """Check if a string is a valid IP address (IPv4 or IPv6)."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _is_hostname_or_ip(self, host: str) -> bool:
        """Check if a string is either a valid hostname or IP address."""
        return self._is_valid_hostname(host) or self._is_valid_ip(host)

    def _parse_host_entry(self, host_entry: str) -> Tuple[str, Dict[str, str]]:
        """Parse a host entry to extract hostname and variables."""
        parts = host_entry.split()
        hostname = parts[0]
        variables = {}

        # Parse host variables - handle both space and equals format
        i = 1
        while i < len(parts):
            part = parts[i]
            if '=' in part:
                # Format: key=value
                key, value = part.split('=', 1)
                variables[key] = value
                i += 1
            elif i + 1 < len(parts):
                # Format: key value (from configparser conversion)
                key = part
                value = parts[i + 1]
                variables[key] = value
                i += 2
            else:
                i += 1

        return hostname, variables

    def _validate_sections(self, sections: Dict[str, List[str]]):
        """Validate that all required sections are present."""
        if not self.platform or not self.topology:
            self.warnings.append("Platform and topology not specified, skipping section validation")
            return

        required = self.required_sections[self.platform][self.topology]

        for section in required:
            if section not in sections:
                self.errors.append(f"Missing required section: [{section}]")
            elif not sections[section]:
                self.errors.append(f"Empty required section: [{section}]")

    def _validate_variables(self, variables: Dict[str, str]):
        """Validate that all required variables are present."""
        if not self.platform:
            self.warnings.append("Platform not specified, skipping variable validation")
            return

        required_vars = self.required_vars[self.platform]

        # Check common variables
        for var in required_vars['common']:
            if var not in variables:
                self.errors.append(f"Missing required variable: {var}")

        # Check component-specific variables
        for component in ['gateway', 'controller', 'hub', 'eda']:
            if component in required_vars:
                for var in required_vars[component]:
                    if var not in variables:
                        self.errors.append(f"Missing required {component} variable: {var}")

        # Validate password variables specifically
        self._validate_password_variables(variables)

        # Validate redis_mode settings
        self._validate_redis_mode(variables)

    def _validate_password_variables(self, variables: Dict[str, str]):
        """Validate that password variables are present and not empty."""
        if not self.platform:
            return

        required_vars = self.required_vars[self.platform]
        password_vars = []

        # Collect all password variables from all components
        for component_vars in required_vars.values():
            if isinstance(component_vars, list):
                password_vars.extend([var for var in component_vars if 'password' in var.lower()])

        for var in password_vars:
            if var not in variables:
                self.errors.append(f"Missing required password variable: {var}")
            elif not variables[var] or variables[var].strip() == '':
                self.errors.append(f"Password variable '{var}' is empty")
            elif self._is_variable_placeholder(variables[var]):
                # Allow parameterized variables but warn about them
                self.warnings.append(f"Password variable '{var}' appears to be parameterized: {variables[var]}")

    def _is_variable_placeholder(self, value: str) -> bool:
        """Check if a variable value is a placeholder/template."""
        if not value:
            return False

        # Only consider Jinja2 variables as placeholders
        return '{{' in value

    def _validate_redis_mode(self, variables: Dict[str, str]):
        """Validate redis_mode settings based on topology."""
        if not self.topology:
            return

        if 'redis_mode' in variables:
            redis_mode = variables['redis_mode'].strip()

            if self.topology == 'growth':
                if redis_mode != 'standalone':
                    self.errors.append(f"Growth topology requires redis_mode=standalone, found: {redis_mode}")
            elif self.topology == 'enterprise':
                if redis_mode != 'cluster':
                    self.errors.append(f"Enterprise topology requires redis_mode=cluster, found: {redis_mode}")
        else:
            # redis_mode is required for growth topology
            if self.topology == 'growth':
                self.errors.append("Growth topology requires redis_mode=standalone")

    def _validate_topology_requirements(self, sections: Dict[str, List[str]]):
        """Validate topology-specific requirements."""
        if not self.topology:
            return

        if self.topology == 'growth':
            # Growth topology should have single hosts in most sections
            for section in ['automationgateway', 'automationcontroller', 'automationhub']:
                if section in sections and len(sections[section]) > 1:
                    self.warnings.append(
                        f"Growth topology typically has single host in [{section}], found {len(sections[section])}")

            # For containerized growth, all hostnames/IPs should be the same (all-in-one)
            if self.platform == 'containerized':
                self._validate_containerized_growth_all_in_one(sections)
            # For RPM growth, all components should have different hostnames/IPs
            elif self.platform == 'rpm':
                self._validate_rpm_growth_different_hosts(sections)

        elif self.topology == 'enterprise':
            # Enterprise topology requires multiple hosts for HA
            enterprise_sections = ['automationgateway', 'automationcontroller', 'automationhub']

            # For RPM, check automationedacontroller instead of automationeda
            if self.platform == 'rpm':
                enterprise_sections.append('automationedacontroller')
            else:
                enterprise_sections.append('automationeda')

            for section in enterprise_sections:
                if section in sections and len(sections[section]) < 2:
                    self.errors.append(
                        f"Enterprise topology requires at least 2 hosts in [{section}] for HA, found {len(sections[section])}")

    def _validate_containerized_growth_all_in_one(self, sections: Dict[str, List[str]]):
        """Validate that containerized growth topology uses the same hostname/IP for all components (all-in-one)."""
        # Extract hostnames from each section (ignore host variables)
        hostnames = {}
        for section_name, hosts in sections.items():
            if section_name in ['automationgateway', 'automationcontroller', 'automationhub', 'automationeda',
                                'database']:
                if hosts:
                    # Extract just the hostname part (before any variables)
                    host = hosts[0].split()[0]
                    hostnames[section_name] = host

        # Check if all hostnames are the same
        if len(hostnames) > 1:
            unique_hostnames = set(hostnames.values())
            if len(unique_hostnames) > 1:
                self.errors.append(
                    f"Containerized growth topology should use the same hostname/IP for all components (all-in-one). Found different hostnames: {dict(hostnames)}")

    def _validate_rpm_growth_different_hosts(self, sections: Dict[str, List[str]]):
        """Validate that RPM growth topology uses different hostnames/IPs for each component."""
        # Extract hostnames from each RPM growth component section
        hostnames = {}
        rpm_growth_sections = ['automationgateway', 'automationcontroller', 'execution_nodes', 'automationhub',
                               'automationedacontroller', 'database']

        for section_name, hosts in sections.items():
            if section_name in rpm_growth_sections and hosts:
                # Extract just the hostname part (before any variables)
                host = hosts[0].split()[0]
                hostnames[section_name] = host

        # Check for duplicate hostnames across different components
        if len(hostnames) > 1:
            hostname_to_sections = {}
            for section, hostname in hostnames.items():
                if hostname not in hostname_to_sections:
                    hostname_to_sections[hostname] = []
                hostname_to_sections[hostname].append(section)

            # Report errors for any hostname used by multiple components
            for hostname, sections_list in hostname_to_sections.items():
                if len(sections_list) > 1:
                    self.errors.append(
                        f"RPM growth topology requires different hosts for each component. Host '{hostname}' is used by multiple components: {sections_list}")

    def _validate_host_entries(self, sections: Dict[str, List[str]]):
        """Validate that group hosts are either hostnames/IPs or aliases with ansible_host defined."""
        for section_name, hosts in sections.items():
            for host_entry in hosts:
                hostname, variables = self._parse_host_entry(host_entry)

                # Check if hostname is a valid hostname or IP
                if self._is_hostname_or_ip(hostname):
                    # Valid hostname/IP, no further validation needed
                    continue
                else:
                    # This appears to be an alias, check for ansible_host
                    if 'ansible_host' in variables:
                        ansible_host = variables['ansible_host']
                        if not self._is_hostname_or_ip(ansible_host):
                            self.errors.append(
                                f"Host alias '{hostname}' in section [{section_name}] has invalid ansible_host '{ansible_host}' (must be hostname or IP)")
                    else:
                        self.errors.append(
                            f"Host alias '{hostname}' in section [{section_name}] must have ansible_host defined with a valid hostname or IP")


class InventoryComparator(InventoryProcessor):
    """Compares two AAP inventory files for semantic equivalence."""

    def compare_inventories(self, inventory1_path: str, inventory2_path: str) -> bool:
        """Compare two inventory files for semantic equivalence."""
        try:
            sections1, variables1 = self.parse_inventory(inventory1_path)
            sections2, variables2 = self.parse_inventory(inventory2_path)
        except Exception as e:
            self.errors.append(str(e))
            return False

        # Compare sections
        sections_equal = self._compare_sections(sections1, sections2)

        # Compare variables
        variables_equal = self._compare_variables(variables1, variables2)

        return sections_equal and variables_equal and len(self.errors) == 0

    def _compare_sections(self, sections1: Dict[str, List[str]], sections2: Dict[str, List[str]]) -> bool:
        """Compare sections between two inventories."""
        all_sections = set(sections1.keys()) | set(sections2.keys())
        sections_equal = True

        for section in all_sections:
            if section not in sections1:
                self.errors.append(f"Section [{section}] missing in first inventory")
                sections_equal = False
            elif section not in sections2:
                self.errors.append(f"Section [{section}] missing in second inventory")
                sections_equal = False
            else:
                # Normalize hosts by sorting (order doesn't matter for semantic equivalence)
                hosts1 = sorted(sections1[section])
                hosts2 = sorted(sections2[section])

                if hosts1 != hosts2:
                    self.errors.append(f"Section [{section}] differs between inventories")
                    self.errors.append(f"  First inventory: {hosts1}")
                    self.errors.append(f"  Second inventory: {hosts2}")
                    sections_equal = False

        return sections_equal

    def _compare_variables(self, variables1: Dict[str, str], variables2: Dict[str, str]) -> bool:
        """Compare variables between two inventories."""
        all_vars = set(variables1.keys()) | set(variables2.keys())
        variables_equal = True

        for var in all_vars:
            if var not in variables1:
                self.errors.append(f"Variable '{var}' missing in first inventory")
                variables_equal = False
            elif var not in variables2:
                self.errors.append(f"Variable '{var}' missing in second inventory")
                variables_equal = False
            else:
                val1 = variables1[var].strip()
                val2 = variables2[var].strip()

                if val1 != val2:
                    self.errors.append(f"Variable '{var}' differs between inventories")
                    self.errors.append(f"  First inventory: '{val1}'")
                    self.errors.append(f"  Second inventory: '{val2}'")
                    variables_equal = False

        return variables_equal


class InventoryGenerator(InventoryProcessor):
    """Generates AAP inventory files based on platform and topology."""

    def generate_inventory(self, output_path: str, output_type: str = 'file', host: str = None, **kwargs) -> bool:
        """Generate inventory file based on platform and topology."""
        if not self.platform or not self.topology:
            self.errors.append("Platform and topology must be specified for generation")
            return False

        if self.platform == 'containerized' and self.topology == 'growth':
            return self._generate_containerized_growth(output_path, output_type, host, **kwargs)
        elif self.platform == 'containerized' and self.topology == 'enterprise':
            return self._generate_containerized_enterprise(output_path, output_type, **kwargs)
        elif self.platform == 'rpm' and self.topology == 'growth':
            return self._generate_rpm_growth(output_path, output_type, **kwargs)
        elif self.platform == 'rpm' and self.topology == 'enterprise':
            return self._generate_rpm_enterprise(output_path, output_type, **kwargs)
        else:
            self.errors.append(f"Generation for {self.platform} {self.topology} is not yet implemented")
            return False

    def _build_hub_signing_section(self, **kwargs) -> str:
        """Build hub signing variables section for inventory."""
        hub_signing_section = ""

        if not self.platform:
            return hub_signing_section

        # Map hub signing parameters to inventory variable names based on platform
        if self.platform == 'rpm':
            var_mapping = {
                'hub_signing_auto_sign': ('automationhub_auto_sign_collections', 'true'),
                'hub_signing_require_content_approval': ('automationhub_require_content_approval', 'true'),
                'hub_signing_collection_key': ('automationhub_collection_signing_key', None),
                'hub_signing_collection_pass': ('automationhub_collection_signing_pass', None),
                'hub_signing_container_key': ('automationhub_container_signing_key', None),
                'hub_signing_container_pass': ('automationhub_container_signing_pass', None)
            }
        elif self.platform == 'containerized':
            var_mapping = {
                'hub_signing_auto_sign': ('hub_auto_sign_collections', 'true'),
                'hub_signing_require_content_approval': ('hub_require_content_approval', 'true'),
                'hub_signing_collection_key': ('hub_collection_signing_key', None),
                'hub_signing_collection_pass': ('hub_collection_signing_pass', None),
                'hub_signing_container_key': ('hub_container_signing_key', None),
                'hub_signing_container_pass': ('hub_container_signing_pass', None)
            }
        else:
            return hub_signing_section

        # Check if any hub signing parameters were passed (even if empty)
        hub_signing_requested = any(param in kwargs for param in var_mapping.keys())

        # Build the variables
        hub_signing_vars = []
        for param, (var_name, default_value) in var_mapping.items():
            if param in kwargs:
                if kwargs[param]:
                    # Value was provided
                    if param in ['hub_signing_auto_sign', 'hub_signing_require_content_approval']:
                        # Boolean parameters
                        hub_signing_vars.append(f"{var_name}={default_value}")
                    else:
                        # String parameters (file paths, passwords)
                        value = kwargs[param]
                        if isinstance(value, str):
                            # If it looks like a template variable, keep it, otherwise use the actual value
                            if '{{' in value and '}}' in value:
                                hub_signing_vars.append(f"{var_name}={value}")
                            else:
                                hub_signing_vars.append(f"{var_name}={value}")
                        else:
                            hub_signing_vars.append(f"{var_name}={value}")
                elif kwargs[param] == '':
                    # Parameter was passed but no value provided
                    if param in ['hub_signing_auto_sign', 'hub_signing_require_content_approval']:
                        # Flag parameters - set to True when passed
                        hub_signing_vars.append(f"{var_name}={default_value}")
                    else:
                        # String parameters - create template variable
                        template_var = var_name.replace('automationhub_', '').replace('hub_', '')
                        hub_signing_vars.append(f"{var_name}={{{{ {template_var} }}}}")

        if hub_signing_vars:
            hub_signing_section = "\n" + "\n".join(hub_signing_vars) + "\n"

        return hub_signing_section

    def _build_ca_cert_section(self, **kwargs) -> str:
        """Build custom CA cert variables section for inventory."""
        ca_cert_section = ""

        if not self.platform:
            return ca_cert_section

        # Map CA cert parameters to inventory variable names based on platform
        if self.platform == 'rpm':
            var_mapping = {
                'custom_ca_cert': ('custom_ca_cert', None),
                'ca_tls_cert': ('aap_ca_cert_file', None),
                'ca_tls_key': ('aap_ca_key_file', None)
            }
        elif self.platform == 'containerized':
            var_mapping = {
                'custom_ca_cert': ('custom_ca_cert', None),
                'ca_tls_cert': ('ca_tls_cert', None),
                'ca_tls_key': ('ca_tls_key', None)
            }
        else:
            return ca_cert_section

        # Build the variables
        ca_cert_vars = []
        for param, (var_name, default_value) in var_mapping.items():
            if param in kwargs:
                if kwargs[param]:
                    # Value was provided
                    value = kwargs[param]
                    if isinstance(value, str):
                        # If it looks like a template variable, keep it, otherwise use the actual value
                        if '{{' in value and '}}' in value:
                            ca_cert_vars.append(f"{var_name}={value}")
                        else:
                            ca_cert_vars.append(f"{var_name}={value}")
                    else:
                        ca_cert_vars.append(f"{var_name}={value}")
                elif kwargs[param] == '':
                    # Parameter was passed but no value provided - create template variable
                    template_var = var_name.replace('aap_', '')
                    ca_cert_vars.append(f"{var_name}={{{{ {template_var} }}}}")

        if ca_cert_vars:
            ca_cert_section = "\n" + "\n".join(ca_cert_vars) + "\n"

        return ca_cert_section

    def _generate_containerized_growth(self, output_path: str, output_type: str = 'file', host: str = None,
                                       **kwargs) -> bool:
        """Generate containerized growth inventory."""
        if not host:
            self.errors.append("Host is required for containerized growth topology")
            return False

        # Build custom CA cert section if provided
        ca_cert_section = self._build_ca_cert_section(**kwargs)

        # Build hub signing section if provided
        hub_signing_section = self._build_hub_signing_section(**kwargs)

        # Template based on the minimal containerized growth file
        inventory_content = f"""[automationgateway]
{host}

[automationcontroller]
{host}

[automationhub]
{host}

[automationeda]
{host}

[database]
{host}

[all:vars]
ansible_connection=local
{ca_cert_section}
postgresql_admin_password={{{{ postgresql_admin_password }}}}

registry_username={{{{ registry_username }}}}
registry_password={{{{ registry_password }}}}

redis_mode=standalone

gateway_admin_password={{{{ gateway_admin_password }}}}
gateway_pg_host={host}
gateway_pg_password={{{{ gateway_pg_password }}}}

controller_admin_password={{{{ controller_admin_password }}}}
controller_pg_host={host}
controller_pg_password={{{{ controller_pg_password }}}}
controller_percent_memory_capacity=0.5

hub_admin_password={{{{ hub_admin_password }}}}
hub_pg_host={host}
hub_pg_password={{{{ hub_pg_password }}}}
hub_seed_collections=false{hub_signing_section}
eda_admin_password={{{{ eda_admin_password }}}}
eda_pg_host={host}
eda_pg_password={{{{ eda_pg_password }}}}
"""

        return self._write_output(output_path, output_type, inventory_content)

    def _generate_containerized_enterprise(self, output_path: str, output_type: str = 'file', **kwargs) -> bool:
        """Generate containerized enterprise inventory."""
        # Extract host lists from kwargs
        gateway_hosts = kwargs.get('gateway_hosts', [])
        controller_hosts = kwargs.get('controller_hosts', [])
        hop_host = kwargs.get('hop_host', None)
        execution_hosts = kwargs.get('execution_hosts', [])
        hub_hosts = kwargs.get('hub_hosts', [])
        eda_hosts = kwargs.get('eda_hosts', [])
        external_database = kwargs.get('external_database', None)
        redis_hosts = kwargs.get('redis_hosts', None)

        # Validate required hosts
        if not gateway_hosts:
            self.errors.append("--gateway-hosts is required for containerized enterprise topology")
        if not controller_hosts:
            self.errors.append("--controller-hosts is required for containerized enterprise topology")
        if not hub_hosts:
            self.errors.append("--hub-hosts is required for containerized enterprise topology")
        if not eda_hosts:
            self.errors.append("--eda-hosts is required for containerized enterprise topology")
        if not hop_host:
            self.errors.append("--hop-host is required for containerized enterprise topology")
        if not execution_hosts or len(execution_hosts) < 2:
            self.errors.append(
                "--execution-hosts is required for containerized enterprise topology (minimum 2 execution hosts)")
        if not external_database:
            self.errors.append("--external-database is required for containerized enterprise topology")

        # Validate Redis hosts if provided
        if redis_hosts and len(redis_hosts) != 6:
            self.errors.append("--redis requires exactly 6 hosts for Redis cluster")

        if self.errors:
            return False

        # Enterprise topology requires at least 2 hosts for HA
        if len(gateway_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 gateway hosts for HA")
        if len(controller_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 controller hosts for HA")
        if len(hub_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 hub hosts for HA")
        if len(eda_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 EDA hosts for HA")

        if self.errors:
            return False

        # Build Redis section - use dedicated Redis hosts if provided, otherwise use gateway + hub + eda hosts
        if redis_hosts:
            final_redis_hosts = redis_hosts
        else:
            final_redis_hosts = gateway_hosts + hub_hosts + eda_hosts

        # Build execution nodes section with hop host and execution hosts
        execution_section = ""
        if hop_host:
            execution_section = f"{hop_host} receptor_type='hop'"
            if execution_hosts:
                execution_section += f"\n{chr(10).join(execution_hosts)}"
        elif execution_hosts:
            execution_section = chr(10).join(execution_hosts)

        # Build custom CA cert section if provided
        ca_cert_section = self._build_ca_cert_section(**kwargs)

        # Build hub signing section if provided
        hub_signing_section = self._build_hub_signing_section(**kwargs)

        # Generate inventory content based on minimal template
        inventory_content = f"""[automationgateway]
{chr(10).join(gateway_hosts)}

[automationcontroller]
{chr(10).join(controller_hosts)}

[execution_nodes]
{execution_section}

[automationhub]
{chr(10).join(hub_hosts)}

[automationeda]
{chr(10).join(eda_hosts)}

[redis]
{chr(10).join(final_redis_hosts)}

[all:vars]
{ca_cert_section}
postgresql_admin_password={{{{ postgresql_admin_password }}}}
registry_username={{{{ registry_username }}}}
registry_password={{{{ registry_password }}}}

gateway_admin_password={{{{ gateway_admin_password }}}}
gateway_pg_host={external_database}
gateway_pg_password={{{{ gateway_pg_password }}}}

controller_admin_password={{{{ controller_admin_password }}}}
controller_pg_host={external_database}
controller_pg_password={{{{ controller_pg_password }}}}

hub_admin_password={{{{ hub_admin_password }}}}
hub_pg_host={external_database}
hub_pg_password={{{{ hub_pg_password }}}}{hub_signing_section}

eda_admin_password={{{{ eda_admin_password }}}}
eda_pg_host={external_database}
eda_pg_password={{{{ eda_pg_password }}}}
"""

        return self._write_output(output_path, output_type, inventory_content)

    def _generate_rpm_growth(self, output_path: str, output_type: str = 'file', **kwargs) -> bool:
        """Generate RPM growth inventory."""
        # Extract host parameters from kwargs
        gateway_host = kwargs.get('gateway_host', None)
        controller_host = kwargs.get('controller_host', None)
        execution_host = kwargs.get('execution_host', None)
        hub_host = kwargs.get('hub_host', None)
        eda_host = kwargs.get('eda_host', None)
        database_host = kwargs.get('database_host', None)

        # Validate required hosts
        if not gateway_host:
            self.errors.append("--gateway-host is required for RPM growth topology")
        if not controller_host:
            self.errors.append("--controller-host is required for RPM growth topology")
        if not execution_host:
            self.errors.append("--execution-host is required for RPM growth topology")
        if not hub_host:
            self.errors.append("--hub-host is required for RPM growth topology")
        if not eda_host:
            self.errors.append("--eda-host is required for RPM growth topology")
        if not database_host:
            self.errors.append("--database-host is required for RPM growth topology")

        if self.errors:
            return False

        # Build custom CA cert section for RPM platform if provided
        ca_cert_section = self._build_ca_cert_section(**kwargs)

        # Build hub signing section if provided
        hub_signing_section = self._build_hub_signing_section(**kwargs)

        # Generate inventory content based on RPM growth template
        inventory_content = f"""[automationgateway]
{gateway_host}

[automationcontroller]
{controller_host}

[automationcontroller:vars]
peers=execution_nodes

[execution_nodes]
{execution_host}

[automationhub]
{hub_host}

[automationedacontroller]
{eda_host}

[database]
{database_host}

[all:vars]
{ca_cert_section}
registry_username={{{{ registry_username }}}}
registry_password={{{{ registry_password }}}}

redis_mode=standalone

automationgateway_admin_password={{{{ automationgateway_admin_password }}}}
automationgateway_pg_host={database_host}
automationgateway_pg_password={{{{ automationgateway_pg_password }}}}

admin_password={{{{ admin_password }}}}
pg_host={database_host}
pg_password={{{{ pg_password }}}}

automationhub_admin_password={{{{ automationhub_admin_password }}}}
automationhub_pg_host={database_host}
automationhub_pg_password={{{{ automationhub_pg_password }}}}{hub_signing_section}

automationedacontroller_admin_password={{{{ automationedacontroller_admin_password }}}}
automationedacontroller_pg_host={database_host}
automationedacontroller_pg_password={{{{ automationedacontroller_pg_password }}}}
"""

        return self._write_output(output_path, output_type, inventory_content)

    def _generate_rpm_enterprise(self, output_path: str, output_type: str = 'file', **kwargs) -> bool:
        """Generate RPM enterprise inventory."""
        # Extract host parameters from kwargs
        gateway_hosts = kwargs.get('gateway_hosts', [])
        controller_hosts = kwargs.get('controller_hosts', [])
        hop_host = kwargs.get('hop_host', None)
        execution_hosts = kwargs.get('execution_hosts', [])
        hub_hosts = kwargs.get('hub_hosts', [])
        eda_hosts = kwargs.get('eda_hosts', [])
        external_database = kwargs.get('external_database', None)
        redis_hosts = kwargs.get('redis_hosts', None)

        # Validate required hosts
        if not gateway_hosts:
            self.errors.append("--gateway-hosts is required for RPM enterprise topology")
        if not controller_hosts:
            self.errors.append("--controller-hosts is required for RPM enterprise topology")
        if not hub_hosts:
            self.errors.append("--hub-hosts is required for RPM enterprise topology")
        if not eda_hosts:
            self.errors.append("--eda-hosts is required for RPM enterprise topology")
        if not hop_host:
            self.errors.append("--hop-host is required for RPM enterprise topology")
        if not execution_hosts or len(execution_hosts) < 2:
            self.errors.append("--execution-hosts is required for RPM enterprise topology (minimum 2 execution hosts)")
        if not external_database:
            self.errors.append("--external-database is required for RPM enterprise topology")

        # Validate Redis hosts if provided
        if redis_hosts and len(redis_hosts) != 6:
            self.errors.append("--redis requires exactly 6 hosts for Redis cluster")

        if self.errors:
            return False

        # Enterprise topology requires at least 2 hosts for HA
        if len(gateway_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 gateway hosts for HA")
        if len(controller_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 controller hosts for HA")
        if len(hub_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 hub hosts for HA")
        if len(eda_hosts) < 2:
            self.errors.append("Enterprise topology requires at least 2 EDA hosts for HA")

        if self.errors:
            return False

        # Build Redis section - use dedicated Redis hosts if provided, otherwise use gateway + hub + eda hosts
        if redis_hosts:
            final_redis_hosts = redis_hosts
        else:
            final_redis_hosts = gateway_hosts + hub_hosts + eda_hosts

        # Build custom CA cert section for RPM platform if provided
        ca_cert_section = self._build_ca_cert_section(**kwargs)

        # Build hub signing section if provided
        hub_signing_section = self._build_hub_signing_section(**kwargs)

        # Build execution nodes section with hop host and execution hosts
        execution_section = f"{hop_host} node_type='hop'"
        if execution_hosts:
            execution_section += f"\n{chr(10).join(execution_hosts)}"

        # Generate inventory content based on RPM enterprise template
        inventory_content = f"""[automationgateway]
{chr(10).join(gateway_hosts)}

[automationcontroller]
{chr(10).join(controller_hosts)}

[automationcontroller:vars]
peers=execution_nodes

[execution_nodes]
{execution_section}

[automationhub]
{chr(10).join(hub_hosts)}

[automationedacontroller]
{chr(10).join(eda_hosts)}

[redis]
{chr(10).join(final_redis_hosts)}

[all:vars]
{ca_cert_section}
registry_username={{{{ registry_username }}}}
registry_password={{{{ registry_password }}}}

automationgateway_admin_password={{{{ automationgateway_admin_password }}}}
automationgateway_pg_host={external_database}
automationgateway_pg_password={{{{ automationgateway_pg_password }}}}

admin_password={{{{ admin_password }}}}
pg_host={external_database}
pg_password={{{{ pg_password }}}}

automationhub_admin_password={{{{ automationhub_admin_password }}}}
automationhub_pg_host={external_database}
automationhub_pg_password={{{{ automationhub_pg_password }}}}{hub_signing_section}

automationedacontroller_admin_password={{{{ automationedacontroller_admin_password }}}}
automationedacontroller_pg_host={external_database}
automationedacontroller_pg_password={{{{ automationedacontroller_pg_password }}}}
"""

        return self._write_output(output_path, output_type, inventory_content)

    def _write_output(self, output_path: str, output_type: str, inventory_content: str) -> bool:
        """Write inventory content to file or print to stdout."""
        try:
            if output_type == 'stdout':
                # Print inventory content to stdout
                print(inventory_content)
                return True
            else:
                # Default file output
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(inventory_content)
                return True
        except Exception as e:
            self.errors.append(f"Error writing output: {e}")
            return False


def get_required_params_list(platform: str, topology: str) -> List[str]:
    """Get list of required parameter names for each platform/topology combination."""

    if platform == "containerized" and topology == "growth":
        return ["host"]
    elif platform == "containerized" and topology == "enterprise":
        return ["gateway_hosts", "controller_hosts", "hub_hosts", "eda_hosts", "hop_host", "execution_hosts",
                "external_database"]
    elif platform == "rpm" and topology == "growth":
        return ["gateway_host", "controller_host", "execution_host", "hub_host", "eda_host", "database_host"]
    elif platform == "rpm" and topology == "enterprise":
        return ["gateway_hosts", "controller_hosts", "hub_hosts", "eda_hosts", "hop_host", "execution_hosts",
                "external_database"]
    else:
        return []


def validate_command(args):
    """Handle the validate subcommand."""
    if not Path(args.inventory).exists():
        print(f"Error: Inventory file not found: {args.inventory}")
        sys.exit(1)

    # Create validator and run validation
    validator = InventoryValidator(args.platform, args.topology)
    is_valid = validator.validate_inventory(args.inventory)

    # Get results
    results = validator.get_results()

    # Print results
    print(f"Validating {args.inventory} for {args.platform} {args.topology} topology...")
    print()

    if results['errors']:
        print("ERRORS:")
        for error in results['errors']:
            print(f"  {error}")
        print()

    if results['warnings']:
        print("WARNINGS:")
        for warning in results['warnings']:
            print(f"  {warning}")
        print()

    if is_valid:
        print("Inventory validation passed!")
        if results['warnings']:
            print("   (with warnings)")
        sys.exit(0)
    else:
        print("Inventory validation failed!")
        sys.exit(1)


def compare_command(args):
    """Handle the compare subcommand."""
    if not Path(args.inventory1).exists():
        print(f"Error: First inventory file not found: {args.inventory1}")
        sys.exit(1)

    if not Path(args.inventory2).exists():
        print(f"Error: Second inventory file not found: {args.inventory2}")
        sys.exit(1)

    # Create comparator and run comparison
    comparator = InventoryComparator()
    are_equivalent = comparator.compare_inventories(args.inventory1, args.inventory2)

    # Get results
    results = comparator.get_results()

    # Print results
    print(f"Comparing {args.inventory1} and {args.inventory2}...")
    print()

    if results['errors']:
        print("DIFFERENCES:")
        for error in results['errors']:
            print(f"  {error}")
        print()

    if results['warnings']:
        print("WARNINGS:")
        for warning in results['warnings']:
            print(f"  {warning}")
        print()

    if are_equivalent:
        print("Inventories are semantically equivalent!")
        sys.exit(0)
    else:
        print("Inventories are not semantically equivalent!")
        sys.exit(1)


def generate_command(args):
    """Handle the generate subcommand."""

    # Validate required parameters using centralized function
    required_params = get_required_params_list(args.platform, args.topology)

    if not required_params:
        print(f"Error: Unknown platform/topology combination: {args.platform} {args.topology}")
        # sys.exit(1) # @tamid
        return

    # Check each required parameter
    for param in required_params:
        value = getattr(args, param, None)
        if not value:
            param_display = param.replace('_', '-')
            print(f"Error: --{param_display} is required for {args.platform} {args.topology} topology")
            # sys.exit(1) # @tamid
            return

    # Additional validation for enterprise topologies (minimum hosts requirements)
    if args.topology == 'enterprise':
        # Check execution hosts minimum count
        execution_hosts = getattr(args, 'execution_hosts', [])
        if execution_hosts and len(execution_hosts) < 2:
            print("Error: --execution-hosts requires minimum 2 execution hosts for enterprise topology")
            # sys.exit(1) # @tamid
            return

        # Validate Redis parameter if provided
        redis_hosts = getattr(args, 'redis', None)
        if redis_hosts and len(redis_hosts) != 6:
            print("Error: --redis requires exactly 6 hosts for Redis cluster")
            # sys.exit(1) # @tamid
            return

    # Create generator and generate inventory
    generator = InventoryGenerator(args.platform, args.topology)
    output_path = getattr(args, 'output_path', 'inventory')  # Handle hyphenated arg

    # Prepare kwargs for different platform/topology combinations
    kwargs = {}

    # Add custom CA cert parameters if provided
    ca_cert_params = {}
    if hasattr(args, 'custom_ca_cert') and args.custom_ca_cert:
        ca_cert_params['custom_ca_cert'] = args.custom_ca_cert
    if hasattr(args, 'ca_tls_cert') and args.ca_tls_cert:
        ca_cert_params['ca_tls_cert'] = args.ca_tls_cert
    if hasattr(args, 'ca_tls_key') and args.ca_tls_key:
        ca_cert_params['ca_tls_key'] = args.ca_tls_key

    # Add hub signing parameters if provided
    hub_signing_params = {}
    if hasattr(args, 'hub_signing_auto_sign') and args.hub_signing_auto_sign:
        hub_signing_params['hub_signing_auto_sign'] = args.hub_signing_auto_sign
    if hasattr(args, 'hub_signing_require_content_approval') and args.hub_signing_require_content_approval:
        hub_signing_params['hub_signing_require_content_approval'] = args.hub_signing_require_content_approval
    if hasattr(args, 'hub_signing_collection_key') and args.hub_signing_collection_key:
        hub_signing_params['hub_signing_collection_key'] = args.hub_signing_collection_key
    if hasattr(args, 'hub_signing_collection_pass') and args.hub_signing_collection_pass:
        hub_signing_params['hub_signing_collection_pass'] = args.hub_signing_collection_pass
    if hasattr(args, 'hub_signing_container_key') and args.hub_signing_container_key:
        hub_signing_params['hub_signing_container_key'] = args.hub_signing_container_key
    if hasattr(args, 'hub_signing_container_pass') and args.hub_signing_container_pass:
        hub_signing_params['hub_signing_container_pass'] = args.hub_signing_container_pass

    if args.platform == 'containerized' and args.topology == 'enterprise':
        kwargs = {
            'gateway_hosts': getattr(args, 'gateway_hosts', []),
            'controller_hosts': getattr(args, 'controller_hosts', []),
            'hop_host': getattr(args, 'hop_host', None),
            'execution_hosts': getattr(args, 'execution_hosts', []),
            'hub_hosts': getattr(args, 'hub_hosts', []),
            'eda_hosts': getattr(args, 'eda_hosts', []),
            'external_database': getattr(args, 'external_database', None),
            'redis_hosts': getattr(args, 'redis', None),
            **ca_cert_params,
            **hub_signing_params
        }
    elif args.platform == 'containerized' and args.topology == 'growth':
        kwargs = {**ca_cert_params, **hub_signing_params}
    elif args.platform == 'rpm' and args.topology == 'growth':
        kwargs = {
            'gateway_host': getattr(args, 'gateway_host', None),
            'controller_host': getattr(args, 'controller_host', None),
            'execution_host': getattr(args, 'execution_host', None),
            'hub_host': getattr(args, 'hub_host', None),
            'eda_host': getattr(args, 'eda_host', None),
            'database_host': getattr(args, 'database_host', None),
            **ca_cert_params,
            **hub_signing_params
        }
    elif args.platform == 'rpm' and args.topology == 'enterprise':
        kwargs = {
            'gateway_hosts': getattr(args, 'gateway_hosts', []),
            'controller_hosts': getattr(args, 'controller_hosts', []),
            'hop_host': getattr(args, 'hop_host', None),
            'execution_hosts': getattr(args, 'execution_hosts', []),
            'hub_hosts': getattr(args, 'hub_hosts', []),
            'eda_hosts': getattr(args, 'eda_hosts', []),
            'external_database': getattr(args, 'external_database', None),
            'redis_hosts': getattr(args, 'redis', None),
            **ca_cert_params,
            **hub_signing_params
        }

    output_type = getattr(args, 'output_type', 'file')
    success = generator.generate_inventory(output_path, output_type, args.host, **kwargs)

    # Get results
    results = generator.get_results()

    # Print results
    if results['errors']:
        print("ERRORS:")
        for error in results['errors']:
            print(f"  {error}")
        print()

    if results['warnings']:
        print("WARNINGS:")
        for warning in results['warnings']:
            print(f"  {warning}")
        print()

    # @Tami Temporarily Commented out
    # if success:
    #     if output_type != 'stdout':
    #         print(f"Inventory file generated successfully: {output_path}")
    #     sys.exit(0)
    # else:
    #     print("Inventory generation failed!")
    #     sys.exit(1)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='AAP Inventory Tool - Validate and compare AAP inventory files'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Validate subcommand
    validate_parser = subparsers.add_parser('validate', help='Validate an inventory file')
    validate_parser.add_argument(
        '--inventory',
        required=True,
        help='Path to the inventory file to validate'
    )
    validate_parser.add_argument(
        '--platform',
        required=True,
        choices=['containerized', 'rpm'],
        help='Platform type (containerized or rpm)'
    )
    validate_parser.add_argument(
        '--topology',
        required=True,
        choices=['growth', 'enterprise'],
        help='Topology type (growth or enterprise)'
    )

    # Compare subcommand
    compare_parser = subparsers.add_parser('compare', help='Compare two inventory files')
    compare_parser.add_argument(
        '--inventory1',
        required=True,
        help='Path to the first inventory file'
    )
    compare_parser.add_argument(
        '--inventory2',
        required=True,
        help='Path to the second inventory file'
    )

    # Generate subcommand
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate an inventory file for AAP deployments',
        usage='%(prog)s --platform {containerized,rpm} --topology {growth,enterprise} [options]',
        description='''Generate inventory files for different AAP deployment scenarios.

Examples:
  # Containerized growth (all-in-one) - requires host
  %(prog)s --platform containerized --topology growth --host server.example.com
  %(prog)s --platform containerized --topology growth --host 192.168.1.100

  # Future: RPM growth (distributed) - no host needed  
  %(prog)s --platform rpm --topology growth --output-path my_inventory

Note: --host is required for containerized growth topology only.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    generate_parser.add_argument(
        '--platform',
        required=True,
        choices=['containerized', 'rpm'],
        help='Platform type (containerized or rpm)'
    )
    generate_parser.add_argument(
        '--topology',
        required=True,
        choices=['growth', 'enterprise'],
        help='Topology type (growth or enterprise)'
    )
    generate_parser.add_argument(
        '--output-path',
        default='inventory',
        help='Output path for the generated inventory file (default: inventory)'
    )
    generate_parser.add_argument(
        '--output-type',
        choices=['file', 'stdout'],
        default='file',
        help='Output type: file (write to file) or stdout (print to stdout) (default: file)'
    )
    generate_parser.add_argument(
        '--host',
        help='Host (hostname or IP) for all-in-one deployment (required for containerized growth topology)'
    )
    generate_parser.add_argument(
        '--gateway-hosts',
        nargs='+',
        help='Gateway hosts (required for RPM enterprise topology and containerized enterprise topology)'
    )
    generate_parser.add_argument(
        '--controller-hosts',
        nargs='+',
        help='Controller hosts (required for RPM enterprise topology and containerized enterprise topology)'
    )
    generate_parser.add_argument(
        '--hop-host',
        help='Hop node host (required for RPM enterprise topology and containerized enterprise topology)'
    )
    generate_parser.add_argument(
        '--execution-hosts',
        nargs='*',
        help='Execution node hosts (required for RPM enterprise topology and containerized enterprise topology, minimum 2 hosts)'
    )
    generate_parser.add_argument(
        '--hub-hosts',
        nargs='+',
        help='Automation Hub hosts (required for RPM enterprise topology and containerized enterprise topology)'
    )
    generate_parser.add_argument(
        '--eda-hosts',
        nargs='+',
        help='EDA Controller hosts (required for RPM enterprise topology and containerized enterprise topology)'
    )
    generate_parser.add_argument(
        '--external-database',
        help='External database host (required for RPM enterprise topology and containerized enterprise topology)'
    )

    # RPM-specific arguments
    generate_parser.add_argument(
        '--gateway-host',
        help='Gateway host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--controller-host',
        help='Controller host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--execution-host',
        help='Execution host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--hub-host',
        help='Hub host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--eda-host',
        help='EDA host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--database-host',
        help='Database host (required for RPM growth topology)'
    )
    generate_parser.add_argument(
        '--redis',
        nargs=6,
        help='Redis cluster hosts (optional for enterprise topologies, requires exactly 6 hosts. If not provided, uses 2 gateway + 2 hub + 2 eda hosts)'
    )

    # Custom CA certificate parameters
    generate_parser.add_argument(
        '--custom-ca-cert',
        nargs='?',
        const='',
        help='Path to custom CA certificate file (optional). If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--ca-tls-cert',
        nargs='?',
        const='',
        help='Path to CA TLS certificate file (optional). If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--ca-tls-key',
        nargs='?',
        const='',
        help='Path to CA TLS key file (optional). If specified without value, will create templated variable.'
    )

    # Hub signing parameters
    generate_parser.add_argument(
        '--hub-signing-auto-sign',
        nargs='?',
        const='',
        help='Enable automatic signing for hub collections. If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--hub-signing-require-content-approval',
        nargs='?',
        const='',
        help='Require content approval for hub collections. If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--hub-signing-collection-key',
        nargs='?',
        const='',
        help='Path to collection signing key. If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--hub-signing-collection-pass',
        nargs='?',
        const='',
        help='Passphrase for collection signing key. If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--hub-signing-container-key',
        nargs='?',
        const='',
        help='Path to container signing key. If specified without value, will create templated variable.'
    )
    generate_parser.add_argument(
        '--hub-signing-container-pass',
        nargs='?',
        const='',
        help='Passphrase for container signing key. If specified without value, will create templated variable.'
    )

    # Parse arguments
    args = parser.parse_args()

    if args.command == 'validate':
        validate_command(args)
    elif args.command == 'compare':
        compare_command(args)
    elif args.command == 'generate':
        generate_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()