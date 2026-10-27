#!/usr/bin/env python3
"""
ClearGlass Cryptocurrency - Setup and Installation Script
"""

import os
import sys
import subprocess

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60 + "\n")


def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} detected")


def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        'wallets',
        'data',
        'logs',
        'backups'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created: {directory}/")
    
    # Create .gitignore to protect wallet files
    gitignore_content = """# ClearGlass - Ignore sensitive files
wallets/*.json
*.key
*.pem
data/*.json
logs/*.log
backups/*
__pycache__/
*.pyc
.env
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    print("✓ Created .gitignore")


def initialize_blockchain():
    """Initialize the blockchain"""
    print("\n⛓️  Initializing blockchain...")
    
    try:
        from clearglass_blockchain import ClearGlassBlockchain
        
        blockchain = ClearGlassBlockchain()
        blockchain.save_to_file('data/blockchain.json')
        
        print("✓ Blockchain initialized with genesis block")
        print(f"  Genesis block hash: {blockchain.chain[0].hash[:40]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize blockchain: {e}")
        return False


def create_sample_wallet():
    """Create a sample wallet for testing"""
    print("\n👛 Creating sample wallet...")
    
    try:
        from clearglass_wallet import ClearGlassWallet
        
        wallet = ClearGlassWallet('wallets/sample_wallet.json')
        wallet_data = wallet.create_new_wallet()
        
        print("✓ Sample wallet created")
        print(f"  Address: {wallet_data['address'][:40]}...")
        print("  Saved to: wallets/sample_wallet.json")
        print("\n⚠️  This is a SAMPLE wallet for testing only!")
        print("  Create your own wallet with: python clearglass_cli.py wallet create --name mywallet")
        return True
    except Exception as e:
        print(f"❌ Failed to create sample wallet: {e}")
        return False


def run_tests():
    """Run basic tests"""
    print("\n🧪 Running tests...")
    
    try:
        # Test blockchain
        from clearglass_blockchain import ClearGlassBlockchain, Transaction, create_wallet
        
        blockchain = ClearGlassBlockchain()
        alice_pub, alice_priv = create_wallet()
        bob_pub, bob_priv = create_wallet()
        
        # Test mining
        blockchain.mine_pending_transactions(alice_pub)
        
        # Test transaction
        from clearglass_blockchain import load_private_key
        tx = Transaction(alice_pub, bob_pub, 10)
        tx.sign_transaction(load_private_key(alice_priv))
        blockchain.add_transaction(tx)
        
        # Test validation
        is_valid = blockchain.is_chain_valid()
        
        if is_valid:
            print("✓ All tests passed")
            return True
        else:
            print("❌ Tests failed: Invalid blockchain")
            return False
            
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False


def print_quick_start():
    """Print quick start guide"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete! Quick Start Guide".center(60))
    print("=" * 60)
    
    print("\n1️⃣  Create a wallet:")
    print("   python clearglass_cli.py wallet create --name mywallet")
    
    print("\n2️⃣  Mine some blocks:")
    print("   python clearglass_cli.py mine --address <your_address> --blocks 5")
    
    print("\n3️⃣  Check your balance:")
    print("   python clearglass_cli.py wallet balance --name mywallet")
    
    print("\n4️⃣  Start the API server:")
    print("   python clearglass_api.py")
    
    print("\n5️⃣  Start a network node:")
    print("   python clearglass_network.py")
    
    print("\n📚 Documentation:")
    print("   • README.md - Getting started guide")
    print("   • WHITEPAPER.md - Technical whitepaper")
    print("   • TECHNICAL_DOCS.md - API and architecture details")
    
    print("\n🔗 Useful Commands:")
    print("   • View blockchain info: python clearglass_cli.py blockchain-cmd info")
    print("   • Validate blockchain: python clearglass_cli.py blockchain-cmd validate")
    print("   • View version: python clearglass_cli.py version")
    
    print("\n⚠️  Security Reminders:")
    print("   • NEVER share your private keys")
    print("   • Backup your wallet files regularly")
    print("   • Keep your software updated")
    
    print("\n" + "=" * 60 + "\n")


def main():
    """Main setup routine"""
    print_header("ClearGlass Cryptocurrency - Setup")
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Initialize blockchain
    if not initialize_blockchain():
        print("\n⚠️  Blockchain initialization failed, but setup will continue")
    
    # Create sample wallet
    if not create_sample_wallet():
        print("\n⚠️  Sample wallet creation failed, but setup will continue")
    
    # Run tests
    print("\n" + "-" * 60)
    if not run_tests():
        print("\n⚠️  Some tests failed, but setup is complete")
    
    # Print quick start guide
    print_quick_start()
    
    print("✅ Setup completed successfully!")
    print("\nFor help, run: python clearglass_cli.py --help\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)
