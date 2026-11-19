---
name: ffmpeg-video-toolkit-pro
description: Professional, production-grade video processing toolkit powered by a verified FFmpeg engine. Use whenever the user asks to compress video to meet size limits (Discord 20MB, WhatsApp 16MB, GitHub 25MB, Slack, etc.), trim silence from video/podcasts, convert videos to vertical 9:16 Shorts/Reels/TikTok format, batch convert containers (MP4, MKV, MOV, WebM), extract audio (MP3, WAV, FLAC), cut clips losslessly or with frame precision, concatenate/merge videos, generate animated GIFs or WebPs, adjust speed with pitch preservation, strip metadata/GPS tags, or create thumbnail contact sheets.
license: Commercial (Single-User)
compatibility: Python 3.9+ with FFmpeg and FFprobe installed (libx264, aac, libmp3lame)
metadata:
  author: Video Toolkit Pro Team
  version: "1.0.0"
  tags:
    - video
    - ffmpeg
    - compression
    - shorts
    - silence-removal
    - gif
    - audio-extraction
    - transcoding
allowed-tools: run_command read_file write_file
---

# FFmpeg Video Toolkit Pro — Agent Execution Guide

You are operating **FFmpeg Video Toolkit Pro**, a self-contained, deterministic video processing engine.
All media operations are driven through the verified Python CLI script:
`python scripts/video_toolkit.py <subcommand> [args]`

This skill executes 100% locally with **zero external dependencies** and **no network access**.

---

## 1. Always Run Pre-Flight Diagnostic First

Before executing any media conversion or processing command, verify that the user's host environment has `ffmpeg` and `ffprobe` installed with required codecs:

```bash
python scripts/video_toolkit.py --check --json-progress
```

* **If status is `"ok"`**: Proceed with the requested task.
* **If status is `"missing_dependencies"`**: Stop and report to the user:
  - Windows: `winget install Gyan.FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org).
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt update && sudo apt install ffmpeg`

---

## 2. Task-to-Subcommand Mapping

| User Intent / Request Phrasing | Subcommand | Key Arguments |
| :--- | :--- | :--- |
| "Make this under 20MB / fit on Discord / WhatsApp / GitHub" | `compress` | `input output --preset <platform>` or `--target-size-mb <N>` |
| "Cut out silent pauses / remove dead air / clean up podcast" | `trim-silence` | `input output --noise -30dB --min-silence 0.5 --pad 0.1` |
| "Turn this into a Short / Reel / TikTok / 9:16 vertical video" | `shorts` | `input output --mode crop` or `--mode blur` |
| "Convert this MKV/MOV/AVI to MP4" or batch convert folder | `convert` | `input [output] --format mp4 [--recursive]` |
| "Extract audio track / rip sound to MP3/WAV/FLAC" | `extract-audio` | `input output.mp3 --bitrate 192k` or `--format wav` |
| "Clip from 00:01:15 to 00:02:30 / trim video" | `cut` | `input output --start 00:01:15 --end 00:02:30 [--precise]` |
| "Join these video clips together / merge files" | `merge` | `input1.mp4 input2.mp4 -o merged.mp4 [--reencode]` |
| "Convert video snippet to animated GIF or WebP" | `gif` | `input output.gif --fps 12 --width 480` or `--format webp` |
| "Speed up 2x / slow down 0.5x" | `speed` | `input output --factor 2.0` |
| "Remove metadata / strip GPS / clean camera tags" | `strip-meta` | `input output` |
| "Create preview thumbnail / contact sheet grid" | `thumbs` | `input sheet.jpg --cols 3 --rows 3` or `--timestamps 00:00:05` |

---

## 3. Subcommand Quick Reference & Examples

### A) Smart Two-Pass Compression
Calculates video bitrate with a 5% container overhead safety buffer. Verifies post-encode size strictly `< target`.
```bash
# Compress using verified platform presets
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset discord
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset whatsapp
python scripts/video_toolkit.py compress input.mp4 output.mp4 --preset github

# Custom target size with downscaling guardrail
python scripts/video_toolkit.py compress raw.mp4 compressed.mp4 --target-size-mb 15 --scale 720p
```
*Platform reference*: Consult [references/platform-limits.md](references/platform-limits.md) for verified size limits.

