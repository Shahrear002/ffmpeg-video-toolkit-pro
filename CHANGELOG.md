# Changelog

All notable changes to **FFmpeg Video Toolkit Pro** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-22

### Initial Commercial Production Release

#### Core Engine (`engine/video_toolkit.py`)
- **Single-File Architecture**: Zero-pip-dependency Python 3.9+ standard library engine.
- **11 Commercial Video Subcommands**:
  - `compress`: True 2-pass libx264 compression with platform size limit presets (Discord 20MB, WhatsApp 16MB, GitHub 25MB, X 512MB, Gmail 20MB, Slack 1GB), container overhead safety margins (5%), and Bits-Per-Pixel-Per-Frame (bppf) quality floor protection.
  - `trim-silence`: `silencedetect` audio analysis, keep-segment generation, and synchronized A/V stitching using dynamic `-filter_complex_script` files.
  - `shorts`: 1080x1920 vertical conversion for 9:16 mobile platforms (TikTok, YouTube Shorts, Reels) using either center crop (with `--x-offset`) or blurred scaled background.
  - `convert`: Single-file and recursive batch standardization to MP4 (H.264 / AAC / `+faststart`) with stream-copy codec compatibility passthrough.
  - `extract-audio`: Extraction to uncompressed WAV, lossless FLAC, or high-quality MP3 (CBR/VBR).
  - `cut`: Fast keyframe-snapped stream copy cuts or `--precise` frame-accurate re-encoded cuts.
  - `merge`: Strict pre-merge ffprobe stream validation (codec, resolution, fps) with concat demuxer join and `--reencode` normalization.
  - `gif`: Two-pass `palettegen` + `paletteuse` animated GIFs or modern animated WebP.
  - `speed`: Playback speed adjustments from 0.25x to 4.0x using chained `atempo` filters and `setpts`.
  - `strip-meta`: Complete privacy sanitization removing EXIF tags, GPS metadata, camera profiles, and chapter markers.
  - `thumbs`: Single frame extraction at timestamps or tiled contact sheets (`tile` filter).
- **Diagnostics & Progress**:
  - `--check` system diagnostic verifying FFmpeg, FFprobe, and codec capabilities.
  - `--json-progress` streaming typed events (`start`, `progress`, `warning`, `done`, `error`) with monotonic multi-pass scaling.
  - Deterministic exit codes (`0` to `6`).

#### Deliverable A: Agensi Agent Skill (`skill/`)
- **Agensi Format Specification Compliance**: Standard frontmatter, progressive disclosure, task-to-subcommand mapping, and copy-paste recipes.
- **Automated AST Security Audit**: `scripts/audit_self.py` statically verifying zero network calls, zero `eval`/`exec`, and no safety bypasses.
- **Deterministic Packaging**: `scripts/build_skill_zip.py` compiling verified platform limits, licensing, and clean SHA-256 checksums.
- **Documentation & References**: Detailed guides on encoding presets, CRF vs 2-pass math, and platform limits.

#### Deliverable B: Desktop Application (`desktop/`)
- **Tauri v2 + Nuxt 3 (TypeScript strict)**: Native desktop application with zero telemetry and local sandboxing.
- **Native Sidecar Execution**: PyInstaller-compiled engine and pinned FFmpeg/FFprobe binaries staged as scoped sidecars (`desktop/src-tauri/binaries/`).
- **Comprehensive UI**:
  - 11 dedicated tool screens with preset selectors and live read-only command preview.
  - Reactive job queue with progress percentage, FPS, speed, ETA, Cancellation, and Retry.
  - Batch conversion support via multi-file and folder drag-and-drop.
  - Live execution log terminal with one-click clipboard copying.
  - Interactive `--check` diagnostic modal.
  - In-app Licenses view presenting GPL v2+ source code offer for FFmpeg/libx264.
  - Commercial license key activation seam (`FVT-PRO-*` / `AGY-*`).
  - Accessible dark/light UI themes.
