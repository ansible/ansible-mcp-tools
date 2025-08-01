#!/usr/bin/env python3
"""
Unit tests for AAP Inventory Tool

This module contains comprehensive unit tests for the AAP inventory validation
and comparison functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the tools directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aap_inventory_tool import (
    InventoryProcessor,
    InventoryValidator,
    InventoryComparator,
    InventoryGenerator,
    validate_command,
    compare_command,
    generate_command,
    main
)


class TestInventoryProcessor(unittest.TestCase):
    """Test cases for the InventoryProcessor base class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = InventoryProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory_file(self, content):
        """Helper method to create a temporary inventory file."""
        file_path = os.path.join(self.temp_dir, 'test_inventory.ini')
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_parse_inventory_basic(self):
        """Test basic inventory parsing functionality."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        sections, variables = self.processor.parse_inventory(file_path)

        self.assertIn('automationgateway', sections)
        self.assertIn('automationcontroller', sections)
        # Check that hosts are parsed correctly
        self.assertEqual(sections['automationgateway'], ['gateway.example.org'])
        self.assertEqual(sections['automationcontroller'], ['controller.example.org'])
        self.assertEqual(variables['registry_username'], 'testuser')
        self.assertEqual(variables['registry_password'], 'testpass')

    def test_parse_inventory_with_host_variables(self):
        """Test parsing inventory with host-specific variables."""
        content = """
[execution_nodes]
exec1.example.org
exec2.example.org receptor_type=hop
"""
        file_path = self.create_test_inventory_file(content)

        sections, variables = self.processor.parse_inventory(file_path)

        self.assertIn('execution_nodes', sections)
        self.assertEqual(len(sections['execution_nodes']), 2)
        # Check that hosts are parsed correctly
        self.assertIn('exec1.example.org', sections['execution_nodes'])
        self.assertIn('exec2.example.org receptor_type hop', sections['execution_nodes'])

    def test_parse_inventory_file_not_found(self):
        """Test handling of non-existent inventory file."""
        with self.assertRaises(FileNotFoundError):
            self.processor.parse_inventory('/nonexistent/file.ini')

    def test_parse_inventory_invalid_format(self):
        """Test handling of invalid INI format."""
        content = "invalid ini content [[[["
        file_path = self.create_test_inventory_file(content)

        with self.assertRaises(Exception):
            self.processor.parse_inventory(file_path)

    def test_get_results_initial(self):
        """Test initial state of results."""
        results = self.processor.get_results()
        self.assertEqual(results['errors'], [])
        self.assertEqual(results['warnings'], [])

    def test_get_results_with_errors_warnings(self):
        """Test results after adding errors and warnings."""
        self.processor.errors.append("Test error")
        self.processor.warnings.append("Test warning")

        results = self.processor.get_results()
        self.assertEqual(results['errors'], ["Test error"])
        self.assertEqual(results['warnings'], ["Test warning"])


class TestInventoryValidator(unittest.TestCase):
    """Test cases for the InventoryValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory_file(self, content):
        """Helper method to create a temporary inventory file."""
        file_path = os.path.join(self.temp_dir, 'test_inventory.ini')
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_validate_containerized_growth_valid(self):
        """Test validation of valid containerized growth topology."""
        content = """
[automationgateway]
server.example.org

[automationcontroller]
server.example.org

[automationhub]
server.example.org

[automationeda]
server.example.org

[database]
server.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=server.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=server.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=server.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=server.example.org
eda_pg_password=testpass
redis_mode=standalone
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertEqual(len(validator.errors), 0)

    def test_validate_containerized_growth_missing_section(self):
        """Test validation with missing required section."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertFalse(result)
        self.assertTrue(any('Missing required section' in error for error in validator.errors))

    def test_validate_containerized_growth_missing_variable(self):
        """Test validation with missing required variable."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[automationhub]
hub.example.org

[automationeda]
eda.example.org

[database]
db.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertFalse(result)
        self.assertTrue(any('Missing required' in error for error in validator.errors))

    def test_validate_rpm_growth_valid(self):
        """Test validation of valid RPM growth topology."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[execution_nodes]
exec.example.org

[automationhub]
hub.example.org

[automationedacontroller]
eda.example.org

[database]
db.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
automationgateway_admin_password=testpass
automationgateway_pg_host=db.example.org
automationgateway_pg_password=testpass
admin_password=testpass
pg_host=db.example.org
pg_password=testpass
automationhub_admin_password=testpass
automationhub_pg_host=db.example.org
automationhub_pg_password=testpass
automationedacontroller_admin_password=testpass
automationedacontroller_pg_host=db.example.org
automationedacontroller_pg_password=testpass
redis_mode=standalone
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('rpm', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertEqual(len(validator.errors), 0)

    def test_validate_enterprise_topology_errors(self):
        """Test that enterprise topology generates errors for single hosts."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[automationhub]
hub.example.org

[automationeda]
eda.example.org

[execution_nodes]
exec.example.org

[redis]
redis.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=db.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=db.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=db.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=db.example.org
eda_pg_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'enterprise')
        result = validator.validate_inventory(file_path)

        self.assertFalse(result)
        self.assertTrue(any('Enterprise topology requires at least 2 hosts' in error for error in validator.errors))

    def test_validate_containerized_enterprise_valid(self):
        """Test that containerized enterprise topology passes with multiple hosts."""
        content = """
[automationgateway]
gateway1.example.org
gateway2.example.org

[automationcontroller]
controller1.example.org
controller2.example.org

[automationhub]
hub1.example.org
hub2.example.org

[automationeda]
eda1.example.org
eda2.example.org

[execution_nodes]
exec1.example.org
exec2.example.org

[redis]
redis1.example.org
redis2.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=db.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=db.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=db.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=db.example.org
eda_pg_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'enterprise')
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertEqual(len(validator.errors), 0)

    def test_validate_rpm_enterprise_valid(self):
        """Test that RPM enterprise topology passes with multiple hosts."""
        content = """
[automationgateway]
gateway1.example.org
gateway2.example.org

[automationcontroller]
controller1.example.org
controller2.example.org

[automationhub]
hub1.example.org
hub2.example.org

[automationedacontroller]
eda1.example.org
eda2.example.org

[execution_nodes]
exec1.example.org
exec2.example.org

[redis]
redis1.example.org
redis2.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
automationgateway_admin_password=testpass
automationgateway_pg_host=db.example.org
automationgateway_pg_password=testpass
admin_password=testpass
pg_host=db.example.org
pg_password=testpass
automationhub_admin_password=testpass
automationhub_pg_host=db.example.org
automationhub_pg_password=testpass
automationedacontroller_admin_password=testpass
automationedacontroller_pg_host=db.example.org
automationedacontroller_pg_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('rpm', 'enterprise')
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertEqual(len(validator.errors), 0)

    def test_validate_growth_topology_warnings(self):
        """Test that growth topology generates warnings for multiple hosts."""
        content = """
