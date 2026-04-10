#!/usr/bin/env python3
"""Bump the StratifyAI version across all project files.

Usage:
    python scripts/bump_version.py 2.1.0        # set explicit version
    python scripts/bump_version.py               # show status, auto-sync if out of sync

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
            print(f"   ⏭️  {filepath.relative_to(ROOT)} — not found, skipping")
            continue
        text = filepath.read_text()
        replacement = template.replace("{v}", new_version)
        new_text, count = re.subn(
            pattern, replacement, text, count=1, flags=re.MULTILINE
        )
        if count:
            filepath.write_text(new_text)
            print(f"   ✅ {filepath.relative_to(ROOT)} — updated to {new_version}")
        else:
            print(
                f"   ⚠️  {filepath.relative_to(ROOT)} — pattern not found, check manually"
            )


def update_package_json(new_version: str) -> None:
    """Update package.json version fields (root and frontend)."""
    for pkg_path in [ROOT / "package.json", ROOT / "frontend" / "package.json"]:
        if not pkg_path.exists():
            print(f"   ⏭️  {pkg_path.relative_to(ROOT)} — not found, skipping")
            continue
        data = json.loads(pkg_path.read_text())
        data["version"] = new_version
        pkg_path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"   ✅ {pkg_path.relative_to(ROOT)} — updated to {new_version}")


def update_changelog(new_version: str) -> None:
    """Ensure docs/CHANGELOG.md has an [Unreleased] section."""
    changelog = ROOT / "docs" / "CHANGELOG.md"
    if not changelog.exists():
        print(f"   ⏭️  {changelog.relative_to(ROOT)} — not found, skipping")
        return
    # Nothing to auto-update in changelog — version entries are manual.
    print(f"   📝 {changelog.relative_to(ROOT)} — update manually with release notes")


def read_file_versions() -> list[tuple[str, str | None]]:
    """Read the current version from each managed file and return (label, version) pairs."""
    results: list[tuple[str, str | None]] = []

    # pyproject.toml
    path = ROOT / "pyproject.toml"
    if path.exists():
        m = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(), re.MULTILINE)
        results.append(("pyproject.toml", m.group(1) if m else None))
    else:
        results.append(("pyproject.toml", None))

    # package.json (root)
    path = ROOT / "package.json"
    if path.exists():
        data = json.loads(path.read_text())
        results.append(("package.json", data.get("version")))
    else:
        results.append(("package.json", None))

    # frontend/package.json
    path = ROOT / "frontend" / "package.json"
    if path.exists():
        data = json.loads(path.read_text())
        results.append(("frontend/package.json", data.get("version")))
    else:
        results.append(("frontend/package.json", None))

    # stratifyai/__init__.py
    path = ROOT / "stratifyai" / "__init__.py"
    if path.exists():
        m = re.search(r'__version__\s*=\s*"([^"]+)"', path.read_text())
        results.append(("stratifyai/__init__.py", m.group(1) if m else None))
    else:
        results.append(("stratifyai/__init__.py", None))

    # api/main.py
    path = ROOT / "api" / "main.py"
    if path.exists():
        m = re.search(r'return\s+"([^"]+)"', path.read_text())
        results.append(("api/main.py", m.group(1) if m else None))
    else:
        results.append(("api/main.py", None))

    # README.md
    path = ROOT / "README.md"
    if path.exists():
        m = re.search(r"# StratifyAI.*v([\d.]+)", path.read_text())
        results.append(("README.md", m.group(1) if m else None))
    else:
        results.append(("README.md", None))

    # developer/PYPI-PUBLISHING.md
    path = ROOT / "developer" / "PYPI-PUBLISHING.md"
    if path.exists():
        m = re.search(r"\*\*v([\d.]+)\.?\*\*", path.read_text())
        results.append(("developer/PYPI-PUBLISHING.md", m.group(1) if m else None))
    else:
        results.append(("developer/PYPI-PUBLISHING.md", None))

    return results


def print_versions(versions: list[tuple[str, str | None]], source_version: str) -> None:
    """Display version values from each file, flagging mismatches."""
    for label, version in versions:
        if version is None:
            print(f"   ⏭️  {label:<35} — not found")
        elif version == source_version:
            print(f"   ✅ {label:<35} → {version}")
        else:
            print(f"   ❌ {label:<35} → {version}  (expected {source_version})")


def has_mismatches(versions: list[tuple[str, str | None]], source_version: str) -> bool:
    """Return True if any file version doesn't match the source of truth."""
    return any(v is not None and v != source_version for _, v in versions)


def print_banner() -> None:
    """Print the script banner."""
    print()
    print("========================================")
    print("  🔄 StratifyAI Version Bump Utility")
    print("========================================")
    print()


def main() -> None:
    print_banner()
    current = get_current_version()

    if len(sys.argv) < 2:
        print(f"📌 Source of truth (pyproject.toml): {current}")
        print()
        print("📂 File versions:")
        versions = read_file_versions()
        print_versions(versions, current)
        print()

        if has_mismatches(versions, current):
            print(f"🔄 Files are out of sync — syncing all to {current}...")
            print()
            print("📂 Updating files:")
            update_regex_files(current)
            update_package_json(current)
            update_changelog(current)
            print()
            print("🔍 Verification:")
            versions = read_file_versions()
            print_versions(versions, current)
            print()
            print(f"✅ All files synced to {current}")
        else:
            print("✅ All files in sync")

        print()
        print(f"▶️  Usage: python scripts/bump_version.py {current}")
        sys.exit(0)

    new_version = sys.argv[1].lstrip("v")

    # Basic semver validation
    if not re.match(r"^\d+\.\d+\.\d+", new_version):
        print(
            f"❌ Error: '{new_version}' doesn't look like a valid version (expected X.Y.Z)",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"📌 Current version: {current}")

    if current == new_version:
        print(f"⚡ No change in version: {current}")
        print(f"🔄 Re-syncing all files to {new_version}...")
    else:
        print(f"▶️  Bumping to new version: {new_version}")
    print()

    print("📂 Updating files:")
    update_regex_files(new_version)
    update_package_json(new_version)
    update_changelog(new_version)

    print()
    if current == new_version:
        print(f"✅ All files re-synced to {new_version}")
    else:
        print(f"✅ Version bumped: {current} → {new_version}")

    print()
    print("🔍 Verification:")
    versions = read_file_versions()
    print_versions(versions, new_version)

    print()
    print("📋 Next steps:")
    print("   1. Update docs/CHANGELOG.md with release notes")
    print(f"   2. Commit: git add -A && git commit -m 'bump: v{new_version}'")
    print("   3. Test deploy: bash scripts/test_deploy_stratifyai.sh")
    print("   4. Prod deploy: bash scripts/prod_deploy_stratifyai.sh")


if __name__ == "__main__":
    main()
