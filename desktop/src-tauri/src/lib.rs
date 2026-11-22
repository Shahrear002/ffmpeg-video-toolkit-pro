use serde::{Deserialize, Serialize};

// ============================================================================
// Sidecar Argument Construction Subsystem
// ============================================================================

pub fn build_sidecar_args(
    subcommand: &str,
    input: &str,
    output: &str,
    extra_args: &[String],
    json_progress: bool,
    overwrite: bool,
) -> Vec<String> {
    let mut args = Vec::new();
    args.push(subcommand.to_string());
    if !input.is_empty() {
        args.push(input.to_string());
    }
    if !output.is_empty() {
        args.push(output.to_string());
    }
    if json_progress {
        args.push("--json-progress".to_string());
    }
    if overwrite {
        args.push("--overwrite".to_string());
    }
    for arg in extra_args {
        args.push(arg.clone());
    }
    args
}

// ============================================================================
// Licensing Seam Interface & Local No-Op Implementation
// ============================================================================

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct LicenseStatus {
    pub is_valid: bool,
    pub license_type: String,
    pub customer_email: Option<String>,
    pub expires_at: Option<String>,
    pub message: String,
}

pub trait LicenseValidator: Send + Sync {
    fn validate(&self, key: &str) -> LicenseStatus;
}

pub struct LocalNoOpLicenseValidator;

impl LicenseValidator for LocalNoOpLicenseValidator {
    fn validate(&self, key: &str) -> LicenseStatus {
        let clean = key.trim();
        if clean.is_empty() {
            LicenseStatus {
                is_valid: false,
                license_type: "Unlicensed".into(),
                customer_email: None,
                expires_at: None,
                message: "No license key entered".into(),
            }
        } else if clean.starts_with("FVT-PRO-") {
            LicenseStatus {
                is_valid: true,
                license_type: "Commercial Single-User".into(),
                customer_email: Some("licensed_buyer@agensi.io".into()),
                expires_at: None, // Perpetual
                message: "License key successfully activated".into(),
            }
        } else {
            LicenseStatus {
                is_valid: false,
                license_type: "Invalid".into(),
                customer_email: None,
                expires_at: None,
                message: "Invalid license key format (must begin with FVT-PRO-)".into(),
            }
        }
    }
}

// ============================================================================
// Tauri Commands Module
// ============================================================================

pub mod commands {
    use super::*;

    #[tauri::command]
    pub fn construct_command_preview(
        subcommand: String,
        input: String,
        output: String,
        extra_args: Vec<String>,
        json_progress: bool,
        overwrite: bool,
    ) -> Vec<String> {
        build_sidecar_args(&subcommand, &input, &output, &extra_args, json_progress, overwrite)
    }

    #[tauri::command]
    pub fn verify_license_key(key: String) -> LicenseStatus {
        let validator = LocalNoOpLicenseValidator;
        validator.validate(&key)
    }

    #[tauri::command]
    pub fn get_platform_info() -> serde_json::Value {
        serde_json::json!({
            "os": std::env::consts::OS,
            "arch": std::env::consts::ARCH,
            "family": std::env::consts::FAMILY,
        })
    }
}

// ============================================================================
// Tauri Application Runner
// ============================================================================

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![
            commands::construct_command_preview,
            commands::verify_license_key,
            commands::get_platform_info,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// ============================================================================
// Unit Tests (Sidecar Argument Construction & Licensing)
// ============================================================================

#[cfg(test)]
mod tests {
    use super::{build_sidecar_args, LicenseValidator, LocalNoOpLicenseValidator};

    #[test]
    fn test_build_sidecar_args_compress() {
        let extra = vec!["--preset".to_string(), "discord".to_string()];
        let args = build_sidecar_args("compress", "C:/video.mp4", "C:/out.mp4", &extra, true, true);
        assert_eq!(
            args,
            vec![
                "compress",
                "C:/video.mp4",
                "C:/out.mp4",
                "--json-progress",
                "--overwrite",
                "--preset",
                "discord"
            ]
        );
    }

    #[test]
    fn test_build_sidecar_args_check_flags() {
        let args = build_sidecar_args("--check", "", "", &[], true, false);
        assert_eq!(args, vec!["--check", "--json-progress"]);
    }

    #[test]
    fn test_license_validation_empty() {
        let validator = LocalNoOpLicenseValidator;
        let res = validator.validate("");
        assert!(!res.is_valid);
        assert_eq!(res.license_type, "Unlicensed");
    }

    #[test]
    fn test_license_validation_valid_prefix() {
        let validator = LocalNoOpLicenseValidator;
        let res = validator.validate("FVT-PRO-ABC123XYZ");
        assert!(res.is_valid);
        assert_eq!(res.license_type, "Commercial Single-User");
    }

    #[test]
    fn test_license_validation_invalid() {
        let validator = LocalNoOpLicenseValidator;
        let res = validator.validate("INVALID-KEY-12345");
        assert!(!res.is_valid);
        assert_eq!(res.license_type, "Invalid");
    }
}
