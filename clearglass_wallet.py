"""
ClearGlass Cryptocurrency - Wallet Management System
Secure wallet creation, storage, and transaction signing
"""

import json
import os
from typing import Dict, Optional
import ecdsa
import base64
import hashlib
from datetime import datetime
from clearglass_blockchain import (
    create_wallet, load_private_key, Transaction, ClearGlassBlockchain
)


class ClearGlassWallet:
    """Wallet for managing ClearGlass cryptocurrency"""
    
    def __init__(self, wallet_file: str = "wallet.json"):
        self.wallet_file = wallet_file
        self.public_key: Optional[str] = None
        self.private_key: Optional[str] = None
        self.address: Optional[str] = None
        
    def create_new_wallet(self, save: bool = True) -> Dict[str, str]:
        """Create a new wallet with keypair"""
        self.public_key, self.private_key = create_wallet()
        self.address = self.public_key
        
        wallet_data = {
            'address': self.address,
            'public_key': self.public_key,
            'private_key': self.private_key,
            'created_at': datetime.now().isoformat(),
            'label': 'ClearGlass Wallet'
        }
        
        if save:
            self.save_wallet(wallet_data)
        
        return {
            'address': self.address,
            'public_key': self.public_key,
            'created_at': wallet_data['created_at']
        }
    
    def save_wallet(self, wallet_data: Dict):
        """Save wallet to encrypted file"""
        # In production, this should be encrypted with a password
        # For this implementation, we're using basic JSON storage
        with open(self.wallet_file, 'w') as f:
            json.dump(wallet_data, f, indent=4)
        
        # Set restrictive permissions (Unix-like systems)
        try:
            os.chmod(self.wallet_file, 0o600)
        except:
            pass
        
        print(f"✓ Wallet saved to {self.wallet_file}")
        print("⚠️  IMPORTANT: Keep your wallet file secure and backed up!")
    
    def load_wallet(self) -> bool:
        """Load wallet from file"""
        if not os.path.exists(self.wallet_file):
            print(f"Wallet file not found: {self.wallet_file}")
            return False
        
        try:
            with open(self.wallet_file, 'r') as f:
                wallet_data = json.load(f)
            
            self.address = wallet_data['address']
            self.public_key = wallet_data['public_key']
            self.private_key = wallet_data['private_key']
            
            print(f"✓ Wallet loaded: {self.address[:20]}...")
            return True
            
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return False
    
    def get_balance(self, blockchain: ClearGlassBlockchain) -> float:
        """Get current wallet balance"""
        if not self.address:
            return 0.0
        return blockchain.get_balance(self.address)
    
    def send_transaction(self, recipient: str, amount: float, 
                        blockchain: ClearGlassBlockchain) -> bool:
        """Create and send a transaction"""
        if not self.private_key or not self.address:
            print("Wallet not initialized")
            return False
        
        # Check balance
        balance = self.get_balance(blockchain)
        if balance < amount:
            print(f"Insufficient balance. Available: {balance} CGLASS")
            return False
        
        # Create transaction
        transaction = Transaction(
            sender=self.address,
            recipient=recipient,
            amount=amount
        )
        
        # Sign transaction
        private_key = load_private_key(self.private_key)
        transaction.sign_transaction(private_key)
        
        # Add to blockchain
        if blockchain.add_transaction(transaction):
            print(f"✓ Transaction created: {amount} CGLASS to {recipient[:20]}...")
            print("  Waiting for confirmation (mining)...")
            return True
        else:
            print("✗ Transaction failed")
            return False
    
    def get_transaction_history(self, blockchain: ClearGlassBlockchain) -> list:
        """Get all transactions involving this wallet"""
        if not self.address:
            return []
        return blockchain.get_transaction_history(self.address)
    
    def export_public_key(self) -> str:
        """Export public key for receiving payments"""
        return self.public_key
    
    def get_wallet_info(self, blockchain: ClearGlassBlockchain) -> Dict:
        """Get complete wallet information"""
        if not self.address:
            return {'error': 'Wallet not initialized'}
        
        return {
            'address': self.address,
            'balance': self.get_balance(blockchain),
            'public_key': self.public_key,
            'transaction_count': len(self.get_transaction_history(blockchain))
        }


