import json
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

import httpx
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables configuration
ANSIBLE_BASE_URL = os.getenv("ANSIBLE_BASE_URL", "")
ANSIBLE_TOKEN = os.getenv("ANSIBLE_TOKEN", "")
AAP_VERSION = os.getenv("AAP_VERSION")
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0") 
MCP_PORT = int(os.getenv("MCP_PORT", "8200"))

if not ANSIBLE_BASE_URL:
    raise ValueError("ANSIBLE_BASE_URL environment variable is required")
if not ANSIBLE_TOKEN:
    raise ValueError("ANSIBLE_TOKEN environment variable is required")

# Initialize FastMCP server
mcp = FastMCP("Ansible Job Template Server")

# Global variables to cache job templates
job_templates_cache: List[Dict[str, Any]] = []
templates_last_fetched: Optional[float] = None
CACHE_TTL = 300  # 5 minutes cache TTL


def parse_extra_vars(extra_vars: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parse and validate extra_vars JSON string with improved error handling.
    
    Args:
        extra_vars: JSON string to parse
        
    Returns:
        Parsed dictionary or None if extra_vars is None/empty
        
    Raises:
        ValueError: If JSON is invalid with detailed error message
    """
    if not extra_vars:
        return None
        
    try:
        # Log the raw extra_vars for debugging
        logger.debug(f"Raw extra_vars received: {repr(extra_vars)}")
        
        # Clean up common issues with malformed JSON
        cleaned_extra_vars = extra_vars.strip()
        
        # Handle empty strings after stripping
        if not cleaned_extra_vars:
            return None
        
        # Handle case where it might be a JavaScript object string
        if cleaned_extra_vars.startswith("[object Object]"):
            # Extract the JSON part after [object Object]
            json_part = cleaned_extra_vars.replace("[object Object]", "").strip()
            if json_part:
                cleaned_extra_vars = json_part
                logger.debug(f"Cleaned [object Object] prefix, extracted: {repr(cleaned_extra_vars)}")
            else:
                # If nothing left after removing [object Object], return None
                return None
        
        parsed_extra_vars = json.loads(cleaned_extra_vars)
        logger.debug(f"Successfully parsed extra_vars: {parsed_extra_vars}")
        return parsed_extra_vars
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed for extra_vars: {repr(extra_vars)}")
        logger.error(f"JSON error: {e}")
        raise ValueError(f"Invalid JSON in extra_vars: {e}. Received: {repr(extra_vars)}")


class AnsibleClient:
    """Client for interacting with Ansible AWX/Controller API"""
    
    def __init__(self, base_url: str, token: str, aap_version: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.aap_version = aap_version
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Set API prefix based on AAP version
        if aap_version == "2.4":
            self.api_prefix = "/api"
        else:
            self.api_prefix = "/api/controller"
        
        logger.info(f"Initialized Ansible client for AAP version {aap_version} with API prefix: {self.api_prefix}")
    
    async def get_job_templates(self, page_size: int = 200) -> List[Dict[str, Any]]:
        """Fetch all job templates from Ansible (handling pagination)"""
        all_templates = []
        page = 1
        total_count = None
        
        async with httpx.AsyncClient() as client:
            base_url = urljoin(self.base_url, f"{self.api_prefix}/v2/job_templates/")
            
            logger.info(f"Fetching job templates from {base_url} with page_size={page_size}")
            
            while True:
                # Construct URL with pagination parameters
                params = {
                    "page_size": page_size,
                    "page": page
                }
                
                logger.debug(f"Fetching page {page} (page_size={page_size})")
                
                try:
                    response = await client.get(base_url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    page_results = data.get("results", [])
                    
                    # Get total count from first page
                    if total_count is None:
                        total_count = data.get("count", 0)
                        logger.info(f"Total job templates available: {total_count}")
                    
                    all_templates.extend(page_results)
                    
                    logger.debug(f"Page {page}: {len(page_results)} templates, total fetched: {len(all_templates)}/{total_count}")
                    
                    # Check if we have more pages
                    if not data.get("next") or len(page_results) == 0:
                        break
                    
                    page += 1
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error fetching job templates page {page}: {e}")
                    if page == 1:
                        # If first page fails, re-raise the error
                        raise
                    else:
                        # If subsequent page fails, log and break (we have partial data)
                        logger.warning(f"Stopping pagination due to error on page {page}")
                        break
                except Exception as e:
                    logger.error(f"Unexpected error fetching job templates page {page}: {e}")
                    if page == 1:
                        raise
                    else:
                        break
            
            logger.info(f"Successfully fetched {len(all_templates)} job templates across {page-1} pages")
            return all_templates
    
    async def launch_job_template(self, template_id: int, extra_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Launch a specific job template"""
        async with httpx.AsyncClient() as client:
            url = urljoin(self.base_url, f"{self.api_prefix}/v2/job_templates/{template_id}/launch/")
            
            payload = {}
            if extra_vars:
                payload["extra_vars"] = extra_vars
            
            logger.info(f"Launching job template {template_id} at {url}")
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            return response.json()
    
    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get status of a specific job"""
        async with httpx.AsyncClient() as client:
            url = urljoin(self.base_url, f"{self.api_prefix}/v2/jobs/{job_id}/")
            
            logger.info(f"Getting job status for job {job_id}")
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
    
    async def get_job_template_survey_spec(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get survey specification for a specific job template"""
        async with httpx.AsyncClient() as client:
            url = urljoin(self.base_url, f"{self.api_prefix}/v2/job_templates/{template_id}/survey_spec/")
            
            logger.debug(f"Fetching survey spec for job template {template_id}")
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                survey_data = response.json()
                logger.debug(f"Successfully fetched survey spec for template {template_id}")
                return survey_data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Survey spec not found - this is normal for templates without surveys
                    logger.debug(f"No survey spec found for job template {template_id} (404)")
                    return None
                else:
                    logger.warning(f"Error fetching survey spec for template {template_id}: {e}")
                    raise
            except Exception as e:
                logger.warning(f"Unexpected error fetching survey spec for template {template_id}: {e}")
                return None
    
    async def get_job_stdout(self, job_id: int) -> str:
        """Get the stdout log of a specific job"""
        async with httpx.AsyncClient() as client:
            url = urljoin(self.base_url, f"{self.api_prefix}/v2/jobs/{job_id}/stdout/")
            
            logger.info(f"Fetching stdout log for job {job_id}")
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                # The stdout endpoint returns plain text, not JSON
                stdout_content = response.text
                logger.debug(f"Successfully fetched stdout log for job {job_id} ({len(stdout_content)} characters)")
                return stdout_content
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Job {job_id} not found or stdout not available")
                    raise ValueError(f"Job {job_id} not found or stdout log not available")
                else:
                    logger.error(f"Error fetching stdout for job {job_id}: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error fetching stdout for job {job_id}: {e}")
                raise


# Initialize Ansible client
ansible_client = AnsibleClient(ANSIBLE_BASE_URL, ANSIBLE_TOKEN, AAP_VERSION)


async def fetch_and_cache_templates():
    """Fetch job templates with their survey specs and cache them"""
    global job_templates_cache, templates_last_fetched
    import time
    
    try:
        # Fetch all job templates (with pagination)
        templates = await ansible_client.get_job_templates()
        logger.info(f"📋 Discovered {len(templates)} job templates total")
        
        # Fetch survey specs for each template
        logger.info("Fetching survey specifications for job templates...")
        templates_with_surveys = []
        survey_count = 0
        
        for template in templates:
            template_id = template.get("id")
            template_name = template.get("name", f"template_{template_id}")
            
            # Copy the template data
            enhanced_template = template.copy()
            
            try:
                # Fetch survey spec for this template
                survey_spec = await ansible_client.get_job_template_survey_spec(template_id)
                if survey_spec:
                    enhanced_template["survey_spec"] = survey_spec
                    survey_count += 1
                    logger.debug(f"Added survey spec for template '{template_name}' ({template_id})")
                else:
                    enhanced_template["survey_spec"] = None
                    logger.debug(f"No survey spec for template '{template_name}' ({template_id})")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch survey spec for template '{template_name}' ({template_id}): {e}")
                enhanced_template["survey_spec"] = None
            
            templates_with_surveys.append(enhanced_template)
        
        # Cache the enhanced templates
        job_templates_cache = templates_with_surveys
        templates_last_fetched = time.time()
        
        logger.info(f"Cached {len(templates_with_surveys)} job templates with {survey_count} survey specifications")
        return templates_with_surveys
        
    except Exception as e:
        logger.error(f"Failed to fetch job templates: {e}")
        raise


async def get_cached_templates():
    """Get job templates from cache or fetch if needed"""
    global job_templates_cache, templates_last_fetched
    import time
    
    current_time = time.time()
    
    # Check if cache is empty or expired
    if not job_templates_cache or not templates_last_fetched or (current_time - templates_last_fetched) > CACHE_TTL:
        await fetch_and_cache_templates()
    
    return job_templates_cache


@mcp.tool()
async def list_job_templates() -> List[Dict[str, Any]]:
    """
    List all available Ansible job templates.
    
    Note: Each job template is also available as a dedicated MCP tool 
    with the name pattern '{template_name}' for direct launching.
    
    Returns:
        List of job templates with their details including id, name, description, and variables.
    """
    templates = await get_cached_templates()
    
    # Return simplified template information
    result = []
    for template in templates:
        template_name = template.get("name", f"template_{template.get('id')}")
        import re
        tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', template_name.lower())
        tool_name = f"{tool_name}"
        
        # Get survey spec info if available
        survey_spec = template.get("survey_spec")
        survey_questions = []
        if survey_spec and isinstance(survey_spec, dict):
            spec_data = survey_spec.get("spec", [])
            if isinstance(spec_data, list):
                survey_questions = [
                    {
                        "variable": q.get("variable"),
                        "question_name": q.get("question_name"),
                        "type": q.get("type"),
                        "required": q.get("required", False),
                        "default": q.get("default", ""),
                        "choices": q.get("choices", []) if q.get("type") in ["multiplechoice", "multiselect"] else []
                    }
                    for q in spec_data if isinstance(q, dict)
                ]

        result.append({
            "id": template.get("id"),
            "name": template.get("name"),
            "description": template.get("description", ""),
            "survey_enabled": template.get("survey_enabled", False),
            "variables": template.get("extra_vars", ""),
            "ask_variables_on_launch": template.get("ask_variables_on_launch", False),
            "inventory": template.get("summary_fields", {}).get("inventory", {}),
            "project": template.get("summary_fields", {}).get("project", {}),
            "survey_questions": survey_questions,  # Include survey questions
            "has_survey": bool(survey_questions),  # Boolean flag for convenience
            "mcp_tool_name": tool_name,  # Include the MCP tool name
        })
    
    return result


# @mcp.tool()
async def launch_job_template(template_id: int, extra_vars: Optional[str] = None) -> Dict[str, Any]:
    """
    Launch an Ansible job template.
    
    Args:
        template_id: The ID of the job template to launch
        extra_vars: Optional JSON string of extra variables to pass to the job
    
    Returns:
        Job launch details including job ID and status.
    """
    # Parse extra_vars if provided
    parsed_extra_vars = parse_extra_vars(extra_vars)
    
    try:
        result = await ansible_client.launch_job_template(template_id, parsed_extra_vars)
        return {
            "job_id": result.get("job"),
            "status": "launched",
            "url": result.get("url", ""),
            "ignore_conflicts": result.get("ignore_conflicts", False),
            "job_type": result.get("job_type", ""),
        }
    except Exception as e:
        logger.error(f"Failed to launch job template {template_id}: {e}")
        raise


@mcp.tool()
async def get_job_status(job_id: int) -> Dict[str, Any]:
    """
    Get the status of a running or completed Ansible job.
    
    Args:
        job_id: The ID of the job to check
    
    Returns:
        Job status details including current state, progress, and results.
    """
    try:
        result = await ansible_client.get_job_status(job_id)
        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "status": result.get("status"),
            "started": result.get("started"),
            "finished": result.get("finished"),
            "elapsed": result.get("elapsed"),
            "job_template": result.get("job_template"),
            "inventory": result.get("inventory"),
            "project": result.get("project"),
            "playbook": result.get("playbook"),
            "artifacts": result.get("artifacts", {}),
            "result_stdout": result.get("result_stdout", ""),
        }
    except Exception as e:
        logger.error(f"Failed to get job status for job {job_id}: {e}")
        raise


