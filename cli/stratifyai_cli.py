"""StratifyAI CLI - Unified LLM interface via terminal."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from stratifyai import (
    ChatRequest,
    LLMClient,
    Message,
    Router,
    RoutingStrategy,
    get_cache_stats,
)
from stratifyai.caching import clear_cache, get_cache_entries
from stratifyai.config import MODEL_CATALOG, PROVIDER_ENV_VARS
from stratifyai.exceptions import (
    AuthenticationError,
    InvalidModelError,
    InvalidProviderError,
)
from stratifyai.mcp_catalog import (
    CATALOG_URL,
    build_claude_code_commands,
    build_client_config,
    detect_client_config_path,
    get_configured_servers,
    get_mcp_client_settings,
    remove_server_from_config,
    validate_prerequisites,
    write_client_config,
    write_mcp_client_settings,
)
from stratifyai.mcp_catalog import (
    list_servers as list_mcp_servers,
)
from stratifyai.mcp_catalog import (
    update_catalog as update_mcp_catalog,
)
from stratifyai.mcp_catalog.manager import get_server
from stratifyai.summarization import summarize_file
from stratifyai.utils.file_analyzer import analyze_file
from stratifyai.utils.sync_helpers import run_sync

# Load environment variables from .env file
load_dotenv()

# Initialize Typer app and Rich console
app = typer.Typer(
    name="stratifyai",
    help="StratifyAI - Unified LLM CLI across 9 providers",
    add_completion=True,
)
mcp_app = typer.Typer(help="Manage curated MCP servers and client configuration")
app.add_typer(mcp_app, name="mcp")
console = Console()

# Mode-specific colors and icons
CHAT_COLOR = "magenta"
CHAT_ACCENT = "bold magenta"
CHAT_ICON = "💬"
INTERACTIVE_COLOR = "cyan"
INTERACTIVE_ACCENT = "bold cyan"
INTERACTIVE_ICON = "⚡"


def mode_prompt(text: str, mode: str = "chat") -> str:
    """Add mode icon prefix to prompt text."""
    icon = CHAT_ICON if mode == "chat" else INTERACTIVE_ICON
    color = CHAT_ACCENT if mode == "chat" else INTERACTIVE_ACCENT
    return f"[{color}]{icon}[/{color}] {text}"


_MCP_CLIENT_CHOICES = ["claude-desktop", "claude-code", "cursor", "vscode"]
_MCP_CLIENT_LABELS = {
    "claude-desktop": "Claude Desktop",
    "claude-code": "Claude Code",
    "cursor": "Cursor",
    "vscode": "VS Code (Copilot Chat)",
}


def _parse_mcp_assignments(values: list[str] | None) -> dict[str, str]:
    """Parse repeated KEY=VALUE CLI options into a dict."""
    parsed: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise typer.BadParameter(
                f"Expected KEY=VALUE format, got: {item!r}", param_hint="--env/--arg"
            )
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _prompt_for_mcp_client() -> str:
    """Interactively select a supported MCP client."""
    console.print("\n[bold cyan]Select MCP Client[/bold cyan]")
    for index, client in enumerate(_MCP_CLIENT_CHOICES, start=1):
        console.print(f"  {index}. {_MCP_CLIENT_LABELS[client]}")

    choice = Prompt.ask(mode_prompt("Choose client", "chat"), default="1")
    try:
        return _MCP_CLIENT_CHOICES[int(choice) - 1]
    except (ValueError, IndexError) as exc:
        raise typer.BadParameter("Invalid client selection") from exc


def _resolve_mcp_client(client: str | None) -> str:
    """Resolve a provided or interactive MCP client selection."""
    selected_client = client or _prompt_for_mcp_client()
    if selected_client not in _MCP_CLIENT_CHOICES:
        raise typer.BadParameter(
            f"Unsupported client '{selected_client}'. Choose from: {', '.join(_MCP_CLIENT_CHOICES)}"
        )
    return selected_client


def _prompt_for_mcp_servers() -> list[str]:
    """Interactively select MCP servers via comma-separated ids."""
    servers = list_mcp_servers()
    table = Table(
        title="📦 MCP Server Catalog", show_lines=False, header_style="bold cyan"
    )
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Install", style="green")

    for server in servers:
        table.add_row(server.id, server.name, server.category, server.install_method)

    console.print()
    console.print(table)
    raw = Prompt.ask(
        mode_prompt("Select servers (comma-separated ids)", "chat"),
        default="stratifyai",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


def _collect_missing_mcp_values(
    server_ids: list[str],
    env_values: dict[str, str],
    arg_values: dict[str, str],
    dry_run: bool,
) -> tuple[dict[str, str], dict[str, str]]:
    """Prompt for any required env vars or user args not provided on the CLI."""
    for server_id in server_ids:
        server = get_server(server_id)

        for env_var in server.env_vars:
            if env_var.name in env_values or os.environ.get(env_var.name):
                continue
            if dry_run:
                env_values[env_var.name] = f"<{env_var.name}>"
                continue

            prompt_text = f"{server.name} — {env_var.name}"
            env_values[env_var.name] = Prompt.ask(prompt_text, password=env_var.secret)

        for user_arg in server.user_args:
            key = f"{server.id}.{user_arg.name}"
            if key in arg_values or user_arg.name in arg_values:
                continue
            if dry_run:
                arg_values[key] = user_arg.example or f"<{user_arg.name}>"
                continue

            prompt_text = f"{server.name} — {user_arg.description or user_arg.name}"
            arg_values[key] = Prompt.ask(
                prompt_text,
                default=user_arg.example or "",
            )

    return env_values, arg_values


def _build_mcp_engine_settings(
    server_ids: list[str],
    *,
    enabled: bool,
    auto_start: bool,
) -> dict[str, Any]:
    """Build StratifyAI-specific MCP engine settings for one or more servers."""
    return {
        "servers": {
            server_id: {
                "enabled": enabled,
                "auto_start": auto_start,
            }
            for server_id in server_ids
        }
    }


@mcp_app.command("list")
def mcp_list(
    category: str | None = typer.Option(None, "--category", help="Filter by category"),
    search: str | None = typer.Option(
        None, "--search", help="Search by id, name, or tag"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON"
    ),
) -> None:
    """List curated MCP servers from the local catalog."""
    servers = list_mcp_servers(category=category, search=search)

    if json_output:
        typer.echo(json.dumps([server.model_dump() for server in servers], indent=2))
        return

    table = Table(title="📦 Curated MCP Servers", header_style="bold cyan")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Install", style="green")
    table.add_column("Requires", style="yellow")

    for server in servers:
        required = ", ".join(env.name for env in server.env_vars if env.required) or "-"
        table.add_row(
            server.id,
            server.name,
            server.category,
            server.install_method,
            required,
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]{len(servers)} server(s) available[/dim]")


@mcp_app.command("setup")
def mcp_setup(
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    servers: str | None = typer.Option(
        None, "--servers", help="Comma-separated server ids to enable"
    ),
    env: list[str] | None = typer.Option(
        None, "--env", help="Environment variable assignment KEY=VALUE (repeatable)"
    ),
    arg: list[str] | None = typer.Option(
        None, "--arg", help="User arg assignment server.arg=value (repeatable)"
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config generation"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override output config path"
    ),
    enabled: bool = typer.Option(
        True,
        "--enabled/--disabled",
        help="Enable or disable the server(s) for StratifyAI's MCP client engine",
    ),
    auto_start: bool = typer.Option(
        True,
        "--auto-start/--manual-start",
        help="Start the server(s) automatically when the MCP client engine starts",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview config without writing it"
    ),
) -> None:
    """Interactive MCP setup wizard and config generator."""
    try:
        selected_client = client or _prompt_for_mcp_client()
        if selected_client not in _MCP_CLIENT_CHOICES:
            raise typer.BadParameter(
                f"Unsupported client '{selected_client}'. Choose from: {', '.join(_MCP_CLIENT_CHOICES)}"
            )

        selected_servers = (
            [item.strip() for item in servers.split(",") if item.strip()]
            if servers
            else _prompt_for_mcp_servers()
        )
        if not selected_servers:
            selected_servers = ["stratifyai"]
        if "stratifyai" not in selected_servers:
            selected_servers.insert(0, "stratifyai")

        env_values = _parse_mcp_assignments(env)
        arg_values = _parse_mcp_assignments(arg)
        env_values, arg_values = _collect_missing_mcp_values(
            selected_servers, env_values, arg_values, dry_run=dry_run
        )

        warnings = validate_prerequisites(selected_servers)

        console.print(
            f"\n[bold cyan]MCP Setup for {_MCP_CLIENT_LABELS[selected_client]}[/bold cyan]"
        )
        console.print(f"[dim]Selected servers: {', '.join(selected_servers)}[/dim]")

        if selected_client == "claude-code":
            commands = build_claude_code_commands(
                selected_servers, env_values, arg_values
            )
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
                console.print(f"\n[green]✓ Commands written to[/green] {output_path}")
            else:
                console.print("\n[bold]Run these commands in your terminal:[/bold]")
                for command in commands:
                    console.print(f"  [green]{command}[/green]")
            if warnings:
                for warning in warnings:
                    console.print(f"[yellow]⚠ {warning}[/yellow]")
            return

        config = build_client_config(
            client=selected_client,
            server_ids=selected_servers,
            env_values=env_values,
            arg_values=arg_values,
            project_root=project_root,
        )

        engine_settings = _build_mcp_engine_settings(
            selected_servers,
            enabled=enabled,
            auto_start=auto_start,
        )

        if dry_run:
            console.print()
            console.print_json(json.dumps(config))
            console.print("\n[dim]StratifyAI MCP engine settings:[/dim]")
            console.print_json(json.dumps(engine_settings))
            config_path = detect_client_config_path(selected_client, project_root)
            if config_path is not None:
                console.print(f"\n[dim]Target path: {config_path}[/dim]")
        else:
            written = write_client_config(
                client=selected_client,
                config=config,
                project_root=project_root,
                output_path=output_path,
            )
            write_mcp_client_settings(
                client=selected_client,
                settings=engine_settings,
                project_root=project_root,
                output_path=output_path,
            )
            console.print(f"\n[green]✓ Config written to[/green] {written}")

        if warnings:
            for warning in warnings:
                console.print(f"[yellow]⚠ {warning}[/yellow]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("status")
def mcp_status(
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config lookup"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override config path to inspect"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON status"),
) -> None:
    """Show currently configured MCP servers for a client."""
    try:
        selected_client = _resolve_mcp_client(client)

        if selected_client == "claude-code":
            payload: dict[str, Any] = {
                "client": selected_client,
                "configured": [],
                "note": "Use `claude mcp list` to inspect Claude Code-managed servers.",
            }
            if json_output:
                typer.echo(json.dumps(payload, indent=2))
            else:
                console.print(
                    "[yellow]Claude Code manages MCP servers via its own CLI.[/yellow]"
                )
                console.print(
                    "[dim]Run `claude mcp list` to inspect the active configuration.[/dim]"
                )
            return

        path, servers = get_configured_servers(
            client=selected_client,
            project_root=project_root,
            output_path=output_path,
        )
        _settings_path, engine_settings = get_mcp_client_settings(
            client=selected_client,
            project_root=project_root,
            output_path=output_path,
        )
        settings_by_server = engine_settings.get("servers", {})
        if not isinstance(settings_by_server, dict):
            settings_by_server = {}

        status_payload: dict[str, Any] = {
            "client": selected_client,
            "path": str(path) if path is not None else None,
            "configured": servers,
            "settings": settings_by_server,
            "count": len(servers),
        }
        if json_output:
            typer.echo(json.dumps(status_payload, indent=2))
            return

        console.print(
            f"\n[bold cyan]Configured MCP Servers — {_MCP_CLIENT_LABELS[selected_client]}[/bold cyan]"
        )
        if path is not None:
            console.print(f"[dim]Config path: {path}[/dim]")

        if not servers:
            console.print("[yellow]No MCP servers configured yet.[/yellow]")
            return

        table = Table(header_style="bold cyan")
        table.add_column("ID", style="cyan")
        table.add_column("Source", style="magenta")
        table.add_column("Enabled", style="yellow")
        table.add_column("Auto-start", style="yellow")
        table.add_column("Command", style="green")
        table.add_column("Args", style="white")

        for server_id, config in sorted(servers.items()):
            server_settings = settings_by_server.get(server_id, {})
            if not isinstance(server_settings, dict):
                server_settings = {}
            try:
                get_server(server_id)
                source = "catalog"
            except KeyError:
                source = "custom"
            table.add_row(
                server_id,
                source,
                "yes" if server_settings.get("enabled", True) else "no",
                "yes" if server_settings.get("auto_start", True) else "no",
                str(config.get("command", "-")),
                " ".join(str(arg) for arg in config.get("args", [])) or "-",
            )

        console.print()
        console.print(table)
        console.print(f"\n[green]{len(servers)} configured server(s)[/green]")
    except Exception as exc:
        console.print(f"[red]Status check failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("add")
def mcp_add(
    server_id: str = typer.Argument(..., help="Catalog server id to add"),
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    env: list[str] | None = typer.Option(
        None, "--env", help="Environment variable assignment KEY=VALUE (repeatable)"
    ),
    arg: list[str] | None = typer.Option(
        None, "--arg", help="User arg assignment server.arg=value (repeatable)"
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config generation"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override output config path"
    ),
    enabled: bool = typer.Option(
        True,
        "--enabled/--disabled",
        help="Enable or disable the server for StratifyAI's MCP client engine",
    ),
    auto_start: bool = typer.Option(
        True,
        "--auto-start/--manual-start",
        help="Start the server automatically when the MCP client engine starts",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview the config without writing it"
    ),
) -> None:
    """Add a single curated MCP server to a client config."""
    try:
        selected_client = _resolve_mcp_client(client)
        get_server(server_id)

        env_values = _parse_mcp_assignments(env)
        arg_values = _parse_mcp_assignments(arg)
        env_values, arg_values = _collect_missing_mcp_values(
            [server_id], env_values, arg_values, dry_run=dry_run
        )
        warnings = validate_prerequisites([server_id])

        if selected_client == "claude-code":
            commands = build_claude_code_commands([server_id], env_values, arg_values)
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
                console.print(f"\n[green]✓ Commands written to[/green] {output_path}")
            else:
                console.print("\n[bold]Run this command in your terminal:[/bold]")
                for command in commands:
                    console.print(f"  [green]{command}[/green]")
        else:
            config = build_client_config(
                client=selected_client,
                server_ids=[server_id],
                env_values=env_values,
                arg_values=arg_values,
                project_root=project_root,
            )
            engine_settings = _build_mcp_engine_settings(
                [server_id],
                enabled=enabled,
                auto_start=auto_start,
            )
            if dry_run:
                console.print()
                console.print_json(json.dumps(config))
                console.print("\n[dim]StratifyAI MCP engine settings:[/dim]")
                console.print_json(json.dumps(engine_settings))
            else:
                written = write_client_config(
                    client=selected_client,
                    config=config,
                    project_root=project_root,
                    output_path=output_path,
                )
                write_mcp_client_settings(
                    client=selected_client,
                    settings=engine_settings,
                    project_root=project_root,
                    output_path=output_path,
                )
                console.print(f"\n[green]✓ Added {server_id} to[/green] {written}")

        for warning in warnings:
            console.print(f"[yellow]⚠ {warning}[/yellow]")
    except Exception as exc:
        console.print(f"[red]Add failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("add-custom")
def mcp_add_custom(
    server_id: str = typer.Argument(..., help="Custom server id to add"),
    command: str = typer.Option(..., "--command", help="Executable or command to run"),
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    command_arg: list[str] | None = typer.Option(
        None, "--command-arg", help="Command argument (repeatable)"
    ),
    env: list[str] | None = typer.Option(
        None, "--env", help="Environment variable assignment KEY=VALUE (repeatable)"
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config generation"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override output config path"
    ),
    enabled: bool = typer.Option(
        True,
        "--enabled/--disabled",
        help="Enable or disable the server for StratifyAI's MCP client engine",
    ),
    auto_start: bool = typer.Option(
        True,
        "--auto-start/--manual-start",
        help="Start the server automatically when the MCP client engine starts",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview the config without writing it"
    ),
) -> None:
    """Add a custom, non-catalog MCP server entry to a client config."""
    try:
        selected_client = _resolve_mcp_client(client)
        env_values = _parse_mcp_assignments(env)

        server_config: dict[str, Any] = {"command": command}
        if command_arg:
            server_config["args"] = list(command_arg)
        if env_values:
            server_config["env"] = env_values

        if selected_client == "vscode":
            config = {"mcp": {"servers": {server_id: server_config}}}
        else:
            config = {"mcpServers": {server_id: server_config}}

        if selected_client == "claude-code":
            parts = ["claude", "mcp", "add", server_id, command]
            parts.extend(list(command_arg or []))
            for key, value in env_values.items():
                parts.extend(["-e", f"{key}={value}"])
            rendered_command = " ".join(parts)

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered_command + "\n", encoding="utf-8")
                console.print(f"\n[green]✓ Command written to[/green] {output_path}")
            else:
                console.print("\n[bold]Run this command in your terminal:[/bold]")
                console.print(f"  [green]{rendered_command}[/green]")
            return

        engine_settings = _build_mcp_engine_settings(
            [server_id],
            enabled=enabled,
            auto_start=auto_start,
        )

        if dry_run:
            console.print()
            console.print_json(json.dumps(config))
            console.print("\n[dim]StratifyAI MCP engine settings:[/dim]")
            console.print_json(json.dumps(engine_settings))
            return

        written = write_client_config(
            client=selected_client,
            config=config,
            project_root=project_root,
            output_path=output_path,
        )
        write_mcp_client_settings(
            client=selected_client,
            settings=engine_settings,
            project_root=project_root,
            output_path=output_path,
        )
        console.print(
            f"\n[green]✓ Added custom server {server_id} to[/green] {written}"
        )
    except Exception as exc:
        console.print(f"[red]Add custom failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("export-custom")
def mcp_export_custom(
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config lookup"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override config path to inspect"
    ),
    output_file: Path | None = typer.Option(
        None, "--file", "-f", help="Write JSON to this file instead of stdout"
    ),
) -> None:
    """Export non-catalog (custom) MCP servers as JSON."""
    try:
        selected_client = _resolve_mcp_client(client)

        if selected_client == "claude-code":
            console.print(
                "[yellow]Claude Code does not use a local config file. "
                "Export is not supported.[/yellow]"
            )
            raise typer.Exit(1)

        path, servers = get_configured_servers(
            client=selected_client,
            project_root=project_root,
            output_path=output_path,
        )

        catalog_ids: set[str] = set()
        try:
            for srv in list_mcp_servers():
                catalog_ids.add(srv.id)
        except Exception:
            pass

        custom_entries: list[dict[str, Any]] = []
        for server_id, config in sorted(servers.items()):
            if server_id in catalog_ids:
                continue
            if not isinstance(config, dict):
                continue
            custom_entries.append(
                {
                    "server_id": server_id,
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "env": config.get("env", {}),
                }
            )

        output_text = json.dumps(custom_entries, indent=2)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(output_text + "\n", encoding="utf-8")
            console.print(
                f"[green]✓ Exported {len(custom_entries)} custom server(s) to[/green] {output_file}"
            )
        else:
            typer.echo(output_text)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("import-custom")
def mcp_import_custom(
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    input_file: Path | None = typer.Option(
        None, "--file", "-f", help="Read JSON from this file instead of stdin"
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config generation"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override output config path"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing servers with the same id"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be imported without writing"
    ),
) -> None:
    """Import custom MCP servers from a JSON file or stdin."""
    import re as _re

    _shell_metachar_re = _re.compile(r"[;|&`]|\$\(")

    try:
        selected_client = _resolve_mcp_client(client)

        if selected_client == "claude-code":
            console.print(
                "[yellow]Claude Code does not use a local config file. "
                "Import is not supported.[/yellow]"
            )
            raise typer.Exit(1)

        if input_file:
            raw_text = input_file.read_text(encoding="utf-8")
        else:
            raw_text = sys.stdin.read()

        entries = json.loads(raw_text)
        if not isinstance(entries, list):
            console.print("[red]Import file must contain a JSON array.[/red]")
            raise typer.Exit(1)

        _, existing_servers = get_configured_servers(
            client=selected_client,
            project_root=project_root,
            output_path=output_path,
        )

        added = 0
        skipped = 0
        errors = 0

        for entry in entries:
            sid = str(entry.get("server_id", "")).strip()
            cmd = str(entry.get("command", "")).strip()

            if not sid:
                console.print("[red]✗ Skipping entry with empty server_id[/red]")
                errors += 1
                continue

            if "/" in sid or "\\" in sid:
                console.print(f"[red]✗ {sid}: server_id contains path separators[/red]")
                errors += 1
                continue

            if not cmd:
                console.print(f"[red]✗ {sid}: empty command[/red]")
                errors += 1
                continue

            if _shell_metachar_re.search(cmd):
                console.print(
                    f"[red]✗ {sid}: command contains shell metacharacters[/red]"
                )
                errors += 1
                continue

            if sid in existing_servers and not overwrite:
                console.print(
                    f"[yellow]⊘ {sid}: already exists (use --overwrite)[/yellow]"
                )
                skipped += 1
                continue

            server_config: dict[str, Any] = {"command": cmd}
            args = entry.get("args", [])
            env = entry.get("env", {})
            if args:
                server_config["args"] = list(args)
            if env:
                server_config["env"] = dict(env)

            if dry_run:
                console.print(f"[dim]+ {sid}: {cmd}[/dim]")
                added += 1
                continue

            if selected_client == "vscode":
                config = {"mcp": {"servers": {sid: server_config}}}
            else:
                config = {"mcpServers": {sid: server_config}}

            write_client_config(
                client=selected_client,
                config=config,
                project_root=project_root,
                output_path=output_path,
            )
            write_mcp_client_settings(
                client=selected_client,
                settings={
                    "servers": {
                        sid: {
                            "enabled": True,
                            "auto_start": True,
                            "permissions": {
                                "default_mode": "confirm",
                                "allow": [],
                                "deny": [],
                                "confirm": [],
                            },
                        }
                    }
                },
                project_root=project_root,
                output_path=output_path,
            )
            existing_servers[sid] = server_config
            console.print(f"[green]✓ {sid}[/green]")
            added += 1

        prefix = "[dim]Dry run:[/dim] " if dry_run else ""
        console.print(
            f"\n{prefix}[green]{added} added[/green], "
            f"[yellow]{skipped} skipped[/yellow], "
            f"[red]{errors} errors[/red]"
        )
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("remove")
def mcp_remove(
    server_id: str = typer.Argument(..., help="Configured server id to remove"),
    client: str | None = typer.Option(
        None,
        "--client",
        help="Target client: claude-desktop, claude-code, cursor, vscode",
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help="Project root for Cursor/VS Code config lookup"
    ),
    output_path: Path | None = typer.Option(
        None, "--output", help="Override config path to modify"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview removal only"),
) -> None:
    """Remove a configured MCP server from a client config."""
    try:
        selected_client = _resolve_mcp_client(client)

        if selected_client == "claude-code":
            command = f"claude mcp remove {server_id}"
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(command + "\n", encoding="utf-8")
                console.print(
                    f"\n[green]✓ Removal command written to[/green] {output_path}"
                )
            else:
                console.print("\n[bold]Run this command in your terminal:[/bold]")
                console.print(f"  [green]{command}[/green]")
            return

        if dry_run:
            path, servers = get_configured_servers(
                client=selected_client,
                project_root=project_root,
                output_path=output_path,
            )
            preview = {
                "client": selected_client,
                "path": str(path) if path is not None else None,
                "server_id": server_id,
                "configured": server_id in servers,
            }
            console.print()
            console.print_json(json.dumps(preview))
            return

        written, removed = remove_server_from_config(
            client=selected_client,
            server_id=server_id,
            project_root=project_root,
            output_path=output_path,
        )
        if removed:
            console.print(f"\n[green]✓ Removed {server_id} from[/green] {written}")
        else:
            console.print(
                f"[yellow]Server '{server_id}' was not configured in {written}[/yellow]"
            )
    except Exception as exc:
        console.print(f"[red]Remove failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@mcp_app.command("catalog-update")
def mcp_catalog_update(
    url: str = typer.Option(CATALOG_URL, "--url", help="Source URL or local file path"),
) -> None:
    """Update the local MCP server catalog from the canonical JSON source."""
    try:
        updated_path = update_mcp_catalog(url=url)
        server_count = len(list_mcp_servers())
        console.print(
            f"[green]✓ Updated MCP catalog[/green] at {updated_path} [dim]({server_count} servers)[/dim]"
        )
    except Exception as exc:
        console.print(f"[red]Catalog update failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def chat(
    message: str | None = typer.Argument(None, help="Message to send to the LLM"),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        envvar=["STRATIFYAI_PROVIDER", "STRATUMAI_PROVIDER"],
        help="LLM provider (openai, anthropic, google, deepseek, groq, grok, ollama, openrouter, bedrock)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        envvar=["STRATIFYAI_MODEL", "STRATUMAI_MODEL"],
        help="Model name",
    ),
    temperature: float | None = typer.Option(
        None, "--temperature", "-t", min=0.0, max=2.0, help="Temperature (0.0-2.0)"
    ),
    max_tokens: int | None = typer.Option(
        None, "--max-tokens", help="Maximum tokens to generate"
    ),
    stream: bool = typer.Option(False, "--stream", help="Stream response in real-time"),
    system: str | None = typer.Option(None, "--system", "-s", help="System message"),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Load content from file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    cache_control: bool = typer.Option(
        False, "--cache-control", help="Enable prompt caching (for supported providers)"
    ),
    chunked: bool = typer.Option(
        False,
        "--chunked",
        help="Enable smart chunking and summarization for large files",
    ),
    chunk_size: int = typer.Option(
        50000, "--chunk-size", help="Chunk size in characters (default: 50000)"
    ),
    auto_select: bool = typer.Option(
        False,
        "--auto-select",
        help="Automatically select optimal model based on file type",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Prompt template name (e.g., code_review, summarize). Use 'stratifyai templates' to list available",
    ),
    params: str | None = typer.Option(
        None,
        "--params",
        help="Template parameters as key=value pairs, comma-separated (e.g., language=python,focus=security)",
    ),
):
    """Send a chat message to an LLM provider.

    Note: For multi-turn conversations with context, use 'stratifyai interactive' instead.
    """
    return _chat_impl(
        message,
        provider,
        model,
        temperature,
        max_tokens,
        stream,
        system,
        file,
        cache_control,
        chunked,
        chunk_size,
        auto_select=auto_select,
        template=template,
        params=params,
    )


def _chat_impl(
    message: str | None,
    provider: str | None,
    model: str | None,
    temperature: float | None,
    max_tokens: int | None,
    stream: bool,
    system: str | None,
    file: Path | None,
    cache_control: bool,
    chunked: bool = False,
    chunk_size: int = 50000,
    auto_select: bool = False,
    _conversation_history: list[Message] | None = None,
    template: str | None = None,
    params: str | None = None,
):
    """Internal implementation of chat with conversation history support."""
    # Show mode banner
    console.print(f"\n[{CHAT_ACCENT}]─── 💬 CHAT MODE ───[/{CHAT_ACCENT}]")
    console.print(
        "[dim]Single message mode - use 'interactive' for conversations[/dim]\n"
    )

    try:
        # Auto-select model based on file type if enabled
        if auto_select and file and not (provider and model):
            from stratifyai.utils.model_selector import select_model_for_file

            try:
                auto_provider, auto_model, reasoning = select_model_for_file(file)
                provider = auto_provider
                model = auto_model
                console.print(f"\n[cyan]🤖 Auto-selected:[/cyan] {provider}/{model}")
                console.print(f"[dim]   Reason: {reasoning}[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]⚠ Auto-selection failed: {e}[/yellow]")
                console.print("[dim]Falling back to manual selection...[/dim]\n")

        # Track if we prompted for provider/model to determine if we should prompt for file
        prompted_for_provider = False
        prompted_for_model = False

        # Interactive prompts if not provided
        if not provider:
            prompted_for_provider = True
            console.print("\n[bold cyan]Select Provider[/bold cyan]")
            providers_list = [
                "openai",
                "anthropic",
                "google",
                "deepseek",
                "groq",
                "grok",
                "ollama",
                "openrouter",
                "bedrock",
            ]
            for i, p in enumerate(providers_list, 1):
                console.print(f"  {i}. {p}")

            # Retry loop for provider selection
            max_attempts = 3
            for attempt in range(max_attempts):
                provider_choice = Prompt.ask(
                    mode_prompt("Choose provider", "chat"), default="1"
                )

                try:
                    provider_idx = int(provider_choice) - 1
                    if 0 <= provider_idx < len(providers_list):
                        provider = providers_list[provider_idx]
                        break
                    else:
                        console.print(
                            f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                        else:
                            console.print(
                                "[yellow]Too many invalid attempts. Using default: openai[/yellow]"
                            )
                            provider = "openai"
                except ValueError:
                    console.print(
                        "[red]✗ Invalid input.[/red] Please enter a number, not letters (e.g., '1' not 'openai')"
                    )
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")
                    else:
                        console.print(
                            "[yellow]Too many invalid attempts. Using default: openai[/yellow]"
                        )
                        provider = "openai"

        # Model selection with vision validation loop
        need_vision_model = (
            file
            and file.suffix.lower()
            in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
            if file
            else False
        )

        if not model:
            prompted_for_model = True
            # Validate and display models for selected provider
            from stratifyai.utils.provider_validator import (
                get_validated_interactive_models,
            )

            if provider in MODEL_CATALOG:
                # Show spinner while validating
                with console.status(
                    f"[cyan]Validating {provider} models...", spinner="dots"
                ):
                    validation_data = get_validated_interactive_models(provider)

                validation_result = validation_data["validation_result"]
                validated_models = validation_data["models"]

                # Show validation result
                if validation_result["error"]:
                    console.print(
                        "[yellow]⚠ Default models displayed. Could not validate models.[/yellow]"
                    )
                    # Fall back to MODEL_CATALOG if validation fails
                    available_models = list(MODEL_CATALOG[provider].keys())
                    model_metadata = MODEL_CATALOG[provider]
                else:
                    console.print(
                        f"[green]✓ Validated {len(validated_models)} models[/green] [dim]({validation_result['validation_time_ms']}ms)[/dim]"
                    )
                    available_models = list(validated_models.keys())
                    model_metadata = validated_models

                # Filter for vision models if image file provided
                if need_vision_model:
                    vision_models = [
                        m
                        for m in available_models
                        if model_metadata.get(m, {}).get("supports_vision", False)
                    ]
                    if vision_models:
                        console.print(
                            f"\n[bold cyan]Vision-capable models for {provider}:[/bold cyan]"
                        )
                        console.print("[dim](Filtered for image file support)[/dim]")
                        available_models = vision_models
                    else:
                        console.print(
                            f"\n[yellow]⚠ No vision-capable models available for {provider}[/yellow]"
                        )
                        console.print(
                            "[yellow]Please select a different provider or remove the image file[/yellow]"
                        )
                        raise typer.Exit(1)
                else:
                    console.print(
                        f"\n[bold cyan]Available {provider} models:[/bold cyan]"
                    )

                # Display with friendly names, descriptions, and categories (same as interactive mode)
                current_category = None
                for i, m in enumerate(available_models, 1):
                    meta = model_metadata.get(m, {})
                    display_name = meta.get("display_name", m)
                    description = meta.get("description", "")
                    category = meta.get("category", "")

                    # Show category header if changed
                    if category and category != current_category:
                        console.print(f"  [dim]── {category} ──[/dim]")
                        current_category = category

                    label = f"  {i}. {display_name}"
                    if description:
                        label += f" [dim]- {description}[/dim]"
                    console.print(label)

                # Retry loop for model selection
                max_attempts = 3
                model = None
                for attempt in range(max_attempts):
                    model_choice = Prompt.ask(mode_prompt("Select model", "chat"))

                    try:
                        model_idx = int(model_choice) - 1
                        if 0 <= model_idx < len(available_models):
                            model = available_models[model_idx]
                            break
                        else:
                            console.print(
                                f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}"
                            )
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(
                            "[red]✗ Invalid input.[/red] Please enter a number, not the model name (e.g., '2' not 'gpt-4o')"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")

                # If still no valid model after retries, exit
                if model is None:
                    console.print("[red]Too many invalid attempts. Exiting.[/red]")
                    raise typer.Exit(1)
            else:
                console.print(f"[red]No models found for provider: {provider}[/red]")
                raise typer.Exit(1)

        # Check if model has fixed temperature
        if temperature is None:
            model_info = MODEL_CATALOG.get(provider or "", {}).get(model, {})
            fixed_temp = model_info.get("fixed_temperature")

            if fixed_temp is not None:
                temperature = fixed_temp
                console.print(
                    f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]"
                )
            else:
                # Retry loop for temperature input
                max_attempts = 3
                temperature = None
                for attempt in range(max_attempts):
                    temp_input = Prompt.ask(
                        mode_prompt("Temperature (0.0-2.0)", "chat"), default="0.7"
                    )

                    try:
                        temp_value = float(temp_input)
                        if 0.0 <= temp_value <= 2.0:
                            temperature = temp_value
                            break
                        else:
                            console.print(
                                "[red]✗ Out of range.[/red] Temperature must be between 0.0 and 2.0"
                            )
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(
                            f"[red]✗ Invalid input.[/red] Please enter a number (e.g., '0.7' not '{temp_input}')"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")

                # If still no valid temperature after retries, use default
                if temperature is None:
                    console.print(
                        "[yellow]Too many invalid attempts. Using default: 0.7[/yellow]"
                    )
                    temperature = 0.7

        # Prompt for file if not provided via flag (only in fully interactive mode and non-follow-up messages)
        # Only prompt if we also prompted for provider AND model (fully interactive)
        if (
            not file
            and _conversation_history is None
            and prompted_for_provider
            and prompted_for_model
        ):
            console.print("\n[bold cyan]File Attachment (Optional)[/bold cyan]")
            console.print(
                "[dim]Attach a file to include its content in your message[/dim]"
            )
            console.print("[dim]Max file size: 5 MB | Leave blank to skip[/dim]")

            # File prompt with retry loop
            max_file_attempts = 3
            file = None
            for file_attempt in range(max_file_attempts):
                file_path_input = Prompt.ask(
                    mode_prompt("File path (or Enter to skip)", "chat"), default=""
                )

                if not file_path_input.strip():
                    # User pressed Enter to skip
                    break

                file = Path(file_path_input.strip()).expanduser()

                # Validate file exists and is readable
                if not file.exists():
                    console.print(f"[red]✗ File not found: {file}[/red]")
                    if file_attempt < max_file_attempts - 1:
                        choice = Prompt.ask(
                            "[cyan]Enter 1 to retry file path or 2 to continue without file[/cyan]",
                            choices=["1", "2"],
                            default="2",
                        )
                        if choice == "2":
                            file = None
                            break
                        # Otherwise loop continues for retry
                    else:
                        console.print("[dim]Continuing without file attachment[/dim]")
                        file = None
                elif not file.is_file():
                    console.print(f"[red]✗ Path is not a file: {file}[/red]")
                    if file_attempt < max_file_attempts - 1:
                        choice = Prompt.ask(
                            "[cyan]Enter 1 to retry file path or 2 to continue without file[/cyan]",
                            choices=["1", "2"],
                            default="2",
                        )
                        if choice == "2":
                            file = None
                            break
                    else:
                        console.print("[dim]Continuing without file attachment[/dim]")
                        file = None
                else:
                    # File is valid, break out of retry loop
                    break

        # Load content from file if provided
        file_content: str | None = None
        if file:
            try:
                # Check if file is an image
                image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                is_image = file.suffix.lower() in image_extensions

                if is_image:
                    # For image files, check if model supports vision
                    model_info = MODEL_CATALOG.get(provider or "", {}).get(model, {})
                    supports_vision = bool(model_info.get("supports_vision", False))

                    if not supports_vision:
                        console.print(
                            f"\n[red]✗ Vision not supported: {model} cannot process image files[/red]"
                        )
                        console.print(
                            "[yellow]⚠️ This model cannot process images. Please select a vision-capable model.[/yellow]"
                        )
                        console.print(
                            "\n[cyan]Returning to model selection...[/cyan]\n"
                        )

                        # Return to model selection - call chat command recursively with vision-required flag
                        # Pass message=None to force prompting for message after model selection
                        import sys

                        sys.argv = [
                            "stratifyai",
                            "chat",
                            "--provider",
                            provider or "",
                            "--file",
                            str(file),
                        ]
                        if system:
                            sys.argv.extend(["--system", system])
                        if max_tokens:
                            sys.argv.extend(["--max-tokens", str(max_tokens)])
                        chat(
                            provider=provider,
                            model=None,
                            message=None,
                            system=system,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            file=file,
                            stream=stream,
                            cache_control=cache_control,
                            chunked=chunked,
                            chunk_size=chunk_size,
                            auto_select=auto_select,
                        )
                        return

                    # Read image as base64
                    import base64

                    with open(file, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode("utf-8")

                    # Get file size
                    file_size = file.stat().st_size
                    file_size_kb = file_size / 1024
                    file_size_mb = file_size / (1024 * 1024)

                    size_str = (
                        f"{file_size_kb:.1f} KB"
                        if file_size_kb < 1024
                        else f"{file_size_mb:.2f} MB"
                    )
                    console.print(
                        f"[green]✓ Loaded {file.name}[/green] [dim]({size_str}, image)[/dim]"
                    )

                    # Return base64 image data with metadata
                    mime_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".gif": "image/gif",
                        ".webp": "image/webp",
                        ".bmp": "image/bmp",
                    }.get(file.suffix.lower(), "image/jpeg")

                    file_content = f"[IMAGE:{mime_type}]\n{image_data}"
                else:
                    # Read text file
                    with open(file, encoding="utf-8") as text_file:
                        file_content = text_file.read()

                    # Get file size for display
                    if isinstance(file, Path) and file.exists():
                        file_size = file.stat().st_size
                        file_size_mb = file_size / (1024 * 1024)
                        file_size_kb = file_size / 1024

                        if file_size_kb < 1:
                            size_str = f"{file_size} bytes"
                        elif file_size_mb < 1:
                            size_str = f"{file_size_kb:.1f} KB"
                        else:
                            size_str = f"{file_size_mb:.2f} MB"

                        console.print(
                            f"[green]✓ Loaded {file.name}[/green] [dim]({size_str}, {len(file_content):,} chars)[/dim]"
                        )

                        # Analyze file if chunking enabled
                        if chunked:
                            analysis = analyze_file(
                                file, provider or "openai", model or "gpt-4o"
                            )
                            console.print("[cyan]File Analysis:[/cyan]")
                            console.print(f"  Type: {analysis.file_type.value}")
                            console.print(f"  Tokens: ~{analysis.estimated_tokens:,}")
                            console.print(
                                f"  Recommendation: {analysis.recommendation}"
                            )

                            if analysis.exceeds_threshold:
                                console.print(
                                    f"[yellow]⚠ {analysis.recommendation}[/yellow]"
                                )
            except Exception as e:
                console.print(f"[red]Error reading file {file}: {e}[/red]")
                raise typer.Exit(1) from e

        # Handle template rendering if provided
        is_image_file = bool(
            file
            and file.suffix.lower()
            in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        )
        template_messages = None
        if template:
            try:
                from stratifyai.prompts import registry

                # Parse template parameters
                template_params = {}
                if params:
                    for param_pair in params.split(","):
                        if "=" in param_pair:
                            key, value = param_pair.split("=", 1)
                            template_params[key.strip()] = value.strip()

                # If file is provided, inject it as the first text parameter
                if file_content and not is_image_file:
                    # Find the first required text/text parameter in template
                    tmpl = registry.get(template)
                    for param in tmpl.parameters:
                        if param.required and param.type in ("text", "string"):
                            template_params[param.name] = file_content
                            break

                # Render template
                template_messages = registry.render(template, **template_params)
                console.print(f"[green]✓ Applied template:[/green] {template}")
            except KeyError as e:
                console.print(f"[red]✗ Template error:[/red] {e}")
                raise typer.Exit(1) from e
            except ValueError as e:
                console.print(f"[red]✗ Template parameter error:[/red] {e}")
                raise typer.Exit(1) from e

        # Prompt for message if not provided
        # For image files, always prompt (user needs to provide instructions for the image)
        # For text files, only prompt if no file content
        is_image_file = bool(
            file
            and file.suffix.lower()
            in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        )

        if not message and not template:
            if is_image_file or not file_content:
                console.print(f"\n[{CHAT_ACCENT}]Enter your message:[/{CHAT_ACCENT}]")
                message = Prompt.ask(mode_prompt("Message", "chat"))

        # Build messages - use conversation history if this is a follow-up
        if _conversation_history is None:
            # Start with template messages if provided
            if template_messages:
                messages = list(template_messages)
            else:
                messages = []
                if system:
                    messages.append(Message(role="system", content=system))
        else:
            messages = _conversation_history.copy()

        # Add file content or message
        if file_content:
            # Check if chunking is needed
            if chunked:
                console.print("\n[cyan]Chunking and summarizing file...[/cyan]")

                # Create client for summarization
                client = LLMClient(provider=provider)

                # Summarize file
                result = summarize_file(
                    file_content,
                    client,
                    chunk_size=chunk_size,
                    model=model,  # Use selected model for summarization
                    context=(
                        f"Analyzing file: {file.name if isinstance(file, Path) else 'uploaded file'}"
                        if message is None
                        else message
                    ),
                    show_progress=True,
                )

                # Show reduction stats
                console.print("[green]✓ Summarization complete[/green]")
                console.print(
                    f"[dim]Original: {result['original_length']:,} chars | Summary: {result['summary_length']:,} chars | Reduction: {result['reduction_percentage']}%[/dim]"
                )

                # Use summary as content
                content = (
                    f"{message}\n\nFile Summary:\n{result['summary']}"
                    if message
                    else f"File Summary:\n{result['summary']}"
                )
            else:
                # If both file and message provided, combine them
                content = f"{message}\n\n{file_content}" if message else file_content

            # Add cache control for large content if requested
            if cache_control and len(file_content) > 1000:
                messages.append(
                    Message(
                        role="user",
                        content=content,
                        cache_control={"type": "ephemeral"},
                    )
                )
            else:
                messages.append(Message(role="user", content=content))
        else:
            messages.append(Message(role="user", content=message or ""))

        # Create client and request
        client = LLMClient(provider=provider)
        request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Execute request
        response_content = ""

        # Get model info for context window
        model_info = MODEL_CATALOG.get(provider or "", {}).get(model, {})
        context_window = model_info.get("context", "N/A")

        if stream:

            async def _stream_and_collect() -> str:
                collected = ""
                async for chunk in client.chat_completion_stream(request):
                    print(chunk.content, end="", flush=True)
                    collected += chunk.content
                return collected

            # Display metadata before streaming
            console.print(
                f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]"
            )
            console.print(f"[dim]Context: {context_window:,} tokens[/dim]")
            console.print()  # Newline before streaming

            response_content = run_sync(_stream_and_collect())
            print()  # Final newline
        else:
            # Show spinner while waiting for response
            with console.status("[cyan]Thinking...", spinner="dots"):
                response = client.chat_completion_sync(request)
                response_content = response.content

            # Display metadata before response (chat mode - magenta)
            console.print(
                f"\n[bold]Provider:[/bold] [{CHAT_COLOR}]{provider}[/{CHAT_COLOR}] | [bold]Model:[/bold] [{CHAT_COLOR}]{model}[/{CHAT_COLOR}]"
            )

            # Build usage line with token breakdown and cache info
            usage_parts = [
                f"Context: {context_window:,} tokens",
                f"In: {response.usage.prompt_tokens:,}",
                f"Out: {response.usage.completion_tokens:,}",
                f"Total: {response.usage.total_tokens:,}",
                f"Cost: ${response.usage.cost_usd:.6f}",
            ]

            # Add latency if available
            if response.latency_ms is not None:
                usage_parts.append(f"Latency: {response.latency_ms:.0f}ms")

            # Add cache statistics if available
            if response.usage.cached_tokens > 0:
                usage_parts.append(f"Cached: {response.usage.cached_tokens:,}")
            if response.usage.cache_creation_tokens > 0:
                usage_parts.append(
                    f"Cache Write: {response.usage.cache_creation_tokens:,}"
                )
            if response.usage.cache_read_tokens > 0:
                usage_parts.append(f"Cache Read: {response.usage.cache_read_tokens:,}")

            console.print(f"[dim]{' | '.join(usage_parts)}[/dim]")

            # Print response with chat mode color (magenta)
            console.print(f"\n{response_content}", style=CHAT_COLOR)

        # Add assistant response to history for multi-turn conversation
        messages.append(Message(role="assistant", content=response_content))

        # Ask what to do next
        console.print(
            "\n[dim]Options: [1] Continue conversation  [2] Save & continue  [3] Save & exit  [4] Exit[/dim]"
        )
        next_action = Prompt.ask(
            mode_prompt("What would you like to do?", "chat"),
            choices=["1", "2", "3", "4"],
            default="1",
        )

        # Handle save requests
        if next_action in ["2", "3"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"response_{timestamp}.md"

            filename = Prompt.ask("\nFilename", default=default_filename)

            # Ensure .md extension
            if not filename.endswith(".md"):
                filename += ".md"

            try:
                with open(filename, "w", encoding="utf-8") as output_file:
                    output_file.write("# LLM Response\n\n")
                    output_file.write(f"**Provider:** {provider}\n")
                    output_file.write(f"**Model:** {model}\n")
                    output_file.write(
                        f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )
                    output_file.write("## Conversation\n\n")

                    # Write full conversation history
                    for msg in messages:
                        if msg.role == "user":
                            output_file.write(f"**You:** {msg.content}\n\n")
                        elif msg.role == "assistant":
                            output_file.write(f"**Assistant:** {msg.content}\n\n")

                console.print(f"[green]✓ Saved to {filename}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to save: {e}[/red]")

        # Exit if requested
        if next_action in ["3", "4"]:
            console.print("[dim]Goodbye![/dim]")
            return

        # Continue conversation (options "1" or "2")
        # Suggest interactive mode for better UX
        if _conversation_history is None and len(messages) > 2:
            console.print(
                "\n[dim]Tip: Use 'stratifyai interactive' for a better multi-turn conversation experience[/dim]"
            )

        # Recursive call with conversation history
        _chat_impl(
            None,
            provider,
            model,
            temperature,
            max_tokens,
            stream,
            None,
            None,
            False,
            chunked,
            chunk_size,
            False,
            messages,
        )

    except InvalidProviderError as e:
        console.print(f"[red]Invalid provider:[/red] {e}")
        raise typer.Exit(1) from e
    except InvalidModelError as e:
        console.print(f"[red]Invalid model:[/red] {e}")
        raise typer.Exit(1) from e
    except AuthenticationError as e:
        console.print("\n[red]✗ Authentication Failed[/red]")
        console.print(f"[yellow]Provider:[/yellow] {e.provider}")
        console.print("[yellow]Issue:[/yellow] API key is missing or invalid\n")

        # Get environment variable name for the provider
        env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")

        console.print("[bold cyan]How to fix:[/bold cyan]")
        console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
        console.print(f'     export {env_var}="your-api-key-here"')
        console.print(
            "\n  2. Or add to your [green].env[/green] file in the project root:"
        )
        console.print(f"     {env_var}=your-api-key-here\n")

        # Provider-specific instructions
        if e.provider == "openai":
            console.print(
                "[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]"
            )
        elif e.provider == "anthropic":
            console.print(
                "[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]"
            )
        elif e.provider == "google":
            console.print(
                "[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]"
            )
        elif e.provider == "deepseek":
            console.print(
                "[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]"
            )
        elif e.provider == "groq":
            console.print(
                "[dim]Get your API key from: https://console.groq.com/keys[/dim]"
            )
        elif e.provider == "grok":
            console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
        elif e.provider == "openrouter":
            console.print(
                "[dim]Get your API key from: https://openrouter.ai/keys[/dim]"
            )
        elif e.provider == "ollama":
            console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")

        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def models(
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="Filter by provider"
    ),
):
    """List available models."""

    try:
        # Create table
        table = Table(
            title="Available Models", show_header=True, header_style="bold magenta"
        )
        table.add_column("Provider", style="cyan", width=12)
        table.add_column("Model", style="green", width=40)
        table.add_column("Context", justify="right", style="yellow", width=10)

        # Populate table
        total_models = 0
        for prov_name, models_dict in MODEL_CATALOG.items():
            if provider and prov_name != provider:
                continue

            for model_name, model_info in models_dict.items():
                context = model_info.get("context", 0)
                table.add_row(
                    prov_name, model_name, f"{context:,}" if context else "N/A"
                )
                total_models += 1

        # Display table
        console.print(table)
        console.print(f"\n[dim]Total: {total_models} models[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def providers():
    """List all available providers."""

    try:
        # Create table
        table = Table(
            title="Available Providers", show_header=True, header_style="bold magenta"
        )
        table.add_column("Provider", style="cyan", width=15)
        table.add_column("Models", justify="right", style="green", width=10)
        table.add_column("Example Model", style="yellow", width=40)

        # Populate table
        for prov_name, models_dict in MODEL_CATALOG.items():
            example_model = list(models_dict.keys())[0] if models_dict else "N/A"
            table.add_row(prov_name, str(len(models_dict)), example_model)

        # Display table
        console.print(table)
        console.print(f"\n[dim]Total: {len(MODEL_CATALOG)} providers[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def route(
    message: str = typer.Argument(..., help="Message to analyze for routing"),
    strategy: str = typer.Option(
        "hybrid",
        "--strategy",
        "-s",
        help="Routing strategy (cost, quality, latency, hybrid)",
    ),
    execute: bool = typer.Option(
        False, "--execute", "-e", help="Execute with selected model"
    ),
    max_cost: float | None = typer.Option(
        None, "--max-cost", help="Maximum cost per 1K tokens"
    ),
    max_latency: int | None = typer.Option(
        None, "--max-latency", help="Maximum latency in milliseconds"
    ),
    capability: list[str] | None = typer.Option(
        None,
        "--capability",
        "-c",
        help="Required capability (vision, tools, reasoning). Can be specified multiple times.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show routing reasoning and ranked candidates without making an API call.",
    ),
):
    """Auto-select best model using router."""

    try:
        # Map strategy string to enum
        strategy_map = {
            "cost": RoutingStrategy.COST,
            "quality": RoutingStrategy.QUALITY,
            "latency": RoutingStrategy.LATENCY,
            "hybrid": RoutingStrategy.HYBRID,
        }

        if strategy not in strategy_map:
            console.print(
                f"[red]Invalid strategy:[/red] {strategy}. Use: cost, quality, latency, or hybrid"
            )
            raise typer.Exit(1)

        if dry_run and execute:
            console.print("[red]Cannot use --execute and --dry-run together.[/red]")
            raise typer.Exit(1)

        # Create router and route
        router = Router(
            strategy=strategy_map[strategy],
            excluded_providers=["ollama"],  # Exclude local models by default
        )

        messages = [Message(role="user", content=message)]

        # Validate capabilities
        valid_capabilities = ["vision", "tools", "reasoning"]
        if capability:
            for cap in capability:
                if cap not in valid_capabilities:
                    console.print(
                        f"[red]Invalid capability:[/red] {cap}. Use: vision, tools, or reasoning"
                    )
                    raise typer.Exit(1)

        # Route with constraints
        provider, model = router.route(
            messages,
            required_capabilities=capability,
            max_cost_per_1k_tokens=max_cost,
            max_latency_ms=max_latency,
        )

        # Get complexity and model info
        complexity = router._analyze_complexity(messages)
        model_info = router.get_model_info(provider, model)

        # Display routing decision
        console.print("\n[bold]Routing Decision[/bold]")
        console.print(f"Strategy: [cyan]{strategy}[/cyan]")
        if capability:
            console.print(f"Required: [magenta]{', '.join(capability)}[/magenta]")
        console.print(f"Complexity: [yellow]{complexity:.3f}[/yellow]")
        console.print(f"Selected: [green]{provider}/{model}[/green]")
        if model_info and model_info.capabilities:
            console.print(
                f"Capabilities: [magenta]{', '.join(model_info.capabilities)}[/magenta]"
            )
        if model_info is not None:
            console.print(f"Quality: [yellow]{model_info.quality_score:.2f}[/yellow]")
            console.print(
                f"Latency: [yellow]{model_info.avg_latency_ms:.0f}ms[/yellow]"
            )

        if dry_run:
            candidates = router._filter_candidates(
                required_capabilities=capability,
                max_cost_per_1k=max_cost,
                max_latency_ms=max_latency,
                min_context_window=None,
            )
            scores = router._score_candidates(candidates, complexity)
            ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

            weights: str
            if strategy_map[strategy] == RoutingStrategy.HYBRID:
                quality_weight = 0.1 + (complexity * 0.5)
                cost_weight = 0.6 - (complexity * 0.3)
                latency_weight = 0.3 - (complexity * 0.2)
                weights = (
                    f"quality={quality_weight:.2f}, "
                    f"cost={cost_weight:.2f}, "
                    f"latency={latency_weight:.2f}"
                )
            else:
                weights = strategy_map[strategy].value

            console.print(f"Reasoning: [dim]{weights}[/dim]")

            table = Table(
                title="Routing Candidates (Dry Run)",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Rank", justify="right")
            table.add_column("Provider", style="cyan")
            table.add_column("Model", style="green")
            table.add_column("Score", justify="right")
            table.add_column("Cost/1K", justify="right")
            table.add_column("Latency", justify="right")
            table.add_column("Capabilities", style="magenta")

            for index, (key, score) in enumerate(ranked[:5], start=1):
                meta = candidates[key]
                avg_cost_per_1k = (
                    meta.cost_per_1m_input + meta.cost_per_1m_output
                ) / 1000
                table.add_row(
                    str(index),
                    meta.provider,
                    meta.model,
                    f"{score:.3f}",
                    f"${avg_cost_per_1k:.4f}",
                    f"{meta.avg_latency_ms:.0f}ms",
                    ", ".join(meta.capabilities) if meta.capabilities else "-",
                )

            console.print(table)
            return

        # Execute if requested
        if execute or Confirm.ask("\nExecute with this model?", default=True):
            client = LLMClient(provider=provider)
            request = ChatRequest(model=model, messages=messages)

            # Show spinner while waiting for response
            with console.status("[cyan]Thinking...", spinner="dots"):
                response = client.chat_completion_sync(request)

            # Get model info for context window
            route_model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
            route_context = route_model_info.get("context", "N/A")

            console.print(
                f"\n[bold]Provider:[/bold] [cyan]{provider}[/cyan] | [bold]Model:[/bold] [cyan]{model}[/cyan]"
            )
            console.print(
                f"[dim]Context: {route_context:,} tokens | Tokens: {response.usage.total_tokens} | Cost: ${response.usage.cost_usd:.6f}[/dim]"
            )
            console.print(f"\n{response.content}", style="cyan")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def interactive(
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        envvar=["STRATIFYAI_PROVIDER", "STRATUMAI_PROVIDER"],
        help="LLM provider",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        envvar=["STRATIFYAI_MODEL", "STRATUMAI_MODEL"],
        help="Model name",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Load initial context from file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """Start interactive chat session."""

    # File upload constraints
    MAX_FILE_SIZE_MB = 5
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    LARGE_FILE_THRESHOLD_KB = 500
    client: LLMClient | None = None
    temperature: float | None = None

    try:
        # Helper function to load file with size validation and intelligent extraction
        def load_file_content(
            file_path: Path, warn_large: bool = True, check_vision: bool = False
        ) -> str | None:
            """Load file content with size restrictions, warnings, and intelligent extraction.

            Args:
                file_path: Path to the file to load
                warn_large: Whether to warn about large files
                check_vision: Whether to check for vision support for image files
            """
            # Declare nonlocal variables at the top before any use
            nonlocal model, client, temperature

            try:
                # Check if file exists
                if not file_path.exists():
                    console.print(f"[red]✗ File not found: {file_path}[/red]")
                    return None

                # Check if file is an image
                image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
                is_image = file_path.suffix.lower() in image_extensions

                if is_image:
                    # For image files, check if model supports vision
                    if check_vision:
                        model_info = MODEL_CATALOG.get(provider or "", {}).get(
                            model or "", {}
                        )
                        supports_vision = bool(model_info.get("supports_vision", False))

                        if not supports_vision:
                            console.print(
                                f"\n[red]✗ Vision not supported: {model} cannot process image files[/red]"
                            )
                            console.print(
                                "[yellow]⚠️ This model cannot process images. Switching to vision-capable model...[/yellow]"
                            )

                            # Offer to switch to a vision model
                            choice = Prompt.ask(
                                "[cyan]Enter 1 to select a vision-capable model or 2 to continue without image[/cyan]",
                                choices=["1", "2"],
                                default="1",
                            )

                            if choice == "1":
                                if provider is None:
                                    return None

                                # Show vision-capable models for current provider (like chat mode)
                                from stratifyai.utils.provider_validator import (
                                    get_validated_interactive_models,
                                )

                                # Validate and get models
                                with console.status(
                                    f"[cyan]Validating {provider} models...",
                                    spinner="dots",
                                ):
                                    validation_data = get_validated_interactive_models(
                                        provider
                                    )

                                validation_result = validation_data["validation_result"]
                                validated_models = validation_data["models"]

                                # Get model metadata
                                if validation_result["error"]:
                                    available_models = list(
                                        MODEL_CATALOG[provider].keys()
                                    )
                                    model_metadata = MODEL_CATALOG[provider]
                                else:
                                    available_models = list(validated_models.keys())
                                    model_metadata = validated_models

                                # Filter for vision models
                                vision_models = [
                                    m
                                    for m in available_models
                                    if model_metadata.get(m, {}).get(
                                        "supports_vision", False
                                    )
                                ]

                                if not vision_models:
                                    console.print(
                                        f"\n[yellow]⚠ No vision-capable models available for {provider}[/yellow]"
                                    )
                                    console.print(
                                        "[yellow]Please use /provider to select a different provider[/yellow]\n"
                                    )
                                    return None

                                # Show vision models
                                console.print(
                                    f"\n[bold cyan]Vision-capable models for {provider}:[/bold cyan]"
                                )
                                console.print(
                                    "[dim](Filtered for image file support)[/dim]"
                                )

                                # Display with categories and descriptions
                                current_category = None
                                for i, m in enumerate(vision_models, 1):
                                    meta = model_metadata.get(m, {})
                                    display_name = meta.get("display_name", m)
                                    description = meta.get("description", "")
                                    category = meta.get("category", "")

                                    # Show category header if changed
                                    if category and category != current_category:
                                        console.print(f"  [dim]── {category} ──[/dim]")
                                        current_category = category

                                    current_marker = (
                                        " [green](current)[/green]"
                                        if m == model
                                        else ""
                                    )
                                    label = f"  {i}. {display_name}{current_marker}"
                                    if description:
                                        label += f" [dim]- {description}[/dim]"
                                    console.print(label)

                                # Get model selection
                                max_attempts = 3
                                new_model = None
                                for attempt in range(max_attempts):
                                    model_choice = Prompt.ask("\nSelect vision model")
                                    try:
                                        model_idx = int(model_choice) - 1
                                        if 0 <= model_idx < len(vision_models):
                                            new_model = vision_models[model_idx]
                                            break
                                        else:
                                            console.print(
                                                f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(vision_models)}"
                                            )
                                            if attempt < max_attempts - 1:
                                                console.print("[dim]Try again...[/dim]")
                                    except ValueError:
                                        console.print(
                                            "[red]✗ Invalid input.[/red] Please enter a number"
                                        )
                                        if attempt < max_attempts - 1:
                                            console.print("[dim]Try again...[/dim]")

                                if new_model:
                                    # Update the outer scope model variable
                                    model = new_model

                                    # Check if new model has fixed temperature and prompt if needed
                                    new_model_info = MODEL_CATALOG.get(
                                        provider, {}
                                    ).get(model, {})
                                    fixed_temp = new_model_info.get("fixed_temperature")

                                    if fixed_temp is not None:
                                        temperature = fixed_temp
                                        console.print(
                                            f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]"
                                        )
                                    else:
                                        # Retry loop for temperature input
                                        max_temp_attempts = 3
                                        temperature = None
                                        for temp_attempt in range(max_temp_attempts):
                                            temp_input = Prompt.ask(
                                                "\n[bold cyan]Temperature[/bold cyan] (0.0-2.0, default 0.7)",
                                                default="0.7",
                                            )

                                            try:
                                                temp_value = float(temp_input)
                                                if 0.0 <= temp_value <= 2.0:
                                                    temperature = temp_value
                                                    break
                                                else:
                                                    console.print(
                                                        "[red]✗ Out of range.[/red] Temperature must be between 0.0 and 2.0"
                                                    )
                                                    if (
                                                        temp_attempt
                                                        < max_temp_attempts - 1
                                                    ):
                                                        console.print(
                                                            "[dim]Try again...[/dim]"
                                                        )
                                            except ValueError:
                                                console.print(
                                                    f"[red]✗ Invalid input.[/red] Please enter a number (e.g., '0.7' not '{temp_input}')"
                                                )
                                                if temp_attempt < max_temp_attempts - 1:
                                                    console.print(
                                                        "[dim]Try again...[/dim]"
                                                    )

                                        # If still no valid temperature after retries, use default
                                        if temperature is None:
                                            console.print(
                                                "[yellow]Too many invalid attempts. Using default: 0.7[/yellow]"
                                            )
                                            temperature = 0.7

                                    # Reinitialize client with new model
                                    client = LLMClient(provider=provider)

                                    # Update context window info
                                    context_window = new_model_info.get(
                                        "context", "N/A"
                                    )

                                    console.print(
                                        f"\n[green]✓ Switched to:[/green] [cyan]{model}[/cyan] | [dim]Context: {context_window:,} tokens[/dim]"
                                    )

                                    # Now try loading the image again (recursively call with updated model)
                                    return load_file_content(
                                        file_path, warn_large, check_vision=True
                                    )
                                else:
                                    console.print("[yellow]Model not changed[/yellow]")

                            return None

                    # Read image as base64
                    import base64

                    with open(file_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("utf-8")

                    # Get file size
                    file_size = file_path.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    file_size_kb = file_size / 1024

                    # Check size limit
                    if file_size > MAX_FILE_SIZE_BYTES:
                        console.print(
                            f"[red]✗ Image too large: {file_size_mb:.2f} MB (max {MAX_FILE_SIZE_MB} MB)[/red]"
                        )
                        return None

                    size_str = (
                        f"{file_size_kb:.1f} KB"
                        if file_size_kb < 1024
                        else f"{file_size_mb:.2f} MB"
                    )
                    console.print(
                        f"[green]✓ Loaded {file_path.name}[/green] [dim]({size_str}, image)[/dim]"
                    )

                    # Return base64 image data with metadata
                    mime_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".gif": "image/gif",
                        ".webp": "image/webp",
                        ".bmp": "image/bmp",
                    }.get(file_path.suffix.lower(), "image/jpeg")

                    return f"[IMAGE:{mime_type}]\n{image_data}"

                # For non-image files, continue with existing logic

                # Check file size
                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                file_size_kb = file_size / 1024

                # Enforce size limit
                if file_size > MAX_FILE_SIZE_BYTES:
                    console.print(
                        f"[red]✗ File too large: {file_size_mb:.2f} MB (max {MAX_FILE_SIZE_MB} MB)[/red]"
                    )
                    console.print(
                        "[yellow]⚠ Large files consume significant tokens and may exceed model context limits[/yellow]"
                    )
                    return None

                # Check if file type supports intelligent extraction
                extension = file_path.suffix.lower()
                supports_extraction = (
                    extension in [".csv", ".json", ".log", ".py"]
                    or "log" in file_path.name.lower()
                )

                # For large files that support extraction, offer schema extraction
                if supports_extraction and file_size > (LARGE_FILE_THRESHOLD_KB * 1024):
                    console.print(
                        f"[cyan]💡 Large {extension} file detected: {file_size_kb:.1f} KB[/cyan]"
                    )
                    console.print(
                        "[cyan]This file supports intelligent extraction for efficient LLM processing[/cyan]"
                    )

                    use_extraction = Confirm.ask(
                        "Extract schema/structure instead of loading full file? (Recommended)",
                        default=True,
                    )

                    if use_extraction:
                        try:
                            from stratifyai.utils.code_extractor import (
                                analyze_code_file,
                            )
                            from stratifyai.utils.csv_extractor import analyze_csv_file
                            from stratifyai.utils.json_extractor import (
                                analyze_json_file,
                            )
                            from stratifyai.utils.log_extractor import (
                                extract_log_summary,
                            )

                            result: Any
                            if extension == ".csv":
                                result = analyze_csv_file(file_path)
                                content: str = result["schema_text"]
                                reduction = result["token_reduction_pct"]
                                console.print(
                                    f"[green]✓ Extracted CSV schema[/green] [dim]({reduction:.1f}% token reduction)[/dim]"
                                )
                            elif extension == ".json":
                                result = analyze_json_file(file_path)
                                content = str(result.get("schema_text", str(result)))
                                reduction = result.get("token_reduction_pct", 0)
                                console.print(
                                    f"[green]✓ Extracted JSON schema[/green] [dim]({reduction:.1f}% token reduction)[/dim]"
                                )
                            elif (
                                extension in [".log", ".txt"]
                                and "log" in file_path.name.lower()
                            ):
                                result = extract_log_summary(file_path)
                                content = result["summary_text"]
                                reduction = result["token_reduction_pct"]
                                console.print(
                                    f"[green]✓ Extracted log summary[/green] [dim]({reduction:.1f}% token reduction)[/dim]"
                                )
                            elif extension == ".py":
                                result = analyze_code_file(file_path)
                                content = result["structure_text"]
                                reduction = result["token_reduction_pct"]
                                console.print(
                                    f"[green]✓ Extracted code structure[/green] [dim]({reduction:.1f}% token reduction)[/dim]"
                                )
                            else:
                                # Fallback to raw content
                                with open(file_path, encoding="utf-8") as text_file:
                                    content = text_file.read()
                                console.print(
                                    f"[green]✓ Loaded {file_path.name}[/green] [dim]({file_size_kb:.1f} KB, {len(content):,} chars)[/dim]"
                                )

                            return str(content)
                        except Exception as e:
                            console.print(f"[yellow]⚠ Extraction failed: {e}[/yellow]")
                            console.print(
                                "[dim]Falling back to loading full file...[/dim]"
                            )
                            # Fall through to normal loading

                # Warn about large files (if not using extraction)
                if warn_large and file_size > (LARGE_FILE_THRESHOLD_KB * 1024):
                    console.print(
                        f"[yellow]⚠ Large file detected: {file_size_kb:.1f} KB[/yellow]"
                    )
                    console.print(
                        "[yellow]⚠ This will consume substantial tokens and may incur significant costs[/yellow]"
                    )

                    if not Confirm.ask("Continue loading full file?", default=False):
                        console.print("[dim]File load cancelled[/dim]")
                        return None

                # Read file content normally
                with open(file_path, encoding="utf-8") as text_file:
                    content = text_file.read()

                # Display success message
                if file_size_kb < 1:
                    size_str = f"{file_size} bytes"
                elif file_size_mb < 1:
                    size_str = f"{file_size_kb:.1f} KB"
                else:
                    size_str = f"{file_size_mb:.2f} MB"

                console.print(
                    f"[green]✓ Loaded {file_path.name}[/green] [dim]({size_str}, {len(content):,} chars)[/dim]"
                )
                return str(content)

            except UnicodeDecodeError:
                console.print(
                    f"[red]✗ Cannot read file: {file_path.name} (not a text file)[/red]"
                )
                return None
            except Exception as e:
                console.print(f"[red]✗ Error reading file: {e}[/red]")
                return None

        # Prompt for provider and model if not provided
        model_was_preselected = model is not None
        if not provider:
            console.print("\n[bold cyan]Select Provider[/bold cyan]")
            providers_list = [
                "openai",
                "anthropic",
                "google",
                "deepseek",
                "groq",
                "grok",
                "ollama",
                "openrouter",
                "bedrock",
            ]
            for i, p in enumerate(providers_list, 1):
                console.print(f"  {i}. {p}")

            # Retry loop for provider selection
            max_attempts = 3
            for attempt in range(max_attempts):
                provider_choice = Prompt.ask(
                    mode_prompt("Choose provider", "interactive"), default="1"
                )

                try:
                    provider_idx = int(provider_choice) - 1
                    if 0 <= provider_idx < len(providers_list):
                        provider = providers_list[provider_idx]
                        break
                    else:
                        console.print(
                            f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                        else:
                            console.print(
                                "[yellow]Too many invalid attempts. Using default: openai[/yellow]"
                            )
                            provider = "openai"
                except ValueError:
                    console.print(
                        "[red]✗ Invalid input.[/red] Please enter a number, not letters (e.g., '1' not 'openai')"
                    )
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")
                    else:
                        console.print(
                            "[yellow]Too many invalid attempts. Using default: openai[/yellow]"
                        )
                        provider = "openai"

        if not model:
            if provider is None:
                raise typer.Exit(1)

            # Validate and display curated models for all providers
            from stratifyai.utils.provider_validator import (
                get_validated_interactive_models,
            )

            # Show spinner while validating
            with console.status(
                f"[cyan]Validating {provider} models...", spinner="dots"
            ):
                validation_data = get_validated_interactive_models(provider)

            validation_result = validation_data["validation_result"]
            validated_models = validation_data["models"]

            # Show validation result
            if validation_result["error"]:
                console.print(
                    "[yellow]⚠ Default models displayed. Could not validate models.[/yellow]"
                )
            else:
                console.print(
                    f"[green]✓ Validated {len(validated_models)} models[/green] [dim]({validation_result['validation_time_ms']}ms)[/dim]"
                )

                # Show any unavailable models
                if validation_result["invalid_models"]:
                    invalid_display = []
                    for inv_model in validation_result["invalid_models"]:
                        # Get display name if available
                        invalid_display.append(inv_model.split("/")[-1].split(":")[0])
                    console.print(
                        f"[yellow]⚠ Unavailable: {', '.join(invalid_display)}[/yellow]"
                    )

            # Build display list
            console.print(f"\n[bold cyan]Available {provider} models:[/bold cyan]")

            # Get interactive models config for fallback
            from stratifyai.config import (
                INTERACTIVE_ANTHROPIC_MODELS,
                INTERACTIVE_BEDROCK_MODELS,
                INTERACTIVE_DEEPSEEK_MODELS,
                INTERACTIVE_GOOGLE_MODELS,
                INTERACTIVE_GROK_MODELS,
                INTERACTIVE_GROQ_MODELS,
                INTERACTIVE_OLLAMA_MODELS,
                INTERACTIVE_OPENAI_MODELS,
                INTERACTIVE_OPENROUTER_MODELS,
            )

            interactive_configs = {
                "openai": INTERACTIVE_OPENAI_MODELS,
                "anthropic": INTERACTIVE_ANTHROPIC_MODELS,
                "google": INTERACTIVE_GOOGLE_MODELS,
                "deepseek": INTERACTIVE_DEEPSEEK_MODELS,
                "groq": INTERACTIVE_GROQ_MODELS,
                "grok": INTERACTIVE_GROK_MODELS,
                "openrouter": INTERACTIVE_OPENROUTER_MODELS,
                "ollama": INTERACTIVE_OLLAMA_MODELS,
                "bedrock": INTERACTIVE_BEDROCK_MODELS,
            }

            fallback_config = interactive_configs.get(provider or "", {})

            # Use validated models, or fall back to interactive config
            if validated_models:
                available_models = list(validated_models.keys())
                model_metadata = validated_models
            elif fallback_config:
                available_models = list(fallback_config.keys())
                model_metadata = fallback_config
            else:
                console.print(
                    f"[red]No models configured for provider: {provider}[/red]"
                )
                raise typer.Exit(1)

            # Display with friendly names and descriptions
            current_category = None
            for i, m in enumerate(available_models, 1):
                meta = model_metadata.get(m, {})
                display_name = meta.get("display_name", m)
                description = meta.get("description", "")
                category = meta.get("category", "")

                # Show category header if changed
                if category and category != current_category:
                    console.print(f"  [dim]── {category} ──[/dim]")
                    current_category = category

                label = f"  {i}. {display_name}"
                if description:
                    label += f" [dim]- {description}[/dim]"
                console.print(label)

            # Retry loop for model selection (shared by all providers)
            max_attempts = 3
            model = None
            for attempt in range(max_attempts):
                model_choice = Prompt.ask(mode_prompt("Select model", "interactive"))

                try:
                    model_idx = int(model_choice) - 1
                    if 0 <= model_idx < len(available_models):
                        model = available_models[model_idx]
                        break
                    else:
                        console.print(
                            f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                except ValueError:
                    console.print(
                        "[red]✗ Invalid input.[/red] Please enter a number, not the model name (e.g., '2' not 'gpt-4o')"
                    )
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")

            # If still no valid model after retries, exit
            if model is None:
                console.print("[red]Too many invalid attempts. Exiting.[/red]")
                raise typer.Exit(1)

        # Check if model has fixed temperature and prompt only when model was not preselected.
        model_info = MODEL_CATALOG.get(provider or "", {}).get(model, {})
        fixed_temp = model_info.get("fixed_temperature")

        if fixed_temp is not None:
            temperature = fixed_temp
            console.print(
                f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]"
            )
        elif model_was_preselected:
            # When provider/model are supplied via CLI flags, avoid extra prompt noise.
            temperature = 0.7
        else:
            # Retry loop for temperature input
            max_attempts = 3
            temperature = None
            for attempt in range(max_attempts):
                temp_input = Prompt.ask(
                    mode_prompt("Temperature (0.0-2.0)", "interactive"), default="0.7"
                )

                try:
                    temp_value = float(temp_input)
                    if 0.0 <= temp_value <= 2.0:
                        temperature = temp_value
                        break
                    else:
                        console.print(
                            "[red]✗ Out of range.[/red] Temperature must be between 0.0 and 2.0"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")
                except ValueError:
                    console.print(
                        f"[red]✗ Invalid input.[/red] Please enter a number (e.g., '0.7' not '{temp_input}')"
                    )
                    if attempt < max_attempts - 1:
                        console.print("[dim]Try again...[/dim]")

            # If still no valid temperature after retries, use default
            if temperature is None:
                console.print(
                    "[yellow]Too many invalid attempts. Using default: 0.7[/yellow]"
                )
                temperature = 0.7

        # Initialize client
        client = LLMClient(provider=provider)
        messages: list[Message] = []

        # Get model info for context window (already retrieved above for temperature check)
        context_window = model_info.get("context", "N/A")

        # Set conversation history limit (reserve 80% for history, 20% for response)
        # Use api_max_input if available (API limit), otherwise use context window
        api_max_input = model_info.get("api_max_input")
        if api_max_input and isinstance(api_max_input, int) and api_max_input > 0:
            # Use API input limit (e.g., Anthropic's 200k limit for Claude Opus 4.5)
            max_history_tokens = int(api_max_input * 0.8)
        elif isinstance(context_window, int) and context_window > 0:
            # Fall back to context window
            max_history_tokens = int(context_window * 0.8)
        else:
            # Default to 128k context window if unknown
            max_history_tokens = int(128000 * 0.8)

        # Prompt for initial file if not provided via flag
        if not file:
            console.print("\n[bold cyan]Initial File Context (Optional)[/bold cyan]")
            console.print(
                "[dim]Load a file to provide context for the conversation[/dim]"
            )
            console.print(
                f"[dim]Max file size: {MAX_FILE_SIZE_MB} MB | Leave blank to skip[/dim]"
            )

            # File prompt with retry loop
            max_file_attempts = 3
            for _file_attempt in range(max_file_attempts):
                file_path_input = Prompt.ask(
                    mode_prompt("File path (or Enter to skip)", "interactive"),
                    default="",
                )

                if not file_path_input.strip():
                    # User pressed Enter to skip
                    break

                file = Path(file_path_input.strip()).expanduser()

                # Validate file exists and is readable
                if not file.exists():
                    console.print(f"[red]✗ File not found: {file}[/red]")
                    console.print("[dim]Continuing without file[/dim]")
                    file = None
                    break
                elif not file.is_file():
                    console.print(f"[red]✗ Path is not a file: {file}[/red]")
                    console.print("[dim]Continuing without file[/dim]")
                    file = None
                    break
                else:
                    # File is valid, break out of retry loop
                    break

        # Load initial file if provided
        if file:
            console.print("\n[bold cyan]Loading initial context...[/bold cyan]")
            file_content = load_file_content(file, warn_large=True, check_vision=True)
            if file_content:
                messages.append(
                    Message(
                        role="user",
                        content=f"[Context from {file.name}]\n\n{file_content}",
                    )
                )
                console.print("[dim]File loaded as initial context[/dim]")

        # Welcome message with mode banner
        console.print("[bold cyan]StratifyAI Interactive Mode[/bold cyan]")
        console.print(
            f"\n[{INTERACTIVE_ACCENT}]═══ ⚡ INTERACTIVE MODE ═══[/{INTERACTIVE_ACCENT}]"
        )
        console.print("[dim]Multi-turn conversation with context preservation[/dim]\n")

        # Display context info with API limit warning if applicable
        if api_max_input and api_max_input < context_window:
            console.print(
                f"Provider: [{INTERACTIVE_COLOR}]{provider}[/{INTERACTIVE_COLOR}] | Model: [{INTERACTIVE_COLOR}]{model}[/{INTERACTIVE_COLOR}] | Context: [{INTERACTIVE_COLOR}]{context_window:,} tokens[/{INTERACTIVE_COLOR}] [yellow](API limit: {api_max_input:,})[/yellow]"
            )
        else:
            console.print(
                f"Provider: [{INTERACTIVE_COLOR}]{provider}[/{INTERACTIVE_COLOR}] | Model: [{INTERACTIVE_COLOR}]{model}[/{INTERACTIVE_COLOR}] | Context: [{INTERACTIVE_COLOR}]{context_window:,} tokens[/{INTERACTIVE_COLOR}]"
            )

        console.print(
            "[dim]Commands: /file <path> | /attach <path> | /clear | /save [path] | /provider | /help | exit[/dim]"
        )
        console.print(
            f"[dim]File size limit: {MAX_FILE_SIZE_MB} MB | Ctrl+C to exit[/dim]\n"
        )

        # Conversation loop
        staged_file_content = None  # For /attach command
        staged_file_name = None
        last_response = None  # Track last assistant response for /save command

        while True:
            # Show staged file indicator with interactive mode styling
            prompt_text = f"[{INTERACTIVE_ACCENT}]⚡ You[/{INTERACTIVE_ACCENT}]"
            if staged_file_content:
                prompt_text = f"[{INTERACTIVE_ACCENT}]⚡ You[/{INTERACTIVE_ACCENT}] [dim]📎 {staged_file_name}[/dim]"

            # Get user input
            try:
                user_input = Prompt.ask(prompt_text)
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Exiting interactive mode...[/dim]")
                break

            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[dim]Goodbye![/dim]")
                break

            # Handle special commands
            if user_input.startswith("/file "):
                # Load and send file immediately with retry option
                file_path_str = user_input[6:].strip()
                file_path = Path(file_path_str).expanduser()

                file_content = load_file_content(
                    file_path, warn_large=True, check_vision=True
                )

                # If file not found, offer retry
                if not file_content and not file_path.exists():
                    choice = Prompt.ask(
                        "[cyan]Enter 1 to retry file path or 2 to enter message[/cyan]",
                        choices=["1", "2"],
                        default="2",
                    )
                    if choice == "1":
                        # Retry - prompt for new path
                        new_path_str = Prompt.ask("File path")
                        new_file_path = Path(new_path_str.strip()).expanduser()
                        file_content = load_file_content(
                            new_file_path, warn_large=True, check_vision=True
                        )
                        if file_content:
                            file_path = new_file_path
                    # If choice == "2", just continue to message prompt

                if file_content:
                    # Send file content as user message
                    user_input = f"[File: {file_path.name}]\n\n{file_content}"
                    messages.append(Message(role="user", content=user_input))
                else:
                    continue  # Skip to next input

            elif user_input.startswith("/attach "):
                # Stage file for next message with retry option
                file_path_str = user_input[8:].strip()
                file_path = Path(file_path_str).expanduser()

                file_content = load_file_content(
                    file_path, warn_large=True, check_vision=True
                )

                # If file not found, offer retry
                if not file_content and not file_path.exists():
                    choice = Prompt.ask(
                        "[cyan]Enter 1 to retry file path or 2 to enter message[/cyan]",
                        choices=["1", "2"],
                        default="2",
                    )
                    if choice == "1":
                        # Retry - prompt for new path
                        new_path_str = Prompt.ask("File path")
                        new_file_path = Path(new_path_str.strip()).expanduser()
                        file_content = load_file_content(
                            new_file_path, warn_large=True, check_vision=True
                        )
                        if file_content:
                            file_path = new_file_path
                    # If choice == "2", continue to message prompt (don't stage anything)

                if file_content:
                    staged_file_content = file_content
                    staged_file_name = file_path.name
                    console.print(
                        "[green]✓ File staged[/green] [dim]- will be attached to your next message[/dim]"
                    )
                continue

            elif user_input.lower() == "/clear":
                # Clear staged attachment
                if staged_file_content:
                    console.print(
                        f"[yellow]Cleared staged file: {staged_file_name}[/yellow]"
                    )
                    staged_file_content = None
                    staged_file_name = None
                else:
                    console.print("[dim]No staged files to clear[/dim]")
                continue

            elif user_input.startswith("/save"):
                # Save last response to file
                if last_response is None:
                    console.print("[yellow]⚠ No response to save yet[/yellow]")
                    console.print(
                        "[dim]Send a message first to get a response, then use /save[/dim]"
                    )
                    continue

                # Parse filename from command or prompt for it
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    save_path = Path(parts[1].strip()).expanduser()
                else:
                    # Prompt for filename
                    default_name = f"response_{provider}_{model.split('-')[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    filename = Prompt.ask("Save as", default=default_name)
                    save_path = Path(filename).expanduser()

                try:
                    # Ensure parent directory exists
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    # Prepare content with metadata
                    content = f"""# AI Response

