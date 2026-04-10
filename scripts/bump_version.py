#!/usr/bin/env python3
"""Bump the StratifyAI version across all project files.

Usage:
    python scripts/bump_version.py 2.1.0        # set explicit version
    python scripts/bump_version.py               # show current version

Source of truth: pyproject.toml [project].version
Updates:
    - pyproject.toml
    - frontend/package.json
    - stratifyai/__init__.py  (fallback string)
    - api/main.py             (fallback string)
    - README.md               (title line)
    - developer/PYPI-PUBLISHING.md
    - docs/CHANGELOG.md       (adds [Unreleased] section if needed)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# -- file definitions: (path, pattern, replacement_template) --
# replacement_template uses {v} as the version placeholder.

REPLACEMENTS: list[tuple[Path, str, str]] = [
    # pyproject.toml
    (
        ROOT / "pyproject.toml",
        r'^(version\s*=\s*")[^"]+(")',
        r"\g<1>{v}\2",
    ),
    # frontend/package.json — handled separately (JSON)
    # stratifyai/__init__.py fallback
    (
        ROOT / "stratifyai" / "__init__.py",
        r'(__version__\s*=\s*")[^"]+(")',
        r"\g<1>{v}\2",
    ),
    # api/main.py fallback
    (
        ROOT / "api" / "main.py",
        r'(return\s+")[^"]+(")',
        r"\g<1>{v}\2",
    ),
    # README.md title
    (
        ROOT / "README.md",
        r"(# StratifyAI — Unified Multi‑Provider LLM Interface) v[\d.]+",
        r"\1 v{v}",
    ),
    # developer/PYPI-PUBLISHING.md  — version in intro line
    (
        ROOT / "developer" / "PYPI-PUBLISHING.md",
        r"(\*\*v)[\d.]+(\.?\*\*)",
        r"\g<1>{v}\2",
    ),
    # developer/PYPI-PUBLISHING.md  — expected output block
    (
        ROOT / "developer" / "PYPI-PUBLISHING.md",
        r"(?m)^(\d+\.\d+\.\d+)\n(\1)\n(\1)$",
        r"{v}\n{v}\n{v}",
    ),
]


def get_current_version() -> str:
    """Read the current version from pyproject.toml."""
    text = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        print("Error: could not read version from pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def update_regex_files(new_version: str) -> None:
    """Apply regex replacements across all configured files."""
    for filepath, pattern, template in REPLACEMENTS:
        if not filepath.exists():
            print(f"  SKIP (not found): {filepath.relative_to(ROOT)}")
            continue
        text = filepath.read_text()
        replacement = template.replace("{v}", new_version)
        new_text, count = re.subn(
            pattern, replacement, text, count=1, flags=re.MULTILINE
        )
        if count:
            filepath.write_text(new_text)
            print(f"  OK: {filepath.relative_to(ROOT)}")
        else:
            print(
                f"  NO MATCH: {filepath.relative_to(ROOT)} — pattern not found, check manually"
            )


def update_package_json(new_version: str) -> None:
    """Update frontend/package.json version field."""
    pkg_path = ROOT / "frontend" / "package.json"
    if not pkg_path.exists():
        print(f"  SKIP (not found): {pkg_path.relative_to(ROOT)}")
        return
    data = json.loads(pkg_path.read_text())
    data["version"] = new_version
    pkg_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  OK: {pkg_path.relative_to(ROOT)}")


def update_changelog(new_version: str) -> None:
    """Ensure docs/CHANGELOG.md has an [Unreleased] section."""
    changelog = ROOT / "docs" / "CHANGELOG.md"
    if not changelog.exists():
        print(f"  SKIP (not found): {changelog.relative_to(ROOT)}")
        return
    # Nothing to auto-update in changelog — version entries are manual.
    print(f"  INFO: {changelog.relative_to(ROOT)} — update manually with release notes")


def main() -> None:
    current = get_current_version()

    if len(sys.argv) < 2:
        print(f"Current version: {current}")
        print(f"\nUsage: python {sys.argv[0]} <new-version>")
        sys.exit(0)

    new_version = sys.argv[1].lstrip("v")

    # Basic semver validation
    if not re.match(r"^\d+\.\d+\.\d+", new_version):
        print(
            f"Error: '{new_version}' doesn't look like a valid version (expected X.Y.Z)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Bumping version: {current} → {new_version}\n")

    update_regex_files(new_version)
    update_package_json(new_version)
    update_changelog(new_version)

    print(f"\nDone! Version bumped to {new_version}")
    print("Remember to update docs/CHANGELOG.md with release notes.")


if __name__ == "__main__":
    main()
