"""Command schema registry for Spix CLI.

This registry is the source of truth for:
- CLI command definitions
- MCP tool generation
- MCP resource generation

NEVER hand-maintain the MCP tool list - it is generated from this registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CommandParam:
    """Schema for a command parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "enum", "file", "array"
    required: bool = False
    description: str = ""
    choices: list[str] = field(default_factory=list)
    default: object = None


@dataclass
class CommandSchema:
    """Schema for a CLI command.

    Each command maps to:
    - A Click command in the CLI
    - Optionally an MCP tool or resource
    """

    path: str  # e.g., "playbook.create", "call.show"
    cli_usage: str  # e.g., "spix playbook create"
    http_method: str  # "GET", "POST", "PATCH", "DELETE"
    api_endpoint: str  # e.g., "/playbooks", "/calls/{id}"
    params: list[CommandParam] = field(default_factory=list)
    positional_args: list[CommandParam] = field(default_factory=list)
    mcp_expose: Literal["tool", "resource", None] = None
    mcp_profile: Literal["safe", "full"] = "safe"  # "safe" = included in both profiles
    destructive: bool = False
    financial: bool = False
    description: str = ""


# ─── Command Registry ─────────────────────────────────────────────────────────
# At least 30 entries covering the most important commands.
# This is the source of truth for MCP tool/resource generation.

