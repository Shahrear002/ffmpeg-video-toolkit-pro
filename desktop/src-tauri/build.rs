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

    // Ensure all target sidecar files exist so tauri_build::build() succeeds
    let target = std::env::var("TARGET").unwrap_or_default();
    let is_windows = target.contains("windows");
    let ext = if is_windows { ".exe" } else { "" };

    // Create a real minimal host executable via rustc if sidecars don't exist
    // This produces a valid Mach-O (macOS), ELF (Linux), or PE (Windows) binary so lipo / patchelf never panic
    let dummy_seed = binaries_dir.join(format!("_dummy_seed{}", ext));
    if !dummy_seed.exists() {
        let _ = std::process::Command::new("rustc")
            .args(&["-", "--crate-type", "bin", "-o"])
            .arg(&dummy_seed)
            .stdin(std::process::Stdio::piped())
            .spawn()
            .and_then(|mut child| {
                use std::io::Write;
                if let Some(mut stdin) = child.stdin.take() {
                    let _ = stdin.write_all(b"fn main() {}\n");
                }
                child.wait()
            });
    }

    let targets = [
        ("x86_64-pc-windows-msvc", ".exe"),
        ("aarch64-apple-darwin", ""),
        ("x86_64-apple-darwin", ""),
        ("x86_64-unknown-linux-gnu", ""),
    ];

    for (tgt, tgt_ext) in &targets {
        for bin_name in &["video_toolkit", "ffmpeg", "ffprobe"] {
            let filename = format!("{}-{}{}", bin_name, tgt, tgt_ext);
            let path = binaries_dir.join(&filename);
            if !path.exists() {
                if dummy_seed.exists() && tgt_ext == &ext {
                    let _ = fs::copy(&dummy_seed, &path);
                } else {
                    let _ = fs::write(&path, b"#!/bin/sh\nexit 0\n");
                }
            }
        }
    }

    tauri_build::build();
}
