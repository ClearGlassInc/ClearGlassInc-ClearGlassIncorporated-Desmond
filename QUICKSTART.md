# 🚀 ClearGlass Cryptocurrency - Quick Start Guide

Welcome to ClearGlass! This guide will get you up and running in 5 minutes.

## Installation

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Setup
```bash
python setup.py
```

This will:
- Create necessary directories
- Initialize the blockchain
- Create a sample wallet
- Run basic tests

## Basic Usage

### 1. Create Your Wallet
```bash
python clearglass_cli.py wallet create --name mywallet
```

**IMPORTANT:** Save your wallet file securely! It contains your private key.

### 2. Mine Some Blocks
Get your wallet address first:
```bash
python clearglass_cli.py wallet info --name mywallet
```

Then mine blocks to that address:
```bash
python clearglass_cli.py mine --address YOUR_ADDRESS --blocks 5
```

### 3. Check Your Balance
```bash
python clearglass_cli.py wallet balance --name mywallet
```

### 4. Send CGLASS
```bash
python clearglass_cli.py wallet send --from mywallet --to RECIPIENT_ADDRESS --amount 25
```

## Run the API Server

```bash
python clearglass_api.py
```

The API will be available at: http://localhost:5000

### API Examples

**Check Balance:**
```bash
curl http://localhost:5000/balance/YOUR_ADDRESS
```

**View Blockchain:**
```bash
curl http://localhost:5000/blockchain
```

**Get Stats:**
```bash
curl http://localhost:5000/stats
```

## Run Examples

See all features in action:
```bash
python examples.py
```

## Run Tests

```bash
python test_clearglass.py
```

## Project Structure

```
clearglass-cryptocurrency/
├── clearglass_blockchain.py    # Core blockchain
├── clearglass_wallet.py        # Wallet management
├── clearglass_api.py           # REST API server
├── clearglass_network.py       # P2P networking
├── clearglass_cli.py           # Command-line interface
├── setup.py                    # Installation script
├── examples.py                 # Usage examples
├── test_clearglass.py          # Test suite
├── requirements.txt            # Dependencies
├── config.ini                  # Configuration
├── README.md                   # Full documentation
├── WHITEPAPER.md              # Technical whitepaper
├── TECHNICAL_DOCS.md          # API & architecture docs
└── LICENSE                     # MIT License
```

## Key Commands

### Wallet Operations
```bash
# List wallets
python clearglass_cli.py wallet list

# View transaction history
python clearglass_cli.py wallet history --name mywallet

# Export public key
python clearglass_cli.py wallet info --name mywallet
```

### Blockchain Operations
```bash
# View blockchain info
python clearglass_cli.py blockchain-cmd info

# Validate blockchain
python clearglass_cli.py blockchain-cmd validate

# View recent blocks
python clearglass_cli.py blockchain-cmd blocks --limit 10

# View pending transactions
python clearglass_cli.py blockchain-cmd pending
```

### Mining
```bash
# Mine blocks
python clearglass_cli.py mine --address YOUR_ADDRESS --blocks 10
```

## Security Tips

1. **NEVER share your private key** - Anyone with your private key can spend your CGLASS
2. **Backup your wallet** - Copy your wallet file to multiple secure locations
3. **Verify addresses** - Double-check recipient addresses before sending
4. **Use testnet first** - Test everything before using real value

## Common Issues

### "Transaction validation failed"
- Make sure you have enough balance
- Verify the transaction was signed correctly

### "Wallet not found"
- Make sure you created the wallet first
- Check that you're using the correct wallet name

### "Port 5000 already in use"
- Change the port in `clearglass_api.py`
- Or stop the conflicting process

## Getting Help

- **Full Documentation:** README.md
- **Technical Details:** WHITEPAPER.md & TECHNICAL_DOCS.md
- **Examples:** Run `python examples.py`
- **CLI Help:** `python clearglass_cli.py --help`

## Next Steps

1. **Read the whitepaper** - WHITEPAPER.md explains the technical design
2. **Explore the API** - TECHNICAL_DOCS.md has full API documentation
3. **Run examples** - examples.py demonstrates all features
4. **Run tests** - test_clearglass.py verifies everything works

## Configuration

Edit `config.ini` to customize:
- Mining difficulty
- Block rewards
- Network settings
- Security options

## Important Notes

⚠️ **This is educational software**
- Not intended for production financial use
- Requires security audit before real deployment
- Use at your own risk

✅ **Open Source**
- MIT Licensed
- Contributions welcome
- Full source code included

## Enjoy ClearGlass!

**Transparency is Trust. Security is Paramount. Decentralization is Freedom.**

For questions or issues, check the documentation or run tests to verify setup.

Happy mining! 🔷
