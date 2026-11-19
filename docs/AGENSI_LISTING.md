# Agensi.io Commercial Marketplace Listing

## 1. Listing Title
**FFmpeg Video Toolkit Pro — Commercial Local Media Processing Engine for AI Agents**

---

## 2. Short Description (Tagline)
*Production-grade video compression, silence trimming, 9:16 Shorts reformatting, and media transformation for AI coding agents. 100% local, zero pip dependencies, guaranteed size compliance.*

---

## 3. Long Description
Transform your AI agents (Claude Code, Cursor, Codex CLI, OpenClaw, Gemini CLI) into expert video editors with **FFmpeg Video Toolkit Pro**.

Handling media in automated AI workflows is notoriously fragile: raw FFmpeg command lines easily crash on argument escaping, produce unwatchable degraded outputs, overshoot hard upload caps (like Discord's 20MB or WhatsApp's 16MB), or hang on subprocess pipe deadlocks. 

**FFmpeg Video Toolkit Pro** solves this by packaging an industrial-grade, deterministic Python engine that sits between your agent and FFmpeg. With verified platform presets, two-pass bitrate calculation with safety margins, filtergraph script generation for hundreds of silence cuts, and a structured JSON event stream, your agent will reliably deliver exact media results every single time.

### Why Agents Love It:
- **Zero Hallucinated Flags**: The agent runs simple, deterministic subcommands (`compress`, `trim-silence`, `shorts`, `merge`, `cut`, `gif`, `thumbs`).
- **Zero Pipeline Deadlocks**: Threaded stderr draining prevents OS pipe buffer hangs on large encodes.
- **Strict Size Verification**: Checks output file size post-encode and fails safely if limits are breached.
- **Safety First**: Zero network permissions, zero eval/exec, zero pip dependencies. Passes automated security audits by construction.

---

## 4. Key Feature Bullets
* **Smart Two-Pass Platform Compression**: Verified target limits for Discord (Free 20MB, Nitro Basic 50MB), WhatsApp (Media 16MB, Doc 2GB), GitHub (Web 25MB, Git 100MB), X/Twitter (512MB), and Slack. Includes Bits-Per-Pixel-Per-Frame (bppf) quality guardrails to eliminate macroblocking.
* **Intelligent Silence Trimming**: Detects audio pauses, inverts them to keep segments with configurable audio padding, and generates `-filter_complex_script` graphs to handle hundreds of segments without exceeding OS command-line limits.
* **Vertical 9:16 Shorts, Reels & TikTok Generator**: Re-formats any landscape video into vertical 1080x1920 with high-precision center cropping or blurred background fill. *Works seamlessly with [Subtitle Generator Pro](https://agensi.io/skills/subtitle-generator-pro) for auto-captioning.*
* **High-Precision Lossless & Frame-Accurate Cutting**: Fast input seeking with keyframe snapping for instant cuts, or `--precise` frame-accurate re-encoding.
* **Intelligent Stream-Verified Concat & Merging**: Probes codecs, resolutions, and sample rates before concatenating; fails safely with a granular diff or auto-normalizes with `--reencode`.
* **Two-Pass Animated GIF & WebP Engine**: Generates dynamic color palettes via `palettegen` and `paletteuse` for dithering without color banding.
* **Metadata & GPS Stripping**: Completely purges camera serial numbers, GPS coordinates, and private tags.
* **Progress Streaming & Diagnostics**: Emits standardized line-delimited JSON events (`start`, `progress`, `eta_s`, `done`, `error`) for agent and GUI integration.

---

## 5. Pricing Rationale
* **List Price**: **$49.00 USD (Single User / Perpetual License)**
* **Market Comparison**:
  - Competing commercial video SDKs and cloud APIs (Cloudinary, Mux, Shotstack) charge $0.05–$0.15 per minute of processed video, easily scaling past $100/month for active users.
  - Desktop GUI standalone video converters charge $39–$69 without programmatic agent automation or terminal tooling.
  - At $49 one-time, this tool pays for itself within the first few client projects or automated batch processing pipelines, with zero recurring API costs.

---

## 6. Screenshot & GIF Shot List
1. **Hero GIF**: Terminal view of Claude Code receiving "Compress this 4K screen recording for Discord", invoking `video_toolkit.py compress --preset discord`, and outputting a crisp 19.8MB MP4 with streaming progress bar.
2. **Silence Removal Visual**: Audio waveform before and after `trim-silence`, showing 45 seconds of dead air removed from a 5-minute podcast clip with smooth cross-padded boundaries.
3. **Shorts Reformatting Comparison**: Split screen showing original 16:9 landscape game stream converted into 9:16 vertical TikTok format with the blurred background fill mode.
4. **Platform Presets Infographic**: Clean visual table showcasing verified size caps and recommended downscaling presets for Discord, WhatsApp, GitHub, and Slack.
5. **JSON Progress Stream**: Developer visual showing real-time JSON events consumed by an automated agent pipeline.

---

## 7. Changelog Entry (v1.0.0)
```markdown
### [1.0.0] - 2026-11-19
- Initial commercial release on Agensi.io.
- Single-file Python engine (Python 3.9+ standard library only).
- Verified platform presets for Discord, WhatsApp, GitHub, X/Twitter, Gmail, and Slack.
- 11 production subcommands: compress, trim-silence, shorts, convert, extract-audio, cut, merge, gif, speed, strip-meta, thumbs.
- Full offline unit test suite and integration test suite with synthetic lavfi media generation.
- Automated security audit compliance: zero network calls, zero eval/exec, zero obfuscation.
```
