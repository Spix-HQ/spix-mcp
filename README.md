# Spix MCP Server

Give AI agents the ability to make phone calls and send emails — as MCP tool calls.

[Spix](https://spix.sh) is communications infrastructure for AI agents. This MCP server exposes Spix's API as tools that any MCP-compatible client (Claude Desktop, Cursor, Windsurf, etc.) can use.

## What your agent gets

| Tool | Description |
|------|-------------|
| `spix_call_create` | Make an outbound AI phone call |
| `spix_call_transcript` | Get the full transcript of a call |
| `spix_call_summary` | Get an AI-generated call summary |
| `spix_email_send` | Send an email |
| `spix_email_reply` | Reply to an email thread |
| `spix_contact_create` | Create or update a contact |
| `spix_contact_history` | Cross-channel interaction history |
| `spix_contact_summary` | AI summary of contact relationship |
| `spix_playbook_list` | List available playbooks |
| `spix_billing_credits` | Check credit balance |

20+ tools total. Run `spix-mcp` to see the full list.

## Quick start

### 1. Get a Spix API key

Sign up at [app.spix.sh](https://app.spix.sh) or via the CLI:

```bash
curl -fsSL https://github.com/Spix-HQ/spix-cli/releases/latest/download/spix-darwin-arm64 -o spix
chmod +x spix && sudo mv spix /usr/local/bin/
spix signup
spix auth key create --name mcp
```

### 2. Install

```bash
pip install spix-mcp
```

Or run directly with uvx (no install):

```bash
uvx spix-mcp
```

### 3. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spix": {
      "command": "uvx",
      "args": ["spix-mcp"],
      "env": {
        "SPIX_API_KEY": "your-api-key"
      }
    }
  }
}
```

Restart Claude Desktop. Spix tools will appear in the tools panel.

### Cursor / Windsurf

```json
{
  "mcpServers": {
    "spix": {
      "command": "uvx",
      "args": ["spix-mcp"],
      "env": {
        "SPIX_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Configuration

All configuration is via environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SPIX_API_KEY` | Yes | Your Spix API key |
| `SPIX_DEFAULT_PLAYBOOK` | No | Default playbook ID for calls |
| `SPIX_SESSION_NAME` | No | Session name for audit logging |
| `SPIX_TOOL_PROFILE` | No | `safe` (default) or `full` |

## Tool profiles

**Safe profile** (default): Read operations + create calls/emails. Cannot delete resources or modify billing.

**Full profile**: All operations including delete, billing management, and admin tools.

```json
{
  "env": {
    "SPIX_API_KEY": "your-key",
    "SPIX_TOOL_PROFILE": "full"
  }
}
```

## Session scoping

Restrict what your agent can access:

```json
{
  "env": {
    "SPIX_API_KEY": "your-key",
    "SPIX_DEFAULT_PLAYBOOK": "your-playbook-id",
    "SPIX_SESSION_NAME": "sales-bot"
  }
}
```

## How it works

```
Your Agent (Claude, etc.)
    ↓ MCP tool call
Spix MCP Server (this package)
    ↓ HTTP API call
Spix Backend (api.spix.sh)
    ↓ Carrier APIs
Phone call / Email / SMS
```

The MCP server is a thin bridge between MCP protocol and the Spix REST API. All business logic runs server-side. The MCP server handles:

- Tool schema generation from the API spec
- Session scoping and access control
- Request/response formatting for MCP protocol

## Voice calls

When your agent calls `spix_call_create`, Spix:

1. Dials the number via Telnyx/Twilio
2. Uses **Deepgram Nova-3** for real-time speech recognition
3. Uses **Claude** for conversation turn generation
4. Uses **Cartesia Sonic-3** for text-to-speech
5. Records the call and generates a transcript + summary

Your agent can then read the transcript and summary via `spix_call_transcript` and `spix_call_summary`.

## Links

- [Spix Website](https://spix.sh)
- [Dashboard](https://app.spix.sh)
- [CLI](https://github.com/Spix-HQ/spix-cli)
- [API Docs](https://docs.spix.sh)

## License

MIT