[automationgateway]
server.example.org
server2.example.org

[automationcontroller]
server.example.org

[automationhub]
server.example.org

[automationeda]
server.example.org

[database]
server.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=server.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=server.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=server.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=server.example.org
eda_pg_password=testpass
redis_mode=standalone
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertTrue(any('Growth topology typically has single host' in warning for warning in validator.warnings))

    def test_validate_containerized_growth_different_hosts_error(self):
        """Test that containerized growth topology fails validation when hosts differ."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[automationhub]
hub.example.org

[automationeda]
eda.example.org

[database]
db.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=db.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=db.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=db.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=db.example.org
eda_pg_password=testpass
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('containerized', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertFalse(result)
        self.assertTrue(any(
            'Containerized growth topology should use the same hostname/IP for all components' in error for error in
            validator.errors))

    def test_validate_without_platform_topology(self):
        """Test validation without platform and topology specified."""
        content = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator()
        result = validator.validate_inventory(file_path)

        self.assertTrue(result)
        self.assertTrue(any('Platform and topology not specified' in warning for warning in validator.warnings))
        self.assertTrue(any('Platform not specified' in warning for warning in validator.warnings))

    def test_validate_rpm_growth_different_hosts_required(self):
        """Test that RPM growth topology requires different hosts for each component."""
        content = """
[automationgateway]
server.example.org

[automationcontroller]
server.example.org

[execution_nodes]
server.example.org

[automationhub]
hub.example.org

[automationedacontroller]
eda.example.org

[database]
db.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
automationgateway_admin_password=testpass
automationgateway_pg_host=db.example.org
automationgateway_pg_password=testpass
admin_password=testpass
pg_host=db.example.org
pg_password=testpass
automationhub_admin_password=testpass
automationhub_pg_host=db.example.org
automationhub_pg_password=testpass
automationedacontroller_admin_password=testpass
automationedacontroller_pg_host=db.example.org
automationedacontroller_pg_password=testpass
redis_mode=standalone
"""
        file_path = self.create_test_inventory_file(content)

        validator = InventoryValidator('rpm', 'growth')
        result = validator.validate_inventory(file_path)

        self.assertFalse(result)
        self.assertTrue(any(
            'RPM growth topology requires different hosts for each component' in error and 'server.example.org' in error
            for error in validator.errors))


class TestInventoryComparator(unittest.TestCase):
    """Test cases for the InventoryComparator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.comparator = InventoryComparator()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory_files(self, content1, content2):
        """Helper method to create two temporary inventory files."""
        file_path1 = os.path.join(self.temp_dir, 'inventory1.ini')
        file_path2 = os.path.join(self.temp_dir, 'inventory2.ini')

        with open(file_path1, 'w') as f:
            f.write(content1)
        with open(file_path2, 'w') as f:
            f.write(content2)

        return file_path1, file_path2

    def test_compare_identical_inventories(self):
        """Test comparison of identical inventories."""
        content = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
"""
        file_path1, file_path2 = self.create_test_inventory_files(content, content)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertTrue(result)
        self.assertEqual(len(self.comparator.errors), 0)

    def test_compare_different_sections(self):
        """Test comparison of inventories with different sections."""
        content1 = """
[automationgateway]
gateway.example.org

[automationcontroller]
controller.example.org

[all:vars]
registry_username=testuser
"""

        content2 = """
[automationgateway]
gateway.example.org

[automationhub]
hub.example.org

[all:vars]
registry_username=testuser
"""

        file_path1, file_path2 = self.create_test_inventory_files(content1, content2)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertFalse(result)
        self.assertTrue(any(
            'Section [automationcontroller] missing in second inventory' in error for error in self.comparator.errors))
        self.assertTrue(
            any('Section [automationhub] missing in first inventory' in error for error in self.comparator.errors))

    def test_compare_different_hosts_in_section(self):
        """Test comparison of inventories with different hosts in same section."""
        content1 = """
[automationgateway]
gateway1.example.org

[all:vars]
registry_username=testuser
"""

        content2 = """
[automationgateway]
gateway2.example.org

[all:vars]
registry_username=testuser
"""

        file_path1, file_path2 = self.create_test_inventory_files(content1, content2)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertFalse(result)
        self.assertTrue(
            any('Section [automationgateway] differs between inventories' in error for error in self.comparator.errors))

    def test_compare_different_variables(self):
        """Test comparison of inventories with different variables."""
        content1 = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser1
registry_password=testpass
"""

        content2 = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser2
registry_password=testpass
"""

        file_path1, file_path2 = self.create_test_inventory_files(content1, content2)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertFalse(result)
        self.assertTrue(any(
            "Variable 'registry_username' differs between inventories" in error for error in self.comparator.errors))

    def test_compare_missing_variables(self):
        """Test comparison with missing variables."""
        content1 = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser
registry_password=testpass
"""

        content2 = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser
