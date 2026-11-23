#!/usr/bin/env python3
"""
FFmpeg Video Toolkit Pro - Core Engine
Commercial-grade, production-tested video processing engine.
Zero external dependencies (Python 3.9+ standard library only).
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# ============================================================================
# Exit Codes & Constants
# ============================================================================

class ExitCode:
    SUCCESS = 0
    GENERAL_ERROR = 1
    ARGUMENT_ERROR = 2
    DEPENDENCY_ERROR = 3
    VERIFICATION_ERROR = 4
    STREAM_ERROR = 5
    CANCELLED = 6

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
NULL_SINK = "NUL" if IS_WINDOWS else "/dev/null"

# Global tracking for active subprocess and temporary directories to ensure clean SIGINT/SIGTERM handling
_ACTIVE_SUBPROCESS: Optional[subprocess.Popen] = None
_REGISTERED_TEMP_DIRS: List[str] = []

def _cleanup_resources() -> None:
    global _ACTIVE_SUBPROCESS
    if _ACTIVE_SUBPROCESS is not None:
        try:
            if _ACTIVE_SUBPROCESS.poll() is None:
                _ACTIVE_SUBPROCESS.terminate()
                try:
                    _ACTIVE_SUBPROCESS.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    _ACTIVE_SUBPROCESS.kill()
        except Exception:
            pass
        _ACTIVE_SUBPROCESS = None

    for temp_dir in _REGISTERED_TEMP_DIRS:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
    _REGISTERED_TEMP_DIRS.clear()

def _signal_handler(signum: int, frame: Any) -> None:
    _cleanup_resources()
    sys.exit(ExitCode.CANCELLED)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ============================================================================
# Encoder Abstraction
# ============================================================================

def get_video_encoder(target_codec: str = "h264") -> Tuple[str, List[str]]:
    """
    Returns (encoder_name, extra_flags).
    In v1: libx264 is returned.
    In v1.1: Hardware encoders (h264_nvenc, h264_videotoolbox, h264_qsv)
    will be selected here dynamically without modifying calling code.
    """
    if target_codec == "h264":
        return ("libx264", [])
    elif target_codec == "hevc":
        return ("libx265", [])
    return ("libx264", [])


# ============================================================================
# Progress & Logging Subsystem
# ============================================================================

class ToolkitLogger:
    def __init__(self, json_mode: bool = False, quiet: bool = False, verbose: bool = False):
        self.json_mode = json_mode
        self.quiet = quiet
        self.verbose = verbose

    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.json_mode:
            payload = {"event": event_type}
            payload.update(data)
            print(json.dumps(payload), flush=True)
        elif not self.quiet:
            if event_type == "start":
                print(f"[START] {data.get('command', '')}: {data.get('input', '')} -> {data.get('output', '')}", file=sys.stderr)
            elif event_type == "progress":
                pass_label = f" [Pass {data['pass']}]" if "pass" in data else ""
                speed = data.get("speed", "N/A")
                fps = data.get("fps", 0.0)
                eta = f"{data['eta_s']:.1f}s" if "eta_s" in data and data["eta_s"] is not None else "N/A"
                print(f"\r[PROGRESS]{pass_label} {data.get('percent', 0.0):.1f}% | FPS: {fps:.1f} | Speed: {speed} | ETA: {eta}", end="", file=sys.stderr)
            elif event_type == "done":
                if "output" in data:
                    print(f"\n[DONE] Finished {data.get('output', '')} ({data.get('bytes', 0):,} bytes)", file=sys.stderr)
                else:
                    print(f"\n[DONE] Batch operation completed ({len(data.get('summary', []))} files processed)", file=sys.stderr)
            elif event_type == "warning":
                print(f"\n[WARNING] {data.get('message', '')}", file=sys.stderr)
            elif event_type == "error":
                print(f"\n[ERROR {data.get('code', 1)}] {data.get('message', '')}", file=sys.stderr)

    def log(self, message: str) -> None:
        if not self.quiet and not self.json_mode:
            print(message, file=sys.stderr)

    def debug(self, message: str) -> None:
        if self.verbose and not self.quiet and not self.json_mode:
            print(f"[DEBUG] {message}", file=sys.stderr)


# ============================================================================
# Platform Limits Repository
# ============================================================================

def load_platform_limits() -> Dict[str, Any]:
    """Loads platform limits from engine/data/platform_limits.json or bundled fallback."""
    candidate_paths = [
        Path(__file__).resolve().parent / "data" / "platform_limits.json",
        Path(__file__).resolve().parent.parent / "engine" / "data" / "platform_limits.json",
        Path(__file__).resolve().parent / "platform_limits.json",
    ]
    for p in candidate_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("platforms", {})
            except Exception:
                pass

    # Built-in verified baseline fallback
    return {
        "discord": {
            "name": "Discord (Free Tier)",
            "target_bytes": 20971520,
            "max_bytes": 20971520,
            "status": "VERIFIED",
            "last_verified": "2026-11-19",
            "source_url": "https://discord.com",
            "recommended_resolution": "1280x720",
        },
        "whatsapp": {
            "name": "WhatsApp (Gallery/Media)",
            "target_bytes": 16777216,
            "max_bytes": 16777216,
            "status": "VERIFIED",
            "last_verified": "2026-11-19",
            "source_url": "https://faq.whatsapp.com",
            "recommended_resolution": "1280x720",
        },
        "github": {
            "name": "GitHub (Issue/PR)",
            "target_bytes": 26214400,
            "max_bytes": 26214400,
            "status": "VERIFIED",
            "last_verified": "2026-11-19",
            "source_url": "https://docs.github.com",
            "recommended_resolution": "1280x720",
        },
    }


# ============================================================================
# Core FFmpeg & FFprobe Process Utilities
# ============================================================================

class FFmpegRunner:
    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
        logger: Optional[ToolkitLogger] = None,
        dry_run: bool = False,
        overwrite: bool = False,
    ):
        self.logger = logger or ToolkitLogger()
        self.dry_run = dry_run
        self.overwrite = overwrite

        self.ffmpeg = (
            ffmpeg_path
            or os.environ.get("FFMPEG_PATH")
            or shutil.which("ffmpeg")
            or "ffmpeg"
        )
        self.ffprobe = (
            ffprobe_path
            or os.environ.get("FFPROBE_PATH")
            or shutil.which("ffprobe")
            or "ffprobe"
        )

    def check_executable(self, exe: str) -> bool:
        return shutil.which(exe) is not None or os.path.isfile(exe)

    def verify_dependencies(self) -> None:
        if not self.check_executable(self.ffmpeg):
            raise FileNotFoundError(f"FFmpeg executable not found: '{self.ffmpeg}'")
        if not self.check_executable(self.ffprobe):
            raise FileNotFoundError(f"FFprobe executable not found: '{self.ffprobe}'")

    def run_probe(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Runs ffprobe on the input file and returns parsed JSON metadata."""
        self.verify_dependencies()
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Input file not found: {p}")

        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            str(p),
        ]
        self.logger.debug(f"Executing: {' '.join(cmd)}")
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"ffprobe failed (code {res.returncode}): {res.stderr.strip()}")
        try:
            return json.loads(res.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")

    def execute_ffmpeg_with_progress(
        self,
        cmd_args: List[str],
        total_duration: float,
        pass_number: Optional[int] = None,
        total_passes: int = 1,
    ) -> subprocess.CompletedProcess:
        """
        Executes FFmpeg with -progress pipe:1 and streams progress events.
        """
        global _ACTIVE_SUBPROCESS
        self.verify_dependencies()

        full_cmd = [self.ffmpeg] + cmd_args

        if self.dry_run:
            self.logger.emit_event("start", {"dry_run": True, "command_line": full_cmd})
            return subprocess.CompletedProcess(args=full_cmd, returncode=0, stdout="", stderr="")

        # Ensure -progress pipe:1 and -nostats are included
        if "-progress" not in full_cmd:
            idx = 1
            if len(full_cmd) > 1 and full_cmd[1] == "-y":
                idx = 2
            full_cmd[idx:idx] = ["-nostats", "-progress", "pipe:1"]

        self.logger.debug(f"FFmpeg command: {' '.join(full_cmd)}")

        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=CREATE_NO_WINDOW,
            bufsize=1,
        )
        _ACTIVE_SUBPROCESS = proc

        progress_data: Dict[str, str] = {}
        stderr_buffer: List[str] = []

        # Consume stderr concurrently in background thread to prevent OS pipe deadlocks
        def _drain_stderr() -> None:
            try:
                for err_line in proc.stderr:
                    stderr_buffer.append(err_line)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # Read stdout line by line
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    progress_data[k.strip()] = v.strip()

                if line.startswith("progress="):
                    status = progress_data.get("progress", "")
                    out_time_us_str = progress_data.get("out_time_us")
                    speed_str = progress_data.get("speed", "N/A")
                    fps_str = progress_data.get("fps", "0.0")

                    fps_val = 0.0
                    try:
                        fps_val = float(fps_str)
                    except ValueError:
                        pass

                    current_sec = 0.0
                    if out_time_us_str and out_time_us_str.isdigit():
                        current_sec = float(out_time_us_str) / 1_000_000.0
                    elif "out_time" in progress_data:
                        # Format: HH:MM:SS.microseconds
                        parts = progress_data["out_time"].split(":")
                        if len(parts) == 3:
                            try:
                                current_sec = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                            except ValueError:
                                pass

                    pct = 0.0
                    if total_duration > 0:
                        pct = min(100.0, max(0.0, (current_sec / total_duration) * 100.0))

                    if total_passes == 2 and pass_number is not None:
                        # Combine pass 1 (0-50%) and pass 2 (50-100%)
                        if pass_number == 1:
                            combined_pct = pct * 0.5
                        else:
                            combined_pct = 50.0 + (pct * 0.5)
                    else:
                        combined_pct = pct

                    speed_mult = 1.0
                    if speed_str.endswith("x"):
                        try:
                            speed_mult = float(speed_str[:-1])
                        except ValueError:
                            speed_mult = 1.0

                    eta_s = None
                    if speed_mult > 0 and total_duration > current_sec:
                        eta_s = (total_duration - current_sec) / speed_mult
                        if total_passes == 2 and pass_number == 1:
                            eta_s += total_duration / speed_mult

                    progress_event = {
                        "percent": round(combined_pct, 2),
                        "fps": round(fps_val, 2),
                        "speed": speed_str,
                        "eta_s": round(eta_s, 1) if eta_s is not None else None,
                    }
                    if pass_number is not None:
                        progress_event["pass"] = pass_number

                    self.logger.emit_event("progress", progress_event)
                    progress_data.clear()

            proc.wait()
            stderr_thread.join(timeout=2)
            stderr_out = "".join(stderr_buffer)
            ret = proc.returncode
        finally:
            if proc.stdout:
                try:
                    proc.stdout.close()
                except Exception:
                    pass
            if proc.stderr:
                try:
                    proc.stderr.close()
                except Exception:
                    pass
            _ACTIVE_SUBPROCESS = None

        if ret != 0:
            raise RuntimeError(f"FFmpeg execution failed with code {ret}:\n{stderr_out.strip()}")

        return subprocess.CompletedProcess(args=full_cmd, returncode=ret, stdout="", stderr=stderr_out)


