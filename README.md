# FFmpeg Video Toolkit Pro

[![CI](https://github.com/agensi/ffmpeg-video-toolkit-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/agensi/ffmpeg-video-toolkit-pro/actions)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-blue.svg)](skill/LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://python.org)
[![Tauri: v2](https://img.shields.io/badge/Tauri-v2-orange.svg)](https://v2.tauri.app)
[![Nuxt: 3](https://img.shields.io/badge/Nuxt-3-00DC82.svg)](https://nuxt.com)

**FFmpeg Video Toolkit Pro** is a commercial, production-grade video processing product engineered around a single, deterministic core engine (`engine/video_toolkit.py`). It powers two distinct deliverables:

1. **Deliverable A — Agensi.io Skill Package**: A self-contained AI Agent Skill packaged for [agensi.io](https://agensi.io) that runs directly on buyer-provided FFmpeg with zero pip dependencies, zero network permissions, and progressive disclosure documentation.
2. **Deliverable B — Cross-Platform Desktop App**: A fast, privacy-respecting desktop application (Windows, macOS, Linux) built with **Tauri v2** + **Nuxt 3** (TypeScript strict) that executes the engine as a native sidecar with real-time JSON progress streaming, job queues, drag-and-drop batch operations, and an in-app license activation seam.

---

## 1. Deliverables & Installation

### Deliverable A: AI Agent Skill Package (Agensi.io)
Designed to run inside AI agent sandboxes (Claude Code, Cursor, Codex CLI, OpenClaw, Gemini CLI):
```bash
# Extract the deterministic skill zip from releases or agensi.io:
unzip ffmpeg-video-toolkit-pro-skill-v1.0.0.zip -d ~/.agensi/skills/ffmpeg-video-toolkit-pro
```
The agent discovers `skill/SKILL.md` and invokes `python skill/scripts/video_toolkit.py <subcommand>` using local FFmpeg.

### Deliverable B: Desktop Application (Windows, macOS, Linux)
Install native desktop binaries from GitHub Releases:
- **Windows**: Download and run `.msi` or `.exe` installer.
- **macOS**: Download `.dmg`, open, and drag to Applications.
- **Linux**: Download `.AppImage` (`chmod +x` and run) or install `.deb`.

The desktop application bundles pinned FFmpeg, FFprobe, and the native engine sidecar—no Python or FFmpeg installation required on the user's host system.

---

## 2. Command Reference & Real Examples

All subcommands can be executed via the CLI engine or the Desktop GUI:

### 1. `compress` — Target Platform File Size Limits
Compresses to exact file size limits using true 2-pass libx264, 5% container margin, and bppf quality floor:
```bash
# Compress using verified platform preset (Discord 20 MB cap)
python engine/video_toolkit.py compress -i raw_gameplay.mp4 -o discord_clip.mp4 --preset discord

# Compress to custom 50 MB limit with automatic 720p downscaling guardrail
python engine/video_toolkit.py compress -i vlog_4k.mp4 -o vlog_compressed.mp4 --target-mb 50 --scale 720p
```

### 2. `trim-silence` — Audio Dead Air Removal
Detects silent sections using `silencedetect` and stitches keep-segments using `-filter_complex_script`:
```bash
# Trim dead air with -30 dB threshold and 0.1s speech padding
python engine/video_toolkit.py trim-silence -i podcast_raw.mp4 -o podcast_snappy.mp4 --noise -30dB --min-silence 0.5 --pad 0.1
```

### 3. `shorts` — 16:9 Landscape to 9:16 Vertical (1080x1920)
Formats video for TikTok, YouTube Shorts, and Instagram Reels:
```bash
# Mode: Blurred scaled background with centered original
python engine/video_toolkit.py shorts -i stream_clip.mp4 -o reel_blur.mp4 --mode blur

# Mode: Center crop with horizontal face-centering offset
python engine/video_toolkit.py shorts -i interview.mp4 -o reel_crop.mp4 --mode crop --x-offset 120
```

### 4. `convert` — Standardize to MP4 (H.264 / AAC / faststart)
Stream-copies compatible streams without re-encoding; re-encodes incompatible codecs:
```bash
# Convert single file
python engine/video_toolkit.py convert -i obs_recording.mkv -o web_stream.mp4

# Batch convert folder recursively
python engine/video_toolkit.py convert -i ./footage/ -o ./web_mp4/ --recursive
```

### 5. `extract-audio` — High-Fidelity Audio Extraction
Extracts audio to uncompressed WAV, lossless FLAC, or high-quality MP3:
```bash
# Extract 320 kbps CBR MP3
python engine/video_toolkit.py extract-audio -i conference.mp4 -o audio.mp3 --format mp3 --quality 320k

# Extract lossless WAV for editing
python engine/video_toolkit.py extract-audio -i session.mov -o master_audio.wav --format wav
```

### 6. `cut` — Fast or Precise Clipping
```bash
# Fast stream-copy cut (keyframe snapping)
python engine/video_toolkit.py cut -i raw.mp4 -o clip1.mp4 --start 00:01:15 --duration 00:00:30

# Frame-accurate precise re-encoded cut
python engine/video_toolkit.py cut -i raw.mp4 -o clip2.mp4 --start 12.34 --end 45.67 --precise
```

### 7. `merge` — Seamless Concat Demuxer Join
Verifies codec, resolution, and fps compatibility before concatenation:
```bash
# Seamless join of identical clips
python engine/video_toolkit.py merge -i part1.mp4 -i part2.mp4 -i part3.mp4 -o complete.mp4

# Join with re-encoding normalization if inputs have mismatched resolutions
python engine/video_toolkit.py merge -i intro.mp4 -i main.mov -o output.mp4 --reencode
```

### 8. `gif` — High-Quality Animated GIF / WebP
Two-pass `palettegen` + `paletteuse` with dithering:
```bash
# 15 fps, 480px width, 10-second animated GIF
python engine/video_toolkit.py gif -i tutorial.mp4 -o demo.gif --fps 15 --width 480 --max-seconds 10

# High-efficiency animated WebP
python engine/video_toolkit.py gif -i animation.mp4 -o demo.webp --format webp --fps 24
```

### 9. `speed` — Playback Tempo Adjustments
Chains `atempo` filters for arbitrary speed factors without audio pitch shifting:
```bash
# 2.0x double speed
python engine/video_toolkit.py speed -i lecture.mp4 -o lecture_fast.mp4 --factor 2.0

# 0.5x smooth slow-motion
python engine/video_toolkit.py speed -i replay.mp4 -o replay_slow.mp4 --factor 0.5
```

### 10. `strip-meta` — Complete Privacy Sanitization
Removes EXIF tags, GPS coordinates, camera serial numbers, and chapters:
```bash
python engine/video_toolkit.py strip-meta -i drone_flight.mp4 -o drone_clean.mp4
```

### 11. `thumbs` — Previews & Contact Sheets
```bash
# Single preview frame at 15.5 seconds
python engine/video_toolkit.py thumbs -i movie.mp4 -o thumb.jpg --timestamps 15.5

# 4x4 tiled contact sheet
python engine/video_toolkit.py thumbs -i movie.mp4 -o contact_sheet.jpg --sheet --cols 4 --rows 4
```

---

## 3. Verified Platform Size Limits Reference

Limits are stored in `engine/data/platform_limits.json` and verified against official platform specifications:

| Platform Preset | Target Size | Max Bytes | Last Verified | Status | Official Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `discord` | 20 MB | 20,971,520 | 2026-11-19 | **VERIFIED** | [Discord Help Center](https://discord.com) |
| `discord-nitro-basic` | 50 MB | 52,428,800 | 2026-11-19 | **VERIFIED** | [Discord Nitro Pricing](https://discord.com) |
| `discord-nitro` | 1 GB | 1,073,741,824 | 2026-11-19 | **VERIFIED** | [Discord Nitro Tier](https://discord.com) |
| `whatsapp` | 16 MB | 16,777,216 | 2026-11-19 | **VERIFIED** | [WhatsApp Media FAQ](https://faq.whatsapp.com) |
| `whatsapp-doc` | 2 GB | 2,147,483,648 | 2026-11-19 | **VERIFIED** | [WhatsApp Doc Limit](https://faq.whatsapp.com) |
| `github` | 25 MB | 26,214,400 | 2026-11-19 | **VERIFIED** | [GitHub File Attachments](https://docs.github.com) |
| `github-push` | 100 MB | 104,857,600 | 2026-11-19 | **VERIFIED** | [GitHub Large Files](https://docs.github.com) |
| `x-twitter` | 512 MB | 536,870,912 | 2026-11-19 | **VERIFIED** | [X Video Specifications](https://help.twitter.com) |
| `email-gmail` | 20 MB | 20,971,520 | 2026-11-19 | **VERIFIED** | [Google Mail Attachments](https://support.google.com/mail) |
| `slack` | 1 GB | 1,073,741,824 | 2026-11-19 | **VERIFIED** | [Slack File Limits](https://slack.com/help) |

---

## 4. Frequently Asked Questions (FAQ)

**Q: Why does `compress` refuse to encode high-resolution videos to tiny limits?**  
A: Naive compression below ~0.04 bits-per-pixel-per-frame (bppf) turns video into unwatchable macroblocked garbage. When a computed bitrate is too low for the resolution, the engine halts with exit code 2 and advises you to downscale (e.g. `--scale 720p` or `--scale 480p`) for clean image fidelity.

**Q: Does the desktop application require Python or FFmpeg installed on the user's computer?**  
A: No. The desktop application bundles the PyInstaller-compiled engine and pinned FFmpeg/FFprobe binaries as self-contained sidecars.

**Q: Can this be run on headless servers or AI agents without a GUI?**  
A: Yes. Deliverable A runs anywhere with Python 3.9+ and FFmpeg. Passing `--json-progress` gives automated agents typed JSON event lines on stdout.

---

## 5. Troubleshooting & Exit Codes

| Exit Code | Meaning | Solution |
|---|---|---|
| `0` | Success | Normal exit. |
| `1` | General Runtime Error | Check input file permissions and codec support. |
| `2` | Argument / Bitrate Error | Bitrate too low for resolution; add `--scale 720p` or check CLI syntax. |
| `3` | Missing Dependency | Install FFmpeg or pass `--ffmpeg <path>` / `--ffprobe <path>`. |
| `4` | Verification Error | Output file already exists (use `--overwrite`) or output exceeded target size limit. |
| `5` | Stream Error | Missing audio stream (e.g. `trim-silence` on video with no sound). |
| `6` | Cancelled / Aborted | Child process interrupted by SIGINT / SIGTERM. |

---

## 6. Building from Source

Detailed build and test instructions are available in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

```bash
# 1. Run local test suite (Python engine + synthetic media)
python -m unittest discover -s engine/tests

# 2. Run AST static security audit
python scripts/audit_self.py

# 3. Build Agensi Skill package
python scripts/build_skill_zip.py

# 4. Run Desktop Vitest suite
cd desktop && pnpm test

# 5. Run Tauri Rust unit tests
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

---

## 7. License & Third-Party Notices

* **Toolkit Engine & Agensi Skill Package**: Commercial Single-User License. See [skill/LICENSE](skill/LICENSE).
* **Desktop Application**: Commercial Desktop Application License.
* **Third-Party Open Source**: Bundles FFmpeg and libx264 under the GNU General Public License v2+ (GPL v2+). In accordance with GPL v2 § 3, complete machine-readable source code is available at https://github.com/FFmpeg/FFmpeg. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full notices.
