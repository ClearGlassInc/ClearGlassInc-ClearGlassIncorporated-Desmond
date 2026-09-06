# ClearGlass Agent Army Secure Runtime

A memory-safe Rust sidecar for encrypting agent-army plans, briefs, evidence, and customer-sensitive artifacts without placing plaintext secrets in the repository.

## Cryptographic design

- **Format:** interoperable `age` v1 files
- **Recipient model:** X25519 public-key encryption
- **Confidentiality and integrity:** authenticated encryption; modified ciphertext fails closed
- **Key separation:** public recipient files may be distributed; private identity files must remain outside Git and backups must be access-controlled
- **Secret memory handling:** identity serialization uses the `secrecy` interface exposed by `age`
- **Output safety:** existing files are never overwritten; writes are synced before being linked into place
- **Resource limits:** artifacts are capped at 32 MiB and key files at 16 KiB

This runtime does not invent a proprietary cipher or protocol. It uses the documented `age` format so encrypted files remain compatible with established `age`/`rage` tooling.

## Build

```powershell
cd agent_army/secure_runtime
cargo build --release --locked
```

Binary:

```text
target/release/clearglass-secure
```

On Windows the executable is `clearglass-secure.exe`.

## Generate a key pair

```powershell
./target/release/clearglass-secure keygen `
  --identity "$HOME/.clearglass/agent-army.identity" `
  --recipient "./agent-army.recipient"
```

The identity is private. Do not commit it, paste it into issues, expose it in logs, or place it in workflow YAML. The recipient is public and can be used by CI or other authorized operators to encrypt artifacts.

On Unix, the runtime creates identity files with mode `0600`. On Windows, store the identity inside a directory protected by NTFS ACLs and BitLocker or equivalent full-disk encryption.

## Encrypt an existing plan

```powershell
./target/release/clearglass-secure encrypt `
  --recipient ./agent-army.recipient `
  --input ./out/plan.json `
  --output ./out/plan.json.age
```

## Generate and encrypt without plaintext at rest

```powershell
python -m agent_army.orchestrator `
  --request "Build and market the secure workflow product" `
  --format json |
  ./agent_army/secure_runtime/target/release/clearglass-secure encrypt `
    --recipient ./agent-army.recipient `
    --input - `
    --output ./out/plan.json.age
```

## Decrypt

```powershell
./target/release/clearglass-secure decrypt `
  --identity "$HOME/.clearglass/agent-army.identity" `
  --input ./out/plan.json.age `
  --output ./out/plan.json
```

Decrypted file output is created with mode `0600` on Unix. Delete plaintext when it is no longer required.

## Pipeline mode

`-` means standard input or standard output:

```bash
cat plan.json | clearglass-secure encrypt \
  --recipient agent-army.recipient --input - --output plan.json.age

clearglass-secure decrypt \
  --identity ~/.clearglass/agent-army.identity \
  --input plan.json.age --output - | jq .
```

## Operational controls

1. Keep private identities out of Git, Actions logs, screenshots, tickets, and shared chat.
2. Rotate the recipient by generating a new identity and re-encrypting retained artifacts.
3. Maintain at least one tested offline recovery copy of the identity.
4. Treat lost identities as unrecoverable data loss; there is no back door.
5. Treat exposed identities as a breach and rotate immediately.
6. Never encrypt malware, stolen data, credential dumps, or unlawful material.
7. Continue applying the agent army's human approval gates after decryption; encryption protects data, not decision quality.
