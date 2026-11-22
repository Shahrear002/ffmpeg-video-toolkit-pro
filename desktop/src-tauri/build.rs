use std::fs;
use std::path::Path;

fn main() {
    let icons_dir = Path::new("icons");
    if !icons_dir.exists() {
        let _ = fs::create_dir_all(icons_dir);
    }

    let binaries_dir = Path::new("binaries");
    if !binaries_dir.exists() {
        let _ = fs::create_dir_all(binaries_dir);
    }

    // Ensure frontendDist stub exists so compile/test passes before pnpm generate
    let frontend_dist = Path::new("../.output/public");
    if !frontend_dist.exists() {
        let _ = fs::create_dir_all(frontend_dist);
        let index_html = frontend_dist.join("index.html");
        if !index_html.exists() {
            let _ = fs::write(&index_html, b"<!DOCTYPE html><html><body><h1>FFmpeg Video Toolkit Pro</h1></body></html>");
        }
    }

    // Ensure all possible target sidecar files exist with dummy content
    // so tauri_build::build() succeeds across Linux, macOS (arm64 + x64), and Windows
    let targets = [
        ("x86_64-pc-windows-msvc", ".exe"),
        ("aarch64-apple-darwin", ""),
        ("x86_64-apple-darwin", ""),
        ("x86_64-unknown-linux-gnu", ""),
    ];

    for (target, ext) in &targets {
        for bin_name in &["video_toolkit", "ffmpeg", "ffprobe"] {
            let filename = format!("{}-{}{}", bin_name, target, ext);
            let path = binaries_dir.join(&filename);
            if !path.exists() {
                let _ = fs::write(&path, b"#!/bin/sh\nexit 0\n");
            }
        }
    }

    tauri_build::build();
}