COMMAND_REGISTRY: list[CommandSchema] = [
    # ─── Playbook Commands ────────────────────────────────────────────────────
    CommandSchema(
        path="playbook.create",
        cli_usage="spix playbook create --type <call|sms> --name <n>",
        http_method="POST",
        api_endpoint="/playbooks",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Create a new call or SMS playbook",
        params=[
            CommandParam("type", "enum", required=True, choices=["call", "sms"], description="Playbook type"),
            CommandParam("name", "string", required=True, description="Playbook name"),
            CommandParam("goal", "string", description="Call playbook goal"),
            CommandParam("persona", "string", description="AI persona description"),
            CommandParam("briefing", "string", description="Playbook briefing text"),
            CommandParam("context", "string", description="Playbook context"),
            CommandParam("voice_id", "uuid", description="Voice UUID for TTS"),
            CommandParam("language", "string", description="Language code (e.g. en, es, fr)"),
            CommandParam("default_emotion", "string", description="Default TTS emotion"),
            CommandParam("speaking_rate", "number", description="Speaking rate (0.6-1.5)"),
            CommandParam("tts_volume", "number", description="TTS volume (0.5-2.0)"),
            CommandParam("max_duration_sec", "integer", description="Max call duration in seconds"),
            CommandParam("record", "boolean", default=True, description="Record calls"),
            CommandParam(
                "amd_action",
                "enum",
                choices=["hang_up", "voicemail_leave_message", "retry_later"],
                description="Answering machine detection action",
            ),
        ],
    ),
    CommandSchema(
        path="playbook.list",
        cli_usage="spix playbook list [--type call|sms] [--status <s>]",
        http_method="GET",
        api_endpoint="/playbooks",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List playbooks",
        params=[
            CommandParam("type", "enum", choices=["call", "sms"], description="Filter by type"),
            CommandParam(
                "status",
                "enum",
                choices=["active", "pending", "paused", "suspended", "rejected"],
                description="Filter by status",
            ),
            CommandParam("limit", "integer", default=50, description="Number of results"),
            CommandParam("cursor", "string", description="Pagination cursor"),
        ],
    ),
    CommandSchema(
        path="playbook.show",
        cli_usage="spix playbook show <playbook_id>",
        http_method="GET",
        api_endpoint="/playbooks/{playbook_id}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show playbook details",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="playbook.update",
        cli_usage="spix playbook update <playbook_id> [--name <n>] [--goal <g>]",
        http_method="PATCH",
        api_endpoint="/playbooks/{playbook_id}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Update playbook configuration",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
        params=[
            CommandParam("name", "string", description="New playbook name"),
            CommandParam("goal", "string", description="New goal"),
            CommandParam("persona", "string", description="AI persona description"),
            CommandParam("briefing", "string", description="Playbook briefing text"),
            CommandParam("context", "string", description="New context"),
            CommandParam("voice_id", "uuid", description="Voice UUID for TTS"),
            CommandParam("language", "string", description="Language code"),
            CommandParam("default_emotion", "string", description="Default TTS emotion"),
            CommandParam("speaking_rate", "number", description="Speaking rate (0.6-1.5)"),
            CommandParam("tts_volume", "number", description="TTS volume (0.5-2.0)"),
        ],
    ),
    CommandSchema(
        path="playbook.delete",
        cli_usage="spix playbook delete <playbook_id>",
        http_method="DELETE",
        api_endpoint="/playbooks/{playbook_id}",
        mcp_expose="tool",
        mcp_profile="full",  # Destructive - full profile only
        destructive=True,
        description="Delete a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="playbook.pause",
        cli_usage="spix playbook pause <playbook_id>",
        http_method="POST",
        api_endpoint="/playbooks/{playbook_id}/pause",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Pause a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="playbook.resume",
        cli_usage="spix playbook resume <playbook_id>",
        http_method="POST",
        api_endpoint="/playbooks/{playbook_id}/resume",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Resume a paused playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="playbook.clone",
        cli_usage="spix playbook clone <playbook_id> --name <n>",
        http_method="POST",
        api_endpoint="/playbooks/{playbook_id}/clone",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Clone an existing playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID to clone"),
        ],
        params=[
            CommandParam("name", "string", required=True, description="Name for the cloned playbook"),
        ],
    ),
    CommandSchema(
        path="playbook.voice.list",
        cli_usage="spix playbook voice list [--language <code>]",
        http_method="GET",
        api_endpoint="/playbooks/voices",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List available voices",
        params=[
            CommandParam("language", "string", description="Filter by language code"),
        ],
    ),
    CommandSchema(
        path="playbook.language.list",
        cli_usage="spix playbook language list",
        http_method="GET",
        api_endpoint="/playbooks/languages",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List supported languages",
    ),
    CommandSchema(
        path="playbook.emotion.list",
        cli_usage="spix playbook emotion list",
        http_method="GET",
        api_endpoint="/playbooks/emotions",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List supported TTS emotions",
    ),
    CommandSchema(
        path="playbook.rule.list",
        cli_usage="spix playbook rule list <playbook_id>",
        http_method="GET",
        api_endpoint="/playbooks/{playbook_id}/rules",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List rules for a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="playbook.rule.add",
        cli_usage="spix playbook rule add <playbook_id> --type <guardrail|objection>",
        http_method="POST",
        api_endpoint="/playbooks/{playbook_id}/rules",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Add rule(s) to a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
        params=[
            CommandParam("type", "enum", required=True, choices=["guardrail", "objection"], description="Rule type"),
            CommandParam("rule", "string", description="Guardrail rule text"),
            CommandParam("priority", "enum", choices=["hard", "soft"], description="Guardrail priority"),
            CommandParam("trigger", "string", description="Objection trigger phrase"),
            CommandParam("response", "string", description="Objection response text"),
        ],
    ),
    CommandSchema(
        path="playbook.rule.remove",
        cli_usage="spix playbook rule remove <playbook_id> --id <rule_id>",
        http_method="DELETE",
        api_endpoint="/playbooks/{playbook_id}/rules/{rule_id}",
        mcp_expose="tool",
        mcp_profile="full",
        destructive=True,
        description="Remove a rule from a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
            CommandParam("rule_id", "string", required=True, description="Rule ID"),
        ],
    ),
    CommandSchema(
        path="playbook.rule.clear",
        cli_usage="spix playbook rule clear <playbook_id>",
        http_method="DELETE",
        api_endpoint="/playbooks/{playbook_id}/rules",
        mcp_expose="tool",
        mcp_profile="full",
        destructive=True,
        description="Remove all rules from a playbook",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    # ─── Call Commands ────────────────────────────────────────────────────────
    CommandSchema(
        path="call.create",
        cli_usage="spix call create <to> --playbook <id> --sender <number>",
        http_method="POST",
        api_endpoint="/calls",
        mcp_expose="tool",
        mcp_profile="safe",
        financial=True,
        description="Initiate a voice call",
        positional_args=[
            CommandParam("to", "string", required=True, description="Destination phone number (E.164)"),
        ],
        params=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
            CommandParam("sender", "string", required=True, description="Sender number (E.164)"),
            CommandParam("contact_id", "string", description="Link to existing contact"),
            CommandParam("webhook_url", "string", description="Override webhook URL"),
        ],
    ),
    CommandSchema(
        path="call.list",
        cli_usage="spix call list [--playbook <id>] [--status <s>]",
        http_method="GET",
        api_endpoint="/calls",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List call sessions",
        params=[
            CommandParam("playbook_id", "string", description="Filter by playbook"),
            CommandParam(
                "status",
                "enum",
                choices=["queued", "dialing", "ringing", "in_progress", "completed", "failed", "cancelled"],
                description="Filter by status",
            ),
            CommandParam("limit", "integer", default=50, description="Number of results"),
            CommandParam("cursor", "string", description="Pagination cursor"),
        ],
    ),
    CommandSchema(
        path="call.show",
        cli_usage="spix call show <session_id>",
        http_method="GET",
        api_endpoint="/calls/{session_id}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show call session details",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    CommandSchema(
        path="call.transcript",
        cli_usage="spix call transcript <session_id>",
        http_method="GET",
        api_endpoint="/calls/{session_id}/transcript",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Get call transcript",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    CommandSchema(
        path="call.summary",
        cli_usage="spix call summary <session_id>",
        http_method="GET",
        api_endpoint="/calls/{session_id}/summary",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Get AI-generated call summary",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    CommandSchema(
        path="call.cancel",
        cli_usage="spix call cancel <session_id>",
        http_method="POST",
        api_endpoint="/calls/{session_id}/cancel",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Cancel an in-progress call",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    # ─── SMS Commands ─────────────────────────────────────────────────────────
    CommandSchema(
        path="sms.send",
        cli_usage="spix sms send <to> --sender <number> --body <text>",
        http_method="POST",
        api_endpoint="/sms",
        mcp_expose="tool",
        mcp_profile="safe",
        financial=True,
        description="Send an SMS message",
        positional_args=[
            CommandParam("to", "string", required=True, description="Destination phone number (E.164)"),
        ],
        params=[
            CommandParam("sender", "string", required=True, description="Sender number (E.164)"),
            CommandParam("body", "string", required=True, description="Message body"),
            CommandParam("playbook_id", "string", description="Playbook ID"),
            CommandParam("contact_id", "string", description="Link to existing contact"),
        ],
    ),
    CommandSchema(
        path="sms.list",
        cli_usage="spix sms list [--playbook <id>]",
        http_method="GET",
        api_endpoint="/sms",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List SMS messages",
        params=[
            CommandParam("playbook_id", "string", description="Filter by playbook"),
            CommandParam("direction", "enum", choices=["inbound", "outbound"], description="Filter by direction"),
            CommandParam("limit", "integer", default=50, description="Number of results"),
            CommandParam("cursor", "string", description="Pagination cursor"),
        ],
    ),
    CommandSchema(
        path="sms.thread",
        cli_usage="spix sms thread <thread_id>",
        http_method="GET",
        api_endpoint="/sms/threads/{thread_id}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show SMS conversation thread",
        positional_args=[
            CommandParam("thread_id", "string", required=True, description="Thread ID"),
        ],
    ),
    # ─── Phone Commands ───────────────────────────────────────────────────────
    CommandSchema(
        path="phone.list",
        cli_usage="spix phone list",
        http_method="GET",
        api_endpoint="/phone/numbers",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List phone numbers",
        params=[
            CommandParam("limit", "integer", default=50, description="Number of results"),
        ],
    ),
    CommandSchema(
        path="phone.show",
        cli_usage="spix phone show <number>",
        http_method="GET",
        api_endpoint="/phone/numbers/{number}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show phone number details",
        positional_args=[
            CommandParam("number", "string", required=True, description="Phone number (E.164)"),
        ],
    ),
    CommandSchema(
        path="phone.bind",
        cli_usage="spix phone bind <number> --playbook <id>",
        http_method="POST",
        api_endpoint="/phone/numbers/{number}/bind",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Bind phone number to playbook",
        positional_args=[
            CommandParam("number", "string", required=True, description="Phone number (E.164)"),
        ],
        params=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID to bind"),
        ],
    ),
    CommandSchema(
        path="phone.unbind",
        cli_usage="spix phone unbind <number> --playbook <id>",
        http_method="POST",
        api_endpoint="/phone/numbers/{number}/unbind",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Unbind phone number from playbook",
        positional_args=[
            CommandParam("number", "string", required=True, description="Phone number (E.164)"),
        ],
        params=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID to unbind"),
        ],
    ),
    CommandSchema(
        path="phone.release",
        cli_usage="spix phone release <number>",
        http_method="DELETE",
        api_endpoint="/phone/numbers/{number}",
        mcp_expose="tool",
        mcp_profile="full",  # Destructive - full profile only
        destructive=True,
        description="Release a phone number",
        positional_args=[
            CommandParam("number", "string", required=True, description="Phone number (E.164)"),
        ],
    ),
    # ─── Email Commands ───────────────────────────────────────────────────────
    CommandSchema(
        path="email.send",
        cli_usage="spix email send --from <addr> --to <addr> --subject <s> --body <b>",
        http_method="POST",
        api_endpoint="/email",
        mcp_expose="tool",
        mcp_profile="safe",
        financial=True,
        description="Send an email",
        params=[
            CommandParam("from_address", "string", required=True, description="Sender email address"),
            CommandParam("to", "string", required=True, description="Recipient email address"),
            CommandParam("subject", "string", required=True, description="Email subject"),
            CommandParam("body", "string", required=True, description="Email body (plain text or HTML)"),
            CommandParam("reply_to", "string", description="Reply-to address"),
        ],
    ),
    CommandSchema(
        path="email.reply",
        cli_usage="spix email reply <email_id> --body <b>",
        http_method="POST",
        api_endpoint="/email/{email_id}/reply",
        mcp_expose="tool",
        mcp_profile="safe",
        financial=True,
        description="Reply to an email",
        positional_args=[
            CommandParam("email_id", "string", required=True, description="Email ID to reply to"),
        ],
        params=[
            CommandParam("body", "string", required=True, description="Reply body"),
        ],
    ),
    CommandSchema(
        path="email.list",
        cli_usage="spix email list [--inbox <id>]",
        http_method="GET",
        api_endpoint="/email",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List emails",
        params=[
            CommandParam("inbox_id", "string", description="Filter by inbox"),
            CommandParam("direction", "enum", choices=["inbound", "outbound"], description="Filter by direction"),
            CommandParam("limit", "integer", default=50, description="Number of results"),
        ],
    ),
    # ─── Contact Commands ─────────────────────────────────────────────────────
    CommandSchema(
        path="contact.create",
        cli_usage="spix contact create --name <n> --phone <p>",
        http_method="POST",
        api_endpoint="/contacts",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Create a new contact",
        params=[
            CommandParam("name", "string", required=True, description="Contact name"),
            CommandParam("phone", "string", description="Phone number (E.164)"),
            CommandParam("email", "string", description="Email address"),
            CommandParam("tags", "array", description="Tags for the contact"),
        ],
    ),
    CommandSchema(
        path="contact.list",
        cli_usage="spix contact list [--tag <t>]",
        http_method="GET",
        api_endpoint="/contacts",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List contacts",
        params=[
            CommandParam("tag", "string", description="Filter by tag"),
            CommandParam("limit", "integer", default=50, description="Number of results"),
            CommandParam("cursor", "string", description="Pagination cursor"),
        ],
    ),
    CommandSchema(
        path="contact.show",
        cli_usage="spix contact show <contact_id>",
        http_method="GET",
        api_endpoint="/contacts/{contact_id}",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show contact details",
        positional_args=[
            CommandParam("contact_id", "string", required=True, description="Contact ID"),
        ],
    ),
    CommandSchema(
        path="contact.history",
        cli_usage="spix contact history <contact_id>",
        http_method="GET",
        api_endpoint="/contacts/{contact_id}/history",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show contact communication history",
        positional_args=[
            CommandParam("contact_id", "string", required=True, description="Contact ID"),
        ],
    ),
    CommandSchema(
        path="contact.summary",
        cli_usage="spix contact summary <contact_id>",
        http_method="GET",
        api_endpoint="/contacts/{contact_id}/summary",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Get AI-generated contact summary",
        positional_args=[
            CommandParam("contact_id", "string", required=True, description="Contact ID"),
        ],
    ),
    CommandSchema(
        path="contact.tag",
        cli_usage="spix contact tag <contact_id> --add <t> --remove <t>",
        http_method="POST",
        api_endpoint="/contacts/{contact_id}/tags",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Add or remove tags from a contact",
        positional_args=[
            CommandParam("contact_id", "string", required=True, description="Contact ID"),
        ],
        params=[
            CommandParam("add", "array", description="Tags to add"),
            CommandParam("remove", "array", description="Tags to remove"),
        ],
    ),
    # ─── Billing Commands ─────────────────────────────────────────────────────
    CommandSchema(
        path="billing.status",
        cli_usage="spix billing",
        http_method="GET",
        api_endpoint="/billing",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show billing summary",
    ),
    CommandSchema(
        path="billing.credits",
        cli_usage="spix billing credits",
        http_method="GET",
        api_endpoint="/billing/credits",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show credit balance",
    ),
    CommandSchema(
        path="billing.credits.history",
        cli_usage="spix billing credits history",
        http_method="GET",
        api_endpoint="/billing/credits/history",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show credit usage history",
        params=[
            CommandParam("limit", "integer", default=50, description="Number of results"),
        ],
    ),
    CommandSchema(
        path="billing.plan.set",
        cli_usage="spix billing plan set --plan <plan>",
        http_method="POST",
        api_endpoint="/billing/plan",
        mcp_expose="tool",
        mcp_profile="full",  # Destructive billing - full profile only
        destructive=True,
        financial=True,
        description="Change subscription plan (returns Stripe checkout URL)",
        params=[
            CommandParam(
                "plan",
                "enum",
                required=True,
                choices=["sandbox", "agent", "operator", "fleet"],
                description="Plan to switch to",
            ),
        ],
    ),
    # ─── Webhook Commands ─────────────────────────────────────────────────────
    CommandSchema(
        path="webhook.endpoint.create",
        cli_usage="spix webhook endpoint create --url <url>",
        http_method="POST",
        api_endpoint="/webhooks/endpoints",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Create a webhook endpoint",
        params=[
            CommandParam("url", "string", required=True, description="Webhook URL"),
            CommandParam("description", "string", description="Endpoint description"),
        ],
    ),
    CommandSchema(
        path="webhook.endpoint.list",
        cli_usage="spix webhook endpoint list",
        http_method="GET",
        api_endpoint="/webhooks/endpoints",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List webhook endpoints",
    ),
    CommandSchema(
        path="webhook.subscription.create",
        cli_usage="spix webhook subscription create --endpoint <id> --events <e>",
        http_method="POST",
        api_endpoint="/webhooks/subscriptions",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Create a webhook subscription",
        params=[
            CommandParam("endpoint_id", "string", required=True, description="Webhook endpoint ID"),
            CommandParam("events", "array", required=True, description="Event types to subscribe to"),
            CommandParam("playbook_id", "string", description="Filter events by playbook"),
        ],
    ),
    # ─── Auth Commands ────────────────────────────────────────────────────────
    CommandSchema(
        path="auth.whoami",
        cli_usage="spix auth whoami",
        http_method="GET",
        api_endpoint="/auth/whoami",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Show current authenticated identity",
    ),
    CommandSchema(
        path="auth.key.list",
        cli_usage="spix auth key list",
        http_method="GET",
        api_endpoint="/auth/keys",
        mcp_expose="tool",
        mcp_profile="safe",
        description="List API keys",
    ),
    CommandSchema(
        path="auth.key.create",
        cli_usage="spix auth key create --name <n>",
        http_method="POST",
        api_endpoint="/auth/keys",
        mcp_expose="tool",
        mcp_profile="safe",
        description="Create a new API key",
        params=[
            CommandParam("name", "string", required=True, description="Key name"),
            CommandParam("expires_at", "string", description="Expiration date (ISO8601)"),
        ],
    ),
    CommandSchema(
        path="auth.key.revoke",
        cli_usage="spix auth key revoke <key_id>",
        http_method="DELETE",
        api_endpoint="/auth/keys/{key_id}",
        mcp_expose="tool",
        mcp_profile="full",  # Destructive - full profile only
        destructive=True,
        description="Revoke an API key",
        positional_args=[
            CommandParam("key_id", "string", required=True, description="Key ID"),
        ],
    ),
]