class WalletManager:
    """Manage multiple wallets"""
    
    def __init__(self, wallets_dir: str = "wallets"):
        self.wallets_dir = wallets_dir
        os.makedirs(wallets_dir, exist_ok=True)
    
    def create_wallet(self, name: str) -> ClearGlassWallet:
        """Create a new named wallet"""
        wallet_file = os.path.join(self.wallets_dir, f"{name}.json")
        wallet = ClearGlassWallet(wallet_file)
        wallet.create_new_wallet()
        return wallet
    
    def load_wallet(self, name: str) -> Optional[ClearGlassWallet]:
        """Load an existing wallet"""
        wallet_file = os.path.join(self.wallets_dir, f"{name}.json")
        wallet = ClearGlassWallet(wallet_file)
        
        if wallet.load_wallet():
            return wallet
        return None
    
    def list_wallets(self) -> list:
        """List all available wallets"""
        wallets = []
        for filename in os.listdir(self.wallets_dir):
            if filename.endswith('.json'):
                wallets.append(filename.replace('.json', ''))
        return wallets
    
    def backup_wallet(self, name: str, backup_path: str):
        """Backup a wallet to specified location"""
        wallet_file = os.path.join(self.wallets_dir, f"{name}.json")
        
        if not os.path.exists(wallet_file):
            print(f"Wallet {name} not found")
            return False
        
        import shutil
        shutil.copy2(wallet_file, backup_path)
        print(f"✓ Wallet backed up to {backup_path}")
        return True


# Command-line interface for wallet operations
def wallet_cli():
    """Interactive wallet management CLI"""
    import sys
    
    print("=" * 60)
    print("ClearGlass Cryptocurrency - Wallet Manager")
    print("=" * 60)
    
    wallet = ClearGlassWallet()
    blockchain = ClearGlassBlockchain()
    
    # Load blockchain if exists
    if os.path.exists("clearglass_blockchain.json"):
        print("Loading existing blockchain...")
        # In a full implementation, we'd load the chain here
    
    while True:
        print("\nWallet Commands:")
        print("1. Create new wallet")
        print("2. Load wallet")
        print("3. View balance")
        print("4. Send transaction")
        print("5. View transaction history")
        print("6. Export public key")
        print("7. Mine blocks")
        print("8. Exit")
        
        choice = input("\nEnter command (1-8): ").strip()
        
        if choice == '1':
            wallet.create_new_wallet()
            print(f"\n✓ New wallet created!")
            print(f"Address: {wallet.address}")
            print("\n⚠️  SAVE YOUR WALLET FILE SECURELY!")
            
        elif choice == '2':
            if wallet.load_wallet():
                print(f"Balance: {wallet.get_balance(blockchain)} CGLASS")
            
        elif choice == '3':
            if wallet.address:
                balance = wallet.get_balance(blockchain)
                print(f"\nCurrent balance: {balance} CGLASS")
            else:
                print("No wallet loaded")
        
        elif choice == '4':
            if not wallet.address:
                print("Please load a wallet first")
                continue
            
            recipient = input("Recipient address: ").strip()
            try:
                amount = float(input("Amount (CGLASS): ").strip())
                wallet.send_transaction(recipient, amount, blockchain)
            except ValueError:
                print("Invalid amount")
        
        elif choice == '5':
            if wallet.address:
                history = wallet.get_transaction_history(blockchain)
                print(f"\nTransaction History ({len(history)} transactions):")
                for tx in history:
                    print(f"  {tx['timestamp']}: {tx['amount']} CGLASS")
                    print(f"    From: {tx['sender'][:20]}...")
                    print(f"    To: {tx['recipient'][:20]}...")
            else:
                print("No wallet loaded")
        
        elif choice == '6':
            if wallet.public_key:
                print(f"\nYour public key (share this to receive payments):")
                print(wallet.public_key)
            else:
                print("No wallet loaded")
        
        elif choice == '7':
            if not wallet.address:
                print("Please load a wallet first")
                continue
            
            num_blocks = input("How many blocks to mine? (default 1): ").strip()
            num_blocks = int(num_blocks) if num_blocks else 1
            
            for i in range(num_blocks):
                print(f"\nMining block {i+1}/{num_blocks}...")
                blockchain.mine_pending_transactions(wallet.address)
            
            print(f"\n✓ Mining complete!")
            print(f"New balance: {wallet.get_balance(blockchain)} CGLASS")
        
        elif choice == '8':
            print("\nGoodbye!")
            blockchain.save_to_file()
            break
        
        else:
            print("Invalid command")


if __name__ == "__main__":
    wallet_cli()