"""

        file_path1, file_path2 = self.create_test_inventory_files(content1, content2)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertFalse(result)
        self.assertTrue(any(
            "Variable 'registry_password' missing in second inventory" in error for error in self.comparator.errors))

    def test_compare_hosts_order_irrelevant(self):
        """Test that host order doesn't affect semantic equivalence."""
        content1 = """
[automationgateway]
gateway1.example.org
gateway2.example.org

[all:vars]
registry_username=testuser
"""

        content2 = """
[automationgateway]
gateway2.example.org
gateway1.example.org

[all:vars]
registry_username=testuser
"""

        file_path1, file_path2 = self.create_test_inventory_files(content1, content2)

        result = self.comparator.compare_inventories(file_path1, file_path2)

        self.assertTrue(result)
        self.assertEqual(len(self.comparator.errors), 0)

    def test_compare_file_not_found(self):
        """Test comparison with non-existent file."""
        content = """
[automationgateway]
gateway.example.org
"""
        file_path1 = os.path.join(self.temp_dir, 'inventory1.ini')
        with open(file_path1, 'w') as f:
            f.write(content)

        result = self.comparator.compare_inventories(file_path1, '/nonexistent/file.ini')

        self.assertFalse(result)
        self.assertTrue(any('Inventory file not found' in error for error in self.comparator.errors))


class TestCLICommands(unittest.TestCase):
    """Test cases for CLI command functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory_file(self, content):
        """Helper method to create a temporary inventory file."""
        file_path = os.path.join(self.temp_dir, 'test_inventory.ini')
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_validate_command_success(self, mock_exit, mock_stdout):
        """Test successful validate command."""
        content = """
[automationgateway]
server.example.org

[automationcontroller]
server.example.org

[automationhub]
server.example.org

[automationeda]
server.example.org

[database]
server.example.org