# ─── MCP Resources ────────────────────────────────────────────────────────────
# Resources for MCP resource:// URIs

MCP_RESOURCES: list[CommandSchema] = [
    CommandSchema(
        path="resource.calls.transcript",
        cli_usage="",
        http_method="GET",
        api_endpoint="/calls/{session_id}/transcript",
        mcp_expose="resource",
        description="Call transcript",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    CommandSchema(
        path="resource.calls.summary",
        cli_usage="",
        http_method="GET",
        api_endpoint="/calls/{session_id}/summary",
        mcp_expose="resource",
        description="Call summary",
        positional_args=[
            CommandParam("session_id", "string", required=True, description="Call session ID"),
        ],
    ),
    CommandSchema(
        path="resource.sms.thread",
        cli_usage="",
        http_method="GET",
        api_endpoint="/sms/threads/{thread_id}",
        mcp_expose="resource",
        description="SMS conversation thread",
        positional_args=[
            CommandParam("thread_id", "string", required=True, description="Thread ID"),
        ],
    ),
    CommandSchema(
        path="resource.playbook",
        cli_usage="",
        http_method="GET",
        api_endpoint="/playbooks/{playbook_id}",
        mcp_expose="resource",
        description="Playbook details",
        positional_args=[
            CommandParam("playbook_id", "string", required=True, description="Playbook ID"),
        ],
    ),
    CommandSchema(
        path="resource.contact.history",
        cli_usage="",
        http_method="GET",
        api_endpoint="/contacts/{contact_id}/history",
        mcp_expose="resource",
        description="Contact communication history",
        positional_args=[
            CommandParam("contact_id", "string", required=True, description="Contact ID"),
        ],
    ),
    CommandSchema(
        path="resource.billing.credits",
        cli_usage="",
        http_method="GET",
        api_endpoint="/billing/credits",
        mcp_expose="resource",
        description="Credit balance",
    ),
    CommandSchema(
        path="resource.phone.route",
        cli_usage="",
        http_method="GET",
        api_endpoint="/phone/numbers/{number}/route",
        mcp_expose="resource",
        description="Number routing bindings",
        positional_args=[
            CommandParam("number", "string", required=True, description="Phone number (E.164)"),
        ],
    ),
]


def get_mcp_tools(profile: str = "safe", disabled: list[str] | None = None) -> list[CommandSchema]:
    """Return tool-exposed commands filtered by profile and disabled list.

    Args:
        profile: "safe" or "full". "safe" excludes destructive operations.
        disabled: List of command paths to exclude (e.g., ["billing.plan.set"]).

    Returns:
        List of CommandSchema objects to expose as MCP tools.
    """
    disabled_set = set(disabled or [])
    return [
        cmd
        for cmd in COMMAND_REGISTRY
        if cmd.mcp_expose == "tool"
        and (profile == "full" or cmd.mcp_profile == "safe")
        and cmd.path not in disabled_set
    ]


def get_mcp_resources() -> list[CommandSchema]:
    """Return resource-exposed commands for MCP resource:// URIs.

    Returns:
        List of CommandSchema objects to expose as MCP resources.
    """
    return [cmd for cmd in MCP_RESOURCES if cmd.mcp_expose == "resource"]


def get_command_by_path(path: str) -> CommandSchema | None:
    """Look up a command schema by its path.

    Args:
        path: Command path (e.g., "playbook.create").

    Returns:
        CommandSchema if found, None otherwise.
    """
    for cmd in COMMAND_REGISTRY:
        if cmd.path == path:
            return cmd
    return None


def build_json_schema(schema: CommandSchema) -> dict:
    """Convert a CommandSchema into a JSON Schema for MCP tool inputSchema.

    Args:
        schema: The command schema to convert.

    Returns:
        JSON Schema dict with properties and required fields.
    """
    properties: dict[str, dict] = {}
    required: list[str] = []

    type_map = {
        "string": "string",
        "integer": "integer",
        "boolean": "boolean",
        "enum": "string",
        "file": "string",
        "array": "array",
        "number": "number",
        "uuid": "string",  # UUID is represented as string in JSON Schema
    }

    for param in schema.positional_args + schema.params:
        prop: dict = {
            "type": type_map.get(param.type, "string"),
        }
        if param.description:
            prop["description"] = param.description
        if param.choices:
            prop["enum"] = param.choices
        if param.default is not None:
            prop["default"] = param.default
        if param.type == "array":
            prop["items"] = {"type": "string"}

        properties[param.name] = prop

        if param.required:
            required.append(param.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
