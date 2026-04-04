"""Configuration loading for the MCP client engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from stratifyai.mcp_catalog import get_configured_servers


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
    default_cwd = path.parent if path is not None else None

    servers: list[ConfiguredServer] = []
    for server_id, cfg in server_map.items():
        command = str(cfg.get("command", "")).strip()
        if not command:
            continue
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
                enabled=bool(cfg.get("enabled", True)),
                auto_start=bool(cfg.get("auto_start", True)),
                timeout_seconds=float(cfg.get("timeout_seconds", 30.0)),
            )
        )

    return [server for server in servers if server.enabled]
