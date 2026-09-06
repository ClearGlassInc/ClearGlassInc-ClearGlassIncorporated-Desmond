use clearglass_agent_crypto::{
    SecureResult, decrypt_bytes, encrypt_bytes, generate_identity_pair, read_key_line,
    read_limited, write_new_file,
};
use std::collections::BTreeMap;
use std::env;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

const USAGE: &str = r#"ClearGlass Agent Army Secure Runtime

Usage:
  clearglass-secure keygen --identity <FILE> --recipient <FILE>
  clearglass-secure encrypt --recipient <FILE> --input <FILE|-> --output <FILE|->
  clearglass-secure decrypt --identity <FILE> --input <FILE|-> --output <FILE|->

Security behavior:
  * Existing output files are never overwritten.
  * Secret identity and decrypted output files use mode 0600 on Unix.
  * Plaintext is limited to 32 MiB and keys are limited to 16 KiB.
  * '-' reads stdin or writes stdout for pipeline operation.
"#;

fn invalid_input(message: impl Into<String>) -> Box<dyn std::error::Error + Send + Sync> {
    Box::new(io::Error::new(io::ErrorKind::InvalidInput, message.into()))
}

fn parse_options(args: &[String], allowed: &[&str]) -> SecureResult<BTreeMap<String, String>> {
    if args.len() % 2 != 0 {
        return Err(invalid_input("every option must have a value"));
    }

    let mut options = BTreeMap::new();
    for pair in args.chunks_exact(2) {
        let name = pair[0]
            .strip_prefix("--")
            .ok_or_else(|| invalid_input(format!("invalid option: {}", pair[0])))?;
        if !allowed.contains(&name) {
            return Err(invalid_input(format!("unsupported option: --{name}")));
        }
        if pair[1].is_empty() {
            return Err(invalid_input(format!("--{name} cannot be empty")));
        }
        if options.insert(name.to_owned(), pair[1].clone()).is_some() {
            return Err(invalid_input(format!("duplicate option: --{name}")));
        }
    }
    Ok(options)
}

fn required<'a>(options: &'a BTreeMap<String, String>, name: &str) -> SecureResult<&'a str> {
    options
        .get(name)
        .map(String::as_str)
        .ok_or_else(|| invalid_input(format!("missing required option: --{name}")))
}

fn read_source(source: &str) -> SecureResult<Vec<u8>> {
    if source == "-" {
        let stdin = io::stdin();
        read_limited(stdin.lock())
    } else {
        read_limited(File::open(source)?)
    }
}

fn write_destination(destination: &str, data: &[u8], private: bool) -> SecureResult<()> {
    if destination == "-" {
        let stdout = io::stdout();
        let mut handle = stdout.lock();
        handle.write_all(data)?;
        handle.flush()?;
        Ok(())
    } else {
        write_new_file(Path::new(destination), data, private)
    }
}

fn keygen(args: &[String]) -> SecureResult<()> {
    let options = parse_options(args, &["identity", "recipient"])?;
    let identity_path = PathBuf::from(required(&options, "identity")?);
    let recipient_path = PathBuf::from(required(&options, "recipient")?);

    if identity_path == Path::new("-") || recipient_path == Path::new("-") {
        return Err(invalid_input(
            "keygen requires file paths; '-' is not accepted",
        ));
    }
    if identity_path == recipient_path {
        return Err(invalid_input(
            "identity and recipient paths must be different",
        ));
    }
    if identity_path.exists() || recipient_path.exists() {
        return Err(invalid_input("refusing to overwrite an existing key file"));
    }

    let (identity, recipient) = generate_identity_pair();
    write_new_file(&recipient_path, format!("{recipient}\n").as_bytes(), false)?;
    if let Err(error) = write_new_file(&identity_path, format!("{identity}\n").as_bytes(), true) {
        let _ = fs::remove_file(&recipient_path);
        return Err(error);
    }

    eprintln!("generated recipient: {}", recipient_path.display());
    eprintln!("generated private identity: {}", identity_path.display());
    Ok(())
}

fn encrypt(args: &[String]) -> SecureResult<()> {
    let options = parse_options(args, &["recipient", "input", "output"])?;
    let recipient = read_key_line(Path::new(required(&options, "recipient")?))?;
    let plaintext = read_source(required(&options, "input")?)?;
    let ciphertext = encrypt_bytes(&recipient, &plaintext)?;
    write_destination(required(&options, "output")?, &ciphertext, false)
}

fn decrypt(args: &[String]) -> SecureResult<()> {
    let options = parse_options(args, &["identity", "input", "output"])?;
    let identity = read_key_line(Path::new(required(&options, "identity")?))?;
    let ciphertext = read_source(required(&options, "input")?)?;
    let plaintext = decrypt_bytes(&identity, &ciphertext)?;
    write_destination(required(&options, "output")?, &plaintext, true)
}

fn run() -> SecureResult<()> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() || matches!(args.first().map(String::as_str), Some("-h" | "--help")) {
        print!("{USAGE}");
        return Ok(());
    }

    let command = args.remove(0);
    match command.as_str() {
        "keygen" => keygen(&args),
        "encrypt" => encrypt(&args),
        "decrypt" => decrypt(&args),
        _ => Err(invalid_input(format!(
            "unknown command: {command}\n\n{USAGE}"
        ))),
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("clearglass-secure: {error}");
        std::process::exit(2);
    }
}
