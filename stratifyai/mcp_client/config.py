"""Configuration loading for the MCP client engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from stratifyai.mcp_catalog import get_configured_servers, get_mcp_client_settings

from .permissions import ServerPermissionConfig


@dataclass(slots=True)
class ConfiguredServer:
    """Runtime server configuration for MCP client engine startup."""

    server_id: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: Path | None = None
    enabled: bool = True
    auto_start: bool = True
    timeout_seconds: float = 30.0
    permissions: ServerPermissionConfig = field(default_factory=ServerPermissionConfig)


def load_enabled_servers(
    client: str = "cursor",
    project_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> list[ConfiguredServer]:
    """Load enabled MCP servers from an existing client configuration."""
    path, server_map = get_configured_servers(
        client=client,
        project_root=project_root,
        output_path=output_path,
    )
    _settings_path, client_settings = get_mcp_client_settings(
        client=client,
        project_root=project_root,
        output_path=output_path,
    )
    settings_by_server = client_settings.get("servers", {})
    if not isinstance(settings_by_server, dict):
        settings_by_server = {}

    default_cwd = path.parent if path is not None else None

    servers: list[ConfiguredServer] = []
    for server_id, cfg in server_map.items():
        if not isinstance(cfg, dict):
            continue
        command = str(cfg.get("command", "")).strip()
        if not command:
            continue

        server_settings = settings_by_server.get(server_id, {})
        if not isinstance(server_settings, dict):
            server_settings = {}

        args = [str(value) for value in cfg.get("args", [])]
        env = {str(k): str(v) for k, v in cfg.get("env", {}).items()}
        cwd = Path(str(cfg["cwd"])) if cfg.get("cwd") else default_cwd

        servers.append(
            ConfiguredServer(
                server_id=server_id,
                command=command,
                args=args,
                env=env,
                cwd=cwd,
                enabled=bool(server_settings.get("enabled", cfg.get("enabled", True))),
                auto_start=bool(
                    server_settings.get("auto_start", cfg.get("auto_start", True))
                ),
                timeout_seconds=float(
                    server_settings.get("timeout_seconds")
                    or cfg.get("timeout_seconds", 30.0)
                    or 30.0
                ),
                permissions=ServerPermissionConfig.from_dict(
                    server_settings.get("permissions")
                ),
            )
        )

    return servers
