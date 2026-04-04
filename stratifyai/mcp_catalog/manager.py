"""Catalog loading, search, config generation, and config file management."""

from __future__ import annotations

import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from .schemas import MCPServerCatalog, MCPServerEntry

CATALOG_URL = (
    "https://raw.githubusercontent.com/Bytes0211/stratifyai/main/"
    "stratifyai/mcp_catalog/catalog.json"
)

_CLIENT_LABELS = {
    "claude-desktop": "Claude Desktop",
    "claude-code": "Claude Code",
    "cursor": "Cursor",
    "vscode": "VS Code",
}

_catalog_cache: MCPServerCatalog | None = None


def get_catalog_path() -> Path:
    """Return the packaged catalog path."""
    return Path(__file__).with_name("catalog.json")


def load_catalog(force_reload: bool = False) -> MCPServerCatalog:
    """Load and validate the local curated MCP server catalog."""
    global _catalog_cache
    if _catalog_cache is not None and not force_reload:
        return _catalog_cache

    data = json.loads(get_catalog_path().read_text(encoding="utf-8"))
    _catalog_cache = MCPServerCatalog.model_validate(data)
    return _catalog_cache


def list_servers(
    category: str | None = None,
    search: str | None = None,
) -> list[MCPServerEntry]:
    """List catalog servers with optional filtering."""
    servers = load_catalog().servers
    if category:
        servers = [s for s in servers if s.category == category]
    if search:
        q = search.lower()
        servers = [
            s
            for s in servers
            if q in s.id.lower()
            or q in s.name.lower()
            or q in s.description.lower()
            or any(q in tag.lower() for tag in s.tags)
        ]
    return sorted(servers, key=lambda s: (s.category, s.name.lower()))


def get_server(server_id: str) -> MCPServerEntry:
    """Get one server by id."""
    for server in load_catalog().servers:
        if server.id == server_id:
            return server
    raise KeyError(f"Unknown MCP server: {server_id}")


def detect_client_config_path(
    client: str,
    project_root: str | Path | None = None,
) -> Path | None:
    """Return the default config path for a supported client."""
    home = Path.home()
    root = Path(project_root) if project_root else Path.cwd()

    if client == "claude-desktop":
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if not appdata:
                return None
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return home / ".config" / "Claude" / "claude_desktop_config.json"
    if client == "cursor":
        return root / ".cursor" / "mcp.json"
    if client == "vscode":
        return root / ".vscode" / "settings.json"
    if client == "claude-code":
        return None
    raise ValueError(
        f"Unsupported client '{client}'. Choose from: {sorted(_CLIENT_LABELS)}"
    )


def _resolve_user_arg_value(
    server: MCPServerEntry,
    arg_name: str,
    arg_values: dict[str, str],
) -> str | None:
    return arg_values.get(f"{server.id}.{arg_name}") or arg_values.get(arg_name) or None


def _build_server_config(
    server: MCPServerEntry,
    env_values: dict[str, str],
    arg_values: dict[str, str],
) -> dict[str, Any]:
    args = list(server.args)
    env: dict[str, str] = {}

    for env_var in server.env_vars:
        value = env_values.get(env_var.name) or os.environ.get(env_var.name)
        if value:
            env[env_var.name] = value
        elif env_var.required:
            env[env_var.name] = f"<{env_var.name}>"

    for user_arg in server.user_args:
        value = _resolve_user_arg_value(server, user_arg.name, arg_values)
        if value is None and user_arg.required:
            value = user_arg.example or f"<{user_arg.name}>"
        if value is None:
            continue

        values = [v.strip() for v in str(value).split(",") if v.strip()]
        if not values:
            continue

        if user_arg.flag:
            for item in values:
                args.extend([user_arg.flag, item])
        else:
            args.extend(values)

    config: dict[str, Any] = {"command": server.command}
    if args:
        config["args"] = args
    if env:
        config["env"] = env
    return config


