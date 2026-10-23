# 🔷 ClearGlass Cryptocurrency (CGLASS)

![ClearGlass Logo](https://img.shields.io/badge/ClearGlass-CGLASS-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8+-blue?style=flat-square)

**Transparent. Secure. Decentralized.**

ClearGlass is a fully functional cryptocurrency built from the ground up with transparency and security at its core. Featuring a custom blockchain implementation, secure wallet system, and complete mining capabilities.

---

## 🌟 Features

### Core Blockchain
- ✅ **Proof of Work Mining** - Secure consensus mechanism
- ✅ **Digital Signatures** - ECDSA cryptographic security
- ✅ **Transaction Validation** - Automatic verification
- ✅ **Supply Cap** - Maximum 21 million CGLASS tokens
- ✅ **Blockchain Validation** - Full chain integrity checks

### Wallet System
- 💼 **Secure Key Management** - ECDSA keypair generation
- 💼 **Transaction Signing** - Cryptographically signed transfers
- 💼 **Balance Tracking** - Real-time balance updates
- 💼 **Transaction History** - Complete audit trail
- 💼 **Multiple Wallet Support** - Manage multiple addresses

### API & Network
- 🌐 **REST API** - Complete HTTP interface
- 🌐 **Node Registration** - Peer-to-peer networking ready
- 🌐 **Mining Endpoints** - Remote mining capability
- 🌐 **Real-time Stats** - Network statistics and monitoring

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the repository**
```bash
cd clearglass-cryptocurrency
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify installation**
```bash
python clearglass_blockchain.py
```

---

## 📖 Usage Guide

### 1. Running the Blockchain Demo
```bash
python clearglass_blockchain.py
```
This will:
- Initialize the blockchain with genesis block
- Create sample wallets
- Demonstrate mining and transactions
- Validate the blockchain

### 2. Wallet Management

#### Create a New Wallet
```bash
python clearglass_wallet.py
# Select option 1: Create new wallet
```

#### Interactive Wallet CLI
```bash
python clearglass_wallet.py
```

**Available Commands:**
1. Create new wallet
2. Load wallet
3. View balance
4. Send transaction
5. View transaction history
6. Export public key
7. Mine blocks
8. Exit

### 3. API Server

#### Start the API Server
```bash
python clearglass_api.py
```

Server runs on: `http://localhost:5000`

#### API Endpoints

**Blockchain Operations**
- `GET /` - API information and documentation
- `GET /blockchain` - Get full blockchain
- `GET /blockchain/latest` - Get latest block
- `GET /blockchain/validate` - Validate blockchain
- `GET /block/<index>` - Get specific block

**Transaction Operations**
- `POST /transaction/new` - Create new transaction
- `GET /transactions/<address>` - Get transaction history
- `GET /pending` - Get pending transactions

**Mining Operations**
- `POST /mine` - Mine pending transactions

**Wallet Operations**
- `POST /wallet/create` - Create new wallet
- `GET /balance/<address>` - Get address balance

**Network Operations**
- `POST /nodes/register` - Register network node
- `GET /nodes` - Get all registered nodes
- `GET /stats` - Get blockchain statistics

#### Example API Calls

**Create a Wallet**
```bash
curl -X POST http://localhost:5000/wallet/create
```

**Check Balance**
```bash
curl http://localhost:5000/balance/YOUR_ADDRESS
```

**Mine a Block**
```bash
curl -X POST http://localhost:5000/mine \
  -H "Content-Type: application/json" \
  -d '{"miner_address": "YOUR_ADDRESS"}'
```

**Get Blockchain Stats**
```bash
curl http://localhost:5000/stats
```

---

## 🏗️ Project Structure

```
clearglass-cryptocurrency/
├── clearglass_blockchain.py    # Core blockchain implementation
├── clearglass_wallet.py        # Wallet management system
├── clearglass_api.py           # REST API server
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── WHITEPAPER.md              # Technical whitepaper
├── TECHNICAL_DOCS.md          # Detailed technical documentation
├── LICENSE                     # MIT License
└── wallets/                   # Wallet storage directory
```

---

## ⚙️ Configuration

### Blockchain Parameters

These can be modified in `clearglass_blockchain.py`:

```python
DIFFICULTY = 4              # Mining difficulty (leading zeros)
MINING_REWARD = 50         # CGLASS tokens per block
MAX_SUPPLY = 21_000_000    # Total supply cap
BLOCK_TIME = 60            # Target seconds per block
```

### Network Configuration

API server settings in `clearglass_api.py`:
```python
HOST = '0.0.0.0'           # Server host
PORT = 5000                # Server port
DEBUG = True               # Debug mode
```

---

## 🔒 Security Features

### Cryptographic Security
- **ECDSA Signatures** - Secp256k1 elliptic curve
- **SHA-256 Hashing** - Industry-standard hashing
- **Proof of Work** - Prevents spam and attacks
- **Chain Validation** - Immutable transaction history

### Wallet Security
- **Private Key Storage** - Secure local storage
- **Transaction Signing** - All transactions must be signed
- **Balance Verification** - Prevents overspending
- **Address Validation** - Checks recipient validity

### Best Practices
1. **Never share your private key**
2. **Backup your wallet file securely**
3. **Use strong passwords** (when encryption is enabled)
4. **Verify recipient addresses** before sending
5. **Keep software updated**

---

## 💡 How It Works

### Transaction Flow
1. User creates transaction with sender, recipient, amount
2. Transaction is signed with sender's private key
3. Transaction is broadcast to network (pending pool)
4. Miner includes transaction in new block
5. Block is mined (Proof of Work)
6. Block is added to blockchain
7. Transaction is confirmed

### Mining Process
1. Collect pending transactions
2. Create block with transactions + mining reward
3. Find nonce that produces valid hash (Proof of Work)
4. Broadcast mined block to network
5. Receive mining reward (50 CGLASS)

### Wallet Operations
1. Generate ECDSA keypair
2. Public key becomes wallet address
3. Private key signs transactions
4. Balance calculated from blockchain history

---

## 📊 Technical Specifications

| Specification | Value |
|--------------|-------|
| **Algorithm** | Proof of Work (SHA-256) |
| **Block Time** | ~60 seconds |
| **Mining Reward** | 50 CGLASS |
| **Max Supply** | 21,000,000 CGLASS |
| **Difficulty** | 4 (adjustable) |
| **Signature Scheme** | ECDSA (Secp256k1) |
| **Hash Function** | SHA-256 |
| **Block Size** | Variable (transaction-dependent) |

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/
```

### Manual Testing
```bash
# Test blockchain
python clearglass_blockchain.py

# Test wallet
python clearglass_wallet.py

# Test API
python clearglass_api.py
# Then use curl or Postman to test endpoints
```

---

## 🛠️ Development

### Adding New Features

1. **Custom Transaction Types**
   - Extend `Transaction` class
   - Add validation logic
   - Update API endpoints

2. **Smart Contracts**
   - Create contract execution engine
   - Define contract language/VM
   - Add contract storage

3. **Network Consensus**
   - Implement peer-to-peer protocol
   - Add consensus algorithm
   - Build node synchronization

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document all functions
- Write unit tests

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## ⚠️ Disclaimer

**IMPORTANT:** This is an educational cryptocurrency implementation. It is NOT intended for production use or real financial transactions. Always conduct thorough security audits before deploying any cryptocurrency in a real-world environment.

Key Limitations:
- No peer-to-peer networking (centralized for demonstration)
- Basic wallet encryption
- No GUI interface (command-line only)
- Not audited by security professionals
- No consensus protocol for network conflicts

---

## 📚 Additional Resources

- **Whitepaper:** See `WHITEPAPER.md` for detailed technical design
- **Technical Docs:** See `TECHNICAL_DOCS.md` for API and architecture details
- **Bitcoin Whitepaper:** https://bitcoin.org/bitcoin.pdf
- **Ethereum Documentation:** https://ethereum.org/en/developers/docs/

---

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Core blockchain implementation
- ✅ Wallet system
- ✅ REST API
- ✅ Basic mining

### Phase 2 (Future)
- ⏳ Peer-to-peer networking
- ⏳ GUI wallet application
- ⏳ Mobile wallet app
- ⏳ Block explorer website

### Phase 3 (Advanced)
- ⏳ Smart contract support
- ⏳ Lightning network integration
- ⏳ Decentralized exchange
- ⏳ Governance system

---

## 💬 Support

For questions, issues, or contributions:
- **GitHub Issues:** Report bugs or request features
- **Documentation:** Check TECHNICAL_DOCS.md
- **Whitepaper:** Read WHITEPAPER.md for deep dive

---

## 🎉 Acknowledgments

Built with inspiration from:
- Bitcoin - The original cryptocurrency
- Ethereum - Smart contract innovation
- Modern blockchain research and development

---

**Made with 💙 by the ClearGlass Development Team**

*Transparency is Trust. Security is Paramount. Decentralization is Freedom.*
