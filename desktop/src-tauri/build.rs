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
        let temp_src = binaries_dir.join("_dummy_seed.rs");
        let _ = fs::write(&temp_src, b"fn main() {}\n");
        let _ = std::process::Command::new("rustc")
            .arg(&temp_src)
            .args(&["--crate-type", "bin", "-o"])
            .arg(&dummy_seed)
            .status();
        let _ = fs::remove_file(&temp_src);
    }

    #[cfg(unix)]
    if dummy_seed.exists() {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = fs::metadata(&dummy_seed) {
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = fs::set_permissions(&dummy_seed, perms);
        }
    }

    // Remove any leftover sidecars that don't match the active target to prevent Tauri from attempting universal lipo or cross-architecture packaging
    if let Ok(entries) = fs::read_dir(binaries_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            if (name.starts_with("video_toolkit-") || name.starts_with("ffmpeg-") || name.starts_with("ffprobe-"))
                && !name.contains(&target)
            {
                let _ = fs::remove_file(entry.path());
            }
        }
    }

    // Tauri externalBin only needs stubs for the active target architecture.
    for bin_name in &["video_toolkit", "ffmpeg", "ffprobe"] {
        let filename = format!("{}-{}{}", bin_name, target, ext);
        let path = binaries_dir.join(&filename);
        if !path.exists() || path.metadata().map(|m| m.len()).unwrap_or(0) < 100 {
            if dummy_seed.exists() {
                let _ = fs::copy(&dummy_seed, &path);
            } else {
                let _ = fs::write(&path, b"#!/bin/sh\nexit 0\n");
            }
        }
        #[cfg(unix)]
        if path.exists() {
            use std::os::unix::fs::PermissionsExt;
            if let Ok(meta) = fs::metadata(&path) {
                let mut perms = meta.permissions();
                perms.set_mode(0o755);
                let _ = fs::set_permissions(&path, perms);
            }
        }
    }

    tauri_build::build();
}