def build_client_config(
    client: str,
    server_ids: list[str],
    env_values: dict[str, str] | None = None,
    arg_values: dict[str, str] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build client-specific JSON config for selected MCP servers."""
    del project_root  # reserved for future client-specific path generation
    env_values = env_values or {}
    arg_values = arg_values or {}

    server_map = {
        server_id: _build_server_config(get_server(server_id), env_values, arg_values)
        for server_id in server_ids
    }

    if client in {"claude-desktop", "cursor", "claude-code"}:
        return {"mcpServers": server_map}
    if client == "vscode":
        return {"mcp": {"servers": server_map}}

    raise ValueError(
        f"Unsupported client '{client}'. Choose from: {sorted(_CLIENT_LABELS)}"
    )


def build_claude_code_commands(
    server_ids: list[str],
    env_values: dict[str, str] | None = None,
    arg_values: dict[str, str] | None = None,
) -> list[str]:
    """Build `claude mcp add` shell commands for Claude Code users."""
    env_values = env_values or {}
    arg_values = arg_values or {}
    commands: list[str] = []

    for server_id in server_ids:
        server = get_server(server_id)
        cfg = _build_server_config(server, env_values, arg_values)
        cmd_parts = ["claude", "mcp", "add", server_id, cfg["command"]]
        for arg in cfg.get("args", []):
            cmd_parts.append(str(arg))
        for key, value in cfg.get("env", {}).items():
            cmd_parts.extend(["-e", f"{key}={value}"])
        commands.append(" ".join(cmd_parts))

    return commands


def write_client_config(
    client: str,
    config: dict[str, Any],
    project_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Merge and write config to the target file, creating a backup first."""
    path = (
        Path(output_path)
        if output_path
        else detect_client_config_path(client, project_root)
    )
    if path is None:
        raise ValueError(
            "Claude Code uses `claude mcp add ...` commands rather than a config file. "
            "Use build_claude_code_commands() or run `stratifyai mcp setup --client claude-code --dry-run`."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        backup_path = Path(str(path) + ".backup")
        backup_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    if client == "vscode":
        merged = dict(existing)
        mcp_block = dict(merged.get("mcp", {}))
        servers = dict(mcp_block.get("servers", {}))
        servers.update(config.get("mcp", {}).get("servers", {}))
        mcp_block["servers"] = servers
        merged["mcp"] = mcp_block
    else:
        merged = dict(existing)
        servers = dict(merged.get("mcpServers", {}))
        servers.update(config.get("mcpServers", {}))
        merged["mcpServers"] = servers

    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return path


def get_configured_servers(
    client: str,
    project_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    """Return the configured MCP servers for a supported client."""
    path = (
        Path(output_path)
        if output_path
        else detect_client_config_path(client, project_root)
    )
    if path is None:
        return None, {}
    if not path.exists():
        return path, {}

    data = json.loads(path.read_text(encoding="utf-8"))
    if client == "vscode":
        servers = data.get("mcp", {}).get("servers", {})
    else:
        servers = data.get("mcpServers", {})
    return path, dict(servers)


def remove_server_from_config(
    client: str,
    server_id: str,
    project_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[Path, bool]:
    """Remove a configured MCP server from a client config file."""
    path = (
        Path(output_path)
        if output_path
        else detect_client_config_path(client, project_root)
    )
    if path is None:
        raise ValueError(
            "Claude Code removal should be performed with `claude mcp remove <server-id>` commands."
        )
    if not path.exists():
        return path, False

    data = json.loads(path.read_text(encoding="utf-8"))

    if client == "vscode":
        mcp_block = dict(data.get("mcp", {}))
        servers = dict(mcp_block.get("servers", {}))
        removed = servers.pop(server_id, None) is not None
        if not removed:
            return path, False
        mcp_block["servers"] = servers
        data["mcp"] = mcp_block
    else:
        servers = dict(data.get("mcpServers", {}))
        removed = servers.pop(server_id, None) is not None
        if not removed:
            return path, False
        data["mcpServers"] = servers

    backup_path = Path(str(path) + ".backup")
    backup_path.write_text(
        json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2),
        encoding="utf-8",
    )
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path, True


def validate_prerequisites(server_ids: list[str]) -> list[str]:
    """Return warnings for missing local prerequisites required by servers."""
    warnings: list[str] = []
    servers = [get_server(server_id) for server_id in server_ids]

    if (
        any(server.install_method == "npx" for server in servers)
        and shutil.which("npx") is None
    ):
        warnings.append(
            "One or more selected servers require Node.js with `npx`, but it was not found on PATH."
        )
    if (
        any(server.install_method == "docker" for server in servers)
        and shutil.which("docker") is None
    ):
        warnings.append(
            "One or more selected servers require Docker, but it was not found on PATH."
        )

    return warnings


def update_catalog(url: str = CATALOG_URL) -> Path:
    """Fetch the latest catalog JSON from a URL or local file path and replace the packaged copy."""
    if Path(url).exists():
        raw_text = Path(url).read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(url, timeout=15) as response:
            raw_text = response.read().decode("utf-8")

    data = json.loads(raw_text)
    MCPServerCatalog.model_validate(data)

    catalog_path = get_catalog_path()
    if catalog_path.exists():
        Path(str(catalog_path) + ".backup").write_text(
            catalog_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    catalog_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    global _catalog_cache
    _catalog_cache = None
    load_catalog(force_reload=True)
    return catalog_path
