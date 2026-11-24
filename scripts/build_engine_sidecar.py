#!/usr/bin/env python3
"""
Compiles engine/video_toolkit.py into a standalone sidecar binary for Tauri v2 using PyInstaller.
Outputs: desktop/src-tauri/binaries/video_toolkit-<target-triple>[.exe]
"""

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def get_host_target_triple() -> str:
    machine = platform.machine().lower()
    system = platform.system().lower()

    if system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "darwin":
        return "aarch64-apple-darwin" if "arm" in machine or "aarch64" in machine else "x86_64-apple-darwin"
    elif system == "linux":
        return "x86_64-unknown-linux-gnu"
    return "x86_64-pc-windows-msvc"


def build_sidecar(target_triple: str, out_dir: Path, repo_root: Path) -> Path:
    engine_script = repo_root / "engine" / "video_toolkit.py"
    if not engine_script.is_file():
        raise FileNotFoundError(f"Engine script missing: {engine_script}")

    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".exe" if "windows" in target_triple else ""
    binary_name = f"video_toolkit-{target_triple}"
    expected_output = out_dir / f"{binary_name}{ext}"

    print(f"[SIDECAR BUILD] Compiling {engine_script.name} -> {expected_output} with PyInstaller...", file=sys.stderr)

    build_temp = repo_root / "build" / f"pyinstaller_{target_triple}"
    build_temp.mkdir(parents=True, exist_ok=True)

    pyinstaller_bin = shutil.which("pyinstaller") or "pyinstaller"

    cmd = [
        pyinstaller_bin,
        "--onefile",
        "--noconfirm",
        "--clean",
        "--name", binary_name,
        "--distpath", str(out_dir),
        "--workpath", str(build_temp),
        "--specpath", str(build_temp),
    ]
    if target_triple == "universal-apple-darwin" and sys.platform == "darwin":
        cmd.extend(["--target-arch", "universal2"])
    cmd.append(str(engine_script))

    res = subprocess.run(cmd, check=False)
    if res.returncode != 0 and target_triple == "universal-apple-darwin":
        print("[SIDECAR] Retrying PyInstaller without --target-arch universal2...", file=sys.stderr)
        fallback_cmd = [
            pyinstaller_bin,
            "--onefile",
            "--noconfirm",
            "--clean",
            "--name", binary_name,
            "--distpath", str(out_dir),
            "--workpath", str(build_temp),
            "--specpath", str(build_temp),
            str(engine_script),
        ]
        res = subprocess.run(fallback_cmd, check=False)

    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {res.returncode}")

    if not expected_output.is_file():
        raise FileNotFoundError(f"Expected compiled binary not found at {expected_output}")

    if not ext:
        expected_output.chmod(0o755)

    if target_triple == "universal-apple-darwin":
        for arch in ["aarch64-apple-darwin", "x86_64-apple-darwin"]:
            arch_bin = out_dir / f"video_toolkit-{arch}{ext}"
            shutil.copy2(expected_output, arch_bin)
            if not ext:
                arch_bin.chmod(0o755)
            print(f"[SIDECAR] Also staged slice: {arch_bin}", file=sys.stderr)

    print(f"[SIDECAR BUILD COMPLETE] Created {expected_output} ({expected_output.stat().st_size:,} bytes)", file=sys.stderr)

    # Smoke test the compiled sidecar
    print(f"[SIDECAR TEST] Verifying sidecar executable...", file=sys.stderr)
    test_res = subprocess.run([str(expected_output), "--check"], capture_output=True, text=True, check=False)
    if test_res.returncode != 0:
        raise RuntimeError(f"Sidecar smoke test failed (code {test_res.returncode}): {test_res.stderr}")

    print(f"[SIDECAR TEST OK] Sidecar diagnostic succeeded.", file=sys.stderr)
    return expected_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PyInstaller sidecar binary for Tauri v2")
    parser.add_argument("--target", default="host", help="Target triple (default 'host')")
    parser.add_argument("--out-dir", default=None, help="Output directory")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "desktop" / "src-tauri" / "binaries")
    target = get_host_target_triple() if args.target == "host" else args.target

    try:
        build_sidecar(target, out_dir, repo_root)
        return 0
    except Exception as e:
        print(f"[SIDECAR BUILD ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
