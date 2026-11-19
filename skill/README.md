# FFmpeg Video Toolkit Pro — Skill Package

**FFmpeg Video Toolkit Pro** is a commercial, production-ready AI Agent Skill that equips coding agents and automation workflows with deterministic, professional video processing capabilities.

Powered by a single-file, zero-dependency Python engine (`scripts/video_toolkit.py`), it interfaces directly with your local FFmpeg installation to perform fast, robust media operations.

---

## Requirements

1. **Python 3.9+** (Standard library only; zero pip dependencies).
2. **FFmpeg & FFprobe** installed and available in PATH:
   - Must include `libx264` (H.264 video), `aac` (audio), and `libmp3lame` (MP3).
   - Verify anytime with `python scripts/video_toolkit.py --check`.

---

## Installation by AI Agent

### 1. Claude Code
Place the skill package into your workspace skills directory:
```bash
# In your repository root
mkdir -p .claude/skills/ffmpeg-video-toolkit-pro
unzip ffmpeg-video-toolkit-pro-skill-v1.0.0.zip -d .claude/skills/ffmpeg-video-toolkit-pro
```

### 2. Cursor
Add the skill folder to `.cursor/rules/` or project context:
```bash
mkdir -p .cursor/skills/ffmpeg-video-toolkit-pro
unzip ffmpeg-video-toolkit-pro-skill-v1.0.0.zip -d .cursor/skills/ffmpeg-video-toolkit-pro
```

### 3. Codex CLI / Gemini CLI / OpenClaw
Unzip the skill folder anywhere in your project:
```bash
unzip ffmpeg-video-toolkit-pro-skill-v1.0.0.zip -d ./skills/ffmpeg-video-toolkit-pro
```

---

## 10 Copy-Paste Examples

### 1. Pre-Flight System Check
Verify FFmpeg binary location, encoder capabilities, and filter availability:
```bash
python scripts/video_toolkit.py --check --json-progress
```

### 2. Compress Video for Discord (Free Tier: 20MB)
True two-pass libx264 encode with strict size verification:
```bash
python scripts/video_toolkit.py compress raw_clip.mp4 discord_ready.mp4 --preset discord
```

### 3. Compress for WhatsApp (16MB Media Limit)
Downscales automatically if needed to prevent macroblocking:
```bash
python scripts/video_toolkit.py compress gameplay.mp4 wa_clip.mp4 --preset whatsapp --scale 720p
```

### 4. Remove Dead Air / Silence from Podcast or Lecture
Inverts silence into keep segments and merges them with non-clipping padding:
```bash
python scripts/video_toolkit.py trim-silence podcast.mp4 trimmed.mp4 --noise -30dB --min-silence 0.5 --pad 0.1
```

### 5. Create 9:16 Vertical Video (Center Crop Mode)
Generates 1080x1920 vertical video for YouTube Shorts, Instagram Reels, and TikTok:
```bash
python scripts/video_toolkit.py shorts landscape.mp4 vertical_short.mp4 --mode crop
```

### 6. Create 9:16 Vertical Video with Blurred Zoomed Background
Preserves entire landscape frame centered over a blurred, scaled background:
```bash
python scripts/video_toolkit.py shorts landscape.mp4 vertical_blur.mp4 --mode blur
```

### 7. Extract High-Quality MP3 from Video
Extracts audio directly with CBR or VBR configuration:
```bash
python scripts/video_toolkit.py extract-audio interview.mp4 audio.mp3 --format mp3 --bitrate 320k
```

### 8. Frame-Accurate Precise Cutting
Re-encodes boundaries to cut exact timestamps without keyframe snapping:
```bash
python scripts/video_toolkit.py cut input.mp4 highlight.mp4 --start 00:01:30 --duration 15 --precise
```

### 9. Join Multiple Video Clips Together
Probes stream parameters first; verifies codec, resolution, and fps match:
```bash
python scripts/video_toolkit.py merge part1.mp4 part2.mp4 part3.mp4 -o final.mp4
```

### 10. Generate High-Quality Animated GIF or WebP
Two-pass color palette generation with artifact-free dithering:
```bash
python scripts/video_toolkit.py gif demo.mp4 preview.gif --fps 15 --width 480 --dither sierra2_4a
```

---

## Troubleshooting

| Error Message | Cause | Resolution |
| :--- | :--- | :--- |
| `[ERROR 3] FFmpeg executable not found` | `ffmpeg` is not in your system PATH | Run `winget install Gyan.FFmpeg` (Windows) or `brew install ffmpeg` (macOS), or pass `--ffmpeg /path/to/ffmpeg`. |
| `[ERROR 4] Output file already exists` | Destination file exists and `--overwrite` was omitted | Add `--overwrite` if you intend to replace the target file. |
| `[ERROR 4] Computed video bitrate is too low...` | Target file size is too small for input resolution | Add `--scale 720p` or `--scale 480p` to reduce pixel count. |
| `[ERROR 4] Cannot perform stream-copy merge...` | Clips have different resolutions, codecs, or frame rates | Add `--reencode` to normalize all inputs automatically. |
| `[ERROR 5] Input contains no audio stream` | Silence trimming requested on video without audio track | Ensure input media has an active audio channel. |

---

## License & Support
Commercial Single-User License. See `LICENSE` for terms.
For questions and issue reports: support@agensi.io
