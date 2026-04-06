"""MCP server catalog and client config generation helpers."""

from .manager import (
    CATALOG_URL,
    build_claude_code_commands,
    build_client_config,
    detect_client_config_path,
    get_configured_servers,
    get_mcp_client_settings,
    get_server,
    list_servers,
    load_catalog,
    remove_server_from_config,
    remove_servers_from_config,
    update_catalog,
    validate_prerequisites,
    write_client_config,
    write_mcp_client_settings,
)
from .schemas import MCPServerCatalog, MCPServerEntry

__all__ = [
    "CATALOG_URL",
    "MCPServerCatalog",
    "MCPServerEntry",
    "build_client_config",
    "build_claude_code_commands",
    "detect_client_config_path",
    "get_configured_servers",
    "get_mcp_client_settings",
    "get_server",
    "list_servers",
    "load_catalog",
    "remove_server_from_config",
    "remove_servers_from_config",
    "update_catalog",
    "validate_prerequisites",
    "write_client_config",
    "write_mcp_client_settings",
]
