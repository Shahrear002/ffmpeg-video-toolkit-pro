#!/usr/bin/env python3
"""
Synchronizes application version across Tauri, Nuxt, Cargo, and Skill configurations.
Usage:
    python scripts/sync_version.py 0.0.5
    python scripts/sync_version.py v1.2.0
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def sync_version(raw_version: str) -> str:
    # Normalize: strip leading 'v'
    version = raw_version.strip()
    if version.startswith("v") or version.startswith("V"):
        version = version[1:]

    # Basic semver validation: X.Y.Z[-prerelease]
    semver_pattern = r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
    if not re.match(semver_pattern, version):
        print(f"[ERROR] Version '{version}' does not match semver pattern (X.Y.Z)", file=sys.stderr)
        sys.exit(1)

    print(f"[SYNC VERSION] Synchronizing version across project to: {version}")

    # 1. desktop/src-tauri/tauri.conf.json
    tauri_conf_path = REPO_ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
    if tauri_conf_path.is_file():
        with open(tauri_conf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        old_ver = data.get("version", "")
        data["version"] = version
        with open(tauri_conf_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"  ✓ Updated {tauri_conf_path.relative_to(REPO_ROOT)} ({old_ver} -> {version})")

    # 2. desktop/package.json
    pkg_json_path = REPO_ROOT / "desktop" / "package.json"
    if pkg_json_path.is_file():
        with open(pkg_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        old_ver = data.get("version", "")
        data["version"] = version
        with open(pkg_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"  ✓ Updated {pkg_json_path.relative_to(REPO_ROOT)} ({old_ver} -> {version})")

    # 3. desktop/src-tauri/Cargo.toml
    cargo_toml_path = REPO_ROOT / "desktop" / "src-tauri" / "Cargo.toml"
    if cargo_toml_path.is_file():
        content = cargo_toml_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r'(?m)^version\s*=\s*"[^"]*"',
            f'version = "{version}"',
            content,
            count=1,
        )
        cargo_toml_path.write_text(new_content, encoding="utf-8")
        print(f"  ✓ Updated {cargo_toml_path.relative_to(REPO_ROOT)}")

    # 4. scripts/build_skill_zip.py
    skill_script_path = REPO_ROOT / "scripts" / "build_skill_zip.py"
    if skill_script_path.is_file():
        content = skill_script_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r'(?m)^SKILL_VERSION\s*=\s*"[^"]*"',
            f'SKILL_VERSION = "{version}"',
            content,
            count=1,
        )
        skill_script_path.write_text(new_content, encoding="utf-8")
        print(f"  ✓ Updated {skill_script_path.relative_to(REPO_ROOT)}")

    # 5. skill/SKILL.md
    skill_md_path = REPO_ROOT / "skill" / "SKILL.md"
    if skill_md_path.is_file():
        content = skill_md_path.read_text(encoding="utf-8")
        new_content = re.sub(
            r'(?m)^\s*version:\s*"[^"]*"',
            f'  version: "{version}"',
            content,
            count=1,
        )
        skill_md_path.write_text(new_content, encoding="utf-8")
        print(f"  ✓ Updated {skill_md_path.relative_to(REPO_ROOT)}")

    print(f"[SYNC VERSION SUCCESS] All targets synchronized to {version}")
    return version


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/sync_version.py <version>", file=sys.stderr)
        sys.exit(1)
    sync_version(sys.argv[1])
