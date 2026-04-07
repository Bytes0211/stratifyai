from pathlib import Path

import tomllib


def test_mcp_is_runtime_dependency_for_api_server() -> None:
    """The API imports MCP modules at startup, so mcp must be a core dependency."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dep.startswith("mcp[cli]>=1.25,<2") for dep in dependencies), (
        "mcp[cli] must be listed in project.dependencies because api.main imports "
        "MCPClientEngine during startup"
    )


def test_fastapi_dependency_is_pinned_below_next_major() -> None:
    """FastAPI should stay below 1.x until that major line is explicitly validated."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert "fastapi>=0.115.0,<1.0" in dependencies, (
        "fastapi should be upper-bounded below 1.0 in project.dependencies to "
        "avoid pulling unvalidated major releases during package installs"
    )


def test_manifest_excludes_local_mcp_editor_configs() -> None:
    """Release artifacts should not ship workspace-local MCP/editor config files."""
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")

    for rule in ("prune .cursor", "prune .vscode", "global-exclude *.backup"):
        assert rule in manifest, f"Missing release-safety rule in MANIFEST.in: {rule}"
