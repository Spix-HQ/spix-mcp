"""MCP tool handler for dispatching tool calls to the backend API.

This module maps MCP tool names to backend API endpoints and handles:
- Tool name to endpoint mapping
- Parameter conversion
- Session scope validation
- Response formatting
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from spix_mcp.session import McpSessionContext

from spix_mcp.registry import COMMAND_REGISTRY, CommandSchema


def get_schema_by_tool_name(tool_name: str) -> CommandSchema | None:
    """Look up a CommandSchema by MCP tool name.

    MCP tool names follow the pattern: spix_{path with dots replaced by underscores}
    e.g., "spix_playbook_create" -> "playbook.create"

    Args:
        tool_name: The MCP tool name (e.g., "spix_playbook_create").

    Returns:
        The matching CommandSchema, or None if not found.
    """
    # Remove the spix_ prefix
    if not tool_name.startswith("spix_"):
        return None

    path_part = tool_name[len("spix_") :]

    # Convert underscores back to dots for path lookup
    # We need to handle multi-part paths like "billing_credits_history" -> "billing.credits.history"
    # Try different dot positions to find the right one
    for cmd in COMMAND_REGISTRY:
        # Convert the command path to expected tool name format
        expected_tool = cmd.path.replace(".", "_")
        if expected_tool == path_part:
            return cmd

    return None


def build_endpoint_url(schema: CommandSchema, arguments: dict) -> tuple[str, dict]:
    """Build the API endpoint URL with path parameters substituted.

    Args:
        schema: The command schema.
        arguments: The tool arguments.

    Returns:
        Tuple of (endpoint_url, remaining_arguments).
        Path parameters are removed from arguments and substituted into the URL.
    """
    endpoint = schema.api_endpoint
    remaining_args = dict(arguments)

    # Substitute path parameters
    for param in schema.positional_args:
        placeholder = f"{{{param.name}}}"
        if placeholder in endpoint and param.name in remaining_args:
            endpoint = endpoint.replace(placeholder, str(remaining_args.pop(param.name)))

    return endpoint, remaining_args


def infer_channel_from_tool(tool_path: str) -> str | None:
    """Infer the channel type from a tool path.

    Args:
        tool_path: The tool path (e.g., "call.create", "sms.send").

    Returns:
        The channel ("call", "sms", "email") or None if not applicable.
    """
    if tool_path.startswith("call."):
        return "call"
    if tool_path.startswith("sms."):
        return "sms"
    if tool_path.startswith("email."):
        return "email"
    return None


async def create_tool_handler(
    session: McpSessionContext,
    tool_name: str,
    arguments: dict,
) -> list:
    """Execute an MCP tool call by dispatching to the backend API.

    This function:
    1. Resolves the tool name to a command schema
    2. Validates session scope (playbook access, channel access)
    3. Builds the API request
    4. Dispatches to the backend
    5. Returns the response as MCP TextContent

    Args:
        session: The MCP session context for scope validation.
        tool_name: The MCP tool name (e.g., "spix_playbook_create").
        arguments: The tool arguments from the MCP client.

    Returns:
        List containing a single TextContent with the JSON response.
    """
    # Import here to avoid circular imports and handle missing mcp package
    try:
        from mcp.types import TextContent
    except ImportError:
        # Fallback for when mcp is not installed
        class TextContent:  # type: ignore[no-redef]
            def __init__(self, type: str, text: str) -> None:
                self.type = type
                self.text = text

    # Resolve tool name to schema
    schema = get_schema_by_tool_name(tool_name)
    if not schema:
        return [
            TextContent(
                type="text",
                text=orjson.dumps(
                    {"ok": False, "error": {"code": "unknown_tool", "message": f"Unknown tool: {tool_name}"}}
                ).decode(),
            )
        ]

    # Validate tool access (not disabled)
    try:
        session.validate_tool_access(schema.path)
    except Exception as e:
        from spix_mcp.session import McpScopeError

        if isinstance(e, McpScopeError):
            return [TextContent(type="text", text=orjson.dumps({"ok": False, "error": e.to_dict()}).decode())]
        raise

    # Validate channel access if applicable
    channel = infer_channel_from_tool(schema.path)
    if channel:
        try:
            session.validate_channel_access(channel)
        except Exception as e:
            from spix_mcp.session import McpScopeError

            if isinstance(e, McpScopeError):
                return [TextContent(type="text", text=orjson.dumps({"ok": False, "error": e.to_dict()}).decode())]
            raise

    # Handle playbook_id: validate and apply default
    playbook_id = arguments.get("playbook_id")
    try:
        effective_playbook = session.validate_playbook_access(playbook_id)
        if effective_playbook and not playbook_id:
            # Apply default playbook
            arguments["playbook_id"] = effective_playbook
    except Exception as e:
        from spix_mcp.session import McpScopeError

        if isinstance(e, McpScopeError):
            return [TextContent(type="text", text=orjson.dumps({"ok": False, "error": e.to_dict()}).decode())]
        raise

    # Build endpoint URL with path parameters
    endpoint, remaining_args = build_endpoint_url(schema, arguments)

    # Dispatch to backend API
    client = session.client
    method = schema.http_method.lower()

    if method == "get":
        response = await asyncio.to_thread(client.get, endpoint, params=remaining_args if remaining_args else None)
    elif method == "post":
        response = await asyncio.to_thread(client.post, endpoint, json=remaining_args if remaining_args else None)
    elif method == "patch":
        response = await asyncio.to_thread(client.patch, endpoint, json=remaining_args if remaining_args else None)
    elif method == "delete":
        response = await asyncio.to_thread(client.delete, endpoint, params=remaining_args if remaining_args else None)
    else:
        response = await asyncio.to_thread(client.get, endpoint)

    # Build response envelope
    envelope: dict = {"ok": response.ok, "meta": response.meta}
    if response.ok:
        envelope["data"] = response.data
        if response.pagination:
            envelope["pagination"] = response.pagination
        if response.warnings:
            envelope["warnings"] = response.warnings
    else:
        envelope["error"] = response.error

    return [TextContent(type="text", text=orjson.dumps(envelope).decode())]
