"""Schemas for curated MCP server catalog entries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MCPEnvVar(BaseModel):
    """Environment variable requirement for a catalog entry."""

    name: str
    description: str = ""
    required: bool = True
    signup_url: str | None = None
    secret: bool = True


class MCPUserArg(BaseModel):
    """User-supplied argument needed to configure a server."""

    name: str
    description: str = ""
    required: bool = True
    flag: str | None = None
    example: str | None = None
    multiple: bool = False


class MCPServerEntry(BaseModel):
    """A single curated MCP server definition."""

    id: str
    name: str
    description: str
    category: str
    website: str | None = None
    install_method: Literal["npx", "pip", "docker", "remote", "uvx", "binary"] = "npx"
    command: str
    args: list[str] = Field(default_factory=list)
    env_vars: list[MCPEnvVar] = Field(default_factory=list)
    user_args: list[MCPUserArg] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MCPServerCatalog(BaseModel):
    """Top-level curated MCP server catalog."""

    version: str
    updated: str
    servers: list[MCPServerEntry] = Field(default_factory=list)
