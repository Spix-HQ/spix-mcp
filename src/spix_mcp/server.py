"""MCP server implementation for Spix.

The MCP server exposes Spix capabilities to LLM agents via:
- Tools: Request-response actions (API calls)
- Resources: Readable state (transcripts, summaries, etc.)

The server uses the official Python MCP SDK and runs via stdio transport.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


async def run_mcp_server(
    api_key: str,
    session_name: str = "unnamed",
    default_playbook: str | None = None,
    allowed_playbooks: list[str] | None = None,
    allowed_channels: list[str] | None = None,
    tool_profile: str = "safe",
    disabled_tools: list[str] | None = None,
    port: int | None = None,  # Reserved for future SSE transport
) -> None:
    """Start the MCP server.

    This function runs until killed. It:
    1. Creates the session context
    2. Registers tools and resources
    3. Starts the stdio server
    4. Handles incoming requests

    Args:
        api_key: The Spix API key for backend requests.
        session_name: Human-readable name for this session.
        default_playbook: Default playbook ID for tool calls.
        allowed_playbooks: List of playbook IDs this session can access.
        allowed_channels: List of channels this session can use.
        tool_profile: "safe" or "full" - controls which tools are exposed.
        disabled_tools: List of tool paths to disable.
        port: Reserved for future SSE transport support.
    """
    # Import MCP SDK - give clear error if not installed
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Resource, TextContent, Tool
    except ImportError as e:
        sys.stderr.write(
            "Error: The 'mcp' package is required for MCP server functionality.\nInstall it with: pip install mcp\n"
        )
        raise SystemExit(1) from e

    from spix_mcp.client import SpixClient
    from spix_mcp.resources import create_resource_handler, list_available_resources
    from spix_mcp.session import McpSessionContext
    from spix_mcp.tools import create_tool_handler
    from spix_mcp.registry import build_json_schema, get_mcp_tools

    # Create the API client
    client = SpixClient(api_key=api_key)

    # Create session context
    session = McpSessionContext(
        session_name=session_name,
        default_playbook_id=default_playbook,
        allowed_playbook_ids=set(allowed_playbooks or []),
        allowed_channels=set(allowed_channels or []),
        tool_profile=tool_profile,
        disabled_tools=set(disabled_tools or []),
        client=client,
    )

    # Register session with backend (fire and forget)
    await session.register()

    # Build MCP server
    server = Server("spix")

    # ─── Tool Surface ─────────────────────────────────────────────────────────
    tool_schemas = get_mcp_tools(profile=tool_profile, disabled=disabled_tools)
    tool_defs: list[Tool] = []

    for schema in tool_schemas:
        # Convert path to tool name: playbook.create -> spix_playbook_create
        tool_name = f"spix_{schema.path.replace('.', '_')}"
        tool_defs.append(
            Tool(
                name=tool_name,
                description=schema.description or f"Spix {schema.path}",
                inputSchema=build_json_schema(schema),
            )
        )

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tool_defs

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
        result = await create_tool_handler(session, name, arguments)
        return result

    # ─── Resource Surface ─────────────────────────────────────────────────────

    @server.list_resources()
    async def list_resources_handler() -> list[Resource]:
        resources: list[Resource] = []
        for res in list_available_resources():
            resources.append(
                Resource(
                    uri=res["uri_template"],
                    name=res["description"],
                    description=res["description"],
                    mimeType="application/json",
                )
            )
        return resources

    @server.read_resource()
    async def read_resource(uri: str) -> Sequence[TextContent]:
        result = await create_resource_handler(session, uri)
        return result

    # ─── Run Server ───────────────────────────────────────────────────────────
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        # Clean up
        client.close()


def check_mcp_available() -> bool:
    """Check if the MCP package is available.

    Returns:
        True if mcp is importable, False otherwise.
    """
    try:
        import mcp  # noqa: F401

        return True
    except ImportError:
        return False
