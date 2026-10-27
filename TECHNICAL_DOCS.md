# ClearGlass Cryptocurrency - Technical Documentation

Version 1.0 | Last Updated: January 2026

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [API Reference](#api-reference)
4. [Cryptography Details](#cryptography-details)
5. [Data Structures](#data-structures)
6. [Network Protocol](#network-protocol)
7. [Development Guide](#development-guide)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────┐
│              ClearGlass Network                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   Wallet     │◄────►│  Blockchain  │        │
│  │   Manager    │      │    Core      │        │
│  └──────────────┘      └──────────────┘        │
│         │                      │                 │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │     API      │◄────►│   Network    │        │
│  │   Server     │      │    Nodes     │        │
│  └──────────────┘      └──────────────┘        │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Python 3.8+
- **Cryptography**: ECDSA (ecdsa library)
- **Hashing**: SHA-256 (hashlib)
- **Web Framework**: Flask
- **Data Format**: JSON

---

## Core Components

### 1. Transaction Class

**Purpose**: Represents a single transaction in the network

**Properties**:
```python
sender: str              # Sender's public key (address)
recipient: str           # Recipient's public key (address)
amount: float           # Amount to transfer
timestamp: float        # Unix timestamp
signature: str          # ECDSA signature (base64)
```

**Methods**:

#### `to_dict() -> Dict`
Converts transaction to JSON-serializable dictionary.

```python
transaction = Transaction("Alice", "Bob", 10.5)
data = transaction.to_dict()
# Returns: {"sender": "Alice", "recipient": "Bob", ...}
```

#### `calculate_hash() -> str`
Calculates SHA-256 hash of transaction data for signing.

```python
tx_hash = transaction.calculate_hash()
# Returns: "a3f5b9c2d1e4..."
```

#### `sign_transaction(private_key: ecdsa.SigningKey)`
Signs the transaction with provided private key.

```python
from clearglass_blockchain import load_private_key

private_key = load_private_key(encoded_private_key)
transaction.sign_transaction(private_key)
```

#### `is_valid() -> bool`
Verifies transaction signature is valid.

```python
if transaction.is_valid():
    print("Transaction is valid")
```

**Special Transactions**:
- **Mining Reward**: sender = "NETWORK_REWARD" (no signature required)
- **Genesis**: sender = "GENESIS" (first block transaction)

---

### 2. Block Class

**Purpose**: Container for transactions forming the blockchain

**Properties**:
```python
index: int                      # Block number (0, 1, 2, ...)
transactions: List[Transaction] # List of transactions
previous_hash: str             # Hash of previous block
timestamp: float               # Block creation time
nonce: int                     # Proof of Work nonce
hash: str                      # This block's hash
```

**Methods**:

#### `calculate_hash() -> str`
Computes SHA-256 hash of block contents.

```python
block_hash = block.calculate_hash()
```

Hash includes:
- Block index
- All transactions (serialized)
- Previous block hash
- Timestamp
- Nonce

#### `mine_block(difficulty: int)`
Performs Proof of Work to find valid hash.

```python
block.mine_block(difficulty=4)
# Finds nonce where hash starts with "0000"
```

**Mining Algorithm**:
```python
while not hash.startswith('0' * difficulty):
    nonce += 1
    hash = calculate_hash()
```

#### `to_dict() -> Dict`
Exports block as JSON-serializable dictionary.

```python
block_data = block.to_dict()
```

---

### 3. ClearGlassBlockchain Class

**Purpose**: Main blockchain manager and validator

**Class Constants**:
```python
DIFFICULTY = 4           # Mining difficulty
MINING_REWARD = 50      # CGLASS per block
MAX_SUPPLY = 21_000_000 # Total supply cap
BLOCK_TIME = 60         # Target seconds per block
```

**Methods**:

#### `__init__()`
Initializes blockchain with genesis block.

```python
blockchain = ClearGlassBlockchain()
# Chain automatically starts with block 0
```

#### `add_transaction(transaction: Transaction) -> bool`
Adds validated transaction to pending pool.

**Validation Steps**:
1. Check sender and recipient exist
2. Verify signature (`transaction.is_valid()`)
3. Check sender has sufficient balance
4. Add to pending pool if valid

```python
success = blockchain.add_transaction(transaction)
if success:
    print("Transaction added to mempool")
```

**Returns**: `True` if added, `False` if invalid

#### `mine_pending_transactions(mining_reward_address: str)`
Mines new block with pending transactions.

**Process**:
1. Check if max supply reached
2. Calculate mining reward
3. Create reward transaction
4. Create new block with pending + reward
5. Mine block (Proof of Work)
6. Add block to chain
7. Clear pending transactions

```python
blockchain.mine_pending_transactions("miner_address")
# Creates and mines new block
```

#### `get_balance(address: str) -> float`
Calculates current balance for address.

**Calculation**:
```python
balance = 0
for block in chain:
    for tx in block.transactions:
        if tx.sender == address:
            balance -= tx.amount
        if tx.recipient == address:
            balance += tx.amount
return balance
```

#### `is_chain_valid() -> bool`
Validates entire blockchain integrity.

**Checks**:
1. Each block hash is correct
2. Each block links to previous
3. All transactions are valid
4. Proof of Work satisfied

```python
if blockchain.is_chain_valid():
    print("Blockchain is valid")
```

#### `get_transaction_history(address: str) -> List[Dict]`
Returns all transactions for address.

```python
history = blockchain.get_transaction_history(address)
for tx in history:
    print(f"Amount: {tx['amount']}, Block: {tx['block_index']}")
```

#### `save_to_file(filename: str)`
Exports blockchain to JSON file.

```python
blockchain.save_to_file("my_blockchain.json")
```

---

### 4. Wallet System

#### `ClearGlassWallet` Class

**Purpose**: Manage keys and create transactions

**Methods**:

##### `create_new_wallet(save: bool = True) -> Dict`
Generates new ECDSA keypair.

```python
wallet = ClearGlassWallet()
wallet_data = wallet.create_new_wallet()
print(f"Address: {wallet_data['address']}")
```

##### `load_wallet() -> bool`
Loads wallet from file.

```python
wallet = ClearGlassWallet("my_wallet.json")
if wallet.load_wallet():
    print("Wallet loaded successfully")
```

##### `send_transaction(recipient: str, amount: float, blockchain)`
Creates, signs, and broadcasts transaction.

```python
wallet.send_transaction(
    recipient="recipient_address",
    amount=25.5,
    blockchain=blockchain
)
```

##### `get_balance(blockchain) -> float`
Gets current wallet balance.

```python
balance = wallet.get_balance(blockchain)
print(f"Balance: {balance} CGLASS")
```

---

## API Reference

### Base URL
```
http://localhost:5000
```

### Authentication
Currently no authentication required (add for production)

### Response Format
All responses in JSON format:
```json
{
  "success": true,
  "data": {...},
  "message": "Optional message"
}
```

---

### Endpoints

#### `GET /`
Returns API documentation and available endpoints.

**Response**:
```json
{
  "name": "ClearGlass Cryptocurrency API",
  "version": "1.0.0",
  "endpoints": {...]
}
```

---

#### `GET /blockchain`
Returns complete blockchain.

**Response**:
```json
{
  "chain": [
    {
      "index": 0,
      "transactions": [...],
      "hash": "abc123...",
      ...
    }
  ],
  "length": 5
}
```

---

#### `GET /blockchain/latest`
Returns most recent block.

**Response**:
```json
{
  "index": 4,
  "transactions": [...],
  "previous_hash": "def456...",
  "timestamp": 1672531200.0,
  "nonce": 12345,
  "hash": "ghi789..."
}
```

---

#### `POST /transaction/new`
Creates new transaction.

**Request Body**:
```json
{
  "sender": "base64_public_key",
  "recipient": "base64_public_key",
  "amount": 10.5,
  "signature": "base64_signature"
}
```

**Response** (201 Created):
```json
{
  "message": "Transaction added to pending pool",
  "transaction": {...}
}
```

**Error** (400 Bad Request):
```json
{
  "error": "Invalid transaction"
}
```

---

#### `POST /mine`
Mines pending transactions.

**Request Body**:
```json
{
  "miner_address": "base64_public_key"
}
```

**Response**:
```json
{
  "message": "Block mined successfully",
  "block": {...},
  "mining_time": 2.34,
  "reward": 50
}
```

---

#### `GET /balance/<address>`
Gets balance for address.

**Example**:
```
GET /balance/Aw5xY7Zq...
```

**Response**:
```json
{
  "address": "Aw5xY7Zq...",
  "balance": 150.5,
  "currency": "CGLASS"
}
```

---

#### `GET /transactions/<address>`
Gets transaction history for address.

**Response**:
```json
{
  "address": "Aw5xY7Zq...",
  "transaction_count": 5,
  "transactions": [
    {
      "sender": "...",
      "recipient": "...",
      "amount": 10.0,
      "timestamp": 1672531200.0,
      "block_index": 2
    }
  ]
}
```

---

#### `POST /wallet/create`
Creates new wallet.

**Response** (201 Created):
```json
{
  "address": "base64_public_key",
  "public_key": "base64_public_key",
  "private_key": "base64_private_key",
  "warning": "SAVE YOUR PRIVATE KEY SECURELY!"
}
```

⚠️ **CRITICAL**: Save private key immediately - it cannot be recovered!

---

#### `GET /stats`
Returns network statistics.

**Response**:
```json
{
  "blocks": 100,
  "total_transactions": 250,
  "total_supply": 5000,
  "max_supply": 21000000,
  "mining_reward": 50,
  "difficulty": 4,
  "pending_transactions": 3,
  "supply_percentage": 0.0238
}
```

---

#### `POST /nodes/register`
Registers network node.

**Request Body**:
```json
{
  "node_address": "http://192.168.1.100:5000"
}
```

**Response**:
```json
{
  "message": "Node registered successfully",
  "total_nodes": 5,
  "nodes": ["http://...", "http://..."]
}
```

---

#### `GET /nodes`
Lists all registered nodes.

**Response**:
```json
{
  "total_nodes": 5,
  "nodes": [
    "http://192.168.1.100:5000",
    "http://192.168.1.101:5000"
  ]
}
```

---

## Cryptography Details

### ECDSA (Elliptic Curve Digital Signature Algorithm)

**Curve**: secp256k1 (same as Bitcoin)

**Key Generation**:
```python
import ecdsa

# Generate private key (256-bit random number)
private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

# Derive public key
public_key = private_key.get_verifying_key()
```

**Signing**:
```python
# Create signature
message = b"transaction_data"
signature = private_key.sign(message)
```

**Verification**:
```python
# Verify signature
try:
    public_key.verify(signature, message)
    print("Valid signature")
except ecdsa.BadSignatureError:
    print("Invalid signature")
```

### SHA-256 Hashing

```python
import hashlib

# Calculate hash
data = "Hello, ClearGlass!"
hash_value = hashlib.sha256(data.encode()).hexdigest()
# Returns: "a1b2c3d4..."
```

**Properties**:
- Output: Always 256 bits (64 hex characters)
- Deterministic: Same input → same output
- One-way: Cannot reverse hash to get input
- Collision-resistant: Practically impossible to find two inputs with same hash

---

## Data Structures

### Transaction Object
```python
{
    "sender": "base64_encoded_public_key",
    "recipient": "base64_encoded_public_key",
    "amount": 10.5,
    "timestamp": 1672531200.0,
    "signature": "base64_encoded_signature"
}
```

### Block Object
```python
{
    "index": 1,
    "transactions": [Transaction, Transaction, ...],
    "previous_hash": "abc123...",
    "timestamp": 1672531200.0,
    "nonce": 12345,
    "hash": "def456..."
}
```

### Wallet File
```json
{
    "address": "base64_public_key",
    "public_key": "base64_public_key",
    "private_key": "base64_private_key",
    "created_at": "2026-01-21T10:30:00",
    "label": "ClearGlass Wallet"
}
```

---

## Development Guide

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/clearglass

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

### Code Style

Follow PEP 8:
```python
# Good
def calculate_balance(address: str) -> float:
    """Calculate balance for given address."""
    return blockchain.get_balance(address)

# Bad
def calc_bal(addr):
    return blockchain.get_balance(addr)
```

### Adding New Features

1. **Create feature branch**
```bash
git checkout -b feature/new-feature
```

2. **Write tests first** (TDD)
```python
def test_new_feature():
    assert new_feature() == expected_result
```

3. **Implement feature**
4. **Run tests**
5. **Submit pull request**

---

## Troubleshooting

### Common Issues

#### "Transaction validation failed"
**Cause**: Invalid signature or insufficient balance  
**Solution**: 
- Verify transaction was signed with correct private key
- Check sender has enough balance

#### "Block hash invalid"
**Cause**: Hash doesn't meet difficulty requirement  
**Solution**: Mine block longer or reduce difficulty

#### "Port 5000 already in use"
**Cause**: Another process using port 5000  
**Solution**:
```python
# Change port in clearglass_api.py
app.run(host='0.0.0.0', port=5001)
```

#### "Wallet file not found"
**Cause**: Wallet file doesn't exist  
**Solution**: Create new wallet first

```python
wallet = ClearGlassWallet()
wallet.create_new_wallet()
```

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Tips

1. **Reduce Mining Difficulty**: For testing, use difficulty=2
2. **Batch Transactions**: Mine multiple transactions per block
3. **Cache Balances**: Store calculated balances temporarily
4. **Database**: Use database instead of JSON for large chains

---

## Performance Benchmarks

### Mining Performance
- **Difficulty 1**: ~0.001 seconds
- **Difficulty 2**: ~0.01 seconds
- **Difficulty 3**: ~0.1 seconds
- **Difficulty 4**: ~1-2 seconds
- **Difficulty 5**: ~10-20 seconds

### Transaction Throughput
- **Validation**: ~1000 tx/second
- **Signing**: ~500 tx/second
- **Balance Calculation**: ~200 addresses/second

### Storage Requirements
- **Per Transaction**: ~300 bytes
- **Per Block**: ~5-50 KB (depends on transactions)
- **Per 1000 Blocks**: ~5-50 MB

---

## Security Best Practices

### For Developers

1. **Never commit private keys**
   - Add `*.json` to `.gitignore` for wallet files
   - Use environment variables for sensitive data

2. **Validate all inputs**
   ```python
   if not isinstance(amount, (int, float)) or amount <= 0:
       raise ValueError("Invalid amount")
   ```

3. **Use HTTPS in production**
   - Never send private keys over HTTP
   - Implement proper TLS/SSL

4. **Rate limit API endpoints**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, default_limits=["100 per hour"])
   ```

### For Users

1. **Backup wallet files** - Store in multiple secure locations
2. **Never share private keys** - Not even with "support"
3. **Verify addresses** - Double-check before sending
4. **Use strong passwords** - For encrypted wallets
5. **Keep software updated** - Install security patches

---

## Glossary

- **Address**: Public key used to receive transactions
- **Block**: Container of transactions added to blockchain
- **Blockchain**: Immutable ledger of all transactions
- **CGLASS**: ClearGlass cryptocurrency token
- **Difficulty**: Number of leading zeros required in block hash
- **Genesis Block**: First block in the blockchain
- **Hash**: Fixed-size output from hash function
- **Mining**: Process of creating new blocks
- **Nonce**: Number adjusted to find valid block hash
- **Private Key**: Secret key used to sign transactions
- **Public Key**: Derived from private key, used as address
- **Signature**: Proof of ownership created with private key
- **Transaction**: Transfer of value between addresses
- **Wallet**: Software that manages keys and creates transactions

---

**For more information, see**:
- README.md - Getting started guide
- WHITEPAPER.md - Detailed technical design
- GitHub Issues - Bug reports and feature requests

---

*ClearGlass Technical Documentation*  
*Version 1.0 | January 2026*