**Provider:** {provider}
**Model:** {model}
**Timestamp:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Tokens:** {last_response.usage.total_tokens:,} (In: {last_response.usage.prompt_tokens:,}, Out: {last_response.usage.completion_tokens:,})
**Cost:** ${last_response.usage.cost_usd:.6f}

---

{last_response.content}
"""

                    # Write to file
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    file_size = save_path.stat().st_size
                    console.print(f"[green]✓ Response saved to:[/green] {save_path}")
                    console.print(
                        f"[dim]  Size: {file_size:,} bytes ({len(last_response.content):,} chars)[/dim]"
                    )

                except Exception as e:
                    console.print(f"[red]✗ Error saving file: {e}[/red]")

                continue

            elif user_input.lower() == "/provider":
                # Switch provider and model
                console.print("\n[bold cyan]Switch Provider and Model[/bold cyan]")
                console.print(
                    "[dim]Your conversation history will be preserved[/dim]\n"
                )

                # Show available providers
                console.print("[bold cyan]Available providers:[/bold cyan]")
                providers_list = list(MODEL_CATALOG.keys())
                for i, p in enumerate(providers_list, 1):
                    current_marker = (
                        " [green](current)[/green]" if p == provider else ""
                    )
                    console.print(f"  {i}. {p}{current_marker}")

                # Get provider selection
                max_attempts = 3
                new_provider = None
                for attempt in range(max_attempts):
                    provider_choice = Prompt.ask("\nSelect provider")
                    try:
                        provider_idx = int(provider_choice) - 1
                        if 0 <= provider_idx < len(providers_list):
                            new_provider = providers_list[provider_idx]
                            break
                        else:
                            console.print(
                                f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(providers_list)}"
                            )
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(
                            "[red]✗ Invalid input.[/red] Please enter a number"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")

                if new_provider is None:
                    console.print("[yellow]Provider not changed[/yellow]")
                    continue

                # Validate and display curated models for the selected provider
                from stratifyai.utils.provider_validator import (
                    get_validated_interactive_models,
                )

                with console.status(
                    f"[cyan]Validating {new_provider} models...", spinner="dots"
                ):
                    validation_data = get_validated_interactive_models(new_provider)

                validation_result = validation_data["validation_result"]
                validated_models = validation_data["models"]

                # Show validation result
                if validation_result["error"]:
                    console.print(
                        "[yellow]⚠ Default models displayed. Could not validate models.[/yellow]"
                    )
                    # Fall back to MODEL_CATALOG if validation fails
                    available_models = list(MODEL_CATALOG[new_provider].keys())
                    model_metadata = MODEL_CATALOG[new_provider]
                else:
                    console.print(
                        f"[green]✓ Validated {len(validated_models)} models[/green] [dim]({validation_result['validation_time_ms']}ms)[/dim]"
                    )
                    available_models = list(validated_models.keys())
                    model_metadata = validated_models

                # Show available models for new provider with full metadata
                console.print(
                    f"\n[bold cyan]Available {new_provider} models:[/bold cyan]"
                )

                # Display with friendly names, descriptions, and categories (same as initial selection)
                current_category = None
                for i, m in enumerate(available_models, 1):
                    meta = model_metadata.get(m, {})
                    display_name = meta.get("display_name", m)
                    description = meta.get("description", "")
                    category = meta.get("category", "")

                    # Show category header if changed
                    if category and category != current_category:
                        console.print(f"  [dim]── {category} ──[/dim]")
                        current_category = category

                    # Build label with current marker
                    current_marker = (
                        " [green](current)[/green]"
                        if m == model and new_provider == provider
                        else ""
                    )
                    label = f"  {i}. {display_name}{current_marker}"
                    if description:
                        label += f" [dim]- {description}[/dim]"
                    console.print(label)

                # Get model selection
                new_model = None
                for attempt in range(max_attempts):
                    model_choice = Prompt.ask("\nSelect model")
                    try:
                        model_idx = int(model_choice) - 1
                        if 0 <= model_idx < len(available_models):
                            new_model = available_models[model_idx]
                            break
                        else:
                            console.print(
                                f"[red]✗ Invalid number.[/red] Please enter a number between 1 and {len(available_models)}"
                            )
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")
                    except ValueError:
                        console.print(
                            "[red]✗ Invalid input.[/red] Please enter a number"
                        )
                        if attempt < max_attempts - 1:
                            console.print("[dim]Try again...[/dim]")

                if new_model is None:
                    console.print("[yellow]Provider and model not changed[/yellow]")
                    continue

                # Update provider and model
                provider = new_provider
                model = new_model

                # Check if new model has fixed temperature and prompt if needed
                new_model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
                fixed_temp = new_model_info.get("fixed_temperature")

                if fixed_temp is not None:
                    temperature = fixed_temp
                    console.print(
                        f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]"
                    )
                else:
                    # Retry loop for temperature input
                    max_attempts = 3
                    temperature = None
                    for attempt in range(max_attempts):
                        temp_input = Prompt.ask(
                            "\n[bold cyan]Temperature[/bold cyan] (0.0-2.0, default 0.7)",
                            default="0.7",
                        )

                        try:
                            temp_value = float(temp_input)
                            if 0.0 <= temp_value <= 2.0:
                                temperature = temp_value
                                break
                            else:
                                console.print(
                                    "[red]✗ Out of range.[/red] Temperature must be between 0.0 and 2.0"
                                )
                                if attempt < max_attempts - 1:
                                    console.print("[dim]Try again...[/dim]")
                        except ValueError:
                            console.print(
                                f"[red]✗ Invalid input.[/red] Please enter a number (e.g., '0.7' not '{temp_input}')"
                            )
                            if attempt < max_attempts - 1:
                                console.print("[dim]Try again...[/dim]")

                    # If still no valid temperature after retries, use default
                    if temperature is None:
                        console.print(
                            "[yellow]Too many invalid attempts. Using default: 0.7[/yellow]"
                        )
                        temperature = 0.7

                client = LLMClient(provider=provider)  # Reinitialize client

                # Update context window info
                model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
                context_window = model_info.get("context", "N/A")
                api_max_input = model_info.get("api_max_input")

                # Update history limit
                if (
                    api_max_input
                    and isinstance(api_max_input, int)
                    and api_max_input > 0
                ):
                    max_history_tokens = int(api_max_input * 0.8)
                elif isinstance(context_window, int) and context_window > 0:
                    max_history_tokens = int(context_window * 0.8)
                else:
                    max_history_tokens = int(128000 * 0.8)

                console.print(
                    f"\n[green]✓ Switched to:[/green] [cyan]{provider}[/cyan] | [cyan]{model}[/cyan] | [dim]Context: {context_window:,} tokens[/dim]"
                )
                console.print("[dim]Conversation history preserved[/dim]\n")
                continue

            elif user_input.lower() == "/help":
                # Display help information
                console.print("\n[bold cyan]Available Commands:[/bold cyan]")
                console.print(
                    "  [green]/file <path>[/green]   - Load and send file immediately"
                )
                console.print(
                    "  [green]/attach <path>[/green] - Stage file for next message"
                )
                console.print(
                    "  [green]/clear[/green]         - Clear staged attachments"
                )
                console.print(
                    "  [green]/save [path][/green]   - Save last response to file (markdown format)"
                )
                console.print(
                    "  [green]/provider[/green]      - Switch provider and model"
                )
                console.print(
                    "  [green]/help[/green]          - Show this help message"
                )
                console.print("  [green]exit, quit, q[/green]  - Exit interactive mode")
                console.print("\n[bold cyan]Session Info:[/bold cyan]")
                console.print(f"  Provider: [cyan]{provider}[/cyan]")
                console.print(f"  Model: [cyan]{model}[/cyan]")
                console.print(f"  Context: [cyan]{context_window:,} tokens[/cyan]")
                console.print(f"  File size limit: [cyan]{MAX_FILE_SIZE_MB} MB[/cyan]")
                if staged_file_content:
                    console.print(
                        f"  Staged file: [yellow]📎 {staged_file_name}[/yellow]"
                    )
                if last_response:
                    console.print("  Last response: [green]✓ Available to save[/green]")
                console.print()
                continue

            elif user_input.startswith("/"):
                # Unknown command
                console.print(
                    f"[yellow]Unknown command: {user_input.split()[0]}[/yellow]"
                )
                console.print(
                    "[dim]Available commands: /file, /attach, /clear, /save, /provider, /help | Type 'exit' to quit[/dim]"
                )
                continue

            # Skip empty input (unless there's a staged file)
            if not user_input.strip() and not staged_file_content:
                continue

            # Build message content (combine text with staged file if present)
            if staged_file_content:
                if user_input.strip():
                    message_content = f"{user_input}\n\n[Attached: {staged_file_name}]\n\n{staged_file_content}"
                else:
                    message_content = (
                        f"[Attached: {staged_file_name}]\n\n{staged_file_content}"
                    )

                # Clear staged file after use
                staged_file_content = None
                staged_file_name = None
            else:
                message_content = user_input

            # Add user message to history
            messages.append(Message(role="user", content=message_content))

            # Truncate conversation history if needed to prevent token limit errors
            # Rough approximation: 1 token ≈ 4 characters
            total_chars = sum(len(msg.content) for msg in messages)
            estimated_tokens = total_chars // 4

            if estimated_tokens > max_history_tokens:
                # Keep system messages and remove oldest user/assistant pairs
                system_messages = [msg for msg in messages if msg.role == "system"]
                conversation_messages = [
                    msg for msg in messages if msg.role != "system"
                ]

                # Calculate how many messages to keep
                while (
                    len(conversation_messages) > 2
                ):  # Keep at least the latest user message
                    # Remove oldest pair (user + assistant)
                    if len(conversation_messages) >= 2:
                        conversation_messages = conversation_messages[2:]

                    # Recalculate tokens
                    total_chars = sum(
                        len(msg.content)
                        for msg in system_messages + conversation_messages
                    )
                    estimated_tokens = total_chars // 4

                    if estimated_tokens <= max_history_tokens:
                        break

                # Rebuild messages list
                messages = system_messages + conversation_messages

                # Notify user of truncation
                console.print(
                    f"[yellow]⚠ Conversation history truncated (estimated {estimated_tokens:,} tokens)[/yellow]"
                )

            # Create request and get response
            request = ChatRequest(
                model=model, messages=messages, temperature=temperature
            )

            try:
                # Show spinner while waiting for response
                with console.status("[cyan]Thinking...", spinner="dots"):
                    response = client.chat_completion_sync(request)

                # Add assistant message to history
                messages.append(Message(role="assistant", content=response.content))

                # Store last response for /save command
                last_response = response

                # Display metadata and response (interactive mode - cyan)
                console.print(
                    f"\n[{INTERACTIVE_ACCENT}]⚡ Assistant[/{INTERACTIVE_ACCENT}]"
                )
                console.print(
                    f"[bold]Provider:[/bold] [{INTERACTIVE_COLOR}]{provider}[/{INTERACTIVE_COLOR}] | [bold]Model:[/bold] [{INTERACTIVE_COLOR}]{model}[/{INTERACTIVE_COLOR}]"
                )

                # Build usage line with token breakdown and cache info
                usage_parts = [
                    f"Context: {context_window:,} tokens",
                    f"In: {response.usage.prompt_tokens:,}",
                    f"Out: {response.usage.completion_tokens:,}",
                    f"Total: {response.usage.total_tokens:,}",
                    f"Cost: ${response.usage.cost_usd:.6f}",
                ]

                # Add latency if available
                if response.latency_ms is not None:
                    usage_parts.append(f"Latency: {response.latency_ms:.0f}ms")

                # Add cache statistics if available
                if response.usage.cached_tokens > 0:
                    usage_parts.append(f"Cached: {response.usage.cached_tokens:,}")
                if response.usage.cache_creation_tokens > 0:
                    usage_parts.append(
                        f"Cache Write: {response.usage.cache_creation_tokens:,}"
                    )
                if response.usage.cache_read_tokens > 0:
                    usage_parts.append(
                        f"Cache Read: {response.usage.cache_read_tokens:,}"
                    )

                console.print(f"[dim]{' | '.join(usage_parts)}[/dim]")
                console.print(f"\n{response.content}", style=INTERACTIVE_COLOR)
                console.print(
                    "[dim]💡 Tip: Use /save to save this response to a file[/dim]\n"
                )

            except AuthenticationError as e:
                console.print("\n[red]✗ Authentication Failed[/red]")
                console.print(f"[yellow]Provider:[/yellow] {e.provider}")
                console.print("[yellow]Issue:[/yellow] API key is missing or invalid\n")

                # Get environment variable name for the provider
                env_var = PROVIDER_ENV_VARS.get(
                    e.provider, f"{e.provider.upper()}_API_KEY"
                )

                console.print("[bold cyan]How to fix:[/bold cyan]")
                console.print(
                    f"  1. Set the environment variable: [green]{env_var}[/green]"
                )
                console.print(f'     export {env_var}="your-api-key-here"')
                console.print(
                    "\n  2. Or add to your [green].env[/green] file in the project root:"
                )
                console.print(f"     {env_var}=your-api-key-here\n")

                # Provider-specific instructions
                if e.provider == "openai":
                    console.print(
                        "[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]"
                    )
                elif e.provider == "anthropic":
                    console.print(
                        "[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]"
                    )
                elif e.provider == "google":
                    console.print(
                        "[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]"
                    )
                elif e.provider == "deepseek":
                    console.print(
                        "[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]"
                    )
                elif e.provider == "groq":
                    console.print(
                        "[dim]Get your API key from: https://console.groq.com/keys[/dim]"
                    )
                elif e.provider == "grok":
                    console.print(
                        "[dim]Get your API key from: https://console.x.ai/[/dim]"
                    )
                elif e.provider == "openrouter":
                    console.print(
                        "[dim]Get your API key from: https://openrouter.ai/keys[/dim]"
                    )
                elif e.provider == "ollama":
                    console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")

                # Remove failed user message from history
                messages.pop()
                console.print(
                    "[dim]You can continue the conversation after fixing the API key issue.\n[/dim]"
                )

            except Exception as e:
                console.print(f"[red]Error:[/red] {e}\n")
                # Remove failed user message from history
                messages.pop()

    except AuthenticationError as e:
        console.print("\n[red]✗ Authentication Failed[/red]")
        console.print(f"[yellow]Provider:[/yellow] {e.provider}")
        console.print("[yellow]Issue:[/yellow] API key is missing or invalid\n")

        # Get environment variable name for the provider
        env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")

        console.print("[bold cyan]How to fix:[/bold cyan]")
        console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
        console.print(f'     export {env_var}="your-api-key-here"')
        console.print(
            "\n  2. Or add to your [green].env[/green] file in the project root:"
        )
        console.print(f"     {env_var}=your-api-key-here\n")

        # Provider-specific instructions
        if e.provider == "openai":
            console.print(
                "[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]"
            )
        elif e.provider == "anthropic":
            console.print(
                "[dim]Get your API key from: https://console.anthropic.com/settings/keys[/dim]"
            )
        elif e.provider == "google":
            console.print(
                "[dim]Get your API key from: https://aistudio.google.com/app/apikey[/dim]"
            )
        elif e.provider == "deepseek":
            console.print(
                "[dim]Get your API key from: https://platform.deepseek.com/api_keys[/dim]"
            )
        elif e.provider == "groq":
            console.print(
                "[dim]Get your API key from: https://console.groq.com/keys[/dim]"
            )
        elif e.provider == "grok":
            console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
        elif e.provider == "openrouter":
            console.print(
                "[dim]Get your API key from: https://openrouter.ai/keys[/dim]"
            )
        elif e.provider == "ollama":
            console.print("[dim]Ensure Ollama is running: ollama serve[/dim]")

        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def analyze(
    file: Path = typer.Argument(
        ...,
        help="File to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="LLM provider for future LLM-enhanced extraction"
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Model name for future LLM-enhanced extraction"
    ),
):
    """Analyze file and extract structure/schema for efficient LLM processing.

    Supports CSV, JSON, log files, and Python code. Reduces token usage by 80-99%.
    If --provider and --model are not specified, the optimal model is auto-selected.
    """
    try:
        from stratifyai.utils.code_extractor import analyze_code_file
        from stratifyai.utils.csv_extractor import analyze_csv_file
        from stratifyai.utils.json_extractor import analyze_json_file
        from stratifyai.utils.log_extractor import extract_log_summary
        from stratifyai.utils.model_selector import select_model_for_file

        # Auto-select model if not specified
        if not provider or not model:
            try:
                auto_provider, auto_model, reasoning = select_model_for_file(file)
                provider = provider or auto_provider
                model = model or auto_model
                console.print(
                    f"\n[cyan]🤖 Auto-selected model:[/cyan] {provider}/{model}"
                )
                console.print(f"[dim]   Reason: {reasoning}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Auto-selection info: {e}[/yellow]")

        # Detect file type
        extension = file.suffix.lower()

        console.print(f"\n[bold cyan]Analyzing File:[/bold cyan] {file}\n")

        try:
            result: Any
            if extension == ".csv":
                result = analyze_csv_file(file)
                console.print("[bold green]CSV Schema Analysis[/bold green]\n")
                console.print(result["schema_text"])
                console.print(
                    f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%"
                )
                console.print(
                    f"[dim]Original: {result['original_size_bytes']:,} bytes → Schema: {result['schema_size_bytes']:,} bytes[/dim]"
                )

            elif extension == ".json":
                result = analyze_json_file(file)
                json_text = str(result)
                console.print("[bold green]JSON Schema Analysis[/bold green]\n")
                console.print(json_text)
                console.print(
                    f"\n[bold]Token Reduction:[/bold] {result.get('token_reduction_pct', 0):.1f}%"
                )

            elif extension in [".log", ".txt"] and "log" in file.name.lower():
                result = extract_log_summary(file)
                console.print("[bold green]Log File Analysis[/bold green]\n")
                console.print(result["summary_text"])
                console.print(
                    f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%"
                )
                console.print(
                    f"[dim]Original: {result['original_size_bytes']:,} bytes → Summary: {result['summary_size_bytes']:,} bytes[/dim]"
                )

            elif extension == ".py":
                result = analyze_code_file(file)
                console.print(
                    "[bold green]Python Code Structure Analysis[/bold green]\n"
                )
                console.print(result["structure_text"])
                console.print(
                    f"\n[bold]Token Reduction:[/bold] {result['token_reduction_pct']:.1f}%"
                )
                console.print(
                    f"[dim]Original: {result['original_size_bytes']:,} bytes → Structure: {result['structure_size_bytes']:,} bytes[/dim]"
                )

            else:
                console.print(
                    f"[yellow]File type not supported for intelligent extraction: {extension}[/yellow]"
                )
                console.print("[dim]Supported types: .csv, .json, .log, .py[/dim]")
                raise typer.Exit(1)

            console.print("\n[green]✓ Analysis complete[/green]")
            console.print(
                "[dim]Recommendation: Use extracted schema/structure for LLM analysis[/dim]\n"
            )

        except Exception as e:
            console.print(f"[red]Error analyzing file:[/red] {e}")
            raise typer.Exit(1) from e

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="cache-stats")
def cache_stats(
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed cache entry information"
    ),
):
    """Display cache statistics with cost savings analytics."""

    try:
        stats = get_cache_stats()

        console.print("\n[bold cyan]📊 Response Cache Statistics[/bold cyan]\n")

        # Create main stats table
        table = Table(title="Cache Metrics", show_header=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="yellow")

        table.add_row(
            "Cache Size", f"{stats['size']:,} / {stats['max_size']:,} entries"
        )
        table.add_row("Total Hits", f"{stats['total_hits']:,}")
        table.add_row("Total Misses", f"{stats['total_misses']:,}")
        table.add_row("Total Requests", f"{stats['total_requests']:,}")

        # Hit rate with visual indicator
        hit_rate = stats.get("hit_rate", 0.0)
        if hit_rate >= 75:
            hit_rate_str = f"[green]{hit_rate:.1f}%[/green] 🎯"
        elif hit_rate >= 50:
            hit_rate_str = f"[yellow]{hit_rate:.1f}%[/yellow] ⚠️"
        else:
            hit_rate_str = f"[red]{hit_rate:.1f}%[/red] 📉"
        table.add_row("Hit Rate", hit_rate_str)

        table.add_row("TTL (Time-to-Live)", f"{stats['ttl']:,} seconds")

        console.print(table)

        # Cost savings section
        cost_saved = stats.get("total_cost_saved", 0.0)
        if cost_saved > 0 or stats["total_hits"] > 0:
            console.print("\n[bold green]💰 Cost Savings Analysis[/bold green]")
            console.print(
                f"\n[green]✓[/green] Total Cost Saved: [bold green]${cost_saved:.4f}[/bold green]"
            )
            console.print(
                f"[dim]   ({stats['total_hits']:,} cached responses avoided API calls)[/dim]"
            )

            if stats["total_hits"] > 0:
                avg_savings_per_hit = cost_saved / stats["total_hits"]
                console.print(
                    f"[dim]   Average savings per hit: ${avg_savings_per_hit:.6f}[/dim]"
                )

        # Detailed entry view
        if detailed and stats["size"] > 0:
            console.print(
                "\n[bold cyan]📝 Cache Entries (Top 10 by hits)[/bold cyan]\n"
            )

            entries = get_cache_entries()[:10]  # Top 10

            entry_table = Table(show_header=True)
            entry_table.add_column("Provider", style="cyan")
            entry_table.add_column("Model", style="magenta")
            entry_table.add_column("Hits", justify="right", style="yellow")
            entry_table.add_column("Cost Saved", justify="right", style="green")
            entry_table.add_column("Age", justify="right", style="blue")
            entry_table.add_column("Expires In", justify="right", style="red")

            for entry in entries:
                age_str = f"{entry['age_seconds']}s"
                expires_str = f"{entry['expires_in']}s"
                cost_str = (
                    f"${entry['cost_saved']:.4f}" if entry["cost_saved"] > 0 else "-"
                )

                entry_table.add_row(
                    entry["provider"],
                    entry["model"],
                    str(entry["hits"]),
                    cost_str,
                    age_str,
                    expires_str,
                )

            console.print(entry_table)

        # Usage tip
        if not detailed and stats["size"] > 0:
            console.print(
                "\n[dim]💡 Tip: Use --detailed flag to see cache entry information[/dim]"
            )

        console.print()

    except Exception as e:
        console.print(f"[red]Error getting cache stats:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="cache-clear")
def cache_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Clear all cache entries."""

    try:
        stats = get_cache_stats()

        if stats["size"] == 0:
            console.print("\n[yellow]Cache is already empty.[/yellow]\n")
            return

        # Show what will be cleared
        console.print("\n[yellow]⚠️  About to clear:[/yellow]")
        console.print(f"   - {stats['size']:,} cache entries")
        console.print(f"   - {stats['total_hits']:,} total hits")
        if stats.get("total_cost_saved", 0) > 0:
            console.print(f"   - ${stats['total_cost_saved']:.4f} saved cost data")

        # Confirm unless --force
        if not force:
            confirm = Confirm.ask(
                "\nAre you sure you want to clear the cache?", default=False
            )
            if not confirm:
                console.print("\n[dim]Cache clear cancelled.[/dim]\n")
                return

        # Clear cache
        clear_cache()
        console.print("\n[green]✓ Cache cleared successfully[/green]\n")

    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def setup():
    """
    Interactive API key setup wizard.

    Shows which providers have API keys configured and provides
    links to get API keys for providers you want to use.
    """
    from stratifyai.api_key_helper import APIKeyHelper, print_setup_instructions

    console.print("\n[bold cyan]🔑 StratifyAI Setup Wizard[/bold cyan]\n")

    # Create .env from .env.example if needed
    if APIKeyHelper.create_env_file_if_missing():
        console.print("[green]✓[/green] Created .env file from .env.example")
        console.print("[dim]  Edit .env to add your API keys[/dim]\n")
    elif not Path(".env").exists():
        console.print("[yellow]⚠[/yellow]  .env file not found")
        console.print("[dim]  Create one by copying .env.example[/dim]\n")

    # Show current status
    print_setup_instructions()

    # Instructions
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  1. Edit .env file and add API keys for providers you want to use")
    console.print("  2. Run [green]stratifyai check-keys[/green] to verify your setup")
    console.print(
        "  3. Test with: [cyan]stratifyai chat -p openai -m gpt-4o-mini 'Hello'[/cyan]\n"
    )


