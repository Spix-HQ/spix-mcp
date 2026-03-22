"""MCP session context and scope validation.

The MCP session context tracks:
- Session identity (name, ID)
- Allowed playbooks and channels
- Tool profile (safe vs full)
- Disabled tools

All tool calls are validated against the session scope BEFORE
dispatching to the backend API.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spix_mcp.client import SpixClient


@dataclass
class McpSessionContext:
    """Scoping and identity for an MCP session.

    Attributes:
        session_name: Human-readable name for this session (from --session-name).
        session_id: Auto-generated UUID for this session.
        default_playbook_id: Playbook used when --playbook is omitted in tool calls.
        allowed_playbook_ids: Set of playbook IDs this session can access.
            Empty set means all playbooks are allowed.
        allowed_channels: Set of channels this session can use (call, sms, email).
            Empty set means all channels are allowed.
        tool_profile: "safe" or "full" - controls which tools are exposed.
        disabled_tools: Set of tool paths explicitly disabled.
        client: The SpixClient for API calls.
    """

    session_name: str
    default_playbook_id: str | None
    allowed_playbook_ids: set[str]
    allowed_channels: set[str]
    tool_profile: str
    disabled_tools: set[str]
    client: SpixClient
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def validate_playbook_access(self, playbook_id: str | None) -> str | None:
        """Validate that the session can access the given playbook.

        Args:
            playbook_id: The playbook ID to validate. If None, uses default.

        Returns:
            The playbook ID to use (may be default if input was None).

        Raises:
            McpScopeError: If the playbook is not in the allowed set.
        """
        # Use default if not provided
        effective_playbook = playbook_id or self.default_playbook_id

        # If no allowed set, all playbooks are accessible
        if not self.allowed_playbook_ids:
            return effective_playbook

        # Check if the playbook is in the allowed set
        if effective_playbook and effective_playbook not in self.allowed_playbook_ids:
            raise McpScopeError(
                code="session_scope_violation",
                message=f"Playbook {effective_playbook} not in allowed set for this MCP session",
                playbook_id=effective_playbook,
                allowed=list(self.allowed_playbook_ids),
            )

        return effective_playbook

    def validate_channel_access(self, channel: str) -> None:
        """Validate that the session can use the given channel.

        Args:
            channel: The channel to validate (call, sms, email).

        Raises:
            McpScopeError: If the channel is not in the allowed set.
        """
        # If no allowed set, all channels are accessible
        if not self.allowed_channels:
            return

        if channel not in self.allowed_channels:
            raise McpScopeError(
                code="session_scope_violation",
                message=f"Channel '{channel}' not allowed for this MCP session",
                channel=channel,
                allowed=list(self.allowed_channels),
            )

    def validate_tool_access(self, tool_path: str) -> None:
        """Validate that the session can use the given tool.

        Args:
            tool_path: The tool path (e.g., "playbook.create").

        Raises:
            McpScopeError: If the tool is disabled.
        """
        if tool_path in self.disabled_tools:
            raise McpScopeError(
                code="tool_disabled",
                message=f"Tool '{tool_path}' is disabled for this MCP session",
                tool_path=tool_path,
            )

    async def register(self) -> None:
        """Register this MCP session with the backend for audit attribution.

        This creates a session record that allows tracing all actions
        back to this MCP session.
        """
        # Registration is optional - the backend may or may not support it
        # Fire and forget - don't fail if the endpoint doesn't exist
        try:
            await asyncio.to_thread(
                self.client.post,
                "/internal/mcp/sessions",
                json={
                    "session_id": self.session_id,
                    "session_name": self.session_name,
                    "default_playbook_id": self.default_playbook_id,
                    "allowed_playbook_ids": list(self.allowed_playbook_ids),
                    "allowed_channels": list(self.allowed_channels),
                    "tool_profile": self.tool_profile,
                },
            )
        except Exception as e:
            sys.stderr.write(f"MCP session registration failed: {e}\n")


class McpScopeError(Exception):
    """Error raised when an MCP operation violates session scope.

    Attributes:
        code: Error code (e.g., "session_scope_violation").
        message: Human-readable error message.
        details: Additional context about the scope violation.
    """

    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        """Convert to a dict suitable for JSON serialization."""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result
