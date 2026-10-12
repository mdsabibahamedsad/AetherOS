use aes_gcm::aead::{Aead, KeyInit, OsRng};
use aes_gcm::{Aes256Gcm, Nonce};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const KEY_FILE: &str = ".machine-key";
const NONCE_SIZE: usize = 12;

fn machine_key_path() -> PathBuf {
    crate::paths::aetheros_home().join("config").join(KEY_FILE)
}

fn derive_key(machine_id: &str) -> [u8; 32] {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(b"aetheros-v1-secret-key-");
    hasher.update(machine_id.as_bytes());
    let result = hasher.finalize();
    let mut key = [0u8; 32];
    key.copy_from_slice(&result);
    key
}

fn get_or_create_machine_key() -> Result<[u8; 32], String> {
    let path = machine_key_path();
    if path.exists() {
        let content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Cannot read machine key: {e}"))?;
        let mut key = [0u8; 32];
        let decoded = base64::Engine::decode(
            &base64::engine::general_purpose::STANDARD,
            content.trim(),
        )
        .map_err(|e| format!("Cannot decode machine key: {e}"))?;
        if decoded.len() != 32 {
            return Err("Invalid machine key length".to_string());
        }
        key.copy_from_slice(&decoded);
        Ok(key)
    } else {
        let mut key = [0u8; 32];
        OsRng.fill_bytes(&mut key);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Cannot create config dir: {e}"))?;
        }
        let encoded = base64::Engine::encode(
            &base64::engine::general_purpose::STANDARD,
            key,
        );
        std::fs::write(&path, &encoded)
            .map_err(|e| format!("Cannot write machine key: {e}"))?;
        Ok(key)
    }
}

pub fn encrypt(plaintext: &str) -> Result<String, String> {
    let key = get_or_create_machine_key()?;
    let cipher = Aes256Gcm::new_from_slice(&key)
        .map_err(|e| format!("Cipher init failed: {e}"))?;

    let mut nonce_bytes = [0u8; NONCE_SIZE];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext = cipher
        .encrypt(nonce, plaintext.as_bytes())
        .map_err(|e| format!("Encryption failed: {e}"))?;

    let mut combined = Vec::with_capacity(NONCE_SIZE + ciphertext.len());
    combined.extend_from_slice(&nonce_bytes);
    combined.extend_from_slice(&ciphertext);

    Ok(base64::Engine::encode(
        &base64::engine::general_purpose::STANDARD,
        &combined,
    ))
}

pub fn decrypt(encoded: &str) -> Result<String, String> {
    let key = get_or_create_machine_key()?;
    let cipher = Aes256Gcm::new_from_slice(&key)
        .map_err(|e| format!("Cipher init failed: {e}"))?;

    let combined = base64::Engine::decode(
        &base64::engine::general_purpose::STANDARD,
        encoded,
    )
    .map_err(|e| format!("Base64 decode failed: {e}"))?;

    if combined.len() < NONCE_SIZE {
        return Err("Encrypted data too short".to_string());
    }

    let (nonce_bytes, ciphertext) = combined.split_at(NONCE_SIZE);
    let nonce = Nonce::from_slice(nonce_bytes);

    let plaintext = cipher
        .decrypt(nonce, ciphertext)
        .map_err(|e| format!("Decryption failed: {e}"))?;

    String::from_utf8(plaintext).map_err(|e| format!("UTF-8 error: {e}"))
}

pub fn encrypt_json<T: serde::Serialize>(value: &T) -> Result<String, String> {
    let json = serde_json::to_string(value).map_err(|e| format!("Serialize error: {e}"))?;
    encrypt(&json)
}

pub fn decrypt_json<T: serde::de::DeserializeOwned>(encoded: &str) -> Result<T, String> {
    let json = decrypt(encoded)?;
    serde_json::from_str(&json).map_err(|e| format!("Deserialize error: {e}"))
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedSecret {
    pub key: String,
    pub encrypted_value: String,
}

pub fn store_secret(key: &str, value: &str) -> Result<(), String> {
    let secrets_path = crate::paths::aetheros_home().join("config").join("secrets.json");
    let mut secrets: Vec<EncryptedSecret> = if secrets_path.exists() {
        let content = std::fs::read_to_string(&secrets_path).unwrap_or_default();
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        Vec::new()
    };

    let encrypted = encrypt(value)?;
    if let Some(existing) = secrets.iter_mut().find(|s| s.key == key) {
        existing.encrypted_value = encrypted;
    } else {
        secrets.push(EncryptedSecret {
            key: key.to_string(),
            encrypted_value: encrypted,
        });
    }

    if let Some(parent) = secrets_path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let content = serde_json::to_string_pretty(&secrets).map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&secrets_path, content).map_err(|e| format!("Write error: {e}"))?;
    Ok(())
}

pub fn read_secret(key: &str) -> Result<Option<String>, String> {
    let secrets_path = crate::paths::aetheros_home().join("config").join("secrets.json");
    if !secrets_path.exists() {
        return Ok(None);
    }
    let content = std::fs::read_to_string(&secrets_path).map_err(|e| format!("Read error: {e}"))?;
    let secrets: Vec<EncryptedSecret> = serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))?;
    if let Some(s) = secrets.iter().find(|s| s.key == key) {
        let value = decrypt(&s.encrypted_value)?;
        Ok(Some(value))
    } else {
        Ok(None)
    }
}

pub fn delete_secret(key: &str) -> Result<(), String> {
    let secrets_path = crate::paths::aetheros_home().join("config").join("secrets.json");
    if !secrets_path.exists() {
        return Ok(());
    }
    let content = std::fs::read_to_string(&secrets_path).map_err(|e| format!("Read error: {e}"))?;
    let mut secrets: Vec<EncryptedSecret> = serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))?;
    secrets.retain(|s| s.key != key);
    let content = serde_json::to_string_pretty(&secrets).map_err(|e| format!("Serialize error: {e}"))?;
    std::fs::write(&secrets_path, content).map_err(|e| format!("Write error: {e}"))?;
    Ok(())
}

pub fn list_secret_keys() -> Result<Vec<String>, String> {
    let secrets_path = crate::paths::aetheros_home().join("config").join("secrets.json");
    if !secrets_path.exists() {
        return Ok(Vec::new());
    }
    let content = std::fs::read_to_string(&secrets_path).map_err(|e| format!("Read error: {e}"))?;
    let secrets: Vec<EncryptedSecret> = serde_json::from_str(&content).map_err(|e| format!("Parse error: {e}"))?;
    Ok(secrets.into_iter().map(|s| s.key).collect())
}