@app.command(name="check-keys")
def check_keys():
    """
    Check which providers have API keys configured.

    Displays a status report showing which providers are ready to use
    and which ones need API keys.
    """
    from stratifyai.api_key_helper import APIKeyHelper

    available = APIKeyHelper.check_available_providers()

    console.print("\n[bold cyan]🔑 API Key Status[/bold cyan]\n")

    # Count configured providers
    configured_count = sum(1 for v in available.values() if v)
    total_count = len(available)

    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Environment Variable", style="dim")

    for provider in sorted(available.keys()):
        is_available = available[provider]
        status = (
            "[green]✓ Configured[/green]" if is_available else "[red]✗ Missing[/red]"
        )
        friendly_name = APIKeyHelper.PROVIDER_FRIENDLY_NAMES.get(provider, provider)
        env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(provider, "N/A")

        table.add_row(friendly_name, status, env_key)

    console.print(table)

    # Summary
    if configured_count == 0:
        console.print("\n[yellow]⚠ No providers configured[/yellow]")
        console.print("[dim]Run [cyan]stratifyai setup[/cyan] to get started[/dim]\n")
    elif configured_count == total_count:
        console.print(f"\n[green]✓ All {total_count} providers configured![/green]\n")
    else:
        console.print(
            f"\n[cyan]{configured_count}/{total_count} providers configured[/cyan]\n"
        )

    # Help tip
    if configured_count < total_count:
        console.print(
            "[dim]💡 Tip: Run [cyan]stratifyai setup[/cyan] to see how to configure missing providers[/dim]\n"
        )


