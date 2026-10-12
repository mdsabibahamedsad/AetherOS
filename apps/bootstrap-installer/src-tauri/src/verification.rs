use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub file: String,
    pub passed: bool,
    pub algorithm: String,
    pub expected_hash: Option<String>,
    pub actual_hash: Option<String>,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignatureResult {
    pub file: String,
    pub signed: bool,
    pub trusted: bool,
    pub message: String,
}

pub fn compute_sha256(path: &Path) -> Result<String, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("Failed to read {}: {e}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

#[tauri::command]
pub async fn verify_file_checksum(
    file_path: String,
    expected_hash: String,
    algorithm: Option<String>,
) -> Result<VerificationResult, String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Ok(VerificationResult {
            file: file_path,
            passed: false,
            algorithm: algorithm.clone().unwrap_or_else(|| "sha256".to_string()),
            expected_hash: Some(expected_hash),
            actual_hash: None,
            message: "File does not exist".to_string(),
        });
    }

    match compute_sha256(path) {
        Ok(actual_hash) => {
            let passed = actual_hash.eq_ignore_ascii_case(&expected_hash);
            let message = if passed {
                "Checksum verified".to_string()
            } else {
                format!("Checksum mismatch (expected {expected_hash}, got {actual_hash})")
            };
            Ok(VerificationResult {
                file: file_path,
                passed,
                algorithm: "sha256".to_string(),
                expected_hash: Some(expected_hash),
                actual_hash: Some(actual_hash),
                message,
            })
        }
        Err(e) => Ok(VerificationResult {
            file: file_path,
            passed: false,
            algorithm: "sha256".to_string(),
            expected_hash: Some(expected_hash),
            actual_hash: None,
            message: e,
        }),
    }
}

#[tauri::command]
pub async fn verify_file_signature(file_path: String) -> Result<SignatureResult, String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Ok(SignatureResult {
            file: file_path,
            signed: false,
            trusted: false,
            message: "File does not exist".to_string(),
        });
    }

    #[cfg(target_os = "windows")]
    {
        let result = std::process::Command::new("powershell.exe")
            .args([
                "-NoProfile",
                "-Command",
                &format!(
                    "Get-AuthenticodeSignature '{}' | Select-Object -ExpandProperty Status",
                    file_path
                ),
            ])
            .output();

        match result {
            Ok(output) => {
                let status = String::from_utf8_lossy(&output.stdout).trim().to_string();
                let signed = !status.is_empty() && status != "NotSigned";
                return Ok(SignatureResult {
                    file: file_path,
                    signed,
                    trusted: status == "Valid",
                    message: if status == "Valid" {
                        "Digital signature verified".to_string()
                    } else if signed {
                        format!("File is signed but status: {status}")
                    } else {
                        "File is not digitally signed".to_string()
                    },
                });
            }
            Err(e) => {
                return Ok(SignatureResult {
                    file: file_path,
                    signed: false,
                    trusted: false,
                    message: format!("Could not verify signature: {e}"),
                });
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let result = std::process::Command::new("codesign")
            .args(["--verify", &file_path])
            .output();

        match result {
            Ok(output) => {
                let valid = output.status.success();
                Ok(SignatureResult {
                    file: file_path,
                    signed: true,
                    trusted: valid,
                    message: if valid {
                        "Code signature verified".to_string()
                    } else {
                        String::from_utf8_lossy(&output.stderr).trim().to_string()
                    },
                })
            }
            Err(_) => Ok(SignatureResult {
                file: file_path,
                signed: false,
                trusted: false,
                message: "Signature verification not available on this platform".to_string(),
            }),
        }
    }
}