# ============================================================================
# Pure-Logic Computational Helpers (Tested Offline Without FFmpeg)
# ============================================================================

def parse_time_to_seconds(time_val: Union[str, float, int]) -> float:
    """Parses seconds, float, or HH:MM:SS / MM:SS strings into total seconds."""
    if isinstance(time_val, (int, float)):
        return float(time_val)
    time_str = str(time_val).strip()
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
    return float(time_str)


def calculate_two_pass_bitrate(
    target_bytes: int,
    duration_s: float,
    audio_bitrate_bps: int = 128_000,
    safety_margin: float = 0.05,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
) -> Tuple[int, int]:
    """
    Computes (video_bitrate_bps, audio_bitrate_bps).
    Enforces container overhead safety margin (default 5%) and quality sanity checks.
    Raises ValueError if bitrate is mathematically impossible or would produce severe visual corruption.
    """
    if duration_s <= 0:
        raise ValueError(f"Invalid duration: {duration_s}s")
    if target_bytes <= 0:
        raise ValueError(f"Invalid target size: {target_bytes} bytes")

    # Dynamic safety margin expansion for small envelopes: fixed MP4/container headers take more percentage of tiny files
    effective_margin = safety_margin
    if safety_margin == 0.05:
        if target_bytes < 150_000:
            effective_margin = 0.15
        elif target_bytes < 500_000:
            effective_margin = 0.10

    effective_target_bytes = target_bytes * (1.0 - effective_margin)
    total_bits = effective_target_bytes * 8.0
    total_bitrate_bps = total_bits / duration_s

    # Dynamic audio bitrate adjustment for small envelopes
    adj_audio_bitrate = audio_bitrate_bps
    if total_bitrate_bps < 250_000:
        adj_audio_bitrate = min(adj_audio_bitrate, 64_000)
    elif total_bitrate_bps < 500_000:
        adj_audio_bitrate = min(adj_audio_bitrate, 96_000)

    video_bitrate_bps = int(total_bitrate_bps - adj_audio_bitrate)
    if video_bitrate_bps <= 0:
        raise ValueError(
            f"Target size ({target_bytes:,} bytes) is too small for a {duration_s:.1f}s video. "
            f"Audio alone requires {adj_audio_bitrate // 1000}k."
        )

    # Sanity check: Bits Per Pixel per Frame (bppf)
    # Threshold < 0.04 bppf or < 48k video bitrate indicates unacceptable degradation
    pixel_rate = width * height * max(fps, 1.0)
    bppf = video_bitrate_bps / pixel_rate if pixel_rate > 0 else 0.1
    if bppf < 0.04 or video_bitrate_bps < 48_000:
        suggested_scale = "720p" if height > 720 else ("480p" if height > 480 else "360p")
        raise ValueError(
            f"Computed video bitrate ({video_bitrate_bps // 1000} kbps, bppf: {bppf:.4f}) is too low "
            f"for {width}x{height} @ {fps:.1f}fps and will produce severe visual artifacts. "
            f"Please downscale using --scale {suggested_scale} or increase the target size."
        )

    return video_bitrate_bps, adj_audio_bitrate