@app.command()
def doctor(
    live: bool = typer.Option(
        False,
        "--live",
        help="Run live provider connectivity checks (makes real API calls).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON output for automation and CI.",
    ),
):
    """Run one-shot diagnostics for environment, keys, providers, and connectivity."""
    from stratifyai.api_key_helper import APIKeyHelper

    if not json_output:
        console.print("\n[bold cyan]🩺 StratifyAI Doctor[/bold cyan]\n")

    checks = Table(show_header=True, header_style="bold magenta")
    checks.add_column("Check", style="cyan")
    checks.add_column("Status", justify="center")
    checks.add_column("Details", style="white")
    check_results: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, details: str, fatal: bool = True) -> None:
        check_results.append(
            {"name": name, "ok": ok, "details": details, "fatal": fatal}
        )
        if ok:
            status = "[green]PASS[/green]"
        elif fatal:
            status = "[red]FAIL[/red]"
        else:
            status = "[yellow]WARN[/yellow]"
        checks.add_row(name, status, details)

    env_exists = Path(".env").exists()
    add_check(
        "Environment file",
        env_exists,
        ".env found" if env_exists else ".env not found",
        fatal=False,
    )

    add_check(
        "Python runtime",
        sys.version_info >= (3, 10),
        f"Python {sys.version.split()[0]}",
    )

    provider_count = len(MODEL_CATALOG)
    model_count = sum(len(models) for models in MODEL_CATALOG.values())
    add_check(
        "Catalog load",
        provider_count > 0 and model_count > 0,
        f"{provider_count} providers, {model_count} models",
    )

    available = APIKeyHelper.check_available_providers()
    configured = [provider for provider, has_key in available.items() if has_key]
    add_check(
        "API keys",
        len(configured) > 0,
        (
            f"{len(configured)}/{len(available)} providers configured"
            if configured
            else "No provider API keys configured"
        ),
        fatal=False,
    )

    init_failures: list[str] = []
    for provider in configured:
        try:
            LLMClient(provider=provider)
        except Exception as exc:
            init_failures.append(f"{provider}: {exc}")

    add_check(
        "Client initialization",
        len(init_failures) == 0,
        "All configured providers initialized"
        if not init_failures
        else "; ".join(init_failures[:3]),
    )

    if live:
        live_failures: list[str] = []
        tested = 0
        for provider in configured:
            models = MODEL_CATALOG.get(provider, {})
            if not models:
                continue
            model = next(iter(models.keys()))
            try:
                client = LLMClient(provider=provider)
                request = ChatRequest(
                    model=model,
                    messages=[Message(role="user", content="Reply with: ok")],
                    temperature=0.0,
                    max_tokens=8,
                )
                client.chat_completion_sync(request)
                tested += 1
            except Exception as exc:
                tested += 1
                live_failures.append(f"{provider}: {exc}")

        add_check(
            "Live connectivity",
            tested > 0 and len(live_failures) == 0,
            (
                f"{tested} provider(s) responded"
                if not live_failures
                else "; ".join(live_failures[:3])
            ),
        )
    else:
        add_check(
            "Live connectivity",
            True,
            "Skipped (use --live to run real provider calls)",
        )

    failed_checks = [
        check for check in check_results if not check["ok"] and check["fatal"]
    ]
    payload = {
        "ok": len(failed_checks) == 0,
        "live_enabled": live,
        "configured_providers": configured,
        "checks": check_results,
        "init_failures": init_failures,
    }

    if json_output:
        typer.echo(json.dumps(payload))
    else:
        console.print(checks)

    if failed_checks:
        raise typer.Exit(1)


