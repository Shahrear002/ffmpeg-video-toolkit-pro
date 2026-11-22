# FFmpeg Video Toolkit Pro — Developer Guide

This guide covers local environment setup, testing procedures, packaging runbooks, and contribution guidelines for **FFmpeg Video Toolkit Pro**.

---

## 1. Prerequisites

Ensure the following tools are installed on your host machine:

| Tool | Minimum Version | Installation / Verification |
|---|---|---|
| **Python** | 3.9+ | `python --version` (standard library only) |
| **Node.js** | 20.x+ LTS | `node --version` |
| **pnpm** | 12.x+ | `pnpm --version` |
| **Rust & Cargo** | 1.80+ (Stable) | `rustc --version` |
| **FFmpeg & FFprobe** | 6.0+ | `ffmpeg -version` (must support `libx264`, `libmp3lame`, `aac`) |
| **PyInstaller** | 6.0+ | `pip install pyinstaller` (for building the sidecar binary) |

---

## 2. Repository Layout

```text
ffmpeg-video-toolkit-pro/
  ├── engine/                       # Core Python engine
  │   ├── video_toolkit.py          # Single-file standard library engine
  │   ├── data/platform_limits.json # Verified platform file size limits
  │   └── tests/                    # Unit and integration test suites
  │       ├── test_pure_logic.py    # Offline mathematical & parsing tests
  │       └── test_integration.py  # Tests on synthetic media (lavfi)
  ├── skill/                        # Deliverable A: Agensi Agent Skill
  │   ├── SKILL.md                  # Specification-compliant skill definition
  │   ├── LICENSE                   # Commercial single-user license
  │   ├── README.md                 # Agent installation & recipe guide
  │   ├── scripts/video_toolkit.py  # Synced from engine at build time
  │   └── references/               # Technical references for agent context
  ├── desktop/                      # Deliverable B: Desktop Application
  │   ├── app.vue                   # Nuxt 3 single-page application
  │   ├── stores/queue.ts           # Reactive job queue manager
  │   ├── utils/                    # Command builder & progress parser
  │   ├── tests/                    # Vitest unit test suites
  │   └── src-tauri/                # Tauri v2 Rust core & sidecar bundle
  ├── scripts/                      # Build automation scripts
  │   ├── audit_self.py             # AST static security auditor
  │   ├── build_skill_zip.py        # Deterministic zip packager
  │   ├── build_engine_sidecar.py   # PyInstaller sidecar binary compiler
  │   └── fetch_ffmpeg.py           # Pinned FFmpeg/FFprobe binary stager
  ├── docs/                         # Technical documentation
  │   ├── ARCHITECTURE.md           # Architecture diagrams & event schemas
  │   ├── DECISIONS.md              # Architectural decision log
  │   ├── DEVELOPMENT.md            # This guide
  │   └── SECURITY.md               # Security policies & threat model
  └── .github/workflows/            # CI/CD automation
      ├── ci.yml                    # Multi-OS test matrix & lint
      └── release.yml               # Multi-platform binary release pipeline
```

---

## 3. Local Development & Testing

### 3.1 Running Engine Tests

The engine test suite contains two test classes:
1. `test_pure_logic.py`: 15 tests running offline without requiring FFmpeg (bitrate math, quality floor, silencedetect parsing, atempo chaining, concat escaping).
2. `test_integration.py`: 16 integration tests that generate synthetic media on-the-fly using FFmpeg's `lavfi` source (`testsrc`, `sine`, silence gaps, vertical video).

Run all engine tests:
```bash
python -m unittest discover -s engine/tests -v
```

### 3.2 Running the Skill Security Audit
Verify zero forbidden functions (`eval`, `exec`, `urllib`, `requests`, `socket`):
```bash
python scripts/audit_self.py
```

### 3.3 Running Frontend Unit Tests
Frontend unit tests in `desktop/tests/` test JSON progress streaming and queue state transitions:
```bash
cd desktop
pnpm install
pnpm test
```

### 3.4 Running Tauri Backend Unit Tests
Rust unit tests test sidecar argument construction and the licensing seam:
```bash
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

---

## 4. Building Deliverables

### 4.1 Packaging Deliverable A (Agensi Skill Zip)
Run the deterministic zip packager:
```bash
python scripts/build_skill_zip.py
```
This performs:
1. Syncing `engine/video_toolkit.py` to `skill/scripts/video_toolkit.py`.
2. Compiling `skill/references/platform-limits.md` from `engine/data/platform_limits.json`.
3. Running the AST security audit on all skill scripts.
4. Packaging into `dist/ffmpeg-video-toolkit-pro-skill-v1.0.0.zip` with normalized timestamps and SHA-256 checksums.

### 4.2 Building Deliverable B (Desktop Application)

1. **Stage FFmpeg Binaries**:
   ```bash
   python scripts/fetch_ffmpeg.py
   ```
2. **Build Engine Sidecar**:
   ```bash
   python scripts/build_engine_sidecar.py
   ```
3. **Compile Nuxt 3 Static Distribution**:
   ```bash
   cd desktop
   pnpm install
   pnpm generate
   ```
4. **Build Tauri Application**:
   ```bash
   cd desktop
   pnpm tauri build
   ```
   Installers will be generated in `desktop/src-tauri/target/release/bundle/`.

---

## 5. Coding Standards

- **No Placeholders or Stubs**: Shipped code must be complete, tested, and production-grade.
- **Python**: Standard library only. Typed annotations (`typing`), PEP 8 compliant, zero runtime pip dependencies.
- **TypeScript**: Strict mode enabled (`"strict": true` in `tsconfig.json`). No untyped `any` in public signatures.
- **Security**: Never interpolate shell commands. Subprocess calls must use list arguments with `shell=False`.
- **Architectural Decisions**: Record any substantial changes in `docs/DECISIONS.md`.
