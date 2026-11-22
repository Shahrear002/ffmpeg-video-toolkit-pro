# Architectural & Implementation Decisions

This document records the architectural and design decisions made for **FFmpeg Video Toolkit Pro**.

---

## 1. Engine Design: Single-File, Standard Library Only (Python 3.9+)
* **Context**: The engine must be packaged both as an Agensi skill package (run directly by buyers or agents via Python) and bundled into desktop sidecar binaries via PyInstaller.
* **Decision**: Implement `engine/video_toolkit.py` as a single file using only Python standard library modules (`argparse`, `subprocess`, `json`, `sys`, `os`, `re`, `pathlib`, `tempfile`, `shutil`, `signal`, `math`, `time`, `typing`).
* **Rationale**: Eliminates pip dependency friction for Agensi buyers, ensures zero-install execution in sandboxed AI environments, and minimizes binary size when packaged with PyInstaller for Tauri.

---

## 2. Process Security & OS Window Management
* **Context**: Subprocess execution must never allow shell injection and must not flash console windows on Windows when invoked from the Tauri GUI desktop application.
* **Decision**:
  - Always invoke `subprocess.Popen` / `subprocess.run` with `shell=False` and argument lists.
  - Convert all filesystem paths to absolute paths (`pathlib.Path.resolve()`).
  - On Windows, pass `creationflags = 0x08000000` (`subprocess.CREATE_NO_WINDOW`) to prevent console pop-ups.
  - Install signal handlers for `SIGINT` and `SIGTERM` to gracefully terminate any running child processes and clean up temp directories before exiting.

---

## 3. Two-Pass Compression Bitrate & Quality Safety Guardrails
* **Context**: When compressing to hard file size limits (e.g. Discord 20MB, WhatsApp 16MB, GitHub 25MB), single-pass CRF or naive bitrate allocation frequently overshoots or produces severe visual corruption.
* **Decision**:
  - Compute total target bits with a container-overhead safety margin: `effective_bytes = target_bytes * 0.95`.
  - Calculate video bitrate: `video_bitrate = (effective_bytes * 8 / duration) - audio_bitrate`.
  - Enforce Bits-Per-Pixel-Per-Frame (bppf) sanity checks: if `video_bitrate / (width * height * fps) < 0.04` or `video_bitrate < 48 kbps`, refuse to encode degraded garbage. Fail with a clear explanation and prompt the user to specify `--scale` (e.g., `720p`, `480p`, `360p`).
  - Perform true 2-pass libx264 encoding with `-passlogfile` stored in a dedicated temporary directory, writing pass 1 to the platform null sink (`NUL` on Windows, `/dev/null` on Unix), and pass 2 with `+faststart`.
  - Strictly verify the post-encode file size via `os.path.getsize(output)`. If `actual_bytes > target_bytes`, exit with code 4 (`VERIFICATION_ERROR`).

---

## 4. Silence Trimming with Filter Complex Scripts
* **Context**: Videos with many short pauses produce hundreds of keep segments. On Windows, command lines are capped at 8,191 characters, causing long filtergraphs to crash.
* **Decision**:
  - Use `silencedetect` filter output on stderr to identify silence start and end timestamps.
  - Invert silence into keep segments, applying a customizable `--pad` (default 0.1s) to prevent audio clipping.
  - Generate a segmented `trim` and `atrim` filter chain and write it to a temporary script file passed via `-filter_complex_script`.
  - Concat all segments with synchronized video and audio stream labels (`[0:v]trim=...[v0];[0:a]atrim=...[a0];...[v0][a0]...concat=n=N:v=1:a=1[v][a]`).
  - Provide clear exit code 5 (`STREAM_ERROR`) if the input contains no audio stream.

---

## 5. Cross-Platform Concat Demuxer Path Escaping
* **Context**: FFmpeg's concat demuxer (`-f concat -safe 0`) parses file paths with specific quoting and escape rules. Windows backslashes are interpreted as escape characters, leading to silent failures on paths with spaces or Unicode.
* **Decision**:
  - Convert all paths to POSIX representation with forward slashes (`/`).
  - Escape single quotes in filenames as `'\''`.
  - Before writing the concat file, probe all input media using `ffprobe` to verify codec, resolution, frame rate, and pixel format match. Fail with a granular explanation if mismatched unless `--reencode` is explicitly supplied.

---