@app.command()
def templates(
    tag: str | None = typer.Option(
        None, "--tag", help="Filter templates by tag (e.g., code, writing, data)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed parameter information"
    ),
):
    """List available prompt templates.

    Templates provide reusable prompts for common tasks like code review,
    summarization, translation, and more.
    """
    try:
        from stratifyai.prompts import registry

        template_list = registry.list(tag=tag)

        if not template_list:
            if tag:
                console.print(
                    f"\n[yellow]No templates found with tag '{tag}'[/yellow]\n"
                )
            else:
                console.print("\n[yellow]No templates available[/yellow]\n")
            return

        # Create table
        title = "📋 Prompt Templates" + (f" [dim](tag: {tag})[/dim]" if tag else "")
        table = Table(title=title, show_lines=True, header_style="bold cyan")
        table.add_column("Name", style="cyan bold", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Tags", style="yellow")
        table.add_column("Source", style="green", justify="center")

        if verbose:
            table.add_column("Parameters", style="magenta")

        for t in template_list:
            # Truncate description if too long
            desc = t.description
            if len(desc) > 80:
                desc = desc[:77] + "..."

            row = [
                t.name,
                desc,
                ", ".join(t.tags) if t.tags else "-",
                "built-in" if t.source == "builtin" else "user",
            ]

            if verbose:
                # Build parameter list with required/optional markers
                param_strs = []
                for p in t.parameters:
                    marker = "*" if p.required else ""
                    default_str = f"={p.default}" if p.default is not None else ""
                    param_strs.append(f"{p.name}{marker}{default_str}")
                row.append(", ".join(param_strs) if param_strs else "-")

            table.add_row(*row)

        console.print()
        console.print(table)
        console.print(
            f"\n[dim]{len(template_list)} template{'s' if len(template_list) != 1 else ''} found[/dim]"
        )

        # Usage examples
        if not verbose:
            console.print("\n[dim]💡 Use --verbose to see template parameters[/dim]")

        console.print("\n[bold cyan]Usage Examples:[/bold cyan]")
        console.print("  List all templates:")
        console.print("    [green]stratifyai templates[/green]")
        console.print("\n  Filter by tag:")
        console.print("    [green]stratifyai templates --tag code[/green]")
        console.print("\n  Use a template:")
        console.print(
            "    [green]stratifyai chat --template code_review --params 'language=python,focus=security' --file script.py[/green]"
        )
        console.print()

    except Exception as e:
        console.print(f"[red]Error listing templates:[/red] {e}")
        raise typer.Exit(1) from e


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