@mcp.tool()
async def get_job_logs(job_id: int) -> Dict[str, Any]:
    """
    Get the stdout logs of a specific Ansible job.
    
    Args:
        job_id: The ID of the job to retrieve logs for
    
    Returns:
        Job logs with metadata including log content, job ID, and content length.
    """
    try:
        # First get job status to provide context
        job_status = await ansible_client.get_job_status(job_id)
        
        # Get the stdout logs
        stdout_content = await ansible_client.get_job_stdout(job_id)
        
        return {
            "job_id": job_id,
            "job_name": job_status.get("name", ""),
            "job_status": job_status.get("status", "unknown"),
            "template_name": job_status.get("summary_fields", {}).get("job_template", {}).get("name", ""),
            "started": job_status.get("started"),
            "finished": job_status.get("finished"),
            "stdout_content": stdout_content,
            "log_length": len(stdout_content),
            "log_lines": len(stdout_content.splitlines()) if stdout_content else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get job logs for job {job_id}: {e}")
        raise


@mcp.tool()
async def refresh_job_templates() -> Dict[str, str]:
    """
    Force refresh the job templates cache.
    
    Note: Dynamic tool recreation is not supported after server initialization.
    To get new tools for updated templates, restart the MCP server.
    
    Returns:
        Success message with count of templates refreshed.
    """
    try:
        templates = await fetch_and_cache_templates()
        
        # Note: We cannot recreate dynamic tools after server initialization in FastMCP
        # The tools created during server startup will remain available
        logger.info(f"Refreshed job templates cache with {len(templates)} templates")
        logger.info("Note: Dynamic tool recreation after server startup is not supported.")
        logger.info("To register new template tools, restart the MCP server.")
        
        return {
            "message": f"Successfully refreshed {len(templates)} job templates. Note: To get tools for new templates, restart the server."
        }
    except Exception as e:
        logger.error(f"Failed to refresh job templates: {e}")
        return {"error": f"Failed to refresh templates: {e}"}


def create_job_template_tool_with_decorator(template):
    """Create and register a dynamic tool for a specific job template using the proper decorator approach"""
    template_id = template.get("id")
    template_name = template.get("name", f"template_{template_id}")
    template_description = template.get("description", f"Launch job template: {template_name}")
    
    # Clean template name for tool name (replace spaces and special chars with underscores)
    import re
    tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', template_name.lower())
    tool_name = f"{tool_name}"

    # Get survey information
    survey_spec = template.get("survey_spec")
    survey_questions = []
    if survey_spec and isinstance(survey_spec, dict):
        spec_data = survey_spec.get("spec", [])
        if isinstance(spec_data, list):
            survey_questions = [q for q in spec_data if isinstance(q, dict)]
    
    # Build comprehensive documentation
    doc_parts = [f"{template_description}", f"Template ID: {template_id}"]
    
    if survey_questions:
        doc_parts.append(f"\nSurvey Questions ({len(survey_questions)} available):")
        for q in survey_questions:
            question_info = f"  - {q.get('variable', 'unknown')}: {q.get('question_name', 'No description')}"
            if q.get('required'):
                question_info += " (required)"
            if q.get('default'):
                question_info += f" [default: {q.get('default')}]"
            if q.get('choices'):
                question_info += f" [choices: {', '.join(q.get('choices'))}]"
            doc_parts.append(question_info)
                
        doc_parts.append("\nInclude survey answers in extra_vars JSON string.")
    else:
        doc_parts.append("\nNo survey questions defined for this template.")
    
    documentation = "\n".join(doc_parts)
    
    # Create and register the tool using the decorator approach
    @mcp.tool(name=tool_name, description=documentation)
    async def template_tool(extra_vars: Optional[str] = None) -> Dict[str, Any]:
        """Dynamically created tool for launching a job template."""
        # Parse extra_vars if provided
        parsed_extra_vars = parse_extra_vars(extra_vars)
        
        try:
            result = await ansible_client.launch_job_template(template_id, parsed_extra_vars)
            return {
                "job_id": result.get("job"),
                "status": "launched",
                "template_id": template_id,
                "template_name": template_name,
                "url": result.get("url", ""),
                "ignore_conflicts": result.get("ignore_conflicts", False),
                "job_type": result.get("job_type", ""),
            }
        except Exception as e:
            logger.error(f"Failed to launch job template {template_id} ({template_name}): {e}")
            raise
    
    return tool_name, template_tool


def create_job_template_tool(template):
    """Create a dynamic tool for a specific job template (for refresh functionality)"""
    template_id = template.get("id")
    template_name = template.get("name", f"template_{template_id}")
    template_description = template.get("description", f"Launch job template: {template_name}")
    
    # Clean template name for tool name (replace spaces and special chars with underscores)
    import re
    tool_name = re.sub(r'[^a-zA-Z0-9_]', '_', template_name.lower())
    tool_name = f"{tool_name}"

    # Get survey information
    survey_spec = template.get("survey_spec")
    survey_questions = []
    if survey_spec and isinstance(survey_spec, dict):
        spec_data = survey_spec.get("spec", [])
        if isinstance(spec_data, list):
            survey_questions = [q for q in spec_data if isinstance(q, dict)]
    
    # Create the tool function
    async def template_tool(extra_vars: Optional[str] = None) -> Dict[str, Any]:
        f"""
        Launch the {template_name} job template with optional extra variables.
        
        Args:
            extra_vars: Optional JSON string of extra variables to pass to the job.
                       {"Survey questions can be included in extra_vars:" if survey_questions else ""}
                       {chr(10).join([f"                       - {q.get('variable', 'unknown')}: {q.get('question_name', 'No description')} ({'required' if q.get('required') else 'optional'})" for q in survey_questions]) if survey_questions else ""}
        
        Returns:
            Job launch details including job ID and status.
        """
        # Parse extra_vars if provided
        parsed_extra_vars = parse_extra_vars(extra_vars)
        
        try:
            result = await ansible_client.launch_job_template(template_id, parsed_extra_vars)
            return {
                "job_id": result.get("job"),
                "status": "launched",
                "template_id": template_id,
                "template_name": template_name,
                "url": result.get("url", ""),
                "ignore_conflicts": result.get("ignore_conflicts", False),
                "job_type": result.get("job_type", ""),
            }
        except Exception as e:
            logger.error(f"Failed to launch job template {template_id} ({template_name}): {e}")
            raise
    
    # Set function metadata
    template_tool.__name__ = tool_name
    
    # Build comprehensive documentation
    doc_parts = [f"{template_description}", f"Template ID: {template_id}"]
    
    if survey_questions:
        doc_parts.append(f"\nSurvey Questions ({len(survey_questions)} available):")
        for q in survey_questions:
            question_info = f"  - {q.get('variable', 'unknown')}: {q.get('question_name', 'No description')}"
            if q.get('required'):
                question_info += " (required)"
            if q.get('default'):
                question_info += f" [default: {q.get('default')}]"
            if q.get('choices'):
                question_info += f" [choices: {', '.join(q.get('choices'))}]"
            doc_parts.append(question_info)
                
        doc_parts.append("\nInclude survey answers in extra_vars JSON string.")
    else:
        doc_parts.append("\nNo survey questions defined for this template.")
    
    template_tool.__doc__ = "\n".join(doc_parts)
    
    return template_tool


async def initialize_server():
    """Initialize the server by fetching job templates and creating dynamic tools"""
    logger.info("🚀 Starting Ansible MCP Server...")
    logger.info(f"📡 Connecting to Ansible instance: {ANSIBLE_BASE_URL}")
    
    try:
        # Fetch job templates from Ansible
        logger.info("📋 Fetching job templates from Ansible...")
        await fetch_and_cache_templates()
        logger.info(f"✅ Found {len(job_templates_cache)} job templates")
        
        # Create dynamic MCP tools for each job template
        logger.info("🔧 Creating dynamic MCP tools for job templates...")
        created_tools = 0
        for template in job_templates_cache:
            try:
                # Register the tool directly using the decorator approach during server initialization
                tool_name, tool_func = create_job_template_tool_with_decorator(template)
                created_tools += 1
                logger.debug(f"   ✓ Created tool: {tool_name} → '{template.get('name')}'")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to create tool for template {template.get('id', 'unknown')}: {e}")
        
        logger.info(f"🎉 Successfully created {created_tools} dynamic job template tools")
        logger.info(f"📚 Total MCP tools available: {created_tools + 5} (5 static + {created_tools} dynamic)")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Ansible connection: {e}")
        logger.info("⚠️  Server will continue with static tools only - dynamic job template tools unavailable")


def start():
    # Initialize the server before running
    try:
        import asyncio
        asyncio.run(initialize_server())
    except Exception as e:
        logger.warning(f"Failed to initialize server: {e}")
        logger.info("Server will start but templates may not be available until first request")
    
    # Run the server with the specified transport
    if MCP_TRANSPORT.lower() == "http":
        logger.info(f"Starting MCP server on http://{MCP_HOST}:{MCP_PORT}/mcp")
        mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT, path="/mcp")
    elif MCP_TRANSPORT.lower() == "sse":
        logger.info(f"Starting MCP server with SSE on {MCP_HOST}:{MCP_PORT}")
        mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)
    else:
        # Default to stdio transport
        logger.info("Starting MCP server with STDIO transport")
        mcp.run() 

if __name__ == "__main__":
    start()
