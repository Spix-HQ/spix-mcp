"""Entry point for running as `python -m spix_mcp` or `uvx spix-mcp`."""

import asyncio
import os
import sys


def main():
    api_key = os.environ.get("SPIX_API_KEY")
    if not api_key:
        sys.stderr.write("Error: SPIX_API_KEY environment variable is required.\n")
        sys.stderr.write("Get one at https://app.spix.sh or run: spix auth key create --name mcp\n")
        sys.exit(1)

    from spix_mcp.server import run_mcp_server

    asyncio.run(
        run_mcp_server(
            api_key=api_key,
            session_name=os.environ.get("SPIX_SESSION_NAME", "mcp"),
            default_playbook=os.environ.get("SPIX_DEFAULT_PLAYBOOK"),
            tool_profile=os.environ.get("SPIX_TOOL_PROFILE", "safe"),
        )
    )


if __name__ == "__main__":
    main()
