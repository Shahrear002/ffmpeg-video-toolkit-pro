# FFmpeg Video Toolkit Pro

[![CI](https://github.com/agensi/ffmpeg-video-toolkit-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/agensi/ffmpeg-video-toolkit-pro/actions)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-blue.svg)](skill/LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://python.org)
[![Tauri: v2](https://img.shields.io/badge/Tauri-v2-orange.svg)](https://v2.tauri.app)
[![Nuxt: 3](https://img.shields.io/badge/Nuxt-3-00DC82.svg)](https://nuxt.com)

**FFmpeg Video Toolkit Pro** is a commercial, production-grade video processing product engineered around a single, deterministic core engine (`engine/video_toolkit.py`). It powers two distinct commercial deliverables:

1. **Deliverable A — Agensi.io Skill Package**: A lightweight, self-contained AI Agent Skill packaged for [agensi.io](https://agensi.io) that runs directly on buyer-provided FFmpeg with zero pip dependencies, no network permissions, and progressive disclosure documentation.
2. **Deliverable B — Cross-Platform Desktop App**: A fast, privacy-respecting desktop application (Windows, macOS, Linux) built with **Tauri v2** + **Nuxt 3** (TypeScript strict) that executes the engine as a native sidecar with real-time JSON progress streaming, job queues, drag-and-drop batch operations, and an in-app license activation seam.

---

## Repository Layout

```text
ffmpeg-video-toolkit-pro/
├── engine/
│   ├── video_toolkit.py          # Single-file core engine (Python 3.9+, standard library only)
│   ├── tests/                    # Unittest test suite (no external dependencies)
│   │   ├── test_pure_logic.py    # Offline unit tests (bitrate math, silence parsing, atempo)
│   │   └── test_integration.py  # Live media tests against lavfi synthetic test fixtures
│   └── data/
│       └── platform_limits.json  # Verified platform upload caps with sources & timestamps
├── skill/                        # Deliverable A: What gets zipped for Agensi.io
│   ├── SKILL.md                  # Progressive disclosure agent instructions & subcommand mapping
│   ├── LICENSE                   # Draft commercial single-user software license
│   ├── README.md                 # Agent installation guide & 10 copy-paste recipes
│   ├── scripts/
│   │   └── video_toolkit.py      # Synced from engine at build time (never hand-edited)
│   └── references/
│       ├── platform-limits.md    # Compiled markdown reference of verified platform caps
│       └── encoding-presets.md   # Guide on CRF vs. 2-pass bitrate, bppf, and yuv420p rules
├── desktop/                      # Deliverable B: Tauri v2 + Nuxt 3 desktop app
│   ├── src-tauri/                # Rust backend with scoped sidecar process capabilities
│   └── app/                      # Nuxt 3 + TypeScript strict + Tailwind UI
├── scripts/
│   ├── audit_self.py             # Security audit static analyzer (zero network, zero eval/exec)
│   ├── build_skill_zip.py        # Deterministic zip packager with SHA256 checksums
│   ├── build_engine_sidecar.py   # PyInstaller sidecar binary cross-compilation helper
│   └── fetch_ffmpeg.py           # Pinned, checksum-verified FFmpeg binary downloader
├── docs/
│   ├── ARCHITECTURE.md           # System design, dataflow & JSON progress schema
│   ├── DECISIONS.md              # Architectural & algorithmic decision log
│   ├── DEVELOPMENT.md            # Local developer onboarding & release runbook
│   └── AGENSI_LISTING.md         # Commercial marketplace copy, pricing & screenshot shot list
├── .gitignore
├── README.md                     # Root documentation
├── CHANGELOG.md
├── SECURITY.md
└── THIRD_PARTY_NOTICES.md
```

---

## Core Engine Feature Matrix

The core engine is driven via `python engine/video_toolkit.py <subcommand>` (or `python scripts/video_toolkit.py <subcommand>` inside the skill package):

| Subcommand | Purpose | Key Technical Guarantees |
| :--- | :--- | :--- |
| `compress` | Target platform byte limits | True 2-pass libx264, 5% safety margin, bppf quality floor, post-encode verification. |
| `trim-silence` | Remove audio pauses / dead air | `silencedetect` parsing, audio padding, `-filter_complex_script` (handles 500+ cuts safely). |
| `shorts` | Landscape to 9:16 vertical | 1080x1920 output via center crop (`--mode crop`) or blurred background fill (`--mode blur`). |
| `convert` | Single or batch container conversion | Stream-copies compatible H.264/AAC streams; re-encodes incompatible codecs. Continues on error. |
| `extract-audio`| Rip audio track | Supports `wav` (pcm_s16le), `flac` (lossless), and `mp3` (libmp3lame CBR/VBR). |
| `cut` | Trim clips | Fast keyframe-snapped copy (default) or re-encoded frame-accurate cut (`--precise`). |
| `merge` | Concatenate video clips | Probes stream params first; rejects mismatches with granular diff unless `--reencode` is passed. |
| `gif` | Animated GIF or WebP | 2-pass `palettegen` + `paletteuse` with dithering for color banding elimination. |
| `speed` | Adjust playback tempo | Video `setpts`; chains `atempo` filters for factors $> 2.0\times$ or $< 0.5\times$ without pitch distortion. |
| `strip-meta` | Privacy / Sanitization | Purges all EXIF metadata, camera serial numbers, GPS tags, and chapters (`+bitexact`). |
| `thumbs` | Previews & Contact sheets | Extracts frame at timestamp or generates full tiled contact sheets (`tile` filter). |
| `--check` | Pre-flight environment check | Diagnostic reporting of FFmpeg/FFprobe availability, versions, encoders, and filters. |

### Global Flags Supported Across All Subcommands
- `--dry-run`: Prints exact FFmpeg command-lines without executing them.
- `--overwrite`: Refuses to overwrite destination files by default (exit code 4) unless explicitly set.
- `--json-progress`: Emits one JSON event per line on stdout (`start`, `progress`, `warning`, `done`, `error`) for agent and GUI integration.
- `--ffmpeg <path>` & `--ffprobe <path>`: Explicit binary overrides (or via `FFMPEG_PATH`/`FFPROBE_PATH` environment variables).
- `--quiet` / `--verbose`: Controls stderr diagnostic logging.

---

## Verified Platform Video Limits Reference

All platform size constraints are stored in `engine/data/platform_limits.json` and verified against official platform specifications:

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

## Architectural Principles & Security Model

1. **Zero External Dependencies**: The engine relies exclusively on the Python 3.9+ standard library (`argparse`, `subprocess`, `json`, `pathlib`, `tempfile`, `threading`).
2. **Subprocess Pipe Deadlock Immunity**: Long-running FFmpeg commands are drained through concurrent background threads (`threading.Thread`) combined with `-nostats -progress pipe:1`.
3. **No Console Flashing on Windows**: All subprocess calls pass `creationflags = 0x08000000` (`CREATE_NO_WINDOW`) so GUI users never experience flashing terminal windows.
4. **Marketplace Security Audit**: The codebase passes `scripts/audit_self.py` by construction:
   - Zero network requests (`no urllib`, `no requests`, `no sockets`).
   - Zero dynamic code evaluation (`no eval`, `no exec`, `no __import__`).
   - Zero obfuscation (`no base64 decoding`).
   - Zero prompt injection patterns or directory escaping.

---

## Quickstart & Local Verification

### 1. Run the Pre-Flight Diagnostic
```bash
python engine/video_toolkit.py --check
```

### 2. Run the Full Test Suite
The repository includes both pure-logic offline unit tests and live media integration tests that generate synthetic clips via FFmpeg's `lavfi` filtergraph:
```bash
python -m unittest discover -s engine/tests
```
*(Runs 31 tests covering bitrate math, silence parsing, atempo chaining, shorts cropping, contact sheets, format conversion, and 3-target compress limit enforcement).*

### 3. Run the Security Audit Scanner
```bash
python scripts/audit_self.py
```

### 4. Build the Deterministic Agensi Skill Package
```bash
python scripts/build_skill_zip.py
```
Outputs `dist/ffmpeg-video-toolkit-pro-skill-v1.0.0.zip` and its companion `.sha256` checksum file.

---

## Companion Workflows

When producing short-form vertical content using `shorts`:
```bash
python scripts/video_toolkit.py shorts raw_stream.mp4 short.mp4 --mode blur
```
We recommend pairing this output with [Subtitle Generator Pro](https://agensi.io/skills/subtitle-generator-pro) to automatically transcribe audio and burn animated karaoke-style subtitles onto your video.

---

## License & Third-Party Notices

* **Toolkit Engine & Skill Package**: Licensed under a commercial single-user software license. See [skill/LICENSE](skill/LICENSE).
* **FFmpeg**: FFmpeg is an open-source software project licensed under the LGPL v2.1+ or GPL v2+ depending on configured build options. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details, attribution, and source-code build scripts.
