//! Memory-safe encryption primitives for ClearGlass agent-army artifacts.
//!
//! The runtime uses the interoperable `age` file format with X25519 recipients.
//! Ciphertexts are authenticated: corrupted or modified data fails decryption.

use age::secrecy::ExposeSecret;
use age::x25519;
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process;

/// Maximum plaintext artifact size accepted by the in-memory CLI path.
pub const MAX_ARTIFACT_BYTES: usize = 32 * 1024 * 1024;
/// Maximum ciphertext stream size, including age format overhead.
pub const MAX_CIPHERTEXT_BYTES: usize = MAX_ARTIFACT_BYTES + 1024 * 1024;
/// Maximum identity or recipient file size.
pub const MAX_KEY_FILE_BYTES: usize = 16 * 1024;

/// Error type returned by the secure runtime.
pub type SecureResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

#[derive(Debug)]
struct SecureRuntimeError(String);

impl Display for SecureRuntimeError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl Error for SecureRuntimeError {}

fn runtime_error(message: impl Into<String>) -> Box<dyn Error + Send + Sync> {
    Box::new(SecureRuntimeError(message.into()))
}

/// Generates an X25519 age identity and its public recipient.
///
/// The first returned string is secret and must never be committed.
pub fn generate_identity_pair() -> (String, String) {
    let identity = x25519::Identity::generate();
    let secret = identity.to_string();
    (
        secret.expose_secret().to_owned(),
        identity.to_public().to_string(),
    )
}

/// Encrypts bytes to an X25519 age recipient.
pub fn encrypt_bytes(recipient: &str, plaintext: &[u8]) -> SecureResult<Vec<u8>> {
    if plaintext.len() > MAX_ARTIFACT_BYTES {
        return Err(runtime_error(format!(
            "artifact exceeds {}-byte limit",
            MAX_ARTIFACT_BYTES
        )));
    }

    let recipient: x25519::Recipient = recipient.trim().parse()?;
    Ok(age::encrypt(&recipient, plaintext)?)
}

/// Decrypts an age ciphertext using an X25519 identity.
pub fn decrypt_bytes(identity: &str, ciphertext: &[u8]) -> SecureResult<Vec<u8>> {
    if ciphertext.len() > MAX_CIPHERTEXT_BYTES {
        return Err(runtime_error(format!(
            "ciphertext exceeds {}-byte limit",
            MAX_CIPHERTEXT_BYTES
        )));
    }

    let identity: x25519::Identity = identity.trim().parse()?;
    let plaintext = age::decrypt(&identity, ciphertext)?;
    if plaintext.len() > MAX_ARTIFACT_BYTES {
        return Err(runtime_error(format!(
            "decrypted artifact exceeds {}-byte limit",
            MAX_ARTIFACT_BYTES
        )));
    }
    Ok(plaintext)
}

/// Reads at most [`MAX_CIPHERTEXT_BYTES`] from a stream.
pub fn read_limited<R: Read>(reader: R) -> SecureResult<Vec<u8>> {
    let mut data = Vec::new();
    let mut limited = reader.take((MAX_CIPHERTEXT_BYTES + 1) as u64);
    limited.read_to_end(&mut data)?;
    if data.len() > MAX_CIPHERTEXT_BYTES {
        return Err(runtime_error(format!(
            "input exceeds {}-byte limit",
            MAX_CIPHERTEXT_BYTES
        )));
    }
    Ok(data)
}

/// Reads the first non-empty, non-comment key line from a small UTF-8 file.
pub fn read_key_line(path: &Path) -> SecureResult<String> {
    let metadata = fs::metadata(path)?;
    if metadata.len() > MAX_KEY_FILE_BYTES as u64 {
        return Err(runtime_error(format!(
            "key file {} exceeds {}-byte limit",
            path.display(),
            MAX_KEY_FILE_BYTES
        )));
    }

    let content = fs::read_to_string(path)?;
    content
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty() && !line.starts_with('#'))
        .map(str::to_owned)
        .ok_or_else(|| runtime_error(format!("no key found in {}", path.display())))
}

fn parent_directory(path: &Path) -> &Path {
    match path.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => parent,
        _ => Path::new("."),
    }
}

fn temporary_path(path: &Path, attempt: u32) -> SecureResult<PathBuf> {
    let file_name = path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| runtime_error("output path must contain a valid UTF-8 file name"))?;
    Ok(parent_directory(path).join(format!(".{file_name}.{}.{}.tmp", process::id(), attempt)))
}

/// Writes a new file without overwriting an existing path.
///
/// Data is written and synced to a temporary file, then linked into place. On Unix,
/// private files are created with mode `0600`; public files use mode `0644` subject
/// to the process umask.
pub fn write_new_file(path: &Path, data: &[u8], private: bool) -> SecureResult<()> {
    if path.as_os_str().is_empty() {
        return Err(runtime_error("output path cannot be empty"));
    }
    if path.exists() {
        return Err(runtime_error(format!(
            "refusing to overwrite existing file: {}",
            path.display()
        )));
    }

    fs::create_dir_all(parent_directory(path))?;

    for attempt in 0..128 {
        let temporary = temporary_path(path, attempt)?;
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);

        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(if private { 0o600 } else { 0o644 });
        }

        let mut file = match options.open(&temporary) {
            Ok(file) => file,
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(Box::new(error)),
        };

        if let Err(error) = file.write_all(data).and_then(|_| file.sync_all()) {
            drop(file);
            let _ = fs::remove_file(&temporary);
            return Err(Box::new(error));
        }
        drop(file);

        if let Err(error) = fs::hard_link(&temporary, path) {
            let _ = fs::remove_file(&temporary);
            return Err(Box::new(error));
        }
        if let Err(error) = fs::remove_file(&temporary) {
            return Err(Box::new(error));
        }
        return Ok(());
    }

    Err(runtime_error(
        "unable to allocate a collision-free temporary file",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_identity_round_trips() {
        let (identity, recipient) = generate_identity_pair();
        let plaintext = br#"{"plan_id":"abc123","classification":"confidential"}"#;

        let ciphertext = encrypt_bytes(&recipient, plaintext).expect("encrypt");
        assert_ne!(ciphertext, plaintext);

        let decrypted = decrypt_bytes(&identity, &ciphertext).expect("decrypt");
        assert_eq!(decrypted, plaintext);
    }

    #[test]
    fn wrong_identity_is_rejected() {
        let (_, recipient) = generate_identity_pair();
        let (wrong_identity, _) = generate_identity_pair();
        let ciphertext = encrypt_bytes(&recipient, b"restricted").expect("encrypt");

        assert!(decrypt_bytes(&wrong_identity, &ciphertext).is_err());
    }

    #[test]
    fn modified_ciphertext_is_rejected() {
        let (identity, recipient) = generate_identity_pair();
        let mut ciphertext = encrypt_bytes(&recipient, b"integrity protected").expect("encrypt");
        let index = ciphertext.len() - 1;
        ciphertext[index] ^= 0x01;

        assert!(decrypt_bytes(&identity, &ciphertext).is_err());
    }

    #[test]
    fn generated_keys_use_age_formats() {
        let (identity, recipient) = generate_identity_pair();
        assert!(identity.starts_with("AGE-SECRET-KEY-"));
        assert!(recipient.starts_with("age1"));
    }

    #[test]
    fn oversized_plaintext_fails_closed() {
        let (_, recipient) = generate_identity_pair();
        let oversized = vec![0_u8; MAX_ARTIFACT_BYTES + 1];
        assert!(encrypt_bytes(&recipient, &oversized).is_err());
    }
}
