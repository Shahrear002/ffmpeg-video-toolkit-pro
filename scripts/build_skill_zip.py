#!/usr/bin/env python3
"""
Build & Packaging Script for Agensi Skill Package.
1. Copies engine/video_toolkit.py to skill/scripts/video_toolkit.py.
2. Compiles skill/references/platform-limits.md from engine/data/platform_limits.json.
3. Runs security audit check (scripts/audit_self.py).
4. Produces a deterministic ZIP package with SHA256 verification hash.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

SKILL_VERSION = "1.0.0"


def generate_platform_limits_markdown(json_path: Path, md_path: Path) -> None:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    platforms = data.get("platforms", {})
    last_updated = data.get("last_updated", "2026-11-19")

    lines = [
        "# Platform Video Limits Reference",
        "",
        f"> Automatically generated from `engine/data/platform_limits.json` on {last_updated}.",
        "",
        "| Platform Preset | Target Size | Max Bytes | Last Verified | Status | Official Documentation |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for key, p in platforms.items():
        size_str = f"{p.get('size_mb')} MB" if p.get('size_mb') < 1024 else f"{p.get('size_mb')//1024} GB"
        bytes_val = f"{p.get('target_bytes'):,}"
        verified = p.get('last_verified', 'N/A')
        status = p.get('status', 'UNVERIFIED')
        source_url = p.get('source_url', '#')
        lines.append(f"| `{key}` | {size_str} | {bytes_val} | {verified} | {status} | [Documentation]({source_url}) |")

    lines.extend([
        "",
        "## Usage in Engine & Agent",
        "",
        "To target any platform preset directly with the toolkit, use `--preset`:",
        "",
        "```bash",
        "python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset discord",
        "python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset whatsapp",
        "python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset github",
        "```",
    ])

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[BUILD] Generated {md_path}", file=sys.stderr)


def build_skill_package(repo_root: Path) -> Path:
    skill_dir = repo_root / "skill"
    engine_file = repo_root / "engine" / "video_toolkit.py"
    target_script = skill_dir / "scripts" / "video_toolkit.py"
    platform_json = repo_root / "engine" / "data" / "platform_limits.json"
    platform_md = skill_dir / "references" / "platform-limits.md"

    # Step 1: Copy script from engine (never hand-edited)
    target_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(engine_file, target_script)
    print(f"[BUILD] Copied {engine_file.name} -> {target_script}", file=sys.stderr)

    # Step 2: Generate platform-limits.md
    generate_platform_limits_markdown(platform_json, platform_md)

    # Step 3: Run security audit
    audit_script = repo_root / "scripts" / "audit_self.py"
    audit_res = subprocess.run([sys.executable, str(audit_script)], check=False)
    if audit_res.returncode != 0:
        raise RuntimeError("Security audit failed! Aborting skill package build.")

    # Step 4: Build deterministic ZIP
    dist_dir = repo_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dist_dir / f"ffmpeg-video-toolkit-pro-skill-v{SKILL_VERSION}.zip"

    files_to_zip = []
    for root, _, files in os.walk(skill_dir):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(skill_dir)
            files_to_zip.append((full_path, rel_path))

    # Sort files for deterministic archive ordering
    files_to_zip.sort(key=lambda x: str(x[1]))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for full_p, rel_p in files_to_zip:
            zinfo = zipfile.ZipInfo(filename=str(rel_p).replace("\\", "/"))
            # Deterministic timestamp: 2026-01-01 00:00:00
            zinfo.date_time = (2026, 1, 1, 0, 0, 0)
            zinfo.external_attr = 0o755 << 16 if rel_p.suffix == ".py" else 0o644 << 16
            with open(full_p, "rb") as f:
                zf.writestr(zinfo, f.read())

    # Step 5: Compute SHA256 checksum
    hasher = hashlib.sha256()
    with open(zip_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    checksum = hasher.hexdigest()

    checksum_file = dist_dir / f"ffmpeg-video-toolkit-pro-skill-v{SKILL_VERSION}.zip.sha256"
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{checksum}  {zip_path.name}\n")

    print(f"[BUILD COMPLETE] Package: {zip_path}", file=sys.stderr)
    print(f"[BUILD COMPLETE] SHA256:  {checksum}", file=sys.stderr)
    return zip_path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    try:
        build_skill_package(repo_root)
        return 0
    except Exception as e:
        print(f"[BUILD ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