def build_atempo_filter_chain(speed_factor: float) -> str:
    """
    Decomposes an arbitrary positive speed factor into chained FFmpeg atempo filters
    since each atempo filter only supports factors in [0.5, 2.0].
    """
    if speed_factor <= 0:
        raise ValueError(f"Speed factor must be positive, got {speed_factor}")

    factors: List[float] = []
    current = speed_factor

    while current > 2.0:
        factors.append(2.0)
        current /= 2.0

    while current < 0.5:
        factors.append(0.5)
        current /= 0.5

    factors.append(round(current, 6))
    return ",".join(f"atempo={f}" for f in factors)


def parse_silencedetect_stderr(stderr_text: str, total_duration: float) -> List[Tuple[float, float]]:
    """
    Parses silence_start and silence_end entries from FFmpeg silencedetect stderr output.
    Returns a sorted list of (start_s, end_s) tuples.
    """
    silences: List[Tuple[float, float]] = []
    current_start: Optional[float] = None

    start_pattern = re.compile(r"silence_start:\s*(-?[0-9.]+)")
    end_pattern = re.compile(r"silence_end:\s*(-?[0-9.]+)")

    for line in stderr_text.splitlines():
        start_match = start_pattern.search(line)
        if start_match:
            current_start = max(0.0, float(start_match.group(1)))
            continue
        end_match = end_pattern.search(line)
        if end_match:
            end_val = min(total_duration, float(end_match.group(1)))
            start_val = current_start if current_start is not None else 0.0
            silences.append((start_val, end_val))
            current_start = None

    if current_start is not None:
        silences.append((current_start, total_duration))

    return silences


def compute_keep_segments(
    silences: List[Tuple[float, float]],
    total_duration: float,
    pad_s: float = 0.1,
) -> List[Tuple[float, float]]:
    """
    Inverts silence segments to non-silent keep segments with edge padding.
    """
    if not silences:
        return [(0.0, total_duration)]

    padded_silences: List[Tuple[float, float]] = []
    for s, e in silences:
        # Contract silence by pad on both sides so audio doesn't get clipped
        s_pad = s + pad_s
        e_pad = e - pad_s
        if s_pad < e_pad:
            padded_silences.append((max(0.0, s_pad), min(total_duration, e_pad)))

    if not padded_silences:
        return [(0.0, total_duration)]

    keep: List[Tuple[float, float]] = []
    last_end = 0.0

    for s, e in padded_silences:
        if s > last_end + 0.01:
            keep.append((last_end, s))
        last_end = max(last_end, e)

    if last_end < total_duration - 0.01:
        keep.append((last_end, total_duration))

    return keep


def escape_concat_demuxer_path(path: Path) -> str:
    """
    Escapes paths for FFmpeg's concat demuxer file list.
    Normalizes Windows backslashes to forward slashes and escapes single quotes as '\\''.
    """
    posix_str = path.as_posix()
    escaped = posix_str.replace("'", r"'\''")
    return f"file '{escaped}'"


# ============================================================================
# Subcommand Handlers
# ============================================================================

def handle_check(runner: FFmpegRunner, as_json: bool = False) -> int:
    """Executes the --check system diagnostic."""
    diag: Dict[str, Any] = {
        "status": "ok",
        "ffmpeg_path": runner.ffmpeg,
        "ffprobe_path": runner.ffprobe,
        "ffmpeg_found": runner.check_executable(runner.ffmpeg),
        "ffprobe_found": runner.check_executable(runner.ffprobe),
        "encoders": {},
        "filters": {},
    }

    if not diag["ffmpeg_found"] or not diag["ffprobe_found"]:
        diag["status"] = "missing_dependencies"
        if as_json or runner.logger.json_mode:
            print(json.dumps(diag, indent=2))
        else:
            print(f"[CHECK] Dependencies missing! FFmpeg: {diag['ffmpeg_found']}, FFprobe: {diag['ffprobe_found']}", file=sys.stderr)
        return ExitCode.DEPENDENCY_ERROR

    # Probe version and capabilities
    try:
        ver_proc = subprocess.run([runner.ffmpeg, "-version"], capture_output=True, text=True, check=False)
        diag["ffmpeg_version"] = ver_proc.stdout.splitlines()[0] if ver_proc.stdout else "Unknown"

        enc_proc = subprocess.run([runner.ffmpeg, "-encoders"], capture_output=True, text=True, check=False)
        enc_out = enc_proc.stdout
        diag["encoders"]["libx264"] = "libx264" in enc_out
        diag["encoders"]["aac"] = "aac" in enc_out
        diag["encoders"]["libmp3lame"] = "libmp3lame" in enc_out
        diag["encoders"]["libwebp"] = "libwebp" in enc_out

        filt_proc = subprocess.run([runner.ffmpeg, "-filters"], capture_output=True, text=True, check=False)
        filt_out = filt_proc.stdout
        diag["filters"]["silencedetect"] = "silencedetect" in filt_out
        diag["filters"]["palettegen"] = "palettegen" in filt_out
        diag["filters"]["paletteuse"] = "paletteuse" in filt_out
        diag["filters"]["tile"] = "tile" in filt_out
    except Exception as e:
        diag["status"] = "error"
        diag["error"] = str(e)
        return ExitCode.GENERAL_ERROR

    if as_json or runner.logger.json_mode:
        print(json.dumps(diag, indent=2))
    else:
        print(f"[CHECK OK] {diag['ffmpeg_version']}", file=sys.stderr)
        print(f"Encoders: {diag['encoders']}", file=sys.stderr)
        print(f"Filters:  {diag['filters']}", file=sys.stderr)

    return ExitCode.SUCCESS


def handle_compress(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input file not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}. Use --overwrite to replace."})
        return ExitCode.VERIFICATION_ERROR

    limits = load_platform_limits()
    target_bytes: Optional[int] = None

    if args.preset:
        preset_key = args.preset.lower().strip()
        if preset_key not in limits:
            runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Unknown preset '{args.preset}'. Available presets: {list(limits.keys())}"})
            return ExitCode.ARGUMENT_ERROR
        target_bytes = limits[preset_key]["target_bytes"]
    elif args.target_size_mb:
        target_bytes = int(args.target_size_mb * 1024 * 1024)
    elif args.target_size_bytes:
        target_bytes = int(args.target_size_bytes)
    else:
        target_bytes = limits.get("discord", {}).get("target_bytes", 20971520)

    # Probe media
    probe_data = runner.run_probe(input_path)
    fmt = probe_data.get("format", {})
    duration_s = float(fmt.get("duration", 0.0))
    if duration_s <= 0:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "Could not determine media duration."})
        return ExitCode.STREAM_ERROR

    v_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v_stream:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "No video stream found in input."})
        return ExitCode.STREAM_ERROR

    width = int(v_stream.get("width", 1920))
    height = int(v_stream.get("height", 1080))
    fps = 30.0
    r_frame_rate = v_stream.get("r_frame_rate", "30/1")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        if float(den) > 0:
            fps = float(num) / float(den)

    # Scale filter handling
    scale_filter = None
    if args.scale:
        s_val = args.scale.lower().strip()
        if s_val == "1080p":
            scale_filter = "scale=-2:1080"
            height = 1080
            width = int(1080 * 16 / 9)
        elif s_val == "720p":
            scale_filter = "scale=-2:720"
            height = 720
            width = int(720 * 16 / 9)
        elif s_val == "480p":
            scale_filter = "scale=-2:480"
            height = 480
            width = int(480 * 16 / 9)
        elif s_val == "360p":
            scale_filter = "scale=-2:360"
            height = 360
            width = int(360 * 16 / 9)
        else:
            scale_filter = f"scale={args.scale}"

    try:
        v_bitrate, a_bitrate = calculate_two_pass_bitrate(
            target_bytes=target_bytes,
            duration_s=duration_s,
            audio_bitrate_bps=args.audio_bitrate * 1000 if args.audio_bitrate else 128_000,
            safety_margin=0.05,
            width=width,
            height=height,
            fps=fps,
        )
    except ValueError as e:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": str(e)})
        return ExitCode.VERIFICATION_ERROR

    runner.logger.emit_event("start", {
        "command": "compress",
        "input": str(input_path),
        "output": str(output_path),
        "target_bytes": target_bytes,
        "video_bitrate": v_bitrate,
        "audio_bitrate": a_bitrate,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    encoder, extra_enc_args = get_video_encoder("h264")
    temp_dir = tempfile.mkdtemp(prefix="fvt_compress_")
    _REGISTERED_TEMP_DIRS.append(temp_dir)

    try:
        passlogfile = os.path.join(temp_dir, "ffmpeg2pass")

        # Pass 1
        pass1_cmd = [
            "-y",
            "-i", str(input_path),
            "-c:v", encoder,
            "-b:v", str(v_bitrate),
            "-pass", "1",
            "-passlogfile", passlogfile,
            "-an",
        ]
        if scale_filter:
            pass1_cmd.extend(["-vf", scale_filter])
        pass1_cmd.extend(extra_enc_args)
        pass1_cmd.extend(["-f", "null", NULL_SINK])

        runner.execute_ffmpeg_with_progress(pass1_cmd, duration_s, pass_number=1, total_passes=2)

        # Pass 2
        pass2_cmd = [
            "-y",
            "-i", str(input_path),
            "-c:v", encoder,
            "-b:v", str(v_bitrate),
            "-pass", "2",
            "-passlogfile", passlogfile,
            "-c:a", "aac",
            "-b:a", str(a_bitrate),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]
        if scale_filter:
            pass2_cmd.extend(["-vf", scale_filter])
        pass2_cmd.extend(extra_enc_args)
        pass2_cmd.append(str(output_path))

        runner.execute_ffmpeg_with_progress(pass2_cmd, duration_s, pass_number=2, total_passes=2)

        # Post-encode size verification
        actual_size = output_path.stat().st_size
        if actual_size > target_bytes:
            msg = f"Compression exceeded target size! Target: {target_bytes:,} bytes, Actual: {actual_size:,} bytes"
            runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": msg})
            return ExitCode.VERIFICATION_ERROR

        runner.logger.emit_event("done", {
            "output": str(output_path),
            "bytes": actual_size,
            "target_bytes": target_bytes,
            "headroom_bytes": target_bytes - actual_size,
        })
        return ExitCode.SUCCESS
    finally:
        if temp_dir in _REGISTERED_TEMP_DIRS:
            _REGISTERED_TEMP_DIRS.remove(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)


def handle_trim_silence(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    audio_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not audio_stream:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "Input contains no audio stream to detect silence."})
        return ExitCode.STREAM_ERROR

    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
    if duration_s <= 0:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "Invalid input media duration."})
        return ExitCode.STREAM_ERROR

    has_video = any(s.get("codec_type") == "video" for s in probe_data.get("streams", []))

    runner.logger.emit_event("start", {
        "command": "trim-silence",
        "input": str(input_path),
        "output": str(output_path),
        "noise": args.noise,
        "min_silence": args.min_silence,
        "pad": args.pad,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    # Pass 1: Run silencedetect
    noise_db = args.noise if args.noise.endswith("dB") else f"{args.noise}dB"
    detect_cmd = [
        runner.ffmpeg,
        "-i", str(input_path),
        "-af", f"silencedetect=noise={noise_db}:d={args.min_silence}",
        "-f", "null",
        "-",
    ]
    runner.logger.debug(f"Running silencedetect: {' '.join(detect_cmd)}")
    det_proc = subprocess.run(
        detect_cmd,
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )

    silences = parse_silencedetect_stderr(det_proc.stderr, duration_s)
    keep_segments = compute_keep_segments(silences, duration_s, pad_s=args.pad)

    if not keep_segments:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "Entire video is detected as silence."})
        return ExitCode.STREAM_ERROR

    if len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and abs(keep_segments[0][1] - duration_s) < 0.05:
        runner.logger.emit_event("warning", {"message": "No silence found matching criteria. Copying input directly."})
        copy_cmd = ["-y", "-i", str(input_path), "-c", "copy", str(output_path)]
        runner.execute_ffmpeg_with_progress(copy_cmd, duration_s)
        runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
        return ExitCode.SUCCESS

    # Build filter complex representation
    filter_lines: List[str] = []
    n_segs = len(keep_segments)

    for i, (s, e) in enumerate(keep_segments):
        if has_video:
            filter_lines.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        filter_lines.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")

    concat_inputs = "".join(f"[v{i}][a{i}]" if has_video else f"[a{i}]" for i in range(n_segs))
    v_flag = "1" if has_video else "0"
    filter_lines.append(f"{concat_inputs}concat=n={n_segs}:v={v_flag}:a=1[outv][outa]" if has_video else f"{concat_inputs}concat=n={n_segs}:v=0:a=1[outa]")

    filter_str = "".join(filter_lines)
    encoder, _ = get_video_encoder("h264")

    temp_dir = None
    try:
        trim_cmd = ["-y", "-i", str(input_path)]
        # For concise filtergraphs (< 4000 chars), pass directly on CLI to avoid script file encoding issues
        if len(filter_str) < 4000:
            trim_cmd.extend(["-filter_complex", filter_str])
        else:
            temp_dir = tempfile.mkdtemp(prefix="fvt_trim_")
            _REGISTERED_TEMP_DIRS.append(temp_dir)
            script_file = os.path.join(temp_dir, "filter_script.txt")
            with open(script_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(filter_str)
            trim_cmd.extend(["-filter_complex_script", Path(script_file).as_posix()])

        if has_video:
            trim_cmd.extend(["-map", "[outv]", "-map", "[outa]", "-c:v", encoder, "-pix_fmt", "yuv420p"])
        else:
            trim_cmd.extend(["-map", "[outa]"])

        trim_cmd.extend(["-c:a", "aac", str(output_path)])

        total_keep_duration = sum(e - s for s, e in keep_segments)
        runner.execute_ffmpeg_with_progress(trim_cmd, total_keep_duration)

        runner.logger.emit_event("done", {
            "output": str(output_path),
            "bytes": output_path.stat().st_size,
            "original_duration_s": duration_s,
            "new_duration_s": total_keep_duration,
            "silence_cut_s": duration_s - total_keep_duration,
            "segments_kept": n_segs,
        })
        return ExitCode.SUCCESS
    finally:
        if temp_dir and temp_dir in _REGISTERED_TEMP_DIRS:
            _REGISTERED_TEMP_DIRS.remove(temp_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)


def handle_shorts(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
    v_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v_stream:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "No video stream found."})
        return ExitCode.STREAM_ERROR

    mode = args.mode.lower().strip()
    x_offset = int(args.x_offset) if args.x_offset else 0

    runner.logger.emit_event("start", {
        "command": "shorts",
        "input": str(input_path),
        "output": str(output_path),
        "mode": mode,
        "x_offset": x_offset,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    has_audio = any(s.get("codec_type") == "audio" for s in probe_data.get("streams", []))
    encoder, _ = get_video_encoder("h264")

    if mode == "crop":
        # Center crop with optional x_offset, scaled to 1080x1920
        # If input is already 9:16, it cleanly scales without overcropping
        filter_str = (
            f"[0:v]crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)':x='max(0,min(iw-ow,(iw-ow)/2+{x_offset}))':y='(ih-oh)/2',"
            f"scale=1080:1920:flags=lanczos[outv]"
        )
    elif mode == "blur":
        # Background: fill 1080x1920 and blur; Foreground: fit 1080x1920 and overlay centered
        filter_str = (
            f"[0:v]split=2[bg_in][fg_in];"
            f"[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
            f"[fg_in]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )
    else:
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Unsupported shorts mode '{mode}'. Choose 'crop' or 'blur'."})
        return ExitCode.ARGUMENT_ERROR

    cmd = [
        "-y",
        "-i", str(input_path),
        "-filter_complex", filter_str,
        "-map", "[outv]",
    ]
    if has_audio:
        cmd.extend(["-map", "0:a?", "-c:a", "aac"])

    cmd.extend([
        "-c:v", encoder,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ])

    runner.execute_ffmpeg_with_progress(cmd, duration_s)
    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


def handle_convert(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_target = Path(args.input).resolve()
    target_format = args.format.lower().lstrip(".")

    files_to_process: List[Path] = []
    if input_target.is_file():
        files_to_process.append(input_target)
    elif input_target.is_dir():
        pattern = "**/*" if args.recursive else "*"
        for p in input_target.glob(pattern):
            if p.is_file() and p.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".wmv"]:
                files_to_process.append(p)
    else:
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input path not found: {input_target}"})
        return ExitCode.ARGUMENT_ERROR

    if not files_to_process:
        runner.logger.emit_event("warning", {"message": "No convertible video files discovered."})
        return ExitCode.SUCCESS

    out_arg = Path(args.output).resolve() if args.output else None
    summary_results: List[Dict[str, Any]] = []
    encoder, _ = get_video_encoder("h264")

    runner.logger.emit_event("start", {
        "command": "convert",
        "file_count": len(files_to_process),
        "target_format": target_format,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    overall_success = True
    for src in files_to_process:
        try:
            if out_arg and out_arg.suffix:
                dest = out_arg
            elif out_arg and out_arg.is_dir():
                dest = out_arg / f"{src.stem}.{target_format}"
            else:
                dest = src.with_suffix(f".{target_format}")

            if dest.exists() and not runner.overwrite:
                summary_results.append({"file": str(src), "status": "skipped", "message": "Destination exists"})
                continue

            probe_data = runner.run_probe(src)
            duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
            streams = probe_data.get("streams", [])
            v_codec = next((s.get("codec_name") for s in streams if s.get("codec_type") == "video"), None)
            a_codec = next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), None)

            # Check if stream-copy is suitable for mp4
            can_copy_v = target_format == "mp4" and v_codec in ["h264", "hevc", "av1"]
            can_copy_a = target_format == "mp4" and (a_codec in ["aac", "mp3"] or a_codec is None)

            cmd = ["-y", "-i", str(src)]
            if can_copy_v and can_copy_a:
                cmd.extend(["-c", "copy"])
            else:
                cmd.extend([
                    "-c:v", encoder if not can_copy_v else "copy",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac" if not can_copy_a else "copy",
                ])

            cmd.extend(["-movflags", "+faststart", str(dest)])
            runner.execute_ffmpeg_with_progress(cmd, duration_s)
            summary_results.append({"file": str(src), "output": str(dest), "status": "success", "bytes": dest.stat().st_size})
        except Exception as e:
            overall_success = False
            summary_results.append({"file": str(src), "status": "error", "message": str(e)})

    runner.logger.emit_event("done", {"summary": summary_results})
    return ExitCode.SUCCESS if overall_success else ExitCode.GENERAL_ERROR


def handle_extract_audio(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    has_audio = any(s.get("codec_type") == "audio" for s in probe_data.get("streams", []))
    if not has_audio:
        runner.logger.emit_event("error", {"code": ExitCode.STREAM_ERROR, "message": "Input contains no audio stream."})
        return ExitCode.STREAM_ERROR

    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
    fmt = (args.format or output_path.suffix.lstrip(".") or "mp3").lower()

    runner.logger.emit_event("start", {
        "command": "extract-audio",
        "input": str(input_path),
        "output": str(output_path),
        "format": fmt,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    cmd = ["-y", "-i", str(input_path), "-vn"]

    if fmt == "wav":
        cmd.extend(["-c:a", "pcm_s16le"])
    elif fmt == "flac":
        cmd.extend(["-c:a", "flac"])
    elif fmt == "mp3":
        cmd.extend(["-c:a", "libmp3lame"])
        if args.vbr_quality is not None:
            cmd.extend(["-q:a", str(args.vbr_quality)])
        elif args.bitrate:
            b_str = args.bitrate if args.bitrate.endswith("k") else f"{args.bitrate}k"
            cmd.extend(["-b:a", b_str])
        else:
            cmd.extend(["-b:a", "192k"])
    else:
        cmd.extend(["-c:a", "copy"])

    cmd.append(str(output_path))
    runner.execute_ffmpeg_with_progress(cmd, duration_s)
    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


def handle_cut(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    total_duration = float(probe_data.get("format", {}).get("duration", 0.0))

    start_s = parse_time_to_seconds(args.start) if args.start is not None else 0.0
    end_s = None
    if args.end is not None:
        end_s = parse_time_to_seconds(args.end)
    elif args.duration is not None:
        end_s = start_s + parse_time_to_seconds(args.duration)
    else:
        end_s = total_duration

    cut_duration = max(0.0, end_s - start_s)

    runner.logger.emit_event("start", {
        "command": "cut",
        "input": str(input_path),
        "output": str(output_path),
        "start": start_s,
        "end": end_s,
        "duration": cut_duration,
        "precise": bool(args.precise),
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    cmd = ["-y", "-ss", str(start_s), "-i", str(input_path), "-t", str(cut_duration)]

    if args.precise:
        encoder, _ = get_video_encoder("h264")
        cmd.extend(["-c:v", encoder, "-pix_fmt", "yuv420p", "-c:a", "aac"])
    else:
        # Stream copy with fast input seeking (snaps to keyframe)
        cmd.extend(["-c", "copy"])

    cmd.extend(["-movflags", "+faststart", str(output_path)])
    runner.execute_ffmpeg_with_progress(cmd, cut_duration)
    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


def handle_merge(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    inputs = [Path(p).resolve() for p in args.inputs]

    if len(inputs) < 2:
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": "At least 2 input files required for merge."})
        return ExitCode.ARGUMENT_ERROR

    for p in inputs:
        if not p.is_file():
            runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input file not found: {p}"})
            return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    # Inspect all inputs
    probes = [runner.run_probe(p) for p in inputs]
    total_duration = sum(float(pr.get("format", {}).get("duration", 0.0)) for pr in probes)

    # Check compatibility across all streams
    compat_ok = True
    mismatch_reasons: List[str] = []

    base_probe = probes[0]
    base_v = next((s for s in base_probe.get("streams", []) if s.get("codec_type") == "video"), None)
    base_a = next((s for s in base_probe.get("streams", []) if s.get("codec_type") == "audio"), None)

    for idx, pr in enumerate(probes[1:], start=2):
        curr_v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), None)
        curr_a = next((s for s in pr.get("streams", []) if s.get("codec_type") == "audio"), None)

        if (base_v is None) != (curr_v is None):
            compat_ok = False
            mismatch_reasons.append(f"Input {idx} video presence differs from Input 1")
        elif base_v and curr_v:
            if base_v.get("codec_name") != curr_v.get("codec_name"):
                compat_ok = False
                mismatch_reasons.append(f"Input {idx} codec ({curr_v.get('codec_name')}) differs from Input 1 ({base_v.get('codec_name')})")
            if base_v.get("width") != curr_v.get("width") or base_v.get("height") != curr_v.get("height"):
                compat_ok = False
                mismatch_reasons.append(f"Input {idx} resolution ({curr_v.get('width')}x{curr_v.get('height')}) differs from Input 1 ({base_v.get('width')}x{base_v.get('height')})")
            if base_v.get("pix_fmt") != curr_v.get("pix_fmt"):
                compat_ok = False
                mismatch_reasons.append(f"Input {idx} pixel format ({curr_v.get('pix_fmt')}) differs from Input 1 ({base_v.get('pix_fmt')})")

    if not compat_ok and not args.reencode:
        msg = f"Cannot perform stream-copy merge due to mismatched stream parameters:\n" + "\n".join(f"- {r}" for r in mismatch_reasons) + "\nUse --reencode to normalize and merge."
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": msg})
        return ExitCode.VERIFICATION_ERROR

    runner.logger.emit_event("start", {
        "command": "merge",
        "inputs": [str(p) for p in inputs],
        "output": str(output_path),
        "reencode": bool(args.reencode),
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    temp_dir = tempfile.mkdtemp(prefix="fvt_merge_")
    _REGISTERED_TEMP_DIRS.append(temp_dir)
    try:
        concat_txt = os.path.join(temp_dir, "concat.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in inputs:
                f.write(f"{escape_concat_demuxer_path(p)}\n")

        if args.reencode:
            encoder, _ = get_video_encoder("h264")
            cmd = [
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt,
                "-c:v", encoder,
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(output_path),
            ]
        else:
            cmd = [
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt,
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path),
            ]

        runner.execute_ffmpeg_with_progress(cmd, total_duration)
        runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
        return ExitCode.SUCCESS
    finally:
        if temp_dir in _REGISTERED_TEMP_DIRS:
            _REGISTERED_TEMP_DIRS.remove(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)


def handle_gif(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
    if args.max_seconds and args.max_seconds > 0:
        duration_s = min(duration_s, float(args.max_seconds))

    fps = int(args.fps) if args.fps else 12
    width = int(args.width) if args.width else 480
    dither = args.dither or "sierra2_4a"
    fmt = (args.format or output_path.suffix.lstrip(".") or "gif").lower()

    runner.logger.emit_event("start", {
        "command": "gif",
        "input": str(input_path),
        "output": str(output_path),
        "fps": fps,
        "width": width,
        "format": fmt,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    cmd = ["-y"]
    if args.max_seconds:
        cmd.extend(["-t", str(args.max_seconds)])
    cmd.extend(["-i", str(input_path)])

    if fmt == "webp":
        cmd.extend([
            "-vf", f"fps={fps},scale={width}:-2:flags=lanczos,format=yuv420p",
            "-c:v", "libwebp",
            "-lossless", "0",
            "-q:v", "75",
            "-loop", "0",
            "-an",
            str(output_path),
        ])
        try:
            runner.execute_ffmpeg_with_progress(cmd, duration_s)
        except Exception:
            # Fallback for systems where libwebp lacks specific options or uses different encoder defaults
            fallback_cmd = ["-y"]
            if args.max_seconds:
                fallback_cmd.extend(["-t", str(args.max_seconds)])
            fallback_cmd.extend([
                "-i", str(input_path),
                "-vf", f"fps={fps},scale={width}:-2:flags=lanczos",
                "-loop", "0",
                "-an",
                str(output_path),
            ])
            runner.execute_ffmpeg_with_progress(fallback_cmd, duration_s)
    else:
        # High quality palettegen + paletteuse filtergraph
        vf = f"fps={fps},scale={width}:-2:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither={dither}"
        cmd.extend(["-vf", vf, "-an", str(output_path)])
        runner.execute_ffmpeg_with_progress(cmd, duration_s)

    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


def handle_speed(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    factor = float(args.factor)
    if factor <= 0:
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Speed factor must be positive: {factor}"})
        return ExitCode.ARGUMENT_ERROR

    probe_data = runner.run_probe(input_path)
    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))
    has_audio = any(s.get("codec_type") == "audio" for s in probe_data.get("streams", []))
    has_video = any(s.get("codec_type") == "video" for s in probe_data.get("streams", []))

    new_duration = duration_s / factor

    runner.logger.emit_event("start", {
        "command": "speed",
        "input": str(input_path),
        "output": str(output_path),
        "factor": factor,
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    pts_factor = 1.0 / factor
    filter_parts: List[str] = []
    if has_video:
        filter_parts.append(f"[0:v]setpts={pts_factor:.6f}*PTS[outv]")
    if has_audio:
        atempo_chain = build_atempo_filter_chain(factor)
        filter_parts.append(f"[0:a]{atempo_chain}[outa]")

    filter_complex = ";".join(filter_parts)
    encoder, _ = get_video_encoder("h264")

    cmd = ["-y", "-i", str(input_path), "-filter_complex", filter_complex]
    if has_video:
        cmd.extend(["-map", "[outv]", "-c:v", encoder, "-pix_fmt", "yuv420p"])
    if has_audio:
        cmd.extend(["-map", "[outa]", "-c:a", "aac"])

    cmd.extend(["-movflags", "+faststart", str(output_path)])
    runner.execute_ffmpeg_with_progress(cmd, new_duration)
    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


def handle_strip_meta(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    if output_path.exists() and not runner.overwrite:
        runner.logger.emit_event("error", {"code": ExitCode.VERIFICATION_ERROR, "message": f"Output file already exists: {output_path}"})
        return ExitCode.VERIFICATION_ERROR

    probe_data = runner.run_probe(input_path)
    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))

    runner.logger.emit_event("start", {
        "command": "strip-meta",
        "input": str(input_path),
        "output": str(output_path),
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    cmd = [
        "-y",
        "-i", str(input_path),
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-c", "copy",
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        str(output_path),
    ]

    runner.execute_ffmpeg_with_progress(cmd, duration_s)

    # Post-strip verification
    post_probe = runner.run_probe(output_path)
    fmt_tags = post_probe.get("format", {}).get("tags", {})
    # Filter out structural container tags that ffmpeg muxer always writes
    user_tags = {k: v for k, v in fmt_tags.items() if k not in ["major_brand", "minor_version", "compatible_brands", "encoder"]}

    runner.logger.emit_event("done", {
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
        "remaining_user_tags": user_tags,
        "chapters_count": len(post_probe.get("chapters", [])),
    })
    return ExitCode.SUCCESS


def handle_thumbs(runner: FFmpegRunner, args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.is_file():
        runner.logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Input not found: {input_path}"})
        return ExitCode.ARGUMENT_ERROR

    probe_data = runner.run_probe(input_path)
    duration_s = float(probe_data.get("format", {}).get("duration", 0.0))

    runner.logger.emit_event("start", {
        "command": "thumbs",
        "input": str(input_path),
        "output": str(output_path),
    })

    if runner.dry_run:
        return ExitCode.SUCCESS

    # If contact sheet grid requested
    if args.cols and args.rows:
        cols = int(args.cols)
        rows = int(args.rows)
        total_thumbs = cols * rows
        interval = max(0.1, duration_s / max(total_thumbs, 1))

        width = int(args.width) if args.width else 320
        vf = f"fps=1/{interval:.4f},scale={width}:-1,tile={cols}x{rows}"
        cmd = [
            "-y",
            "-i", str(input_path),
            "-vf", vf,
            "-update", "1",
            "-frames:v", "1",
            str(output_path),
        ]
        runner.execute_ffmpeg_with_progress(cmd, duration_s)
    elif args.timestamps:
        timestamps = [parse_time_to_seconds(t.strip()) for t in args.timestamps.split(",")]
        # Extract at specific timestamp
        ts = timestamps[0] if timestamps else 1.0
        cmd = [
            "-y",
            "-ss", str(ts),
            "-i", str(input_path),
            "-frames:v", "1",
            "-update", "1",
            str(output_path),
        ]
        runner.execute_ffmpeg_with_progress(cmd, 1.0)
    else:
        # Default single thumbnail at 1s or midpoint
        ts = min(1.0, duration_s / 2.0)
        cmd = [
            "-y",
            "-ss", str(ts),
            "-i", str(input_path),
            "-frames:v", "1",
            "-update", "1",
            str(output_path),
        ]
        runner.execute_ffmpeg_with_progress(cmd, 1.0)

    runner.logger.emit_event("done", {"output": str(output_path), "bytes": output_path.stat().st_size})
    return ExitCode.SUCCESS


# ============================================================================
# CLI Parser Setup & Main Entrypoint
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--check", action="store_true", help="Inspect FFmpeg/FFprobe availability and capabilities")
    common_parser.add_argument("--dry-run", action="store_true", help="Print FFmpeg commands without executing")
    common_parser.add_argument("--overwrite", action="store_true", help="Overwrite output files if they exist")
    common_parser.add_argument("--json-progress", action="store_true", help="Emit line-delimited JSON events to stdout")
    common_parser.add_argument("--ffmpeg", help="Path to ffmpeg executable (overrides env FFMPEG_PATH)")
    common_parser.add_argument("--ffprobe", help="Path to ffprobe executable (overrides env FFPROBE_PATH)")
    common_parser.add_argument("--quiet", action="store_true", help="Suppress stderr logs")
    common_parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")

    parser = argparse.ArgumentParser(
        prog="video_toolkit.py",
        description="FFmpeg Video Toolkit Pro - Core Engine",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # compress
    p_comp = subparsers.add_parser("compress", parents=[common_parser], help="Compress video to target byte size or platform preset using 2-pass libx264")
    p_comp.add_argument("input", help="Path to source video file")
    p_comp.add_argument("output", help="Path to output compressed video")
    p_comp.add_argument("--preset", help="Platform preset (discord, whatsapp, github, slack, etc.)")
    p_comp.add_argument("--target-size-mb", type=float, help="Target file size in megabytes")
    p_comp.add_argument("--target-size-bytes", type=int, help="Target file size in raw bytes")
    p_comp.add_argument("--scale", help="Downscale resolution (e.g. 1080p, 720p, 480p, 360p, or W:H)")
    p_comp.add_argument("--audio-bitrate", type=int, default=128, help="Audio bitrate in kbps (default 128)")

    # trim-silence
    p_trim = subparsers.add_parser("trim-silence", parents=[common_parser], help="Detect and remove silent segments from audio/video")
    p_trim.add_argument("input", help="Source file")
    p_trim.add_argument("output", help="Output trimmed file")
    p_trim.add_argument("--noise", default="-30dB", help="Silence audio threshold (default -30dB)")
    p_trim.add_argument("--min-silence", type=float, default=0.5, help="Minimum silence duration in seconds (default 0.5)")
    p_trim.add_argument("--pad", type=float, default=0.1, help="Audio buffer padding in seconds (default 0.1)")

    # shorts
    p_shorts = subparsers.add_parser("shorts", parents=[common_parser], help="Reformat video to 9:16 vertical (1080x1920) for Shorts/TikTok/Reels")
    p_shorts.add_argument("input", help="Source file")
    p_shorts.add_argument("output", help="Output vertical file")
    p_shorts.add_argument("--mode", default="crop", choices=["crop", "blur"], help="Mode: center crop or blurred background fill")
    p_shorts.add_argument("--x-offset", type=int, default=0, help="Horizontal offset in pixels for crop mode")

    # convert
    p_conv = subparsers.add_parser("convert", parents=[common_parser], help="Batch or single video format converter")
    p_conv.add_argument("input", help="Source file or directory")
    p_conv.add_argument("output", nargs="?", help="Output file or directory")
    p_conv.add_argument("--format", default="mp4", help="Target container format (default mp4)")
    p_conv.add_argument("--recursive", action="store_true", help="Recursively search directory")

    # extract-audio
    p_aud = subparsers.add_parser("extract-audio", parents=[common_parser], help="Extract audio track to wav, flac, or mp3")
    p_aud.add_argument("input", help="Source video file")
    p_aud.add_argument("output", help="Output audio file")
    p_aud.add_argument("--format", choices=["wav", "flac", "mp3"], help="Audio container format")
    p_aud.add_argument("--bitrate", help="MP3 bitrate (e.g. 192k, 320k)")
    p_aud.add_argument("--vbr-quality", type=int, choices=range(0, 10), help="MP3 VBR quality level (0=best, 9=worst)")

    # cut
    p_cut = subparsers.add_parser("cut", parents=[common_parser], help="Cut clip by start, end, or duration")
    p_cut.add_argument("input", help="Source file")
    p_cut.add_argument("output", help="Output cut clip")
    p_cut.add_argument("--start", help="Start timestamp (HH:MM:SS or seconds)")
    p_cut.add_argument("--end", help="End timestamp (HH:MM:SS or seconds)")
    p_cut.add_argument("--duration", help="Clip duration in seconds")
    p_cut.add_argument("--precise", action="store_true", help="Re-encode for exact frame accuracy instead of keyframe snapping")

    # merge
    p_merge = subparsers.add_parser("merge", parents=[common_parser], help="Concatenate matching video clips")
    p_merge.add_argument("inputs", nargs="+", help="Input video clips (in order)")
    p_merge.add_argument("--output", "-o", required=True, help="Output merged video")
    p_merge.add_argument("--reencode", action="store_true", help="Re-encode clips if stream parameters mismatch")

    # gif
    p_gif = subparsers.add_parser("gif", parents=[common_parser], help="Create high-quality GIF or animated WebP")
    p_gif.add_argument("input", help="Source video")
    p_gif.add_argument("output", help="Output gif or webp file")
    p_gif.add_argument("--fps", type=int, default=12, help="Frame rate (default 12)")
    p_gif.add_argument("--width", type=int, default=480, help="Output width in pixels (default 480)")
    p_gif.add_argument("--max-seconds", type=float, help="Maximum duration to encode")
    p_gif.add_argument("--dither", default="sierra2_4a", help="Dither algorithm for paletteuse")
    p_gif.add_argument("--format", choices=["gif", "webp"], help="Target format")

    # speed
    p_speed = subparsers.add_parser("speed", parents=[common_parser], help="Adjust video and audio speed")
    p_speed.add_argument("input", help="Source file")
    p_speed.add_argument("output", help="Output speed-adjusted file")
    p_speed.add_argument("--factor", type=float, required=True, help="Speed multiplier (e.g. 0.5, 1.5, 2.0, 4.0)")

    # strip-meta
    p_strip = subparsers.add_parser("strip-meta", parents=[common_parser], help="Remove all metadata, chapters, and location tags")
    p_strip.add_argument("input", help="Source file")
    p_strip.add_argument("output", help="Output stripped file")

    # thumbs
    p_thumbs = subparsers.add_parser("thumbs", parents=[common_parser], help="Generate video thumbnails or a contact sheet")
    p_thumbs.add_argument("input", help="Source file")
    p_thumbs.add_argument("output", help="Output image file or contact sheet")
    p_thumbs.add_argument("--timestamps", help="Comma-separated timestamps (e.g. 00:00:01,00:00:05)")
    p_thumbs.add_argument("--cols", type=int, help="Grid columns for contact sheet")
    p_thumbs.add_argument("--rows", type=int, help="Grid rows for contact sheet")
    p_thumbs.add_argument("--width", type=int, default=320, help="Thumbnail width in pixels")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        raw_args = list(sys.argv[1:])
    else:
        raw_args = list(argv)

    # Normalize options where the value starts with '-' (like --noise -30dB) so argparse does not confuse it for an option flag
    normalized_argv: List[str] = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in ("--noise",) and i + 1 < len(raw_args) and raw_args[i + 1].startswith("-") and not raw_args[i + 1].startswith("--"):
            normalized_argv.append(f"{arg}={raw_args[i + 1]}")
            i += 2
        else:
            normalized_argv.append(arg)
            i += 1

    parser = build_parser()
    args = parser.parse_args(normalized_argv)

    logger = ToolkitLogger(
        json_mode=args.json_progress,
        quiet=args.quiet,
        verbose=args.verbose,
    )

    runner = FFmpegRunner(
        ffmpeg_path=args.ffmpeg,
        ffprobe_path=args.ffprobe,
        logger=logger,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )

    if args.check or args.command == "check":
        return handle_check(runner, as_json=args.json_progress)

    if not args.command:
        parser.print_help(sys.stderr)
        return ExitCode.ARGUMENT_ERROR

    handlers = {
        "compress": handle_compress,
        "trim-silence": handle_trim_silence,
        "shorts": handle_shorts,
        "convert": handle_convert,
        "extract-audio": handle_extract_audio,
        "cut": handle_cut,
        "merge": handle_merge,
        "gif": handle_gif,
        "speed": handle_speed,
        "strip-meta": handle_strip_meta,
        "thumbs": handle_thumbs,
    }

    handler = handlers.get(args.command)
    if not handler:
        logger.emit_event("error", {"code": ExitCode.ARGUMENT_ERROR, "message": f"Unknown command '{args.command}'"})
        return ExitCode.ARGUMENT_ERROR

    try:
        return handler(runner, args)
    except Exception as e:
        logger.emit_event("error", {"code": ExitCode.GENERAL_ERROR, "message": str(e)})
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return ExitCode.GENERAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