### B) Silence Removal (Dead-Air Trimming)
Parses audio volume and cuts silent intervals with non-clipping padding:
```bash
python scripts/video_toolkit.py trim-silence podcast.mp4 trimmed.mp4 --noise -30dB --min-silence 0.5 --pad 0.1
```

### C) Vertical Shorts & Reels (9:16)
Centers and crops or generates a blurred background fill for 1080x1920 output:
```bash
# Mode crop: center crop with optional pixel offset
python scripts/video_toolkit.py shorts landscape.mp4 short.mp4 --mode crop

# Mode blur: original centered over blurred zoomed background
python scripts/video_toolkit.py shorts landscape.mp4 short.mp4 --mode blur
```
> [!TIP]
> *Companion Workflow*: Combine vertical formatting with [Subtitle Generator Pro](https://agensi.io/skills/subtitle-generator-pro) to automatically burn viral animated captions onto the resulting Shorts.

### D) Lossless or Frame-Accurate Cutting
```bash
# Lossless stream copy (instant, keyframe snapping)
python scripts/video_toolkit.py cut lecture.mp4 highlight.mp4 --start 00:02:00 --duration 45

# Precise frame-accurate cut (re-encoded)
python scripts/video_toolkit.py cut lecture.mp4 highlight.mp4 --start 00:02:00 --duration 45 --precise
```

### E) Clip Concatenation / Merge
```bash
# Lossless merge (checks codec, resolution, and pixel format compatibility first)
python scripts/video_toolkit.py merge intro.mp4 body.mp4 outro.mp4 -o full_video.mp4

# Normalize and merge mismatched clips
python scripts/video_toolkit.py merge intro.mp4 body.mp4 outro.mp4 -o full_video.mp4 --reencode
```

### F) High-Quality GIF & Animated WebP
Uses two-pass palette generation for artifact-free color dithering:
```bash
python scripts/video_toolkit.py gif clip.mp4 demo.gif --fps 15 --width 480 --dither sierra2_4a
python scripts/video_toolkit.py gif clip.mp4 demo.webp --format webp --fps 15 --width 480
```

---

## 4. How to Read Output & Errors

When invoking from an agent script, always include `--json-progress` to stream structured JSON events on stdout:

```json
{"event": "start", "command": "compress", "input": "input.mp4", "output": "output.mp4"}
{"event": "progress", "percent": 45.2, "fps": 112.4, "speed": "2.4x", "eta_s": 8.5, "pass": 1}
{"event": "done", "output": "output.mp4", "bytes": 18239012}
```

### Documented Exit Codes
* **0 (SUCCESS)**: Task completed and verified.
* **1 (GENERAL_ERROR)**: Unexpected runtime exception. Check stderr trace.
* **2 (ARGUMENT_ERROR)**: Invalid arguments, missing required flags, or non-existent file.
* **3 (DEPENDENCY_ERROR)**: `ffmpeg` or `ffprobe` binary missing from PATH. Run `--check`.
* **4 (VERIFICATION_ERROR)**: File exists without `--overwrite`, output size exceeded target limit, or merge streams mismatched without `--reencode`.
* **5 (STREAM_ERROR)**: Media missing required stream (e.g. attempting `trim-silence` on a video with no audio).
* **6 (CANCELLED)**: Process terminated via SIGINT/SIGTERM.

---

## 5. What NEVER to Do

1. **NEVER string-interpolate shell commands**: Always invoke `video_toolkit.py` with argument lists.
2. **NEVER overwrite files without `--overwrite`**: By default, the engine halts with exit code 4 if the destination exists to prevent accidental data loss.
3. **NEVER ignore resolution when compressing**: If the engine fails with a Bits-Per-Pixel-Per-Frame (bppf) warning, pass `--scale 720p` or `--scale 480p` rather than lowering bitrate into unwatchable garbage.
4. **NEVER attempt network calls**: The toolkit is strictly local. Do not attempt to pipe remote URLs directly into the engine; download media to the local disk first.
