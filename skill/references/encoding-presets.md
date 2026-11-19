# Encoding Presets & Best Practices Reference Guide

This reference documents encoding standards, bitrate math, rate control methods, and compatibility rules implemented across FFmpeg Video Toolkit Pro.

---

## 1. Rate Control: Two-Pass Bitrate vs. Constant Rate Factor (CRF)

| Method | Target Use Case | Advantages | Disadvantages |
| :--- | :--- | :--- | :--- |
| **Two-Pass Bitrate** | Hard file size caps (Discord, WhatsApp, Email, GitHub) | **Guarantees exact byte output** under the target cap | Slower encoding (requires two complete passes) |
| **CRF (Constant Rate Factor)** | Quality-based archival, personal playback | Consistent visual fidelity; faster single-pass encode | Output file size is unpredictable |

### Two-Pass Bitrate Calculation Formula
To ensure output files fit within upload thresholds, FFmpeg Video Toolkit Pro uses the following algorithm:

$$\text{Effective Target} = \text{Target Bytes} \times (1.0 - \text{Safety Margin})$$
$$\text{Total Bitrate} = \frac{\text{Effective Target} \times 8}{\text{Duration Seconds}}$$
$$\text{Video Bitrate} = \text{Total Bitrate} - \text{Audio Bitrate}$$

* **Safety Margin**: Default $5\%$ ($0.05$). This accommodates MP4 container muxing overhead (moov, mvhd, trak atoms).
* **Pass 1**: Writes stats to `-passlogfile` and sends video frames to the platform null sink (`NUL` on Windows, `/dev/null` on Unix). Audio is disabled (`-an`).
* **Pass 2**: Reads the pass log and encodes the final media with `-movflags +faststart`.

---

## 2. Visual Quality Guardrails: Bits-Per-Pixel-Per-Frame (bppf)

When compressing long or high-resolution videos into small file envelopes, setting a naive low bitrate results in severe macroblocking, color banding, and unwatchable video.

The engine calculates the **bppf** ratio before starting the encode:

$$\text{bppf} = \frac{\text{Video Bitrate (bps)}}{\text{Width} \times \text{Height} \times \text{FPS}}$$

* **$\text{bppf} \ge 0.10$**: Excellent visual fidelity.
* **$0.06 \le \text{bppf} < 0.10$**: Good web distribution quality.
* **$0.04 \le \text{bppf} < 0.06$**: Acceptable for low-motion / talking-head content.
* **$\text{bppf} < 0.04$**: **Quality Failure Threshold**. The engine rejects the encode with a recommendation to downscale (e.g. `--scale 720p` or `--scale 480p`).

### Resolution Downscaling Recommendations
If input resolution produces $\text{bppf} < 0.04$:
- For 1080p ($1920 \times 1080$): Downscale to **720p** ($1280 \times 720$), cutting pixel count by $55\%$.
- For 720p ($1280 \times 720$): Downscale to **480p** ($854 \times 480$), cutting pixel count by another $55\%$.
- For 480p: Downscale to **360p** ($640 \times 360$).

---

## 3. Pixel Format Compatibility: The `yuv420p` Rule

By default, modern FFmpeg builds with synthetic sources or RGB assets will encode using `yuv444p` or high bit-depth profiles.
* **Problem**: QuickTime Player, iOS Safari, Android hardware decoders, and Chrome mobile do **not** support `yuv444p` H.264 video.
* **Rule**: FFmpeg Video Toolkit Pro **strictly enforces `-pix_fmt yuv420p`** across all standard MP4 exports to guarantee 100% universal hardware playback.

---

## 4. Container Optimization: `+faststart`

Standard MP4 muxers append the index atom (`moov`) to the end of the file. Web browsers and mobile clients must download the entire video before playback can begin.

The engine automatically passes:
`-movflags +faststart`
This relocates the `moov` atom to the beginning of the file, enabling immediate streaming and progressive playback in browsers, Discord, and Slack without buffering delays.

---

## 5. Audio Codecs & Bitrate Selection

| Format | Codec | Recommended Settings | Notes |
| :--- | :--- | :--- | :--- |
| **MP4 Video Audio** | `aac` | `128k` (or `64k`-`96k` for tight limits) | Native browser and platform compatibility |
| **MP3 Extraction** | `libmp3lame` | `192k` CBR or `-q:a 2` VBR | Standard for podcasting and universal audio |
| **Lossless Master** | `flac` | `flac` native | Compression without generational loss |
| **Raw Studio Wave** | `pcm_s16le` | 16-bit 44.1/48kHz PCM | Uncompressed audio for DAW import |
