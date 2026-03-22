"""MCP config installation for Claude Desktop and Cursor.

This module writes MCP server configuration to the config files for:
- Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
- Cursor: Various locations depending on platform

Safety:
- ALWAYS backup existing config before modifying
- Use atomic write (write to temp, then rename)
"""

from __future__ import annotations

import platform
import shutil
import stat
import tempfile
from pathlib import Path

import orjson


def install_claude(api_key: str, session_name: str = "claude-desktop") -> str:
    """Write MCP config to Claude Desktop config file.

    This adds a "spix" entry to the mcpServers section of
    Claude Desktop's configuration.

    Args:
        api_key: The Spix API key to use.
        session_name: Name for the MCP session.

    Returns:
        Path to the modified config file.
    """
    config_path = _claude_config_path()

    # Load existing config or create new
    config = _load_or_init(config_path)

    # Backup existing config
    _backup_config(config_path)

    # Add/update Spix MCP server
    config.setdefault("mcpServers", {})
    config["mcpServers"]["spix"] = {
        "command": "spix",
        "args": [
            "mcp",
            "serve",
            "--session-name",
            session_name,
            "--tool-profile",
            "safe",
        ],
        "env": {"SPIX_API_KEY": api_key},
    }

    # Write atomically
    _write_atomic(config_path, config)

    return str(config_path)


def install_cursor(api_key: str, session_name: str = "cursor") -> str:
    """Write MCP config to Cursor config file.

    This adds a "spix" entry to the mcpServers section of
    Cursor's MCP configuration.

    Args:
        api_key: The Spix API key to use.
        session_name: Name for the MCP session.

    Returns:
        Path to the modified config file.
    """
    config_path = _cursor_config_path()

    # Load existing config or create new
    config = _load_or_init(config_path)

    # Backup existing config
    _backup_config(config_path)

    # Add/update Spix MCP server
    config.setdefault("mcpServers", {})
    config["mcpServers"]["spix"] = {
        "command": "spix",
        "args": [
            "mcp",
            "serve",
            "--session-name",
            session_name,
            "--tool-profile",
            "safe",
        ],
        "env": {"SPIX_API_KEY": api_key},
    }

    # Write atomically
    _write_atomic(config_path, config)

    return str(config_path)


def uninstall_claude() -> str | None:
    """Remove Spix from Claude Desktop config.

    Returns:
        Path to the modified config file, or None if not found.
    """
    config_path = _claude_config_path()

    if not config_path.exists():
        return None

    config = _load_or_init(config_path)

    if "mcpServers" not in config or "spix" not in config["mcpServers"]:
        return None

    # Backup before modifying
    _backup_config(config_path)

    # Remove Spix entry
    del config["mcpServers"]["spix"]

    # Write atomically
    _write_atomic(config_path, config)

    return str(config_path)


def uninstall_cursor() -> str | None:
    """Remove Spix from Cursor config.

    Returns:
        Path to the modified config file, or None if not found.
    """
    config_path = _cursor_config_path()

    if not config_path.exists():
        return None

    config = _load_or_init(config_path)

    if "mcpServers" not in config or "spix" not in config["mcpServers"]:
        return None

    # Backup before modifying
    _backup_config(config_path)

    # Remove Spix entry
    del config["mcpServers"]["spix"]

    # Write atomically
    _write_atomic(config_path, config)

    return str(config_path)


def _claude_config_path() -> Path:
    """Get the Claude Desktop config file path."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        import os

        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:
        # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _cursor_config_path() -> Path:
    """Get the Cursor MCP config file path."""
    system = platform.system()
    if system == "Darwin":
        # Cursor on macOS stores MCP config in the User globalStorage
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "cursor.mcp"
            / "config.json"
        )
    elif system == "Windows":
        import os

        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "config.json"
    else:
        # Linux
        return Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "config.json"


def _load_or_init(path: Path) -> dict:
    """Load existing JSON config or return empty dict."""
    if path.exists():
        try:
            return orjson.loads(path.read_bytes())
        except (orjson.JSONDecodeError, OSError):
            return {}
    return {}


def _backup_config(path: Path) -> Path | None:
    """Create a backup of the config file if it exists.

    Returns:
        Path to the backup file, or None if no backup was created.
    """
    if not path.exists():
        return None

    backup_path = path.with_suffix(".json.backup")
    shutil.copy2(path, backup_path)
    return backup_path


def _write_atomic(path: Path, data: dict) -> None:
    """Write config file atomically.

    Writes to a temp file then renames to avoid corruption.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (for same-filesystem rename)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        import os

        # Write JSON with pretty formatting — close fd in finally to avoid leak
        try:
            content = orjson.dumps(data, option=orjson.OPT_INDENT_2)
            os.write(fd, content)
        finally:
            os.close(fd)

        # Atomic rename
        shutil.move(tmp_path, path)

        # Restrict permissions: owner read/write only (0600)
        # Config files may contain API keys in env section
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        # Clean up temp file on error
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise
