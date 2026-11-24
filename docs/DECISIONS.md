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

---

## 13. Deterministic Cross-Platform CI/CD Package Management & Concurrency
* **Context**: GitHub Actions runners on macOS default to Apple Silicon arm64 (`macos-latest` / `macos-14`), where third-party setup actions (e.g., `FedericoCarboni/setup-ffmpeg` or `AnimMouse/setup-ffmpeg`) encounter architecture mismatches (`[ERR_FOOTPRINT] arm64 != x86_64`) or unauthenticated GitHub API rate limits. Additionally, truthy concurrency expressions caused premature shutdown of active matrix runners.
* **Decision**:
  - Install FFmpeg and FFprobe directly through native OS package managers on runners: Ubuntu `apt-get`, macOS `brew`, and Windows `choco`.
  - Set `cancel-in-progress: false` across CI workflows to guarantee complete execution without mid-run worker termination.
  - Optimize the engine matrix to cover Python 3.9-3.12 on Linux, Python 3.11 on Windows, and Python 3.11 on macOS arm64, conserving runner concurrency limits.
  - Automatically stub `frontendDist` (`../.output/public`) in `desktop/src-tauri/build.rs` to allow isolated backend test builds on fresh checkouts.

---

## 14. Argparse Option Normalization & Cross-Platform Sidecar Stubs
* **Context**: Python `argparse` across Python 3.9–3.11 parses option arguments starting with `-` (such as `--noise -30dB`) as unrecognized flags instead of values because the string contains non-numeric characters (`dB`). Additionally, Tauri's `externalBin` bundling requires valid target binary files (ELF on Linux, Mach-O on macOS, PE on Windows) with executable permissions (`0o755`) so `patchelf` and `lipo` do not fail during `cargo test`.
* **Decision**:
  - Normalize space-separated negative option arguments (e.g. `--noise -30dB` -> `--noise=-30dB`) in `engine/video_toolkit.py`'s `main()` before invoking `argparse.parse_args()`.
  - Compile real dummy seed executables using host `rustc` via a temporary source file in `desktop/src-tauri/build.rs` and apply `0o755` Unix executable permissions to all target sidecar stubs.
  - In `handle_gif`, enforce `-an` and `scale={width}:-2:flags=lanczos` to ensure even-dimension scaling and prevent audio stream muxing errors in WebP and GIF animations across platforms.

---

## 15. Tauri 4-Channel RGBA Icon Format & Dynamic Small-Target Compression Headroom
* **Context**:
  - In Tauri v2, `tauri::generate_context!()` compiles desktop window icons during `cargo test --lib` and panics with `proc macro panicked: icon .../icon.png is not RGBA` if PNGs are encoded in RGB (3-channel) format rather than true RGBA (4-channel).
  - On macOS Apple Silicon and Windows runners with newer FFmpeg versions, small target sizes (e.g. 80KB in `test_compress_three_different_inputs_and_targets`) exceeded target bytes by ~500 bytes when using a static 5% safety margin due to fixed MP4 container header (moov atom, faststart sample tables) overhead.
  - `libwebp` on macOS Apple Silicon requires explicit `yuv420p` pixel format to avoid unsupported color conversion failures.
* **Decision**:
  - Re-encode all 13 PNG icons in `desktop/src-tauri/icons/` to true 4-channel RGBA (8-bit depth, color type 6).
  - Implement dynamic container safety margin expansion in `calculate_two_pass_bitrate`: targets under 150 KB use a 12% margin, targets under 500 KB use 8%, and standard targets retain 5%.
  - Add `format=yuv420p` to the video filterchain for WebP animations in `handle_gif`.

---

## 16. Multi-Platform Animated WebP Encoder Detection & Capability Cascade
* **Context**:
  - FFmpeg installations vary significantly across distributions: Ubuntu 22.04 supplies FFmpeg 4.4, Ubuntu 24.04 provides FFmpeg 6.x, Windows Chocolatey provides FFmpeg 7.x, and Homebrew on macOS Apple Silicon provides minimal FFmpeg 9.x bottles built without `--enable-libwebp`.
  - Attempting to invoke `-c:v libwebp` or output `.webp` on an FFmpeg binary compiled without WebP support causes fatal `Encoder not found` errors (exit code 8).
* **Decision**:
  - In `FFmpegRunner`, provide dynamic cached capability detection via `has_encoder(name)`.
  - In `handle_gif`, verify availability of `libwebp` or `libwebp_anim` before encoding:
    - If neither encoder is compiled into the host FFmpeg binary, emit a structured error event and cleanly return `ExitCode.DEPENDENCY_ERROR` (code 5).
    - If supported, execute an ordered multi-strategy candidate cascade (`libwebp` / `libwebp_anim` with appropriate pixel format and muxer loop flags).
  - In integration test `test_gif_and_webp_generation`, assert `ExitCode.SUCCESS` when WebP encoders are present, and assert clean graceful `ExitCode.DEPENDENCY_ERROR` (code 5) when absent on minimal package-managed builds.

---

## 17. Multi-Architecture Desktop Release Matrix, WiX Icon Configuration & Conditional Code Signing
* **Context**:
  - In `desktop/src-tauri/tauri.conf.json`, omission of `bundle.icon` caused Windows WiX packaging (`.msi`) to fail with `failed to bundle project: Couldn't find a .ico icon`, despite `icons/icon.ico` existing in the filesystem.
  - In `.github/workflows/release.yml`, passing `APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}` unconditionally caused `tauri-action` to attempt `security import -f pkcs12` on empty strings when repository secrets were unconfigured, aborting with `SecKeychainItemImport: Unable to decode the provided data`.
  - The macOS release matrix only targeted `macos-arm64` (`aarch64-apple-darwin`), leaving Intel Mac users unable to execute the application.
* **Decision**:
  - Explicitly declare the icon array (`32x32.png`, `128x128.png`, `128x128@2x.png`, `icon.ico`, `icon.icns`) under `bundle.icon` in `desktop/src-tauri/tauri.conf.json` and generate `desktop/src-tauri/icons/icon.icns`.
  - Conditionally export Apple code signing environment variables only when `secrets.APPLE_CERTIFICATE` is non-empty. When unconfigured, `tauri-action` builds clean, unsigned native DMG packages without keychain import errors.
  - Expand the release matrix to build native installers for all major desktop architectures:
    - `windows-x64` (`x86_64-pc-windows-msvc` on `windows-latest`)
    - `macos-universal` (`universal-apple-darwin` on `macos-latest` producing a single Universal DMG that natively supports both Apple Silicon M1/M2/M3/M4 and Intel Macs)
    - `linux-x64` (`x86_64-unknown-linux-gnu` on `ubuntu-22.04`)



