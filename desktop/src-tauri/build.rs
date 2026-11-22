use std::fs;
use std::path::Path;

fn main() {
    // Ensure icons directory exists
    let icons_dir = Path::new("icons");
    if !icons_dir.exists() {
        let _ = fs::create_dir_all(icons_dir);
    }

    // Ensure binaries directory exists and sidecar stubs exist for the current TARGET triple
    // so tauri_build::build() succeeds in CI/test environments before real binaries are staged.
    if let Ok(target) = std::env::var("TARGET") {
        let is_windows = target.contains("windows");
        let ext = if is_windows { ".exe" } else { "" };

        let binaries_dir = Path::new("binaries");
        if !binaries_dir.exists() {
            let _ = fs::create_dir_all(binaries_dir);
        }

        for bin_name in &["video_toolkit", "ffmpeg", "ffprobe"] {
            let filename = format!("{}-{}{}", bin_name, target, ext);
            let path = binaries_dir.join(&filename);
            if !path.exists() {
                let _ = fs::write(&path, b"");
            }
        }
    }

    tauri_build::build();
}
