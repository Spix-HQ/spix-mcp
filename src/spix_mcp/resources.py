"""MCP resource handler for reading resources via resource:// URIs.

MCP resources provide read-only access to Spix data. Resources are
accessed via resource:// URIs and return data from the backend API.

Example URIs:
- resource://calls/cse_001/transcript
- resource://playbooks/plb_call_abc123
- resource://billing/credits
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import orjson

if TYPE_CHECKING:
    from spix_mcp.session import McpSessionContext

from spix_mcp.registry import MCP_RESOURCES, CommandSchema


# URI pattern to endpoint mapping
# Maps resource:// URI patterns to their corresponding API endpoints
RESOURCE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Call resources
    (re.compile(r"^resource://calls/([^/]+)/transcript$"), "/calls/{0}/transcript"),
    (re.compile(r"^resource://calls/([^/]+)/summary$"), "/calls/{0}/summary"),
    # SMS resources
    (re.compile(r"^resource://sms/([^/]+)/thread$"), "/sms/threads/{0}"),
    # Playbook resources
    (re.compile(r"^resource://playbooks?/([^/]+)$"), "/playbooks/{0}"),
    # Contact resources
    (re.compile(r"^resource://contacts?/([^/]+)/history$"), "/contacts/{0}/history"),
    (re.compile(r"^resource://contacts?/([^/]+)$"), "/contacts/{0}"),
    # Phone resources
    (re.compile(r"^resource://phone/([^/]+)/route$"), "/phone/numbers/{0}/route"),
    # Billing resources
    (re.compile(r"^resource://billing/credits$"), "/billing/credits"),
    (re.compile(r"^resource://billing$"), "/billing"),
]


def parse_resource_uri(uri: str) -> tuple[str, dict] | None:
    """Parse a resource:// URI into an API endpoint and parameters.

    Args:
        uri: The resource URI (e.g., "resource://calls/cse_001/transcript").

    Returns:
        Tuple of (endpoint, params) if the URI matches a known pattern,
        None otherwise.
    """
    # Parse any query parameters
    parsed = urlparse(uri)
    query_params = parse_qs(parsed.query)
    # Flatten single-value params
    params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}

    # Reconstruct URI without query string for pattern matching
    uri_without_query = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    for pattern, endpoint_template in RESOURCE_PATTERNS:
        match = pattern.match(uri_without_query)
        if match:
            # Substitute captured groups into endpoint
            endpoint = endpoint_template
            for i, group in enumerate(match.groups()):
                endpoint = endpoint.replace(f"{{{i}}}", group)
            return endpoint, params

    return None


def get_resource_schema_by_uri(uri: str) -> CommandSchema | None:
    """Find the CommandSchema that matches a resource URI.

    Args:
        uri: The resource URI.

    Returns:
        The matching CommandSchema, or None if not found.
    """
    result = parse_resource_uri(uri)
    if not result:
        return None

    endpoint, _ = result

    # Find matching schema by endpoint pattern
    for schema in MCP_RESOURCES:
        # Check if the endpoint matches (accounting for path parameters)
        schema_pattern = re.sub(r"\{[^}]+\}", r"[^/]+", schema.api_endpoint)
        if re.match(f"^{schema_pattern}$", endpoint):
            return schema

    return None


async def create_resource_handler(
    session: McpSessionContext,
    uri: str,
) -> list:
    """Read an MCP resource by URI and return its contents.

    This function:
    1. Parses the resource URI
    2. Maps it to an API endpoint
    3. Fetches data from the backend
    4. Returns the response as MCP TextContent

    Args:
        session: The MCP session context.
        uri: The resource URI (e.g., "resource://calls/cse_001/transcript").

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

    # Parse the URI
    result = parse_resource_uri(uri)
    if not result:
        return [
            TextContent(
                type="text",
                text=orjson.dumps(
                    {"ok": False, "error": {"code": "invalid_resource_uri", "message": f"Unknown resource URI: {uri}"}}
                ).decode(),
            )
        ]

    endpoint, params = result

    # Validate playbook access if the URI references a playbook
    from spix_mcp.session import McpScopeError

    playbook_match = re.search(r"resource://playbooks?/([^/]+)", uri)
    if playbook_match:
        playbook_id = playbook_match.group(1)
        try:
            session.validate_playbook_access(playbook_id)
        except McpScopeError:
            return [
                TextContent(
                    type="text",
                    text=orjson.dumps(
                        {
                            "ok": False,
                            "error": {
                                "code": "session_scope_violation",
                                "message": f"Playbook {playbook_id} not in allowed set for this MCP session",
                            },
                        }
                    ).decode(),
                )
            ]

    # Fetch from backend API
    client = session.client

    try:
        response = await asyncio.to_thread(client.get, endpoint, params=params if params else None)
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=orjson.dumps({"ok": False, "error": {"code": "resource_fetch_error", "message": str(e)}}).decode(),
            )
        ]

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

    # Check playbook scope on response data (catches resources like call transcripts
    # that belong to a playbook but aren't accessed via playbook URIs)
    if session and session.allowed_playbook_ids:
        data = response.data or {}
        resource_playbook = data.get("playbook_id") if isinstance(data, dict) else None
        if resource_playbook and resource_playbook not in session.allowed_playbook_ids:
            return [
                TextContent(
                    type="text",
                    text="Error: Access denied — resource belongs to a restricted playbook.",
                )
            ]

    return [TextContent(type="text", text=orjson.dumps(envelope).decode())]


def list_available_resources() -> list[dict]:
    """List all available resource URIs and their descriptions.

    Returns:
        List of dicts with 'uri_template' and 'description' keys.
    """
    return [
        {
            "uri_template": "resource://calls/{session_id}/transcript",
            "description": "Call transcript",
        },
        {
            "uri_template": "resource://calls/{session_id}/summary",
            "description": "Call summary",
        },
        {
            "uri_template": "resource://sms/{thread_id}/thread",
            "description": "SMS conversation thread",
        },
        {
            "uri_template": "resource://playbook/{playbook_id}",
            "description": "Playbook details",
        },
        {
            "uri_template": "resource://contact/{contact_id}/history",
            "description": "Contact communication history",
        },
        {
            "uri_template": "resource://contact/{contact_id}",
            "description": "Contact details",
        },
        {
            "uri_template": "resource://phone/{number}/route",
            "description": "Phone number routing bindings",
        },
        {
            "uri_template": "resource://billing/credits",
            "description": "Credit balance",
        },
        {
            "uri_template": "resource://billing",
            "description": "Billing summary",
        },
    ]