## 6. Chained Audio Tempo for Wide Speed Ranges
* **Context**: FFmpeg's `atempo` filter only accepts values between 0.5 and 2.0.
* **Decision**: Implement a pure-logic chaining algorithm that decomposes any positive factor into chained `atempo` filters (e.g. 4x -> `atempo=2.0,atempo=2.0`; 0.25x -> `atempo=0.5,atempo=0.5`). Handle video speed with `setpts=(1/factor)*PTS`.

---

## 7. Standardized JSON Progress & Exit Codes
* **Context**: Both the Agensi AI agent and the Tauri desktop application require deterministic event streaming and exit codes.
* **Decision**:
  - Parse `ffmpeg -progress pipe:1` key=value pairs into typed JSON progress events (`start`, `progress`, `warning`, `done`, `error`).
  - For two-pass encoding, scale pass 1 to 0-50% and pass 2 to 50-100% so client applications observe monotonic progress.
  - Document and enforce standard exit codes:
    - `0`: Success
    - `1`: General Error / Runtime Exception
    - `2`: Command Syntax / Argument Error
    - `3`: Missing Dependency (`ffmpeg` / `ffprobe` not found)
    - `4`: Verification Error (output size exceeded target, overwrite refused)
    - `5`: Stream / Input Format Error (missing audio stream, corrupted container)
    - `6`: Aborted / Cancelled (`SIGINT` / `SIGTERM`)

---

## 8. Verified Platform Limits Data Architecture
* **Context**: Platform video upload limits change frequently across subscription tiers.
* **Decision**: Store limits in `engine/data/platform_limits.json` containing explicit source documentation URLs, verified dates, max byte limits, and recommended presets for Discord, WhatsApp, GitHub, X/Twitter, Gmail, and Slack.


---

## 9. Desktop Sidecar Architecture & Scoped Capabilities (Tauri v2)
* **Context**: The desktop app must execute the engine without requiring the end-user to install Python, while maintaining strict local security sandbox boundaries.
* **Decision**:
  - Package `video_toolkit.py` into a standalone PyInstaller binary per target OS (`video_toolkit-$TARGET_TRIPLE`).
  - Bundle pinned, checksum-verified FFmpeg and FFprobe binaries in `src-tauri/binaries/`.
  - Configure Tauri v2 capabilities (`desktop/src-tauri/capabilities/default.json`) with strictly scoped sidecar execution (`core:default`, `shell:allow-spawn`, `dialog:default`, `fs:default`).
  - Disallow arbitrary shell execution; only the bundled binaries can be executed.

---

## 10. Nuxt 3 Static Single-Page Application (SPA) with Zero Telemetry
* **Context**: The desktop app runs offline in a secure local desktop webview. It must load instantly without a Node.js server runtime, telemetry, or remote CDN requests.
* **Decision**:
  - Configure Nuxt 3 with `ssr: false` and `telemetry: false`.
  - Use `nitro.output.publicDir: '.output/public'` with `pnpm generate` to compile a zero-dependency static bundle (HTML, JS, CSS).
  - Enforce a strict Content Security Policy (CSP): `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: asset:; font-src 'self'; connect-src 'self'; media-src 'self' asset:;`.

---

## 11. Licensing Seam & Local Validation Architecture
* **Context**: The product will be sold commercially, requiring an activation interface for license keys without deploying an unmaintained or fragile remote activation server.
* **Decision**:
  - Implement a `LicenseValidator` trait in Rust with a `LocalNoOpLicenseValidator` implementation.
  - Define standard format checks (e.g. `FVT-PRO-*` or `AGY-*`) verifying key checksums locally while providing an asynchronous extension seam for future licensing providers.
  - Expose `verify_license_key` via Tauri invoke handler and provide a responsive settings view with status feedback.

---

## 12. In-App GPL v2+ Compliance & Source Code Offer
* **Context**: libx264 builds of FFmpeg are licensed under GPL v2+. Distributing compiled binaries requires GPL compliance.
* **Decision**:
  - Include an explicit "Licenses" screen in the desktop UI presenting the GPL v2+ notice and machine-readable source offer link (`https://github.com/FFmpeg/FFmpeg`).
  - Detail third-party component licenses (Tauri, Nuxt 3, Vue 3, Lucide) in `THIRD_PARTY_NOTICES.md` and make them accessible directly from the app interface.