[all:vars]
postgresql_admin_username=postgres
postgresql_admin_password=testpass
registry_username=testuser
registry_password=testpass
gateway_admin_password=testpass
gateway_pg_host=server.example.org
gateway_pg_password=testpass
controller_admin_password=testpass
controller_pg_host=server.example.org
controller_pg_password=testpass
hub_admin_password=testpass
hub_pg_host=server.example.org
hub_pg_password=testpass
eda_admin_password=testpass
eda_pg_host=server.example.org
eda_pg_password=testpass
redis_mode=standalone
"""
        file_path = self.create_test_inventory_file(content)

        # Mock args
        args = MagicMock()
        args.inventory = file_path
        args.platform = 'containerized'
        args.topology = 'growth'

        validate_command(args)

        mock_exit.assert_called_with(0)
        output = mock_stdout.getvalue()
        self.assertIn('Inventory validation passed!', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_validate_command_failure(self, mock_exit, mock_stdout):
        """Test failed validate command."""
        content = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser
"""
        file_path = self.create_test_inventory_file(content)

        # Mock args
        args = MagicMock()
        args.inventory = file_path
        args.platform = 'containerized'
        args.topology = 'growth'

        validate_command(args)

        mock_exit.assert_called_with(1)
        output = mock_stdout.getvalue()
        self.assertIn('Inventory validation failed!', output)
        self.assertIn('ERRORS:', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_validate_command_file_not_found(self, mock_exit, mock_stdout):
        """Test validate command with non-existent file."""
        args = MagicMock()
        args.inventory = '/nonexistent/file.ini'
        args.platform = 'containerized'
        args.topology = 'growth'

        validate_command(args)

        mock_exit.assert_called_with(1)
        output = mock_stdout.getvalue()
        self.assertIn('Error: Inventory file not found', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_compare_command_success(self, mock_exit, mock_stdout):
        """Test successful compare command."""
        content = """
[automationgateway]
gateway.example.org

[all:vars]
registry_username=testuser
"""
        file_path1 = os.path.join(self.temp_dir, 'inventory1.ini')
        file_path2 = os.path.join(self.temp_dir, 'inventory2.ini')

        with open(file_path1, 'w') as f:
            f.write(content)
        with open(file_path2, 'w') as f:
            f.write(content)

        # Mock args
        args = MagicMock()
        args.inventory1 = file_path1
        args.inventory2 = file_path2

        compare_command(args)

        mock_exit.assert_called_with(0)
        output = mock_stdout.getvalue()
        self.assertIn('Inventories are semantically equivalent!', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_compare_command_failure(self, mock_exit, mock_stdout):
        """Test failed compare command."""
        content1 = """
[automationgateway]
gateway1.example.org

[all:vars]
registry_username=testuser
"""
        content2 = """
[automationgateway]
gateway2.example.org

[all:vars]
registry_username=testuser
"""

        file_path1 = os.path.join(self.temp_dir, 'inventory1.ini')
        file_path2 = os.path.join(self.temp_dir, 'inventory2.ini')

        with open(file_path1, 'w') as f:
            f.write(content1)
        with open(file_path2, 'w') as f:
            f.write(content2)

        # Mock args
        args = MagicMock()
        args.inventory1 = file_path1
        args.inventory2 = file_path2

        compare_command(args)

        mock_exit.assert_called_with(1)
        output = mock_stdout.getvalue()
        self.assertIn('Inventories are not semantically equivalent!', output)
        self.assertIn('DIFFERENCES:', output)


class TestMainFunction(unittest.TestCase):
    """Test cases for the main function."""

    @patch('sys.argv', ['aap_inventory_tool.py', 'validate', '--help'])
    def test_main_validate_help(self):
        """Test main function with validate help."""
        with self.assertRaises(SystemExit):
            main()

    @patch('sys.argv', ['aap_inventory_tool.py', 'compare', '--help'])
    def test_main_compare_help(self):
        """Test main function with compare help."""
        with self.assertRaises(SystemExit):
            main()

    @patch('sys.argv', ['aap_inventory_tool.py', '--help'])
    def test_main_help(self):
        """Test main function with general help."""
        with self.assertRaises(SystemExit):
            main()

    @patch('sys.argv', ['aap_inventory_tool.py'])
    @patch('sys.exit')
    def test_main_no_command(self, mock_exit):
        """Test main function with no command."""
        main()

        mock_exit.assert_called_with(1)

    @patch('sys.argv', ['aap_inventory_tool.py', 'generate', '--help'])
    def test_main_generate_help(self):
        """Test main function with generate help."""
        with self.assertRaises(SystemExit):
            main()

    @patch('sys.argv', ['aap_inventory_tool.py', 'generate', '--platform', 'containerized', '--topology', 'growth'])
    @patch('sys.exit')
    def test_main_generate_missing_host(self, mock_exit):
        """Test main function generate command missing host."""
        main()

        mock_exit.assert_called_with(1)


class TestPasswordVariableValidation(unittest.TestCase):
    """Test cases for password variable validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = InventoryValidator('containerized', 'growth')
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory(self, content: str) -> str:
        """Create a temporary inventory file with given content."""
        temp_file = os.path.join(self.temp_dir, 'test_inventory.ini')
        with open(temp_file, 'w') as f:
            f.write(content)
        return temp_file

    def test_missing_password_variables(self):
        """Test validation fails when password variables are missing."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=secret123
postgresql_admin_username=postgres
# postgresql_admin_password missing
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=gatewaydb123
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertFalse(is_valid)
        self.assertTrue(any('postgresql_admin_password' in error for error in results['errors']))

    def test_empty_password_variables(self):
        """Test validation fails when password variables are empty."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=optional123
postgresql_admin_username=postgres
postgresql_admin_password=
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=gatewaydb123
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertFalse(is_valid)
        self.assertTrue(
            any("Password variable 'postgresql_admin_password' is empty" in error for error in results['errors']))

    def test_parameterized_password_variables_warning(self):
        """Test validation warns about parameterized password variables."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password={{ vault_registry_password }}
postgresql_admin_username=postgres
postgresql_admin_password={{ vault_postgres_password }}
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=gatewaydb123
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
redis_mode=standalone
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertTrue(is_valid)
        self.assertTrue(any(
            "postgresql_admin_password" in warning and "parameterized" in warning for warning in results['warnings']))
        # registry_password is not required, so it won't generate warnings about parameterization

    def test_placeholder_detection(self):
        """Test detection of Jinja2 placeholder patterns."""
        test_cases = [
            ("{{ vault_password }}", True),
            ("{{vault_password}}", True),
            ("prefix_{{ vault_password }}_suffix", True),
            ("${PASSWORD}", False),
            ("CHANGEME", False),
            ("REPLACE_THIS", False),
            ("TODO: set password", False),
            ("FIXME", False),
            ("<password>", False),
            ("example_password", False),
            ("dummy_pass", False),
            ("real_password_123", False),
            ("secretpassword", False),
            ("", False),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value):
                result = self.validator._is_variable_placeholder(value)
                self.assertEqual(result, expected, f"Failed for value: '{value}'")

    def test_valid_inventory_with_all_passwords(self):
        """Test validation passes when all password variables are present."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=secret123
postgresql_admin_username=postgres
postgresql_admin_password=postgres123
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=gatewaydb123
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
redis_mode=standalone
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertTrue(is_valid)
        self.assertEqual(len(results['errors']), 0)

    def test_rpm_platform_password_validation(self):
        """Test password validation for RPM platform."""
        rpm_validator = InventoryValidator('rpm', 'growth')

        inventory_content = """
[automationgateway]
gateway.example.com

[automationcontroller]
controller.example.com

[execution_nodes]
exec.example.com

[automationhub]
hub.example.com

[automationedacontroller]
eda.example.com

[database]
db.example.com

[all:vars]
registry_username=admin
registry_password=secret123
automationgateway_admin_password=gateway123
automationgateway_pg_host=db.example.com
automationgateway_pg_password=gatewaydb123
admin_password=controller123
pg_host=db.example.com
pg_password=controllerdb123
automationhub_admin_password=hub123
automationhub_pg_host=db.example.com
automationhub_pg_password=hubdb123
automationedacontroller_admin_password=eda123
automationedacontroller_pg_host=db.example.com
automationedacontroller_pg_password=edadb123
redis_mode=standalone
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = rpm_validator.validate_inventory(inventory_file)
        results = rpm_validator.get_results()

        self.assertTrue(is_valid)
        self.assertEqual(len(results['errors']), 0)

    def test_multiple_missing_passwords(self):
        """Test validation reports multiple missing password variables."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=optional123
# Missing multiple password variables
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
controller_admin_password=controller123
controller_pg_host=server.example.com
hub_admin_password=hub123
hub_pg_host=server.example.com
eda_admin_password=eda123
eda_pg_host=server.example.com
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertFalse(is_valid)

        # Check for multiple missing password errors
        password_errors = [error for error in results['errors'] if 'password' in error.lower()]
        self.assertGreater(len(password_errors), 1)

        # Check for specific missing passwords - only required ones
        self.assertTrue(any('postgresql_admin_password' in error for error in results['errors']))
        self.assertTrue(any('gateway_pg_password' in error for error in results['errors']))
        self.assertTrue(any('controller_pg_password' in error for error in results['errors']))

    def test_whitespace_only_password_variables(self):
        """Test validation fails when password variables contain only whitespace."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=optional123
postgresql_admin_username=postgres
postgresql_admin_password=   
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=gatewaydb123
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertFalse(is_valid)
        self.assertTrue(
            any("Password variable 'postgresql_admin_password' is empty" in error for error in results['errors']))

    def test_mixed_valid_and_parameterized_passwords(self):
        """Test validation with mix of valid and parameterized password variables."""
        inventory_content = """
[automationgateway]
server.example.com

[automationcontroller]
server.example.com

[automationhub]
server.example.com

[automationeda]
server.example.com

[database]
server.example.com

[all:vars]
registry_username=admin
registry_password=secret123
postgresql_admin_username=postgres
postgresql_admin_password={{ vault_postgres_password }}
gateway_admin_password=gateway123
gateway_pg_host=server.example.com
gateway_pg_password=${GATEWAY_DB_PASSWORD}
controller_admin_password=controller123
controller_pg_host=server.example.com
controller_pg_password=controllerdb123
hub_admin_password=hub123
hub_pg_host=server.example.com
hub_pg_password=hubdb123
eda_admin_password=eda123
eda_pg_host=server.example.com
eda_pg_password=edadb123
redis_mode=standalone
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        self.assertTrue(is_valid)
        # Should have warnings for Jinja2 parameterized passwords (only required ones)
        self.assertTrue(any(
            "postgresql_admin_password" in warning and "parameterized" in warning for warning in results['warnings']))
        # Should not have warnings for shell variables or valid passwords
        self.assertFalse(
            any("gateway_pg_password" in warning and "parameterized" in warning for warning in results['warnings']))
        # registry_password is not required, so it won't generate warnings about parameterization
        self.assertFalse(
            any("registry_password" in warning and "parameterized" in warning for warning in results['warnings']))


class TestHostValidation(unittest.TestCase):
    """Test cases for host validation methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = InventoryValidator('containerized', 'growth')
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_test_inventory(self, content: str) -> str:
        """Create a temporary inventory file with given content."""
        temp_file = os.path.join(self.temp_dir, 'test_inventory.ini')
        with open(temp_file, 'w') as f:
            f.write(content)
        return temp_file

    def test_is_valid_hostname(self):
        """Test hostname validation."""
        valid_hostnames = [
            'server.example.com',
            'host-1.example.org',
            'a.b.c.d.example.net',
            'simple-host',
            'host123',
            'test-server.local',
            'server.example.com.',  # trailing dot
            'host',  # single label
            'a' * 63,  # max label length
            'a.b'  # minimal two-label domain
        ]

        invalid_hostnames = [
            '',  # empty
            'host..example.com',  # double dots
            'host-.example.com',  # ending with dash
            '-host.example.com',  # starting with dash
            'host_name.example.com',  # underscore
            'host@example.com',  # invalid character
            'host with spaces.com',  # spaces
            'a' * 64,  # label too long
            'a' * 254,  # hostname too long
            '.host.example.com',  # starting with dot
            'host.example.com..',  # ending with double dots
            'HOST.EXAMPLE.COM',  # uppercase (actually valid, but test case)
        ]

        for hostname in valid_hostnames:
            with self.subTest(hostname=hostname):
                self.assertTrue(self.validator._is_valid_hostname(hostname),
                                f"'{hostname}' should be valid")

        for hostname in invalid_hostnames:
            with self.subTest(hostname=hostname):
                if hostname == 'HOST.EXAMPLE.COM':
                    # Actually valid - uppercase is allowed
                    self.assertTrue(self.validator._is_valid_hostname(hostname))
                else:
                    self.assertFalse(self.validator._is_valid_hostname(hostname),
                                     f"'{hostname}' should be invalid")

    def test_is_valid_ip(self):
        """Test IP address validation."""
        valid_ipv4 = [
            '192.168.1.1',
            '10.0.0.1',
            '172.16.0.1',
            '127.0.0.1',
            '255.255.255.255',
            '0.0.0.0',
            '8.8.8.8',
            '1.1.1.1'
        ]

        valid_ipv6 = [
            '2001:db8::1',
            '::1',
            '2001:db8:85a3::8a2e:370:7334',
            'fe80::1',
            '::',
            '2001:db8:85a3:0:0:8a2e:370:7334',
            '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        ]

        invalid_ips = [
            '',  # empty
            '192.168.1.256',  # invalid IPv4
            '192.168.1',  # incomplete IPv4
            '192.168.1.1.1',  # too many octets
            'not.an.ip',  # hostname
            '2001:db8::1::1',  # invalid IPv6
            'gggg::1',  # invalid hex
            '192.168.1.1/24',  # CIDR notation
            'localhost',  # hostname
            '999.999.999.999',  # out of range
        ]

        for ip in valid_ipv4:
            with self.subTest(ip=ip):
                self.assertTrue(self.validator._is_valid_ip(ip),
                                f"'{ip}' should be valid IPv4")

        for ip in valid_ipv6:
            with self.subTest(ip=ip):
                self.assertTrue(self.validator._is_valid_ip(ip),
                                f"'{ip}' should be valid IPv6")

        for ip in invalid_ips:
            with self.subTest(ip=ip):
                self.assertFalse(self.validator._is_valid_ip(ip),
                                 f"'{ip}' should be invalid")

    def test_is_hostname_or_ip(self):
        """Test combined hostname/IP validation."""
        valid_entries = [
            'server.example.com',
            '192.168.1.1',
            '2001:db8::1',
            'localhost',
            'host-1.example.org',
            '10.0.0.1',
            'simple-host'
        ]

        invalid_entries = [
            '',  # empty
            'host..example.com',  # invalid hostname
            'host@example.com',  # invalid hostname
            'not a valid entry',  # spaces
            'alias_name'  # underscore (could be alias)
        ]

        for entry in valid_entries:
            with self.subTest(entry=entry):
                self.assertTrue(self.validator._is_hostname_or_ip(entry),
                                f"'{entry}' should be valid hostname or IP")

        for entry in invalid_entries:
            with self.subTest(entry=entry):
                self.assertFalse(self.validator._is_hostname_or_ip(entry),
                                 f"'{entry}' should be invalid")

    def test_parse_host_entry(self):
        """Test parsing of host entries."""
        test_cases = [
            ('server.example.com', ('server.example.com', {})),
            ('server.example.com ansible_host=192.168.1.1',
             ('server.example.com', {'ansible_host': '192.168.1.1'})),
            ('web-server ansible_host=web.example.com ansible_port=8080',
             ('web-server', {'ansible_host': 'web.example.com', 'ansible_port': '8080'})),
            ('192.168.1.1', ('192.168.1.1', {})),
            ('node1 ansible_host=10.0.0.1 ansible_user=admin',
             ('node1', {'ansible_host': '10.0.0.1', 'ansible_user': 'admin'})),
            ('host receptor_type=hop', ('host', {'receptor_type': 'hop'})),
            ('server key=value another=test',
             ('server', {'key': 'value', 'another': 'test'})),
            ('server key=value=with=equals',
             ('server', {'key': 'value=with=equals'})),
        ]

        for host_entry, expected in test_cases:
            with self.subTest(host_entry=host_entry):
                result = self.validator._parse_host_entry(host_entry)
                self.assertEqual(result, expected)

    def test_validate_host_entries_valid_hostnames(self):
        """Test host validation with valid hostnames."""
        inventory_content = """
[automationgateway]
gateway.example.com
gateway-2.example.org

[automationcontroller]
controller.example.com
192.168.1.10

[automationhub]
hub.example.com
2001:db8::1

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should not have host validation errors
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 0)

    def test_validate_host_entries_valid_aliases(self):
        """Test host validation with valid aliases."""
        inventory_content = """
[automationgateway]
gateway-primary ansible_host=gateway.example.com
gateway-backup ansible_host=192.168.1.1

[automationcontroller]
controller-1 ansible_host=controller.example.com
controller-2 ansible_host=10.0.0.1

[automationhub]
hub-node ansible_host=2001:db8::1

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should not have host validation errors
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 0)

    def test_validate_host_entries_invalid_aliases_missing_ansible_host(self):
        """Test host validation with aliases missing ansible_host."""
        inventory_content = """
[automationgateway]
gateway_primary
web-server_backup

[automationcontroller]
controller_node_1

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should have host validation errors for missing ansible_host
        host_errors = [error for error in results['errors'] if 'must have ansible_host defined' in error]
        self.assertEqual(len(host_errors), 3)  # 3 invalid aliases

        # Check specific error messages
        self.assertTrue(any('gateway_primary' in error for error in host_errors))
        self.assertTrue(any('web-server_backup' in error for error in host_errors))
        self.assertTrue(any('controller_node_1' in error for error in host_errors))

    def test_validate_host_entries_invalid_ansible_host_values(self):
        """Test host validation with invalid ansible_host values."""
        inventory_content = """
[automationgateway]
gateway_primary ansible_host=invalid..hostname
gateway-backup ansible_host=192.168.1.256

[automationcontroller]
controller_1 ansible_host=host@invalid.com

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should have host validation errors for invalid ansible_host values
        host_errors = [error for error in results['errors'] if 'has invalid ansible_host' in error]
        self.assertEqual(len(host_errors),
                         2)  # 2 invalid ansible_host values (192.168.1.256 is actually valid as hostname)

        # Check specific error messages
        self.assertTrue(any('gateway_primary' in error and 'invalid..hostname' in error for error in host_errors))
        self.assertTrue(any('controller_1' in error and 'host@invalid.com' in error for error in host_errors))

    def test_validate_host_entries_mixed_valid_invalid(self):
        """Test host validation with mix of valid and invalid entries."""
        inventory_content = """
[automationgateway]
gateway.example.com
gateway-alias ansible_host=gateway-backup.example.com

[automationcontroller]
controller_invalid_alias
192.168.1.10

[automationhub]
hub_node ansible_host=host@invalid.com
hub.example.com

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should have host validation errors for the invalid entries only
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 2)  # 2 invalid entries

        # Check specific error messages
        self.assertTrue(any(
            'controller_invalid_alias' in error and 'must have ansible_host defined' in error for error in host_errors))
        self.assertTrue(any('hub_node' in error and 'host@invalid.com' in error for error in host_errors))

    def test_validate_host_entries_with_additional_variables(self):
        """Test host validation with additional host variables."""
        inventory_content = """
[automationgateway]
gateway.example.com ansible_port=8080 ansible_user=admin

[automationcontroller]
controller-alias ansible_host=controller.example.com ansible_port=443 receptor_type=control

[execution_nodes]
exec-node ansible_host=192.168.1.100 receptor_type=execution

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should not have host validation errors (ignore topology errors)
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 0)

    def test_validate_host_entries_empty_sections(self):
        """Test host validation with empty sections."""
        inventory_content = """
[automationgateway]
gateway.example.com

[automationcontroller]

[automationhub]
hub.example.com

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should not have host validation errors (empty sections are handled elsewhere)
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 0)

    def test_validate_special_characters_in_hostnames(self):
        """Test validation of hostnames with special characters."""
        inventory_content = """
[automationgateway]
server-with-dashes.example.com
server123.example.org

[automationcontroller]
under_score_host ansible_host=valid-server.example.com
special@host ansible_host=192.168.1.1

[all:vars]
registry_username=admin
"""
        inventory_file = self.create_test_inventory(inventory_content)

        is_valid = self.validator.validate_inventory(inventory_file)
        results = self.validator.get_results()

        # Should not have errors because the ansible_host values are valid
        host_errors = [error for error in results['errors'] if
                       ('has invalid ansible_host' in error or 'must have ansible_host defined' in error)]
        self.assertEqual(len(host_errors), 0)  # All have valid ansible_host values


class TestInventoryGenerator(unittest.TestCase):
    """Test cases for the InventoryGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_generate_containerized_growth_basic(self):
        """Test basic containerized growth inventory generation."""
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'generated_inventory')
        host = 'test.example.com'

        success = generator.generate_inventory(output_path, host)
        results = generator.get_results()

        self.assertTrue(success)
        self.assertEqual(len(results['errors']), 0)

        # Verify file was created
        self.assertTrue(Path(output_path).exists())

        # Read and verify content
        with open(output_path, 'r') as f:
            content = f.read()

        # Check for required sections
        self.assertIn('[automationgateway]', content)
        self.assertIn('[automationcontroller]', content)
        self.assertIn('[automationhub]', content)
        self.assertIn('[automationeda]', content)
        self.assertIn('[database]', content)
        self.assertIn('[all:vars]', content)

        # Check that host is used throughout
        self.assertIn(host, content)

        # Check for Jinja2 placeholders
        self.assertIn('{{ postgresql_admin_password }}', content)
        self.assertIn('{{ gateway_admin_password }}', content)
        self.assertIn('{{ controller_admin_password }}', content)
        self.assertIn('{{ hub_admin_password }}', content)
        self.assertIn('{{ eda_admin_password }}', content)

        # Check that comments are not present
        self.assertNotIn('#', content)
        self.assertNotIn('This is the AAP installer inventory file', content)

    def test_generate_containerized_growth_without_host(self):
        """Test that generation fails without host for containerized growth."""
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'generated_inventory')

        success = generator.generate_inventory(output_path, None)
        results = generator.get_results()

        self.assertFalse(success)
        self.assertTrue(any('Host is required' in error for error in results['errors']))

        # File should not exist
        self.assertFalse(Path(output_path).exists())

    def test_generate_unsupported_platform_topology(self):
        """Test generation fails for unsupported platform/topology combinations."""
        # Test invalid platform
        generator = InventoryGenerator('invalid_platform', 'growth')
        output_path = os.path.join(self.temp_dir, 'generated_inventory')

        success = generator.generate_inventory(output_path, 'test.example.com')
        results = generator.get_results()

        self.assertFalse(success)
        self.assertTrue(any(
            'Generation for invalid_platform growth is not yet implemented' in error for error in results['errors']))

    def test_generate_without_platform_topology(self):
        """Test generation fails without platform and topology."""
        generator = InventoryGenerator()
        output_path = os.path.join(self.temp_dir, 'generated_inventory')

        success = generator.generate_inventory(output_path, 'test.example.com')
        results = generator.get_results()

        self.assertFalse(success)
        self.assertTrue(any('Platform and topology must be specified' in error for error in results['errors']))

    def test_generate_creates_parent_directories(self):
        """Test that generation creates parent directories if they don't exist."""
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'nested', 'folder', 'inventory')

        success = generator.generate_inventory(output_path, 'test.example.com')
        results = generator.get_results()

        self.assertTrue(success)
        self.assertEqual(len(results['errors']), 0)
        self.assertTrue(Path(output_path).exists())
        self.assertTrue(Path(output_path).parent.exists())

    def test_generate_file_write_error(self):
        """Test handling of file write errors."""
        generator = InventoryGenerator('containerized', 'growth')
        # Use a path that should cause a write error (read-only directory)
        output_path = '/root/cannot_write_here'

        success = generator.generate_inventory(output_path, 'test.example.com')
        results = generator.get_results()

        self.assertFalse(success)
        self.assertTrue(any('Error writing inventory file' in error for error in results['errors']))

    def test_generated_inventory_validates_successfully(self):
        """Test that generated inventory passes validation using existing validator."""
        # Generate inventory
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'generated_inventory')
        host = 'server.example.com'

        success = generator.generate_inventory(output_path, host)
        self.assertTrue(success)

        # Now validate the generated inventory
        validator = InventoryValidator('containerized', 'growth')
        is_valid = validator.validate_inventory(output_path)
        results = validator.get_results()

        # The generated inventory should be valid (except for templated passwords which will generate warnings)
        self.assertTrue(is_valid)

        # Should have warnings about parameterized passwords, but no errors
        self.assertEqual(len(results['errors']), 0)
        self.assertTrue(any('parameterized' in warning for warning in results['warnings']))

    def test_generated_inventory_content_structure(self):
        """Test the detailed structure of generated inventory content."""
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'generated_inventory')
        host = 'myhost.example.org'

        success = generator.generate_inventory(output_path, host)
        self.assertTrue(success)

        # Parse the generated file to verify structure
        sections, variables = generator.parse_inventory(output_path)

        # Check sections contain the host
        expected_sections = ['automationgateway', 'automationcontroller', 'automationhub', 'automationeda', 'database']
        for section in expected_sections:
            self.assertIn(section, sections)
            self.assertEqual(sections[section], [host])

        # Check variables
        expected_vars = [
            'ansible_connection', 'postgresql_admin_password',
            'registry_username', 'registry_password', 'redis_mode',
            'gateway_admin_password', 'gateway_pg_host', 'gateway_pg_password',
            'controller_admin_password', 'controller_pg_host', 'controller_pg_password',
            'controller_percent_memory_capacity',
            'hub_admin_password', 'hub_pg_host', 'hub_pg_password', 'hub_seed_collections',
            'eda_admin_password', 'eda_pg_host', 'eda_pg_password'
        ]

        for var in expected_vars:
            self.assertIn(var, variables)

        # Check specific values
        self.assertEqual(variables['ansible_connection'], 'local')
        self.assertEqual(variables['redis_mode'], 'standalone')
        self.assertEqual(variables['controller_percent_memory_capacity'], '0.5')
        self.assertEqual(variables['hub_seed_collections'], 'false')

        # Check that host variables point to the host
        self.assertEqual(variables['gateway_pg_host'], host)
        self.assertEqual(variables['controller_pg_host'], host)
        self.assertEqual(variables['hub_pg_host'], host)
        self.assertEqual(variables['eda_pg_host'], host)

        # Check that password variables are templated
        password_vars = ['postgresql_admin_password', 'registry_username', 'registry_password',
                         'gateway_admin_password', 'gateway_pg_password',
                         'controller_admin_password', 'controller_pg_password',
                         'hub_admin_password', 'hub_pg_password',
                         'eda_admin_password', 'eda_pg_password']

        for var in password_vars:
            self.assertIn('{{', variables[var])
            self.assertIn('}}', variables[var])


class TestGenerateCommand(unittest.TestCase):
    """Test cases for the generate_command function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_generate_command_success(self, mock_exit, mock_stdout):
        """Test successful generate command."""
        args = MagicMock()
        args.platform = 'containerized'
        args.topology = 'growth'
        args.host = 'test.example.com'
        args.output_path = os.path.join(self.temp_dir, 'test_inventory')

        generate_command(args)

        mock_exit.assert_called_with(0)
        output = mock_stdout.getvalue()
        self.assertIn('Inventory file generated successfully', output)
        self.assertTrue(Path(args.output_path).exists())

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_generate_command_missing_host(self, mock_exit, mock_stdout):
        """Test generate command failure when host is missing for containerized growth."""
        args = MagicMock()
        args.platform = 'containerized'
        args.topology = 'growth'
        args.host = None
        args.output_path = os.path.join(self.temp_dir, 'test_inventory')

        generate_command(args)

        mock_exit.assert_called_with(1)
        output = mock_stdout.getvalue()
        self.assertIn('Error: --host is required for containerized growth topology', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_generate_command_unsupported_platform_topology(self, mock_exit, mock_stdout):
        """Test generate command with unsupported platform/topology."""
        args = MagicMock()
        args.platform = 'rpm'
        args.topology = 'growth'
        # Missing required arguments for RPM growth
        args.gateway_host = None
        args.controller_host = None
        args.execution_host = None
        args.hub_host = None
        args.eda_host = None
        args.database_host = None
        args.host = 'test.example.com'
        args.output_path = os.path.join(self.temp_dir, 'test_inventory')

        generate_command(args)

        mock_exit.assert_called_with(1)
        output = mock_stdout.getvalue()
        self.assertIn('Error:', output)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.exit')
    def test_generate_command_default_output_path(self, mock_exit, mock_stdout):
        """Test generate command with default output path."""
        args = MagicMock()
        args.platform = 'containerized'
        args.topology = 'growth'
        args.host = 'test.example.com'
        # Simulate missing output_path attribute (hyphenated arg)
        del args.output_path

        # Change to temp directory so default 'inventory' file is created there
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            generate_command(args)

            mock_exit.assert_called_with(0)
            output = mock_stdout.getvalue()
            self.assertIn('Inventory file generated successfully: inventory', output)
            self.assertTrue(Path('inventory').exists())
        finally:
            os.chdir(original_cwd)


class TestGenerateIntegration(unittest.TestCase):
    """Integration tests for the generate functionality with validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_generate_and_validate_cycle(self):
        """Test complete cycle: generate inventory, then validate it."""
        # Generate inventory
        generator = InventoryGenerator('containerized', 'growth')
        output_path = os.path.join(self.temp_dir, 'test_inventory')
        host = 'production.example.com'

        success = generator.generate_inventory(output_path, host)
        self.assertTrue(success)

        # Validate the generated inventory
        validator = InventoryValidator('containerized', 'growth')
        is_valid = validator.validate_inventory(output_path)
        results = validator.get_results()

        # Should be valid with warnings about templated passwords
        self.assertTrue(is_valid)
        self.assertEqual(len(results['errors']), 0)
        # Should have warnings about parameterized passwords
        self.assertTrue(len(results['warnings']) > 0)
        self.assertTrue(any('parameterized' in warning for warning in results['warnings']))

    def test_generate_and_compare_with_reference(self):
        """Test generating inventory and comparing with a reference manually created inventory."""
        # Generate inventory
        generator = InventoryGenerator('containerized', 'growth')
        generated_path = os.path.join(self.temp_dir, 'generated_inventory')
        host = 'server.example.com'

        success = generator.generate_inventory(generated_path, host)
        self.assertTrue(success)

        # Create a reference inventory manually (without templates)
        reference_content = f"""[automationgateway]
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

postgresql_admin_password=testpass

registry_username=testuser
registry_password=testpass

redis_mode=standalone

gateway_admin_password=testpass
gateway_pg_host={host}
gateway_pg_password=testpass

controller_admin_password=testpass
controller_pg_host={host}
controller_pg_password=testpass
controller_percent_memory_capacity=0.5

hub_admin_password=testpass
hub_pg_host={host}
hub_pg_password=testpass
hub_seed_collections=false

eda_admin_password=testpass
eda_pg_host={host}
eda_pg_password=testpass
"""

        reference_path = os.path.join(self.temp_dir, 'reference_inventory')
        with open(reference_path, 'w') as f:
            f.write(reference_content)

        # Parse both inventories
        generated_sections, generated_vars = generator.parse_inventory(generated_path)
        ref_sections, ref_vars = generator.parse_inventory(reference_path)

        # Sections should be identical
        self.assertEqual(generated_sections, ref_sections)

        # Variables should have same keys, but generated will have templated values
        # Note: generated inventory may have additional variables like hub signing
        generated_keys = set(generated_vars.keys())
        ref_keys = set(ref_vars.keys())

        # All reference keys should be in generated
        missing_keys = ref_keys - generated_keys
        self.assertEqual(len(missing_keys), 0, f"Generated inventory missing keys: {missing_keys}")

        # Generated may have additional keys (like hub signing vars), that's ok

        # Non-password variables should match exactly
        non_password_vars = ['ansible_connection', 'redis_mode',
                             'controller_percent_memory_capacity', 'hub_seed_collections']
        non_password_vars.extend([f'{comp}_pg_host' for comp in ['gateway', 'controller', 'hub', 'eda']])

        for var in non_password_vars:
            self.assertEqual(generated_vars[var], ref_vars[var])

    def test_multiple_hosts_edge_cases(self):
        """Test generation with various host formats (hostnames and IPs)."""
        test_hosts = [
            'simple',
            'server.example.com',
            'complex-server-01.subdomain.example.org',
            '192.168.1.100',
            '2001:db8::1'
        ]

        for host in test_hosts:
            with self.subTest(host=host):
                generator = InventoryGenerator('containerized', 'growth')
                output_path = os.path.join(self.temp_dir, f'inventory_{host.replace(":", "_").replace(".", "_")}')

                success = generator.generate_inventory(output_path, host)
                self.assertTrue(success, f"Failed to generate inventory for host: {host}")

                # Verify the host appears in the file
                with open(output_path, 'r') as f:
                    content = f.read()
                self.assertIn(host, content)

                # Validate the generated inventory
                validator = InventoryValidator('containerized', 'growth')
                is_valid = validator.validate_inventory(output_path)
                self.assertTrue(is_valid, f"Generated inventory invalid for host: {host}")


if __name__ == '__main__':
    unittest.main()